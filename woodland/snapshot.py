"""Explicit research cutoff and content provenance; never writes market data."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from woodland.config import ROOT, all_tickers, load_config


class ResearchSnapshotHashMismatchError(RuntimeError):
    """The configured ETF research artifact no longer matches its content hash."""


FREEZE_TIME_ANCHORS_FILE = "freeze-time-anchors.json"


def research_as_of() -> str:
    return str(load_config()["data"]["as_of"])


def bound_frame(frame: pd.DataFrame) -> pd.DataFrame:
    index = pd.DatetimeIndex(frame.index)
    end = pd.Timestamp(research_as_of())
    if index.tz is not None:
        end = end.tz_localize(index.tz)
    return frame.loc[index.normalize() <= end]


def frame_hash(frame: pd.DataFrame) -> str:
    """SHA256 of sorted ISO-date CSV, ordered labels, %.17g values, explicit NA."""
    raw = frame.sort_index().to_csv(
        date_format="%Y-%m-%d", float_format="%.17g", na_rep="NA", lineterminator="\n"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _etf_snapshot_record(cfg: dict, store: Path) -> dict:
    symbols = all_tickers(cfg)
    for symbol in symbols:
        verify_pinned_input(store / f"{symbol}.parquet")
    frame = pd.DataFrame(
        {s: pd.read_parquet(store / f"{s}.parquet")["adj_close"] for s in symbols}
    ).sort_index()
    frame = bound_frame(frame).loc[cfg["data"]["start"] :]
    return dict(
        as_of=research_as_of(),
        sha256=frame_hash(frame),
        field="adj_close",
        hash_format="sorted date-index CSV; ordered config columns; %.17g; NA; LF; UTF-8",
        first=str(frame.index[0].date()),
        last=str(frame.index[-1].date()),
        rows=len(frame),
        columns=symbols,
    )


def _assert_research_snapshot_hash(observed: str, expected: str) -> None:
    if observed != expected:
        raise ResearchSnapshotHashMismatchError(
            "configured ETF research snapshot hash mismatch: "
            f"expected {expected}, observed {observed}; refuse research read"
        )


def etf_snapshot() -> dict:
    """Return the configured ETF snapshot only after validating its full content hash."""
    cfg = load_config()
    record = _etf_snapshot_record(cfg, ROOT / cfg["data"]["store"])
    expected = str(cfg["data"]["research_snapshot_sha256"])
    _assert_research_snapshot_hash(str(record["sha256"]), expected)
    return record


def verify_research_store(store: Path) -> None:
    """Verify every research read that resolves to the configured ETF store."""
    cfg = load_config()
    configured = (ROOT / cfg["data"]["store"]).resolve()
    if Path(store).resolve() == configured:
        etf_snapshot()


def emit_freeze_time_anchors(
    snapshot_dir: Path,
    *,
    snapshot: Mapping[str, Any],
    anchors: Sequence[Mapping[str, Any]],
) -> Path:
    """Persist the exact anchor registry with a snapshot at freeze time.

    A content-addressed snapshot is incomplete without the reference values
    needed to reproduce it.  The writer never replaces an existing manifest:
    a repeat call must be byte-for-structure identical.
    """
    snapshot_dir = Path(snapshot_dir)
    expected_dir = f"etf-{snapshot['sha256']}"
    if snapshot_dir.name != expected_dir:
        raise ValueError(
            f"snapshot directory {snapshot_dir.name!r} does not match {expected_dir!r}"
        )
    payload = {
        "snapshot": dict(snapshot),
        "anchors": [dict(anchor) for anchor in anchors],
    }
    path = snapshot_dir / FREEZE_TIME_ANCHORS_FILE
    if path.exists():
        existing = json.loads(path.read_text())
        if existing != payload:
            raise ValueError(f"freeze-time anchors already differ at {path}")
        return path
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_pinned_input(path: Path) -> None:
    """Refuse changed repo-owned ignored study inputs before parsing them.

    Temporary test fixtures outside the repository have no historical pin.
    """
    try:
        relative = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return
    pins = load_config()["data"].get("pinned_input_sha256", {})
    if relative not in pins:
        raise ResearchSnapshotHashMismatchError(
            f"refused: no SHA-256 pin for study input {relative}"
        )
    expected = str(pins[relative])
    observed = file_hash(Path(path))
    if observed != expected:
        raise ResearchSnapshotHashMismatchError(
            f"refused: study input SHA-256 mismatch for {relative}: "
            f"expected {expected}, observed {observed}"
        )


def refuse_pinned_write(path: Path) -> None:
    """Keep configured research inputs immutable; rebuilds need a new path."""
    destination = Path(path).resolve()
    cfg = load_config()["data"]
    factors = "fama_french_factors_daily.parquet"
    pinned_factors = {
        (ROOT / "data" / factors).resolve(),
        (ROOT / cfg["store"] / factors).resolve(),
    }
    try:
        relative = destination.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return
    if relative not in cfg.get("pinned_input_sha256", {}) and destination not in pinned_factors:
        return
    raise ResearchSnapshotHashMismatchError(
        f"refused: {relative} is hash-pinned; write the rebuild to a new path"
    )
