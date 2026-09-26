# 2026-09-03 — planning finding: the rf=0 Sharpe convention biases every comparison toward the balanced control

Append-only. This is a **measurement finding, not a new study**. It re-examines
results already on the record using series already stored. It is raised because
it may have caused a false negative in the study that closed the research
phase, and the termination decision should not take effect until it is resolved.

## The problem

Every pre-registered pass/fail criterion in v15 and v17 was evaluated on
**annualized Sharpe with rf = 0**. `paired_inference` in
`scripts/run_sleeve_overlay.py` computes column Sharpes directly on the raw
return series with no risk-free subtraction, and C1/C3 are read off those
deltas.

The Sharpe ratio is defined on **excess** returns. Setting rf = 0 is
harmless only when the risk-free rate is actually near zero. The OOS window
here is 1932-09-06 to 2026-06-30, over which the journalled mean annualized
real risk-free rate is **3.0761%**. It is not near zero.

The consequence is not neutral across the configurations being compared,
because the incumbent holds cash and the challengers do not. For
`60/40 = 0.6*MKT + 0.4*CASH`:

    rf=0 Sharpe(60/40) = mean(0.6*r_mkt + 0.4*rf) / sd(0.6*r_mkt)
                       = Sharpe_rf0(MKT) + (0.4 * rf) / sd(60/40)

The second term is a **mechanical addition** to the incumbent's measured
Sharpe, arising entirely from counting the cash leg's return as return while
it contributes no volatility. With rf = 3.0761% and sd(60/40) ~ 10.8%
annualized, it is worth approximately:

    +0.114 Sharpe, handed to the incumbent by the choice of metric alone.

v15's own results entry already identified the mechanism in passing — "the
balanced control retained the highest rf=0 Sharpe at every registered cost
because its CASH return is included in the portfolio return before the rf=0
calculation" — but the observation was not carried through to the pass
criteria, which continued to be evaluated on the biased measure. Planning owns
that oversight; it read the sentence and did not act on it.

## Why it is material rather than a technicality

The artifact is larger than every effect being tested:

| Quantity | Value | Artifact / effect |
|---|---:|---:|
| Mechanical bonus to 60/40 from rf=0 | +0.114 | — |
| v17 primary A, 10 bps, delta SR | -0.0054 | 21.1x |
| v17 post-1980, 10 bps, delta SR | -0.0125 | 9.1x |
| v17 s=30%, 10 bps, delta SR | -0.0195 | 5.8x |

A measurement artifact twenty-one times the size of the measured effect is not
a rounding concern. It is the dominant term.

## The sign flips on the correct measure

Both v15 and v17 also reported Sharpe against the real risk-free series. Those
numbers were printed but were not the criterion:

| Series, 10 bps | rf=0 Sharpe | Sharpe vs real rf |
|---|---:|---:|
| v15 monthly momentum | 0.789 | 0.620 |
| v15 60/40 | 0.858 | 0.538 |
| v17 overlay, s=10% | 0.852530 | 0.556338 |
| v17 60/40 | 0.857929 | 0.538109 |

v17 primary A: delta is **-0.0054 on rf=0** (C1 failed) and **+0.0182 against
the real risk-free rate** (sign reversed). v15 monthly versus 60/40 moves from
-0.069 to **+0.082**.

## What this does NOT establish

It does not establish that v17 passes, and it must not be reported that way.

1. **Significance is unknown.** Every confidence interval and p-value in v15
   and v17 was bootstrapped on rf=0 deltas. The excess-return deltas have no
   inference attached to them yet. A sign flip in a point estimate is not a
   result.
2. **The tail findings are unaffected.** 60/40's advantage in CVaR95, CVaR99,
   maximum drawdown and underwater duration does not depend on the Sharpe
   convention. v17's C2 comparison and every tail conclusion stand.
3. **The identification gap is unaffected.** Both sleeve paths and all
   turnover figures remain model-implied, not observed.
4. **The post-1980 question is unresolved,** not overturned. It must be
   recomputed, not assumed to flip.
5. **The turnover budget is unaffected** — it is derived from crossover costs
   and turnover, neither of which involves the risk-free convention.

## Required correction — a recomputation, not a study

This qualifies under T2 of
`2026-09-03-planning-decision-termination-and-v16-withdrawal.md` because it
names precisely the quantity it changes: the metric on which the incumbent's
measured advantage rests. It adds no configuration, no data and no
hypothesis, and it must not be permitted to become a search.

Recompute, from stored return series, with the pre-registered bootstrap
unchanged (10,000 resamples, expected block 21, seed 0):

* v17 C1 and C3, on excess returns over the aligned daily real risk-free
  series, at all five registered costs, for all four fixed weights and B.
* v15's paired comparisons versus 60/40 and versus MKT on the same basis.
* Both era subsamples.

Report the excess-return result **beside** the rf=0 result for every
comparison, never in place of it. The rf=0 numbers are the pre-registered
ones and remain on the record exactly as journalled; this is a stated,
dated correction to the metric, not a revision of history.

`woodland/metrics.py` already accepts `rf_daily`; the defect is that the
inference path does not use it. Fix the inference path, and add a regression
test asserting that a paired comparison between a cash-heavy and a
fully-invested portfolio gives different answers under the two conventions —
so this cannot silently recur.

## Status

**The termination decision is suspended pending this recomputation.** T1's
condition was met on a metric that is now known to be biased against the
challenger by roughly twenty-one times the measured effect. Whether the
research phase closes depends on what the corrected inference says.
