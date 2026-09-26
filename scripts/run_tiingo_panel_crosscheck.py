"""Cross-check every resolved panel symbol against Tiingo, the second source.

The duplicate-locator census finds a missed corporate action only where a
duplicate file happens to exist in the store. `SYMC` was caught that way and it
was luck: had EODHD not also shipped `GEN` and `NLOK`, a two-for-one split
carried into the adjusted column as a 48.6% loss would have entered the panel
silently. This is the generic form of that test, and it is the design
`crosscheck_sources` was written for on 2026-09-01 and never run on this data.

For each automatically resolved locator the two providers' ADJUSTED daily
RETURNS are compared over the constituent's membership window, and every day
they disagree beyond the planning-owned tolerances in `config/universe.yaml` is
recorded. Symbols are ordered by membership-years so that the names carrying
the most panel weight are covered first.

Two refusals are built in:

* **A throttle is never a finding.** The vendor signals a rate limit in prose;
  an early version of the adjudication script read that as "no such ticker" and
  reported 19 pairs as having no third source. A symbol that could not be
  fetched is recorded as `not_attempted`, never as agreeing.
* **A ticker is not an identity.** Tiingo's `WIN` is a company first listed in
  2023, not the Windstream delisted in 2020. Every series is qualified on price
  against our own file before its returns are compared.

Read-only. Builds no panel, changes no price, applies nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_locator_adjudication import (  # noqa: E402
    TIINGO_MIN_ENTITY_MATCH,
    TiingoThrottled,
    load_frame,
    membership_intervals,
    tiingo_is_same_entity,
    tiingo_series,
    tiingo_ticker_candidates,
    window_mask,
)
from woodland.data import crosscheck_sources  # noqa: E402
from woodland.snapshot import refuse_pinned_write  # noqa: E402

THROTTLE_SLEEP_SECONDS = 300
MAX_THROTTLE_WAITS = 220


def aligned_returns(
    store: Path, symbol: str, intervals: list[tuple[str, str]], reference: pd.DataFrame
) -> tuple[pd.Series, pd.Series] | None:
    """Our adjusted closes and Tiingo's, on the same in-window trading days."""
    frame = load_frame(store, symbol).dropna(subset=["adjusted_close"])
    frame = frame[frame["adjusted_close"] > 0]
    ours = pd.Series(frame["adjusted_close"].to_numpy(float),
                     index=pd.DatetimeIndex(frame["date"]))
    ours = ours[window_mask(pd.Series(ours.index), intervals)]
    joined = ours.to_frame("ours").join(reference["adj_close"].rename("them"),
                                        how="inner").dropna()
    if len(joined) < 250:
        return None
    return joined["ours"], joined["them"]


def compare(
    ours: pd.Series, theirs: pd.Series, fail: float, monitor: float
) -> dict[str, Any]:
    """crosscheck_sources, plus the cumulative gap a panel would inherit.

    The gap is compounded in log space: over a twenty-year window a running
    product of (1 + r) is the kind of thing that quietly loses precision, and
    the whole point of the number is that it be trustworthy at the third
    decimal place.
    """
    result = dict(crosscheck_sources(ours, theirs,
                                     fail_tolerance=fail, monitor_tolerance=monitor))
    frame = pd.DataFrame({"a": ours, "b": theirs}).dropna()
    returns = frame.pct_change().dropna()
    mine = returns["a"].to_numpy(float)
    yours = returns["b"].to_numpy(float)
    gap = float(np.expm1(np.log1p(mine).sum() - np.log1p(yours).sum()))
    difference = np.abs(mine - yours)
    dates = pd.DatetimeIndex(returns.index)
    failing = difference > fail
    result["cumulative_gap"] = gap
    result["sum_abs_diff_on_failing_days"] = float(difference[failing].sum())
    if failing.any():
        worst = int(np.argmax(difference))
        result["first_fail_date"] = str(dates[failing][0].date())
        result["worst_fail_date"] = str(dates[worst].date())
        result["worst_fail_ours"] = float(mine[worst])
        result["worst_fail_theirs"] = float(yours[worst])
        result["fail_dates"] = ";".join(str(d.date()) for d in dates[failing][:20])
    else:
        result["first_fail_date"] = ""
        result["worst_fail_date"] = ""
        result["worst_fail_ours"] = float("nan")
        result["worst_fail_theirs"] = float("nan")
        result["fail_dates"] = ""
    return result


