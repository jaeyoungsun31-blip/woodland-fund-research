from __future__ import annotations

import pytest

from woodland import data
from woodland.config import ROOT, all_tickers, load_config
from woodland.snapshot import (
    ResearchSnapshotHashMismatchError,
    _assert_research_snapshot_hash,
    etf_snapshot,
)


def test_configured_snapshot_hash_is_verified_before_research_use() -> None:
    config = load_config()
    snapshot = ROOT / config["data"]["store"]
    if not snapshot.exists():
        pytest.skip(
            f"gitignored ETF snapshot {snapshot.name} is absent (rebuild with scripts/ingest.py)"
        )
    assert snapshot.is_dir()
    assert (snapshot / f"{all_tickers(config)[0]}.parquet").is_file()
    assert etf_snapshot()["sha256"] == config["data"]["research_snapshot_sha256"]


def test_snapshot_hash_mismatch_refuses_research_read(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_config()
    snapshot = ROOT / config["data"]["store"]
    expected = str(config["data"]["research_snapshot_sha256"])

    with pytest.raises(ResearchSnapshotHashMismatchError, match="refuse research read"):
        _assert_research_snapshot_hash("not-the-registered-content", expected)

    def fail_if_guarded(_store: object) -> None:
        raise ResearchSnapshotHashMismatchError("refuse research read")

    monkeypatch.setattr("woodland.snapshot.verify_research_store", fail_if_guarded)
    with pytest.raises(ResearchSnapshotHashMismatchError, match="refuse research read"):
        data.build_matrix(["SPY"], snapshot)
