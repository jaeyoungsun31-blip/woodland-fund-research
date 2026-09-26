"""Preflight the signed xsmom-v16 universe-control study; never fit by default."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.harness.universe_control import execute, preflight

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = ROOT / "reports/xsmom-v16-universe-control/summary.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args(argv)
    if args.execute:
        result = execute()
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(result, indent=2, default=str))
        print(json.dumps(result, indent=2, default=str))
        return 0
    print(json.dumps(preflight(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
