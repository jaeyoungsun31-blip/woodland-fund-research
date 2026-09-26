"""Exercise every live-paper refusal without mutating ``data/`` or placing orders."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.config import ROOT, load_config
from woodland.live.broker import (
    PAPER_BASE_URL,
    PaperSubmissionRefused,
    assert_paper_base_url,
    validate_submission,
)
from woodland.live.cycle import CycleSnapshot, build_snapshot, run_cycle
from woodland.live.refusal import CycleHealth


@dataclass(frozen=True)
class RehearsalResult:
    condition: str
    cycle_refused: bool
    target_emitted: bool
    detail: str
    passed: bool


def _store_digest(store: Path) -> str:
    """Stable content digest used to prove the source store remained untouched."""
    digest = hashlib.sha256()
    for path in sorted(item for item in store.rglob("*") if item.is_file()):
        digest.update(path.relative_to(store).as_posix().encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
    return digest.hexdigest()


def _healthy_snapshot(snapshot: CycleSnapshot) -> CycleSnapshot:
    """Start every injected case from a healthy operational state."""
    as_of = date.today()
    health = CycleHealth(
        integrity_failures=(),
        store_last_bar=pd.Timestamp(as_of),
        as_of=as_of,
        realized_folds=22,
        expected_folds=22,
        spy_cagr_since_2000=0.075,
        spy_max_drawdown_since_2000=-0.55,
    )
    return replace(snapshot, health=health)


def _phase3_case(
    name: str, snapshot: CycleSnapshot, health: CycleHealth, code: str
) -> RehearsalResult:
    result = run_cycle(replace(snapshot, health=health), snapshot.seeded_incumbent, dry_run=True)
    codes = {reason.code for reason in result.refusal.reasons}
    passed = result.refusal.refused and not result.target_emitted and code in codes
    return RehearsalResult(
        name, result.refusal.refused, result.target_emitted, result.refusal.summary, passed
    )


def run_rehearsal(snapshot: CycleSnapshot) -> tuple[RehearsalResult, ...]:
    """Induce each refusal against a copied-store snapshot; this function never orders."""
    base = _healthy_snapshot(snapshot)
    as_of = base.health.as_of
    cases = [
        _phase3_case(
            "stale data (>5 calendar days)",
            base,
            replace(base.health, store_last_bar=pd.Timestamp(as_of - timedelta(days=6))),
            "stale_data",
        ),
        _phase3_case(
            "corrupted calendar date",
            base,
            replace(
                base.health, integrity_failures=("calendar integrity: injected corrupted date",)
            ),
            "integrity",
        ),
        _phase3_case(
            "frozen fold-count mismatch",
            base,
            replace(base.health, realized_folds=21),
            "fold_count",
        ),
        _phase3_case(
            "sanity-anchor breach",
            base,
            replace(base.health, spy_cagr_since_2000=0.15),
            "sanity_anchor",
        ),
    ]
    market_reasons = validate_submission(
        phase3_refused=False,
        market_open=False,
        target_weights={"SPY": 0.60, "IEF": 0.40},
        orders=(),
    )
    cases.append(
        RehearsalResult(
            "market closed",
            False,
            False,
            ", ".join(market_reasons),
            "market_closed" in market_reasons,
        )
    )
    try:
        assert_paper_base_url("https://api.alpaca.markets/v2")
    except PaperSubmissionRefused as error:
        cases.append(RehearsalResult("live base URL", False, False, str(error), True))
    else:  # pragma: no cover - a safety failure is asserted below
        cases.append(RehearsalResult("live base URL", False, False, "live host accepted", False))
    assert PAPER_BASE_URL.endswith("paper-api.alpaca.markets/v2")
    return tuple(cases)


def _table(results: tuple[RehearsalResult, ...]) -> str:
    lines = [
        "| Condition | Cycle refused | Target emitted | Result | Detail |",
        "|---|---:|---:|---|---|",
    ]
    for item in results:
        lines.append(
            f"| {item.condition} | {item.cycle_refused} | {item.target_emitted} | "
            f"{'PASS' if item.passed else 'FAIL'} | {item.detail} |"
        )
    return "\n".join(lines)


def _write_journal(directory: Path, results: tuple[RehearsalResult, ...]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%H%M%S")
    path = directory / f"{date.today().isoformat()}-phase4-dress-rehearsal-{stamp}.md"
    content = "\n".join(
        [
            f"# {date.today().isoformat()} — Phase 4 dress rehearsal",
            "",
            "Append-only operational safety rehearsal. Not a study and no order was submitted.",
            "The source `data/` store was content-hashed before and after a temporary "
            "copied-store run.",
            "",
            _table(results),
            "",
            "Market-closed and live-host cases are broker submission guards; no broker "
            "request was made.",
        ]
    )
    path.write_text(content + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal-dir", type=Path, default=ROOT / "journal")
    args = parser.parse_args()
    source = ROOT / load_config()["data"]["store"]
    assert source.exists() and source.is_dir(), f"data store does not exist: {source}"
    before = _store_digest(source)
    with tempfile.TemporaryDirectory(prefix="woodland-dress-rehearsal-") as temporary:
        copied_store = Path(temporary) / "store"
        assert copied_store.resolve() != source.resolve(), "rehearsal must never operate on data/"
        shutil.copytree(source, copied_store)
        snapshot = build_snapshot(store=copied_store)
        results = run_rehearsal(snapshot)
    assert _store_digest(source) == before, "dress rehearsal mutated data/"
    print(_table(results))
    journal_path = _write_journal(args.journal_dir, results)
    print(f"journal: {journal_path}")
    return 0 if all(item.passed for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
