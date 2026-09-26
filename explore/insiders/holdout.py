"""Fail-closed filing-date boundary for every insider return-analysis entry point."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

import pandas as pd

TRAINING_START = date(2012, 1, 1)
TRAINING_END = date(2022, 6, 30)
HOLDOUT_START = date(2022, 7, 1)
HOLDOUT_END = date(2026, 6, 30)


def require_training_events(filing_dates: Iterable[object]) -> None:
    """Refuse any event outside the locked training period, including NaT."""
    dates = pd.to_datetime(list(filing_dates), errors="coerce")
    if len(dates) == 0:
        raise ValueError("No training events supplied")
    if dates.isna().any():
        raise ValueError("Invalid or missing filing date; refusing return analysis")
    if ((dates >= pd.Timestamp(HOLDOUT_START)) & (dates <= pd.Timestamp(HOLDOUT_END))).any():
        raise ValueError("Sealed holdout filing; refusing return analysis")
    if ((dates < pd.Timestamp(TRAINING_START)) | (dates > pd.Timestamp(TRAINING_END))).any():
        raise ValueError("Filing outside locked training interval; refusing return analysis")
