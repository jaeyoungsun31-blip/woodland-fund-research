from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from woodland.harness.costaware_panel import frozen_research_store
from woodland.harness.dual_panel import (
    ARMS,
    DUAL_COSTS,
    SUBSET,
    _start_run,
    completed_report,
    load_frozen_subset,
    v5_study_id,
)
from woodland.harness.ledger import TrialsLedger


def test_v5_uses_a_fresh_study_namespace_and_all_registered_costs() -> None:
    assert DUAL_COSTS == (0.0, 5.0, 10.0, 25.0)
    assert [v5_study_id(arm) for arm in ARMS] == [
        "xsmom-v16-panel-dual-v5-A-20260909",
        "xsmom-v16-panel-dual-v5-B-20260909",
        "xsmom-v16-panel-dual-v5-C-20260909",
        "xsmom-v16-panel-dual-v5-D-20260909",
    ]


def test_baselines_resolve_the_declared_frozen_store(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    (config / "universe.yaml").write_text("data:\n  store: data/snapshots/frozen\n")
    assert frozen_research_store(tmp_path) == tmp_path / "data/snapshots/frozen"


def test_aborted_study_id_is_reusable_but_completed_id_is_not(tmp_path: Path) -> None:
    with TrialsLedger(tmp_path / "trials.db") as ledger:
        ledger.record("dual-v5-A", {"alpha": 1}, status="aborted")
        assert not ledger.has_completed_study("dual-v5-A")
        ledger.record("dual-v5-A", {"alpha": 1}, status="evaluated")
        assert ledger.has_completed_study("dual-v5-A")


def _completed_arm(root: Path, arm: str, run_id: str) -> None:
    path = root / "reports/xsmom-v16-dual-run/arms" / f"dual-{arm}"
    path.mkdir(parents=True)
    (path / "run_id").write_text(f"{run_id}\n")
    (path / "summary.json").write_text(
        json.dumps({"run_id": run_id, "arm": arm, "status": "completed"})
    )


def test_start_run_replaces_stale_identity_and_completed_arms(tmp_path: Path) -> None:
    run_dir = tmp_path / "reports/xsmom-v16-dual-run"
    (run_dir / "arms/dual-A").mkdir(parents=True)
    (run_dir / "run_id").write_text("9b586a78-efc3-4860-8617-4e8a39d7340e\n")
    _, run_id = _start_run(tmp_path)
    assert run_id != "9b586a78-efc3-4860-8617-4e8a39d7340e"
    assert (run_dir / "run_id").read_text().strip() == run_id
    assert not (run_dir / "arms/dual-A").exists()


@pytest.mark.skipif(
    not SUBSET.exists(),
    reason=f"{SUBSET.name} (per-symbol, vendor-derived) is absent; it is excluded from the "
    "public export and gitignored data is not in a fresh clone",
)
def test_report_refuses_missing_or_mismatched_completed_arms(tmp_path: Path) -> None:
    _, run_id = _start_run(tmp_path)
    _completed_arm(tmp_path, "A", run_id)
    with pytest.raises(RuntimeError, match="arm B"):
        completed_report(tmp_path)
    for arm in ARMS[1:]:
        _completed_arm(tmp_path, arm, run_id)
    with pytest.raises(RuntimeError, match="combined report artifact"):
        completed_report(tmp_path)

    # Synthetic panels satisfy the report's containment audit without a study run.
    panel_dir = tmp_path / "reports/security-resolver/2026-09-07-constituent-panel"
    panel_dir.mkdir(parents=True)
    index = pd.bdate_range("2020-01-01", periods=2)
    cleared = load_frozen_subset()
    columns = cleared + [f"SYNTH{i}" for i in range(942 - len(cleared))]
    favourable = pd.DataFrame(0.0, index=index, columns=columns)
    adverse = favourable.reindex(columns=columns + [f"BOUND{i}" for i in range(8)])
    favourable.to_parquet(panel_dir / "panel-returns-a2-favourable.parquet")
    adverse.to_parquet(panel_dir / "panel-returns-a2-adverse.parquet")
    pd.DataFrame(False, index=index, columns=adverse.columns).to_parquet(
        panel_dir / "membership-mask.parquet"
    )
    run_dir = tmp_path / "reports/xsmom-v16-dual-run"
    (run_dir / "summary.json").write_text(json.dumps({"run_id": run_id, "disclosure": {}}))
    report = completed_report(tmp_path)
    assert report["run_id"] == run_id
    assert set(report["disclosure"]["feature_containment"]["arms"]) == set(ARMS)
    (tmp_path / "reports/xsmom-v16-dual-run/arms/dual-D/run_id").write_text("other\n")
    with pytest.raises(RuntimeError, match="another run_id"):
        completed_report(tmp_path)


def test_report_never_uses_staged_directory(tmp_path: Path) -> None:
    _, run_id = _start_run(tmp_path)
    staged = tmp_path / "reports/xsmom-v16-dual-run/arms/.tmp-any-A"
    staged.mkdir()
    (staged / "run_id").write_text(f"{run_id}\n")
    with pytest.raises(RuntimeError, match="arm A"):
        completed_report(tmp_path)
