# 2026-09-01 — Trend study v1: results

Append-only. Pre-registered in
`journal/2026-09-01-trend-study-preregistration.md`; nothing below deviates
from what was fixed there. Ledger: `journal/trials.db`, study `trend-v1`.

**Harness output, not a promotion decision.** The §8 gate is Phase 3 and
planning has not ruled on these numbers. Nothing is promoted; nothing trades.

## Result: the strategy loses to both baselines risk-adjusted

Stitched out-of-sample, 2004-10-22 .. 2026-09-01, 5498 bars (21.8y), identical
window for every row.

| | CAGR | vol | Sharpe (rf=0) | max DD | ann. turnover |
|---|---|---|---|---|---|
| trend-v1 @0bps | 9.20% | 15.84% | 0.636 | −43.2% | 7.46 |
| **trend-v1 @5bps** | **8.80%** | **15.83%** | **0.612** | **−43.6%** | **7.46** |
| trend-v1 @10bps | 8.39% | 15.83% | 0.589 | −44.1% | 7.46 |
| SPY buy&hold | 11.25% | 18.84% | 0.660 | −55.2% | 0.00 |
| 60/40 @5bps | 8.33% | 10.62% | 0.806 | −32.3% | 0.23 |

Read plainly:

* It **loses to 60/40 on every axis that matters** — lower Sharpe (0.612 vs
  0.806), deeper drawdown (−43.6% vs −32.3%), and **32x the turnover**
  (7.46 vs 0.23 annually). The marginal CAGR edge (8.80% vs 8.33%) is bought
  with half again as much volatility.
* It **loses to SPY on Sharpe** (0.612 vs 0.660) and on CAGR (8.80% vs
  11.25%), winning only on drawdown (−43.6% vs −55.2%). Trend-following is
  supposed to buy drawdown protection with return; here it paid for the
  protection and got less risk-adjusted return anyway.
* Costs bite as expected but do not drive the conclusion: the ranking is
  unchanged at 0 bps, where the strategy still trails both baselines on Sharpe.

## Deflated Sharpe — and why it must not be over-read

At 5 bps: Sharpe 0.61 over 21.8y, SR0 = 0.05 after 7 trials, **DSR = 0.995**
(0.996 at 0 bps, 0.993 at 10 bps). Skew −0.49, excess kurtosis **18.4**.

A 0.995 looks like a pass. It is not, for two reasons:

1. **DSR tests the wrong benchmark for this question.** It asks whether the
   true Sharpe exceeds SR0 — a selection-adjusted *zero* — not whether it
   exceeds SPY or 60/40. It says "this 0.61 is probably genuinely positive",
   which is not in dispute. The gate's question is whether it beats an
   incumbent, and on that the answer above is no.
2. **The deflation is weak here because the trials were near-collinear.** The
   7 configs are one parameter apart on the same strategy; their mean train
   Sharpes span only 0.579–0.682, sd 0.04, so SR0 comes out at 0.05 — almost
   no hurdle. The deflated Sharpe punishes *breadth* of search, and this
   search had none. A high DSR from 7 nearly-identical configs is much weaker
   evidence than the same number from 7 genuinely different strategies.

Excess kurtosis of 18.4 is also worth stating: daily returns are far from
normal, so every Sharpe here is less informative than its standard error
suggests.

## Config churn — DESIGN.md §10's named failure mode, visible

Selected lookback per fold:
`4 4 4 4 8 10 6 6 6 5 5 4 4 8 8 8 7 5 5 10 5 5`

**6 of the 7 available lookbacks were selected at some point, with 10 switches
across 22 folds.** Win counts: 4→6 folds, 5→6, 8→4, 6→3, 10→2, 7→1, 9→0. The
train window does not identify a stable parameter; it picks a different one
roughly every other year. That is precisely the "chasing last year's winner"
degeneracy §10 warns about, and it is an argument that this parameter is not
estimable from 5 years of data rather than an argument for a different value.

## Sub-period breakdown @5bps (regime honesty, §7)

| period | CAGR | Sharpe | max DD |
|---|---|---|---|
| 2004-10-22..2008-01-01 | 13.22% | 1.075 | −10.9% |
| 2008-01-01..2015-01-01 | 6.99% | 0.492 | −41.0% |
| 2015-01-01..2020-01-01 | 8.50% | 0.726 | −17.5% |
| 2020-01-01..2022-01-01 | 14.96% | 0.666 | −30.6% |
| 2022-01-01..2026-09-01 | 6.33% | 0.497 | −22.0% |

The best sub-period is the **earliest and shortest** (3.2 years), and the two
weakest are 2008-2015 and 2022-present. There is no period in which it clearly
beats 60/40 on Sharpe. Whatever is here is not strengthening over time.

## Process notes

* 154 evaluations recorded, 7 distinct configs — exactly as pre-registered.
* The study is deterministic: it was run twice (once after adding turnover to
  the report) and produced identical figures. The ledger was reset before the
  final run so it holds exactly one clean record of the pre-registered study.
* Data carries the unlifted single-source caveat
  (`journal/2026-09-01-tiingo-crosscheck-first-run.md`). Measured provider
  disagreement is ~0.004 Sharpe, far below the gaps above, so it does not
  change any conclusion here.

## What I am NOT concluding

Not that trend-following does not work — this is one universe (9 sector ETFs),
one risk-off leg, one parameter, one cost model, monthly rebalancing, no
volatility targeting. DESIGN.md §9's candidate 3 (vol-managed overlay) is
untested and is the natural next variation. The finding is narrower and firmer
than a verdict on the family: **as specified and pre-registered, trend-v1 does
not beat the baselines it must beat, and its parameter is unstable.**
