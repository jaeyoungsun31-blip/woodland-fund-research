# Planning correction — survivorship-correction citations re-pointed to committed files

Date: 2026-09-26
Corrects (without editing): the evidence citations in
`2026-09-26-planning-correction-survivorship-claim-strength.md` and in
a companion study sheet. The accompanying working paper is being rewritten by the author and will be added later.

**No fact, number or conclusion changes.** Those two documents cited files
under `reports/security-resolver/`. That directory is gitignored (`reports/*`
in `.gitignore`), so the files exist only in the author's local working copy
and are **not in the repository**. The gap was found in
a pre-release audit (not included in this copy). Each fact below is re-pointed to a
committed journal entry that carries the same fact. Every fact has a
committed equivalent, so **no evidence is local-only**.

## Citation map

| Fact (as stated) | Untracked file cited | Committed file carrying the same fact |
|---|---|---|
| Membership comes from the GitHub S&P 500 **symbol-only** list | `reports/security-resolver/2026-09-06-v8-resolver/manifest.json` | `2026-09-06-phase3-midwindow-coverage-measurement.md` (lines 21–26: the pinned `fja05680/sp500` symbol-only snapshot, SHA-256 `39a9202c…`, "EODHD security-linked historical membership is still unavailable"); `2026-09-06-phase3-resolver-v110-windowed.md` (line 40: "Historical membership remains the GitHub symbol-only" source) |
| Resolver records are source symbol-years, 1999 through 2026 | `reports/security-resolver/2026-09-07-v10-resolver/resolution.jsonl` | `2026-09-06-phase3-resolver-v140-results.md` (line 10: window 1999-01-05 through 2026-06-30, 14,635 source symbol-year records) |
| EODHD `HistoricalTickerComponents` returned **HTTP 403** | `reports/security-resolver/2026-09-06-v7-predicates/endpoint-entitlement.json` | `2026-09-06-phase3-resolver-predicate-diagnostics.md` (lines 42–43: two requests to `fundamentals/GSPC.INDX` returned HTTP 403, for Components and HistoricalTickerComponents). The original entry already cited this file alongside the untracked one |
| Resolved panel: 942 symbols × 6,736 days, 1999-01-06 to 2026-06-30 | `reports/security-resolver/2026-09-07-constituent-panel/README.md` | `2026-09-23-codex-defect-v16-panel-hash-mismatch.md` (line 13: 6,736 dates, 1999-01-06 through 2026-06-30, the same 942 ordered symbols) |
| 213 constituent symbols / 1,574 symbol-years refused | `panel-summary.json` (`refused`), in the untracked panel directory | `2026-09-07-xsmom-v16-panel-preregistration.md` (line 93: "213 constituents refused / 1574 symbol-years"); `2026-09-07-phase3-signed-date-admissibility-results.md` (line 9: 1,574 / 14,635 symbol-years refused) |
| 441 unclassified exits run at a 0% favourable and a −100% adverse bound | `reports/security-resolver/2026-09-07-constituent-panel/README.md` | `2026-09-08-codex-a-a2-amendment-2.md` (lines 31 and 37: "unclassified: 441"; "The 441 unclassified symbol-years enter both bounds"); `2026-09-08-planning-decision-A2-amendment-2-two-sided-bound.md` (lines 25–31: the bound definitions, adverse −100%) |

The phrase "EODHD end-of-day files, which include delisted securities" is
supported by `writeup/research-report.md` ("The panel": "a purchased EODHD
subscription including delisted companies") and by
`2026-09-06-phase3-delisted-coverage-floor.md`.

## Drafts updated in the same commit

- The accompanying working paper is being rewritten by the author and will be added later.

## Standing rule

Evidence cited from the journal or the writeup must be a **tracked** file.
Before citing a path under `reports/`, check it with `git ls-files`. Most of
`reports/` is gitignored.
