"""Validate-only wiring for the signed xsmom-v16 four-arm study.

This module deliberately contains no fitting or execution path.  It assembles
the preregistered arms and evaluates gates only after a future all-arm result
artifact is supplied.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from woodland import cash, stats
from woodland.harness import costaware_panel
from woodland.snapshot import etf_snapshot, verify_pinned_input

ROOT = Path(__file__).resolve().parents[2]
PANEL_DIR = ROOT / "reports/security-resolver/2026-09-07-constituent-panel"
SUBSET = ROOT / "reports/cleared-subset-2026-09-07/cleared-subset.csv"
ARMS = ("A", "B", "C", "D")
DUAL_COSTS = (0.0, 5.0, 10.0, 25.0)
DUAL_OUT = ROOT / "reports/xsmom-v16-dual-run"


@dataclass(frozen=True)
class ArmEvidence:
    """Primary-effect inference and inherited-gate outcome for one completed arm."""

    primary_effect: float
    ci_low: float
    ci_high: float
    inherited_gate_pass: bool


def load_frozen_subset(path: Path = SUBSET) -> list[str]:
    """Load, never re-derive, the planning-produced cleared subset."""
    frame = pd.read_csv(path, dtype={"symbol": str})
    required = {"symbol", "cleared"}
    if missing := required - set(frame.columns):
        raise ValueError(f"frozen subset missing columns: {sorted(missing)}")
    if frame.symbol.duplicated().any():
        raise ValueError("frozen subset contains duplicate symbols")
    cleared = frame.loc[frame.cleared.astype(str).str.casefold() == "true", "symbol"].tolist()
    if len(cleared) != 220:
        raise ValueError(f"frozen subset must contain 220 symbols, got {len(cleared)}")
    return cleared


def build_arms(root: Path = ROOT, subset_path: Path = SUBSET) -> dict[str, pd.DataFrame]:
    """Assemble all four panels without computing any signal, fit, or return."""
    panel_dir = root / "reports/security-resolver/2026-09-07-constituent-panel"
    favourable_path = panel_dir / "panel-returns-a2-favourable.parquet"
    adverse_path = panel_dir / "panel-returns-a2-adverse.parquet"
    verify_pinned_input(favourable_path)
    verify_pinned_input(adverse_path)
    favourable = pd.read_parquet(favourable_path)
    adverse = pd.read_parquet(adverse_path)
    if not favourable.index.equals(adverse.index):
        raise ValueError("A2 favourable and adverse dates do not reconcile")
    if favourable.shape[1] != 942 or adverse.shape[1] != 950:
        raise ValueError("unexpected A2 panel universe sizes; refusing stale or changed artifacts")
    subset = load_frozen_subset(subset_path)
    missing = set(subset) - set(favourable.columns)
    if missing:
        raise ValueError(f"frozen subset symbols absent from panel: {sorted(missing)}")
    arms = {
        "A": favourable.loc[:, subset],
        "B": adverse.reindex(columns=subset),
        "C": favourable,
        "D": adverse,
    }
    dates_reconcile = all(panel.index.equals(favourable.index) for panel in arms.values())
    if set(arms) != set(ARMS) or not dates_reconcile:
        raise AssertionError("four-arm date indices do not reconcile")
    return arms


def _anchor_ruling(root: Path) -> dict[str, Any] | None:
    """Select the one active, explicit anchor-ruling record."""
    config_dir = root / "config"
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in config_dir.glob("*anchor*ruling*.json"):
        record = json.loads(path.read_text())
        records.append((path, record))
    if not records:
        return None
    superseded = {
        str(record.get("supersedes")) for _, record in records if record.get("supersedes")
    }
    active = [
        (path, record)
        for path, record in records
        if str(path.relative_to(root)) not in superseded
    ]
    if len(active) != 1:
        raise RuntimeError("refused: anchor ruling selection is ambiguous")
    path, record = active[0]
    decision = str(record.get("decision", "")).casefold()
    if decision != "accept-under-declared-tolerance" or record.get("tolerance") is None:
        raise RuntimeError("refused: active anchor ruling is incomplete")
    return {"source": str(path.relative_to(root)), **record}


def require_anchor_ruling(root: Path = ROOT) -> dict[str, Any]:
    """Mechanical execution gate required by dual-run preregistration clause 5."""
    ruling = _anchor_ruling(root)
    if ruling is None:
        raise RuntimeError(
            "refused: no recorded ETF anchor ruling with declared tolerance or re-anchor"
        )
    return ruling


def disclosure(arms: dict[str, pd.DataFrame], root: Path = ROOT) -> dict[str, Any]:
    """Mandatory data-quality disclosure, populated without fitting an arm."""
    summary_path = (root / "reports/security-resolver/2026-09-07-constituent-panel"
                    / "panel-summary.json")
    verify_pinned_input(summary_path)
    construction = json.loads(summary_path.read_text())["construction"]
    full_symbols = set(arms["C"].columns)
    crosscheck_path = root / "reports/security-resolver/2026-09-07-tiingo-crosscheck/crosscheck.csv"
    verify_pinned_input(crosscheck_path)
    checked = pd.read_csv(crosscheck_path)
    checked = checked[checked.symbol.isin(full_symbols)]
    independently_compared = int((checked.status == "compared").sum())
    subset = load_frozen_subset(root / "reports/cleared-subset-2026-09-07/cleared-subset.csv")
    return {
        "symbols_cleared": {"cleared": len(subset), "total": len(full_symbols)},
        "a2": {
            "unclassified_exits": construction["a2_coverage"]["unclassified"],
            "total_exits": construction["a2_coverage"]["exits_total"],
            "coverage": construction["a2_coverage"],
        },
        "independent_crosscheck": {
            "compared": independently_compared,
            "total": len(full_symbols),
            "coverage_skew": "The un-compared population is delisted-skewed; Tiingo cannot "
                             "independently check the half of the panel most exposed to exits.",
        },
        "universe_asymmetry": {
            "favourable_columns": int(arms["C"].shape[1]),
            "adverse_columns": int(arms["D"].shape[1]),
            "statement": "The adverse panel has eight additional Case 2 absent-name columns; "
                         "they do not exist under the favourable bound.",
        },
        "prior_trials": {
            "execution": "2026-09-08 22:34 five-bps execution",
            "study_id_template": "xsmom-v16-panel-dual-v3-<arm>-20260907",
            "cost_bps": [5],
            "distinct_configurations_per_arm": 16,
            "raw_rows_per_arm": 352,
            "treatment": "disclosed prior trial; not counted as this study's result",
        },
        "phantom_trials": {
            "execution": "2026-09-09 03:08 arm-A attempt",
            "study_id": "xsmom-v16-panel-dual-v4-A-20260909",
            "status_recorded": "evaluated",
            "raw_rows": 352,
            "distinct_configurations": 16,
            "oos_result": "none; disclosed phantom, not counted as this study's result",
        },
        "known_unresolved_defects": {
            "refused_constituents": 213,
            "refused_symbol_years": 1574,
            "quality_flagged_symbols": 67,
            "volume_flagged_symbols": 25,
            "pending_A2_amendment_1": construction["quarantined"],
            "excluded_panel_defects": ["CTX", "DF", "IGT", "COG"],
        },
    }


def infer_primary_effect(
    candidate: pd.Series, comparator: pd.Series, *, inherited_gate_pass: bool,
    rf_daily: pd.Series | None = None,
) -> tuple[ArmEvidence, dict[str, Any]]:
    """Use the existing bootstrap and Ledoit-Wolf paths for a completed arm."""
    bootstrap = stats.bootstrap_sharpe_difference(candidate, comparator, rf_daily=rf_daily, seed=0)
    hac = stats.ledoit_wolf_sharpe_test(candidate, comparator, rf_daily=rf_daily)
    evidence = ArmEvidence(bootstrap.difference, bootstrap.ci_low, bootstrap.ci_high,
                           inherited_gate_pass)
    return evidence, {"bootstrap": asdict(bootstrap), "hac": asdict(hac)}


def evaluate_gate(evidence: dict[str, ArmEvidence]) -> dict[str, Any]:
    """Acceptance-standard agreement plus all-arm inherited promotion gate."""
    if set(evidence) != set(ARMS):
        raise ValueError(f"must evaluate all four arms exactly: {ARMS}")
    values = list(evidence.values())
    signs = {int(np.sign(item.primary_effect)) for item in values}
    common_low = max(item.ci_low for item in values)
    common_high = min(item.ci_high for item in values)
    agreement = len(signs) == 1 and common_low <= common_high
    inherited_all_pass = all(item.inherited_gate_pass for item in values)
    return {
        "agreement": agreement,
        "same_sign": len(signs) == 1,
        "confidence_intervals_overlap": common_low <= common_high,
        "common_confidence_interval": [common_low, common_high],
        "inherited_gate_all_arms": inherited_all_pass,
        "promotion_eligible": agreement and inherited_all_pass,
    }


def validate(root: Path = ROOT, subset_path: Path = SUBSET) -> dict[str, Any]:
    """Validate four-arm wiring and stop at the fit boundary unconditionally."""
    arms = build_arms(root, subset_path)
    return {
        "status": "validated_no_fit",
        "arms": {name: {"dates": int(len(panel)), "symbols": int(panel.shape[1])}
                 for name, panel in arms.items()},
        "disclosure": disclosure(arms, root),
        "anchor_ruling": _anchor_ruling(root),
        "execution_refused": _anchor_ruling(root) is None,
        "fit_boundary_reached": True,
    }


def _run_directory(root: Path) -> Path:
    return root / "reports/xsmom-v16-dual-run"


def v5_study_id(arm: str) -> str:
    """Fresh ledger namespace; prior v3 rows remain immutable evidence."""
    if arm not in ARMS:
        raise ValueError(f"unknown dual-run arm: {arm}")
    return f"xsmom-v16-panel-dual-v5-{arm}-20260909"


def _start_run(root: Path) -> tuple[Path, str]:
    """Create a fresh run identity and remove only stale generated artifacts."""
    run_dir = _run_directory(root)
    arms_dir = run_dir / "arms"
    arms_dir.mkdir(parents=True, exist_ok=True)
    run_id_path = run_dir / "run_id"
    # The v2 abandoned-launch identifier is not evidence of a completed arm.
    if run_id_path.exists():
        run_id_path.unlink()
    for arm in ARMS:
        stale = arms_dir / f"dual-{arm}"
        if stale.exists():
            shutil.rmtree(stale)
    for staged in arms_dir.glob(".tmp-*"):
        if staged.is_dir():
            shutil.rmtree(staged)
    run_id = str(uuid.uuid4())
    run_id_path.write_text(f"{run_id}\n")
    return run_dir, run_id


def _stamp_completion(path: Path, run_id: str) -> None:
    """Put the run identity beside an arm's contents before atomic promotion."""
    (path / "run_id").write_text(f"{run_id}\n")
    summary_path = path / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary["run_id"] = run_id
    summary_path.write_text(json.dumps(summary, indent=2, default=str))


