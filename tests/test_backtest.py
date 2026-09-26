"""Known-answer correctness tests for the backtest engine (DESIGN.md §6).

Every test here is a claim the engine must reproduce EXACTLY (to float
precision) on synthetic data where the right answer is computable by hand.
"""

import numpy as np
import pandas as pd
import pytest

from woodland import backtest


def make_prices(n_days=300, tickers=("AAA", "BBB"), seed=7, start="2020-01-01"):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, periods=n_days)
    data = {t: 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n_days)) for t in tickers}
    return pd.DataFrame(data, index=idx)


def sparse_targets(prices):
    return pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)


# ---------------------------------------------------------------- exactness

def test_buy_and_hold_matches_asset_return_exactly():
    """Weight 1.0 in one asset, zero cost: equity must equal the asset's
    cumulative return from the execution bar onward."""
    prices = make_prices()
    res = backtest.buy_and_hold(prices, "AAA", cost_bps=0.0)
    # instruction on day0 close -> executed day1 close -> returns accrue from day2
    expected = prices["AAA"].iloc[-1] / prices["AAA"].iloc[1]
    assert res.equity.iloc[-1] == pytest.approx(expected, rel=1e-12)


def test_daily_rebalanced_5050_matches_analytic():
    """Daily-rebalanced 50/50 at zero cost: portfolio daily return must be
    the mean of the two asset returns, every day after execution."""
    prices = make_prices()
    targets = sparse_targets(prices)
    targets.iloc[:, :] = 0.5  # instruction every day
    res = backtest.run(prices, targets, cost_bps=0.0)
    r = prices.pct_change()
    expected = 0.5 * r["AAA"] + 0.5 * r["BBB"]
    # first executed bar is day1 (day0 instruction shifted); day1 return is
    # earned by the pre-trade (empty) portfolio, so comparison starts day2
    got = res.returns.iloc[2:]
    want = expected.iloc[2:]
    assert np.allclose(got.to_numpy(), want.to_numpy(), atol=1e-14)


def test_single_rebalance_cost_charged_exactly_once():
    """Going 0 -> 100% in one asset at 10bps must cost exactly 10bps of equity."""
    prices = make_prices()
    t_free = sparse_targets(prices)
    t_free.loc[prices.index[0], "AAA"] = 1.0
    t_cost = t_free.copy()
    free = backtest.run(prices, t_free, cost_bps=0.0)
    paid = backtest.run(prices, t_cost, cost_bps=10.0)
    ratio = paid.equity.iloc[-1] / free.equity.iloc[-1]
    assert ratio == pytest.approx(1 - 10 / 1e4, rel=1e-12)
    assert paid.turnover.sum() == pytest.approx(1.0)


def test_drift_turnover_hand_computed():
    """Two-day example with hand-computed drifted weights and turnover."""
    idx = pd.bdate_range("2020-01-01", periods=4)
    prices = pd.DataFrame({"AAA": [100, 100, 110, 110],
                           "BBB": [100, 100, 100, 100]}, index=idx, dtype=float)
    targets = pd.DataFrame(np.nan, index=idx, columns=prices.columns)
    targets.loc[idx[0]] = [0.5, 0.5]   # executed day1
    targets.loc[idx[2]] = [0.5, 0.5]   # executed day3: rebalance back after drift
    res = backtest.run(prices, targets, cost_bps=0.0)
    # day2: AAA +10%, port return = 0.05; drifted w_AAA = 0.5*1.1/1.05
    assert res.returns.iloc[2] == pytest.approx(0.05)
    drifted = 0.5 * 1.1 / 1.05
    assert res.holdings.iloc[2]["AAA"] == pytest.approx(drifted)
    # day3: rebalance to 0.5/0.5 -> turnover = 2*(drifted-0.5)
    assert res.turnover.iloc[3] == pytest.approx(2 * (drifted - 0.5))


def test_cash_earns_zero():
    """50% invested, 50% cash: portfolio return must be half the asset return."""
    prices = make_prices(tickers=("AAA",))
    targets = sparse_targets(prices)
    targets.iloc[:, 0] = 0.5
    res = backtest.run(prices, targets, cost_bps=0.0)
    r = prices["AAA"].pct_change()
    assert np.allclose(res.returns.iloc[2:].to_numpy(), (0.5 * r).iloc[2:].to_numpy(), atol=1e-14)


# ---------------------------------------------------------------- guardrails

def test_leverage_rejected():
    prices = make_prices()
    targets = sparse_targets(prices)
    targets.loc[prices.index[0]] = [0.8, 0.5]
    with pytest.raises(ValueError, match="leverage"):
        backtest.run(prices, targets)


def test_shorts_rejected():
    prices = make_prices()
    targets = sparse_targets(prices)
    targets.loc[prices.index[0]] = [1.2, -0.2]
    with pytest.raises(ValueError, match="long-only"):
        backtest.run(prices, targets)


def test_weight_on_missing_price_rejected():
    prices = make_prices()
    prices.loc[prices.index[:50], "BBB"] = np.nan  # BBB doesn't exist yet
    targets = sparse_targets(prices)
    targets.loc[prices.index[10], "BBB"] = 1.0
    with pytest.raises(ValueError, match="missing-price"):
        backtest.run(prices, targets)


# ---------------------------------------------------------------- cash realism

def constant_rf(index, annual_rate):
    """A constant daily risk-free series over a calendar."""
    return pd.Series(annual_rate / 252.0, index=index, name="risk_free")


