# 2026-09-04 — Phase 4 dress rehearsal

Append-only operational safety rehearsal. Not a study and no order was submitted.
The source `data/` store was content-hashed before and after a temporary copied-store run.

| Condition | Cycle refused | Target emitted | Result | Detail |
|---|---:|---:|---|---|
| stale data (>5 calendar days) | True | False | PASS | stale_data: terminal bar is 6 calendar days old; tolerance is 5 |
| corrupted calendar date | True | False | PASS | integrity: calendar integrity: injected corrupted date |
| frozen fold-count mismatch | True | False | PASS | fold_count: realized 21, expected 22 |
| sanity-anchor breach | True | False | PASS | sanity_anchor: SPY CAGR 15.00% outside 6%-9% |
| market closed | False | False | PASS | market_closed |
| live base URL | False | False | PASS | submission refused: execution host must be exactly paper-api.alpaca.markets |

Market-closed and live-host cases are broker submission guards; no broker request was made.
