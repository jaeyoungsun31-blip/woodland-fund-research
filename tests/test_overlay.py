"""Known-answer tests for maintained baseline/sleeve overlays."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from woodland import overlay


def component_returns() -> tuple[pd.Series, pd.Series]:
    index = pd.bdate_range("2020-01-01", periods=5)
    baseline = pd.Series([0.01, -0.02, 0.03, 0.00, 0.02], index=index)
    sleeve = pd.Series([-0.03, 0.04, 0.01, -0.02, 0.05], index=index)
    return baseline, sleeve


def test_zero_weight_reproduces_baseline_exactly() -> None:
    baseline, sleeve = component_returns()
    result = overlay.mix_returns(
        baseline, sleeve, 0.0, pd.DatetimeIndex(baseline.index[1::2]), cost_bps=50.0
    )
    pd.testing.assert_series_equal(result.returns, baseline.rename("ret"))
    assert result.remix_turnover.sum() == 0.0


def test_full_weight_reproduces_sleeve_exactly() -> None:
    baseline, sleeve = component_returns()
    result = overlay.mix_returns(
        baseline, sleeve, 1.0, pd.DatetimeIndex(baseline.index[1::2]), cost_bps=50.0
    )
    pd.testing.assert_series_equal(result.returns, sleeve.rename("ret"))
    assert result.remix_turnover.sum() == 0.0


def test_two_bar_mix_matches_hand_calculation() -> None:
    index = pd.bdate_range("2020-01-01", periods=2)
    baseline = pd.Series([0.10, 0.00], index=index)
    sleeve = pd.Series([0.00, 0.10], index=index)
    result = overlay.mix_returns(
        baseline,
        sleeve,
        0.5,
        pd.DatetimeIndex([index[0]]),
        cost_bps=100.0,
    )

    drifted_baseline = 0.5 * 1.10 / 1.05
    turnover = 2.0 * (drifted_baseline - 0.5)
    expected_first = 1.05 * (1.0 - turnover * 0.01) - 1.0
    assert result.returns.iloc[0] == pytest.approx(expected_first)
    assert result.remix_turnover.iloc[0] == pytest.approx(turnover)
    assert result.returns.iloc[1] == pytest.approx(0.05)
    assert result.equity.iloc[-1] == pytest.approx(
        (1.0 + expected_first) * 1.05
    )


def test_remix_turnover_and_cost_occur_only_on_formation_dates() -> None:
    index = pd.bdate_range("2020-01-01", periods=4)
    baseline = pd.Series([0.10, 0.10, 0.10, 0.10], index=index)
    sleeve = pd.Series([0.00, 0.00, 0.00, 0.00], index=index)
    dates = pd.DatetimeIndex([index[1], index[3]])
    free = overlay.mix_returns(baseline, sleeve, 0.5, dates)
    paid = overlay.mix_returns(baseline, sleeve, 0.5, dates, cost_bps=25.0)

    assert list(paid.remix_turnover[paid.remix_turnover > 0.0].index) == list(dates)
    assert paid.remix_turnover.loc[index[0]] == 0.0
    assert paid.remix_turnover.loc[index[2]] == 0.0
    for date in dates:
        expected = (1.0 + free.returns.loc[date]) * (
            1.0 - paid.remix_turnover.loc[date] * 25.0 / 10_000.0
        ) - 1.0
        assert paid.returns.loc[date] == pytest.approx(expected)
    for date in index.difference(dates):
        assert paid.returns.loc[date] == pytest.approx(free.returns.loc[date])


def test_dynamic_weight_changes_only_at_formation_dates() -> None:
    baseline, sleeve = component_returns()
    dates = pd.DatetimeIndex([baseline.index[1], baseline.index[3]])
    targets = pd.Series([0.2, 0.8], index=dates)
    result = overlay.mix_returns(baseline, sleeve, targets, dates)

    assert result.holdings.loc[dates[0], "sleeve"] == pytest.approx(0.2)
    assert result.holdings.loc[dates[1], "sleeve"] == pytest.approx(0.8)
    assert not np.isclose(result.holdings.loc[baseline.index[2], "sleeve"], 0.8)


def test_bad_inputs_are_rejected() -> None:
    baseline, sleeve = component_returns()
    with pytest.raises(ValueError, match="indexes must match"):
        overlay.mix_returns(baseline, sleeve.iloc[:-1], 0.1, pd.DatetimeIndex([]))
    with pytest.raises(ValueError, match=r"\[0, 1\]"):
        overlay.mix_returns(baseline, sleeve, 1.1, pd.DatetimeIndex([]))
    with pytest.raises(ValueError, match="formation dates"):
        overlay.mix_returns(
            baseline, sleeve, 0.1, pd.DatetimeIndex([pd.Timestamp("1999-01-01")])
        )
