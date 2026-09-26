"""Focused construction tests for the pre-registered v7 sleeve study."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from scripts import run_trend_sleeve as sleeve


def _targets(rows: list[list[float]]) -> pd.DataFrame:
    index = pd.date_range("2020-01-01", periods=len(rows), freq="D")
    return pd.DataFrame(rows, index=index, columns=["A", "B"])


def test_blend_targets_uses_union_decisions_and_preserves_residual_cash() -> None:
    base = _targets([[0.6, 0.4], [np.nan, np.nan], [0.6, 0.4]])
    strategy = _targets([[np.nan, np.nan], [0.5, 0.0], [0.0, 0.0]])

    actual = sleeve.blend_targets(base, strategy, 0.2)

    assert actual.iloc[0].tolist() == pytest.approx([0.48, 0.32])
    assert actual.iloc[1].tolist() == pytest.approx([0.10, 0.00])
    assert actual.iloc[2].tolist() == pytest.approx([0.48, 0.32])
    assert bool((actual.sum(axis=1) <= 1.0).all())


def test_monthly_static_targets_leaves_unavailable_asset_in_cash() -> None:
    index = pd.bdate_range("2020-01-01", "2020-02-28")
    prices = pd.DataFrame(
        {
            "A": np.linspace(100.0, 110.0, len(index)),
            "B": [np.nan] * 23 + list(np.linspace(50.0, 55.0, len(index) - 23)),
        },
        index=index,
    )

    targets = sleeve.monthly_static_targets(prices, {"A": 0.5, "B": 0.5}).dropna()

    assert targets.iloc[0].tolist() == pytest.approx([0.5, 0.0])
    assert targets.iloc[-1].tolist() == pytest.approx([0.5, 0.5])


def test_match_volatility_scales_more_volatile_excess_returns_only() -> None:
    index = pd.bdate_range("2020-01-01", periods=100)
    rf = pd.Series(0.0001, index=index)
    pattern = np.tile(np.array([-0.01, 0.01]), 50)
    volatile = pd.Series(rf.to_numpy() + 2.0 * pattern, index=index)
    quiet = pd.Series(rf.to_numpy() + pattern, index=index)

    matched = sleeve.match_volatility(
        volatile, quiet, rf, name_a="volatile", name_b="quiet"
    )

    assert matched.scaled_side == "volatile"
    assert matched.scale == pytest.approx(0.5)
    assert matched.a.equals(quiet)
    assert matched.b.equals(quiet)
    assert matched.matched_vol == pytest.approx(quiet.std(ddof=1) * math.sqrt(252))


def test_frozen_config_accounting_excludes_incumbent() -> None:
    etf = {
        (curve_type, weight)
        for curve_type in sleeve.ETF_CURVE_TYPES
        for weight in sleeve.BLEND_WEIGHTS
    }
    deep = {
        (curve_type, weight)
        for curve_type in sleeve.DEEP_CURVE_TYPES
        for weight in sleeve.BLEND_WEIGHTS
    }

    assert len(etf) == 12
    assert len(deep) == 9
    assert all(weight != 0.0 for _, weight in etf | deep)
    assert "gold" not in sleeve.DEEP_CURVE_TYPES
