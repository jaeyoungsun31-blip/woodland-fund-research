import math

import pandas as pd
import pytest

from woodland import metrics


def test_empty_returns_are_not_reported_as_performance():
    returns = pd.Series([], dtype=float, index=pd.DatetimeIndex([]))

    assert math.isnan(metrics.cagr(returns))
    assert math.isnan(metrics.ann_vol(returns))
    assert math.isnan(metrics.sharpe(returns))
    assert math.isnan(metrics.max_drawdown(returns))
    assert metrics.drawdown_duration_days(returns) == 0
    assert math.isnan(metrics.hit_rate(returns))
    assert math.isnan(metrics.ann_turnover(returns))


def test_single_bar_returns_do_not_create_a_volatility_or_sharpe_estimate():
    returns = pd.Series([0.01], index=pd.DatetimeIndex(["2024-01-02"]))

    assert metrics.cagr(returns) == pytest.approx((1.01**252) - 1)
    assert math.isnan(metrics.ann_vol(returns))
    assert math.isnan(metrics.sharpe(returns))
    assert metrics.max_drawdown(returns) == pytest.approx(0.0)
    assert metrics.drawdown_duration_days(returns) == 0


def test_all_negative_returns_keep_loss_and_drawdown_signs():
    returns = pd.Series([-0.01, -0.02, -0.03], index=pd.bdate_range("2024-01-02", periods=3))

    assert metrics.cagr(returns) < 0
    assert metrics.sharpe(returns) < 0
    assert metrics.max_drawdown(returns) == pytest.approx((0.98 * 0.97) - 1)
    assert metrics.drawdown_duration_days(returns) == 2
    assert metrics.hit_rate(returns) == pytest.approx(0.0)
