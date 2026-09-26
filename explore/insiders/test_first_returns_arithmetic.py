"""Small hand-calculated checks for the locked return implementation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from first_returns import Trade, cluster_starts, corwin_schultz_spread, simulate


def test_cluster_starts_at_second_owner_and_suppresses_90_days() -> None:
    events = pd.DataFrame(
        {
            "ISSUERCIK": ["1"] * 5,
            "RPTOWNERCIK": ["a", "b", "c", "c", "d"],
            "filing_date": pd.to_datetime(
                ["2020-01-01", "2020-01-15", "2020-02-01", "2020-04-20", "2020-05-01"]
            ),
        }
    )
    assert cluster_starts(events).filing_date.dt.strftime("%Y-%m-%d").tolist() == [
        "2020-01-15",
        "2020-05-01",
    ]


def test_full_spread_is_paid_on_entry_and_exit() -> None:
    dates = pd.date_range("2020-01-02", periods=2, freq="B")
    trade = Trade(
        issuer_cik="1",
        ticker="X",
        filing_date=pd.Timestamp("2020-01-01"),
        bucket="under_300k",
        entry_idx=0,
        exit_idx=1,
        spread=0.01,
        opens=np.array([100.0, 110.0]),
        closes=np.array([110.0, 120.0]),
    )
    cash = pd.Series([100.0, 100.0], index=dates)
    result = simulate([trade], dates, cash)
    assert np.isclose(result.gross.iloc[0], 0.2)
    expected_net = 1.2 * (1 - 0.0105) ** 2 - 1
    assert np.isclose(result.net.iloc[0], expected_net)


def test_zero_range_implies_zero_corwin_schultz_spread() -> None:
    assert corwin_schultz_spread(np.full(20, 10.0), np.full(20, 10.0)) == 0.0
