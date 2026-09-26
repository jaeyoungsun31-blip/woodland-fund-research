# 2026-09-02 — xsmom-v11-deciles: EXPLORATORY, NOT PRE-REGISTERED

Append-only.

## Procedural disclosure — read before the numbers

**This study was run WITHOUT a pre-registration entry, violating CLAUDE.md
rule 3.** The v10 entry pre-registered cross-sectional momentum on the 12
industry portfolios; this extends to a different universe (10 stock-level
prior-return deciles) and should have had its own entry written first. It did
not. The error is the planning session's own, recorded here rather than
quietly fixed, because a rule that bends for whoever is impatient is not a rule.

**Consequence, applied:** everything below is EXPLORATORY. It generates a
hypothesis; it does not confirm one. No number here may be cited as a
pre-registered finding, and the headline result requires a pre-registered
confirmation study before it counts for anything.

Data: Ken French 10 Portfolios Formed on Prior (12-2) Returns, value-weighted
daily, downloaded by the user (both sandboxes are blocked from the server).
OOS 1932-09-06 .. 2026-06-30, 24,434 bars (94.1y), 94 folds, 252-bar embargo.
Script `scripts/run_xsmom_deciles.py`, raw output `reports/xsmom-v11-stdout.txt`.

## 1. The sort is real, and it is monotone

This is what 12 industries were too coarse to show.

| decile | CAGR | vol | Sharpe | max DD |
|---|---:|---:|---:|---:|
| Lo PRIOR | 2.86% | 26.6% | 0.238 | −93.7% |
| PRIOR 2 | 7.43% | 21.6% | 0.439 | −77.3% |
| PRIOR 3 | 10.33% | 19.0% | 0.612 | −70.4% |
| PRIOR 4 | 10.40% | 17.8% | 0.645 | −61.3% |
| PRIOR 5 | 10.52% | 17.0% | 0.675 | −53.9% |
| PRIOR 6 | 11.30% | 16.7% | 0.724 | −57.0% |
| PRIOR 7 | 11.50% | 16.7% | 0.734 | −50.3% |
| PRIOR 8 | 13.20% | 17.0% | 0.815 | −50.3% |
| PRIOR 9 | 12.40% | 18.3% | 0.730 | −60.5% |
| **Hi PRIOR** | **16.70%** | 22.2% | 0.809 | −56.7% |

A **13.8-point CAGR spread** from worst to best decile, rising almost
monotonically over 94 years. Volatility is U-shaped: losers are the most
volatile, the middle is calmest, winners are volatile again.

## 2. The load-bearing control PASSES here — unlike at industry level

| comparison | ΔSharpe | 95% CI | p (boot) | p (HAC) | corr |
|---|---:|---|---:|---:|---:|
| **top-3 deciles − equal-weight 10** | **+0.132** | [+0.042, +0.226] | **0.0046** | **0.0037** | 0.916 |
| top decile − equal-weight 10 | +0.121 | [−0.004, +0.250] | 0.065 | 0.055 | 0.829 |
| top decile − MKT | +0.084 | [−0.027, +0.197] | 0.142 | 0.124 | 0.866 |
| top decile − 60/40 | −0.051 | [−0.164, +0.063] | 0.387 | 0.361 | 0.865 |

v10 found industry momentum could not beat equal-weighting the same 12
industries (+0.028, p = 0.52). At stock level the same control is cleared at
**p = 0.005**. The v10 conclusion was therefore about **granularity**, not
about momentum — exactly the caveat that entry flagged, now measured.

Note also that the top *three* deciles beat the top *one* on Sharpe (0.820 vs
0.809) with meaningfully less volatility. "Averaging beats choosing" appears a
fourth time.

## 3. THE CAVEAT THAT DOMINATES EVERYTHING ABOVE

French constructs these portfolios **daily**. Stocks enter and leave each
decile continuously, and that internal turnover is **entirely uncharged** —
our engine sees annual turnover of **0.01** for holding a decile, because the
only trade it observes is the trivial monthly re-weight.

Momentum is among the highest-turnover strategies known. The real cost of
maintaining a top-decile momentum portfolio is large and is **not modelled
anywhere in this result**. The 5 bps figure in the tables is therefore close
to meaningless for these series.

Until a study charges realistic momentum turnover, the honest reading is:
**the momentum sort is real in gross returns, and its net tradeability is
untested.** That is not a footnote; it is the difference between an academic
regularity and a strategy.

## 4. Still loses to the boring portfolio

60/40 MKT/CASH: Sharpe 0.859. Top decile: 0.809. Even with a real, monotone,
century-long stock-level sort — gross of its own costs — the risk-adjusted
winner remains a balanced portfolio, because momentum carries 22.2% volatility
against 9.6%.

## 5. Decay, again

| era | top decile vs EW-10 | p |
|---|---|---|
| 1932-1979 (50.5y) | +0.162, CI [+0.002, +0.327] | 0.052 |
| 1980-2026 (46.5y) | +0.082, CI [−0.113, +0.274] | 0.404 |

The same pre/post-1980 weakening seen in v4's trend result. Note this
CONTRADICTS v10, where industry momentum looked slightly stronger post-1980 —
so the v10 non-decay reading should not be carried forward.

## 6. The long-short factor, for the record

Hi − Lo, unlevered: Sharpe 0.512, max drawdown **−85.2%**, **6,404 days
(25 years) underwater**, skew −1.15, excess kurtosis 20.5. The academic
momentum factor is a catastrophic standalone holding, and Sharpe describes it
poorly at that level of skew.

## Trials

6 fixed configurations plus 10 single-decile diagnostics = 16 evaluated. Not
logged to `journal/trials.db` by this script — a further consequence of
skipping pre-registration, and something the confirmation study must repair.

## Required next step

Pre-register a confirmation study before any of this is treated as a finding:
charge realistic momentum turnover, log to the ledger, and fix in advance
whether the claim is about the top decile or the top three.
