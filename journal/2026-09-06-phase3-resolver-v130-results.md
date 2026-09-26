# Resolver 1.3.0 — archived segmentation and price evidence

2026-09-06. Executed after the v130 preregistration. Read the planning v7
packet/name-defect correction first. MOB/RAL name counterexamples are withdrawn;
all older journal entries are preserved. Catalog Name is display-only, including
in lookup, exact-name matching, manual catalog-name checks, instrument vetoes
and active/delisted catalog-conflict detection. Independent manual identity
constraints and identifier conflicts remain. A provider-Type misclassification
can no longer be diagnosed from the unreliable Name field; no claim of fully
verified instrument class is made.

No panel, price writes, ingest, backtest, web lookup, approval ingestion, git
add, or git commit occurred. All work remains for human review.

## Segmentation

ARCHIVED_SPLICE_GAP_DAYS = 200 calendar days, strict greater-than. Segments
are independent candidates with own bounds, source_price_symbol and a 1-based
segment_index. Split candidates use ::segmentN locators. Full _dates containment
is unchanged; archived price/date plausibility never automatically approves an
identity. No-gap files are not asserted to be single economic securities.

All 171 archived files referenced by the full constituent candidate search
were scanned; 10 split at 12 seams. Of the 141 archives in the old review packet,
exactly the expected nine split. ECHO_old is the additional full-candidate file.

| File | Previous bar → next bar | Gap days |
| --- | --- | ---: |
| DNB_old | 2000-10-02 → 2003-09-10 | 1,073 |
| ECHO_old | 2008-02-29 → 2009-10-02 | 581 |
| IGT_old | 2008-10-20 → 2009-08-26 | 310 |
| LB_old1 | 1982-12-23 → 2003-09-10 | 7,566 |
| LIFE_old1 | 1984-12-21 → 1985-12-23 | 367 |
| LIFE_old1 | 1988-12-22 → 2001-12-19 | 4,745 |
| LIFE_old1 | 2004-12-17 → 2015-05-07 | 3,793 |
| Q_old1 | 2011-03-31 → 2013-05-09 | 770 |
| RAL_old | 2001-12-12 → 2010-02-22 | 2,994 |
| SGP_old2 | 2009-11-20 → 2010-09-29 | 313 |
| TEK_old | 2007-12-17 → 2008-12-17 | 366 |
| TOS_old1 | 2008-12-16 → 2010-05-07 | 507 |

Live scan, separately: 49,232 non-archived files scanned, 8,868 files with
24,980 qualifying gaps. These are report-only: no live segmentation or
acceptance/rejection based on these gaps. A gap detects missing coverage or a
possible seam; it does not prove slot reuse. Source files are stat-checked
before/after reading; no file is repaired, rewritten or sorted on disk.

## Price evidence and suggestions

Review packet includes first_close, last_close, median_volume, last_bar_volume,
last_bar_volume_ratio, bar_count and segment_index, plus reference median and
reference-bar count. All are raw and segment-local. The reference median uses
up to 60 PRECEDING bars, excluding the terminal bar. Zero/missing reference
produces an empty ratio, never infinity or invented evidence. Date bounds and
numeric price/volume heuristics were declared before the scan; no names enter
suggestions. accept/medium means compatible, not independently verified identity.

Counts below are candidate rows (337), not unique constituents (211):

| Category | Symbols | High (reject) | Medium (accept) | Low (unknown) |
| --- | ---: | ---: | ---: | ---: |
| reuse_archived_available | 99 | 94 | 61 | 62 |
| reuse_no_archived | 51 | 40 | 0 | 11 |
| no_candidates_archived_only | 27 | 8 | 16 | 10 |
| no_candidates_absent | 29 | 0 | 0 | 29 |
| delist_truncation | 4 | 1 | 0 | 3 |
| multi_candidate | 1 | 0 | 1 | 1 |
| Total | 211 | 143 | 78 | 116 |

## Re-adjudication of earlier suggestions

* MOB_old: reject/high → accept/medium. Last bar 1999-11-30 on volume
  1.93x the preceding-60-bar median (levels redacted in the public export).
  483 bars; contains its pending membership window.
* RAL_old segment 1: reject/high → accept/medium. Last bar 2001-12-12, close
  0.06% below the $33.50 offer, on volume 7.06x the reference median.
  993 bars; contains pending membership. This reference differs from the
  planning example because the precise 60-prior-bar convention is declared.
* RAL_old segment 2: reject/high on date non-overlap, not its catalog name.
  The live MOB and RAL candidates also remain reject/high on date non-overlap.
* LB_old1 segment 1 remains reject/high because it ends before membership.
  Segment 2 changes to unknown/low: starts 2003-09-10, does not contain the
  full 1999–2021 pending span, and terminal volume is 0.88x reference.
  Live LB remains reject/high; LB_old remains unknown/low.
* BSC_old: accept/medium → unknown/low. Its last bar is 2008-03-14 at 30.0
  on 186,986,896 shares versus reference median 6,843,050 (27.33x), but
  membership extends through 2008-05-29. Price evidence cannot waive dates_last.
* APC_old, Q_old, SEG_old and SGP_old1 remain accept/medium, now solely under
  the declared date/price/volume evidence rule. No suggested verdict was applied.

## Resolver outcome and validation

13,074 membership records resolved: 12,974 unique_live_candidate, 52
normalized_symbol, 48 manual. 122 no_candidates and 1,439 candidates_unmatched;
zero empty_response. All 13 coverage inputs still unresolved, real materiality
still unknown, panel_ready false, CLI exit 2.

Only two statuses changed from v7: IGT in 2008 and 2009 now resolves to live
IGT because no archived segment contains its entire membership window. This
is the existing unique-live rule on the new independent segment candidates,
not action on the live gap report. The live file was not split or changed.
All 1,021 baseline live-candidate dates_first failures / 136 symbols persist.

Artifacts: reports/security-resolver/2026-09-06-v8-resolver/.
review-packet.csv and README.md are the review deliverable; segmentation.json
and archived-segmentation.csv list all archived splits; live-gaps-report-only.csv
contains the separate live scan. verdict-changes.csv records re-adjudication;
category-confidence.csv distinguishes row counts from category symbol counts.
resolution.jsonl and summary.json preserve refusal and acceptance evidence.
The v7 directory remains unchanged.

Focused validation: 72 tests pass; Ruff and mypy pass. Tests previously asserting
catalog-name authority were updated to assert the user-directed display-only
invariance, not skipped. New tests cover strict 200-day boundaries, segment-local
containment, live report-only behavior, read-only file handling, reference
volume excluding the terminal bar, zero reference, and name-invariant suggestions
and catalog conflicts. The known full-suite ETF bar-count failure is unchanged
(5502 versus 5499), and is not suppressed or fixed.

Final full-suite run after the name-only conflict guard: 478 passed, 1 skipped,
1 failed solely on the unchanged ETF bar-count assertion (89.88 seconds).
