"""Ingest the official Fama-French 12-industry daily portfolios."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.config import ROOT
from woodland.fama_french import ingest_12_industry_daily, ingest_research_factors_daily
from woodland.snapshot import refuse_pinned_write


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "fama_french_12_industry_daily.parquet",
        help="derived index-level parquet (default: data/fama_french_12_industry_daily.parquet)",
    )
    parser.add_argument(
        "--factors-output",
        type=Path,
        default=ROOT / "data" / "fama_french_factors_daily.parquet",
        help="derived MKT/CASH index-level parquet",
    )
    args = parser.parse_args()
    refuse_pinned_write(args.factors_output)

    result = ingest_12_industry_daily(args.output)
    print(
        f"saved {len(result.levels)} rows x {len(result.levels.columns)} industries "
        f"({result.provenance['first']}..{result.provenance['last']}) to {result.data_path}"
    )
    print(f"provenance: {result.provenance_path}")
    factors = ingest_research_factors_daily(args.factors_output)
    print(
        f"saved {len(factors.levels)} rows x {len(factors.levels.columns)} series "
        f"({factors.provenance['first']}..{factors.provenance['last']}) "
        f"to {factors.data_path}"
    )
    print(f"provenance: {factors.provenance_path}")
    print("WARNING: frictionless academic portfolios; these are not tradeable securities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
