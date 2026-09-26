"""Ignored study inputs must be checked before their contents are read."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest

from woodland import snapshot
from woodland.harness import universe_control


def test_tampered_membership_mask_is_refused_before_read(tmp_path: Path, monkeypatch) -> None:
    relative = "reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    pd.DataFrame({"A": [True]}, index=pd.date_range("2020-01-01", periods=1)).to_parquet(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(snapshot, "load_config", lambda: {
        "data": {"pinned_input_sha256": {relative: digest}}
    })
    monkeypatch.setattr(universe_control, "MEMBERSHIP", path)
    monkeypatch.setattr(universe_control, "OUT", tmp_path / "out")

    with universe_control.configured_costaware():
        pass

    path.write_bytes(path.read_bytes() + b"tampered")
    with (
        pytest.raises(snapshot.ResearchSnapshotHashMismatchError, match="membership-mask.parquet"),
        universe_control.configured_costaware(),
    ):
        pass


def test_unpinned_repository_input_is_refused(tmp_path: Path, monkeypatch) -> None:
    path = tmp_path / "ignored.parquet"
    path.write_bytes(b"some data")
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(snapshot, "load_config", lambda: {
        "data": {"pinned_input_sha256": {}}
    })
    with pytest.raises(snapshot.ResearchSnapshotHashMismatchError, match="no SHA-256 pin"):
        snapshot.verify_pinned_input(path)


def test_snapshot_refuses_raw_parquet_change_outside_adj_close(tmp_path: Path, monkeypatch) -> None:
    relative = "data/snapshots/frozen/SPY.parquet"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    index = pd.date_range("2020-01-01", periods=2)
    prices = pd.DataFrame({"adj_close": [100.0, 101.0], "volume": [10, 11]}, index=index)
    prices.to_parquet(path)
    config = {
        "universe": {"broad": ["SPY"]},
        "data": {
            "store": "data/snapshots/frozen",
            "start": "2020-01-01",
            "as_of": "2020-01-02",
            "research_snapshot_sha256": snapshot.frame_hash(
                pd.DataFrame({"SPY": prices["adj_close"]})
            ),
            "pinned_input_sha256": {relative: hashlib.sha256(path.read_bytes()).hexdigest()},
        },
    }
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(snapshot, "load_config", lambda: config)
    assert snapshot.etf_snapshot()["sha256"] == config["data"]["research_snapshot_sha256"]

    prices["volume"] = [99, 99]
    prices.to_parquet(path)
    with pytest.raises(snapshot.ResearchSnapshotHashMismatchError, match="SPY.parquet"):
        snapshot.etf_snapshot()


def test_panel_builder_refuses_rebuild_over_pinned_artifact(tmp_path: Path, monkeypatch) -> None:
    from scripts import build_constituent_panel

    relative = "reports/security-resolver/panel-returns.parquet"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(b"changed panel")
    monkeypatch.setattr(snapshot, "ROOT", tmp_path)
    monkeypatch.setattr(snapshot, "load_config", lambda: {
        "data": {
            "store": "data/snapshots/frozen",
            "pinned_input_sha256": {relative: hashlib.sha256(b"original panel").hexdigest()},
        }
    })
    monkeypatch.setattr(sys, "argv", [
        "build_constituent_panel.py", "--resolution", str(tmp_path / "missing.jsonl"),
        "--store", str(tmp_path / "store"), "--out", str(path.parent),
        "--a2-census", str(tmp_path / "missing-census.csv"),
        "--a2-classification", str(tmp_path / "missing-classification.csv"),
    ])
    with pytest.raises(snapshot.ResearchSnapshotHashMismatchError, match="write the rebuild"):
        build_constituent_panel.main()
    assert path.read_bytes() == b"changed panel"
