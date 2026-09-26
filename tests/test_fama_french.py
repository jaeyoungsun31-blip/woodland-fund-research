"""Fama-French 12-industry ingestion and index construction."""

from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from woodland import fama_french


def _archive(body: str, member: str = "12_Industry_Portfolios_Daily.csv") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, mode="w") as archive:
        archive.writestr(member, body)
    return output.getvalue()


def _fixture_body() -> str:
    header = "," + ",".join(fama_french.INDUSTRIES)
    return "\n".join(
        [
            "This file contains value- and equal-weighted returns.",
            "Missing data are indicated by -99.99 or -999.",
            "",
            "  Average Value Weighted Returns -- Daily",
            header,
            "19260701," + ",".join(["1.00"] * 12),
            "19260702," + ",".join(["-0.50"] * 12),
            "",
            "  Average Equal Weighted Returns -- Daily",
            header,
            "19260701," + ",".join(["9.00"] * 12),
        ]
    )


def test_parser_selects_value_weighted_block_and_converts_percentages():
    returns = fama_french.parse_12_industry_daily(_archive(_fixture_body()))

    assert list(returns.columns) == list(fama_french.INDUSTRIES)
    assert list(returns.index) == [pd.Timestamp("1926-07-01"), pd.Timestamp("1926-07-02")]
    assert returns.index.name == "Date"
    assert returns.iloc[0, 0] == pytest.approx(0.01)
    assert returns.iloc[1, 0] == pytest.approx(-0.005)
    assert returns.max().max() < 0.02  # equal-weighted 9% block was not spliced


def test_parser_rejects_missing_or_malformed_sections():
    with pytest.raises(ValueError, match="section not found"):
        fama_french.parse_12_industry_daily(_archive("not the expected file"))

    malformed = _fixture_body().replace("19260701,1.00", "19260701")
    with pytest.raises(ValueError, match="malformed"):
        fama_french.parse_12_industry_daily(_archive(malformed))


def test_missing_sentinel_is_preserved_as_missing_then_blocks_compounding():
    body = _fixture_body().replace("19260701,1.00", "19260701,-99.99", 1)
    returns = fama_french.parse_12_industry_daily(_archive(body))

    assert pd.isna(returns.iloc[0, 0])
    with pytest.raises(ValueError, match="missing returns"):
        fama_french.returns_to_index_levels(returns)


def test_returns_compound_to_base_100_levels():
    index = pd.date_range("2020-01-01", periods=2, name="Date")
    returns = pd.DataFrame({"A": [0.10, -0.10]}, index=index)

    levels = fama_french.returns_to_index_levels(returns)

    assert levels.iloc[:, 0].tolist() == pytest.approx([110.0, 99.0])


def test_ingest_persists_levels_and_explicit_academic_provenance(tmp_path, monkeypatch):
    payload = _archive(_fixture_body())
    monkeypatch.setattr(fama_french, "fetch_12_industry_daily", lambda timeout=60: payload)
    output = tmp_path / "ff12.parquet"

    result = fama_french.ingest_12_industry_daily(output)

    pd.testing.assert_frame_equal(pd.read_parquet(output), result.levels)
    assert result.provenance_path.exists()
    assert result.provenance["first"] == "1926-07-01"
    assert result.provenance["portfolio_weighting"] == "value weighted"
    assert "Frictionless academic" in str(result.provenance["limitations"])


# --------------------------------------------------------------- factors

FACTOR_CSV = """This file was created by CMPT_ME_BEME_RETS using the CRSP database.

,Mkt-RF,SMB,HML,RF
19260701, 0.10,-0.24,-0.28,0.009
19260702, 0.45,-0.32,-0.08,0.009
19260706,-0.17, 0.27,-0.35,0.009
19260707,-99.99,-99.99,-99.99,-99.99

Copyright 2026 Kenneth R. French
"""


def _factor_zip(text: str = FACTOR_CSV) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("F-F_Research_Data_Factors_daily.CSV", text)
    return buffer.getvalue()


def test_parse_factors_converts_percentages_and_masks_sentinels():
    factors = fama_french.parse_research_factors_daily(_factor_zip())
    assert list(factors.columns) == list(fama_french.FACTOR_COLUMNS)
    assert factors.index[0] == pd.Timestamp("1926-07-01")
    assert factors.loc["1926-07-01", "Mkt-RF"] == pytest.approx(0.0010)
    assert factors.loc["1926-07-01", "RF"] == pytest.approx(0.00009)
    assert factors.loc["1926-07-02", "SMB"] == pytest.approx(-0.0032)
    assert factors.loc["1926-07-07"].isna().all()      # -99.99 sentinel row


def test_parse_factors_stops_at_the_copyright_line():
    factors = fama_french.parse_research_factors_daily(_factor_zip())
    assert len(factors) == 4


def test_parse_factors_rejects_a_missing_header():
    bad = _factor_zip("no header here\n19260701,0.1\n")
    with pytest.raises(ValueError, match="factor header"):
        fama_french.parse_research_factors_daily(bad)


def test_parse_factors_rejects_a_short_row():
    bad = _factor_zip(",Mkt-RF,SMB,HML,RF\n19260701,0.10,-0.24\n")
    with pytest.raises(ValueError, match="malformed factor row"):
        fama_french.parse_research_factors_daily(bad)


def test_market_total_return_adds_the_risk_free_rate_back():
    """MKT must be a TOTAL return; Mkt-RF alone is an excess return and would
    understate the equity baseline by the whole T-bill yield."""
    factors = fama_french.parse_research_factors_daily(_factor_zip())
    derived = fama_french.market_and_cash_returns(factors)
    assert list(derived.columns) == ["MKT", "CASH"]
    assert derived.loc["1926-07-01", "MKT"] == pytest.approx(0.0010 + 0.00009)
    assert derived.loc["1926-07-01", "CASH"] == pytest.approx(0.00009)
    assert len(derived) == 3, "the all-missing row must be dropped, not zero-filled"


def test_market_and_cash_requires_the_needed_columns():
    with pytest.raises(ValueError, match="missing"):
        fama_french.market_and_cash_returns(pd.DataFrame({"SMB": [0.1]}))


def test_cash_levels_compound_upward_and_never_fall():
    """The defensive leg must earn the T-bill rate, so its level is
    non-decreasing whenever the rate is non-negative."""
    factors = fama_french.parse_research_factors_daily(_factor_zip())
    levels = fama_french.returns_to_index_levels(
        fama_french.market_and_cash_returns(factors))
    cash = levels["CASH"]
    assert (cash.diff().dropna() >= 0).all()
    assert cash.iloc[-1] > cash.iloc[0]
