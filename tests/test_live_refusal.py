from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from woodland.live.refusal import CycleHealth, evaluate_refusal


@pytest.fixture
def healthy() -> CycleHealth:
    return CycleHealth(
        integrity_failures=(),
        store_last_bar=pd.Timestamp("2026-09-01"),
        as_of=date(2026, 9, 3),
        realized_folds=22,
        expected_folds=22,
        spy_cagr_since_2000=0.075,
        spy_max_drawdown_since_2000=-0.55,
    )


def test_healthy_cycle_does_not_refuse(healthy: CycleHealth) -> None:
    verdict = evaluate_refusal(healthy)
    assert not verdict.refused
    assert verdict.summary == "checks passed"


@pytest.mark.parametrize(
    ("changed", "code"),
    [
        ({"integrity_failures": ("SPY cross-check failed",)}, "integrity"),
        ({"store_last_bar": pd.Timestamp("2026-08-20")}, "stale_data"),
        ({"realized_folds": 21}, "fold_count"),
        ({"spy_cagr_since_2000": 0.10}, "sanity_anchor"),
        ({"spy_max_drawdown_since_2000": -0.40}, "sanity_anchor"),
    ],
)
def test_each_refusal_condition_fires(
    healthy: CycleHealth, changed: dict[str, object], code: str
) -> None:
    verdict = evaluate_refusal(replace(healthy, **changed))
    assert verdict.refused
    assert code in {reason.code for reason in verdict.reasons}
