"""Lookahead tests: the single most likely way this project fails (DESIGN.md §10).

The perturbation principle: change the FUTURE and nothing in the past may
move. If any position or return before date T changes when prices after T
change, information is leaking backward.
"""

import numpy as np
import pandas as pd
import pytest

from tests.test_backtest import make_prices
from woodland import backtest, xsmom
from woodland.pipeline import DecisionPipeline, PipelineConfig
from woodland.signals import costaware, trend
from woodland.signals.voltarget import vol_target_targets


def test_engine_past_is_invariant_to_future_prices():
    prices = make_prices(n_days=400)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for d in prices.index[::21]:  # rebalance roughly monthly
        targets.loc[d] = [0.6, 0.4]

    base = backtest.run(prices, targets, cost_bps=5.0)

    bumped = prices.copy()
    cut = 300
    bumped.iloc[cut:, :] *= 1.5  # violent future shock

    pert = backtest.run(bumped, targets, cost_bps=5.0)

    pd.testing.assert_series_equal(base.returns.iloc[:cut], pert.returns.iloc[:cut])
    pd.testing.assert_frame_equal(base.holdings.iloc[:cut], pert.holdings.iloc[:cut])


def test_trend_signal_past_is_invariant_to_future_prices():
    """The signal layer must also be leak-free, independently of the engine."""
    prices = make_prices(n_days=900, tickers=("AAA", "BBB", "IEF"))
    kw = dict(risk_assets=["AAA", "BBB"], risk_off="IEF", lookback_months=10)

    base = trend.trend_targets(prices, **kw)

    bumped = prices.copy()
    cut = 700
    bumped.iloc[cut:, :] *= 0.5  # future crash

    pert = trend.trend_targets(bumped, **kw)

    cutoff_date = prices.index[cut]
    pd.testing.assert_frame_equal(base.loc[:cutoff_date].iloc[:-1],
                                  pert.loc[:cutoff_date].iloc[:-1])


def test_trend_signal_decision_uses_only_history():
    """A month-end decision must not depend on that month's FUTURE days.

    Construct prices where the asset is above its SMA at month-end, then
    verify the same decision row appears whether or not later data exists.
    """
    prices = make_prices(n_days=900, tickers=("AAA", "IEF"))
    kw = dict(risk_assets=["AAA"], risk_off="IEF", lookback_months=6)

    full = trend.trend_targets(prices, **kw)
    decision_days = full.dropna(how="all").index

    # re-run with data truncated exactly at each of a few decision days:
    for day in decision_days[8:11]:
        truncated = trend.trend_targets(prices.loc[:day], **kw)
        pd.testing.assert_series_equal(full.loc[day], truncated.loc[day])


def test_trend_ensemble_past_is_invariant_to_future_prices():
    prices = make_prices(n_days=900, tickers=("AAA", "BBB", "IEF"), seed=29)
    cutoff = prices.index[600]
    kwargs = {
        "risk_assets": ["AAA", "BBB"],
        "risk_off": "IEF",
        "lookback_months": list(range(4, 11)),
    }
    original = trend.ensemble_targets(prices, **kwargs)
    shocked = prices.copy()
    shocked.loc[shocked.index > cutoff] *= 7.0
    changed = trend.ensemble_targets(shocked, **kwargs)

    pd.testing.assert_frame_equal(original.loc[:cutoff], changed.loc[:cutoff])


def test_vol_target_past_is_invariant_to_future_prices():
    prices = make_prices(n_days=900, tickers=("AAA", "BBB", "IEF"), seed=37)
    kwargs = {
        "risk_assets": ["AAA", "BBB"],
        "risk_off": "IEF",
        "lookback_months": list(range(4, 11)),
    }
    cutoff = prices.index[650]
    base = trend.ensemble_targets(prices, **kwargs)
    original = vol_target_targets(prices, base, window=63, target_ann_vol=0.10)

    shocked_prices = prices.copy()
    shocked_prices.loc[shocked_prices.index > cutoff] *= 0.2
    shocked_base = trend.ensemble_targets(shocked_prices, **kwargs)
    changed = vol_target_targets(
        shocked_prices, shocked_base, window=63, target_ann_vol=0.10
    )

    pd.testing.assert_frame_equal(original.loc[:cutoff], changed.loc[:cutoff])


# --------------------------------------------------------------- trend-v5

