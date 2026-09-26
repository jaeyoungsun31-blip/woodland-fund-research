"""Build the constituent return panel from the automatically resolved locators.

Returns come from `adjusted_close` only.  The signed A2 convention is applied
from the resolver's cited census.  The base panel excludes Case 2 names without
a price file; its mandatory -100% adverse bound is emitted as a separate panel.

Three things are declared rather than assumed:

* **The refused set.** Constituents the resolver could not resolve are refused,
  not omitted, and their symbol-years are reported in the metadata as the A2
  convention requires.
* **Substitutions.** Where adjudication found the resolved file defective and
  named the correct one, the panel reads the correct file and records the
  substitution. Nothing is written back to the resolver; this is a panel
  construction choice, visible in the metadata.
* **Quality flags.** Symbols whose in-window series carry impossible daily
  moves or long frozen runs are flagged, counted, and reported. They are NOT
  removed - that is planning's call - but no result should be computed on this
  panel until it is made.

A return is contributed only when the PREVIOUS bar is also inside the
membership window, so a name never contributes the move that happened before it
joined the index.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from itertools import groupby
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.a2_panel import (  # noqa: E402
    A2Exit,
    bounded_exit_panels,
    classify_exit_coverage,
    read_a2_census,
    signed_a2_report,
)
from scripts.run_locator_adjudication import (  # noqa: E402
    load_frame,
    membership_intervals,
    window_mask,
)
from woodland.snapshot import refuse_pinned_write  # noqa: E402

# Adjudicated: the resolved file is defective and the named file is correct.
# Evidence per name is in reports/security-resolver/2026-09-07-locator-adjudication/.
SUBSTITUTIONS = {
    "SYMC": "GEN",     # SYMC carries a 2:1 split as a -48.6% adjusted return
    "NLOK": "GEN",     # single differing bar 2019-11-06, Tiingo matches GEN
    "WIN": "WINMQ",    # WIN applies ~0.8% where WINMQ applies a stable ~3.1%
    "KRFT": "KHC",     # KRFT applies no distribution on three ex-dates
    "MMC": "MRSH",     # MMC applies ~4x a quarterly distribution on 1999-10-06
}

# Material disagreement, no verdict: excluded rather than guessed at.
EXCLUDED_UNRESOLVED = {
    "CTX": "raw close doubles 2003-09-10 and persists; CTX1 disagrees; deferred",
    "DF": "monotonicity and the step-date test name different files",
    "IGT": "no Tiingo series under either ticker",
    "COG": "disagreement below what a third source can settle",
}

# Impossible for an index constituent's adjusted series; flags, never filters.
EXTREME_UP = 1.0
EXTREME_DOWN = -0.5
FROZEN_FRACTION = 0.10
THIN_DAY = 30


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--a2-census", type=Path, required=True,
                        help="signed-base census-symbol-years.csv")
    parser.add_argument("--a2-classification", type=Path, required=True,
                        help="cited candidate classifications; successor ambiguity only")
    args = parser.parse_args()

    for name in (
        "panel-returns.parquet", "membership-mask.parquet", "panel-summary.json",
        "panel-returns-a2-favourable.parquet", "panel-returns-a2-adverse.parquet",
    ):
        refuse_pinned_write(args.out / name)

    rows = [json.loads(line) for line in args.resolution.read_text().splitlines()
            if line.strip()]
    rows = [r for r in rows if "status" in r]
    resolved = [r for r in rows if r["status"] == "resolved"]
    automatic = [r for r in resolved if r.get("match_basis") == "unique_live_candidate"]
    refused = [r for r in rows if r["status"] != "resolved"]
    a2_census = read_a2_census(str(args.a2_census))
    a2_counts, pending_amendment = signed_a2_report(
        a2_census, str(args.a2_classification)
    )

    windows = membership_intervals(automatic)
    years = Counter(r["price_symbol"] for r in automatic)
    refused_years = Counter(r["constituent_symbol"] for r in refused)

    columns: dict[str, pd.Series] = {}
    flags: list[dict[str, Any]] = []
    missing: list[str] = []

    for symbol in sorted(windows):
        if symbol in EXCLUDED_UNRESOLVED:
            continue
        source = SUBSTITUTIONS.get(symbol, symbol)
        if not (args.store / f"{source}.US.parquet").exists():
            missing.append(symbol)
            continue
        frame = load_frame(args.store, source).dropna(subset=["adjusted_close"])
        frame = frame[frame["adjusted_close"] > 0]
        level = pd.Series(frame["adjusted_close"].to_numpy(float),
                          index=pd.DatetimeIndex(frame["date"]))
        inside = window_mask(pd.Series(level.index), windows[symbol])
        returns = level.pct_change()
        # Contribute only where the PREVIOUS bar is also inside the window.
        eligible = inside & np.concatenate([[False], inside[:-1]])
        series = returns[eligible]
        if series.empty:
            missing.append(symbol)
            continue
        columns[symbol] = series

        values = series.to_numpy(float)
        extreme = int(((values > EXTREME_UP) | (values < EXTREME_DOWN)).sum())
        frozen = int((values == 0.0).sum())
        if extreme or frozen / len(values) > FROZEN_FRACTION:
            flags.append({
                "symbol": symbol, "source_file": source,
                "symbol_years": years[symbol], "bars": len(values),
                "extreme_days": extreme,
                "frozen_days": frozen,
                "frozen_fraction": round(frozen / len(values), 4),
                "max_return": round(float(values.max()), 4),
                "min_return": round(float(values.min()), 4),
            })

    panel = pd.DataFrame(columns).sort_index()
    args.out.mkdir(parents=True, exist_ok=True)
    membership = pd.DataFrame(
        {
            symbol: window_mask(pd.Series(panel.index), windows[symbol])
            for symbol in panel.columns
        },
        index=panel.index,
    ).astype(bool)
    fills: list[dict[str, Any]] = []
    for symbol in panel.columns:
        column_index = cast(int, panel.columns.get_loc(symbol))
        missing_inside = membership[symbol] & panel[symbol].isna()
        for is_missing, run in groupby(enumerate(missing_inside.to_numpy()), key=lambda x: x[1]):
            positions = [pos for pos, _ in run]
            interior = (
                positions[0] > 0
                and positions[-1] + 1 < len(panel)
                and pd.notna(panel.iloc[positions[0] - 1, column_index])
                and pd.notna(panel.iloc[positions[-1] + 1, column_index])
            )
            if is_missing and len(positions) <= 5 and interior:
                panel.iloc[positions, column_index] = 0.0
                fills.extend(
                    {"date": str(panel.index[pos].date()), "symbol": symbol, "return": 0.0}
                    for pos in positions
                )
    panel.to_parquet(args.out / "panel-returns.parquet")
    membership.to_parquet(args.out / "membership-mask.parquet")
    pd.DataFrame(fills).to_csv(args.out / "short-gap-fills.csv", index=False)
    panel_end = panel.index.max()
    final_record_by_symbol = {
        symbol: max(symbol_rows, key=lambda row: row["end"])
        for symbol, symbol_rows in groupby(
            sorted(automatic, key=lambda row: (row["price_symbol"], row["end"])),
            key=lambda row: row["price_symbol"],
        )
    }
    exits = [
        A2Exit(final_record_by_symbol[symbol]["record_id"], symbol, terminal)
        for symbol, terminal in panel.apply(lambda series: series.last_valid_index()).items()
        if terminal < panel_end
    ]
    # Case 2 absent files are exits too, although they have no base panel column.
    absent_final_by_symbol: dict[str, Any] = {}
    for row in a2_census:
        if row.a2_case == "2" and row.case2_absent:
            current = absent_final_by_symbol.get(row.symbol)
            if current is None or row.end > current.end:
                absent_final_by_symbol[row.symbol] = row
    exits.extend(
        A2Exit(row.record_id, row.symbol, pd.Timestamp(row.end))
        for row in absent_final_by_symbol.values()
        if row.record_id not in {exit.record_id for exit in exits}
    )
    # Amendment 1 quarantines are terminal symbol-years for coverage only.
    # They are deliberately excluded from both bound panels.
    census_by_id = {row.record_id: row for row in a2_census}
    exits.extend(
        A2Exit(record_id, census_by_id[record_id].symbol, pd.Timestamp(census_by_id[record_id].end))
        for record_id in sorted(pending_amendment)
        if record_id not in {exit.record_id for exit in exits}
    )
    a2_coverage, unclassified_exits = classify_exit_coverage(
        exits, a2_census, pending_amendment
    )
    favourable_panel, adverse_panel, bound_terminal_rows, adverse_terminal_rows = (
        bounded_exit_panels(
        panel, unclassified_exits, a2_census
        )
    )
    favourable_panel.to_parquet(args.out / "panel-returns-a2-favourable.parquet")
    adverse_panel.to_parquet(args.out / "panel-returns-a2-adverse.parquet")
    pd.DataFrame(bound_terminal_rows).to_csv(args.out / "a2-unclassified-terminal-bounds.csv",
                                             index=False)

    per_day = panel.notna().sum(axis=1)
    thin = per_day[per_day < THIN_DAY]
    flagged_symbols = {f["symbol"] for f in flags}
    clean = panel.drop(columns=[c for c in panel.columns if c in flagged_symbols])
    clean_per_day = clean.notna().sum(axis=1)

    summary = {
        "construction": {
            "returns_from": "adjusted_close",
            "synthetic_bars": 0,
            "price_data_changed": False,
            "a2_treatment_applied": True,
            "a2_convention": "2026-09-06 signed base plus 2026-09-08 Amendment 2",
            "symbol_years_by_a2_case": a2_counts,
            "a2_coverage": a2_coverage,
            "a2_coverage_definition": "one final symbol-year for every panel column "
                                      "whose last return precedes panel end, plus final "
                                      "absent Case 2 and pending Amendment 1 symbol-years; "
                                      "no 180-day cutoff is applied",
            "a2_note": "Case 2 absent names are excluded in base. Amendment 2 bounds "
                       "each unclassified exit at 0% (favourable) and -100% (adverse). "
                       "Successor ambiguity remains quarantined; Amendment 1 is unsigned.",
            "unclassified_exit_bounds": {
                "favourable_return": 0.0,
                "adverse_return": -1.0,
                "terminal_rows": len(bound_terminal_rows),
                "terminal_rows_file": "a2-unclassified-terminal-bounds.csv",
            },
            "case2_adverse_bound": {
                "return": -1.0,
                "absent_symbol_years": sum(
                    row.a2_case == "2" and row.case2_absent for row in a2_census
                ),
                "terminal_rows": adverse_terminal_rows,
            },
            "quarantined": {
                "status": "pending_A2_amendment_1",
                "symbol_years": len(pending_amendment),
                "record_ids": sorted(pending_amendment),
            },
            "seam_rule": "a return is contributed only when the previous bar is also "
                         "inside the membership window",
            "membership_mask": "membership-mask.parquet; resolver-derived per date/symbol",
            "short_gap_fill": {"max_trading_bars": 5, "filled_cells": len(fills),
                               "audit_file": "short-gap-fills.csv"},
        },
        "universe": {
            "automatic_locators": len(windows),
            "in_panel": len(panel.columns),
            "excluded_unresolved_defect": EXCLUDED_UNRESOLVED,
            "substituted": SUBSTITUTIONS,
            "no_usable_bars": missing,
        },
        "refused": {
            "note": "declared refused, not omitted",
            "constituent_symbols": len(refused_years),
            "symbol_years": int(sum(refused_years.values())),
            "resolved_symbol_years_total": int(sum(years.values())),
            "resolved_non_automatic_symbol_years": len(
                [r for r in resolved if r.get("match_basis") != "unique_live_candidate"]),
        },
        "dimensions": {
            "dates": int(len(panel)),
            "symbols": int(len(panel.columns)),
            "first_date": str(panel.index.min().date()) if len(panel) else None,
            "last_date": str(panel.index.max().date()) if len(panel) else None,
            "observations": int(panel.notna().sum().sum()),
            "density": round(float(panel.notna().sum().sum() / panel.size), 4)
            if panel.size else None,
        },
        "names_per_day": {
            "min": int(per_day.min()), "median": float(per_day.median()),
            "max": int(per_day.max()),
            "dates_under_30_names": int(len(thin)),
            "thin_dates": [
                {"date": str(day.date()), "names": int(count)}
                for day, count in zip(pd.DatetimeIndex(thin.index),
                                      thin.to_numpy(int), strict=True)
            ][:60],
        },
        "quality_flags": {
            "note": "impossible daily moves or long frozen runs in the in-window "
                    "adjusted series; flagged and counted, NOT removed",
            "extreme_up": EXTREME_UP, "extreme_down": EXTREME_DOWN,
            "frozen_fraction": FROZEN_FRACTION,
            "symbols_flagged": len(flags),
            "symbol_years_flagged": int(sum(f["symbol_years"] for f in flags)),
            "if_flagged_symbols_were_dropped": {
                "symbols": int(len(clean.columns)),
                "dates_under_30_names": int((clean_per_day < THIN_DAY).sum()),
                "min_names_per_day": int(clean_per_day.min()) if len(clean) else None,
            },
            "worst": sorted(flags, key=lambda f: -f["extreme_days"])[:25],
        },
    }
    (args.out / "panel-summary.json").write_text(json.dumps(summary, indent=2))
    pd.DataFrame(flags).to_csv(args.out / "quality-flags.csv", index=False)
    per_day.rename("names").to_frame().to_csv(args.out / "names-per-day.csv")

    print(f"panel: {len(panel)} dates x {len(panel.columns)} symbols, "
          f"{panel.notna().sum().sum():,} observations")
    print(f"  {panel.index.min().date()} .. {panel.index.max().date()}")
    print(f"  names per day: min {per_day.min()}, median {per_day.median():.0f}, "
          f"max {per_day.max()}")
    print(f"  dates under {THIN_DAY} names: {len(thin)}")
    print(f"  quality-flagged symbols: {len(flags)} "
          f"({sum(f['symbol_years'] for f in flags)} symbol-years)")
    print(f"  refused: {len(refused_years)} constituent symbols, "
          f"{sum(refused_years.values())} symbol-years")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
