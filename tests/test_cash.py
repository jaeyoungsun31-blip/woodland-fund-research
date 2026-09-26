"""The risk-free (cash) leg: loading and calendar alignment."""

import hashlib

import numpy as np
import pandas as pd
import pytest

from woodland import cash


def levels(index, daily_rate=0.0002):
    return pd.DataFrame({cash.CASH_COLUMN: 100 * (1 + daily_rate) ** np.arange(len(index))},
                        index=index)


def test_load_recovers_the_daily_rate_from_index_levels(tmp_path):
    index = pd.bdate_range("2020-01-01", periods=500)
    levels(index).to_parquet(tmp_path / cash.FACTORS_PARQUET)
    rf = cash.load_risk_free_daily(tmp_path)
    assert len(rf) == 499                          # pct_change drops the first
    assert np.allclose(rf.to_numpy(), 0.0002)
    assert rf.name == "risk_free"


def test_missing_file_says_how_to_build_it(tmp_path):
    with pytest.raises(FileNotFoundError, match="ingest_fama_french"):
        cash.load_risk_free_daily(tmp_path)


def test_missing_column_is_rejected(tmp_path):
    pd.DataFrame({"MKT": [1.0, 2.0]},
                 index=pd.bdate_range("2020-01-01", periods=2)).to_parquet(
        tmp_path / cash.FACTORS_PARQUET)
    with pytest.raises(ValueError, match="CASH"):
        cash.load_risk_free_daily(tmp_path)


def test_negative_rates_are_rejected(tmp_path):
    index = pd.bdate_range("2020-01-01", periods=10)
    frame = levels(index)
    frame.iloc[5, 0] = frame.iloc[4, 0] * 0.9      # a fall in the cash index
    frame.to_parquet(tmp_path / cash.FACTORS_PARQUET)
    with pytest.raises(ValueError, match="negative daily rates"):
        cash.load_risk_free_daily(tmp_path)


def test_tampered_factors_file_in_configured_research_store_is_refused(tmp_path, monkeypatch):
    store = tmp_path / "data" / "frozen"
    store.mkdir(parents=True)
    path = store / cash.FACTORS_PARQUET
    index = pd.bdate_range("2020-01-01", periods=10)
    levels(index).to_parquet(path)
    pinned = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(cash, "ROOT", tmp_path)
    monkeypatch.setattr(
        cash,
        "load_config",
        lambda: {"data": {"store": "data/frozen", "risk_free_sha256": pinned}},
    )
    assert len(cash.load_risk_free_daily(store)) == 9
    levels(index, daily_rate=0.0003).to_parquet(path)
    with pytest.raises(ValueError, match="risk-free file hash mismatch"):
        cash.load_risk_free_daily(store)


def test_alignment_on_an_identical_calendar_is_a_no_op():
    index = pd.bdate_range("2020-01-01", periods=300)
    rf = pd.Series(0.0002, index=index)
    aligned, prov = cash.align_risk_free(rf, index)
    assert np.allclose(aligned.to_numpy(), 0.0002)
    assert prov["n_carried_forward"] == 0
    assert prov["n_before_source_zeroed"] == 0
    assert prov["mean_annualized"] == pytest.approx(0.0002 * 252)


def test_trailing_bars_are_carried_forward_and_counted():
    source = pd.bdate_range("2020-01-01", periods=200)
    target = pd.bdate_range("2020-01-01", periods=230)
    rf = pd.Series(0.0002, index=source)
    aligned, prov = cash.align_risk_free(rf, target)
    assert prov["n_carried_forward"] == 30
    assert np.allclose(aligned.to_numpy(), 0.0002)   # carried, not zeroed


def test_too_many_stale_bars_is_an_error_not_a_footnote():
    source = pd.bdate_range("2020-01-01", periods=200)
    target = pd.bdate_range("2020-01-01", periods=400)
    with pytest.raises(ValueError, match="over the .* limit"):
        cash.align_risk_free(pd.Series(0.0002, index=source), target)


def test_bars_before_the_source_earn_nothing():
    """There is no rate to carry backward, and inventing one would be worse
    than a zero."""
    source = pd.bdate_range("2020-06-01", periods=200)
    target = pd.bdate_range("2020-01-01", periods=350)
    aligned, prov = cash.align_risk_free(pd.Series(0.0002, index=source), target)
    assert prov["n_before_source_zeroed"] > 0
    assert aligned.loc[:"2020-05-29"].eq(0.0).all()
    assert aligned.loc["2020-06-01":].gt(0.0).all()


def test_provenance_records_what_a_report_must_disclose():
    source = pd.bdate_range("2020-01-01", periods=200)
    target = pd.bdate_range("2020-01-01", periods=210)
    _, prov = cash.align_risk_free(pd.Series(0.0002, index=source), target)
    assert set(prov) == {
        "source_first", "source_last", "calendar_first", "calendar_last",
        "n_bars", "n_carried_forward", "n_before_source_zeroed", "mean_annualized",
    }
    assert prov["n_bars"] == 210
