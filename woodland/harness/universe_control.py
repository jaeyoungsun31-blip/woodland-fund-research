"""Signed configuration and preflight for the xsmom-v16 universe control."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from woodland.harness import costaware_panel
from woodland.harness.ledger import TrialsLedger
from woodland.snapshot import etf_snapshot, file_hash, verify_pinned_input

ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "xsmom-v16-universe-control-20260909"
MANIFEST = ROOT / "reports/defect-excluded-universe-2026-09-09/universe.csv"
MANIFEST_SHA256 = "25d65a86c5f26fa8d68e331b39d5f46e7bc1af270765ef0eba3531194b36dbcd"
PANEL = (
    ROOT
    / "reports/security-resolver/2026-09-07-constituent-panel"
    / "panel-returns-a2-favourable.parquet"
)
OUT = ROOT / "reports/xsmom-v16-universe-control"
COSTS: tuple[float, ...] = (0.0, 5.0, 10.0, 25.0)
G1_N_TRIALS = 80
# Amendment 1 (2026-09-09) declares G2 as penalized@25 minus momentum@25.
G2_COST_BPS = 25.0
MEMBERSHIP = (
    ROOT
    / "reports/security-resolver/2026-09-07-constituent-panel"
    / "membership-mask.parquet"
)


@contextmanager
def configured_costaware() -> Iterator[None]:
    """Apply the signed single-arm engine settings, then restore the engine."""
    old_out, old_costs, old_panel, old_eligibility = (
        costaware_panel.OUT,
        costaware_panel.COSTS,
        costaware_panel.PANEL,
        costaware_panel.eligibility,
    )
    try:
        costaware_panel.OUT = OUT
        OUT.mkdir(parents=True, exist_ok=True)
        costaware_panel.COSTS = COSTS
        costaware_panel.PANEL = PANEL
        verify_pinned_input(MEMBERSHIP)
        membership = pd.read_parquet(MEMBERSHIP)
        costaware_panel.eligibility = costaware_panel.declared_membership_eligibility(membership)
        yield
    finally:
        costaware_panel.OUT = old_out
        costaware_panel.COSTS = old_costs
        costaware_panel.PANEL = old_panel
        costaware_panel.eligibility = old_eligibility


def load_panel() -> pd.DataFrame:
    """Read the signed universe exactly, refusing a changed manifest."""
    if file_hash(MANIFEST) != MANIFEST_SHA256:
        raise RuntimeError("refused: frozen universe manifest SHA-256 mismatch")
    manifest = pd.read_csv(MANIFEST, dtype={"symbol": str})
    required = {"symbol", "excluded", "reason"}
    if set(manifest.columns) != required:
        raise RuntimeError("refused: frozen universe manifest columns changed")
    symbols = manifest.loc[
        manifest.excluded.astype(str).str.casefold() != "true", "symbol"
    ].tolist()
    if len(symbols) != 915 or len(set(symbols)) != 915:
        raise RuntimeError("refused: frozen universe must contain 915 unique included symbols")
    verify_pinned_input(PANEL)
    panel = pd.read_parquet(PANEL)
    if set(symbols) - set(panel.columns):
        raise RuntimeError("refused: frozen universe contains absent panel symbols")
    return panel.loc[:, symbols]


def preflight() -> dict[str, Any]:
    """Validate frozen inputs and ensure the declared study ID is unused."""
    with TrialsLedger(ROOT / "journal/trials.db") as ledger:
        rows = ledger.n_trials(STUDY_ID, distinct=False)
    if rows:
        raise RuntimeError("refused: declared study ID already has ledger rows")
    panel = load_panel()
    return {
        "status": "validated_no_fit",
        "study_id": STUDY_ID,
        "symbols": int(panel.shape[1]),
        "ledger_rows": rows,
    }


def execute() -> dict[str, Any]:
    """Run only after separate authorization from the operator."""
    panel = load_panel()
    with configured_costaware():
        # Sections 5 and 6 of the signed 2026-09-09 pre-registration authorize
        # this external count over deflated.py's ledger-derived default guidance.
        return costaware_panel.execute(
            panel,
            "universe-control",
            etf_snapshot(),
            study_id=STUDY_ID,
            dsr_n_trials=G1_N_TRIALS,
            momentum_gate_cost_bps=G2_COST_BPS,
            positive_gate=True,
        )
