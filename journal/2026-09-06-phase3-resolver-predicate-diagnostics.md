# Resolver predicate instrumentation — 2026-09-06

Resolver 1.1.1 adds candidate_diagnostics to audit_one outputs. Acceptance
rules, candidate generation, date bounds and priorities are unchanged. Every
candidate records availability, response state, all five failed predicates
(archived, quarantine, instrument_exclusion, dates, id_conflict), and whether
it passed those predicates but lacked an acceptance basis. Multiple predicate
failures are recorded together, not short-circuited. Accepted candidates are
not labelled no_acceptance_basis. Unavailable records retain availability
context so file failure is not confused with identity acceptance.

Windowed rerun: reports/security-resolver/2026-09-06-v7-predicates/.
Across 14,635 membership records, there are 14,264 candidate occurrences
(a candidate can recur across membership years):

| Predicate | Candidate occurrences |
| --- | ---: |
| archived | 0 |
| quarantine | 0 |
| instrument_exclusion | 0 |
| dates | 1,053 |
| id_conflict | 0 |
| no_acceptance_basis | 13,163 |
| Accepted | 48 |

There are no overlapping failed predicates in this observed run; synthetic
regression tests cover simultaneous failure of all five. Zero archived
rejections means these source records did not generate archived candidates,
not that the exclusion rule was removed. Missing company names/exchanges/
identifiers in the symbol-only source leave most candidates without an
acceptance basis. Candidate counts are not unique securities or record totals.

A record-by-record comparison with v6 asserted identical status, price_symbol,
resolved_security, match_basis, reason and candidate list, including unchanged
coverage input rows. Outcomes remain 48 resolved, 418 no_candidates, 14,169
candidates_unmatched, zero empty_response. All 13 coverage inputs remain
unresolved. Exit 2 correctly refuses use. No panel or price changes.

## Subscription and endpoint fields

Two read-only authenticated requests using the saved private key returned
HTTP 403: fundamentals/GSPC.INDX filtered to Components and to
HistoricalTickerComponents. No key or authenticated URL was saved in outputs.
Thus the current credential does not expose these constituent sections.

Official documentation checked on 2026-09-06:
https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds
The historical section documents Code, Name, StartDate, EndDate, IsActiveNow,
and IsDelisted, but not ISIN. Current components document ticker, exchange,
name, sector, industry and weight. No authenticated response was available
for field verification, so ISIN absence is a documented-schema finding.
The provider states historical S&P membership coverage begins April 2012;
earlier join dates exist, but companies that left before that boundary are
missing. An upgrade would therefore not by itself establish a complete 1999
constituent universe. No subscription change or purchase was made.

predicate-distribution.json and endpoint-entitlement.json preserve the
measurements; resolution.jsonl contains per-candidate diagnostics. Ruff and
mypy pass. Existing full-suite ETF bar-count defect remains outside this task.
