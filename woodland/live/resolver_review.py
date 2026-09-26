"""Human review artifacts and explicit, offline approval import. Never auto-approve."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from woodland.live.resolver_a2 import identity_coverage
from woodland.live.resolver_prices import suggest_price_verdict
from woodland.live.security_resolver import Constituent, Resolution, Security, archived_symbol


def write_review_packet(
    out: Path,
    rows: list[Resolution],
    securities: list[Security],
    identity_evidence: dict[str, dict[str, Any]] | None = None,
) -> None:
    catalog = {s.price_symbol: s for s in securities}
    groups: dict[str, list[Resolution]] = defaultdict(list)
    for row in rows:
        if row.status != "resolved":
            groups[row.constituent_symbol].append(row)
    packet = []
    categories: Counter[str] = Counter()
    for symbol, pending in sorted(groups.items()):
        occurrences = [r for r in rows if r.constituent_symbol == symbol]
        candidates = sorted({c for r in pending for c in r.candidates})
        archive = any(archived_symbol(c) for c in candidates)
        literal = any(not archived_symbol(c) for c in candidates)
        if symbol in {"COV", "HET", "PEAK", "RTN"}:
            category = "delist_truncation"
        elif symbol == "WM" or (literal and not archive and len(candidates) > 1):
            category = "multi_candidate"
        elif not candidates:
            category = "no_candidates_absent"
        elif archive and not literal:
            category = "no_candidates_archived_only"
        elif archive:
            category = "reuse_archived_available"
        else:
            category = "reuse_no_archived"
        categories[category] += 1
        for candidate in candidates or [""]:
            s = catalog.get(candidate)
            relevant = [r for r in pending if candidate in r.candidates]
            failures = {r.record_id: r.failures.get(candidate, []) for r in relevant}
            eligible = bool(
                s
                and any(
                    s.first is not None
                    and s.last is not None
                    and s.first.isoformat() <= r.start <= r.end <= s.last.isoformat()
                    for r in relevant
                )
            )
            _, _, notes = suggest_price_verdict(s, relevant)
            proof = (identity_evidence or {}).get(candidate, {})
            windows = [
                Constituent(
                    r.record_id, symbol, date.fromisoformat(r.start), date.fromisoformat(r.end)
                )
                for r in relevant or pending
            ]
            split = identity_coverage(s, windows, proof)
            evidence = dict(s.price_evidence) if s else {}
            packet.append(
                dict(
                    category=category,
                    constituent_symbol=symbol,
                    membership_start=min(r.start for r in occurrences),
                    membership_end=max(r.end for r in occurrences),
                    membership_years=",".join(sorted({r.start[:4] for r in occurrences})),
                    candidate_symbol=candidate,
                    candidate_name=s.name if s else "",
                    source_price_symbol=(s.storage_symbol or s.price_symbol) if s else "",
                    segment_index=s.segment_index if s else "",
                    first_close=evidence.get("first_close"),
                    last_close=evidence.get("last_close"),
                    median_volume=evidence.get("median_volume"),
                    last_bar_volume=evidence.get("last_bar_volume"),
                    last_bar_volume_ratio=evidence.get("last_bar_volume_ratio"),
                    trailing_volume_median=evidence.get("trailing_volume_median"),
                    trailing_volume_bar_count=evidence.get("trailing_volume_bar_count"),
                    bar_count=evidence.get("bar_count"),
                    candidate_first=str(s.first or "") if s else "",
                    candidate_last=str(s.last or "") if s else "",
                    candidate_isin=s.catalog_identifiers.get("ISIN", "") if s else "",
                    candidate_archived=archived_symbol(candidate),
                    date_eligible=eligible,
                    failure_reasons=json.dumps(failures, sort_keys=True),
                    **split,
                    citation=proof.get("citation", ""),
                    predicted_signature=proof.get("predicted_signature", ""),
                    observed_from_data=proof.get("observed_from_data", ""),
                    agrees=proof.get("agrees", False),
                    pivot_side=proof.get("pivot_side", ""),
                    pivot_date=proof.get("pivot_date", ""),
                    pivot_multiplicity=proof.get("pivot_multiplicity", ""),
                    numerical_citation=proof.get("numerical_citation", ""),
                    numerical_claim=proof.get("numerical_claim", ""),
                    numerical_check=json.dumps(proof.get("numeric_check", {})),
                    notes=notes,
                )
            )
    packet.sort(
        key=lambda r: (str(r["category"]), str(r["constituent_symbol"]), str(r["candidate_symbol"]))
    )
    with (out / "review-packet.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(packet[0]))
        writer.writeheader()
        writer.writerows(packet)
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary.update(
        basis_counts=dict(Counter(r.match_basis for r in rows if r.status == "resolved")),
        review_categories=dict(categories),
        review_symbols=len(groups),
        review_packet_rows=len(packet),
        identity_confidence_counts=dict(Counter(r["identity_confidence"] for r in packet)),
        identity_verdict_counts=dict(Counter(r["identity_verdict"] for r in packet)),
        coverage_verdict_counts=dict(Counter(r["coverage_verdict"] for r in packet)),
    )
    summary_path.write_text(json.dumps(summary, indent=2))
    (out / "README.md").write_text("""# Resolver 1.4.0 identity and coverage review packet

