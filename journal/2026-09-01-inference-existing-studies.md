# 2026-09-01 — Error bars on the existing studies

Append-only. HANDOFF 2026-09-01c step 2. **No new backtest and no new ledger
rows**: v2 and v3 each have one pre-registered configuration, so their stitched
OOS series are fully determined by the frozen split scheme and were rebuilt
exactly. `scripts/run_inference.py` refuses to report any inference unless the
rebuild reproduces the journalled Sharpes first — it does, to three decimals,
for all five series (v2 0.700, v3 0.709, SPY 0.660, 60/40 0.806, vol-target
60/40 0.853).

Window: 2004-10-22 .. 2026-09-01, 5,499 bars (21.8y), all series at 5 bps.
Bootstrap: stationary block bootstrap, **10,000 resamples, block length 21**,
pre-chosen. HAC: Ledoit-Wolf delta method, Bartlett kernel, Andrews plug-in
bandwidth (5-7 lags selected).

## Planning's question: is 60/40's lead over the ensemble real?

**No. It is well inside noise.**

| comparison | ΔSharpe | 95% CI (bootstrap) | p (bootstrap) | p (HAC) | corr |
|---|---:|---|---:|---:|---:|
| v2 − 60/40 | **−0.106** | [−0.371, +0.158] | **0.433** | 0.417 | 0.782 |
| v2 − SPY | +0.040 | [−0.197, +0.284] | 0.746 | 0.741 | 0.796 |
| v3 − vol-target 60/40 | −0.144 | [−0.385, +0.088] | 0.234 | 0.242 | 0.831 |

Not one comparison is distinguishable from zero at 5%. The two methods agree
closely throughout (p within 0.02 of each other everywhere), which is the
reassurance worth having: a block bootstrap and an analytic HAC test share
almost no machinery, so their agreement is evidence the numbers are real.

Every ranking this project has stated across three sessions — "v2 is ahead of
SPY", "still behind 60/40", "v3 trails vol-targeted 60/40" — describes
differences the data cannot resolve. Those statements were not wrong as
descriptions of the point estimates, but they were read as if they ranked the
strategies, and they do not.

## The levels are far worse determined than the differences

| series | Sharpe | 95% CI | width |
|---|---:|---|---:|
| v2 ensemble | 0.700 | [0.322, 1.107] | 0.785 |
| v3 voltarget | 0.709 | [0.334, 1.109] | 0.775 |
| SPY buy&hold | 0.660 | [0.282, 1.078] | 0.796 |
| 60/40 | 0.806 | [0.405, 1.244] | 0.840 |
| vol-target 60/40 | 0.853 | [0.451, 1.287] | 0.836 |

A single Sharpe on 21.8 years carries a CI roughly **±0.4** — every strategy
here is individually consistent with anything from "mediocre" to "excellent".
Differences are about three times better determined (±0.13) purely because the
series are 78-83% correlated and the comparison is paired. That is the entire
reason `stats.py` resamples rows jointly.

## The naive iid test is wrong in both directions

Worth recording precisely, because it corrects an over-simple claim I would
otherwise have carried forward. In the synthetic tests the naive iid test
**over-rejects** badly — measured size 20.0% at a nominal 5% on autocorrelated
data under a true null, against 4.5% for the block bootstrap and 5.0% for HAC.

On these real comparisons it does the opposite: its CI for v2 − 60/40 is
[−0.700, +0.488], **more than twice as wide** as the bootstrap's. The naive
test makes two false assumptions, and they push opposite ways — ignoring
autocorrelation narrows the interval, ignoring the 0.78 cross-correlation
between the two strategies widens it. Which error dominates depends on the
data. The lesson is not "the naive test is too aggressive"; it is that its
answer carries no reliable sign of error at all.

## What this does not say

Failing to reject is not evidence of equivalence. The CI for v2 − 60/40 spans
−0.371 to +0.158: entirely consistent with 60/40 being genuinely much better,
and also with the two being equal. The honest summary is that **21.8 years of
monthly decisions cannot separate these strategies**, not that they are the
same.

## Power: what this sample can and cannot resolve

Measured SE of a Sharpe difference on this window is ≈ **0.125**. Taking that
as representative, at α = 0.05 two-sided:

| target difference | years of OOS needed (80% power) | (50% power) |
|---|---:|---:|
| 0.10 Sharpe | **269** | 132 |
| 0.20 Sharpe | 67 | 33 |
| 0.30 Sharpe | 30 | 15 |
| 0.50 Sharpe | 11 | 5 |

With the 21.8 years we have, the smallest difference detectable at 80% power
is **0.351 Sharpe**. The pre-registered §8 gate's threshold is 0.10 — roughly
**3.5x finer than the data can resolve**. A gate that simply demanded p < 0.05
on a 0.10 Sharpe edge would never promote anything, for any strategy, within
any horizon this project will ever have.

That is not an argument against measuring significance. It is an argument that
the gate must be designed knowing this, which is what the proposal under
QUESTIONS FOR PLANNING addresses. Not self-adopted: §8 is pre-registered.

## Caveats

Source-verification caveat unchanged (63 historical observations over the 2%
threshold, `journal/2026-09-01-crosscheck-policy-reingest.md`). Sharpes use
rf = 0, which overstates every level here but affects differences far less
since a common risk-free rate largely cancels. Bootstrap CIs are percentile
intervals; no BCa correction was applied.
