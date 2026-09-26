"""Maintain a two-return-stream mix and charge its re-mix trades.

The inputs are complete component return streams. Any trading costs internal
to a component belong in those inputs; this layer charges only the additional
turnover required to restore the requested baseline/sleeve allocation.
Re-mixing happens after the dated component return and therefore sets the
allocation for the following bar.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_EPSILON = 1e-12


@dataclass(frozen=True)
class OverlayResult:
    """Net return path and post-close state of a maintained two-part mix."""

    returns: pd.Series
    equity: pd.Series
    holdings: pd.DataFrame
    remix_turnover: pd.Series
    cost_bps: float


def _validate_inputs(
    baseline: pd.Series,
    sleeve: pd.Series,
    formation_dates: pd.DatetimeIndex,
) -> pd.DatetimeIndex:
    if not baseline.index.equals(sleeve.index):
        raise ValueError("baseline and sleeve return indexes must match exactly")
    index = pd.DatetimeIndex(baseline.index)
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("return index must be sorted and unique")
    values = np.column_stack(
        [baseline.to_numpy(dtype=float), sleeve.to_numpy(dtype=float)]
    )
    if not np.isfinite(values).all():
        raise ValueError("component returns must be finite")
    if (values <= -1.0).any():
        raise ValueError("component returns must be greater than -100%")
    dates = pd.DatetimeIndex(formation_dates)
    if not dates.is_monotonic_increasing or dates.has_duplicates:
        raise ValueError("formation dates must be sorted and unique")
    unknown = dates.difference(index)
    if len(unknown):
        raise ValueError("formation dates must belong to the return index")
    return index


def _weight_schedule(
    sleeve_weight: float | pd.Series,
    formation_dates: pd.DatetimeIndex,
) -> tuple[float, dict[pd.Timestamp, float]]:
    if isinstance(sleeve_weight, pd.Series):
        targets = sleeve_weight.astype(float)
        target_dates = pd.DatetimeIndex(targets.index)
        if not target_dates.equals(formation_dates):
            raise ValueError(
                "dynamic sleeve weights must have exactly the formation-date index"
            )
        if targets.empty:
            raise ValueError("dynamic sleeve weights must not be empty")
        initial = float(targets.iloc[0])
        schedule = {
            date: float(value)
            for date, value in zip(
                target_dates, targets.to_numpy(dtype=float), strict=True
            )
        }
    else:
        initial = float(sleeve_weight)
        schedule = {pd.Timestamp(date): initial for date in formation_dates}
    weights = np.asarray([initial, *schedule.values()], dtype=float)
    if not np.isfinite(weights).all() or ((weights < 0.0) | (weights > 1.0)).any():
        raise ValueError("sleeve weights must be finite and in [0, 1]")
    return initial, schedule


def mix_returns(
    baseline: pd.Series,
    sleeve: pd.Series,
    sleeve_weight: float | pd.Series,
    formation_dates: pd.DatetimeIndex,
    *,
    cost_bps: float = 0.0,
) -> OverlayResult:
    """Compose two return streams and restore ``(1-s)/s`` at formations.

    The portfolio starts at the first requested mix without an initial funding
    charge. On every bar, component returns accrue first. A formation date then
    trades from drifted weights back to that date's target; one-way cost is
    charged on ``sum(abs(target - drifted))`` on that date. The restored mix
    consequently governs the next bar.

    A scalar ``sleeve_weight`` uses one fixed mix. A Series supports a
    walk-forward-selected mix: it must contain one target for every formation
    date, and its first value is also the initial allocation.
    """
    if cost_bps < 0.0:
        raise ValueError("cost_bps must be non-negative")
    index = _validate_inputs(baseline, sleeve, formation_dates)
    initial, schedule = _weight_schedule(sleeve_weight, formation_dates)
    component_returns = np.column_stack(
        [baseline.to_numpy(dtype=float), sleeve.to_numpy(dtype=float)]
    )

    holdings = np.empty_like(component_returns)
    output_returns = np.empty(len(index), dtype=float)
    output_turnover = np.zeros(len(index), dtype=float)
    weights = np.asarray([1.0 - initial, initial], dtype=float)
    cost_rate = cost_bps / 10_000.0

    for position, (date, component_return) in enumerate(
        zip(index, component_returns, strict=True)
    ):
        gross_return = float(weights @ component_return)
        growth = 1.0 + gross_return
        if growth <= _EPSILON:
            raise ValueError(f"overlay wealth is non-positive on {date.date()}")
        drifted = weights * (1.0 + component_return) / growth
        day_return = gross_return

        target_sleeve = schedule.get(date)
        if target_sleeve is not None:
            target = np.asarray([1.0 - target_sleeve, target_sleeve])
            turnover = float(np.abs(target - drifted).sum())
            day_return = (1.0 + gross_return) * (1.0 - turnover * cost_rate) - 1.0
            output_turnover[position] = turnover
            weights = target
        else:
            weights = drifted

        output_returns[position] = day_return
        holdings[position] = weights

    returns = pd.Series(output_returns, index=index, name="ret")
    return OverlayResult(
        returns=returns,
        equity=(1.0 + returns).cumprod().rename("equity"),
        holdings=pd.DataFrame(
            holdings, index=index, columns=["baseline", "sleeve"]
        ),
        remix_turnover=pd.Series(output_turnover, index=index, name="turnover"),
        cost_bps=float(cost_bps),
    )
