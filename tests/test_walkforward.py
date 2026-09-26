"""Walk-forward runner behaviour, on synthetic data only (DESIGN.md §7).

No real-data run happens here. These tests pin the properties that make the
runner's output evidence rather than decoration: every trial logged, the
embargo enforced, selection blind to the validate window, and seam rebalances
actually paid for.
"""

import numpy as np
import pandas as pd
import pytest

from woodland import backtest, metrics
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward, with_baselines


def synth_prices(n_years=18, seed=2, tickers=("SPY", "AAA", "IEF")):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2000-01-03", periods=252 * n_years)
    mus = {"SPY": 0.0004, "AAA": 0.0005, "IEF": 0.00012}
    return pd.DataFrame(
        {t: 100 * np.cumprod(1 + rng.normal(mus.get(t, 0.0003), 0.01, len(idx))) for t in tickers},
        index=idx,
    )


def sma_targets(prices, config):
    """Toy causal signal: hold AAA when above its N-day SMA, else IEF."""
    n = config["lookback_days"]
    ma = prices["AAA"].rolling(n).mean()
    on = prices["AAA"] > ma
    reb = prices.index[::21]
    tgt = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for d in reb:
        if pd.isna(ma.loc[d]):
            continue
        tgt.loc[d, "AAA"] = 1.0 if on.loc[d] else 0.0
        tgt.loc[d, "IEF"] = 0.0 if on.loc[d] else 1.0
        tgt.loc[d, "SPY"] = 0.0
    return tgt


GRID = [{"lookback_days": n} for n in (20, 50, 100, 150, 200)]
LOOKBACK = 200


@pytest.fixture
def setup(tmp_path):
    prices = synth_prices()
    s = sp.make_splits(prices.index, train_years=5, validate_years=1,
                       step_years=1, embargo_days=210)
    led = TrialsLedger(tmp_path / "trials.db")
    return prices, s, led


def run(setup, **kw):
    prices, s, led = setup
    return prices, led, run_walkforward(
        prices, sma_targets, GRID, splits=s, ledger=led, study="toy",
        max_lookback_days=LOOKBACK, **kw)


# ---------------------------------------------------------------- accounting

def test_every_config_on_every_split_reaches_the_ledger(setup):
    prices, led, res = run(setup)
    n_splits = len([s for s in res.splits if len(s.validate_index(prices.index))])
    assert res.n_trial_rows == len(GRID) * n_splits
    assert res.n_trials == len(GRID)          # distinct configs
    assert len(res.trial_sharpes) == len(GRID)


def test_deflation_uses_the_ledger_count_not_one(setup):
    _, _, res = run(setup)
    d = res.deflated(cost_bps=5.0)
    assert d["n_trials"] == len(GRID)
    assert d["sr0_annual"] > 0, "with >1 trial there must be a selection hurdle"
    assert d["dsr"] <= d["psr_vs_zero"], "deflation can only reduce confidence"


def test_errored_configs_are_logged_not_silently_dropped(setup):
    prices, s, led = setup

    def flaky(prices, config):
        if config["lookback_days"] == 50:
            raise RuntimeError("synthetic failure")
        return sma_targets(prices, config)

    res = run_walkforward(prices, flaky, GRID, splits=s, ledger=led, study="toy",
                          max_lookback_days=LOOKBACK)
    rows = led.trials("toy")
    errs = rows[rows["status"] == "error"]
    assert len(errs) == 1
    assert "synthetic failure" in errs.iloc[0]["notes"]
    assert res.n_trials == len(GRID), "the failed config still counts as a trial"


# ---------------------------------------------------------------- leakage

def test_embargo_is_enforced_before_any_window_is_touched(setup):
    prices, s, led = setup
    with pytest.raises(ValueError, match="embargo too short"):
        run_walkforward(prices, sma_targets, GRID, splits=s, ledger=led, study="toy",
                        max_lookback_days=500)          # longer than the 210-bar embargo
    assert led.n_trials("toy") == 0, "nothing may be evaluated once the check fails"


def test_selection_cannot_see_the_validate_window(setup):
    """Perturb prices AFTER a split's train window: the config chosen for that
    split must not change."""
    prices, s, led = setup
    _, _, base = run((prices, s, led))

    bumped = prices.copy()
    cut = base.splits[2].train_end
    bumped.loc[cut:] *= 1.4

    led2 = TrialsLedger(led.path.parent / "t2.db")
    pert = run_walkforward(bumped, sma_targets, GRID, splits=s, ledger=led2,
                           study="toy", max_lookback_days=LOOKBACK)
    assert base.selections.loc[0, "config"] == pert.selections.loc[0, "config"]
    assert base.selections.loc[1, "config"] == pert.selections.loc[1, "config"]
    assert base.selections.loc[0, "train_score"] == pytest.approx(
        pert.selections.loc[0, "train_score"])


def test_oos_window_starts_at_the_first_validate_bar(setup):
    prices, _, res = run(setup)
    first_v = res.splits[0].validate_index(prices.index)[0]
    assert res.oos_start == first_v
    assert res.oos_returns[5.0].index[0] == first_v
    assert res.oos_returns[5.0].index[-1] == res.oos_end


# ---------------------------------------------------------------- stitching

def test_stitched_curve_pays_for_seam_rebalances(setup):
    """Costs must bite: a higher cost scenario must produce a lower curve, and
    turnover must be non-zero at config switches."""
    _, _, res = run(setup)
    assert res.oos_turnover[5.0].sum() > 0
    eq = {c: float((1 + r).prod()) for c, r in res.oos_returns.items()}
    assert eq[0.0] > eq[5.0] > eq[10.0]


def test_summary_reports_all_three_cost_scenarios(setup):
    _, _, res = run(setup)
    s = res.summary()
    assert list(s.index) == ["OOS @0bps", "OOS @5bps", "OOS @10bps"]
    assert {"cagr", "sharpe_rf0", "max_drawdown", "ann_turnover"} <= set(s.columns)


def test_baselines_are_measured_over_the_same_window(setup):
    prices, _, res = run(setup)
    table = with_baselines(prices, res)
    assert "SPY buy&hold" in table.index
    assert "60/40 @10bps" in table.index
    spy_oos = backtest.buy_and_hold(prices, "SPY", cost_bps=0.0).returns.loc[
        res.oos_start:res.oos_end]
    assert table.loc["SPY buy&hold", "cagr"] == pytest.approx(metrics.cagr(spy_oos))


def test_subperiod_breakdown_available(setup):
    _, _, res = run(setup)
    assert len(res.by_subperiod(5.0)) >= 2


# ---------------------------------------------------------------- guards

def test_empty_grid_and_no_splits_rejected(setup):
    prices, s, led = setup
    with pytest.raises(ValueError, match="empty configuration grid"):
        run_walkforward(prices, sma_targets, [], splits=s, ledger=led,
                        study="toy", max_lookback_days=LOOKBACK)
    with pytest.raises(ValueError, match="no splits"):
        run_walkforward(prices, sma_targets, GRID, splits=[], ledger=led,
                        study="toy", max_lookback_days=LOOKBACK)


def test_all_configs_failing_raises(setup):
    prices, s, led = setup
    def broken(prices, config):
        raise RuntimeError("nope")
    with pytest.raises(RuntimeError, match="every configuration"):
        run_walkforward(prices, broken, GRID, splits=s, ledger=led,
                        study="toy", max_lookback_days=LOOKBACK)
    assert led.n_trials("toy") == len(GRID), "failures still count as trials"
