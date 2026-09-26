# Resolver 1.4.0 — census, gap refusal, split identity/coverage, proposed A2

Date: 2026-09-06
Status: completed engineering/measurement; adjudication and A2 remain provisional
Declaration: `2026-09-06-phase3-resolver-v140-preregistration.md`
Artifacts: `reports/security-resolver/2026-09-06-v9-resolver/`

## Census — panel is not ready

Window 1999-01-05 through 2026-06-30. Denominator: 14,635 source symbol-year records. 1,574 remain identity-unresolved/refused. No panel was built.

Mutually exclusive proposed census labels: Case 1 = 0, Case 2 = 58 (all absent-candidate), corroborated Case 3 = 1 (BSC 2008), Case 4 = 0, unresolved case/identity = 1,515, resolver-resolved with no A2 trigger established = 13,061. Refusal overlaps these labels, including all proposed Case 2 and Case 3 rows; no proposed treatment changes resolver status. The 13 pre-existing coverage inputs remain unresolved separately. Case 4 would drop zero seam days because no join met the literal signature.

A residual Case 3 candidate shortfall appears in 235 symbol-years, but only 107 intersect refused rows: 1 corroborated and 106 unverified. An unverified residual is not asserted to be a confirmed vendor defect. No performance, strategy return, or backtest result was consulted for classification.

## Gap defect

Before-change measurement: 948 automatic symbols, 38 gapped live files, exactly two affected symbols, satisfying the required stop gate. CTXS 1999–2003 and JP 1999–2006 lose 13 automatic rows. Later CTXS years still resolve, so 947 symbols retain at least one automatic row. Other 36 gapped automatic symbols are unaffected. `_dates` remains full containment; no gap threshold was tuned.

Final statuses: resolved 13,061; no_candidates 122; candidates_unmatched 1,452; empty_response 0. Bases: unique_live_candidate 12,961; normalized_symbol 52; manual 48.

## Identity and coverage

339 review rows / 213 symbols: identity accept/high 18, unknown/low 321. Six of the original 87 partial-containment unknowns become corroborated identity suggestions: RTN, BSC_old, CA_old, DOW_old, LB_old1::segment2, TMK. Eighty-one remain unknown. Coverage independently reports complete 119, truncated_end 19, truncated_start 169, interior_gap 3, absent 29; simultaneous flags are preserved.

BSC is identity accept/high and coverage truncated_end. Retrieved court opinion: March 13 close $57, March 14 close $30 and approximately 187 million shares, with subsequent March 17 trading. Observed: $57, $30, 186,986,896 shares, file ends March 14. Source: https://law.justia.com/cases/federal/district-courts/new-york/nysdce/1%3A2007cv10453/316881/89/ . Citation/observation pairs and missing evidence are in the packet. Catalog Name is display-only.

## Stitching and A2 limits

All 213 unresolved symbols received actual-session union measurements, with ordered candidate files/segments, cited successors, covered spans, and hole lengths. 112 candidate unions have no missing observed-calendar session, but geometry does not verify identity and no join is approved.

All requested 36 shortfall rows across 30 symbols plus 29 absent-candidate symbols were assessed: 59 symbols / 65 candidate rows. Symbol-level proposals: Case 1 one (DELL_old), Case 2 eight, Case 4 zero, Case 3 residual 29 (only BSC corroborated), unresolved absent/other 21. All unsuccessful tests remain visible.

The expected shape is not supported. Actual successor starts include FI 1986-09-25, DWDP 1980-03-17, RTX 1984-11-05. These precede predecessor ends and fail the literal first-bar adjacency rule; files were not clipped to force compliance. COV's final bar is 655 observed sessions before its cited acquisition, so the acquisition cannot repair the missing history. Source: https://www.sec.gov/Archives/edgar/data/1613103/000119312515020681/d859999dex991.htm . No qualifying signature is silently promoted into an applied stitch.

The v8 envelope may combine distinct ticker vintages. DELL_old's 2013-10-29 cash event matches ($13.86 observed versus $13.75 cash consideration, 0.8% difference), but source membership observations for that vintage end 2013-10-18. The later DELL vintage is not assigned the old cash exit; hence no affected Case 1 symbol-year. Source: https://www.silverlake.com/dell-completes-go-private-transaction/ . This is not an amendment to membership dates.

The absent list is not uniformly established bankruptcies. CDAY→DAY and RE→EG have retrieved ticker-change citations, but missing predecessor files prevent literal Case 4 verification. Sources: https://www.sec.gov/Archives/edgar/data/1725057/000095017024009619/day-20240131.htm and https://www.nasdaq.com/press-release/everest-to-rebrand-company-name-and-nyse-ticker-to-reflect-its-evolution-global . Unknowns remain refused. Case 2 absence verifies only the structural absence branch; it does not prove price identity or recovery. AAMRQ's cited noncash distributions remain a partial, uncomputed recovery, not a fabricated zero or terminal return.

Calendar is the existing read-only SPY observation calendar, spanning the panel window. Distances outside its range are unknown, not zero. No independent exchange-calendar certification is claimed. Full URLs and predictions for encoded actions are in events-retrieved.json; no citation was invented for unsupported actions. A2 remains unsigned/proposed and unapplied.

## Verification and prohibitions

Focused tests: 80 passed. Full suite: 486 passed, 1 skipped, 1 unchanged ETF bar-count failure (5,502 versus 5,499; 22 folds). Baseline reproduced that failure (478 passed, 1 skipped, 1 failed). Existing ETF test not changed or suppressed. The outdated live-gap acceptance assertion was strengthened to require refusal. Ruff and mypy passed on changed modules. Artifact schema, count, evidence, and gate assertions passed.

All 50,864 snapshot price-file size/mtime checks remained unchanged. SHA-256 checks agreed before/after for 316 measured files including the calendar. v8 was not overwritten. No panel, price-data changes, ingest, backtest, synthetic bars, manual-rule ingestion, git add, or git commit. No secrets were read or exposed. All work remains in the working tree for review.
