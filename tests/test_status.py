from __future__ import annotations

import json
from pathlib import Path

from scripts.status import cycle_journals, cycle_summary, drift_summary


def _journal(path: Path, *, status: str = "completed", refusal: str = "checks passed") -> None:
    path.write_text(
        "\n".join(
            [
                f"- Status: **{status}**",
                "- Decision: **no change**",
                f"- Refusal: **{refusal}**",
                "- Paper orders: **0**",
            ]
        )
        + "\n"
    )


def _record(order_id: str, event: str, symbol: str, *, recorded_at: str) -> dict[str, object]:
    return {
        "order_id": order_id,
        "event": event,
        "symbol": symbol,
        "recorded_at": recorded_at,
        "iex_half_spread_bps": 2.0 if symbol == "SPY" else None,
        "signed_implementation_shortfall_bps": 3.0 if event == "reconciled" else None,
    }


def test_status_summarizes_cycles_costs_and_old_pending_without_writing(tmp_path: Path) -> None:
    journal_dir = tmp_path / "journal"
    journal_dir.mkdir()
    for stamp in ("090000", "100000", "110000"):
        _journal(journal_dir / f"2026-09-04-phase3-cycle-{stamp}.md")
    drift_log = tmp_path / "paper-drift.jsonl"
    records = [
        _record("pending", "submitted", "SPY", recorded_at="2026-09-04T08:00:00+00:00"),
        _record("done", "reconciled", "SPY", recorded_at="2026-09-04T08:00:00+00:00"),
        _record("orphan", "orphan", "IEF", recorded_at="2026-09-04T08:00:00+00:00"),
    ]
    drift_log.write_text("".join(json.dumps(record) + "\n" for record in records))
    before = drift_log.read_text()

    journals = cycle_journals(journal_dir)
    lines = drift_summary(drift_log, journals)

    assert cycle_summary(journals[-1]).startswith("2026-09-04 | status=completed")
    assert "orders=3 | pending=1 | reconciled=1 | orphan=1" in lines
    assert any("SPY | IEX half-spread bps lower bound/upward bias" in line for line in lines)
    assert any(
        "WARNING: pending order pending has remained pending for 3 cycles" in line for line in lines
    )
    assert drift_log.read_text() == before