def _v5_prices(n_days=1400, seed=21):
    """Several risky assets with genuinely different volatilities, so the
    risk-weighting schemes produce distinguishable allocations."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n_days)
    sds = {"AAA": 0.008, "BBB": 0.014, "CCC": 0.022, "IEF": 0.003}
    return pd.DataFrame(
        {t: 100 * np.cumprod(1 + rng.normal(0.0004, sd, n_days)) for t, sd in sds.items()},
        index=idx,
    )


@pytest.mark.parametrize("weighting", ["inverse_vol", "min_variance"])
def test_risk_weighted_trend_past_is_invariant_to_future_prices(weighting):
    """Binding rule 2, for the trend-v5 weighting schemes: shock the future,
    assert no decision at or before the cut moves."""
    prices = _v5_prices()
    kw = dict(risk_assets=["AAA", "BBB", "CCC"], risk_off="IEF",
              lookback_months=10, weighting=weighting, vol_window=126)

    base = trend.trend_targets(prices, **kw)

    bumped = prices.copy()
    cut = 1100
    bumped.iloc[cut:, :] *= 0.6            # violent future crash

    pert = trend.trend_targets(bumped, **kw)

    cutoff = prices.index[cut]
    pd.testing.assert_frame_equal(base.loc[:cutoff].iloc[:-1], pert.loc[:cutoff].iloc[:-1])


@pytest.mark.parametrize("weighting", ["inverse_vol", "min_variance"])
def test_risk_weighted_decision_uses_only_history(weighting):
    """Truncating the data exactly at a decision day must not change that
    day's weights — the covariance window cannot be peeking forward."""
    prices = _v5_prices()
    kw = dict(risk_assets=["AAA", "BBB", "CCC"], risk_off="IEF",
              lookback_months=6, weighting=weighting, vol_window=126)

    full = trend.trend_targets(prices, **kw)
    decision_days = full.dropna(how="all").index

    for day in decision_days[10:14]:
        truncated = trend.trend_targets(prices.loc[:day], **kw)
        pd.testing.assert_series_equal(full.loc[day], truncated.loc[day])


@pytest.mark.parametrize("weighting", ["inverse_vol", "min_variance"])
def test_risk_weighted_ensemble_past_is_invariant_to_future_prices(weighting):
    """The v5 study runs the schemes through the ensemble, so the ensemble
    path needs its own perturbation check, not just the single-lookback one."""
    prices = _v5_prices(n_days=1600)
    kw = dict(risk_assets=["AAA", "BBB", "CCC"], risk_off="IEF",
              lookback_months=[4, 6, 8, 10], weighting=weighting, vol_window=126)

    base = trend.ensemble_targets(prices, **kw)
    bumped = prices.copy()
    cut = 1300
    bumped.iloc[cut:, :] *= 1.8
    pert = trend.ensemble_targets(bumped, **kw)

    cutoff = prices.index[cut]
    pd.testing.assert_frame_equal(base.loc[:cutoff].iloc[:-1], pert.loc[:cutoff].iloc[:-1])


def test_risk_weighting_actually_changes_the_allocation():
    """Guard against the perturbation tests passing vacuously: the schemes
    must produce genuinely different weights from equal weighting, or the
    tests above would prove nothing."""
    prices = _v5_prices()
    kw = dict(risk_assets=["AAA", "BBB", "CCC"], risk_off="IEF", lookback_months=10)
    equal = trend.trend_targets(prices, **kw).dropna(how="all")
    for weighting in ("inverse_vol", "min_variance"):
        other = trend.trend_targets(prices, weighting=weighting, vol_window=126,
                                    **kw).dropna(how="all")
        common = equal.index.intersection(other.index)
        assert len(common) > 10
        assert not equal.loc[common].equals(other.loc[common])
        # the quietest asset should on average carry more weight than the loudest
        assert other.loc[common, "AAA"].mean() > other.loc[common, "CCC"].mean()


# --------------------------------------------------------------- trend-v6

