"""Read-only store snapshot and versioned resolver diagnostics (no panel/ingest).

Run: python -m woodland.live.resolver_audit --help
Outputs are written before a nonzero exit on unresolved constituents.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq  # type: ignore[import-untyped]

from woodland.live.security_resolver import (
    RESOLVER_VERSION,
    Constituent,
    ManualRule,
    Resolution,
    Security,
    SecurityResolver,
    UnresolvedConstituents,
    instrument_exclusion,
    require_resolved,
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_conventions(path: Path) -> tuple[dict[str, Any], list[ManualRule]]:
    obj = json.loads(path.read_text())
    rules = [ManualRule(
        symbol=r["symbol"], price_symbol=r["price_symbol"],
        start=date.fromisoformat(r["start"]), end=date.fromisoformat(r["end"]),
        evidence=r["evidence"], names=tuple(r.get("names", [])),
        exchanges=tuple(r.get("exchanges", [])),
        expected_identifiers=r.get("expected_identifiers", {}),
        require_constituent_name=r.get("require_constituent_name", False),
    ) for r in obj["rules"]]
    return obj, rules


def snapshot_store(store: Path, conventions: dict[str, Any]) -> tuple[
    list[Security], dict[str, Any], list[dict[str, Any]]
]:
    """Capture names once; inspect immutable completed parquet footers only.

    Missing/corrupt/changing files are not declared nonexistent companies. No
    network calls, writes, repairs, or inference of relationships from suffixes.
    """
    paths = {p.name: p for p in store.glob("*.US.parquet")}
    records: dict[str, dict[str, Any]] = {}
    conflicts: set[str] = set()
    manifest: dict[str, Any] = {
        "captured_at": datetime.now(UTC).isoformat(), "store": str(store.resolve()),
        "provisional": True, "listed_parquet_files": len(paths), "catalogs": {}, "files": {},
    }
    for name in ("active-symbols.json", "delisted-symbols.json"):
        raw = (store / name).read_bytes()
        manifest["catalogs"][name] = {"sha256": sha256(raw), "bytes": len(raw)}
        for row in json.loads(raw):
            code = row["Code"]
            if code in records and (
                {k: v for k, v in records[code].items() if k != "Name"}
                != {k: v for k, v in row.items() if k != "Name"}
            ):
                conflicts.add(code)
            records[code] = row
    securities, excluded = [], []
    for code, row in sorted(records.items()):
        reason = instrument_exclusion(row.get("Type", ""), row.get("Name", ""))
        if reason:
            excluded.append({"price_symbol": code, "name": row.get("Name", ""),
                             "provider_type": row.get("Type", ""), "reason": reason})
        available = False
        first = last = None
        filename = code + ".US.parquet"
        path = paths.get(filename)
        file_info: dict[str, Any] = {"state": "not_in_snapshot"}
        if path is not None:
            try:
                before = path.stat()
                parquet = pq.ParquetFile(path)
                meta = parquet.metadata
                if meta.num_rows == 0:
                    file_info = {"state": "empty_response", "rows": 0}
                    raise ValueError("Empty parquet")
                index = meta.schema.names.index("date")
                minimums, maximums = [], []
                for i in range(meta.num_row_groups):
                    stats = meta.row_group(i).column(index).statistics
                    if stats is None or not stats.has_min_max:
                        raise ValueError("Date statistics unavailable")
                    minimums.append(str(stats.min)[:10])
                    maximums.append(str(stats.max)[:10])
                if not minimums or meta.num_rows == 0:
                    raise ValueError("Empty parquet")
                first = date.fromisoformat(min(minimums))
                last = date.fromisoformat(max(maximums))
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError("File changed during snapshot")
                available = True
                file_info = {"state": "readable", "bytes": after.st_size,
                             "mtime_ns": after.st_mtime_ns, "rows": meta.num_rows,
                             "first": first.isoformat(), "last": last.isoformat(),
                             "columns": meta.schema.names}
            except (OSError, ValueError) as error:
                # ArrowInvalid derives from ValueError. No partial file is repaired.
                if file_info.get("state") != "empty_response":
                    file_info = {"state": "unreadable_or_changing", "error": type(error).__name__}
        manifest["files"][code] = file_info
        quarantine = conventions.get("quarantine", {}).get(code, "")
        if code in conflicts:
            quarantine = "Conflicting active/delisted catalog rows for same storage symbol"
        securities.append(Security(
            security_id=conventions.get("security_ids", {}).get(code, "unverified:eodhd:" + code),
            price_symbol=code, name=row.get("Name", ""), exchange=row.get("Exchange", ""),
            instrument_type=row.get("Type", ""), first=first, last=last, available=available,
            catalog_identifiers={"ISIN": row["Isin"]} if row.get("Isin") else {},
            price_identifiers={}, quarantine=quarantine, response_state=file_info["state"],
        ))
    manifest["catalog_conflicts"] = sorted(conflicts)
    return securities, manifest, excluded


def load_constituents(path: Path) -> list[Constituent]:
    """Accept explicit rows or historical EODHD records, never enrich from today's names.

    CSV schema: record_id,symbol,start,end,name,exchange (optional ISIN/CUSIP/FIGI).
    JSON: HistoricalTickerComponents object, or a list of its records.
    Open-ended bounds require a caller-supplied end in the input: no today default.
    Symbol-only date,tickers snapshots become annual observation envelopes for
    diagnostics only, not inferred continuous membership intervals or panel input.
    """
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        if rows and set(rows[0]) == {"date", "tickers"}:
            # Aggregate observations without claiming continuous membership.
            observations: dict[tuple[str, int], list[date]] = defaultdict(list)
            for row in rows:
                when = date.fromisoformat(row["date"])
                for symbol in row["tickers"].split(","):
                    if not symbol:
                        raise ValueError("Empty constituent symbol")
                    observations[symbol, when.year].append(when)
            return [Constituent(f"{year}:{symbol}", symbol, min(dates), max(dates))
                    for (symbol, year), dates in sorted(observations.items())]
    else:
        obj = json.loads(path.read_text())
        rows = obj.get("HistoricalTickerComponents", obj) if isinstance(obj, dict) else obj
        if isinstance(rows, dict):
            rows = list(rows.values())
    result = []
    for i, row in enumerate(rows):
        symbol = row.get("symbol", row.get("Code"))
        start = row.get("start", row.get("StartDate"))
        end = row.get("end", row.get("EndDate"))
        if not symbol or not start or not end:
            raise ValueError(f"Constituent row {i} requires explicit symbol/start/end")
        result.append(Constituent(
            record_id=row.get("record_id", str(i)), symbol=symbol,
            start=date.fromisoformat(start), end=date.fromisoformat(end),
            name=row.get("name", row.get("Name", "")) or "",
            exchange=row.get("exchange", row.get("Exchange", "")) or "",
            identifiers={key: row[key] for key in ("ISIN", "CUSIP", "FIGI") if row.get(key)},
        ))
    if len({r.record_id for r in result}) != len(result):
        raise ValueError("Duplicate constituent record_id")
    return result


def annual_report(rows: list[Resolution]) -> list[dict[str, Any]]:
    """Unique historical symbols per year/status; total may span multiple identities."""
    years: dict[int, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in rows:
        for year in range(int(row.start[:4]), int(row.end[:4]) + 1):
            years[year][row.status].add(row.constituent_symbol)
    return [{"year": year, "provisional": True,
             **{status: len(groups.get(status, set())) for status in
                ("resolved", "no_candidates", "candidates_unmatched", "empty_response")}}
            for year, groups in sorted(years.items())]


def write_report(
    destination: Path, rows: list[Resolution], manifest: dict[str, Any],
    excluded: list[dict[str, Any]], conventions: dict[str, Any], source: str,
) -> None:
    """Append-only run directories; no overwriting previous resolution tables."""
    destination.mkdir(parents=True, exist_ok=False)
    identity = sha256(json.dumps(manifest, sort_keys=True).encode())
    meta = {"resolver_version": RESOLVER_VERSION, "conventions_version": conventions["version"],
            "snapshot_sha256": identity, "source": source, "provisional": True}
    (destination / "manifest.json").write_text(json.dumps({**meta, **manifest}, indent=2))
    # One row per constituent occurrence; symbol reuse cannot be flattened to symbol alone.
    with (destination / "resolution.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps({**meta, **row.to_dict()}) + "\n")
    fuzzy = [{"record_id": row.record_id, "constituent_symbol": row.constituent_symbol,
              **match} for row in rows for match in row.fuzzy_matches]
    (destination / "fuzzy-review.json").write_text(json.dumps(fuzzy, indent=2))
    (destination / "excluded-instruments.json").write_text(json.dumps(excluded, indent=2))
    annual = annual_report(rows)
    with (destination / "annual-unresolved.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "year", "provisional", "resolved", "no_candidates", "candidates_unmatched",
            "empty_response"])
        writer.writeheader()
        writer.writerows(annual)
    counts = dict(Counter(row.status for row in rows))
    (destination / "summary.json").write_text(json.dumps({
        **meta, "record_counts": counts, "excluded_catalog_records": len(excluded),
        "identity_resolved": bool(rows) and all(r.status == "resolved" for r in rows),
        "panel_ready": False,
        "note": "Counts are provisional until ingest completes. This is identity resolution only; "
                "resolved does not certify price integrity, membership completeness "
                "or delisting returns.",
    }, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--constituents", type=Path, required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--conventions", type=Path,
                        default=Path(__file__).with_name("resolver_conventions.json"))
    parser.add_argument("--coverage-input", type=Path, required=True,
                        help="Versioned mid-window audit JSON inputs; unresolved rows block use")
    args = parser.parse_args()
    # Refuse output anywhere in the input store, project data/, or input files.
    out = args.output.resolve()
    protected = [args.store.resolve(), Path("data").resolve()]
    if any(out == p or p in out.parents for p in protected):
        parser.error("Output must be outside the read-only input store and data/")
    conventions, rules = load_conventions(args.conventions)
    window_start, window_end = date(1999, 1, 5), date(2026, 6, 30)
    inputs = [replace(c, start=max(c.start, window_start), end=min(c.end, window_end))
              for c in load_constituents(args.constituents)
              if c.end >= window_start and c.start <= window_end]
    coverage = json.loads(args.coverage_input.read_text())
    if len(coverage) != 13 or len({r["symbol"] for r in coverage}) != 13:
        parser.error("Coverage inputs must contain all 13 unique mid-window records")
    # Identity verification and real interval evidence are still outstanding.
    # Do not promote imported classifications or materiality claims.
    if any(r.get("classification") != "unresolved" for r in coverage):
        parser.error("Reviewed identity/interval evidence required before coverage promotion")
    if not inputs:
        parser.error("Empty constituent input is not a resolved universe")
    securities, manifest, excluded = snapshot_store(args.store, conventions)
    manifest["panel_window"] = [str(window_start), str(window_end)]
    manifest["coverage_input_sha256"] = sha256(args.coverage_input.read_bytes())
    manifest["constituents_sha256"] = sha256(args.constituents.read_bytes())
    manifest["conventions_sha256"] = sha256(args.conventions.read_bytes())
    from woodland.live.resolver_prices import scan_price_evidence
    securities, price_scan = scan_price_evidence(args.store, securities, inputs, rules)
    manifest["price_evidence_scan"] = price_scan
    resolver = SecurityResolver(securities, rules)
    rows = [resolver.audit_one(c) for c in inputs]
    write_report(out, rows, manifest, excluded, conventions, args.source_label)
    from woodland.live.resolver_review import write_review_packet
    write_review_packet(out, rows, securities)
    (out / "segmentation.json").write_text(json.dumps(price_scan, indent=2))
    (out / "coverage-inputs.json").write_text(json.dumps(coverage, indent=2))
    with (out / "resolution.jsonl").open("a") as handle:
        for record in coverage:
            handle.write(json.dumps({**record, "resolver_version": RESOLVER_VERSION,
                                     "classification": "unresolved"}) + "\n")
    summary_path = out / "summary.json"
    summary = json.loads(summary_path.read_text())
    summary.update(coverage_unresolved=len(coverage), panel_ready=False,
                   panel_window=[str(window_start), str(window_end)])
    summary_path.write_text(json.dumps(summary, indent=2))
    print(json.dumps({"output": str(out), "provisional": True,
                      "records": dict(Counter(r.status for r in rows))}))
    try:
        require_resolved(rows)
    except UnresolvedConstituents as error:
        print(str(error))
        return 2
    if coverage:
        print("Refusing use: 13 unresolved coverage identity inputs")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
