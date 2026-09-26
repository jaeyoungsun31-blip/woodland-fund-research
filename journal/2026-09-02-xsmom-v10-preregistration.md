# 2026-09-02 — xsmom-v10-industry: pre-registration (BINDING)

Append-only, written BEFORE the study runs. Executed by the planning session
(no coding agent available); same rules apply.

Study id: `xsmom-v10-industry`.

## Direction

First CROSS-SECTIONAL study in the project, and the first test of DESIGN.md §9
candidate 2, unrun since day one. Every prior study has been time-series trend:
"is this asset above its own average?" This asks a different question: **"which
assets are outperforming the others right now?"** — ranking rather than
thresholding.

That is what quantitative equity research actually is. Firms do not pick
stocks; they rank a universe on a characteristic and hold the top slice. A
12-industry cross-section is that operation on a century of survivorship-free
data. Stock-level deciles are the same operation at finer granularity and are
blocked only by data access, not by method.

## AMENDMENT TO THE PRE-REGISTERED WALK-FORWARD SCHEME

`journal/2026-09-01-harness-scheme-preregistration.md` fixed the embargo at 210
trading days, sized to a 10-month time-series lookback. Cross-sectional
momentum uses a 12-month formation window (252 bars), which exceeds it, and
`check_embargo_covers_lookback` would correctly refuse to run.

**For this study only, the embargo is 252 trading days.** Declared here, before
running, as the harness-scheme entry requires. All other split parameters are
unchanged (5y train / 1y validate / 1y step). This shortens usable history
slightly and is the honest cost of a longer signal.

## Fixed design — nothing searched

| choice | value | why fixed |
|---|---|---|
| universe | FF 12 value-weighted industry portfolios, daily | already ingested, survivorship-free, 1926+ |
| signal | cumulative return from t−252 to t−21 | standard 12-1 momentum; the skipped final month avoids short-term reversal contaminating the rank |
| holding | top k = 3, equal weight | k fixed, NOT searched |
| rebalance | month-end, executed next bar | as every prior study |
| exposure | long-only, fully invested | no risk-off leg; this is a cross-sectional study, not a timing one |

Holding k fixed keeps the searched surface at zero. If a later study varies k,
that is a search and the trials ledger must carry it.

## Baselines — identical window

1. **MKT** buy-and-hold.
2. **60% MKT / 40% CASH**, monthly.
3. **Equal-weight all 12 industries**, monthly — **LOAD-BEARING.**

Baseline 3 is the point of the study, exactly as the static basket was in v7.
It isolates the ranking: it holds the same universe, rebalanced on the same
calendar, with no momentum information whatsoever. If top-3 does not beat
equal-weight-12, the ranking contributes nothing and the honest finding is that
cross-sectional momentum adds no value here — irrespective of how it compares
to the market.

## Reporting, fixed in advance

Stitched OOS Sharpe at rf=0 and against the real risk-free rate; paired
bootstrap (10,000 resamples, block 21) and HAC differences versus all three
baselines; max drawdown; worst day; turnover; correlation of every comparison
pair; 0/5/10 bps; **by-decade breakdown**; and the **pre/post-1980 split**,
because v4 found our one significant result concentrated before 1980 and this
study must be checked for the same decay rather than assumed immune.

## Trial accounting

One configuration, no selection, no fitting. Deflation vacuous; the paired
tests are load-bearing.

## What this cannot conclude

Industry portfolios are frictionless academic constructs, not instruments —
this measures the signal, not a tradeable product. Twelve industries is a
coarse cross-section; stock-level deciles would be finer and are unavailable
here. Nothing is promoted; the §8 gate is Phase 3.

## Pre-declared expectation

Planning expects a positive raw result versus the market (industry momentum is
well documented) and considers it genuinely uncertain whether top-3 beats
equal-weight-12 after costs, given that ranking 12 correlated equity industries
is a narrow cross-section. Recorded in advance.