One row per unresolved symbol and candidate, with empty candidates retained.
Identity and coverage are separate verdicts and confidence fields. Identity
acceptance requires a retrieved citation and corroborated price prediction;
without both, identity stays unknown. Coverage measures pending membership
windows independently; coverage_flags preserves multiple simultaneous defects.
Catalog Name is display-only. No identity suggestion is automatically applied.

Archived gaps over 200 calendar days define independent segments. Live files
remain intact, but a qualifying gap intersecting a membership window now blocks
the automatic unique-live basis. Full _dates containment remains unchanged.
The terminal volume ratio uses up to 60 preceding bars, excluding the final bar.
Membership bounds summarize observation windows, not continuous membership.
No panel or price/return series is constructed by this report.

## Human approval (not run by this audit)
Copy this packet to review-packet-approved.csv. Add a verdict column containing
accept/reject/unknown for EVERY row, plus review_start and review_end for every
accept (inclusive dates). Review intervals must stay inside membership bounds
and the candidate price bounds. Use separate reviewed packets for disjoint
approval windows. Never turn identity_verdict into approval automatically.

Run explicitly after human review:
python -m woodland.live.resolver_review --approved /path/review-packet-approved.csv \\
  --packet /path/review-packet.csv --reviewer "Human name" \\
  --conventions woodland/live/resolver_conventions.json

The importer verifies original row content, refuses missing/duplicate/forged
rows and conflicting approvals, then appends ManualRule entries, preserving
existing rules. Evidence cites packet hash, row number, reviewer and verdict.
Reject/unknown rows add no rule. It does not alter prices or run the resolver.
Quarantine, dates and identifier conflict checks remain binding after approval.
""")


def import_approvals(approved: Path, packet: Path, reviewer: str, conventions: Path) -> None:
    if not reviewer.strip():
        raise ValueError("Reviewer is required")
    raw = packet.read_bytes()
    original = list(csv.DictReader(raw.decode().splitlines()))
    edited = list(csv.DictReader(approved.open(newline="")))

    def key(r: dict[str, str]) -> tuple[str, str]:
        return r["constituent_symbol"], r["candidate_symbol"]

    indexed = {key(r): r for r in original}
    if len(indexed) != len(original) or len(edited) != len(original):
        raise ValueError("Packet row count/uniqueness mismatch")
    seen = set()
    additions: list[dict[str, Any]] = []
    for line, row in enumerate(edited, 2):
        k = key(row)
        if k in seen or k not in indexed or any(row.get(f) != v for f, v in indexed[k].items()):
            raise ValueError("Original packet fields must be preserved exactly")
        seen.add(k)
        if row.get("verdict") not in {"accept", "reject", "unknown"}:
            raise ValueError("Every row requires a human verdict")
        if row["verdict"] != "accept":
            continue
        from datetime import date

        start, end = date.fromisoformat(row["review_start"]), date.fromisoformat(row["review_end"])
        if not row["candidate_symbol"] or not (
            date.fromisoformat(row["candidate_first"])
            <= start
            <= end
            <= date.fromisoformat(row["candidate_last"])
            and date.fromisoformat(row["membership_start"])
            <= start
            <= end
            <= date.fromisoformat(row["membership_end"])
        ):
            raise ValueError("Approved window must fit membership and price bounds")
        additions.append(
            dict(
                symbol=row["constituent_symbol"],
                price_symbol=row["candidate_symbol"],
                start=str(start),
                end=str(end),
                names=[],
                expected_identifiers={"ISIN": row["candidate_isin"]}
                if row["candidate_isin"]
                else {},
                evidence=f"Human {reviewer}; verdict accept; packet {packet.name}; "
                f"SHA256 {hashlib.sha256(raw).hexdigest()}; approved row {line}",
            )
        )
    obj = json.loads(conventions.read_text())
    all_rules = obj["rules"] + additions
    for i, a in enumerate(all_rules):
        for b in all_rules[i + 1 :]:
            if (
                a["symbol"] == b["symbol"]
                and a["price_symbol"] != b["price_symbol"]
                and max(a["start"], b["start"]) <= min(a["end"], b["end"])
            ):
                raise ValueError("Conflicting overlapping approval rules")
    obj["rules"] = all_rules
    obj["version"] += "-human-" + hashlib.sha256(approved.read_bytes()).hexdigest()[:12]
    conventions.write_text(json.dumps(obj, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", type=Path, required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--conventions", type=Path, required=True)
    args = parser.parse_args()
    import_approvals(args.approved, args.packet, args.reviewer, args.conventions)