def _v6_prices(n_days=1500, seed=31):
    """Sleeves with genuinely different behaviour, plus an IEF column so the
    same data can be run with either risk-off convention."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n_days)
    spec = {"SPY": 0.011, "EFA": 0.012, "EEM": 0.015,
            "TLT": 0.009, "IEF": 0.004, "GLD": 0.010}
    return pd.DataFrame(
        {t: 100 * np.cumprod(1 + rng.normal(0.0003, sd, n_days)) for t, sd in spec.items()},
        index=idx,
    )


def test_cash_risk_off_ensemble_past_is_invariant_to_future_prices():
    """Binding rule 2 for the v6 configuration: risk_off=None leaves the
    residual in cash, and no decision at or before the cut may move."""
    prices = _v6_prices()
    kw = dict(risk_assets=["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"],
              risk_off=None, lookback_months=[4, 6, 8, 10])

    base = trend.ensemble_targets(prices, **kw)
    bumped = prices.copy()
    cut = 1200
    bumped.iloc[cut:, :] *= 0.55
    pert = trend.ensemble_targets(bumped, **kw)

    cutoff = prices.index[cut]
    pd.testing.assert_frame_equal(base.loc[:cutoff].iloc[:-1], pert.loc[:cutoff].iloc[:-1])


def test_cash_risk_off_decision_uses_only_history():
    prices = _v6_prices()
    kw = dict(risk_assets=["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"],
              risk_off=None, lookback_months=6)
    full = trend.trend_targets(prices, **kw)
    for day in full.dropna(how="all").index[10:14]:
        truncated = trend.trend_targets(prices.loc[:day], **kw)
        pd.testing.assert_series_equal(full.loc[day], truncated.loc[day])


def test_cash_risk_off_leaves_a_residual_instead_of_buying_a_bond_sleeve():
    """The behavioural difference the v6 universe depends on: with risk_off
    set, the out-of-trend budget buys that asset; with None it stays in cash,
    which the engine pays the risk-free rate on."""
    prices = _v6_prices()
    assets = ["SPY", "EFA", "EEM", "TLT", "GLD"]

    with_ief = trend.trend_targets(prices, risk_assets=assets, risk_off="IEF",
                                   lookback_months=10).dropna(how="all")
    with_cash = trend.trend_targets(prices, risk_assets=assets, risk_off=None,
                                    lookback_months=10).dropna(how="all")

    assert with_ief.sum(axis=1).min() == pytest.approx(1.0)
    assert with_cash["IEF"].abs().max() == 0.0
    # rows where nothing is in trend: IEF version holds the bond, cash version holds nothing
    idle = with_cash.index[with_cash.sum(axis=1) < 1e-12]
    assert len(idle) > 0
    assert np.allclose(with_ief.loc[idle, "IEF"].to_numpy(), 1.0)


def test_unknown_risk_off_ticker_still_rejected():
    prices = _v6_prices()
    with pytest.raises(ValueError, match="not in price matrix"):
        trend.trend_targets(prices, risk_assets=["SPY"], risk_off="NOPE",
                            lookback_months=10)


# ----------------------------------------------------------- pipeline-v14

@pytest.mark.parametrize(
    "config",
    [
        PipelineConfig(regime_filter=True),
        PipelineConfig(sizing="inverse_vol"),
        PipelineConfig(sizing="min_variance"),
        PipelineConfig(exposure="symmetric"),
        PipelineConfig(exposure="asymmetric"),
    ],
)
def test_v14_pipeline_past_is_invariant_to_future_prices(config):
    """Every new v14 signal stage passes the binding perturbation test."""
    prices = _v6_prices(n_days=1800, seed=43)
    assets = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"]
    cutoff_position = 1450
    cutoff = prices.index[cutoff_position]

    original = DecisionPipeline(assets, config).build(prices)
    shocked = prices.copy()
    shocked.iloc[cutoff_position + 1:] *= 0.37
    changed = DecisionPipeline(assets, config).build(shocked)

    pd.testing.assert_frame_equal(
        original.targets.loc[:cutoff], changed.targets.loc[:cutoff]
    )
    assert original.state.features is not None
    assert changed.state.features is not None
    pd.testing.assert_series_equal(
        original.state.features.dispersion.loc[:cutoff],
        changed.state.features.dispersion.loc[:cutoff],
    )


# ----------------------------------------------------------- xsmom-v15

def test_stale_cohort_past_is_invariant_to_future_decile_returns() -> None:
    """The v15 modeled cohort must not let later decile returns move the past."""
    rng = np.random.default_rng(61)
    index = pd.bdate_range("2010-01-04", periods=800)
    deciles = pd.DataFrame(
        rng.normal(0.0003, 0.012, size=(len(index), 10)),
        index=index,
        columns=xsmom.DECILE_COLUMNS,
    )
    dates = xsmom.formation_dates(index, "quarterly")
    original = xsmom.stale_cohort_returns(deciles, dates)

    cutoff_position = 600
    shocked = deciles.copy()
    shocked.iloc[cutoff_position + 1:] *= -9.0
    changed = xsmom.stale_cohort_returns(shocked, dates)

    pd.testing.assert_series_equal(
        original.iloc[: cutoff_position + 1],
        changed.iloc[: cutoff_position + 1],
    )


def test_panel_perturbation_features_coefficients_and_targets_bit_identical():
    rng = np.random.default_rng(17)
    idx = pd.bdate_range("2000-01-01", periods=650)
    r = pd.DataFrame(rng.normal(0.0001, 0.01, (650, 9)), index=idx)
    e = r.notna()
    cut = 520
    changed = r.copy()
    changed.iloc[cut + 1 :] *= 3
    x = costaware.features(r, e)
    z = costaware.features(changed, e)
    np.testing.assert_array_equal(x[: cut + 1], z[: cut + 1])
    y = costaware.labels(r)
    v = costaware.labels(changed)
    # Fit only samples with labels completed by cutoff.
    b = costaware.fit(costaware.sufficient_statistics(x[: cut - 21], y[: cut - 21]), 0.1, 2.0)
    c = costaware.fit(costaware.sufficient_statistics(z[: cut - 21], v[: cut - 21]), 0.1, 2.0)
    np.testing.assert_array_equal(b, c)
    left = costaware.targets(r, x, e, b).iloc[: cut + 1]
    right = costaware.targets(changed, z, e, c).iloc[: cut + 1]
    pd.testing.assert_frame_equal(left, right, check_exact=True)
