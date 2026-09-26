# Planning correction — the constituent panel is not "survivorship-free"

Date: 2026-09-26
Corrects (without editing): every unqualified use of "survivorship-free" for
the EODHD S&P 500 constituent panel, listed below. Principal instances:
`2026-09-09-planning-preregistration-universe-control.md` and
`2026-09-10-planning-decision-termination-signed.md`.

**No verdict changes.** The v16 dual run, the universe control and the
post-1980 momentum finding all stand. What changes is the strength of the
description of the data they were run on.

## What the panel actually controls for

**1. Membership: a symbol-matched public list for the whole window, not a
vendor point-in-time record, before or after 2012-04-04.**

- **The source.** Every membership window in the panel comes from the pinned
  GitHub `fja05680/sp500` symbol-only snapshot CSV (SHA-256
  `39a9202c9ef69a74c0ff07e2113ad41fb6da7c8c5b6cd9541f0185fb4391e717`).
  - Its windows are reconstructed from changes in presence across successive
    snapshots.
  - Its own documentation warns of potentially missing early members
    (`2026-09-06-phase3-midwindow-coverage-measurement.md`).
  - Resolver v8's manifest records its source as "GitHub S&P500 symbol-only
    diagnostic"
    (`reports/security-resolver/2026-09-06-v8-resolver/manifest.json`).
  - Resolver v10's records are source symbol-years from 1999 through 2026,
    matched to EODHD price files by symbol with identity checks
    (`reports/security-resolver/2026-09-07-v10-resolver/resolution.jsonl`).
- **The vendor record was never obtained.** EODHD's continuous
  point-in-time membership record begins 2012-04-04
  (`2026-09-06-planning-finding-eodhd-constituent-history-floor.md`). It sits
  under `fundamentals/GSPC.INDX` → `HistoricalTickerComponents`, which is not
  in the held plan. The request returned **HTTP 403**
  (`reports/security-resolver/2026-09-06-v7-predicates/endpoint-entitlement.json`,
  `2026-09-06-phase3-resolver-predicate-diagnostics.md`). No later entry
  records it being purchased or used.
- **So 2012-04-04 is not a boundary in the panel.** Membership is the same
  symbol-matched public list before and after it. The 2012-04-04 figure
  appears in `explore/deletions/README.md` only as a date at which the mask
  was counted.

**This departs from the wording requested for this correction.** The request
described membership as "point-in-time from EODHD from 2012-04-04". The
committed record does not support that, so it is not stated here. If a vendor
membership record for 2012 forward is wanted, it requires the Fundamentals or
All-In-One EODHD tier, which the finding above prices at $59.99 or $99.99 a
month.

**2. Prices: delisting-inclusive, with a declared refused set.**

- **Coverage.** Returns come from EODHD end-of-day `adjusted_close` files,
  which include delisted securities. The resolved panel is 942 symbols ×
  6,736 days, 1999-01-06 to 2026-06-30
  (`reports/security-resolver/2026-09-07-constituent-panel/README.md`).
- **Refused names.** **213 constituent symbols, 1,574 symbol-years, could
  not be resolved to a price file and are absent**. They are declared, not
  omitted (`panel-summary.json`, `refused`). Unresolved names are plausibly
  over-represented among renamed, acquired and failed firms, which is exactly
  the survivorship-relevant population. That correlation was not measured.
- **The universe control** drops 27 further defect symbols, leaving 915. Of
  those, 44.0% exited the index, against 48% panel-wide
  (`writeup/research-report.md`, "The control that finally tested the
  hypothesis").

**3. Delisting returns: bracketed, not observed.**

- **Coverage.** The signed A2 base assigns a terminal treatment to only 8 of
  430 exits, 1.9%
  (`2026-09-08-planning-finding-a2-applied-but-covers-2-percent-of-exits.md`).
- **The bound.** Under A2 Amendment 2
  (`2026-09-08-planning-decision-A2-amendment-2-two-sided-bound.md`), the
  441 unclassified exits are run at a 0% favourable and a −100% adverse
  terminal bound (`reports/security-resolver/2026-09-07-constituent-panel/README.md`).
- **The effect.** The bound moved v16 Sharpe by −0.071 (cleared) and −0.032
  (full) and changed no verdict
  (`2026-09-09-planning-ruling-v16-dual-run-closed.md`).

## Restated claim

> The EODHD constituent panel uses **delisting-inclusive prices**, with 213
> constituent symbols (1,574 symbol-years) refused as unresolved. **Delisting
> returns are bracketed** between 0% and −100% for unclassified exits.
> **Membership throughout 1999–2026 comes from a symbol-matched public list
> (`fja05680/sp500`), not a vendor point-in-time record.**

The short form, where one is needed, is **"delisting-inclusive,
survivorship-controlled"** with a pointer to this entry. **Not
"survivorship-free".**

## Why the negative findings still stand

The residual gaps are:
- refused names
- a public membership list with possible missing early members
- the membership-leakage test (A4) that was never implemented
  (`journal/FINDINGS-INDEX.md` §3)

Survivorship and lookahead residue each tend to bias a long-short momentum
result **upward**. That direction is an inference, not a measurement. A
strategy that fails on a possibly flattered universe is not rescued by
removing the flattery. Any **positive** number from these runs stays
unciteable, as already recorded.

## Committed files using "survivorship-free" without this qualification

From
`grep -rn -i "survivorship-free" journal/ writeup/ reports/ STATE.md`, run
2026-09-26. Prior journal entries are **not edited**; this entry is their
correction.

| File:line | Refers to | Action |
|---|---|---|
| `journal/FINDINGS-INDEX.md:20` | EODHD panel | Index row rewording is out of scope for this task; the new index row points here |
| `journal/2026-09-09-planning-preregistration-universe-control.md:8` | EODHD panel | Corrected by this entry |
| `journal/2026-09-09-planning-preregistration-universe-control.md:92` | EODHD panel ("genuinely survivorship-free") | Corrected by this entry |
| `journal/2026-09-09-planning-correction-cleared-subset-is-survivorship-biased.md:5` | EODHD panel | Corrected by this entry |
| `journal/2026-09-10-planning-decision-termination-signed.md:49` | EODHD panel | Corrected by this entry |
| `journal/2026-09-06-planning-review-v8-segmentation-threshold-and-cost-fallback.md:118` | EODHD panel (cost context) | Corrected by this entry |
| `journal/2026-09-02-xsmom-v10-preregistration.md:18` | Fama–French 12-industry portfolios | Different data, CRSP-based academic portfolios. Not this correction's subject |
| `journal/2026-09-02-xsmom-v10-preregistration.md:38` | Fama–French 12-industry portfolios | As above |
| `STATE.md:242` | EODHD panel (cost context) | Not edited; STATE.md summarizes the journal |
| `writeup/research-report.md:881` | EODHD panel | Edited in the same commit, with a note at the top |
| `writeup/research-report.md:1027` | EODHD panel | Edited in the same commit |
| The accompanying working paper is being rewritten by the author and will be added later. | | |

`reports/` had no occurrences. The same commit also qualifies
"point-in-time" wherever it describes the panel's membership in the paper
and the research report, for the reason in §1.
