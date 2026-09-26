"""Construction tests for the fixed trend-v8 blend curves."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts import run_trend_blend as blend
from woodland import bayes, stats


def _targets(rows: list[list[float]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        index=pd.date_range("2020-01-01", periods=len(rows), freq="D"),
        columns=["A", "B", "C"],
    )


def test_average_targets_equals_portfolio_average_on_union_decisions() -> None:
    first = _targets([[0.6, 0.4, 0.0], [np.nan, np.nan, np.nan]])
    second = _targets([[0.2, 0.3, 0.5], [0.3, 0.0, 0.0]])

    actual = blend.average_targets([first, second])

    assert actual.iloc[0].tolist() == pytest.approx([0.4, 0.35, 0.25])
    assert actual.iloc[1].tolist() == pytest.approx([0.15, 0.0, 0.0])
    assert bool((actual.dropna(how="all").sum(axis=1) <= 1.0).all())


def test_average_targets_rejects_axis_mismatch() -> None:
    first = _targets([[0.6, 0.4, 0.0]])
    second = first.rename(columns={"C": "D"})

    with pytest.raises(ValueError, match="identical axes"):
        blend.average_targets([first, second])


def test_preregistered_mix_and_comparison_counts_are_fixed() -> None:
    assert len(blend.MIX_COMPONENTS) * len(blend.v7.BLEND_WEIGHTS) == 12
    blend_vs_single = (
        len(blend.MIX_COMPONENTS)
        * len(blend.SINGLE_ARMS)
        * len(blend.v7.BLEND_WEIGHTS)
    )
    blend_vs_blend = (
        6 * len(blend.v7.BLEND_WEIGHTS)
    )

    assert blend_vs_single == 36
    assert blend_vs_blend == 18
    assert blend_vs_single + blend_vs_blend == 54


def test_deep_prior_mapping_excludes_every_gold_arm() -> None:
    assert {
        "trend",
        "defensive",
        "trend_defensive",
    } == blend.DEEP_INFORMED_ARMS
    assert all(
        "gold" not in arm for arm in blend.DEEP_INFORMED_ARMS
    )


def test_gold_posterior_rows_mark_deep_prior_unavailable() -> None:
    draws = np.array([0.01, 0.02, 0.03])
    likelihood = bayes.likelihood_from_bootstrap(0.02, draws, block_length=21)
    hac = stats.SharpeComparison(
        name_a="trend_gold:w=0.1",
        name_b="base:w=0.0",
        sharpe_a=0.8,
        sharpe_b=0.78,
        difference=0.02,
        ci_low=-0.01,
        ci_high=0.05,
        p_value=0.2,
        n_obs=100,
        method="synthetic",
    )
    evidence = blend.PairEvidence(
        "trend_gold:w=0.1",
        "base:w=0.0",
        likelihood,
        0.01,
        0.03,
        0.2,
        0.99,
        hac,
    )

    rows = blend.posterior_rows(evidence, deep_prior=None)

    assert [row["prior"] for row in rows] == [
        "skeptical",
        "neutral",
        "deep_informed",
    ]
    assert rows[-1]["lower_loss_action"] == "UNAVAILABLE"
    assert "no vetted" in rows[-1]["comparison_status"]
