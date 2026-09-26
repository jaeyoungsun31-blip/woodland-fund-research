"""Unattended Phase 3 retrain-cycle orchestration.

The default path is deliberately read-only.  Research remains outside this
module: challengers arrive as already-registered, already-computed evidence.
This code refreshes or inspects data, refuses unsafe operation, applies the
frozen gate, bounds trades, and records an explicitly executed cycle.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from woodland import backtest, cash, data, metrics, study
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness.ledger import TrialsLedger
from woodland.live.bands import DEFAULT_BAND, BandDecision, apply_no_trade_band
from woodland.live.broker import DEFAULT_MAX_ORDER_NOTIONAL, PaperBroker, PaperSubmissionRefused
from woodland.live.drift import append_drift_record
from woodland.live.gate import GateVerdict, PortfolioEvidence, evaluate_gate
from woodland.live.incumbent import BALANCED_NAME, Incumbent, IncumbentStore, balanced_seed
from woodland.live.refusal import CycleHealth, RefusalVerdict, evaluate_refusal

LIVE_STUDY_ID = "phase3-retrain-cycle"
DEFAULT_STATE_DIR = ROOT / "data" / "live"
DEFAULT_LEDGER = ROOT / "journal" / "trials.db"
DEFAULT_JOURNAL_DIR = ROOT / "journal"
DEFAULT_DRIFT_LOG = ROOT / "data" / "live" / "paper-drift.jsonl"
# Baseline fixed by journal/2026-09-04-planning-decision-scope-integrity-refusal.md.
STORE_WIDE_INVESTIGATE_BASELINE = 11


def _utc_rfc3339(timestamp: pd.Timestamp) -> str:
    """Render a cycle boundary in the UTC-aware form Alpaca accepts for ``after``."""
    value = pd.Timestamp(timestamp)
    value = value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class RegisteredChallenger:
    """Frozen evidence for a challenger registered outside the live loop."""

    record: Incumbent
    study_id: str
    config: Mapping[str, Any]

    def evidence(self) -> PortfolioEvidence:
        turnover = self.record.oos_turnover.get(5.0)
        if turnover is None:
            raise ValueError(f"{self.record.name} has no 5 bps turnover evidence")
        return PortfolioEvidence(
            name=self.record.name,
            returns=self.record.oos_returns,
            turnover=turnover,
        )


@dataclass(frozen=True)
class CycleSnapshot:
    prices: pd.DataFrame
    risk_free: pd.Series
    health: CycleHealth
    seeded_incumbent: Incumbent
    current_weights: pd.Series
    ideal_target: pd.Series
    decision_close: pd.Series
    decision_timestamp: pd.Timestamp
    integrity_report: pd.DataFrame
    refresh_note: str
    store_wide_investigate_tickers: tuple[str, ...] = ()
    integrity_target_symbols: tuple[str, ...] = ()
    store_wide_investigate_baseline: int = STORE_WIDE_INVESTIGATE_BASELINE


@dataclass(frozen=True)
class CycleResult:
    status: str
    decision: str
    incumbent_before: str
    incumbent_after: str
    dry_run: bool
    refusal: RefusalVerdict
    gate_verdicts: tuple[GateVerdict, ...]
    band_decision: BandDecision | None
    refit_note: str
    target_emitted: bool
    state_action: str
    ledger_rows: int = 0
    journal_path: Path | None = None
    paper_submission: str = "not requested"
    paper_order_count: int = 0
    submitted_notional: float | None = None
    submitted_one_way_turnover: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "decision": self.decision,
            "incumbent_before": self.incumbent_before,
            "incumbent_after": self.incumbent_after,
            "dry_run": self.dry_run,
            "refusal": {
                "refused": self.refusal.refused,
                "reasons": [asdict(reason) for reason in self.refusal.reasons],
            },
            "gate_verdicts": [verdict.to_dict() for verdict in self.gate_verdicts],
            "band": _band_dict(self.band_decision),
            "refit_note": self.refit_note,
            "target_emitted": self.target_emitted,
            "state_action": self.state_action,
            "ledger_rows": self.ledger_rows,
            "journal_path": str(self.journal_path) if self.journal_path else None,
            "paper_submission": self.paper_submission,
            "paper_order_count": self.paper_order_count,
            "submitted_notional": self.submitted_notional,
            "submitted_one_way_turnover": self.submitted_one_way_turnover,
        }


def _band_dict(decision: BandDecision | None) -> dict[str, object] | None:
    if decision is None:
        return None
    return {
        "band": decision.band,
        "ideal_target": decision.ideal_target.to_dict(),
        "current_weights": decision.current_weights.to_dict(),
        "trades": decision.trades.to_dict(),
        "bounded_target": decision.bounded_target.to_dict(),
        "one_way_turnover": decision.one_way_turnover,
        "annualized_turnover": decision.annualized_turnover,
        "turnover_budget_status": decision.turnover_budget_status,
    }


def _provenance_failures(store: Path, tickers: Sequence[str]) -> list[str]:
    provenance = data.read_provenance(store)
    failures: list[str] = []
    for ticker in tickers:
        record = provenance.get(ticker)
        if not record:
            failures.append(f"{ticker}: missing provenance")
            continue
        adjustment = record.get("adjustment", {}).get("verdict")
        crosscheck = record.get("crosscheck", {}).get("verdict")
        if adjustment != "ok":
            failures.append(f"{ticker}: adjustment={adjustment!r}")
        if crosscheck not in {"ok", "INVESTIGATE"}:
            failures.append(f"{ticker}: crosscheck={crosscheck!r}")
    return failures


def _integrity_failures(
    prices: pd.DataFrame,
    report: pd.DataFrame,
    store: Path,
    tickers: Sequence[str],
    *,
    blocking_tickers: Sequence[str],
    store_wide_investigate_tickers: Sequence[str],
    investigate_baseline: int = STORE_WIDE_INVESTIGATE_BASELINE,
) -> list[str]:
    failures = _provenance_failures(store, blocking_tickers)
    failures.extend(_target_investigate_failures(store_wide_investigate_tickers, blocking_tickers))
    failures.extend(
        _investigate_escalation_failures(
            store_wide_investigate_tickers, baseline=investigate_baseline
        )
    )
    stale = report.index[report["freshness"] != "CURRENT"].tolist()
    if stale:
        failures.append(f"stale versus store consensus: {','.join(stale)}")
    invalid = report.index[
        report.get("n_nonpositive", pd.Series(0, index=report.index)).fillna(0).astype(int) > 0
    ].tolist()
    if invalid:
        failures.append(f"nonpositive adjusted prices: {','.join(invalid)}")
    calendar = data.calendar_report(prices)
    if not calendar.empty:
        failures.append(f"calendar integrity: {len(calendar)} suspect date(s)")
    return failures


def _store_wide_investigate_tickers(store: Path, tickers: Sequence[str]) -> tuple[str, ...]:
    provenance = data.read_provenance(store)
    return tuple(
        ticker
        for ticker in tickers
        if provenance.get(ticker, {}).get("crosscheck", {}).get("verdict") == "INVESTIGATE"
    )


def _investigate_escalation_failures(
    flagged_tickers: Sequence[str], *, baseline: int = STORE_WIDE_INVESTIGATE_BASELINE
) -> list[str]:
    """Escalate a growing store-wide disagreement even when targets remain clean."""
    if len(flagged_tickers) > baseline:
        return [
            "store-wide INVESTIGATE count "
            f"{len(flagged_tickers)} exceeds stored baseline {baseline}"
        ]
    return []


def _target_investigate_failures(
    flagged_tickers: Sequence[str], target_tickers: Sequence[str]
) -> list[str]:
    target_set = set(target_tickers)
    return [
        f"{ticker}: crosscheck='INVESTIGATE'" for ticker in flagged_tickers if ticker in target_set
    ]


def _terminal_consensus(report: pd.DataFrame) -> pd.Timestamp | None:
    current = report.loc[report["freshness"] == "CURRENT", "last"]
    if current.empty:
        return None
    modes = pd.to_datetime(current).mode()
    return pd.Timestamp(modes.iloc[-1]) if len(modes) else None


def _balanced_oos_evidence(
    prices: pd.DataFrame,
    risk_free: pd.Series,
    folds: list[Any],
) -> tuple[Incumbent, backtest.BacktestResult]:
    lo, hi, _ = study.oos_window(pd.DatetimeIndex(prices.index), folds)
    returns: dict[float, pd.Series] = {}
    turnover: dict[float, pd.Series] = {}
    primary: backtest.BacktestResult | None = None
    for cost_bps in (5.0, 10.0):
        result = backtest.fixed_mix(
            prices,
            {"SPY": 0.60, "IEF": 0.40},
            cost_bps=cost_bps,
            risk_free=risk_free,
        )
        returns[cost_bps] = result.returns.loc[lo:hi]
        turnover[cost_bps] = result.turnover.loc[lo:hi]
        if cost_bps == 5.0:
            primary = result
    if primary is None:
        raise RuntimeError("failed to build primary 60/40 evidence")
    return balanced_seed(returns, turnover), primary


def refresh_store(*, enabled: bool) -> str:
    """Run the existing ingest entrypoint only when refresh is explicit."""
    if not enabled:
        return "refresh skipped; existing store inspected"
    process = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ingest.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode:
        detail = (process.stderr or process.stdout).strip().splitlines()
        tail = detail[-1] if detail else "no diagnostic"
        return f"refresh failed with exit {process.returncode}: {tail}"
    return "refresh completed"


def build_snapshot(
    *,
    as_of: date | None = None,
    refresh: bool = False,
    store: Path | None = None,
) -> CycleSnapshot:
    """Inspect the current store and build the fixed incumbent's live inputs."""
    cfg = load_config()
    store_path = store or (ROOT / cfg["data"]["store"])
    tickers = all_tickers(cfg)
    ideal = pd.Series({"SPY": 0.60, "IEF": 0.40}, dtype=float)
    target_symbols = tuple(str(symbol) for symbol in ideal.index)
    store_wide_investigate = _store_wide_investigate_tickers(store_path, tickers)
    refresh_note = refresh_store(enabled=refresh)
    prices = data.build_matrix(tickers, store_path, research=False)
    integrity = data.integrity_report(prices)
    failures = _integrity_failures(
        prices,
        integrity,
        store_path,
        tickers,
        blocking_tickers=target_symbols,
        store_wide_investigate_tickers=store_wide_investigate,
    )
    if refresh_note.startswith("refresh failed"):
        failures.insert(0, refresh_note)

    cleaned, _ = data.drop_suspect_dates(prices)
    index = pd.DatetimeIndex(cleaned.index)
    folds = study.make_folds(index)
    raw_rf = cash.load_risk_free_daily(store_path)
    risk_free, _ = cash.align_risk_free(raw_rf, index)
    incumbent, primary = _balanced_oos_evidence(cleaned, risk_free, folds)

    spy_prices = cleaned.loc[cleaned.index >= pd.Timestamp("2000-01-01"), ["SPY"]]
    spy = backtest.buy_and_hold(spy_prices, "SPY", cost_bps=0.0).returns
    health = CycleHealth(
        integrity_failures=tuple(failures),
        store_last_bar=_terminal_consensus(integrity),
        as_of=as_of or date.today(),
        realized_folds=len(folds),
        expected_folds=study.ETF_EXPECTED_FOLDS,
        spy_cagr_since_2000=metrics.cagr(spy),
        spy_max_drawdown_since_2000=metrics.max_drawdown(spy),
    )
    current = primary.holdings.iloc[-1].reindex(ideal.index).fillna(0.0)
    return CycleSnapshot(
        prices=cleaned,
        risk_free=risk_free,
        health=health,
        seeded_incumbent=incumbent,
        current_weights=current,
        ideal_target=ideal,
        decision_close=cleaned.iloc[-1].reindex(ideal.index).astype(float),
        decision_timestamp=pd.Timestamp(cleaned.index[-1]),
        integrity_report=integrity,
        refresh_note=refresh_note,
        store_wide_investigate_tickers=store_wide_investigate,
        integrity_target_symbols=target_symbols,
    )