def _feature_containment_disclosure(
    arms: dict[str, pd.DataFrame], root: Path
) -> dict[str, Any]:
    """Audit the adverse terminal-return infinity boundary without scoring arms."""
    membership_path = (
        root / "reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet"
    )
    verify_pinned_input(membership_path)
    membership = pd.read_parquet(membership_path)
    warmup_days = dict(zip(costaware_panel.model.FEATURES, (251, 20, 4, 62, 82, 251), strict=True))
    arm_counts: dict[str, dict[str, int]] = {}
    for arm, panel in arms.items():
        eligible = membership.reindex(index=panel.index, columns=panel.columns, fill_value=False)
        eligible_array = eligible.to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            features = costaware_panel.model.features(panel, eligible)
            log_returns = np.log1p(panel.to_numpy())
        eligible_cells = np.broadcast_to(eligible_array[..., None], features.shape)
        infinite_eligible = int((np.isinf(features) & eligible_cells).sum())

        warmup = np.zeros(features.shape, dtype=bool)
        for column in range(eligible_array.shape[1]):
            starts = np.flatnonzero(
                eligible_array[:, column] & np.r_[True, ~eligible_array[:-1, column]]
            )
            ends = np.flatnonzero(
                eligible_array[:, column] & np.r_[~eligible_array[1:, column], True]
            )
            for start, end in zip(starts, ends, strict=True):
                for feature, days in enumerate(warmup_days.values()):
                    warmup[start : min(start + days, end + 1), column, feature] = True
        nonfinite = ~np.isfinite(features) & eligible_cells
        terminal = np.isneginf(log_returns)
        escaped_terminal_contamination = 0
        for date, symbol in zip(*np.nonzero(terminal), strict=True):
            escaped_terminal_contamination += int(eligible_array[date:, symbol].sum())
        arm_counts[arm] = {
            "infinite_eligible_feature_cells": infinite_eligible,
            "nan_eligible_feature_cells": int((np.isnan(features) & eligible_cells).sum()),
            "nan_warmup_feature_cells": int((nonfinite & warmup).sum()),
            "nan_residual_feature_cells": int((nonfinite & ~warmup).sum()),
            "terminal_contamination_in_eligible_cells": escaped_terminal_contamination,
        }
    invalid = {
        arm: values
        for arm, values in arm_counts.items()
        if values["infinite_eligible_feature_cells"]
        or values["terminal_contamination_in_eligible_cells"]
    }
    if invalid:
        raise RuntimeError(f"refused: adverse terminal-return containment failed: {invalid}")
    return {
        "adverse_bound": "-inf log-returns by construction; contained to ineligible cells",
        "feature_warmup_eligible_days": warmup_days,
        "arms": arm_counts,
    }


