"""Screen all resolved panel symbols for corporate actions the store did not apply.

`check_missed_events` in `woodland/data.py` looks for the signature
`check_adjustment` is blind to: a large single-day adjusted return with the
adjustment factor unchanged across it. Symantec's file carries a two-for-one
split as a 48.6% loss and `check_adjustment` returns "ok", because a missed
event leaves `adj_close/close` flat.

The screen is run over each constituent's membership window - the days that
would actually reach a panel - and over the whole file for context. It is a
screen: a genuine crash has the same signature as a missed split, so the count
is reported as a candidate count at several thresholds and nothing is
corrected.

Read-only.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_locator_adjudication import (  # noqa: E402
    load_frame,
    membership_intervals,
    window_mask,
)
from woodland.data import MISSED_EVENT_FACTOR_TOL, check_missed_events  # noqa: E402
from woodland.snapshot import refuse_pinned_write  # noqa: E402

THRESHOLDS = (0.20, 0.25, 0.30, 0.40, 0.45)

# A missed split leaves the raw price ratio near a simple rational number. This
# is reported, never used to filter: SYMC's own 2004-12-01 ratio is 0.5139, not
# 0.5, because the stock also moved that day.
SPLIT_RATIOS = {
    "2:1": 0.5, "3:1": 1 / 3, "4:1": 0.25, "3:2": 2 / 3, "5:4": 0.8,
    "10:1": 0.1, "5:1": 0.2, "1:2": 2.0, "1:5": 5.0, "1:10": 10.0,
}
SPLIT_RATIO_TOL = 0.03


def nearest_split_ratio(ratio: float) -> str:
    best, distance = "", 1e9
    for name, value in SPLIT_RATIOS.items():
        relative = abs(ratio / value - 1.0)
        if relative < distance:
            best, distance = name, relative
    return best if distance <= SPLIT_RATIO_TOL else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.25)
    args = parser.parse_args()
    refuse_pinned_write(args.out / "missed-event-candidates.csv")

    rows = [json.loads(line) for line in args.resolution.read_text().splitlines()
            if line.strip()]
    rows = [r for r in rows if "status" in r]
    automatic = [r for r in rows if r["status"] == "resolved"
                 and r.get("match_basis") == "unique_live_candidate"]
    windows = membership_intervals(automatic)
    years = Counter(r["price_symbol"] for r in automatic)
    print(f"screening {len(windows)} automatically resolved locators")

    candidates: list[dict[str, Any]] = []
    per_symbol: list[dict[str, Any]] = []
    curve: dict[str, dict[str, int]] = {}
    missing = 0

    for symbol in sorted(windows):
        path = args.store / f"{symbol}.US.parquet"
        if not path.exists():
            missing += 1
            continue
        frame = load_frame(args.store, symbol).set_index("date")
        inside = frame[window_mask(pd.Series(frame.index), windows[symbol])]

        row: dict[str, Any] = {"symbol": symbol, "symbol_years": years[symbol],
                               "bars": len(frame), "window_bars": len(inside)}
        for threshold in THRESHOLDS:
            whole = check_missed_events(frame, move_threshold=threshold,
                                        adj_column="adjusted_close")
            within = check_missed_events(inside, move_threshold=threshold,
                                         adj_column="adjusted_close")
            key = f"{threshold:.2f}"
            bucket = curve.setdefault(key, {"file_symbols": 0, "file_days": 0,
                                            "window_symbols": 0, "window_days": 0})
            bucket["file_symbols"] += int(bool(whole["n_candidates"]))
            bucket["file_days"] += int(whole["n_candidates"])
            bucket["window_symbols"] += int(bool(within["n_candidates"]))
            bucket["window_days"] += int(within["n_candidates"])
            if threshold == args.threshold:
                row["candidates_in_file"] = whole["n_candidates"]
                row["candidates_in_window"] = within["n_candidates"]
                for candidate in within.get("candidates", []):
                    candidates.append({
                        "symbol": symbol, "symbol_years": years[symbol],
                        **candidate,
                        "nearest_split_ratio": nearest_split_ratio(
                            candidate["price_ratio"]),
                    })
        per_symbol.append(row)

    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "missed-event-candidates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(candidates[0]))
        writer.writeheader()
        writer.writerows(sorted(candidates, key=lambda c: c["adj_return"]))
    with (args.out / "per-symbol.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_symbol[0]))
        writer.writeheader()
        writer.writerows(per_symbol)

    flagged = [r for r in per_symbol if r["candidates_in_window"]]
    near_split = [c for c in candidates if c["nearest_split_ratio"]]
    summary = {
        "screened": len(per_symbol),
        "files_missing_from_store": missing,
        "threshold_reported": args.threshold,
        "factor_tolerance": MISSED_EVENT_FACTOR_TOL,
        "symbols_flagged_in_window": len(flagged),
        "candidate_days_in_window": len(candidates),
        "candidate_days_near_a_simple_split_ratio": len(near_split),
        "threshold_curve": curve,
        "caveat": "a screen, not a detector: a genuine crash has the same signature "
                  "as a missed split. Every hit is a candidate; nothing is corrected.",
        "worst_by_adjusted_move": sorted(candidates, key=lambda c: c["adj_return"])[:25],
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"  symbols flagged in-window at {args.threshold:.0%}: {len(flagged)} "
          f"of {len(per_symbol)}")
    print(f"  candidate days in-window                : {len(candidates)}")
    print(f"  of those near a simple split ratio      : {len(near_split)}")
    print("\n  threshold curve (in-window):")
    for key, bucket in curve.items():
        print(f"    move >= {key}: {bucket['window_symbols']:>3d} symbols, "
              f"{bucket['window_days']:>4d} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
