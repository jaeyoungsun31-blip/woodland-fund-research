"""Ingest the AQR Time Series Momentum monthly factor (external validation)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.aqr import ingest_tsmom_monthly
from woodland.config import ROOT


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "data" / "aqr_tsmom_monthly.parquet")
    args = parser.parse_args()
    result = ingest_tsmom_monthly(args.output)
    prov = result.provenance
    print(f"saved {prov['rows']} monthly rows ({prov['first']}..{prov['last']}) "
          f"to {result.data_path}")
    print(f"columns: {prov['columns']}")
    print(f"provenance: {result.provenance_path}")
    print("NOTE: long/short, vol-targeted futures factor — not scale-comparable "
          "to a long-only ETF portfolio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
