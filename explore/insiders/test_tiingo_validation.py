"""Guard the retired Tiingo raw-cache workflow and retained derived tables."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_tiingo_validation import fetch_all
from validate_tiingo_prices import analyze

HERE = Path(__file__).resolve().parent


def test_tiingo_raw_cache_is_empty() -> None:
    assert not list((HERE / "cache" / "tiingo").rglob("*"))


def test_retired_raw_fetch_refuses() -> None:
    with pytest.raises(RuntimeError, match="caching is retired"):
        fetch_all()


def test_retired_raw_analysis_refuses() -> None:
    with pytest.raises(RuntimeError, match="raw responses were deleted"):
        analyze()


def test_derived_validation_tables_survive_without_raw_bars() -> None:
    events = pd.read_csv(HERE / "tiingo_validation_events.csv")
    summary = pd.read_csv(HERE / "tiingo_validation_summary.csv")
    splits = pd.read_csv(HERE / "tiingo_validation_splits.csv")
    missing = pd.read_csv(HERE / "tiingo_validation_missing_symbols.csv")
    assert len(events) == 300
    assert events.ticker.nunique() == 272
    assert {"offline_return", "eodhd_adjusted_return", "tiingo_return"} <= set(events)
    assert len(summary) == 6
    assert {"ticker", "date", "tiingo_split_factor"} <= set(splits)
    assert {"ticker", "reason", "in_eodhd_delisted_list"} <= set(missing)