def completed_report(root: Path = ROOT) -> dict[str, Any]:
    """Return completed-arm artifacts only when the sealed-run gate is satisfied."""
    run_dir = _run_directory(root)
    run_id_path = run_dir / "run_id"
    if not run_id_path.is_file():
        raise RuntimeError("refused: no run_id for dual-run report")
    run_id = run_id_path.read_text().strip()
    if not run_id:
        raise RuntimeError("refused: empty run_id for dual-run report")
    arms: list[dict[str, Any]] = []
    for arm in ARMS:
        path = run_dir / "arms" / f"dual-{arm}"
        if not path.is_dir():
            raise RuntimeError(f"refused: arm {arm} is not atomically completed")
        completion_id = path / "run_id"
        summary_path = path / "summary.json"
        if not completion_id.is_file() or not summary_path.is_file():
            raise RuntimeError(f"refused: arm {arm} lacks completion identity")
        if completion_id.read_text().strip() != run_id:
            raise RuntimeError(f"refused: arm {arm} belongs to another run_id")
        summary = json.loads(summary_path.read_text())
        if summary.get("run_id") != run_id:
            raise RuntimeError(f"refused: arm {arm} summary belongs to another run_id")
        arms.append(summary)
    report_path = run_dir / "summary.json"
    if not report_path.is_file():
        raise RuntimeError("refused: sealed arm directories lack a combined report artifact")
    report = cast(dict[str, Any], json.loads(report_path.read_text()))
    if report.get("run_id") != run_id:
        raise RuntimeError("refused: combined report belongs to another run_id")
    assembled_arms = build_arms(root)
    report["disclosure"]["feature_containment"] = _feature_containment_disclosure(
        assembled_arms, root
    )
    report["disclosure"]["nonfinite_train_excess_sharpe_guard"] = {
        arm["arm"]: arm["status"] == "completed" for arm in arms
    }
    return report


