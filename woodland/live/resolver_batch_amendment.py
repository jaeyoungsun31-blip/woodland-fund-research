"""Recheck batch01 endpoint hypotheses against the signed date policy, read-only."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from woodland.live.resolver_date_evidence import (
    date_admissibility,
    endpoint_counts,
    numerical_check,
)


def run(batch: Path, manifest_path: Path, sources_path: Path, out: Path) -> None:
    if Path("data").resolve() == out.resolve() or Path("data").resolve() in out.resolve().parents:
        raise ValueError("Output must be outside data")
    out.mkdir(exist_ok=True, parents=True)
    if (out / "evidence.json").exists():
        raise FileExistsError("Do not overwrite an existing amendment")
    manifest = json.loads(manifest_path.read_text())
    counts = endpoint_counts(manifest)
    sources = json.loads(sources_path.read_text())
    rows = json.loads(batch.read_text())
    hashes = {}
    for r in rows:
        path = Path(r["price_file"])
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != r["price_sha256"]:
            raise ValueError("Price file changed since original batch: " + r["candidate_symbol"])
        hashes[str(path)] = digest
        frame = pd.read_parquet(path)
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
        frame = frame[(frame.date >= r["first_date"]) & (frame.date <= r["last_date"])].sort_values(
            "date"
        )
        if frame.empty:
            raise ValueError("Missing original segment")
        r["previous_identity_verdict"] = r["identity_verdict"]
        r["first_date_multiplicity"] = counts["first"][r["first_date"]]
        r["last_date_multiplicity"] = counts["last"][r["last_date"]]
        r["pivot_side"] = ""
        r["pivot_date"] = ""
        r["pivot_multiplicity"] = None
        r["numeric_prediction"] = sources.get(r["candidate_symbol"], {})
        r["numeric_check"] = {}
        r["numerical_citation"] = r["numeric_prediction"].get("citation", "")
        r["predicted_number"] = r["numeric_prediction"].get("expected")
        r["observed_number"] = None
        r["numerical_lower"] = None
        r["numerical_upper"] = None
        r["numerical_agrees"] = None
        r["identity_confidence"] = "low"
        r["evidence_basis"] = ""
        r["date_agrees"] = False
        r["coverage_verdict"] = r["coverage"]
        r["coverage_notes"] = r["coverage_basis"]
        if r["previous_identity_verdict"] != "accept":
            # New hypotheses on the original unknowns are outside this retroactive pass.
            r["pivot_notes"] = (
                "No previously accepted endpoint hypothesis; "
                "both endpoint multiplicities are display context only."
            )
            continue
        side = "first" if r["prediction"].startswith("first") else "last"
        expected_date = r["prediction"].split(" = ")[1][:10]
        observed = frame.iloc[0] if side == "first" else frame.iloc[-1]
        r.update(
            pivot_side=side,
            pivot_date=expected_date,
            pivot_multiplicity=counts[side][expected_date],
            date_agrees=str(observed.date) == expected_date,
            pivot_notes="Original-file endpoint counter; segments never inflate multiplicity.",
        )
        check = (
            numerical_check(r["numeric_prediction"], float(observed.close))
            if r["numeric_prediction"]
            else {}
        )
        r["numeric_check"] = check
        r["observed_number"] = float(observed.close)
        r["numerical_lower"] = check.get("lower")
        r["numerical_upper"] = check.get("upper")
        r["numerical_agrees"] = check.get("agrees")
        verdict = date_admissibility(
            expected_date,
            r["pivot_multiplicity"],
            r["date_agrees"],
            r["citation_url"],
            bool(r["retrieval"]),
            check,
        )
        r.update(verdict)
        r["observed"] = json.dumps(
            dict(
                date=str(observed.date), close=float(observed.close), volume=float(observed.volume)
            )
        )
        r["agreement"] = "yes" if verdict["identity_verdict"] == "accept" else "not_established"
        if r["candidate_symbol"] == "CEG_old":
            r["pivot_notes"] += (
                " Multiplicity 3: signed 2–3 rule allows date-only at medium; "
                "no numeric upgrade claimed."
            )
    for file_name, digest in hashes.items():
        if hashlib.sha256(Path(file_name).read_bytes()).hexdigest() != digest:
            raise ValueError("Price changed while measuring")
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with (out / "review-packet.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(
            {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()}
            for r in rows
        )
    with (out / "manifest-date-multiplicities.csv").open("w", newline="") as f:
        date_writer = csv.writer(f)
        date_writer.writerow(["endpoint", "date", "original_file_count"])
        date_writer.writerows((side, day, count) for side in ("first", "last")
                         for day, count in sorted(counts[side].items()))
    (out / "evidence.json").write_text(json.dumps(rows, indent=2) + "\n")
    summary: dict[str, Any] = dict(
        supersedes=str(batch),
        manifest=str(manifest_path),
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        original_files=sum(counts["first"].values()),
        floor_first_counts={d: counts["first"][d] for d in ["1997-12-31", "1999-01-04"]},
        identity=dict(Counter(r["identity_verdict"] for r in rows)),
        confidence=dict(Counter(r["identity_confidence"] for r in rows)),
        basis=dict(Counter(r["evidence_basis"] for r in rows)),
        reverted_to_unknown=[
            r["candidate_symbol"]
            for r in rows
            if r["previous_identity_verdict"] == "accept" and r["identity_verdict"] == "unknown"
        ],
        raw_file_hashes_unchanged=len(hashes),
        a2_status="SIGNED",
        treatments_applied=0,
        panel_built=False,
        price_changes=False,
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "price-file-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["batch", "manifest", "sources", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    run(a.batch, a.manifest, a.sources, a.output)
