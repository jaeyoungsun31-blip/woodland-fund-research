"""Exploratory S&P 500 deletion-event census and abnormal returns.

Reads the pinned constituent membership mask and local adjusted prices only.
All output is confined to this directory. No study ledger or journal writes.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
PANEL_DIR = REPO / "reports/security-resolver/2026-09-07-constituent-panel"
MASK_FILE = PANEL_DIR / "membership-mask.parquet"
STORE = REPO / "data/Woodland-EODHD"
FLOOR = pd.Timestamp("2012-04-04")
WINDOWS = {"pre_-20_-1": (-20, -1), "post_0_5": (0, 5), "post_1_20": (1, 20), "post_1_60": (1, 60)}
BENCHMARKS = ("SPY", "IWM")


def load_price(path: Path, column: str) -> pd.Series:
    frame = pd.read_parquet(path)
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"])
    else:
        dates = pd.to_datetime(frame.index)
    values = pd.to_numeric(frame[column], errors="coerce")
    series = pd.Series(values.to_numpy(float), index=pd.DatetimeIndex(dates))
    series = series[series.notna() & (series > 0)]
    return series[~series.index.duplicated(keep="last")].sort_index()


def write_csv(name: str, rows: list[dict]) -> None:
    if not rows:
        return
    with (ROOT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def bootstrap_clustered_mean(rows: list[dict], seed: int = 20260923) -> tuple[float, float]:
    groups: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        groups[row["day0"]].append(float(row["car"]))
    clusters = list(groups.values())
    rng = np.random.default_rng(seed)
    draws = np.empty(10_000)
    for i in range(len(draws)):
        chosen = rng.integers(0, len(clusters), size=len(clusters))
        sample = [value for index in chosen for value in clusters[index]]
        draws[i] = float(np.mean(sample))
    return tuple(float(x) for x in np.quantile(draws, [0.025, 0.975]))


def summarize(rows: list[dict], label: str, benchmark: str, window: str, cost_bps: int = 0) -> dict:
    adjusted = [{**row, "car": float(row["car"]) - cost_bps / 10_000} for row in rows]
    values = np.array([row["car"] for row in adjusted], dtype=float)
    lo, hi = bootstrap_clustered_mean(adjusted)
    return {
        "period": label,
        "benchmark": benchmark,
        "window": window,
        "round_trip_cost_bps": cost_bps,
        "events": len(adjusted),
        "event_dates": len({row["day0"] for row in adjusted}),
        "mean_car": float(values.mean()),
        "median_car": float(np.median(values)),
        "share_positive": float((values > 0).mean()),
        "bootstrap_low": lo,
        "bootstrap_high": hi,
    }


def main() -> None:
    ROOT.mkdir(exist_ok=True)
    actual_hash = hashlib.sha256(MASK_FILE.read_bytes()).hexdigest()
    expected_hash = "decdd7dfd9123dca73f9aa6af148e889e53ea5afcd250f06ccc4b400af971400"
    if actual_hash != expected_hash:
        raise RuntimeError("Pinned membership-mask hash mismatch; refusing analysis")
    mask = pd.read_parquet(MASK_FILE)
    summary = json.loads((PANEL_DIR / "panel-summary.json").read_text())
    substitutions = summary["universe"]["substituted"]
    flagged = set(pd.read_csv(PANEL_DIR / "quality-flags.csv")["symbol"])
    benchmarks = {
        name: load_price(REPO / f"data/{name}.parquet", "adj_close") for name in BENCHMARKS
    }
    calendar = benchmarks["SPY"].index.intersection(benchmarks["IWM"].index)
    calendar = calendar.sort_values()
    price_cache = {}
    exits = []
    mask_values = mask.to_numpy(bool)
    for column, symbol in enumerate(mask.columns):
        transitions = np.flatnonzero(mask_values[:-1, column] & ~mask_values[1:, column])
        for index in transitions:
            last_member = mask.index[index]
            if last_member < FLOOR:
                continue
            day0 = mask.index[index + 1]
            source = substitutions.get(symbol, symbol)
            path = STORE / f"{source}.US.parquet"
            if source not in price_cache:
                price_cache[source] = load_price(path, "adjusted_close") if path.exists() else None
            price = price_cache[source]
            location = calendar.searchsorted(last_member, side="right")
            threshold = calendar[location + 4] if location + 4 < len(calendar) else pd.NaT
            later = (
                price is not None and pd.notna(threshold) and bool((price.index >= threshold).any())
            )
            category = "discretionary deletion" if later else "acquisition or delisting"
            exits.append(
                {
                    "symbol": symbol,
                    "price_symbol": source,
                    "last_member_date": last_member.date().isoformat(),
                    "day0": day0.date().isoformat(),
                    "year": last_member.year,
                    "classification": category,
                    "fifth_session_after_exit": threshold.date().isoformat()
                    if pd.notna(threshold)
                    else "",
                    "last_price_date": price.index.max().date().isoformat()
                    if price is not None and len(price)
                    else "",
                    "quality_flagged_symbol": symbol in flagged,
                }
            )
    exits.sort(key=lambda row: (row["last_member_date"], row["symbol"]))
    write_csv("exit_list.csv", exits)
    counts = Counter((row["year"], row["classification"]) for row in exits)
    count_rows = [
        {"year": year, "classification": category, "exits": count}
        for (year, category), count in sorted(counts.items())
    ]
    write_csv("counts_by_year.csv", count_rows)

    coverage = []
    event_cars = []
    for row in exits:
        if row["classification"] != "discretionary deletion":
            continue
        day0 = pd.Timestamp(row["day0"])
        position = calendar.get_indexer([day0])[0]
        reason = ""
        if position < 60 or position + 60 >= len(calendar):
            reason = "benchmark calendar lacks full -60/+60 sessions"
        else:
            dates = calendar[position - 60 : position + 61]
            price = price_cache[row["price_symbol"]]
            missing = dates.difference(price.index)
            if len(missing):
                reason = (
                    f"EODHD missing {len(missing)} required sessions; first={missing[0].date()}"
                )
            else:
                levels = price.loc[dates]
                if not np.isfinite(levels.to_numpy()).all():
                    reason = "EODHD nonfinite adjusted close"
        coverage.append({**row, "full_coverage": not bool(reason), "coverage_failure": reason})
        if reason:
            continue
        asset_returns = price.loc[dates].pct_change()
        for benchmark in BENCHMARKS:
            benchmark_returns = benchmarks[benchmark].loc[dates].pct_change()
            abnormal = asset_returns - benchmark_returns
            for window, (start, end) in WINDOWS.items():
                values = abnormal.iloc[60 + start : 60 + end + 1]
                event_cars.append(
                    {
                        "symbol": row["symbol"],
                        "day0": row["day0"],
                        "last_member_date": row["last_member_date"],
                        "year": row["year"],
                        "benchmark": benchmark,
                        "window": window,
                        "car": float(values.sum()),
                        "quality_flagged_symbol": row["quality_flagged_symbol"],
                    }
                )
    write_csv("coverage.csv", coverage)
    write_csv("event_cars.csv", event_cars)
    results = []
    for period, selected in (
        ("all", event_cars),
        ("2012-2018", [r for r in event_cars if r["year"] <= 2018]),
        ("2019-present", [r for r in event_cars if r["year"] >= 2019]),
    ):
        for benchmark in BENCHMARKS:
            for window in WINDOWS:
                subset = [
                    r for r in selected if r["benchmark"] == benchmark and r["window"] == window
                ]
                if not subset:
                    continue
                results.append(summarize(subset, period, benchmark, window))
                if window == "post_1_20":
                    for cost in (10, 25):
                        results.append(summarize(subset, period, benchmark, window, cost))
    write_csv("car_summary.csv", results)
    metadata = {
        "membership_sha256": actual_hash,
        "membership_end": str(mask.index.max().date()),
        "eodhd_floor": str(FLOOR.date()),
        "exits": len(exits),
        "discretionary": sum(r["classification"] == "discretionary deletion" for r in exits),
        "acquisition_or_delisting": sum(
            r["classification"] == "acquisition or delisting" for r in exits
        ),
        "discretionary_full_coverage": sum(r["full_coverage"] for r in coverage),
        "discretionary_coverage_failures": sum(not r["full_coverage"] for r in coverage),
        "quality_flagged_in_covered_discretionary": sum(
            r["quality_flagged_symbol"] and r["full_coverage"] for r in coverage
        ),
    }
    (ROOT / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
