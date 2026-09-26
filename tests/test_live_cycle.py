from __future__ import annotations

from dataclasses import replace
from datetime import date

import pandas as pd

from woodland.harness.ledger import TrialsLedger
from woodland.live.cycle import (
    CycleSnapshot,
    RegisteredChallenger,
    _investigate_escalation_failures,
    _journal_text,
    _target_investigate_failures,
    execute_cycle,
    format_result,
    run_cycle,
)
from woodland.live.incumbent import Incumbent, IncumbentStore, balanced_seed
from woodland.live.refusal import CycleHealth


def _snapshot() -> CycleSnapshot:
    index = pd.date_range("2024-01-02", periods=80, freq="B")
    prices = pd.DataFrame(
        {
            "SPY": pd.Series(range(100, 180), index=index, dtype=float),
            "IEF": pd.Series(range(100, 180), index=index, dtype=float),
        }
    )
    returns = {cost: pd.Series(0.0003, index=index) for cost in (5.0, 10.0)}
    turnover = {cost: pd.Series(0.0005, index=index) for cost in (5.0, 10.0)}
    health = CycleHealth(
        integrity_failures=(),
        store_last_bar=pd.Timestamp("2026-09-01"),
        as_of=date(2026, 9, 3),
        realized_folds=22,
        expected_folds=22,
        spy_cagr_since_2000=0.075,
        spy_max_drawdown_since_2000=-0.55,
    )
    return CycleSnapshot(
        prices=prices,
        risk_free=pd.Series(0.00005, index=index),
        health=health,
        seeded_incumbent=balanced_seed(returns, turnover),
        current_weights=pd.Series({"SPY": 0.58, "IEF": 0.42}),
        ideal_target=pd.Series({"SPY": 0.60, "IEF": 0.40}),
        decision_close=pd.Series({"SPY": 179.0, "IEF": 179.0}),
        decision_timestamp=index[-1],
        integrity_report=pd.DataFrame(),
        refresh_note="synthetic stored-data fixture inspected",
    )


def test_full_stored_data_dry_run_completes_with_no_change_and_no_writes(tmp_path) -> None:
    snapshot = _snapshot()
    state = IncumbentStore(tmp_path / "state")
    state.initialize(snapshot.seeded_incumbent)
    audit_before = state.audit_path.read_text()
    ledger = tmp_path / "trials.db"
    journal = tmp_path / "journal"

    result = execute_cycle(
        snapshot,
        state,
        dry_run=True,
        ledger_path=ledger,
        journal_dir=journal,
    )

    assert result.status == "completed"
    assert result.decision == "no change"
    assert not result.target_emitted
    assert result.ledger_rows == 0
    assert result.journal_path is None
    assert not ledger.exists()
    assert not journal.exists()
    assert state.audit_path.read_text() == audit_before
    assert format_result(result).endswith("FINAL: no change")


def test_refused_cycle_has_no_target_or_refit(tmp_path) -> None:
    snapshot = _snapshot()
    refused = replace(
        snapshot,
        health=replace(snapshot.health, integrity_failures=("cross-check failed",)),
    )

    result = execute_cycle(refused, IncumbentStore(tmp_path / "state"), dry_run=True)

    assert result.status == "refused"
    assert result.decision == "no change"
    assert result.band_decision is None
    assert result.refit_note == "not run: refusal precedes refit"
    assert not result.target_emitted


def test_investigate_on_target_blocks_but_outside_target_is_a_warning() -> None:
    snapshot = _snapshot()
    inside = _target_investigate_failures(("SPY", "XLK"), ("SPY", "IEF"))
    blocked = run_cycle(
        replace(snapshot, health=replace(snapshot.health, integrity_failures=tuple(inside))),
        snapshot.seeded_incumbent,
        dry_run=True,
    )
    assert blocked.refusal.refused
    assert not blocked.target_emitted
    assert _target_investigate_failures(("XLK",), ("SPY", "IEF")) == []


def test_store_wide_investigate_count_above_baseline_blocks_regardless_of_scope() -> None:
    snapshot = _snapshot()
    escalation = _investigate_escalation_failures(tuple(f"X{i}" for i in range(12)))
    blocked = run_cycle(
        replace(snapshot, health=replace(snapshot.health, integrity_failures=tuple(escalation))),
        snapshot.seeded_incumbent,
        dry_run=True,
    )
    assert blocked.refusal.refused
    assert "baseline 11" in blocked.refusal.summary


def test_failed_challenger_is_committed_as_completed_not_dropped(tmp_path) -> None:
    snapshot = _snapshot()
    challenger = Incumbent(
        name="exact-tie",
        parameters={"registered": True},
        effective_date=date(2026, 9, 3),
        journal_entry="journal/2026-09-03-phase3-tie-registration.md",
        oos_returns=snapshot.seeded_incumbent.oos_returns,
        oos_turnover=snapshot.seeded_incumbent.oos_turnover,
    )
    registered = RegisteredChallenger(
        record=challenger,
        study_id="phase3-test-challenge",
        config={"name": challenger.name},
    )
    ledger_path = tmp_path / "trials.db"
    journal_dir = tmp_path / "journal"

    result = execute_cycle(
        snapshot,
        IncumbentStore(tmp_path / "state"),
        [registered],
        dry_run=False,
        ledger_path=ledger_path,
        journal_dir=journal_dir,
        inference_resamples=25,
    )

    assert result.decision == "no change"
    assert result.gate_verdicts[0].completed
    assert not result.gate_verdicts[0].promote
    assert result.ledger_rows == 1
    assert result.journal_path is not None
    assert "phase3" in result.journal_path.name
    assert result.journal_path.exists()
    with TrialsLedger(ledger_path) as ledger:
        rows = ledger.trials("phase3-test-challenge")
    assert len(rows) == 1
    assert rows.iloc[0]["status"] == "evaluated"


def test_cycle_journal_names_every_store_wide_investigate_ticker(tmp_path) -> None:
    snapshot = replace(
        _snapshot(),
        store_wide_investigate_tickers=("XLK", "XLY"),
        integrity_target_symbols=("SPY", "IEF"),
        store_wide_investigate_baseline=11,
    )
    result = execute_cycle(
        snapshot,
        IncumbentStore(tmp_path / "state"),
        dry_run=False,
        ledger_path=tmp_path / "trials.db",
        journal_dir=tmp_path / "journal",
    )
    assert result.status == "completed"
    assert result.journal_path is not None
    journal = result.journal_path.read_text()
    assert "Store-wide INVESTIGATE baseline: 11" in journal
    assert "Store-wide INVESTIGATE tickers: XLK, XLY" in journal


def test_cycle_journal_labels_submitted_turnover_separately_from_bounded_target() -> None:
    snapshot = _snapshot()
    result = run_cycle(snapshot, snapshot.seeded_incumbent, dry_run=False, emit_targets=True)
    journal = _journal_text(
        replace(result, submitted_notional=50.0, submitted_one_way_turnover=0.05), snapshot
    )
    assert "Bounded-target reference one-cycle turnover" in journal
    assert "Realized one-cycle turnover (submitted notional / account equity): 0.050000" in journal
    assert "Submitted notional: 50.00" in journal