def run_cycle(
    snapshot: CycleSnapshot,
    incumbent: Incumbent,
    challengers: Sequence[RegisteredChallenger] = (),
    *,
    dry_run: bool = True,
    emit_targets: bool = False,
    band: float = DEFAULT_BAND,
    approved_promotion: str | None = None,
    inference_resamples: int = 10_000,
) -> CycleResult:
    """Run the decision portion of one cycle without performing persistence."""
    refusal = evaluate_refusal(snapshot.health)
    if refusal.refused:
        return CycleResult(
            status="refused",
            decision="no change",
            incumbent_before=incumbent.name,
            incumbent_after=incumbent.name,
            dry_run=dry_run,
            refusal=refusal,
            gate_verdicts=(),
            band_decision=None,
            refit_note="not run: refusal precedes refit",
            target_emitted=False,
            state_action="none",
        )

    refit_note = "fixed 60/40 parameters revalidated; no estimable signal parameters"
    incumbent_turnover = incumbent.oos_turnover.get(5.0)
    if incumbent_turnover is None:
        raise ValueError("incumbent has no 5 bps turnover evidence")
    incumbent_evidence = PortfolioEvidence(
        name=incumbent.name,
        returns=incumbent.oos_returns,
        turnover=incumbent_turnover,
    )
    verdicts = tuple(
        evaluate_gate(
            challenger.evidence(),
            incumbent_evidence,
            snapshot.risk_free,
            n_resamples=inference_resamples,
        )
        for challenger in challengers
    )

    passing = [verdict for verdict in verdicts if verdict.promote]
    after = incumbent.name
    state_action = "none"
    if approved_promotion is not None:
        matches = [verdict for verdict in passing if verdict.challenger == approved_promotion]
        if len(matches) != 1:
            raise ValueError("explicit promotion must name exactly one gate-passing challenger")
        after = approved_promotion
        state_action = "would replace incumbent" if dry_run else "replace incumbent"
    elif passing:
        state_action = "gate passed; explicit promotion authority absent"

    band_decision = apply_no_trade_band(
        snapshot.ideal_target,
        snapshot.current_weights,
        band=band,
    )
    emitted = bool(emit_targets and not dry_run)
    return CycleResult(
        status="completed",
        decision="no change" if after == incumbent.name else f"promote {after}",
        incumbent_before=incumbent.name,
        incumbent_after=after,
        dry_run=dry_run,
        refusal=refusal,
        gate_verdicts=verdicts,
        band_decision=band_decision,
        refit_note=refit_note,
        target_emitted=emitted,
        state_action=state_action,
    )


