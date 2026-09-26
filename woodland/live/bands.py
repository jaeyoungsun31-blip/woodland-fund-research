"""No-trade bands for turning an ideal target into a bounded trade."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# Operational default, declared rather than tuned.  Five percentage points is
# the already-implemented v12/v14 band setting and is not re-evaluated here.
DEFAULT_BAND = 0.05
DEFAULT_PERIODS_PER_YEAR = 252
TURNOVER_BUDGET_MIN = 4.6
TURNOVER_BUDGET_MAX = 9.3


@dataclass(frozen=True)
class BandDecision:
    ideal_target: pd.Series
    current_weights: pd.Series
    trades: pd.Series
    bounded_target: pd.Series
    band: float
    one_way_turnover: float
    annualized_turnover: float
    turnover_budget_status: str


def _budget_status(annualized_turnover: float) -> str:
    if annualized_turnover < TURNOVER_BUDGET_MIN:
        return "below 4.6x-9.3x retail budget range"
    if annualized_turnover <= TURNOVER_BUDGET_MAX:
        return "inside 4.6x-9.3x retail budget range"
    return "above 4.6x-9.3x retail budget range"


def apply_no_trade_band(
    ideal_target: pd.Series,
    current_weights: pd.Series,
    *,
    band: float = DEFAULT_BAND,
    periods_per_year: int = DEFAULT_PERIODS_PER_YEAR,
) -> BandDecision:
    """Trade only the part of each target gap lying outside ``band``.

    Assets already inside the band do not move.  An asset outside it is moved
    to the nearest band boundary, not all the way to the ideal.  Turnover is
    the same one-way sum of absolute weight changes used by the backtester.
    """
    if not 0.0 <= band < 1.0:
        raise ValueError("band must be in [0, 1)")
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if not ideal_target.index.equals(current_weights.index):
        raise ValueError("ideal target and current weights must have identical assets")
    if ideal_target.isna().any() or current_weights.isna().any():
        raise ValueError("weights must be complete")
    if not np.isfinite(ideal_target.to_numpy(float)).all() or not np.isfinite(
        current_weights.to_numpy(float)
    ).all():
        raise ValueError("weights must be finite")

    gap = ideal_target.astype(float) - current_weights.astype(float)
    trades = gap.apply(lambda value: np.sign(value) * max(abs(value) - band, 0.0))
    trades.name = "trade"
    bounded = (current_weights.astype(float) + trades).rename("bounded_target")
    turnover = float(trades.abs().sum())
    annualized = turnover * periods_per_year
    return BandDecision(
        ideal_target=ideal_target.astype(float).rename("ideal_target"),
        current_weights=current_weights.astype(float).rename("current_weights"),
        trades=trades,
        bounded_target=bounded,
        band=float(band),
        one_way_turnover=turnover,
        annualized_turnover=annualized,
        turnover_budget_status=_budget_status(annualized),
    )
