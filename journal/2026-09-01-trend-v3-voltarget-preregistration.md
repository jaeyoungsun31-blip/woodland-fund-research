# 2026-09-01 — Preregistration: trend-v3-voltarget

Append-only preregistration written before implementation is run or any
result is inspected.

## Question

Does scaling the fixed v2 ensemble down when its current realized volatility
is high improve how it spends risk, without conditioning on named crashes or
learning from its own trade outcomes?

## Frozen specification

* Study id: `trend-v3-voltarget`.
* Base portfolio: the exact fixed `trend-v2-ensemble` target vectors (equal
  average of 4-10 month trend portfolios; nine original sector ETFs; IEF as
  risk-off).
* Realized-volatility window: exactly 63 trading days. No search.
* Annualized volatility target: exactly 10%. No search.
* Realized vol at decision close t is the sample standard deviation of the
  unscaled base portfolio's daily returns through t over the trailing 63 bars,
  annualized by sqrt(252).
* Exposure multiplier: `min(1.0, 0.10 / realized_vol)`. The entire base
  target vector, including IEF, is multiplied by it; the remainder is cash.
  Leverage is never introduced. Until 63 valid observations exist, or if
  realized vol is zero, the multiplier is 1.0.
* The overlay acts only on current realized volatility. It contains no crash
  labels, historical crash-shape rules, drawdown pattern conditioning, or
  reinforcement/trade-outcome learning.
* One fixed configuration is entered in the trials ledger. No per-fold
  selection occurs.
* Existing 5-year train / 1-year validate / 1-year step scheme and
  210-trading-day embargo. Both fixed feature windows (210-day trend maximum
  and 63-day realized vol) are within the preregistered embargo.
* Execution and costs: existing next-close engine, reported at 0/5/10 bps.

## Like-for-like baseline

In addition to SPY and the ordinary 60/40 baseline, report a monthly
rebalanced 60% SPY / 40% IEF portfolio with the identical 63-day, 10%,
no-leverage volatility overlay at 0/5/10 bps over the same OOS window.

## Required report

Stitched OOS metrics at every cost; SPY, ordinary 60/40, and vol-targeted
60/40 on the identical window; sub-periods; turnover; folds; trials count;
DSR with effective breadth. Journal the result either way. No promotion
decision is made.
