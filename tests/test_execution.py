from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.run_trend_execution import (
    ConfigRun,
    bootstrap_surface,
    config_dict,
    execution_grid,
    inference_table,
)
from woodland import backtest, execution, metrics, stats


def _prices(n: int = 40) -> pd.DataFrame:
    index = pd.bdate_range("2020-01-01", periods=n)
    return pd.DataFrame(
        {
            "A": 100.0 * np.cumprod(np.full(n, 1.001)),
            "B": 100.0 * np.cumprod(np.full(n, 0.999)),
        },
        index=index,
    )


def _targets(prices: pd.DataFrame) -> pd.DataFrame:
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[prices.index[0]] = [0.6, 0.4]
    targets.loc[prices.index[10]] = [0.2, 0.8]
    targets.loc[prices.index[20]] = [0.7, 0.3]
    return targets


def test_unbuffered_policy_is_exact_backtest() -> None:
    prices = _prices()
    targets = _targets(prices)
    rf = pd.Series(0.0001, index=prices.index)
    expected = backtest.run(prices, targets, cost_bps=17.0, risk_free=rf)
    actual = execution.run(
        prices,
        targets,
        execution.ExecutionPolicy(),
        cost_bps=17.0,
        risk_free=rf,
    )
    pd.testing.assert_series_equal(actual.returns, expected.returns)
    pd.testing.assert_series_equal(actual.turnover, expected.turnover)
    pd.testing.assert_frame_equal(actual.holdings, expected.holdings)


def test_band_skips_entire_small_instruction() -> None:
    prices = _prices(8)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[prices.index[0]] = [0.5, 0.5]
    targets.loc[prices.index[2]] = [0.51, 0.49]
    result = execution.run(
        prices,
        targets,
        execution.ExecutionPolicy(band=0.025),
        cost_bps=0.0,
    )
    assert result.turnover.iloc[3] == 0.0


def test_partial_adjustment_moves_fraction_from_drifted_weights() -> None:
    prices = pd.DataFrame(
        {"A": [100.0] * 5, "B": [100.0] * 5},
        index=pd.bdate_range("2020-01-01", periods=5),
    )
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[prices.index[0]] = [1.0, 0.0]
    targets.loc[prices.index[2]] = [0.0, 1.0]
    result = execution.run(
        prices,
        targets,
        execution.ExecutionPolicy(adjustment=0.5),
        cost_bps=0.0,
    )
    assert result.holdings.loc[prices.index[1], "A"] == pytest.approx(0.5)
    assert result.holdings.loc[prices.index[3], "A"] == pytest.approx(0.25)
    assert result.holdings.loc[prices.index[3], "B"] == pytest.approx(0.5)


def test_additional_delay_never_executes_early() -> None:
    prices = _prices(8)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[prices.index[0]] = [1.0, 0.0]
    result = execution.run(
        prices,
        targets,
        execution.ExecutionPolicy(delay=2),
        cost_bps=0.0,
    )
    assert result.holdings.iloc[:3].to_numpy().sum() == 0.0
    assert result.holdings.iloc[3, 0] == 1.0


def test_missed_masks_are_reproducible_common_and_nested() -> None:
    prices = _prices(100)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.iloc[::2] = [0.5, 0.5]
    five_a = execution.decision_mask(targets, 0.05, seed=1202)
    five_b = execution.decision_mask(targets, 0.05, seed=1202)
    ten = execution.decision_mask(targets, 0.10, seed=1202)
    pd.testing.assert_series_equal(five_a, five_b)
    assert (five_a <= ten).all()


def test_explicit_missed_mask_is_shared_across_target_subsets() -> None:
    prices = _prices(12)
    full_targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    full_targets.loc[prices.index[[0, 4, 8]]] = [1.0, 0.0]
    sparse_targets = full_targets.copy()
    sparse_targets.loc[prices.index[0]] = np.nan
    shared_mask = pd.Series(False, index=prices.index, dtype=bool)
    shared_mask.loc[prices.index[4]] = True

    policy = execution.ExecutionPolicy(missed_rebalance=0.1)
    full = execution.run(
        prices, full_targets, policy, cost_bps=0.0, missed_mask=shared_mask
    )
    sparse = execution.run(
        prices, sparse_targets, policy, cost_bps=0.0, missed_mask=shared_mask
    )

    assert full.turnover.loc[prices.index[5]] == 0.0
    assert sparse.turnover.loc[prices.index[5]] == 0.0


