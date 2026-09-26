from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from woodland.harness.dual_panel import (
    ARMS,
    ArmEvidence,
    build_arms,
    evaluate_gate,
    execute_all,
    load_frozen_subset,
    require_anchor_ruling,
)


def test_anchor_ruling_uses_the_repo_published_precision_record() -> None:
    ruling = require_anchor_ruling()
    assert ruling["basis"] == (
        "published precision (half-last-digit at each anchor's declared precision)"
    )
    assert ruling["tolerance"] != "1e-3"


def test_frozen_subset_load_is_not_derived_from_other_inputs(tmp_path: Path) -> None:
    path = tmp_path / "cleared.csv"
    rows = [f"S{i},true" for i in range(220)] + ["EXCLUDED,false"]
    path.write_text("symbol,cleared\n" + "\n".join(rows) + "\n")
    assert load_frozen_subset(path) == [f"S{i}" for i in range(220)]
    path.write_text("symbol,cleared\nS0,true\n")
    with pytest.raises(ValueError, match="220"):
        load_frozen_subset(path)


def test_all_four_arms_construct_with_shared_dates(tmp_path: Path) -> None:
    root = tmp_path
    panel_dir = root / "reports/security-resolver/2026-09-07-constituent-panel"
    subset_dir = root / "reports/cleared-subset-2026-09-07"
    panel_dir.mkdir(parents=True)
    subset_dir.mkdir(parents=True)
    index = pd.date_range("2020-01-01", periods=2, freq="B")
    favourable = pd.DataFrame(0.0, index=index, columns=[f"S{i}" for i in range(942)])
    adverse = favourable.copy()
    for i in range(8):
        adverse[f"BK{i}"] = -1.0
    favourable.to_parquet(panel_dir / "panel-returns-a2-favourable.parquet")
    adverse.to_parquet(panel_dir / "panel-returns-a2-adverse.parquet")
    subset_dir.joinpath("cleared-subset.csv").write_text(
        "symbol,cleared\n" + "\n".join(f"S{i},true" for i in range(220)) + "\n"
    )
    arms = build_arms(root, subset_dir / "cleared-subset.csv")
    assert set(arms) == set(ARMS)
    assert {name: panel.shape for name, panel in arms.items()} == {
        "A": (2, 220), "B": (2, 220), "C": (2, 942), "D": (2, 950),
    }
    assert all(panel.index.equals(index) for panel in arms.values())


def test_acceptance_gate_requires_agreement_and_all_inherited_gates() -> None:
    agree = {arm: ArmEvidence(0.2, -0.1, 0.3, True) for arm in ARMS}
    assert evaluate_gate(agree)["promotion_eligible"]
    disagree = dict(agree, D=ArmEvidence(-0.2, -0.3, 0.1, True))
    assert not evaluate_gate(disagree)["agreement"]
    failed = dict(agree, B=ArmEvidence(0.2, -0.1, 0.3, False))
    assert not evaluate_gate(failed)["promotion_eligible"]


def test_anchor_ruling_refuses_without_explicit_record(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "journal").mkdir()
    with pytest.raises(RuntimeError, match="no recorded ETF anchor ruling"):
        require_anchor_ruling(tmp_path)
    (tmp_path / "config/etf-anchor-ruling.json").write_text(json.dumps({
        "decision": "accept-under-declared-tolerance", "tolerance": 0.001,
    }))
    assert require_anchor_ruling(tmp_path)["tolerance"] == 0.001


def test_execute_refuses_before_any_arm_without_signed_ruling(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    (tmp_path / "journal").mkdir()
    with pytest.raises(RuntimeError, match="no recorded ETF anchor ruling"):
        execute_all(tmp_path)
