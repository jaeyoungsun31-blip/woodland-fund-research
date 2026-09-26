from __future__ import annotations

from datetime import date

import pandas as pd

from scripts.dress_rehearsal import run_rehearsal
from woodland.live.cycle import CycleSnapshot
from woodland.live.incumbent import balanced_seed
from woodland.live.refusal import CycleHealth


def test_dress_rehearsal_induces_each_refusal_without_emitting_a_target() -> None:
    index = pd.date_range("2026-01-02", periods=80, freq="B")
    returns = {cost: pd.Series(0.0003, index=index) for cost in (5.0, 10.0)}
    turnover = {cost: pd.Series(0.0005, index=index) for cost in (5.0, 10.0)}
    snapshot = CycleSnapshot(
        prices=pd.DataFrame({"SPY": 100.0, "IEF": 100.0}, index=index),
        risk_free=pd.Series(0.00005, index=index),
        health=CycleHealth((), pd.Timestamp("2026-09-04"), date(2026, 9, 4), 22, 22, 0.075, -0.55),
        seeded_incumbent=balanced_seed(returns, turnover),
        current_weights=pd.Series({"SPY": 0.58, "IEF": 0.42}),
        ideal_target=pd.Series({"SPY": 0.60, "IEF": 0.40}),
        decision_close=pd.Series({"SPY": 100.0, "IEF": 100.0}),
        decision_timestamp=index[-1],
        integrity_report=pd.DataFrame(),
        refresh_note="fixture",
    )

    results = run_rehearsal(snapshot)

    assert len(results) == 6
    assert all(result.passed and not result.target_emitted for result in results)
    assert {result.condition for result in results} == {
        "stale data (>5 calendar days)",
        "corrupted calendar date",
        "frozen fold-count mismatch",
        "market closed",
        "sanity-anchor breach",
        "live base URL",
    }
