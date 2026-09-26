"""Re-adjudicate evidence-batch01 under the signed date-admissibility rule.

Read-only. Reads the v9 manifest, the batch01 evidence, and the raw bars of the
files batch01 measured; writes a report directory. It builds no panel, changes
no price, runs no backtest, applies no approval, and writes nothing under
`journal/`.

    .venv/bin/python scripts/run_date_admissibility.py \
        --manifest reports/security-resolver/2026-09-06-v9-resolver/manifest.json \
        --batch01  reports/security-resolver/2026-09-06-evidence-batch01 \
        --out      reports/security-resolver/2026-09-07-date-admissibility
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland.live.resolver_multiplicity import (  # noqa: E402
    VENDOR_FLOORS,
    ManifestBoundaries,
    date_admissibility,
)
from woodland.live.resolver_numeric import BANDS, NumericCheck, check  # noqa: E402

# --------------------------------------------------------------------------
# The retrieved numbers, transcribed from batch01's own citations. Nothing here
# is new retrieval: each value already appears in `citation_claim` or
# `additional_price_check` of the row it belongs to. `counterpart=False` marks a
# retrieved number that does not predict a closing price.
# --------------------------------------------------------------------------
FINGERPRINTS: dict[str, dict[str, Any]] = {
    "DOW_old": dict(
        kind="exact_close", predicted=66.65, boundary="last",
        source="cited Dow closing price on the merger completion date",
    ),
    "CA_old": dict(
        kind="cash", predicted=44.50, boundary="last",
        source="cited all-cash consideration, Broadcom/CA",
    ),
    "AGN": dict(
        kind="stock", predicted=120.30 + 0.866 * 83.96, boundary="last",
        source="cited $120.30 cash + 0.866 x cited ABBV same-event close $83.96",
    ),
    "HCA": dict(
        kind="ipo_offering", predicted=30.00, boundary="first",
        source="cited IPO offering price $30",
    ),
    "KMI": dict(
        kind="ipo_offering", predicted=30.00, boundary="first",
        source="cited IPO offering price $30",
    ),
    "APC_old": dict(
        kind="stock", predicted=59.0 + 0.2934 * 46.31, boundary="last", counterpart=False,
        source="cited $59 cash + 0.2934 x OXY acquisition-date AVERAGE price $46.31",
        note="an average valuation price is not a closing-price prediction",
    ),
    "STI_old": dict(
        kind="stock", predicted=1.295 * 54.24, boundary="last", counterpart=False,
        source="1.295 x BBT_old close 54.24 taken from this store, not from a citation",
        note="acquirer close is read from the price store, not independently cited; "
             "corroborating one unverified file with another is one channel, not two",
    ),
}

DATE_ONLY_NO_NUMBER = {
    "CF": "listing date cited; no offering price retrieved",
    "DG": "IPO date cited; no offering price retrieved",
    "HLT": "listing date cited; no offering price retrieved",
    "LB_old1::segment2": "separation date cited; no consideration figure retrieved",
    "RTN": "exchange ratio 2.3348 RTX cited, but no RTX same-event close retrieved",
    "BBT_old": "completion date cited; BB&T was the acquirer, no consideration on its own shares",
    "TMK": "rename/ticker change cited; a rename carries no consideration figure",
    "PX_old": "one-for-one with LIN cited; a 1:1 ratio predicts no closing price",
    "CEG_old": "0.93 EXC cited, but no EXC same-event close retrieved",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def raw_bounds(store: Path, storage_symbol: str) -> dict[str, Any]:
    """First and last raw close of a file, with the hash checked either side."""
    path = store / f"{storage_symbol}.US.parquet"
    before = path.stat()
    digest = sha256(path.read_bytes())
    frame = pd.read_parquet(path, columns=["date", "close"]).sort_values("date")
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f"price file changed during read: {storage_symbol}")
    return dict(
        sha256=digest,
        first_date=str(pd.Timestamp(frame["date"].iloc[0]).date()),
        first_close=float(frame["close"].iloc[0]),
        last_date=str(pd.Timestamp(frame["date"].iloc[-1]).date()),
        last_close=float(frame["close"].iloc[-1]),
        bar_count=int(len(frame)),
    )


def segment_close(store: Path, storage_symbol: str, on: str) -> float | None:
    """Raw close on one date, for a segment whose bound is not the file's bound."""
    frame = pd.read_parquet(store / f"{storage_symbol}.US.parquet", columns=["date", "close"])
    hit = frame[frame["date"].astype(str).str[:10] == on]
    return float(hit["close"].iloc[0]) if len(hit) else None


