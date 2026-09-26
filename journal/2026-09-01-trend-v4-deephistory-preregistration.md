# 2026-09-01 — trend-v4-deephistory: pre-registration (BINDING)

Append-only, written BEFORE the study ran (CLAUDE.md rule 3). Owed from
HANDOFF 2026-09-01b, ordered by 2026-09-01c step 4.

## The two blockers from 2026-09-01b, and how they are resolved

`journal/2026-09-01-fama-french-12-industry-ingest.md` refused to specify v4
because the 12-industry file has no defensive leg and no way to build the
rule-5 baselines. Both are resolved from the **same academic source**, by
additionally ingesting the Ken French daily research-factors file
(`F-F_Research_Data_Factors_daily_CSV.zip`, 26,274 rows, identical calendar):

1. **Defensive leg — resolved, and more faithfully than before.** The factors
   file carries `RF`, the one-month Treasury bill rate. DESIGN.md §9 specifies
   the trend rule's alternative as "T-bills/IEF", so on a 1926-2026 window the
   T-bill leg is the *primary* reading of the design, not a substitute forced
   by data limits. v1/v2 used IEF only because T-bills were not in the ETF
   store. The leg earns the actual daily RF rather than zero-return cash.
2. **Baselines — partially resolved, and the shortfall is declared below.**
   `MKT = Mkt-RF + RF` is the CRSP value-weighted market total return, giving
   a genuine equity baseline over the whole window.

Sanity anchors on the derived series, checked before pre-registering: MKT CAGR
9.83%, vol 17.10%, max drawdown **-84.07%** (the 1929-32 collapse, matching
the textbook figure); CASH CAGR 3.06%, vol 0.19%, max drawdown 0.00% (T-bills
never fall nominally). Both are what they should be.

## Declared deviation from binding rule 5

Rule 5 requires results "beside SPY buy&hold and 60/40". **Neither exists over
1926-2026** — SPY begins 1993, IEF 2002. This study therefore reports:

* **MKT buy&hold** in place of SPY. Labelled `MKT`, never called SPY.
* **60% MKT / 40% CASH**, monthly rebalanced, in place of 60/40. Labelled
  exactly that. It is **not** a 60/40: T-bills are not ten-year Treasuries, and
  this analogue will understate both the return and the drawdown of a real
  bond sleeve, especially through the 1980s rate decline. It is the closest
  construction this source supports and it is the weaker of the two baselines
  as a result.

This is a deviation, not a satisfaction, of rule 5. It is raised as Q6 for
planning. If planning rejects it, the study is cheap to re-run against a
different baseline; nothing is promoted from it either way.

## Design, fixed in advance

| Choice | Value |
|---|---|
| risk assets | the 12 FF value-weighted industry portfolios |
| risk-off leg | `CASH` (daily RF, compounded) |
| rebalance | month-end, executed next bar |
| max risk weight | 1.0, long-only, no leverage |
| splits | frozen scheme: 5y train / 1y validate / 1y step / 210-bar embargo |
| realized folds | **95**, OOS 1932-03-15 .. 2026-06-30 (24,579 bars, 97.5y) |
| declared max_lookback_days | 210 (= 10 months, equal to the embargo) |
| costs | 0 / 5 / 10 bps |

## Two studies, deliberately separate

The handoff asks for selection AND ensemble. Running them as one grid would
conflate the questions, so they are two ledger studies mirroring v1 and v2
exactly, on 4.5x the data:

* **`trend-v4-deephistory-selection`** — grid of 7 single-lookback configs,
  `lookback_months ∈ {4..10}`, per-fold selection on train Sharpe at 5 bps.
  This is v1's setup. Expected ledger: 7 distinct configs, 665 rows.
  **It answers the question v1 raised**: v1 selected 6 of 7 lookbacks with 10
  switches over 22 folds. Does the choice stabilize with 5x the data, or was
  the instability intrinsic?
* **`trend-v4-deephistory-ensemble`** — one config, the fixed equal-weight
  average of all seven lookback portfolios. This is v2's setup. Expected
  ledger: 1 distinct config, 95 rows.

## Reporting, fixed in advance

0/5/10 bps; both baselines over the identical window; `metrics.by_subperiod`;
deflated Sharpe with the effective-breadth note; annualized turnover. **Plus,
new this session:** 95% bootstrap CIs and Sharpe-difference tests
(`woodland/stats.py`, 10,000 resamples, block length 21) on every headline
comparison. On 97.5 years the standard error of a Sharpe difference should
fall to roughly 0.06 from the ETF window's 0.125, making a ~0.17 difference
detectable at 80% power where 0.35 was needed before — this is the first study
in the project with enough sample to resolve anything.

Sub-period breaks: the default metric breaks were chosen for the ETF era. This
study additionally reports by decade, since the default four breaks would
lump 1932-2008 into one bucket.

## What this study cannot conclude

The series are **frictionless academic constructs, not tradeable securities**.
No index fund existed for most of this window; industry portfolios are not
purchasable; costs in 1932 were vastly higher than 10 bps, so the cost
scenarios understate real-world friction by an unknown and large factor for
the early decades. A good result here is evidence about the *signal*, not a
claim that the *strategy* was harvestable. Nothing is promoted; §8 is Phase 3.