def test_four_tranches_stagger_first_fill_without_lookahead() -> None:
    prices = _prices(25)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[prices.index[0]] = [1.0, 0.0]
    result = execution.run(
        prices,
        targets,
        execution.ExecutionPolicy(tranches=4),
        cost_bps=0.0,
    )
    assert result.holdings.iloc[0, 0] == 0.0
    assert result.holdings.iloc[1, 0] == pytest.approx(0.25)
    numeric_holdings = result.holdings.to_numpy(dtype=float)
    assert 0.25 < numeric_holdings[6, 0] < 0.51
    assert numeric_holdings[16, 0] > 0.99


def test_future_price_shock_does_not_change_past_execution() -> None:
    prices = _prices(40)
    targets = _targets(prices)
    policy = execution.ExecutionPolicy(
        band=0.025,
        adjustment=0.5,
        tranches=4,
        delay=2,
        missed_rebalance=0.1,
    )
    cutoff = prices.index[24]
    original = execution.run(prices, targets, policy, cost_bps=10.0)
    shocked = prices.copy()
    shocked.loc[shocked.index > cutoff, "A"] *= 3.0
    changed = execution.run(shocked, targets, policy, cost_bps=10.0)
    pd.testing.assert_series_equal(
        original.returns.loc[:cutoff], changed.returns.loc[:cutoff]
    )
    pd.testing.assert_frame_equal(
        original.holdings.loc[:cutoff], changed.holdings.loc[:cutoff]
    )


def test_cost_crossover_interpolates_first_positive_crossing() -> None:
    assert execution.cost_crossover([0, 10, 25], [-0.02, -0.01, 0.02]) == pytest.approx(15.0)
    assert execution.cost_crossover([0, 10], [0.01, 0.02]) == 0.0
    assert execution.cost_crossover([0, 10], [-0.01, -0.001]) is None


def test_maximum_viable_turnover_matches_known_constant_spread() -> None:
    index = pd.bdate_range("2020-01-01", periods=80)
    benchmark = pd.Series(np.tile([-0.01, 0.01], 40), index=index)
    strategy = benchmark + 0.0001
    viable = execution.maximum_viable_turnover(strategy, benchmark, cost_bps=10.0)
    assert viable is not None
    assert viable == pytest.approx(25.2)
    assert execution.net_sharpe_at_turnover(
        strategy, viable, cost_bps=10.0
    ) == pytest.approx(metrics.sharpe(benchmark))


def test_maximum_viable_turnover_is_none_when_gross_already_trails() -> None:
    index = pd.bdate_range("2020-01-01", periods=80)
    benchmark = pd.Series(np.tile([-0.01, 0.01], 40), index=index)
    strategy = benchmark - 0.0001
    assert execution.maximum_viable_turnover(strategy, benchmark, 10.0) is None


def test_preregistered_execution_grid_has_216_unique_configurations() -> None:
    grid = execution_grid()
    configs = {tuple(sorted(config_dict(policy).items())) for policy in grid}
    assert len(grid) == 216
    assert len(configs) == 216


def test_batched_bootstrap_matches_existing_pairwise_implementation() -> None:
    rng = np.random.default_rng(42)
    index = pd.bdate_range("2020-01-01", periods=80)
    reference = pd.Series(rng.normal(0.0002, 0.01, len(index)), index=index)
    candidates = [
        reference + pd.Series(rng.normal(0.0001, 0.002, len(index)), index=index),
        reference + pd.Series(rng.normal(-0.0001, 0.003, len(index)), index=index),
    ]
    actual = bootstrap_surface(candidates, reference, n_resamples=200)

    for position, candidate in enumerate(candidates):
        expected = stats.bootstrap_sharpe_difference(
            candidate, reference, n_resamples=200, seed=0
        )
        assert actual.loc[position, "delta_sharpe"] == pytest.approx(
            expected.difference
        )
        assert actual.loc[position, "bootstrap_ci_low"] == pytest.approx(
            expected.ci_low
        )
        assert actual.loc[position, "bootstrap_ci_high"] == pytest.approx(
            expected.ci_high
        )
        assert actual.loc[position, "bootstrap_p"] == pytest.approx(expected.p_value)


def test_inference_reference_row_is_exactly_defined() -> None:
    index = pd.bdate_range("2020-01-01", periods=40)
    returns = pd.Series(
        np.random.default_rng(5).normal(0.0002, 0.01, len(index)), index=index
    )
    turnover = pd.Series(0.0, index=index)
    run = ConfigRun(
        config={},
        policy=execution.ExecutionPolicy(seed=1202),
        returns_10=returns,
        turnover_10=turnover,
        metrics_10={},
        train_metrics=[],
    )
    result = inference_table([run], returns, n_resamples=20)
    assert result.loc[0, "delta_sharpe"] == 0.0
    assert result.loc[0, "bootstrap_ci_low"] == 0.0
    assert result.loc[0, "bootstrap_ci_high"] == 0.0
    assert result.loc[0, "bootstrap_p"] == 1.0
