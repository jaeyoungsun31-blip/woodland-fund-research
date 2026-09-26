# Delisted history coverage floor — 2026-09-06

Read-only data-integrity audit requested by the user; no panel, study, fit,
ingest, or trial-ledger change. No existing preregistration was altered.

Used the completed-download manifest's parquet date bounds after verifying
both catalog SHA-256 hashes and the size/mtime of every one of its 50,864
price files against the current store. All matched. Report directory:
`reports/security-resolver/2026-09-06-delisted-start-floor/`.
The directory contains the reproducible audit script, full daily start-date
distributions for four cohorts, every history's bounds, the delisted records
starting on the floor, and a machine-readable summary. The script runs from
the project root with PYTHONPATH=. and requires a fresh output directory.

Today is Sunday, 2026-09-06; the latest stored date is Friday, 2026-09-04.
Thus the literal condition end < today includes every active history too.
Use catalog membership to identify the delisted cohort, not that condition
alone. Counts below are provider symbol/history records, not deduplicated
economic securities; unresolved ticker reuse remains a separate issue.

| Cohort, all ending before today | Histories | Start 1997-12-31 | Share | Start earlier | Start later |
| --- | ---: | ---: | ---: | ---: | ---: |
| All catalog histories | 50,864 | 3,760 | 7.39% | 3,843 | 43,261 |
| Delisted catalog | 32,910 | 3,745 | 11.38% | 1,470 | 27,695 |
| Delisted, passing resolver common-stock filter | 31,686 | 3,744 | 11.82% | 1,460 | 26,482 |

As an alternative stale-history definition, 33,416 histories end before the
latest stored date; 3,746 (11.21%) start on 1997-12-31. This is not proof
that all such histories are delisted.

Most frequent start dates among eligible delisted common-stock histories:

| Start | Histories |
| --- | ---: |
| 1997-12-31 | 3,744 |
| 1999-01-04 | 1,530 |
| 2003-09-10 | 183 |
| 2016-01-04 | 148 |
| 2001-07-11 | 88 |
| 1984-11-05 | 81 |
| 2001-06-21 | 79 |
| 2017-09-22 | 67 |
| 1969-12-31 | 64 |
| 2001-07-12 | 56 |

The exact-date mass strongly supports a shared vendor archival coverage
boundary for a substantial subset. It is not a universal EODHD floor:
1,460 eligible delisted records begin earlier. **3,744 eligible delisted
histories are floor-affected / suspected truncated** (3,745 before the
instrument filter). Start-date evidence alone cannot prove that every one
traded before that date; the number individually confirmed truncated needs
independent listing/history evidence and is not established by this audit.

Under the user's stated rule, any proposed panel start must be **at or after
1998-01-01**. This is a minimum coverage constraint, not a declaration that
1998 onward is complete or that all signals can start then. The second mass
at 1999-01-04 needs investigation, and lookback requirements may delay the
first usable signal further. No frozen v16 dates or DESIGN.md were changed.

These counts describe the completed local catalog snapshot, whose presence
has been verified; they remain provisional with respect to a final resolved
constituent universe. No unresolved constituent may be silently dropped.
