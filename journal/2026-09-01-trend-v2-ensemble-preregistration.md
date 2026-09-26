# 2026-09-01 — Preregistration: trend-v2-ensemble

Append-only preregistration written before the study is run or any result is
inspected.

## Question

Does eliminating per-fold lookback selection improve the stability and
out-of-sample behavior of trend-v1 by averaging the same seven nearby trend
portfolios?

## Frozen specification

* Study id: `trend-v2-ensemble`.
* Data: current ETF adjusted-close store. The source-verification caveat from
  `2026-09-01-crosscheck-policy-reingest.md` remains in force.
* Risk assets: XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY.
* Risk-off asset: IEF.
* Constituent lookbacks: exactly 4, 5, 6, 7, 8, 9, and 10 months.
* Each constituent is the existing Faber-style monthly trend portfolio. The
  ensemble target at each decision date is the arithmetic mean of the seven
  complete target-weight vectors, including each vector's IEF allocation.
* No lookback is selected per fold. There is one fixed ensemble configuration
  and therefore one distinct trial/configuration in this study's ledger.
* Maximum declared lookback: 210 trading days.
* Walk-forward scheme: the already preregistered 5-year train / 1-year
  validate / 1-year step scheme with a 210-trading-day embargo. The fixed
  configuration is evaluated and logged on every fold; train scores do not
  choose or alter it.
* Execution and costs: existing next-close engine, reported at 0/5/10 bps.

## Required report

One stitched OOS curve at all three costs, beside SPY buy-and-hold and 60/40
over the identical window; sub-period metrics; annualized turnover; fold
count; trials count; DSR with the effective-breadth note. The result is
journaled whether positive or negative. No promotion decision is made.
