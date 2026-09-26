"""Hand-computed checks for the declared training-only robustness transforms."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from first_returns import Trade
from robustness_screen import gross_event_return, median_monthly, winsorize_trade


def sample_trade(*, terminal: bool = False) -> Trade:
    return Trade(
        issuer_cik="1",
        ticker="ABC",
        filing_date=pd.Timestamp("2020-01-30"),
        bucket="under_300k",
        entry_idx=1,
        exit_idx=3,
        spread=0.01,
        opens=np.array([100.0, 110.0, 120.0]),
        closes=np.array([110.0, 120.0, 130.0]),
        delisting_return=-0.3 if terminal else 0.0,
    )


def test_winsorization_only_changes_exit_mark() -> None:
    trade = sample_trade()
    clipped = winsorize_trade(trade, -0.2, 0.2)
    assert gross_event_return(trade) == pytest.approx(0.3)
    assert gross_event_return(clipped) == pytest.approx(0.2)
    assert np.array_equal(clipped.closes[:-1], trade.closes[:-1])
    assert trade.closes[-1] == 130.0


def test_winsorization_includes_terminal_haircut() -> None:
    trade = sample_trade(terminal=True)
    clipped = winsorize_trade(trade, -0.05, 0.5)
    assert gross_event_return(trade) == pytest.approx(-0.09)
    assert gross_event_return(clipped) == pytest.approx(-0.05)


def test_monthly_median_uses_partial_month_position_marks() -> None:
    calendar = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-03", "2020-02-04"])
    monthly = median_monthly([sample_trade()], calendar)
    cost = 0.0105
    assert len(monthly) == 2
    assert monthly.gross.iloc[0] == pytest.approx(0.10)
    assert monthly.net.iloc[0] == pytest.approx(1.10 * (1 - cost) - 1)
    assert monthly.gross.iloc[1] == pytest.approx(130 / 110 - 1)
    assert monthly.net.iloc[1] == pytest.approx(130 / 110 * (1 - cost) - 1)
