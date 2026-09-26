"""Runner for the sealed xsmom-v16 dual-run harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.harness.dual_panel import completed_report, execute_all, validate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate", action="store_true", help="assemble arms and stop before fitting"
    )
    parser.add_argument(
        "--run-all", action="store_true", help="run A, B, C, and D sequentially"
    )
    parser.add_argument("--report", action="store_true", help="emit only a sealed four-arm report")
    args = parser.parse_args()
    if sum((args.validate, args.run_all, args.report)) != 1:
        parser.error("select exactly one of --validate, --run-all, or --report")
    if args.validate:
        result = validate()
    elif args.run_all:
        completed = execute_all()
        # Keep arm-level results sealed until the explicit --report gate.
        result = {
            "status": completed["status"],
            "run_id": completed["run_id"],
            "arms_completed": len(completed["arms"]),
        }
    else:
        result = completed_report()
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
