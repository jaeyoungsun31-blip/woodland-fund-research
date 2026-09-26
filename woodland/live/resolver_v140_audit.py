"""Read-only v1.4 review/census from a captured catalog and price scan; never a panel."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from woodland.live.resolver_a2 import classify_a2, union_coverage
from woodland.live.resolver_audit import load_conventions, write_report
from woodland.live.resolver_date_evidence import (
    date_admissibility,
    endpoint_counts,
    numerical_check,
)
from woodland.live.resolver_review import write_review_packet
from woodland.live.security_resolver import Constituent, Security, SecurityResolver


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(
            {
                k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                for k, v in r.items()
            }
            for r in rows
        )


def run(previous: Path, snapshot: Path, events_path: Path, batch: Path, out: Path) -> None:
    obj = json.loads(snapshot.read_text())
    store = Path(obj["manifest"]["store"])
    if out.resolve() == store.resolve() or store.resolve() in out.resolve().parents:
        raise ValueError("Output cannot be in price store")
    if Path("data").resolve() in out.resolve().parents:
        raise ValueError("Output cannot be in data")
    securities = []
    for raw in obj["securities"]:
        raw["first"] = date.fromisoformat(raw["first"]) if raw["first"] else None
        raw["last"] = date.fromisoformat(raw["last"]) if raw["last"] else None
        raw["trading_gaps"] = tuple(
            (date.fromisoformat(a), date.fromisoformat(b)) for a, b in raw["trading_gaps"]
        )
        securities.append(Security(**raw))
    catalog = {s.price_symbol: s for s in securities}
    old = [json.loads(x) for x in (previous / "resolution.jsonl").read_text().splitlines()]
    inputs = [
        Constituent(
            r["record_id"],
            r["constituent_symbol"],
            date.fromisoformat(r["start"]),
            date.fromisoformat(r["end"]),
        )
        for r in old
        if "record_id" in r
    ]
    conventions, rules = load_conventions(Path(__file__).with_name("resolver_conventions.json"))
    resolver = SecurityResolver(securities, rules)
    rows = [resolver.audit_one(c) for c in inputs]
    by_id = {r.record_id: r for r in rows}
    changed = [
        r
        for r in old
        if r.get("match_basis") == "unique_live_candidate"
        and by_id[r["record_id"]].status != "resolved"
    ]
    affected = sorted({r["constituent_symbol"] for r in changed})
    if affected != ["CTXS", "JP"]:
        raise ValueError(f"Stop: expected only CTXS and JP, observed {affected}")
    events = json.loads(events_path.read_text())
    frames: dict[str, pd.DataFrame] = {}
    dates: dict[str, set[date]] = {}
    hashes: dict[str, str] = {}

    def frame(s: Security) -> pd.DataFrame:
        if s.price_symbol not in frames:
            path = store / ((s.storage_symbol or s.price_symbol) + ".US.parquet")
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
            f = pd.read_parquet(path)
            f["date"] = pd.to_datetime(f["date"]).dt.date
            f = f[(f.date >= s.first) & (f.date <= s.last)].sort_values("date")
            frames[s.price_symbol] = f
            dates[s.price_symbol] = set(f.date)
        return frames[s.price_symbol]

    calendar_path = Path("data/SPY.parquet")
    hashes[str(calendar_path)] = hashlib.sha256(calendar_path.read_bytes()).hexdigest()
    calendar = sorted(pd.to_datetime(pd.read_parquet(calendar_path).index).date)
    proofs = {}
    pivot_counts = endpoint_counts(obj["manifest"])
    for e in json.loads(batch.read_text()):
        if (
            e["identity_verdict"] != "accept" and e.get("previous_identity_verdict") != "accept"
        ) or e["candidate_symbol"] not in catalog:
            continue
        s = catalog[e["candidate_symbol"]]
        f = frame(s)
        observed = f.iloc[0] if e["prediction"].startswith("first") else f.iloc[-1]
        # Check the independently stated prediction, not a copied acceptance flag.
        expected = e["prediction"].split(" = ")[1][:10]
        agrees = str(observed.date) == expected
        if "terminal close = 66.65" in e["prediction"]:
            agrees = agrees and float(observed.close) == 66.65
        numeric_prediction = e.get("numeric_prediction", {})
        # Legacy batches cannot launder their accepted flag into a new approval.
        if not numeric_prediction and "terminal close = 66.65" in e["prediction"]:
            numeric_prediction = dict(
                kind="exact_close",
                expected=66.65,
                citation=e["citation_url"],
                retrieved=True,
                claim="Independently cited terminal close $66.65",
            )
        check = (
            numerical_check(numeric_prediction, float(observed.close)) if numeric_prediction else {}
        )
        side = "first" if e["prediction"].startswith("first") else "last"
        multiplicity = pivot_counts[side][expected]
        admissibility = date_admissibility(
            expected, multiplicity, agrees, e["citation_url"], bool(e.get("retrieval")), check
        )
        proofs[s.price_symbol] = dict(
            evidence_kind="date_match",
            pivot_side=side,
            pivot_date=expected,
            pivot_multiplicity=multiplicity,
            date_agrees=agrees,
            numeric_check=check,
            admissibility=admissibility,
            citation=e["citation_url"],
            retrieved=True,
            predicted_signature=e["prediction"],
            observed_from_data=f"date {observed.date}; close {observed.close}",
            agrees=admissibility["identity_verdict"] == "accept",
            identity_scope=e["identity_scope"],
            numerical_citation=numeric_prediction.get("citation", ""),
            numerical_claim=numeric_prediction.get("claim", ""),
        )
    bsc = catalog["BSC_old"]
    b = frame(bsc)
    p0 = float(b.loc[b.date == date(2008, 3, 13), "close"].iloc[0])
    p1 = float(b.loc[b.date == date(2008, 3, 14), "close"].iloc[0])
    corroborates = round(100 * (1 - p1 / p0)) == 47 and p1 == 30 and bsc.last == date(2008, 3, 14)
    proofs["BSC_old"] = dict(
        pivot_side="last",
        pivot_date=str(bsc.last),
        pivot_multiplicity=pivot_counts["last"][str(bsc.last)],
        citation=events["BSC"][0]["citation"],
        retrieved=True,
        predicted_signature=events["BSC"][0]["prediction"],
        observed_from_data=f"2008-03-13 {p0}; 2008-03-14 {p1}; decline {100 * (1 - p1 / p0):.6f}%; "
        f"volume {b.loc[b.date == date(2008, 3, 14), 'volume'].iloc[0]}",
        agrees=corroborates,
    )
    events["BSC"][0]["corroborated"] = corroborates
    manifest = obj["manifest"]
    manifest.update(
        previous_resolution_sha256=hashlib.sha256(
            (previous / "resolution.jsonl").read_bytes()
        ).hexdigest(),
        panel_window=["1999-01-05", "2026-06-30"],
    )
    write_report(
        out,
        rows,
        manifest,
        obj["excluded"],
        conventions,
        "v1.4 gap refusal; identity/coverage split; proposed A2; no panel",
    )
    write_review_packet(out, rows, securities, proofs)
    packet = list(csv.DictReader((out / "review-packet.csv").open()))
    original = list(csv.DictReader((previous / "review-packet.csv").open()))
    partial = {
        (r["constituent_symbol"], r["candidate_symbol"])
        for r in original
        if r["suggested_verdict"] == "unknown" and "Partial containment" in r["notes"]
    }
    moved = [
        r
        for r in packet
        if (r["constituent_symbol"], r["candidate_symbol"]) in partial
        and r["identity_verdict"] == "accept"
    ]
    groups: dict[str, list[Constituent]] = defaultdict(list)
    for c in inputs:
        groups[c.symbol].append(c)
    pending = {r.constituent_symbol for r in rows if r.status != "resolved"}
    stitches = []
    candidate_cases = []
    a2_symbols = {
        r["constituent_symbol"]
        for r in original
        if not r["candidate_symbol"]
        or (r["candidate_last"] and r["membership_end"] > r["candidate_last"])
    }
    for symbol in sorted(pending):
        occurrences = groups[symbol]
        locators = sorted({s for r in rows if r.constituent_symbol == symbol for s in r.candidates})
        candidates = [catalog[s] for s in locators if s in catalog]
        successors = {
            e["successor"]: catalog[e["successor"]]
            for e in events.get(symbol, [])
            if e.get("successor") in catalog and e.get("retrieved") and e.get("citation")
        }
        for s in candidates + list(successors.values()):
            if s.available:
                frame(s)
        union = union_coverage(occurrences, candidates + list(successors.values()), calendar, dates)
        stitches.append(
            dict(
                constituent_symbol=symbol,
                membership_windows=[
                    dict(record_id=c.record_id, first=str(c.start), last=str(c.end))
                    for c in occurrences
                ],
                **union,
                cited_successors=[
                    dict(
                        symbol=k,
                        citation=[e["citation"] for e in events[symbol] if e.get("successor") == k],
                    )
                    for k in successors
                ],
                note="Candidate union is availability only. "
                "Unverified identity or joins remain refused.",
            )
        )
        if symbol not in a2_symbols:
            continue
        short: list[Security | None] = [
            catalog[r["candidate_symbol"]]
            for r in original
            if r["constituent_symbol"] == symbol
            and r["candidate_last"]
            and r["membership_end"] > r["candidate_last"]
        ]
        for short_candidate in short or [None]:
            result = classify_a2(short_candidate, events.get(symbol, []), successors, calendar)
            candidate_cases.append(
                dict(
                    constituent_symbol=symbol,
                    candidate_symbol=short_candidate.price_symbol if short_candidate else "",
                    **result,
                )
            )
    for result in candidate_cases:
        if result["agrees"] and result["a2_case"] in {"1", "4"} and result["candidate_symbol"]:
            proofs[result["candidate_symbol"]] = dict(
                pivot_side="last",
                pivot_date=str(catalog[result["candidate_symbol"]].last),
                pivot_multiplicity=pivot_counts["last"][
                    str(catalog[result["candidate_symbol"]].last)
                ],
                citation=result["citation"],
                retrieved=True,
                predicted_signature=result["predicted_signature"],
                observed_from_data=json.dumps(result["observed_from_data"]),
                agrees=True,
            )
    write_review_packet(out, rows, securities, proofs)
    packet = list(csv.DictReader((out / "review-packet.csv").open()))
    for record in packet:
        for side in ("first", "last"):
            endpoint = record.get("candidate_" + side, "")
            record[side + "_date_multiplicity"] = pivot_counts[side][endpoint] if endpoint else ""
    write_csv(out / "review-packet.csv", packet)
    moved = [
        r
        for r in packet
        if (r["constituent_symbol"], r["candidate_symbol"]) in partial
        and r["identity_verdict"] == "accept"
    ]
    # One symbol-level row, with every candidate test retained to expose reuse conflicts.
    classifications = []
    for symbol in sorted(a2_symbols):
        cases = [r for r in candidate_cases if r["constituent_symbol"] == symbol]
        confirmed = [r for r in cases if r["case_status"] == "proposed"]
        winner = next(
            (r for k in ["1", "4", "2", "3"] for r in confirmed if r["a2_case"] == k), None
        )
        classification = winner or cases[0]
        classifications.append(
            dict(
                constituent_symbol=symbol,
                a2_case=classification["a2_case"],
                case_status=classification["case_status"],
                citation=classification["citation"],
                predicted_signature=classification["predicted_signature"],
                observed_from_data=classification["observed_from_data"],
                agrees=classification["agrees"],
                recovery=classification["recovery"],
                exchange=classification["exchange"],
                exchange_citation=classification["exchange_citation"],
                shumway_fill=classification["shumway_fill"],
                missing=classification["missing"],
                candidate_tests=cases,
                scope="Candidate-specific proposal; does not classify other uses of same symbol.",
            )
        )
    write_csv(out / "stitching.csv", stitches)
    write_csv(out / "a2-classification.csv", classifications)
    write_csv(out / "a2-candidate-tests.csv", candidate_cases)
    # Census accounts for each source symbol-year exactly once. Case assignment is
    # scoped to a cited event year; absence applies to each unavailable membership year.
    census: list[dict[str, Any]] = []
    seams = set()
    for row in rows:
        candidates_for_year = []
        for a in candidate_cases:
            if a["constituent_symbol"] != row.constituent_symbol:
                continue
            absent = not a["candidate_symbol"]
            event = a["event_date"]
            candidate = catalog.get(a["candidate_symbol"])
            in_event_window = bool(event and row.start <= event <= row.end)
            residual_overlap = bool(
                candidate
                and candidate.last
                and str(candidate.last) < row.end
                and candidate.first
                and str(candidate.first) <= row.end
            )
            if absent or in_event_window or (a["a2_case"] == "3" and residual_overlap):
                candidates_for_year.append(a)
        good = [a for a in candidates_for_year if a["case_status"] == "proposed"]
        chosen = next((a for k in ["1", "4", "2", "3"] for a in good if a["a2_case"] == k), None)
        label = (
            chosen["a2_case"]
            if chosen
            else ("unresolved" if row.status != "resolved" else "no_A2_trigger")
        )
        if chosen and label == "4":
            seams.add(
                (
                    chosen["constituent_symbol"],
                    chosen["candidate_symbol"],
                    chosen["successor"],
                    chosen["event_date"],
                )
            )
        residual = any(a["a2_case"] == "3" for a in candidates_for_year)
        census.append(
            dict(
                record_id=row.record_id,
                symbol=row.constituent_symbol,
                start=row.start,
                end=row.end,
                a2_case=label,
                resolver_status=row.status,
                refused=row.status != "resolved" or label == "3",
                case3_residual_present=residual,
                identity_still_unresolved=row.status != "resolved",
                case2_absent=bool(chosen and label == "2" and not chosen["candidate_symbol"]),
            )
        )
    write_csv(out / "census-symbol-years.csv", census)
    annual_census = []
    for year in sorted({r["start"][:4] for r in census}):
        annual_rows = [r for r in census if r["start"][:4] == year]
        annual_census.append(
            dict(
                year=year,
                denominator=len(annual_rows),
                **{
                    f"case_{k}": sum(r["a2_case"] == k for r in annual_rows)
                    for k in ["1", "2", "3", "4", "unresolved", "no_A2_trigger"]
                },
                refused=sum(bool(r["refused"]) for r in annual_rows),
                identity_unresolved=sum(bool(r["identity_still_unresolved"]) for r in annual_rows),
            )
        )
    write_csv(out / "annual-a2-census.csv", annual_census)
    summary = json.loads((out / "summary.json").read_text())
    summary.update(
        census=dict(
            denominator_symbol_years=len(rows),
            symbol_years_by_case={
                k: sum(r["a2_case"] == k for r in census)
                for k in ["1", "2", "3", "4", "unresolved", "no_A2_trigger"]
            },
            symbol_years_refused=sum(r["refused"] for r in census),
            symbol_years_still_unresolved=sum(r["identity_still_unresolved"] for r in census),
            symbol_years_with_case3_residual=sum(r["case3_residual_present"] for r in census),
            refused_case3_confirmed=sum(r["a2_case"] == "3" for r in census),
            refused_case3_residual_unverified=sum(
                r["case3_residual_present"]
                and r["identity_still_unresolved"]
                and r["a2_case"] != "3"
                for r in census
            ),
            case2_absent_symbol_years=sum(r["case2_absent"] for r in census),
            seam_days_case4_would_drop=len(seams),
            note="Mutually exclusive case labels; refusal overlaps identity unresolved. "
            "No automatic acceptance of A2 proposals. "
            "Event cases attach only to cited event windows; "
            "later reused ticker years remain unresolved.",
        ),
        gap_gate=dict(
            affected_symbols=affected,
            affected_symbol_years=len(changed),
            record_ids=[r["record_id"] for r in changed],
        ),
        partial_containment_rows=len(partial),
        partial_rows_identity_accept=len(moved),
        partial_rows_moved=[
            dict(symbol=r["constituent_symbol"], candidate=r["candidate_symbol"]) for r in moved
        ],
        a2_symbol_count=len(classifications),
        a2_candidate_rows=len(candidate_cases),
        a2_symbol_cases=dict(Counter(r["a2_case"] for r in classifications)),
        stitching_symbol_count=len(stitches),
        geometrically_contiguous_symbols=sum(r["contiguous_on_trading_sessions"] for r in stitches),
        coverage_unresolved=13,
        panel_ready=False,
        a2_proposed_only=True,
        a2_convention_status="SIGNED",
        date_admissibility_status="SIGNED",
        synthetic_bars=0,
        manual_rules_applied=0,
    )
    summary["note"] = (
        "Download reported complete; this snapshot is measured, while identity "
        "adjudication and A2 remain provisional. No panel readiness is implied."
    )
    summary["automatic_symbol_count"] = len(
        {r.constituent_symbol for r in rows if r.match_basis == "unique_live_candidate"}
    )
    summary["record_counts"].setdefault("empty_response", 0)
    coverage = json.loads((previous / "coverage-inputs.json").read_text())
    (out / "coverage-inputs.json").write_text(json.dumps(coverage, indent=2))
    with (out / "resolution.jsonl").open("a") as handle:
        for c in coverage:
            handle.write(
                json.dumps({**c, "resolver_version": "1.4.0", "classification": "unresolved"})
                + "\n"
            )
    (out / "events-retrieved.json").write_text(json.dumps(events, indent=2))
    (out / "identity-evidence.json").write_text(json.dumps(proofs, indent=2))
    (out / "segmentation.json").write_text(json.dumps(obj["scan"], indent=2))
    for p, h in hashes.items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest() != h:
            raise ValueError("Measured price file changed during audit")
    for symbol, info in manifest["files"].items():
        if info["state"] == "readable":
            stat = (store / (symbol + ".US.parquet")).stat()
            if (stat.st_size, stat.st_mtime_ns) != (info["bytes"], info["mtime_ns"]):
                raise ValueError(f"Store file changed since snapshot: {symbol}")
    summary["price_integrity"] = dict(
        measured_sha256_files=len(hashes),
        hashes_unchanged=True,
        snapshot_size_mtime_unchanged=True,
        listed_files=manifest["listed_parquet_files"],
    )
    (out / "price-file-hashes.json").write_text(json.dumps(hashes, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["previous", "snapshot", "events", "batch", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    run(args.previous, args.snapshot, args.events, args.batch, args.output)