def test_zero_rate_reproduces_the_old_engine_exactly():
    """Regression guard for the journalled record: passing no risk-free series,
    or an all-zero one, must give bit-identical results to the pre-cash engine.
    Every number in journal/ was computed under this path."""
    prices = make_prices(n_days=500)
    targets = sparse_targets(prices)
    for d in prices.index[::21]:
        targets.loc[d] = [0.3, 0.2]        # deliberately only 50% invested

    baseline = backtest.run(prices, targets, cost_bps=5.0)
    explicit_zero = backtest.run(prices, targets, cost_bps=5.0,
                                 risk_free=constant_rf(prices.index, 0.0))

    pd.testing.assert_series_equal(baseline.returns, explicit_zero.returns)
    pd.testing.assert_frame_equal(baseline.holdings, explicit_zero.holdings)
    assert baseline.equity.iloc[-1] == explicit_zero.equity.iloc[-1]


def test_all_cash_compounds_at_the_risk_free_rate():
    """Known answer: holding no assets at a constant rate must compound to
    exactly (1 + daily)^(n-1) — n-1 because the first bar earns nothing, the
    same convention asset returns follow."""
    prices = make_prices(n_days=253)
    empty = sparse_targets(prices)                    # never invested
    annual = 0.05
    res = backtest.run(prices, empty, cost_bps=0.0,
                       risk_free=constant_rf(prices.index, annual))

    daily = annual / 252.0
    expected = (1.0 + daily) ** (len(prices) - 1)
    assert res.equity.iloc[-1] == pytest.approx(expected, rel=1e-12)
    assert res.returns.iloc[0] == 0.0
    assert res.returns.iloc[1] == pytest.approx(daily)
    assert res.holdings.to_numpy().sum() == pytest.approx(0.0)


def test_half_invested_earns_half_the_asset_and_half_the_rate():
    prices = make_prices(n_days=400, tickers=("AAA",))
    targets = sparse_targets(prices)
    targets.iloc[:, 0] = 0.5                          # 50% AAA, 50% cash daily
    annual = 0.04
    res = backtest.run(prices, targets, cost_bps=0.0,
                       risk_free=constant_rf(prices.index, annual))

    asset = prices["AAA"].pct_change()
    expected = 0.5 * asset + 0.5 * (annual / 252.0)
    assert np.allclose(res.returns.iloc[2:].to_numpy(),
                       expected.iloc[2:].to_numpy(), atol=1e-14)


def test_fully_invested_portfolio_is_unaffected_by_the_rate():
    """The change must move only strategies that actually hold cash — this is
    why v2 and 60/40 are untouched while v3 is not."""
    prices = make_prices(n_days=400)
    targets = sparse_targets(prices)
    for d in prices.index[::21]:
        targets.loc[d] = [0.5, 0.5]                   # always 100% invested

    flat = backtest.run(prices, targets, cost_bps=0.0)
    with_rate = backtest.run(prices, targets, cost_bps=0.0,
                             risk_free=constant_rf(prices.index, 0.05))

    # Bar 1 is the exception and it is correct: the day-0 instruction executes
    # at bar 1's CLOSE, so the portfolio holds cash through that whole bar and
    # rightly earns the rate on it. From bar 2 the portfolio is fully invested
    # and the rate cannot touch it.
    assert with_rate.returns.iloc[1] == pytest.approx(0.05 / 252)
    assert flat.returns.iloc[1] == 0.0
    pd.testing.assert_series_equal(flat.returns.iloc[2:], with_rate.returns.iloc[2:])


def test_a_positive_rate_helps_a_cash_holding_strategy():
    prices = make_prices(n_days=600)
    targets = sparse_targets(prices)
    for d in prices.index[::21]:
        targets.loc[d] = [0.25, 0.25]                 # half in cash
    flat = backtest.run(prices, targets, cost_bps=0.0)
    paid = backtest.run(prices, targets, cost_bps=0.0,
                        risk_free=constant_rf(prices.index, 0.05))
    assert paid.equity.iloc[-1] > flat.equity.iloc[-1]


def test_cash_weight_drifts_correctly_against_a_rising_asset():
    """Hand-computed: 50/50 asset/cash, asset +10%, rate 0 for clarity of the
    arithmetic, then the same with a rate to show cash keeps its share."""
    idx = pd.bdate_range("2020-01-01", periods=3)
    prices = pd.DataFrame({"AAA": [100.0, 100.0, 110.0]}, index=idx)
    targets = pd.DataFrame(np.nan, index=idx, columns=prices.columns)
    targets.loc[idx[0]] = [0.5]                       # executed on day 1

    daily = 0.001
    res = backtest.run(prices, targets, cost_bps=0.0,
                       risk_free=pd.Series(daily, index=idx))
    # day 2: asset +10% on half, cash +0.1% on half
    assert res.returns.iloc[2] == pytest.approx(0.5 * 0.10 + 0.5 * daily)
    growth = 1.0 + 0.5 * 0.10 + 0.5 * daily
    assert res.holdings.iloc[2]["AAA"] == pytest.approx(0.5 * 1.10 / growth)


def test_risk_free_must_cover_every_price_date():
    prices = make_prices(n_days=300)
    short = constant_rf(prices.index[:100], 0.03)
    with pytest.raises(ValueError, match="does not cover"):
        backtest.run(prices, sparse_targets(prices), risk_free=short)


def test_non_finite_risk_free_is_rejected():
    prices = make_prices(n_days=300)
    bad = constant_rf(prices.index, 0.03)
    bad.iloc[50] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        backtest.run(prices, sparse_targets(prices), risk_free=bad)
