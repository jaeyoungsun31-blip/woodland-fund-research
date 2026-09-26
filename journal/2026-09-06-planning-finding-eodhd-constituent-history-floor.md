# Planning finding — EODHD cannot supply the constituent source for 1999–2012

Date: 2026-09-06
Status: finding (blocking Option A of the resolver review)
Supersedes: the "check the EODHD index-constituents endpoint first" recommendation
in `2026-09-06-planning-review-resolver-no-acceptance-path.md`

## What was checked

Vendor documentation for the plan actually held (EOD Historical Data — All World,
$19.99/mo) and for the endpoints that would carry constituent identity.

## Findings

1. **`/api/eod/{ticker}` returns no identity.** Fields are exactly
   `date, open, high, low, close, adjusted_close, volume`. No name, exchange,
   ISIN, CUSIP or FIGI. The price side carries no identifier at all.

2. **Historical index constituents live in `/api/fundamentals/GSPC.INDX`,
   under `HistoricalTickerComponents`.** Per-record fields: `Code`, `Name`,
   `StartDate`, `EndDate`, `IsActiveNow`, `IsDelisted`. No `Exchange`, no
   `Sector`, no `ISIN` in the historical log — those appear only in the
   current-components snapshot.

3. **The continuous membership record begins 2012-04-04.** Vendor language:
   snapshots before 2012 are incomplete and "should be treated as indicative."
   One earlier record exists (Lehman Brothers, removed 2008-09-16).

4. **Fundamentals is not in the held plan.** EOD All-World ($19.99) excludes the
   Fundamental Data API. Access requires Fundamentals Data Feed ($59.99/mo) or
   All-In-One ($99.99/mo).

5. **The ID Mapping API `/api/id-mapping` IS in the held plan.** Bidirectional
   `symbol ↔ isin, figi, lei, cusip, cik`. Response `data[]` objects carry
   `symbol, isin, figi, lei, cusip, cik`. Delisted coverage is undocumented.

## Consequence

The declared panel window is 1999-01-05 → 2026-06-30 (27.5 years). EODHD's
continuous membership record covers 2012-04-04 → present (14.2 years). The
uncovered 13.2 years contain the dot-com unwind and 2008 — the periods whose
delisted names are the reason the data was bought.

Option A as written in the resolver review is therefore **unavailable for the
first half of the window at any price on this vendor**. $59.99/mo buys
constituent identity for 2012 forward only. The existing symbol-only GitHub
source covers more of the window than the paid endpoint would.

## Non-circularity constraint restated

Buying ISINs does not by itself help. `stable_id` requires an identifier on
**both** sides that were established independently. Looking up the ISIN by
ticker on the constituent side and again by ticker on the price side is the same
ticker match wearing an identifier's clothes. This applies to the ID Mapping API
exactly as it applied to name enrichment.

## The one non-circular use of the held plan

`/api/id-mapping` can test whether a ticker maps to more than one security. That
is an **independent** uniqueness test — it does not presuppose the match it is
checking. It is therefore admissible as evidence for the
`unique_catalog_candidate` basis under discussion, and it costs nothing beyond
the current subscription.

## Open, unsigned

- Whether the panel window is shortened to a period with defensible membership,
  or `unique_catalog_candidate` is declared and the 1999–2012 membership is
  accepted as symbol-only with that limitation recorded in every result.
- Whether an external non-EODHD membership source (CRSP via WRDS; SEC-derived
  reconstruction) is pursued for the pre-2012 half.
