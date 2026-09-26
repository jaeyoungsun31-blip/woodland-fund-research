"""Normal, structured halt conditions for a live retrain cycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

DEFAULT_MAX_STALE_CALENDAR_DAYS = 5
SPY_CAGR_MIN = 0.06
SPY_CAGR_MAX = 0.09
# The documented "about -55%" anchor is made executable as +/- five points.
SPY_MAX_DRAWDOWN_MIN = -0.60
SPY_MAX_DRAWDOWN_MAX = -0.50


@dataclass(frozen=True)
class CycleHealth:
    integrity_failures: tuple[str, ...]
    store_last_bar: pd.Timestamp | None
    as_of: date
    realized_folds: int
    expected_folds: int
    spy_cagr_since_2000: float
    spy_max_drawdown_since_2000: float


@dataclass(frozen=True)
class RefusalReason:
    code: str
    message: str


@dataclass(frozen=True)
class RefusalVerdict:
    refused: bool
    reasons: tuple[RefusalReason, ...]

    @property
    def summary(self) -> str:
        if not self.refused:
            return "checks passed"
        return "; ".join(f"{reason.code}: {reason.message}" for reason in self.reasons)


def evaluate_refusal(
    health: CycleHealth,
    *,
    max_stale_calendar_days: int = DEFAULT_MAX_STALE_CALENDAR_DAYS,
) -> RefusalVerdict:
    """Evaluate all halt conditions without raising for an expected refusal."""
    if max_stale_calendar_days < 0:
        raise ValueError("max_stale_calendar_days must be non-negative")
    reasons: list[RefusalReason] = []

    if health.integrity_failures:
        reasons.append(
            RefusalReason(
                "integrity",
                " | ".join(health.integrity_failures),
            )
        )

    if health.store_last_bar is None:
        reasons.append(RefusalReason("stale_data", "store has no terminal bar"))
    else:
        last_bar = pd.Timestamp(health.store_last_bar).date()
        age = (health.as_of - last_bar).days
        if age < 0:
            reasons.append(
                RefusalReason("stale_data", f"terminal bar {last_bar} is after as-of date")
            )
        elif age > max_stale_calendar_days:
            reasons.append(
                RefusalReason(
                    "stale_data",
                    f"terminal bar is {age} calendar days old; tolerance is "
                    f"{max_stale_calendar_days}",
                )
            )

    if health.realized_folds != health.expected_folds:
        reasons.append(
            RefusalReason(
                "fold_count",
                f"realized {health.realized_folds}, expected {health.expected_folds}",
            )
        )

    cagr = health.spy_cagr_since_2000
    drawdown = health.spy_max_drawdown_since_2000
    if not SPY_CAGR_MIN <= cagr <= SPY_CAGR_MAX:
        reasons.append(
            RefusalReason(
                "sanity_anchor",
                f"SPY CAGR {cagr:.2%} outside {SPY_CAGR_MIN:.0%}-{SPY_CAGR_MAX:.0%}",
            )
        )
    if not SPY_MAX_DRAWDOWN_MIN <= drawdown <= SPY_MAX_DRAWDOWN_MAX:
        reasons.append(
            RefusalReason(
                "sanity_anchor",
                f"SPY max drawdown {drawdown:.2%} outside "
                f"{SPY_MAX_DRAWDOWN_MIN:.0%}..{SPY_MAX_DRAWDOWN_MAX:.0%}",
            )
        )

    return RefusalVerdict(refused=bool(reasons), reasons=tuple(reasons))
