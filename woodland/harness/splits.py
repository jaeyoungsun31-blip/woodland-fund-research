"""Rolling walk-forward splits (DESIGN.md §7).

    train 5y -> [embargo] -> validate 1y, stepping forward 1y

The validate windows tile the calendar without overlap, so they stitch into
one continuous out-of-sample curve. Parameters are chosen on a split's train
window and evaluated on the NEXT window only.

The embargo is the part people skip. A signal evaluated on the first day of a
validate window looks back `max_lookback` bars; without a gap those bars sit
inside the train window the parameters were fitted on, and information flows
across the seam. So the embargo is measured in TRADING DAYS (not calendar
days, which would shrink it across holidays) and must be at least the signal's
maximum lookback. `check_embargo_covers_lookback` turns that from a comment
into an assertion.

Windows are half-open [start, end) throughout.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Split:
    """One walk-forward fold. All boundaries are half-open [start, end)."""

    i: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    validate_start: pd.Timestamp
    validate_end: pd.Timestamp

    @property
    def embargo_start(self) -> pd.Timestamp:
        return self.train_end

    @property
    def embargo_end(self) -> pd.Timestamp:
        return self.validate_start

    def train_index(self, index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        return index[(index >= self.train_start) & (index < self.train_end)]

    def embargo_index(self, index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        return index[(index >= self.train_end) & (index < self.validate_start)]

    def validate_index(self, index: pd.DatetimeIndex) -> pd.DatetimeIndex:
        return index[(index >= self.validate_start) & (index < self.validate_end)]

    def __str__(self) -> str:
        return (f"split {self.i}: train {self.train_start.date()}..{self.train_end.date()} "
                f"| embargo | validate {self.validate_start.date()}..{self.validate_end.date()}")


def trading_days_for_months(months: int, days_per_month: float = 21.0) -> int:
    """Trading-day embargo covering a lookback expressed in months.

    Rounded UP: an embargo that is too long only costs sample, while one that
    is too short leaks.
    """
    return int(-(-months * days_per_month // 1))


def make_splits(
    index: pd.DatetimeIndex,
    *,
    train_years: int = 5,
    validate_years: int = 1,
    step_years: int = 1,
    embargo_days: int = 210,
) -> list[Split]:
    """Build rolling walk-forward splits over a trading calendar.

    `index` is the trading calendar (a price matrix's index), NOT a calendar-day
    range: the embargo is counted in bars of this index.

    Window lengths are calendar-year offsets so windows mean what they say
    across leap years and holiday drift; only the embargo is positional.
    """
    if embargo_days < 0:
        raise ValueError("embargo_days must be >= 0")
    for name, v in [("train_years", train_years), ("validate_years", validate_years),
                    ("step_years", step_years)]:
        if v <= 0:
            raise ValueError(f"{name} must be > 0")

    index = pd.DatetimeIndex(index).sort_values().unique()
    n = len(index)
    if n == 0:
        return []

    # Earliest validate start with room for a full train window plus the embargo.
    pos = int(index.searchsorted(index[0] + pd.DateOffset(years=train_years))) + embargo_days

    splits: list[Split] = []
    while pos < n:
        validate_start = index[pos]
        validate_end = validate_start + pd.DateOffset(years=validate_years)
        train_end = index[pos - embargo_days] if embargo_days else validate_start
        train_start = train_end - pd.DateOffset(years=train_years)
        if train_start < index[0]:
            break
        if not len(index[(index >= validate_start) & (index < validate_end)]):
            break
        splits.append(Split(len(splits), train_start, train_end, validate_start, validate_end))
        pos = int(index.searchsorted(validate_start + pd.DateOffset(years=step_years)))
        if pos >= n:
            break
    return splits


def check_embargo_covers_lookback(
    splits: list[Split], index: pd.DatetimeIndex, max_lookback_days: int
) -> None:
    """Assert no signal lookback from a validate window reaches into its train window.

    Raises ValueError naming the offending split. Call this before any
    walk-forward run — it is the guard that makes the embargo real rather than
    decorative.
    """
    index = pd.DatetimeIndex(index).sort_values().unique()
    for s in splits:
        v_pos = int(index.searchsorted(s.validate_start))
        reach = index[max(v_pos - max_lookback_days, 0)]
        if reach < s.train_end:
            raise ValueError(
                f"embargo too short on split {s.i}: a {max_lookback_days}-bar lookback from "
                f"{s.validate_start.date()} reaches {reach.date()}, inside the train window "
                f"ending {s.train_end.date()}. Increase embargo_days to >= "
                f"{max_lookback_days}."
            )


def describe(splits: list[Split], index: pd.DatetimeIndex) -> pd.DataFrame:
    """Inspection table: one row per split with bar counts for each window."""
    index = pd.DatetimeIndex(index).sort_values().unique()
    rows = []
    for s in splits:
        rows.append({
            "split": s.i,
            "train_start": s.train_start.date(),
            "train_end": s.train_end.date(),
            "train_days": len(s.train_index(index)),
            "embargo_days": len(s.embargo_index(index)),
            "validate_start": s.validate_start.date(),
            "validate_end": s.validate_end.date(),
            "validate_days": len(s.validate_index(index)),
        })
    return pd.DataFrame(rows).set_index("split")