def _write_ledger(
    challengers: Sequence[RegisteredChallenger],
    verdicts: Sequence[GateVerdict],
    path: Path,
    *,
    attempts: int = 5,
) -> int:
    """Write each completed challenge once, retrying a concurrent SQLite lock."""
    if len(challengers) != len(verdicts):
        raise ValueError("challenger and verdict counts differ")
    if not challengers:
        return 0
    for attempt in range(attempts):
        try:
            with TrialsLedger(path) as ledger:
                for challenger, verdict in zip(challengers, verdicts, strict=True):
                    primary = challenger.record.oos_returns[5.0]
                    condition = verdict.conditions[0]
                    ledger.record(
                        challenger.study_id,
                        dict(challenger.config),
                        status="evaluated",
                        metrics={
                            "sharpe": verdict.inference[0].bootstrap.sharpe_a,
                            "max_drawdown": metrics.max_drawdown(primary),
                            "ann_turnover": metrics.ann_turnover(
                                challenger.record.oos_turnover[5.0]
                            ),
                            "n_obs": len(primary),
                        },
                        cost_bps=5.0,
                        window="stored stitched OOS",
                        notes=(
                            f"Phase 3 completed challenge; decision={verdict.decision}; "
                            f"condition1_delta_excess_sharpe={condition.observed:+.6f}; "
                            f"journal={challenger.record.journal_entry}"
                        ),
                    )
            return len(challengers)
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower() or attempt + 1 == attempts:
                raise
            time.sleep(0.25 * (attempt + 1))
    return 0


