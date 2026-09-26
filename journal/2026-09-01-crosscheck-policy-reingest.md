# 2026-09-01 — Two-tier cross-check re-ingest

Append-only result of the first full ingest after implementing the planning
decision in `2026-09-01-planning-decisions-crosscheck-dsr.md`.

## Codified policy

* Adjusted-return differences greater than 50 bps are monitored and counted.
* Adjusted-return differences greater than 2% are hard failures.
* The planning-approved 2026-08-28 repair may source a missing bar from
  Tiingo, with per-bar provenance. Tiingo adjusted closes are rebased to the
  nearby Yahoo level epoch before storage; this preserves Tiingo's return
  path without splicing incompatible adjusted-price levels.

## Run result

The live Yahoo + Tiingo ingest completed for all 20 tickers. All stored
tickers are current through 2026-09-01, the cross-sectional calendar check is
clean, all adjustment checks pass, and 13 missing 2026-08-28 bars were filled
from Tiingo with provenance recorded in `data/_provenance.json`.

The 50 bp monitoring count did not grow: **484 / 122,890** return comparisons,
versus the recorded baseline count of **484 / 122,905**. The small denominator
difference reflects current provider calendar overlap; the monitored-event
count is unchanged.

The hard-fail result was **not clean**: 63 observations across 11 tickers
exceeded 2%:

| Ticker | >2% observations |
|---|---:|
| DBC | 3 |
| EFA | 4 |
| QQQ | 2 |
| XLB | 10 |
| XLE | 6 |
| XLI | 4 |
| XLK | 4 |
| XLP | 12 |
| XLU | 1 |
| XLV | 11 |
| XLY | 6 |

These are within the already-known historical disagreement population, but
the codified rule says any observation above 2% is a failure; no exemption
was invented after seeing the result.

## Consequence

The single-source/source-verification caveat is **not lifted**. The primary
Yahoo store remains usable for the already-approved harness studies, but
every result continues to carry the caveat until planning resolves the
conflict between the explicit 2% rule and the historical observations above
it.
