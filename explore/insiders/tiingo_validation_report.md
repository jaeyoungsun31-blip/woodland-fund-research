# Phase 2 independent price validation — locked training sample

The pre-inspection repository suite finished: `619 passed, 1 skipped in 97.73s (0:01:37)`. The 2022-07-01 through 2026-06-30 filing holdout guard ran before price access. No portfolio return was calculated and no filter or offline classification was changed.

[Tiingo's official EOD documentation](https://www.tiingo.com/documentation/end-of-day) defines `close`, `adjClose`, `splitFactor`, and `divCash` and the historical daily-prices endpoint. [Its split documentation](https://www.tiingo.com/documentation/corporate-actions/splits) defines `splitFactor` as new shares divided by old shares. Requests used only the Authorization header; request pacing respected 50 per hour. The raw response cache and request timestamps were deleted after these derived tables were produced, in line with the free-tier terms.
The Tiingo ticker string was not independently linked to the SEC issuer CIK; ticker reuse remains a possible source of disagreement and is not filtered here.

The seeded file contains **300 events** and **272 distinct symbols**. Of these, **264 events** have exact Tiingo bars at all EODHD session dates through the exit; **36 events** do not. **32 symbols** return no Tiingo bars or HTTP 404; **32** of those appear in the local EODHD delisted list.

## Return comparison

Each event enters at the raw open on the first trading day after filing and exits at the EODHD reference exit close (60 sessions later, or the final available close for an early terminal event). The same prespecified −30% terminal haircut is applied to all three sources where applicable. Tiingo total return compounds raw close with `splitFactor` and `divCash` on each subsequent ex-date. EODHD adjusted-close return scales the entry raw open by its entry-day adjustment factor. Percent-point comparisons include only events with exact entry, exit, and interior Tiingo dates; unavailable events are listed separately and are not counted as agreements. No portfolio aggregation is done.
As an arithmetic check, Tiingo raw-action returns versus Tiingo's own `adjClose` differ by at most 2.74e-11 in the comparable events.

| Dollar-volume bucket | Comparison | Sample events | Comparable | Within 1 pp | Within 5 pp | Median abs diff (pp) | >10 pp cases |
| --- | --- | --- | --- | --- | --- | --- | --- |
| under_300k | offline_vs_tiingo | 100 | 84 | 95.2% | 96.4% | <0.001 | 3 |
| under_300k | eodhd_adjusted_vs_tiingo | 100 | 84 | 96.4% | 97.6% | <0.001 | 2 |
| 300k_to_2m | offline_vs_tiingo | 100 | 87 | 100.0% | 100.0% | 0.003 | 0 |
| 300k_to_2m | eodhd_adjusted_vs_tiingo | 100 | 87 | 100.0% | 100.0% | 0.003 | 0 |
| over_2m | offline_vs_tiingo | 100 | 93 | 97.8% | 98.9% | 0.003 | 1 |
| over_2m | eodhd_adjusted_vs_tiingo | 100 | 93 | 97.8% | 98.9% | 0.003 | 1 |


## Every case more than 10 percentage points apart

*Redacted in the public export: the per-ticker table (7 rows, 4 symbols) is
omitted as vendor-derived per-event detail.* In aggregate: 3 cases in
under_300k under the offline rebuild and 2 under EODHD adjusted close; 1 case
in over_2m under each; none in 300k_to_2m (table above). The largest, a
+749.47 pp offline-rebuild disagreement, is the reverse split discussed in
`journal/2026-09-25-planning-decision-insider-clusters-closed.md`.

## Tiingo split records in sampled event windows

*Redacted in the public export: per-ticker split factors omitted.* Two split
records fell inside sampled event windows; the offline rebuild classified one
correctly and one incorrectly.

## Symbols without Tiingo bars

*Redacted in the public export: the per-ticker list is omitted.* 32 symbols
returned no Tiingo bars (26 empty series, 6 HTTP 404); all 32 are
in EODHD's delisted list.

## Other event-level coverage failures

*Redacted in the public export: per-ticker rows omitted.* 2 events had
missing interior dates at Tiingo.

Full derived event-level values were kept in `tiingo_validation_events.csv`,
which is not part of this repository. No raw Tiingo daily prices are included.