def _journal_text(result: CycleResult, snapshot: CycleSnapshot) -> str:
    lines = [
        f"# {snapshot.health.as_of.isoformat()} — Phase 3 retrain cycle",
        "",
        "Append-only operational record. Not a study.",
        "",
        f"- Status: **{result.status}**",
        f"- Decision: **{result.decision}**",
        f"- Incumbent: `{result.incumbent_before}` -> `{result.incumbent_after}`",
        f"- Data: {snapshot.refresh_note}",
        f"- Refusal: {result.refusal.summary}",
        f"- Refit: {result.refit_note}",
        f"- Targets emitted: {result.target_emitted}",
        f"- Ledger rows: {result.ledger_rows}",
        f"- Paper submission: {result.paper_submission}",
        f"- Paper orders: {result.paper_order_count}",
        f"- Integrity target scope: {', '.join(snapshot.integrity_target_symbols) or 'none'}",
        f"- Store-wide INVESTIGATE baseline: {snapshot.store_wide_investigate_baseline}",
        "- Store-wide INVESTIGATE tickers: "
        + (", ".join(snapshot.store_wide_investigate_tickers) or "none"),
    ]
    if result.band_decision is not None:
        lines.extend(
            [
                f"- No-trade band: {result.band_decision.band:.1%}",
                "- Bounded-target reference one-cycle turnover: "
                f"{result.band_decision.one_way_turnover:.6f}",
                "- Bounded-target reference annualized turnover: "
                f"{result.band_decision.annualized_turnover:.3f}x "
                f"({result.band_decision.turnover_budget_status})",
            ]
        )
    if result.submitted_one_way_turnover is not None:
        lines.extend(
            [
                "- Realized one-cycle turnover (submitted notional / account equity): "
                f"{result.submitted_one_way_turnover:.6f}",
                "- Submitted notional: "
                f"{result.submitted_notional:.2f}",
                "- Realized annualized turnover: "
                f"{result.submitted_one_way_turnover * 252:.3f}x",
            ]
        )
    if result.gate_verdicts:
        lines.extend(["", "## Completed challenges", ""])
        for verdict in result.gate_verdicts:
            failed = ", ".join(verdict.failed) or "none"
            lines.append(
                f"- `{verdict.challenger}`: {verdict.decision}; failed conditions: {failed}"
            )
    return "\n".join(lines) + "\n"


