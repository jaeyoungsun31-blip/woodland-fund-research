from __future__ import annotations

import pandas as pd
import pytest

from woodland.live.bands import apply_no_trade_band


def test_band_emits_nothing_when_every_gap_is_inside() -> None:
    current = pd.Series({"SPY": 0.58, "IEF": 0.42})
    ideal = pd.Series({"SPY": 0.60, "IEF": 0.40})

    decision = apply_no_trade_band(ideal, current, band=0.05, periods_per_year=12)

    pd.testing.assert_series_equal(
        decision.trades, pd.Series({"SPY": 0.0, "IEF": -0.0}, name="trade")
    )
    pd.testing.assert_series_equal(
        decision.bounded_target,
        current.astype(float).rename("bounded_target"),
    )
    assert decision.one_way_turnover == 0.0


def test_band_trades_only_the_gap_beyond_the_boundary() -> None:
    current = pd.Series({"SPY": 0.48, "IEF": 0.52})
    ideal = pd.Series({"SPY": 0.60, "IEF": 0.40})

    decision = apply_no_trade_band(ideal, current, band=0.05, periods_per_year=12)

    assert decision.trades["SPY"] == pytest.approx(0.07)
    assert decision.trades["IEF"] == pytest.approx(-0.07)
    assert decision.bounded_target["SPY"] == pytest.approx(0.55)
    assert decision.bounded_target["IEF"] == pytest.approx(0.45)
    assert decision.one_way_turnover == pytest.approx(0.14)
    assert decision.annualized_turnover == pytest.approx(1.68)
