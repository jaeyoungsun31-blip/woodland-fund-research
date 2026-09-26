# Resolver 1.2.0 review packet — 2026-09-06

Executed after 2026-09-06-phase3-resolver-v120-preregistration.md. Read all
three planning findings requested by the user. No web name research, catalog
name/ISIN enrichment of constituents, fuzzy acceptance, panel, backtest, price
writes, git add or git commit occurred. Approval import was built, not run.

Windowed membership records (1999-01-05 through 2026-06-30):

| Status | Records |
| --- | ---: |
| resolved | 13,072 |
| no_candidates | 122 |
| candidates_unmatched | 1,441 |
| empty_response | 0 |

Resolved bases: unique_live_candidate 12,972 records / 948 unique symbols;
normalized_symbol 52 records / 5 symbols; manual 48 records. The 13 mid-window
coverage inputs remain unresolved separately, without upgrading proxy coverage
or materiality. CLI exit 2 refuses 1,563 unresolved membership records.

All six normalization examples leave no_candidates. BF.B (28 records), BRK.B
(17), COC.B (4), FTL.A (1), TMC.A (2) resolve with normalized_symbol. RDS.A's
four 1999–2002 records find RDS-A, but its history begins 2005-07-21; dates_first
correctly keeps all four unresolved. No dates predicate was relaxed.

| Review category | Distinct symbols |
| --- | ---: |
| reuse_archived_available | 99 |
| reuse_no_archived | 51 |
| no_candidates_archived_only | 27 |
| no_candidates_absent | 29 |
| delist_truncation | 4 |
| multi_candidate | 1 |

Total 211 symbols / 326 symbol-candidate packet rows. Expectations were not
used as targets. Compared with the estimated 961 automatic symbols, 13 are
blocked by the full archive-family search: AIT, BBT, CCE, CHK, CPWR, EP, KG,
KMG, MIL, NYX, PARA, WEN, XL. RDS.A accounts for the extra non-archive review
case after normalization. Existing manual reuse guards remain in force.

Regression measurement on the original live-candidate failure population:
all **1,021 records / 136 symbols** still fail dates_first for that candidate,
and all remain candidates_unmatched. Full containment is unchanged. Archived
records are considered but cannot win on ticker plus dates, including MOB_old
and RAL_old. A date-eligible quarantined archive also blocks uniqueness.

Artifacts: reports/security-resolver/2026-09-06-v7-resolver/ contains
review-packet.csv, README.md, resolution.jsonl (structured failures),
summary.json (basis and category counts), annual-unresolved.csv, and
reuse-regression.json. Packet suggestions are deliberately unknown/low where
catalog metadata alone cannot establish an historical company. Specific
contradictions in the supplied planning findings receive reject suggestions;
five named archived examples from those findings receive accept/medium
suggestions. None is applied.

The approval importer requires an explicitly human-edited packet, a verdict
for each row, reviewer identity and reviewed date bounds for accepted rows.
It validates unchanged source columns and row identity and rejects conflicting
approval windows. It appends evidence-bearing ManualRule entries only when
explicitly invoked; it was not invoked in this task. Other eligibility rules
still apply to approved candidates, including quarantines.

Validation: 66 focused resolver tests pass, including the local 1,021-row
regression. Ruff and mypy pass on all three resolver modules. Tests for the
superseded no-archive-candidate expectation and unsplit dates diagnostic were
updated to assert the explicitly requested new behavior; unrelated tests and
full containment were preserved. The existing full-suite ETF bar-count
failure (5502 versus 5499) remains out of scope and unmodified.