def _next_journal_path(directory: Path, as_of: date) -> Path:
    stamp = datetime.now().strftime("%H%M%S")
    path = directory / f"{as_of.isoformat()}-phase3-cycle-{stamp}.md"
    counter = 1
    while path.exists():
        path = directory / f"{as_of.isoformat()}-phase3-cycle-{stamp}-{counter}.md"
        counter += 1
    return path


def execute_cycle(
    snapshot: CycleSnapshot,
    store: IncumbentStore,
    challengers: Sequence[RegisteredChallenger] = (),
    *,
    dry_run: bool = True,
    emit_targets: bool = False,
    band: float = DEFAULT_BAND,
    approved_promotion: str | None = None,
    promotion_journal: str | None = None,
    ledger_path: Path = DEFAULT_LEDGER,
    journal_dir: Path = DEFAULT_JOURNAL_DIR,
    inference_resamples: int = 10_000,
    submit_paper: bool = False,
    paper_broker: PaperBroker | None = None,
    max_order_notional: float = DEFAULT_MAX_ORDER_NOTIONAL,
    drift_path: Path = DEFAULT_DRIFT_LOG,
) -> CycleResult:
    """Run a cycle and, only outside dry-run, commit its audit records."""
    cycle_start = _utc_rfc3339(snapshot.decision_timestamp)
    if submit_paper and dry_run:
        raise ValueError("paper submission requires a non-dry-run cycle")
    if submit_paper and not emit_targets:
        raise ValueError("paper submission requires explicit target emission")
    if store.exists:
        incumbent = store.load()
        initial_state_action = "loaded incumbent"
    else:
        incumbent = snapshot.seeded_incumbent
        initial_state_action = "would initialize balanced incumbent" if dry_run else "initialize"
    if submit_paper and incumbent.name != BALANCED_NAME:
        raise ValueError("paper submission is restricted to the declared balanced-60-40 incumbent")

    result = run_cycle(
        snapshot,
        incumbent,
        challengers,
        dry_run=dry_run,
        emit_targets=emit_targets,
        band=band,
        approved_promotion=approved_promotion,
        inference_resamples=inference_resamples,
    )
    if result.state_action == "none":
        result = replace(result, state_action=initial_state_action)
    if dry_run:
        return result

    if submit_paper and paper_broker is not None:
        paper_broker.reconcile_drift_log(
            drift_path,
            cycle_start=cycle_start,
            record_sink=lambda record: append_drift_record(drift_path, record),
        )

    if not store.exists:
        store.initialize(incumbent)
    ledger_rows = _write_ledger(challengers, result.gate_verdicts, ledger_path)

    if approved_promotion is not None and result.incumbent_after == approved_promotion:
        selected = [item.record for item in challengers if item.record.name == approved_promotion]
        if len(selected) != 1 or promotion_journal is None:
            raise ValueError("promotion requires one named challenger and --promotion-journal")
        store.replace(selected[0], journal_entry=promotion_journal)

    result = replace(result, ledger_rows=ledger_rows)

    if submit_paper:
        if result.refusal.refused:
            result = replace(result, paper_submission="blocked by Phase 3 refusal")
        elif result.band_decision is None:
            result = replace(result, paper_submission="blocked: no bounded target")
        elif paper_broker is None:
            raise ValueError("paper submission requires a paper broker")
        else:
            try:
                submission = paper_broker.submit_rebalance(
                    target_weights={
                        str(symbol): float(weight)
                        for symbol, weight in snapshot.ideal_target.items()
                    },
                    decision_close={
                        str(symbol): float(close)
                        for symbol, close in snapshot.decision_close.items()
                    },
                    decision_timestamp=snapshot.decision_timestamp.isoformat(),
                    phase3_refused=False,
                    band=band,
                    max_order_notional=max_order_notional,
                    record_sink=lambda record: append_drift_record(drift_path, record),
                )
            except PaperSubmissionRefused as error:
                result = replace(result, paper_submission=str(error))
            else:
                result = replace(
                    result,
                    paper_submission=(
                        "submitted to Alpaca Paper; costs are lower bounds and "
                        "IEX spreads are upward-biased"
                    ),
                    paper_order_count=len(submission.records),
                    submitted_notional=submission.submitted_notional,
                    submitted_one_way_turnover=submission.submitted_one_way_turnover,
                )
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal_path = _next_journal_path(journal_dir, snapshot.health.as_of)
    journal_path.write_text(_journal_text(result, snapshot))
    return replace(result, journal_path=journal_path)


