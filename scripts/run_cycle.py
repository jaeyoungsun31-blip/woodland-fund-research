"""Run one Phase 3 operational cycle; read-only dry-run is the default."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.live.bands import DEFAULT_BAND
from woodland.live.broker import DEFAULT_MAX_ORDER_NOTIONAL, PaperBroker
from woodland.live.cycle import (
    DEFAULT_DRIFT_LOG,
    DEFAULT_JOURNAL_DIR,
    DEFAULT_LEDGER,
    DEFAULT_STATE_DIR,
    RegisteredChallenger,
    build_snapshot,
    execute_cycle,
    format_result,
)
from woodland.live.incumbent import IncumbentStore
from woodland.config import ROOT, load_config


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    mode.add_argument(
        "--execute",
        dest="dry_run",
        action="store_false",
        help="persist incumbent initialization, ledger rows, and the cycle journal",
    )
    parser.add_argument(
        "--emit-targets",
        action="store_true",
        help="print the bounded target; valid only with --execute",
    )
    parser.add_argument("--refresh-data", action="store_true")
    parser.add_argument(
        "--submit-paper",
        action="store_true",
        help="submit bounded targets to Alpaca Paper only; requires --execute and --emit-targets",
    )
    parser.add_argument("--max-order-notional", type=float, default=DEFAULT_MAX_ORDER_NOTIONAL)
    parser.add_argument("--drift-log", type=Path, default=DEFAULT_DRIFT_LOG)
    parser.add_argument("--band", type=float, default=DEFAULT_BAND)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--journal-dir", type=Path, default=DEFAULT_JOURNAL_DIR)
    parser.add_argument(
        "--challenger-state",
        action="append",
        type=Path,
        default=[],
        help="directory containing frozen, registered challenger evidence",
    )
    parser.add_argument("--promote", help="exact gate-passing challenger name")
    parser.add_argument("--promotion-journal", help="journal entry authorizing replacement")
    return parser


def _challengers(paths: list[Path]) -> list[RegisteredChallenger]:
    out: list[RegisteredChallenger] = []
    for path in paths:
        record = IncumbentStore(path).load()
        out.append(
            RegisteredChallenger(
                record=record,
                study_id=f"phase3-challenge-{record.name}",
                config={"name": record.name, "parameters": record.parameters},
            )
        )
    return out


def main() -> int:
    args = _parser().parse_args()
    if args.emit_targets and args.dry_run:
        raise SystemExit("--emit-targets requires --execute")
    if args.submit_paper and args.dry_run:
        raise SystemExit("--submit-paper requires --execute")
    if args.submit_paper and not args.emit_targets:
        raise SystemExit("--submit-paper requires --emit-targets")
    if args.challenger_state:
        raise SystemExit("Phase 4 paper execution has no registered challenger; v17 failed C3")
    if args.promote or args.promotion_journal:
        raise SystemExit("Phase 4 paper execution keeps the declared 60/40 incumbent fixed")
    if args.promote and args.dry_run:
        raise SystemExit("--promote requires --execute")
    if bool(args.promote) != bool(args.promotion_journal):
        raise SystemExit("--promote and --promotion-journal must be supplied together")

    # Keep the live cycle on the mutable operational store.  Research scripts
    # use ``data.store``, which is a separately frozen snapshot.
    data_config = load_config()["data"]
    live_store = ROOT / data_config.get("live_store", data_config["store"])
    snapshot = build_snapshot(refresh=args.refresh_data, store=live_store)
    result = execute_cycle(
        snapshot,
        IncumbentStore(args.state_dir),
        _challengers(args.challenger_state),
        dry_run=args.dry_run,
        emit_targets=args.emit_targets,
        band=args.band,
        approved_promotion=args.promote,
        promotion_journal=args.promotion_journal,
        ledger_path=args.ledger,
        journal_dir=args.journal_dir,
        submit_paper=args.submit_paper,
        paper_broker=PaperBroker.from_environment() if args.submit_paper else None,
        max_order_notional=args.max_order_notional,
        drift_path=args.drift_log,
    )
    print(format_result(result, include_targets=result.target_emitted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
