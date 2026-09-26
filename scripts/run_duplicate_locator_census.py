"""Duplicate-locator census over the automatically resolved symbols.

For every symbol the resolver matched on the automatic path, search the whole
store for another file covering substantially the same span for the same entity,
and measure how far the two disagree.

**Candidates are generated from prices, never from tickers or catalog names.**
The reference case is `FISV`/`FI`, which share no ticker string and are linked by
nothing in the catalog that may be trusted; a name-based search would not find
them, and looking an entity up by ticker is the circularity the resolver exists
to avoid. Two files are proposed as contenders when they carry the *same closing
price on the same date* often enough that coincidence is implausible.

Agreement is then measured on raw close, adjusted close and volume separately.
That split is the point of the census: `FISV`/`FI` agree on 80.0% of 9,858
overlapping raw closes and on **20.9%** of adjusted closes, and adjusted close is
what returns are computed from. A wrong locator is therefore nearly invisible on
the price column and produces a silently different return series.

Read-only. Builds no panel, changes no price, applies nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Two files are a candidate pair when they share at least this many exact
# (date, close) tokens on the probe calendar. Sharing five exact prices on five
# specific dates by coincidence is not a realistic failure mode.
MIN_SHARED_TOKENS = 5
PROBE_MODULUS = 20          # sample roughly every 20th calendar day
MIN_OVERLAP_BARS = 250      # "substantially the same span": about a trading year
AGREEMENT_RTOL = 1e-6       # effectively exact; reproduces the reference figures

# Token co-occurrence alone is far too weak a filter. With 50,806 files and
# prices quantised to six significant figures, five coincidental (date, close)
# collisions are common - AEP and ES share tokens and agree on 0.5% of closes.
# A genuine same-entity pair records the same traded prices: FISV/FI agree on
# 99.0% of overlapping closes at 1e-3. Qualification is on that, not on tokens.
SAME_ENTITY_CLOSE_RTOL = 1e-3
SAME_ENTITY_MIN_CLOSE_AGREEMENT = 0.90

# Exact agreement on the adjusted LEVEL is degenerate as a contamination test:
# each file's factor reaches 1.0 at its own final bar, so two files ending on
# different dates disagree on every level by construction. What matters to the
# panel is whether the implied RETURNS differ. If two files are one series under
# two normalisations, adj_a/adj_b is constant across the overlap and this range
# is 1.0. FISV/FI ranges 0.999918 to 1.402309, so they are not one series.
RATIO_RANGE_TOLERANCE = 1.001
GATE_FRACTION = 0.05             # >5% of symbols diverging stops the panel


def probe_tokens(path: Path) -> tuple[str, dict[str, Any]] | None:
    """Bounds, bar count, and exact (date, close) tokens on the probe calendar."""
    symbol = path.name.split(".")[0]
    try:
        frame = pd.read_parquet(path, columns=["date", "close"])
    except Exception:
        return None
    if not len(frame):
        return None
    dates = pd.to_datetime(frame["date"])
    close = pd.to_numeric(frame["close"], errors="coerce")
    keep = close.notna() & (close > 0)
    if not keep.any():
        return None
    ordinals = dates[keep].map(pd.Timestamp.toordinal).to_numpy()
    sampled = ordinals % PROBE_MODULUS == 0
    values = close[keep].to_numpy()[sampled]
    tokens = [f"{o}|{v:.6g}" for o, v in zip(ordinals[sampled], values, strict=True)]
    return symbol, {
        "first": str(dates.min().date()),
        "last": str(dates.max().date()),
        "bars": int(len(frame)),
        "tokens": tokens,
    }


def measure_pair(store: Path, left: str, right: str) -> dict[str, Any]:
    """Overlap length and per-column agreement between two locators."""
    columns = ["date", "close", "adjusted_close", "volume"]
    a = pd.read_parquet(store / f"{left}.US.parquet", columns=columns)
    b = pd.read_parquet(store / f"{right}.US.parquet", columns=columns)
    merged = a.merge(b, on="date", suffixes=("_a", "_b")).sort_values("date")
    out: dict[str, Any] = {"overlap_bars": int(len(merged))}
    for column in ("close", "adjusted_close", "volume"):
        if not len(merged):
            out[f"{column}_agreement"] = None
            continue
        x = pd.to_numeric(merged[f"{column}_a"], errors="coerce").to_numpy(float)
        y = pd.to_numeric(merged[f"{column}_b"], errors="coerce").to_numpy(float)
        valid = np.isfinite(x) & np.isfinite(y)
        out[f"{column}_agreement"] = (
            float(np.isclose(x[valid], y[valid], rtol=AGREEMENT_RTOL, atol=0).mean())
            if valid.any() else None
        )
    # Loose close agreement qualifies the pair as the same entity at all.
    if len(merged):
        x = pd.to_numeric(merged["close_a"], errors="coerce").to_numpy(float)
        y = pd.to_numeric(merged["close_b"], errors="coerce").to_numpy(float)
        valid = np.isfinite(x) & np.isfinite(y)
        out["close_agreement_loose"] = (
            float(np.isclose(x[valid], y[valid], rtol=SAME_ENTITY_CLOSE_RTOL, atol=0).mean())
            if valid.any() else None)
    else:
        out["close_agreement_loose"] = None
    # Return divergence: the measure that actually reaches the panel.
    aa = pd.to_numeric(merged["adjusted_close_a"], errors="coerce").to_numpy(float)
    bb = pd.to_numeric(merged["adjusted_close_b"], errors="coerce").to_numpy(float)
    good = np.isfinite(aa) & np.isfinite(bb) & (aa > 0) & (bb > 0)
    if good.sum() >= 3:
        ratio = aa[good] / bb[good]
        out["adjusted_ratio_min"] = float(ratio.min())
        out["adjusted_ratio_max"] = float(ratio.max())
        out["adjusted_ratio_range"] = float(ratio.max() / ratio.min())
        ra = np.diff(aa[good]) / aa[good][:-1]
        rb = np.diff(bb[good]) / bb[good][:-1]
        fine = np.isfinite(ra) & np.isfinite(rb)
        out["adjusted_return_agreement"] = (
            float(np.isclose(ra[fine], rb[fine], rtol=0, atol=1e-6).mean())
            if fine.any() else None)
        out["adjusted_return_correlation"] = (
            float(np.corrcoef(ra[fine], rb[fine])[0, 1])
            if fine.sum() > 2 and ra[fine].std() > 0 and rb[fine].std() > 0 else None)
    else:
        for key in ("adjusted_ratio_min", "adjusted_ratio_max", "adjusted_ratio_range",
                    "adjusted_return_agreement", "adjusted_return_correlation"):
            out[key] = None
    return out


def prefer(candidates: list[dict[str, Any]], start: str, end: str) -> str:
    """Signed preferred-locator rule: spans the membership window, then bar count.

    Deterministic by construction — the final key is the symbol itself, so two
    files with identical spans and identical bar counts still order stably.
    """
    def key(entry: dict[str, Any]) -> tuple[int, int, str]:
        spans = entry["first"] <= start and entry["last"] >= end
        return (0 if spans else 1, -entry["bars"], entry["symbol"])
    return str(sorted(candidates, key=key)[0]["symbol"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.resolution.read_text().splitlines() if line.strip()]
    resolved = [r for r in rows if r.get("status") == "resolved"]
    automatic = [r for r in resolved if r.get("match_basis") == "unique_live_candidate"]
    windows: dict[str, dict[str, Any]] = {}
    for row in automatic:
        entry = windows.setdefault(
            row["price_symbol"],
            {"constituents": set(), "start": row["start"], "end": row["end"], "symbol_years": 0},
        )
        entry["constituents"].add(row["constituent_symbol"])
        entry["start"] = min(entry["start"], row["start"])
        entry["end"] = max(entry["end"], row["end"])
        entry["symbol_years"] += 1
    targets = sorted(windows)
    print(f"{len(targets)} automatically resolved locators ({len(automatic)} rows)")

    print("indexing the store on exact (date, close) tokens ...")
    files = sorted(args.store.glob("*.parquet"))
    catalog: dict[str, dict[str, Any]] = {}
    index: dict[str, list[str]] = defaultdict(list)
    with ProcessPoolExecutor(max_workers=8) as executor:
        for done, result in enumerate(executor.map(probe_tokens, files, chunksize=64), 1):
            if result is None:
                continue
            symbol, info = result
            catalog[symbol] = info
            for token in info["tokens"]:
                index[token].append(symbol)
            if done % 10000 == 0:
                print(f"  {done}/{len(files)}")
    print(f"  indexed {len(catalog)} files, {len(index)} distinct tokens")

    print("finding contenders ...")
    rejected = 0
    pairs: list[dict[str, Any]] = []
    census: list[dict[str, Any]] = []
    for target in targets:
        found = catalog.get(target)
        if found is None:
            census.append({"locator": target, "in_store": False, "contenders": 0})
            continue
        info = found
        shared: dict[str, int] = defaultdict(int)
        for token in info["tokens"]:
            for other in index[token]:
                if other != target:
                    shared[other] += 1
        window = windows[target]
        contenders = []
        for other, count in shared.items():
            if count < MIN_SHARED_TOKENS:
                continue
            measured = measure_pair(args.store, target, other)
            if measured["overlap_bars"] < MIN_OVERLAP_BARS:
                continue
            loose = measured["close_agreement_loose"]
            if loose is None or loose < SAME_ENTITY_MIN_CLOSE_AGREEMENT:
                rejected += 1
                continue
            entry = {
                "locator": target,
                "contender": other,
                "shared_tokens": count,
                "membership_start": window["start"],
                "membership_end": window["end"],
                "locator_first": info["first"], "locator_last": info["last"],
                "locator_bars": info["bars"],
                "contender_first": catalog[other]["first"],
                "contender_last": catalog[other]["last"],
                "contender_bars": catalog[other]["bars"],
                **measured,
            }
            contenders.append(entry)
        if contenders:
            options = [{"symbol": target, **info}] + [
                {"symbol": c["contender"], **catalog[c["contender"]]} for c in contenders
            ]
            preferred = prefer(options, window["start"], window["end"])
            for entry in contenders:
                entry["preferred_locator"] = preferred
                entry["preferred_is_resolved"] = preferred == target
                span = entry["adjusted_ratio_range"]
                entry["diverges"] = span is not None and span > RATIO_RANGE_TOLERANCE
            pairs.extend(contenders)
        worst = max(
            (c["adjusted_ratio_range"] for c in contenders
             if c["adjusted_ratio_range"] is not None), default=None)
        census.append({
            "locator": target, "in_store": True,
            "constituent_symbols": ",".join(sorted(window["constituents"])),
            "symbol_years": window["symbol_years"],
            "membership_start": window["start"], "membership_end": window["end"],
            "contenders": len(contenders),
            "worst_adjusted_ratio_range": worst,
            "worst_adjusted_level_agreement": min(
                (c["adjusted_close_agreement"] for c in contenders
                 if c["adjusted_close_agreement"] is not None), default=None),
            "diverges": bool(contenders) and worst is not None
            and worst > RATIO_RANGE_TOLERANCE,
            "preferred_locator": contenders[0]["preferred_locator"] if contenders else target,
            "preferred_is_resolved": contenders[0]["preferred_is_resolved"]
            if contenders else True,
        })

    args.out.mkdir(parents=True, exist_ok=True)
    if pairs:
        with (args.out / "duplicate-locators.csv").open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(pairs[0]))
            writer.writeheader()
            writer.writerows(pairs)
    with (args.out / "census.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(census[0]))
        writer.writeheader()
        writer.writerows(census)

    with_contender = [c for c in census if c["contenders"]]
    diverging = [c for c in with_contender if c["diverges"]]
    print(f"  {rejected} token collisions rejected as different entities")
    wrong_preference = [c for c in with_contender if not c["preferred_is_resolved"]]
    fraction = len(diverging) / len(targets) if targets else 0.0
    summary = {
        "automatic_locators": len(targets),
        "automatic_rows": len(automatic),
        "method": {
            "candidate_generation": "exact (date, close) token co-occurrence; never ticker "
                                    "strings or catalog names",
            "min_shared_tokens": MIN_SHARED_TOKENS,
            "probe_modulus_days": PROBE_MODULUS,
            "min_overlap_bars": MIN_OVERLAP_BARS,
            "agreement_rtol": AGREEMENT_RTOL,
            "same_entity_qualification": f"close agreement >= "
                                         f"{SAME_ENTITY_MIN_CLOSE_AGREEMENT} at rtol "
                                         f"{SAME_ENTITY_CLOSE_RTOL}",
            "divergence_test": "range of adjusted_a/adjusted_b across the overlap; 1.0 means "
                               "one series under two normalisations, >1 means different returns",
            "ratio_range_tolerance": RATIO_RANGE_TOLERANCE,
        },
        "locators_with_contender": len(with_contender),
        "contender_pairs": len(pairs),
        "token_collisions_rejected_as_different_entities": rejected,
        "locators_with_diverging_returns": len(diverging),
        "diverging_fraction": round(fraction, 6),
        "gate_threshold": GATE_FRACTION,
        "gate": "PROCEED" if fraction < GATE_FRACTION else "STOP",
        "preferred_differs_from_resolved": len(wrong_preference),
        "preferred_differs_list": [c["locator"] for c in wrong_preference],
        "diverging_list": [
            {"locator": c["locator"],
             "worst_adjusted_ratio_range": c["worst_adjusted_ratio_range"],
             "worst_adjusted_level_agreement": c["worst_adjusted_level_agreement"],
             "symbol_years": c["symbol_years"]}
            for c in sorted(diverging,
                            key=lambda c: -(c["worst_adjusted_ratio_range"] or 0))
        ],
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nlocators with a contender          : {len(with_contender)}")
    print(f"diverging returns                  : {len(diverging)}"
          f"  = {100 * fraction:.2f}% of {len(targets)}")
    print(f"preferred locator != resolved      : {len(wrong_preference)}")
    print(f"GATE: {summary['gate']} (threshold {100 * GATE_FRACTION:.0f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
