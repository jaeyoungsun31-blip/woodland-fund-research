# 2026-09-01 — Fama-French 12-industry deep-history ingest

Append-only engineering record for HANDOFF 2026-09-01b, step 4. This is data
preparation, not a strategy result or performance claim.

## Source and construction

Downloaded the official `12_Industry_Portfolios_daily_CSV.zip` archive from
the [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html).
The parser selects only `Average Value Weighted Returns -- Daily`; it does not
splice the equal-weighted section that follows it. Source percentages are
divided by 100 and compounded into synthetic index levels from base 100.

These series are **frictionless academic portfolio constructs, not tradeable
securities**. The derived levels omit spreads, commissions, market impact,
implementation lag, and any investable product tracking difference. That
limitation is printed by the ingest script and persisted in provenance.

## Realized ingest

Command: `.venv/bin/python scripts/ingest_fama_french.py`

| Check | Result |
|---|---:|
| source archive member | `12_Industry_Portfolios_Daily.csv` |
| archive SHA-256 | `0f651b0c3eaedb7e13b4997ab6e7ac6f3405160f5049ffada7fc12a3534fb231` |
| first / last observation | 1926-07-01 / 2026-06-30 |
| daily rows | 26,274 |
| industries | 12 |
| missing returns | 0 |
| nonpositive derived levels | 0 |
| folds under the frozen 5y/1y/1y/210-bar scheme | 95 |

The rebuildable parquet and provenance JSON are under ignored `data/`; no
market data is committed. Code and parsing/validation tests are commit
`4719562`. The commit's required post-commit test run passed: 94 tests.

## v4 status: blocked before pre-registration

The requested deep-history strategy cannot be specified faithfully from this
dataset alone:

1. v1/v2 allocate every failed trend sleeve to IEF, but IEF begins in 2002 and
   the academic industry file has no bond or risk-free leg. Choosing zero-return
   cash or adding a historical fixed-income source changes the strategy.
2. Binding rule 5 requires literal SPY and 60/40 over the identical reporting
   window. Neither SPY nor IEF exists over 1926+, and this file cannot construct
   a 60/40 benchmark. Calling an industry average “SPY” would mislabel a proxy.

Those are planning-owned methodology choices, not ingestion engineering. Q4
has been added to `CLAUDE.md`. No v4 pre-registration, ledger rows, backtest,
or result inspection occurred.