def main() -> int:  # noqa: C901
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0,
                        help="cover only the top N by membership-years (0 = all)")
    parser.add_argument("--fail-tolerance", type=float, default=0.02)
    parser.add_argument("--monitor-tolerance", type=float, default=0.005)
    args = parser.parse_args()
    refuse_pinned_write(args.out / "crosscheck.csv")

    rows = [json.loads(line) for line in args.resolution.read_text().splitlines()
            if line.strip()]
    rows = [r for r in rows if "status" in r]
    automatic = [r for r in rows if r["status"] == "resolved"
                 and r.get("match_basis") == "unique_live_candidate"]
    windows = membership_intervals(automatic)
    years = Counter(r["price_symbol"] for r in automatic)
    ordered = sorted(windows, key=lambda s: (-years[s], s))
    targets = ordered[: args.limit] if args.limit else ordered
    print(f"{len(windows)} automatically resolved locators; "
          f"cross-checking {len(targets)} of them, most membership-years first")

    args.out.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    waits = 0

    for index, symbol in enumerate(targets, 1):
        intervals = windows[symbol]
        record: dict[str, Any] = {
            "symbol": symbol, "symbol_years": years[symbol],
            "window_start": intervals[0][0], "window_end": intervals[-1][1],
        }
        reference, ticker, rejected = None, "", []
        for candidate in tiingo_ticker_candidates(symbol, symbol):
            while True:
                try:
                    frame = tiingo_series(candidate, intervals[0][0], args.cache)
                    break
                except TiingoThrottled:
                    waits += 1
                    if waits > MAX_THROTTLE_WAITS:
                        frame = None
                        break
                    print(f"  [{index}/{len(targets)}] throttled; waiting "
                          f"{THROTTLE_SLEEP_SECONDS}s (wait {waits})", flush=True)
                    time.sleep(THROTTLE_SLEEP_SECONDS)
            if frame is None:
                if waits > MAX_THROTTLE_WAITS:
                    record["status"] = "not_attempted"
                    record["detail"] = "vendor throttled; NOT a finding"
                    results.append(record)
                    break
                continue
            match = tiingo_is_same_entity(args.store, symbol, intervals, frame)
            if match is None or match < TIINGO_MIN_ENTITY_MATCH:
                rejected.append(f"{candidate}"
                                f"({'no overlap' if match is None else f'{match:.2f}'})")
                continue
            reference, ticker = frame, candidate
            record["tiingo_entity_match"] = match
            break
        if record.get("status") == "not_attempted":
            continue
        if rejected:
            record["tiingo_tickers_rejected"] = ";".join(rejected)
        if reference is None:
            record["status"] = ("different_entity" if rejected else "no_tiingo_series")
            results.append(record)
            continue

        record["tiingo_ticker"] = ticker
        pair = aligned_returns(args.store, symbol, intervals, reference)
        if pair is None:
            record["status"] = "insufficient_overlap"
            results.append(record)
            continue
        record.update(compare(*pair, args.fail_tolerance, args.monitor_tolerance))
        record["status"] = "compared"
        results.append(record)
        if record.get("n_days_gt_fail"):
            print(f"  [{index}/{len(targets)}] {symbol}: "
                  f"{record['n_days_gt_fail']} day(s) past the 2% fail tolerance, "
                  f"cumulative gap {record['cumulative_gap'] * 100:+.2f}pp", flush=True)

        if index % 10 == 0 or index == len(targets):
            write_outputs(args, results, len(windows), len(targets))
    write_outputs(args, results, len(windows), len(targets))
    return 0


def write_outputs(
    args: argparse.Namespace, results: list[dict[str, Any]], total: int, attempted: int
) -> None:
    refuse_pinned_write(args.out / "crosscheck.csv")
    fields: list[str] = []
    for record in results:
        for key in record:
            if key not in fields:
                fields.append(key)
    with (args.out / "crosscheck.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    compared = [r for r in results if r["status"] == "compared"]
    failing = [r for r in compared if r.get("n_days_gt_fail")]
    ranked = sorted(failing, key=lambda r: -abs(float(r.get("cumulative_gap") or 0)))
    summary = {
        "purpose": "generic form of the SYMC missed-split defect: compare both "
                   "providers' adjusted returns over each membership window",
        "automatic_locators": total,
        "attempted": sum(r["status"] != "not_attempted" for r in results),
        "planned": attempted,
        "sample_selection": {
            "method": "Longest membership-history names first; descending membership-years, "
                      "ticker tie-break",
            "random_sample": False,
            "interpretation": "Failure fraction is conditional on the compared sample; "
                              "it is not a store-wide failure rate.",
        },
        "coverage": {
            "compared": len(compared),
            "not_attempted_throttled": sum(
                1 for r in results if r["status"] == "not_attempted"),
            "no_tiingo_series": sum(1 for r in results if r["status"] == "no_tiingo_series"),
            "different_entity": sum(1 for r in results if r["status"] == "different_entity"),
            "insufficient_overlap": sum(
                1 for r in results if r["status"] == "insufficient_overlap"),
        },
        "tolerances": {"fail": args.fail_tolerance, "monitor": args.monitor_tolerance},
        "symbols_past_fail_tolerance": len(failing),
        "ranked_by_cumulative_impact": [
            {"symbol": r["symbol"], "symbol_years": r["symbol_years"],
             "n_days_gt_fail": r["n_days_gt_fail"],
             "cumulative_gap": r["cumulative_gap"],
             "worst_fail_date": r["worst_fail_date"],
             "worst_fail_ours": r["worst_fail_ours"],
             "worst_fail_theirs": r["worst_fail_theirs"],
             "fail_dates": r["fail_dates"]}
            for r in ranked
        ],
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
