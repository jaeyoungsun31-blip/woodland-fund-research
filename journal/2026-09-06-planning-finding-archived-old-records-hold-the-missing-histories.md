# Planning finding — the blanket `_old` exclusion is discarding the constituent price histories

Date: 2026-09-06
Status: finding (blocking); partially retracts the third defect claim in
`2026-09-06-planning-review-resolver-no-acceptance-path.md`

## Measurements

Simulated the `_dates` predicate against the 14,167 single-candidate
`candidates_unmatched` rows, using `manifest.json` first/last bounds.

| outcome | rows | distinct symbols |
|---|---|---|
| would PASS `_dates` | 13,133 | 961 |
| FAIL — membership starts before first bar | 1,021 | 136 |
| FAIL — membership ends after last bar | 13 | 4 (PEAK, COV, HET, RTN) |
| candidate on excluded-instrument list | 0 | — |

## Retraction

The prior entry called `_dates` full containment a latent defect biased against
delisted names. That was wrong. Measured, it rejects 13 rows on the delisting
axis. It rejects 1,021 on the opposite axis, and that rejection is **correct
protective behaviour**: those are index members whose live price file begins
years after their membership, i.e. ticker reuse. `_dates` is the only predicate
currently catching it. Do not relax it.

Of the 136 affected symbols, 130 have a gap greater than three years. They
concentrate in 1999–2010 (95 rows in 1999, decaying to 40 by 2010).

## The finding

For 74 of those 136 symbols, an archived `_old` file exists whose bounds DO
cover the membership window, and the archived catalog record carries the
company name:

```
APC : live 2026-02-12..2026-09-04 | APC_old  1997-12-31..2019-08-08  Anadarko Petroleum Corp
Q   : live 2024-12-31..2026-09-04 | Q_old    1997-12-31..2011-03-31  Qwest Communications International Inc
SEG : live 2024-07-29..2026-09-04 | SEG_old  1997-12-31..2000-11-21  Seagate Technology Inc
SGP : live 2026-02-06..2026-09-04 | SGP_old1 1997-12-31..2011-11-15  Schering Plough Corp
```

Resolver 1.1.0 excludes all 1,632 `_old` records wholesale
(`reason: archived_symbol_excluded`). The histories the panel needs for the
1999–2010 constituents are in that excluded pile.

## Why blanket inclusion is equally wrong

The `_old` slot is itself reused, and date overlap does not disambiguate:

```
MOB_old 1997-12-31..1999-11-30  Mobilicom Limited ADS      (NOT Mobil)
RAL_old 1997-12-31..2022-03-02  Ralliant Corporation       (NOT Ralston Purina)
LB_old1 1982-04-01..2021-08-02  LandBridge Company LLC     (implausible first date)
```

`MOB_old` overlaps Mobil's 1999 membership on dates and ticker, and is a
different company. Ticker + date containment is therefore **not** a sufficient
match rule against the archived pile.

## What this changes

The archived catalog records carry **names**. The constituent side does not —
that, and only that, is why `exact_name` is unreachable. The missing input is
constituent company names for 1999–2012, not ISINs and not the Fundamentals
subscription.

Consequence for the options in
`2026-09-06-planning-finding-eodhd-constituent-history-floor.md`: the $59.99
Fundamentals upgrade remains unhelpful (2012 floor), but the ISIN/ID-Mapping
line of attack is also unnecessary. A free membership source carrying company
names over the full window is sufficient and is the cheapest available fix.

## Open, unsigned

- Source for 1999–2012 constituent names with membership dates.
- Whether `exact_name`'s `c.exchange == s.exchange` requirement is relaxed to
  name + date containment when the constituent source carries no exchange, and
  under what recorded evidence standard.
- Admission rule for archived `_old` records: they must become candidates, but
  only under a name-verified basis, never ticker + date alone.
- The 13 delist-truncation rows (PEAK, COV, HET, RTN) still need the A2
  truncation convention.

## Addendum — manual adjudication workload, and a third defect

Distinct symbols by disposition:

| disposition | symbols |
|---|---|
| auto-resolvable (unique candidate, dates contain) | 961 |
| manual — ticker reuse, archived `_old` present | 86 |
| manual — ticker reuse, no archived record | 50 |
| manual — delisting truncation (COV, HET, PEAK, RTN) | 4 |
| manual — `no_candidates` | 62 |
| manual — multi-candidate (WM) | 1 |
| **total requiring human adjudication** | **203** |

Third defect: **no ticker normalization.** `BRK.B` is reported `no_candidates`
while `BRK-B` (1996-05-09..2026-09-04) sits in the store. Same for `BF.B`/`BF-B`
and `COC.B`/`COC-B`. The constituent source uses dot class suffixes; EODHD uses
dashes.

Sampling the `no_candidates` set also shows most are recoverable from the
archived pile, not absent: `BSC_old` 1999-01-04..2008-03-14 (Bear Stearns),
`CA_old`, `CAM_old`, `EMC_old`, `ACV_old`, `ABI_old1`. The `no_candidates`
label is an artifact of the blanket `_old` exclusion plus missing normalization,
not a statement about the store's contents.
