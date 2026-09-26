from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from woodland import tailrisk


def test_tail_metrics_match_empirical_definitions() -> None:
    returns = pd.Series([-0.10, -0.04, -0.01, 0.02, 0.03, 0.05])
    assert tailrisk.expected_shortfall(returns, 0.95) == pytest.approx(0.10)
    assert tailrisk.omega(returns) == pytest.approx(0.10 / 0.15)
    assert np.isfinite(tailrisk.sortino(returns))
    assert np.isfinite(tailrisk.tail_ratio(returns))
    assert np.isfinite(tailrisk.adjusted_sharpe(returns))


def test_drawdown_durations_include_completed_and_terminal_spells() -> None:
    returns = pd.Series([0.10, -0.05, 0.06, 0.02, -0.10, 0.01, 0.01])
    assert tailrisk.drawdown_durations(returns).tolist() == [1, 3]


def test_bootstrap_intervals_are_deterministic() -> None:
    rng = np.random.default_rng(9)
    returns = pd.Series(rng.normal(0.0004, 0.01, 120))
    first = tailrisk.bootstrap_intervals(returns, n_resamples=20, seed=4)
    second = tailrisk.bootstrap_intervals(returns, n_resamples=20, seed=4)
    pd.testing.assert_frame_equal(first, second)


def test_vectorized_bootstrap_summaries_match_scalar_calculation() -> None:
    rng = np.random.default_rng(11)
    samples = rng.normal(0.0003, 0.012, size=(4, 180))
    vectorized = tailrisk._summarize_samples(samples)
    scalar = np.vstack([tailrisk._summarize_array(row) for row in samples])
    np.testing.assert_allclose(vectorized, scalar, rtol=1e-11, atol=1e-12)
