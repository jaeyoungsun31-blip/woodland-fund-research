"""Causal realized-volatility exposure overlay."""

from __future__ import annotations

import numpy as np
import pandas as pd

from woodland import backtest
from woodland.metrics import TRADING_DAYS


def vol_target_targets(
    prices: pd.DataFrame,
    base_targets: pd.DataFrame,
    *,
    window: int = 63,
    target_ann_vol: float = 0.10,
    max_scale: float = 1.0,
) -> pd.DataFrame:
    """Scale target vectors using trailing volatility through each decision.

    The volatility estimate comes from the unscaled base portfolio's pre-cost
    returns. The overlay is causal: a target decided at close t uses returns
    through t and is still executed by the engine at close t+1.
    """
    if window < 2:
        raise ValueError("volatility window must be at least two bars")
    if target_ann_vol <= 0:
        raise ValueError("target_ann_vol must be positive")
    if not 0 < max_scale <= 1:
        raise ValueError("max_scale must be in (0, 1]")

    unscaled = backtest.run(prices, base_targets, cost_bps=0.0)
    realized = unscaled.returns.rolling(window, min_periods=window).std()
    realized = realized * np.sqrt(TRADING_DAYS)
    scale = (target_ann_vol / realized).clip(lower=0.0, upper=max_scale)
    scale = scale.where(np.isfinite(scale), max_scale).fillna(max_scale)

    scaled = base_targets.copy()
    decisions = base_targets.notna().any(axis=1)
    scaled.loc[decisions] = base_targets.loc[decisions].mul(scale.loc[decisions], axis=0)
    return scaled
