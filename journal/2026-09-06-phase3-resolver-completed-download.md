# Resolver audit after completed download — 2026-09-06

User reported download completion and moved the store to
`data/Woodland-EODHD`. Re-ran the unchanged resolver (1.0.1, conventions
2026-09-06.2) against that read-only location. No ingest, panel, fit, repair,
promotion, or ledger change occurred. Previous reports remain intact.

The snapshot contains **50,864 readable price files**, matching all catalog
symbols: no catalog symbol lacks a readable file in this snapshot. This is
file-level coverage, not proof of complete price histories or vendor-wide
coverage. WM and WAMUQ are now present as distinct files, with ranges
1988-06-22–2026-09-04 and 1997-12-31–2012-03-20 respectively. BBBY_old remains
quarantined; moving/completing the store does not resolve its identity conflict.

Using exactly the same **GitHub symbol-only membership diagnostic input**,
across 16,180 symbol-year observation envelopes:

| Status | Earlier incomplete snapshot | Completed-download snapshot |
| --- | ---: | ---: |
| resolved | 23 | 50 |
| no_candidates | 7,237 | 578 |
| candidates_unmatched | 8,920 | 15,552 |

More candidates_unmatched after downloading is expected: files now exist,
but the input still lacks names, exchanges and identifiers needed for safe
automatic resolution. The 578 no_candidates records do not imply an
unfinished download: no plausible candidate was found using the available
symbol-only evidence, without inventing suffix mappings. These are
symbol-year records, not distinct companies.

The strict CLI exited **2**, refusing all 16,130 unresolved records. Nothing
was silently dropped. Instrument exclusions remain 1,492 catalog records.

New report directory:
`reports/security-resolver/2026-09-06-v3-completed-download/`
contains `annual-unresolved.csv`, `resolution.jsonl`, `manifest.json`,
`summary.json`, `fuzzy-review.json`, and `excluded-instruments.json`.
Snapshot hash:
`6cdaf3a07138eb86aabe004a33efff99be8b60c25abe9e21cdcb66286b3515d3`.

**Historical EODHD index membership is still absent.** The store's only JSON
files are active-symbols.json and delisted-symbols.json; these are not
historical index membership. Actual EODHD unresolved-constituent counts remain
unavailable. The report retains its provisional label because it is a
diagnostic proxy, not the declared EODHD universe. User-reported download
completion has now been checked against the captured catalog inventory.

No executable code changed. The previous resolver validation (53 passing
tests; Ruff/mypy clean) applies. The known full-suite ETF bar-count failure
was not modified or worked around, and no commit was made.