def pivot_of(prediction: str) -> str | None:
    if prediction.startswith("last date"):
        return "last"
    if prediction.startswith("first date"):
        return "first"
    return None


def adjudicate(
    row: dict[str, Any], boundaries: ManifestBoundaries, store: Path
) -> dict[str, Any]:
    """One packet row, under the signed rule."""
    locator = row["candidate_symbol"]
    counts = boundaries.row_counts(locator, row.get("first_date"), row.get("last_date"))
    boundary = pivot_of(row.get("prediction", ""))
    out: dict[str, Any] = {
        "constituent_symbol": row["constituent_symbol"],
        "candidate_symbol": locator,
        "batch01_verdict": row["identity_verdict"],
        **{k: counts[k] for k in counts if k != "locator"},
        "pivot_boundary": boundary or "",
        "pivot_date": counts.get(f"{boundary}_bar") if boundary else None,
        "pivot_multiplicity": counts.get(f"{boundary}_multiplicity") if boundary else None,
    }

    if row["identity_verdict"] != "accept":
        out.update(verdict="unknown", confidence="low", numeric_kind="", numeric_outcome="",
                   numeric_predicted="", numeric_observed="", numeric_residual="",
                   reason="not an accept in batch01; unchanged by this rule")
        return out

    if boundary is None:
        out.update(verdict="unknown", confidence="low", numeric_kind="", numeric_outcome="",
                   numeric_predicted="", numeric_observed="", numeric_residual="",
                   reason="citation predicts no bar date; a date match cannot be tested")
        return out

    rule = date_admissibility(out["pivot_date"], out["pivot_multiplicity"])
    out["date_rule_verdict"] = rule.verdict
    out["date_rule_reason"] = rule.reason

    if rule.verdict == "inadmissible":
        out.update(verdict="unknown", confidence="low", numeric_kind="", numeric_outcome="",
                   numeric_predicted="", numeric_observed="", numeric_residual="",
                   reason=rule.reason)
        return out

    if rule.verdict == "sufficient":
        out.update(verdict="accept", confidence=rule.confidence, numeric_kind="",
                   numeric_outcome="not_required", numeric_predicted="", numeric_observed="",
                   numeric_residual="", reason=rule.reason)
        return out

    # Numeric fingerprint required.
    spec = FINGERPRINTS.get(locator)
    if spec is None:
        why = DATE_ONLY_NO_NUMBER.get(locator, "no number retrieved")
        out.update(verdict="unknown", confidence="low", numeric_kind="",
                   numeric_outcome="unknown", numeric_predicted="", numeric_observed="",
                   numeric_residual="", reason=f"{rule.reason}; {why}")
        return out

    storage = counts["storage_symbol"]
    which = spec["boundary"]
    bound_date = out["pivot_date"]
    bounds = raw_bounds(store, storage)
    observed = (
        bounds[f"{which}_close"]
        if bounds[f"{which}_date"] == bound_date
        else segment_close(store, storage, bound_date)
    )
    result: NumericCheck = check(
        spec["kind"], spec["predicted"], observed,
        counterpart=spec.get("counterpart", True), note=spec.get("note", ""),
    )
    out.update(
        numeric_kind=result.kind,
        numeric_outcome=result.outcome,
        numeric_predicted=round(result.predicted, 6) if result.predicted is not None else "",
        numeric_observed=result.observed if result.observed is not None else "",
        numeric_residual=round(result.residual, 6) if result.residual is not None else "",
        numeric_source=spec["source"],
        numeric_band=f"{result.band_mode} {result.band}",
    )
    if result.outcome == "agrees":
        confidence = "medium" if result.kind == "ipo_offering" else "high"
        out.update(verdict="accept", confidence=confidence,
                   reason=f"{rule.reason}; fingerprint agrees ({result.reason})")
    else:
        out.update(verdict="unknown", confidence="low",
                   reason=f"{rule.reason}; fingerprint {result.outcome} ({result.reason})")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--batch01", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text())
    store = Path(manifest["store"])
    boundaries = ManifestBoundaries(manifest)
    evidence = json.loads((args.batch01 / "evidence.json").read_text())

    rows = [adjudicate(r, boundaries, store) for r in evidence]
    args.out.mkdir(parents=True, exist_ok=True)

    fields = sorted({k for r in rows for k in r})
    lead = ["constituent_symbol", "candidate_symbol", "batch01_verdict", "verdict", "confidence",
            "pivot_boundary", "pivot_date", "pivot_multiplicity",
            "first_bar", "first_multiplicity", "last_bar", "last_multiplicity"]
    order = lead + [f for f in fields if f not in lead]
    with (args.out / "admissibility.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=order, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in order})
    (args.out / "admissibility.json").write_text(json.dumps(rows, indent=2, default=str))

    # Store-wide census: the measurement the signed decision rests on, recomputed
    # here so the rule and its justification are checked by the same command.
    census = {}
    for boundary in ("first", "last"):
        counter = boundaries.counter(boundary)
        total = len(boundaries.readable)
        census[boundary] = {
            "distinct_dates": len(counter),
            "files_with_unique_date": sum(1 for c in counter.values() if c == 1),
            "pct_unique": round(100.0 * sum(1 for c in counter.values() if c == 1) / total, 2),
            "pct_shared_by_more_than_100": round(
                100.0 * sum(c for c in counter.values() if c > 100) / total, 2),
            "largest": [
                {"date": d, "files": c} for d, c in counter.most_common(5)
            ],
        }
    census["vendor_floors"] = {
        floor: {"as_first_bar": boundaries.first_counts.get(floor, 0),
                "as_last_bar": boundaries.last_counts.get(floor, 0)}
        for floor in sorted(VENDOR_FLOORS)
    }
    (args.out / "multiplicity-census.json").write_text(json.dumps(census, indent=2))

    accepts = [r for r in rows if r["batch01_verdict"] == "accept"]
    survivors = [r for r in accepts if r["verdict"] == "accept"]
    returned = [r for r in accepts if r["verdict"] != "accept"]
    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "supersedes": "reports/security-resolver/2026-09-06-evidence-batch01",
        "manifest_source": str(args.manifest),
        "manifest_sha256": sha256(args.manifest.read_bytes()),
        "evidence_sha256": sha256((args.batch01 / "evidence.json").read_bytes()),
        "readable_manifest_files": len(boundaries.readable),
        "listed_parquet_files": boundaries.listed,
        "vendor_floors": sorted(VENDOR_FLOORS),
        "bands": {k: {"mode": v[0], "value": v[1], "label": v[2]} for k, v in BANDS.items()},
        "batch01_accepts": len(accepts),
        "accepts_surviving": len(survivors),
        "accepts_returned_to_unknown": len(returned),
        "surviving": [
            {"candidate": r["candidate_symbol"], "confidence": r["confidence"],
             "basis": r["reason"]} for r in survivors
        ],
        "returned_to_unknown": [
            {"candidate": r["candidate_symbol"], "reason": r["reason"]} for r in returned
        ],
        "multiplicity_census": census,
        "note": "Returning to unknown is not a rejection. No approval was applied.",
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"{len(rows)} packet rows adjudicated, {len(accepts)} were batch01 accepts")
    print(f"  surviving : {len(survivors)}  {[r['candidate_symbol'] for r in survivors]}")
    print(f"  to unknown: {len(returned)}  {[r['candidate_symbol'] for r in returned]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