def execute_all(root: Path = ROOT, subset_path: Path = SUBSET) -> dict[str, Any]:
    """Run the four signed arms sequentially and atomically promote each one.

    This deliberately delegates fitting, costs, baselines, folds, and the
    inherited criteria to the already-preregistered v16 engine.  It changes
    only the supplied panel and uses no per-symbol costs.
    """
    ruling = require_anchor_ruling(root)
    arms = build_arms(root, subset_path)
    expected = (pd.Timestamp("1999-01-06"), pd.Timestamp("2026-06-30"))
    if (arms["A"].index[0], arms["A"].index[-1]) != expected:
        raise ValueError("dual-run panel window differs from the signed window")
    run_dir, run_id = _start_run(root)
    arms_dir = run_dir / "arms"

    # The shared engine's only alternative arm is a diagnostic exclusion mask;
    # these names deliberately avoid it so each supplied panel is the arm.
    old_out, old_costs, old_panel, old_eligibility = (
        costaware_panel.OUT,
        costaware_panel.COSTS,
        costaware_panel.PANEL,
        costaware_panel.eligibility,
    )
    costaware_panel.OUT = arms_dir
    costaware_panel.COSTS = DUAL_COSTS
    costaware_panel.PANEL = (
        root / "reports/security-resolver/2026-09-07-constituent-panel"
        / "panel-returns-a2-favourable.parquet"
    )
    # The dual registration defines population membership wholly by the arm
    # panels.  Do not import the superseded two-arm diagnostic exclusion mask.
    membership_path = (
        root / "reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet"
    )
    verify_pinned_input(membership_path)
    membership = pd.read_parquet(membership_path)

    costaware_panel.eligibility = costaware_panel.declared_membership_eligibility(membership)
    provenance = etf_snapshot()
    outcomes = []
    try:
        for name in ARMS:
            staged = arms_dir / f".tmp-{run_id}-{name}"
            outcome = costaware_panel.execute(
                arms[name],
                f"dual-{name}",
                provenance,
                output_path=staged,
                study_id=v5_study_id(name),
                defer_success_ledger=True,
            )
            if outcome["status"] != "completed":
                raise RuntimeError(f"arm {name} refused; staging directory retained for diagnosis")
            _stamp_completion(staged, run_id)
            completed_path = arms_dir / f"dual-{name}"
            os.rename(staged, completed_path)
            outcome.update(
                costaware_panel.commit_completed_ledger(
                    outcome.pop("_ledger_study"), outcome.pop("_ledger_records")
                )
            )
            summary_path = completed_path / "summary.json"
            summary = json.loads(summary_path.read_text())
            summary.update(
                {"trials": outcome["trials"], "distinct_cells": outcome["distinct_cells"]}
            )
            summary_path.write_text(json.dumps(summary, indent=2, default=str))
            outcomes.append(outcome)
    finally:
        costaware_panel.OUT = old_out
        costaware_panel.COSTS = old_costs
        costaware_panel.PANEL = old_panel
        costaware_panel.eligibility = old_eligibility

    arm_index = pd.DatetimeIndex(arms["A"].index)
    rf, _ = cash.align_risk_free(cash.load_risk_free_daily(root / "data"), arm_index)
    evidence: dict[str, ArmEvidence] = {}
    inference: dict[str, Any] = {}
    for name, outcome in zip(ARMS, outcomes, strict=True):
        path = arms_dir / f"dual-{name}"
        penalized = pd.read_csv(
            path / "penalized-10-returns.csv", index_col=0, parse_dates=True
        )["return"]
        ridge = pd.read_csv(path / "ridge-10-returns.csv", index_col=0, parse_dates=True)["return"]
        momentum = pd.read_csv(
            path / "momentum-25-returns.csv", index_col=0, parse_dates=True
        )["return"]
        c1, c1_detail = infer_primary_effect(
            penalized,
            ridge,
            inherited_gate_pass=bool(outcome["C1"]),
            rf_daily=rf.reindex(penalized.index),
        )
        c2, c2_detail = infer_primary_effect(
            penalized.reindex(momentum.index), momentum, inherited_gate_pass=bool(outcome["C2"]),
            rf_daily=rf.reindex(momentum.index),
        )
        evidence[name] = c1
        inference[name] = {"C1": c1_detail, "C2": c2_detail, "C3": outcome["C3"]}
    report = {
        "status": "completed",
        "run_id": run_id,
        "anchor_ruling": ruling,
        "cost_bps": [0, 5, 10, 25],
        "arms": outcomes,
        "agreement": evaluate_gate(evidence),
        "inference": inference,
        "disclosure": disclosure(arms, root),
    }
    (run_dir / "summary.json").write_text(json.dumps(report, indent=2, default=str))
    return report
