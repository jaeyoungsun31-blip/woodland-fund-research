# Resolver 1.2.0 acceptance declaration — 2026-09-06

Written before the 1.2.0 audit, on explicit user authority. Read all three
planning findings named in the task. This supersedes blanket archived exclusion.
No panel, prices, backtest, git add or commit is authorized.

Normalize constituent spelling dot to dash only for candidate lookup. Include
matching base-symbol _old and _oldN locators as candidates, without inferring
security equivalence. Archived records cannot be accepted by bare ticker,
normalization or date uniqueness. Independent identity/manual evidence remains
required. Fuzzy matches remain suggestions only; do not enrich constituent
names or identifiers from the price catalog.

New basis unique_live_candidate: after instrument, quarantine, full containment
_dates and _id_conflict checks, exactly one non-archived candidate for the
literal/normalized symbol must remain, and no archived candidate for that
symbol may be date-eligible, even if quarantined or instrument-excluded. Search
the full catalog before filters. Existing reviewed ticker-reuse constraints
continue to apply. A normalized-spelling acceptance under this same rule uses
normalized_symbol and records both spellings. Explicit identity/manual bases
retain precedence. Full containment is unchanged.

Review suggestions do not become rules. Packet approval ingestion is built but
not run; accepted human decisions must carry reviewer attribution and evidence
and preserve all other rules. All unresolved occurrences remain a refusal.
Window remains 1999-01-05 through 2026-06-30. The 13 coverage inputs stay
unresolved pending actual identity and interval review; no proxy materiality
is upgraded. Counts and expected workload are measurements, not tuning targets.
