"""Capture a read-only Alpaca Paper/IEX snapshot. This script never submits orders."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from woodland.live.alpaca import PaperClient, write_snapshot

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default="SPY,IEF", help="comma-separated IEX quote symbols")
    parser.add_argument("--output", type=Path, default=Path("data/live/alpaca"))
    args = parser.parse_args()
    symbols = [item.strip().upper() for item in args.symbols.split(",") if item.strip()]
    path = write_snapshot(PaperClient.from_environment().snapshot(symbols), args.output)
    print(f"read-only paper snapshot written: {path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
