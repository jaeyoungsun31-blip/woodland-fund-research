from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from woodland.live.incumbent import Incumbent, IncumbentStore, balanced_seed


def _evidence() -> tuple[dict[float, pd.Series], dict[float, pd.Series]]:
    index = pd.date_range("2020-01-01", periods=40, freq="B")
    returns = {cost: pd.Series(0.001 - cost / 1e6, index=index) for cost in (5.0, 10.0)}
    turnover = {cost: pd.Series(0.01, index=index) for cost in (5.0, 10.0)}
    return returns, turnover


def test_incumbent_store_round_trip_and_explicit_audit(tmp_path) -> None:
    returns, turnover = _evidence()
    incumbent = balanced_seed(returns, turnover)
    store = IncumbentStore(tmp_path)

    store.initialize(incumbent)
    loaded = store.load()

    assert loaded.name == "balanced-60-40"
    assert loaded.parameters["weights"] == {"SPY": 0.6, "IEF": 0.4}
    pd.testing.assert_series_equal(
        loaded.oos_returns[5.0], returns[5.0], check_names=False, check_freq=False
    )
    assert len(store.audit_path.read_text().splitlines()) == 1


def test_replacement_requires_its_exact_journal_reference(tmp_path) -> None:
    returns, turnover = _evidence()
    store = IncumbentStore(tmp_path)
    store.initialize(balanced_seed(returns, turnover))
    challenger = Incumbent(
        name="registered-challenger",
        parameters={"fixed": True},
        effective_date=date(2026, 9, 4),
        journal_entry="journal/2026-09-04-phase3-promotion.md",
        oos_returns=returns,
        oos_turnover=turnover,
    )

    with pytest.raises(ValueError, match="exact journal"):
        store.replace(challenger, journal_entry="journal/wrong.md")

    assert store.load().name == "balanced-60-40"
    assert len(store.audit_path.read_text().splitlines()) == 1

    store.replace(challenger, journal_entry=challenger.journal_entry)
    assert store.load().name == "registered-challenger"
    assert len(store.audit_path.read_text().splitlines()) == 2