def format_result(result: CycleResult, *, include_targets: bool = False) -> str:
    """Human-readable stdout; target weights stay hidden without explicit consent."""
    lines = [
        "=== PHASE 3 RETRAIN CYCLE ===",
        f"mode: {'DRY RUN' if result.dry_run else 'EXECUTE'}",
        f"status: {result.status}",
        f"decision: {result.decision}",
        f"incumbent: {result.incumbent_before} -> {result.incumbent_after}",
        f"refusal: {result.refusal.summary}",
        f"refit: {result.refit_note}",
        f"state: {result.state_action}",
        f"completed challengers: {len(result.gate_verdicts)}",
        f"paper submission: {result.paper_submission}",
    ]
    if result.band_decision is not None:
        lines.extend(
            [
                f"band: {result.band_decision.band:.1%}",
                f"annualized turnover: {result.band_decision.annualized_turnover:.3f}x "
                f"({result.band_decision.turnover_budget_status})",
            ]
        )
        if include_targets:
            target = json.dumps(result.band_decision.bounded_target.to_dict())
            lines.append("bounded target: " + target)
        else:
            lines.append("target: suppressed (use --emit-targets with --execute)")
    else:
        lines.append("target: none")
    lines.extend(
        [
            f"target emitted: {result.target_emitted}",
            f"ledger rows written: {result.ledger_rows}",
            f"journal: {result.journal_path or 'not written in dry-run'}",
            "FINAL: no change" if result.decision == "no change" else f"FINAL: {result.decision}",
        ]
    )
    return "\n".join(lines)
