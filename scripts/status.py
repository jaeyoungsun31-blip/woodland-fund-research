"""Read-only local status summary for Phase 3 cycles and Phase 4 paper drift."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.config import ROOT

DEFAULT_JOURNAL_DIR = ROOT / "journal"
DEFAULT_DRIFT_LOG = ROOT / "data" / "live" / "paper-drift.jsonl"
_CYCLE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-phase3-cycle-(\d{6})(?:-\d+)?\.md$")


def _field(text: str, label: str) -> str:
    match = re.search(rf"^- {re.escape(label)}: (.+)$", text, re.MULTILINE)
    if match is None:
        return "unknown"
    return match.group(1).removeprefix("**").removesuffix("**")


def cycle_journals(directory: Path) -> list[Path]:
    return sorted(
        path for path in directory.glob("*-phase3-cycle-*.md") if _CYCLE_RE.match(path.name)
    )


def cycle_summary(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    refusal = _field(text, "Refusal")
    return (
        f"{path.name[:10]} | status={_field(text, 'Status')} | "
        f"decision={_field(text, 'Decision')} | orders={_field(text, 'Paper orders')} | "
        f"refusal={refusal}"
    )


def _cycle_timestamp(path: Path) -> datetime | None:
    match = _CYCLE_RE.match(path.name)
    if match is None:
        return None
    return datetime.strptime("".join(match.groups()), "%Y-%m-%d%H%M%S").replace(
        tzinfo=ZoneInfo("America/New_York")
    )


def latest_orders(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    latest: dict[str, dict[str, object]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        latest[str(record["order_id"])] = record
    return latest


def _numbers(records: list[dict[str, object]], field: str) -> list[float]:
    return [
        float(value)
        for record in records
        if isinstance((value := record.get(field)), (int, float))
    ]


def _pending_cycles(record: dict[str, object], journals: list[Path]) -> int:
    raw = record.get("recorded_at")
    if not isinstance(raw, str):
        return 0
    recorded_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=UTC)
    return sum(
        stamp is not None and stamp.astimezone(UTC) > recorded_at.astimezone(UTC)
        for journal in journals
        if (stamp := _cycle_timestamp(journal)) is not None
    )


def drift_summary(drift_log: Path, journals: list[Path]) -> list[str]:
    orders = latest_orders(drift_log)
    latest = list(orders.values())
    pending = [
        record
        for record in latest
        if record.get("event") in {"submitted", "reconciliation_timeout"}
    ]
    reconciled = [record for record in latest if record.get("event") == "reconciled"]
    orphan = [record for record in latest if record.get("event") == "orphan"]
    lines = [
        "DRIFT (all paper-derived cost figures are lower bounds; IEX spreads are upward-biased)",
        f"orders={len(latest)} | pending={len(pending)} | reconciled={len(reconciled)} | "
        f"orphan={len(orphan)}",
    ]
    by_symbol: dict[str, list[dict[str, object]]] = {}
    for record in latest:
        by_symbol.setdefault(str(record.get("symbol", "unknown")), []).append(record)
    for symbol in sorted(by_symbol):
        records = by_symbol[symbol]
        spread = _numbers(records, "iex_half_spread_bps")
        shortfall = _numbers(records, "signed_implementation_shortfall_bps")
        lines.append(
            f"{symbol} | IEX half-spread bps lower bound/upward bias: "
            f"median={_stat(spread, statistics.median)} mean={_stat(spread, statistics.fmean)} | "
            f"signed shortfall bps lower bound/upward bias: "
            f"median={_stat(shortfall, statistics.median)} "
            f"mean={_stat(shortfall, statistics.fmean)}"
        )
    for record in pending:
        cycles = _pending_cycles(record, journals)
        if cycles > 2:
            lines.append(
                f"WARNING: pending order {record['order_id']} has remained pending for "
                f"{cycles} cycles"
            )
    return lines


def _stat(values: list[float], function: Callable[[list[float]], float]) -> str:
    if not values:
        return "n/a"
    return f"{function(values):.2f}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--last", type=int, default=10, help="number of latest cycle journals")
    parser.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
    parser.add_argument("--drift-log", type=Path, default=DEFAULT_DRIFT_LOG)
    args = parser.parse_args()
    if args.last < 0:
        raise SystemExit("--last must be non-negative")
    journals = cycle_journals(args.journal_dir)
    print("CYCLES")
    for journal in journals[-args.last :] if args.last else []:
        print(cycle_summary(journal))
    if not journals:
        print("none")
    for line in drift_summary(args.drift_log, journals):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
