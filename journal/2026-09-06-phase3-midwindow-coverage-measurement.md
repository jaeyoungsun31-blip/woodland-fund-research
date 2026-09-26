# Declared 1999-01-05 start and mid-window audit — 2026-09-06

User-directed decision supersedes the threshold-based exclusion proposal in
2026-09-06-phase3-A4-coverage-boundary-amendment.md. Panel start is fixed at
**1999-01-05**. No threshold is required for exclusion: coverage_limited names
are never excluded for this reason. Include them during their membership
from their price-history start and record their missing membership interval.
This decision does not authorize a panel build or waive unresolved identities.
The membership and price perturbation requirements remain in force.

The constituent-candidate vintage counts are 156 / 16 / 9 / 4 at
1997-12-31 / 1999-01-04 / 2003-09-10 / 2016-01-04 respectively.
The 156 and 16 cohorts require no treatment for these leading coverage
boundaries: their histories start before the full declared panel window.
This does not assert that every file extends to today: delisted histories
end earlier, and identity, exit treatment, internal gaps and feature warm-up
remain distinct checks. No blanket full-window price-completeness claim is made.

## Measurement

The available source is the pinned GitHub S&P 500 symbol-only snapshot CSV,
SHA-256 39a9202c9ef69a74c0ff07e2113ad41fb6da7c8c5b6cd9541f0185fb4391e717.
Source documentation: https://github.com/fja05680/sp500 . It describes a
snapshot lookup and warns of potentially missing early members. The local
snapshot ends 2026-06-30; no extrapolation to 2026-09-06 was made.
EODHD security-linked historical membership is still unavailable.

Intervals below are source SYMBOL intervals, start-inclusive/end-exclusive,
not verified security-level intervals. They were reconstructed by changes in
presence across successive complete source snapshots; every separate spell
is preserved. Calendar days are used explicitly, not exchange sessions.
The source begins in 1996, so intervals beginning there are left-censored.
All 13 candidate identity mappings remain unresolved; all requested security
membership/intersection/day fields are null, with these diagnostic fields
provided separately. An empty diagnostic intersection does not imply clean.
In particular NVLS (Nivalis), PBY (Prospect Capital ELKS), XL (XL Fleet), and
CHK (possible reorganization identity) need identity-specific investigation.

| Symbol | Candidate catalog security (not resolved) | Price start | Source symbol intervals | Diagnostic pre-price intersection | Calendar symbol-days | Classification |
| --- | --- | --- | --- | --- | ---: | --- |
| CHK | Chesapeake Energy Corporation | 2016-01-04 | [2006-03-03, 2018-03-19) | [2006-03-03, 2016-01-04) | 3594 | unresolved |
| CRR | CARBO Ceramics Inc | 2003-09-10 | [1996-01-02, 1997-05-27) | none | 0 | unresolved |
| HNZ | H. J. Heinz Company | 2003-09-10 | [1996-01-02, 2013-06-07) | [1999-01-05, 2003-09-10) | 1709 | unresolved |
| JEC | Jacobs Engineering Group Inc | 2003-09-10 | [2007-10-26, 2019-12-10) | none | 0 | unresolved |
| MDR | McDermott International Inc | 2003-09-10 | [1996-01-02, 2003-08-20) | [1999-01-05, 2003-08-20) | 1688 | unresolved |
| MIL | EMD Millipore Corporation  | 2003-09-10 | [1996-01-02, 2010-07-15) | [1999-01-05, 2003-09-10) | 1709 | unresolved |
| NVLS | Nivalis Therapeutics Inc | 2003-09-10 | [2000-06-19, 2012-06-05) | [2000-06-19, 2003-09-10) | 1178 | unresolved |
| PBY | Prospect Capital Corp ELKS | 2016-01-04 | [1996-01-02, 2000-04-03) | [1999-01-05, 2000-04-03) | 454 | unresolved |
| SUNEQ | Sunedison Inc | 2016-01-04 | [2007-05-31, 2011-12-19) | [2007-05-31, 2011-12-19) | 1663 | unresolved |
| SYMC | NortonLifeLock Inc | 2003-09-10 | [2003-03-31, 2019-11-05) | [2003-03-31, 2003-09-10) | 163 | unresolved |
| TMK | Torchmark Corporation | 2003-09-10 | [1996-01-02, 2019-08-08) | [1999-01-05, 2003-09-10) | 1709 | unresolved |
| WIN | Windstream Holdings Inc | 2003-09-10 | [2006-07-18, 2015-04-07) | none | 0 | unresolved |
| XL | XL Fleet Corp | 2016-01-04 | [2001-09-04, 2018-09-12) | [2001-09-04, 2016-01-04) | 5235 | unresolved |

## Materiality and artifacts

Verified total constituent-days lost: **unknown**. Full constituent-day
denominator over 1999-01-05 through present: **unknown**. Requested materiality:
**unknown**, not zero. Unknown identities are not silently accepted or dropped.

Diagnostic only: the symbol intervals imply **19,102 calendar symbol-days**
before candidate price starts. The source denominator over
[1999-01-05, 2026-06-30) is **5,012,285 calendar symbol-days**, calculated by
summing snapshot membership count times calendar days until the next snapshot,
clipped to that window. The ratio is **0.381104%**. This is NOT the requested
verified panel materiality, a trading-day measure, or evidence for exclusions.
It may be distorted by ticker reuse and source omissions.

New versioned output: reports/security-resolver/2026-09-06-v4-midwindow-coverage/.
resolution.jsonl preserves the entire prior version byte-for-byte as a prefix
and appends exactly 13 typed midwindow_coverage_audit records; no resolver
status is upgraded. midwindow-coverage.csv and .json contain all requested
fields and explicit nulls; summary.json and reproduce.py preserve the method.
Assertions verified 13 unique names and preservation of the prior table.
No production code, price store, ingest, panel, fit, trial or exclusion changed.
