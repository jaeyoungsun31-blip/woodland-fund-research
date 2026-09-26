"""AQR TSMOM factor parsing — external validation source.

Skipped entirely when the optional `external` extra is absent, since the core
pipeline never reads spreadsheets.
"""

import io

import pandas as pd
import pytest

from woodland import aqr

pytest.importorskip("openpyxl", reason="needs the 'external' extra")


def workbook(rows=None, header_offset=12, sheet=aqr.SHEET) -> bytes:
    """Build a workbook shaped like AQR's: preamble, header, then dated rows."""
    rows = rows if rows is not None else [
        ("1985-01-31", 0.0435, -0.0130, 0.1534, -0.0156, 0.0560),
        ("1985-02-28", 0.0377, 0.0462, 0.0431, -0.1938, 0.0993),
        ("1985-03-29", -0.0520, -0.0816, 0.0328, 0.0710, -0.1171),
    ]
    table: list[list] = [[None] * 6 for _ in range(header_offset)]
    table[0][0] = "AQR Capital Management, LLC — Time Series Momentum"
    table.append([None, "TSMOM", "TSMOM^CM", "TSMOM^EQ", "TSMOM^FI", "TSMOM^FX"])
    for row in rows:
        table.append([pd.Timestamp(row[0]), *row[1:]])
    table.append(["Copyright 2026 AQR", None, None, None, None, None])

    buffer = io.BytesIO()
    pd.DataFrame(table).to_excel(buffer, sheet_name=sheet, header=False, index=False)
    return buffer.getvalue()


def test_parses_factors_after_a_variable_length_preamble():
    """The header is found by content, not by a fixed row offset — AQR moves it."""
    for offset in (8, 12, 20):
        factors = aqr.parse_tsmom_monthly(workbook(header_offset=offset))
        assert list(factors.columns) == ["TSMOM", "TSMOM^CM", "TSMOM^EQ",
                                         "TSMOM^FI", "TSMOM^FX"]
        assert len(factors) == 3
        assert factors.index[0] == pd.Timestamp("1985-01-31")
        assert factors.loc["1985-01-31", "TSMOM"] == pytest.approx(0.0435)


def test_trailing_copyright_line_is_dropped():
    factors = aqr.parse_tsmom_monthly(workbook())
    assert factors.index.notna().all()
    assert len(factors) == 3


def test_missing_header_is_rejected():
    buffer = io.BytesIO()
    pd.DataFrame([["nothing here", "NOTMOM"], ["still nothing", "ALSONOT"]]).to_excel(
        buffer, sheet_name=aqr.SHEET, header=False, index=False)
    with pytest.raises(ValueError, match="header row not found"):
        aqr.parse_tsmom_monthly(buffer.getvalue())


def test_single_column_sheet_reports_clearly_rather_than_indexing_off_the_end():
    buffer = io.BytesIO()
    pd.DataFrame([["only one column"]]).to_excel(
        buffer, sheet_name=aqr.SHEET, header=False, index=False)
    with pytest.raises(ValueError, match="expected a date column"):
        aqr.parse_tsmom_monthly(buffer.getvalue())


def test_percentage_scaled_values_are_rejected():
    """A guard against AQR switching to percent: 4.35 is not a monthly return."""
    rows = [("1985-01-31", 4.35, 0.1, 0.1, 0.1, 0.1),
            ("1985-02-28", 3.77, 0.1, 0.1, 0.1, 0.1)]
    with pytest.raises(ValueError, match="percentages, not decimals"):
        aqr.parse_tsmom_monthly(workbook(rows))


def test_unsorted_dates_are_rejected():
    rows = [("1985-02-28", 0.03, 0.1, 0.1, 0.1, 0.1),
            ("1985-01-31", 0.04, 0.1, 0.1, 0.1, 0.1)]
    with pytest.raises(ValueError, match="unique and increasing"):
        aqr.parse_tsmom_monthly(workbook(rows))


def test_non_zip_payload_is_rejected(monkeypatch):
    class Response:
        content = b"<html>not a workbook</html>"
        def raise_for_status(self): return None
    monkeypatch.setattr(aqr.requests, "get", lambda *a, **k: Response())
    with pytest.raises(ValueError, match="did not return an xlsx"):
        aqr.fetch_tsmom_monthly()


def test_ingest_persists_data_and_provenance(tmp_path, monkeypatch):
    payload = workbook()

    class Response:
        content = payload
        def raise_for_status(self): return None

    monkeypatch.setattr(aqr.requests, "get", lambda *a, **k: Response())
    result = aqr.ingest_tsmom_monthly(tmp_path / "aqr.parquet")

    assert result.data_path.exists() and result.provenance_path.exists()
    prov = result.provenance
    assert prov["rows"] == 3
    assert prov["frequency"] == "monthly"
    assert prov["values"] == "excess returns, decimal"
    assert len(str(prov["archive_sha256"])) == 64
    assert "long/short" in str(prov["limitations"]).lower()
    assert pd.read_parquet(result.data_path).equals(result.returns)


def test_load_says_how_to_build_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="ingest_aqr"):
        aqr.load_tsmom_monthly(tmp_path)


def test_month_end_compounding_matches_a_hand_computation():
    """Daily -> monthly alignment must compound, not average or sum."""
    index = pd.bdate_range("2020-01-01", "2020-02-28")
    daily = pd.Series(0.001, index=index)
    monthly = aqr.to_month_end_returns(daily)
    january = index[index.month == 1]
    assert monthly.iloc[0] == pytest.approx(1.001 ** len(january) - 1)
    assert len(monthly) == 2
