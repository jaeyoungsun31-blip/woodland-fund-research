"""Shared study scaffolding.

The constants here were previously copied across ten scripts. These tests pin
the values, pin the single-source-of-truth relationships, and pin the one
distinction that copying had blurred: two different windows that were both
called VOL_WINDOW.
"""

import numpy as np
import pandas as pd
import pytest

from woodland import pipeline, study
from woodland.harness import splits as sp

# ---------------------------------------------------------------- constants

def test_frozen_scheme_matches_the_journalled_values():
    assert (study.TRAIN_YEARS, study.VALIDATE_YEARS, study.STEP_YEARS) == (5, 1, 1)
    assert study.MAX_LOOKBACK_DAYS == 210
    assert study.XSMOM_EMBARGO_DAYS == 252
    assert study.LOOKBACKS == [4, 5, 6, 7, 8, 9, 10]
    assert study.COSTS == (0.0, 5.0, 10.0)
    assert study.PRIMARY_COST == 5.0


def test_universes_match_the_journalled_membership():
    assert study.SECTORS == ["XLB", "XLE", "XLF", "XLI", "XLK",
                             "XLP", "XLU", "XLV", "XLY"]  # noqa: SIM300
    assert study.MULTI_ASSET == ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"]
    assert [*study.MULTI_ASSET, "DBC"] == study.MULTI_ASSET_DBC
    assert len(study.DEEP_INDUSTRIES) == 12
    assert study.ETF_RISK_OFF == "IEF" and study.DEEP_RISK_OFF == "CASH"


def test_pipeline_constants_are_re_exported_not_restated():
    """One number, one home. If pipeline changes, study must follow — so these
    must be the same object, not two copies that happen to agree today."""
    assert study.VOL_TARGET_WINDOW == pipeline.REALIZED_VOL_WINDOW
    assert study.VOL_TARGET_ANN == pipeline.TARGET_ANN_VOL
    assert study.RISK_COV_WINDOW == pipeline.SIZING_WINDOW
    assert list(pipeline.DEFAULT_LOOKBACKS) == study.LOOKBACKS


def test_the_two_windows_that_were_both_called_vol_window_are_distinct():
    """63 bars scales exposure; 126 bars estimates a covariance. Different
    scripts spelled both VOL_WINDOW with different values."""
    assert study.VOL_TARGET_WINDOW == 63
    assert study.RISK_COV_WINDOW == 126
    assert study.VOL_TARGET_WINDOW != study.RISK_COV_WINDOW


# ---------------------------------------------------------------- stitching

def _toy():
    index = pd.bdate_range("2000-01-03", periods=2600)
    prices = pd.DataFrame({t: 100.0 + np.arange(len(index)) * 0.01
                           for t in ("AAA", "BBB")}, index=index)
    folds = sp.make_splits(index, train_years=5, validate_years=1,
                           step_years=1, embargo_days=210)
    return prices, folds


def test_stitch_keeps_only_validate_window_rows():
    prices, folds = _toy()
    targets = pd.DataFrame(0.5, index=prices.index, columns=prices.columns)
    stitched = study.stitch(prices, targets, folds)

    kept = stitched.dropna(how="all").index
    covered = pd.DatetimeIndex(sorted(
        set().union(*[set(f.validate_index(prices.index)) for f in folds])))
    assert list(kept) == list(covered)
    assert stitched.loc[prices.index[0]].isna().all()   # pre-OOS row untouched


def test_stitch_preserves_values_and_leaves_gaps_as_nan():
    prices, folds = _toy()
    targets = pd.DataFrame(float("nan"), index=prices.index, columns=prices.columns)
    inside = folds[0].validate_index(pd.DatetimeIndex(prices.index))[5]
    targets.loc[inside] = [0.3, 0.7]
    stitched = study.stitch(prices, targets, folds)
    assert stitched.loc[inside].tolist() == [0.3, 0.7]
    assert stitched.dropna(how="all").index.tolist() == [inside]


def test_oos_window_reports_first_last_and_count():
    prices, folds = _toy()
    index = pd.DatetimeIndex(prices.index)
    lo, hi, n = study.oos_window(index, folds)
    windows = [f.validate_index(index) for f in folds]
    assert lo == windows[0][0]
    assert hi == windows[-1][-1]
    assert n == sum(len(w) for w in windows)


def test_oos_window_rejects_an_empty_scheme():
    prices, _ = _toy()
    with pytest.raises(ValueError, match="no validate window"):
        study.oos_window(pd.DatetimeIndex(prices.index), [])


def test_make_folds_enforces_the_embargo():
    prices, _ = _toy()
    index = pd.DatetimeIndex(prices.index)
    folds = study.make_folds(index)
    assert all(len(f.embargo_index(index)) == study.MAX_LOOKBACK_DAYS for f in folds)
    with pytest.raises(ValueError, match="embargo too short"):
        study.make_folds(index, embargo_days=5)


# ---------------------------------------------------------------- realisation

def test_check_realisation_fails_on_a_changed_shape():
    """The guard that makes a moved window a loud failure rather than a
    quietly different number."""
    bad = study.StudyContext(
        name="etf", prices=pd.DataFrame(), folds=[],
        lo=pd.Timestamp("2004-10-22"), hi=pd.Timestamp("2026-09-01"),
        risk_free=None, n_bars=1,
    )
    with pytest.raises(ValueError, match="journalled"):
        study.check_realisation(bad)


def test_check_realisation_ignores_an_unknown_universe():
    other = study.StudyContext("scratch", pd.DataFrame(), [],
                               pd.Timestamp("2020-01-01"), pd.Timestamp("2020-12-31"),
                               None, 10)
    study.check_realisation(other)          # must not raise


def _require_study_data(name):
    """Skip when the gitignored research data is absent (e.g. a fresh clone)."""
    path = study.data_store() if name == "etf" else (
        study.ROOT / "data/fama_french_12_industry_daily.parquet")
    if not path.exists():
        pytest.skip(f"gitignored {name} research data {path.name} is absent")


@pytest.mark.parametrize("name", ["etf", "deep"])
def test_real_universes_realise_their_journalled_shape(name):
    """Integration: the frozen scheme still produces the window every journal
    entry was computed on."""
    _require_study_data(name)
    context = study.etf_context() if name == "etf" else study.deep_context()
    study.check_realisation(context)
    expected_bars = (study.ETF_EXPECTED_BARS if name == "etf"
                     else study.DEEP_EXPECTED_BARS)
    assert context.n_bars == expected_bars
    assert context.index.is_monotonic_increasing


def test_etf_context_carries_a_risk_free_series_and_deep_does_not():
    _require_study_data("etf")
    _require_study_data("deep")
    etf = study.etf_context()
    assert etf.risk_free is not None
    assert len(etf.risk_free) == len(etf.prices)
    # the deep universe carries CASH as an explicit asset instead
    deep = study.deep_context()
    assert deep.risk_free is None
    assert study.DEEP_RISK_OFF in deep.prices.columns
