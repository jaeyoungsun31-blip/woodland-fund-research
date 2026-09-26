# 2026-09-02 — pipeline-v14-ablation: pre-registration (BINDING)

Append-only. Written and committed before `pipeline-v14-ablation` code is
implemented or any v14 market result is computed. Study id:
`pipeline-v14-ablation`.

## Question, prior, and stopping rule

This study asks which parts of a modular decision pipeline contribute anything
when added one at a time to the fixed v6 multi-asset trend ensemble. It does
not search for or promote a compound strategy. The incumbent research state is
the v6 equal-weight 4-10 month ensemble over SPY, EFA, EEM, TLT, IEF, and GLD,
with residual cash earning the real T-bill rate, implemented with v12's
planning-adopted partial-adjustment fraction of 0.50 and otherwise neutral
execution settings.

The prior evidence is adverse for several proposed options and is part of the
interpretation, not something to rediscover selectively:

* v5 found inverse-vol and shrinkage minimum-variance Sharpe of 0.679 and
  0.624, versus 0.700 for equal weighting. V14 re-tests those estimators on
  the v6 multi-asset universe so the sizing stage is complete.
* v3 and v9 found that volatility targeting helped the balanced benchmark
  more than trend. V14's symmetric and asymmetric exposure arms are re-tests
  of that mechanism, not novel hypotheses.
* v12 found partial adjustment useful as a turnover-reducing non-inferiority
  mechanic, not as return edge, and materially decade-dependent. Its 0.50
  setting is the baseline implementation; v14 does not reopen the 216-cell
  execution search.

The study stops after the nine fixed states, eight paired ablations, required
leave-one-decade-out checks, immutable ledger rows, stdout record, and factual
results entry are complete. No state, option, stage, or decade is selected.

## Universe and frozen harness

Use the same ETF price matrix, suspect-date treatment, real daily risk-free
series, and frozen walk-forward scheme as v6/v12: 5-year train, 1-year
validation, 1-year step, 210-bar embargo, 22 realized folds, and the stitched
OOS window 2004-10-22 through 2026-09-01 (expected 5,499 bars). The v6 target
stream is rebuilt and the baseline partial-0.50 result is sanity-checked before
inference or ledger writes.

All features and decisions at close t use only observations through t. Sparse
month-end decisions execute at close t+1 under the existing engine contract.
New feature and overlay behavior receives future-price perturbation tests
before the first v14 market result is inspected.

## Composable state machine and fixed stage definitions

`woodland/pipeline.py` will implement ordered state transitions S0 through S4.
Each optional stage can be disabled independently, and the implementation must
reject skipped, repeated, or out-of-order transitions.

### S0 — features

The fixed momentum object is `trend.ensemble_targets` over lookbacks 4 through
10 months. S0 also computes:

1. trailing 63-bar annualized realized volatility for each risk asset; and
2. cross-sectional dispersion at each month end: the population standard
   deviation across the six assets of each asset's equal-weight average
   trailing total return over the same 4-10 month horizons.

The low-dispersion threshold at month t is the expanding 33 1/3 percentile of
prior month-end dispersion observations, shifted one month and requiring 12
prior observations. It is therefore known before t's dispersion is classified.
The tercile, 12-observation warm-up, feature definition, and lookbacks are
fixed here and are not searched. Before the threshold exists, S1 is inactive.

S0 is the common information layer, not a return-bearing alternative: removing
momentum leaves no v6 strategy, while realized vol and dispersion only affect
returns through their separately tested S1/S3 consumers. No independent
performance claim is made for merely computing an unused feature.

### S1 — regime filter

When current dispersion is at or below its pre-t-known bottom-tercile
threshold, multiply the entire risky target vector by 0.50; otherwise multiply
it by 1.00. Residual weight is cash. The 0.50 scale and the tercile rule are
single fixed values, not searched. This conditions only on a current measured
state, never on named historical crashes or the strategy's trade outcomes.

### S2 — sizing

Options are equal weight (default), inverse volatility, and long-only
Ledoit-Wolf shrinkage minimum variance. The latter two use the existing
`signals/riskweight.py` implementation and a trailing 126-bar window, exactly
the fixed estimator window used in v5. They allocate the risky budget only
among assets active in each trend constituent; all seven lookback target
vectors are still averaged without selection.

### S3 — exposure

Options are none (default), symmetric volatility target, and asymmetric
volatility target. Both use trailing 63-bar annualized pre-cost portfolio
volatility, a 10% annual target, and a maximum scale of 1.0, leaving residual
capital in cash. Symmetric targeting applies the desired scale immediately at
each month-end decision. Asymmetric targeting applies a downward scale change
immediately but restores exposure by only 50% of the gap to the desired scale
at each later decision. Down-rate 1.0 and up-rate 0.50 are fixed and not
searched. The volatility estimate is based on the post-S1/S2 target stream.

### S4 — execution

Options are no overlay (full adjustment, used only as an ablation comparator),
partial adjustment 0.50 (adopted default), a portfolio-wide 5% L-infinity
no-trade band with full adjustment, and both the 0.50 partial adjustment and
5% band. These reuse `woodland/execution.py`; no delay, tranching, or missed
rebalance is introduced.

## Fixed configurations and ablations

Exactly nine configurations are evaluated:

| id | S1 | S2 | S3 | S4 |
|---|---|---|---|---|
| `raw-v6` | off | equal | none | none |
| `baseline` | off | equal | none | partial-0.50 |
| `s1-dispersion` | on | equal | none | partial-0.50 |
| `s2-inverse-vol` | off | inverse-vol | none | partial-0.50 |
| `s2-min-variance` | off | min-variance | none | partial-0.50 |
| `s3-symmetric` | off | equal | symmetric | partial-0.50 |
| `s3-asymmetric` | off | equal | asymmetric | partial-0.50 |
| `s4-band` | off | equal | none | band-0.05 |
| `s4-partial-band` | off | equal | none | partial-0.50 + band-0.05 |

The eight contribution comparisons, fixed before results, are:

* S1 dispersion minus `baseline`;
* S2 inverse-vol minus `baseline`;
* S2 min-variance minus `baseline`;
* S3 symmetric minus `baseline`;
* S3 asymmetric minus `baseline`;
* S4 partial-0.50 (`baseline`) minus `raw-v6`;
* S4 band-only minus `raw-v6`; and
* S4 adding the band (`s4-partial-band`) minus `baseline`.

This is intentionally not a 2 x 3 x 3 x 4 factorial search. Interactions and
compound combinations are outside v14. A failure of any full/compound
pipeline, here or later, falsifies nothing about any individual stage. Only a
stage's own pre-specified paired ablation against the otherwise identical
pipeline without that mechanic speaks to that stage. Conversely, one passing
stage does not establish that a compound pipeline passes.

## Inference, pass labels, and decade dependence

The primary contribution table is at 10 bps and reports stage/option,
comparator, Sharpe difference, paired 95% stationary-block-bootstrap interval
and two-sided p-value (10,000 resamples, expected block length 21, seed 0), the
Ledoit-Wolf HAC counterpart, pairwise correlation, and annualized-turnover
change.

Two labels are descriptive and fixed in advance:

1. `statistically_positive` requires positive delta Sharpe and both the
   bootstrap and HAC two-sided p-values below 0.05.
2. `current_gate_shape` applies the still-binding DESIGN.md section 8 shape to
   the paired ablation at 10 bps: delta Sharpe at least +0.10, bootstrap lower
   endpoint above -0.10, maximum drawdown no worse than 1.25 times the
   comparator's magnitude, and annualized turnover no more than 1.5 times the
   comparator's. This label is diagnostic and does not promote a stage.

Any ablation receiving either label gets leave-one-decade-out reporting with
the 2000s, 2010s, and 2020s removed in turn. Recompute delta Sharpe, bootstrap
CI/p, HAC delta/p, correlation, and turnover change on each remaining sample.
No omission is selected. If none qualifies, print that the pre-registered LODO
section has no qualifying stage rather than expanding the rule after seeing
results.

## Standard reporting and accounting

For all nine configurations, print CAGR, annualized volatility, Sharpe at rf=0
and against the real risk-free rate, maximum drawdown, worst day, fifth
percentile daily return, annualized turnover, and exposure diagnostics at
0/5/10 bps. Print SPY buy-and-hold, monthly 60/40, and the vol-targeted 60/40
on the identical OOS dates. Print `metrics.by_subperiod` at 5 bps for every
configuration and the required baselines. Print the contribution table, any
LODO rows, distinct trial count, and deflated-Sharpe effective-breadth note.
Positive, null, and negative results receive the same output.

Ledger accounting is nine configurations x 22 folds = 198 new rows under
`pipeline-v14-ablation`, scored at the standard 5 bps ledger cost. The same
configuration reported at additional costs is not a new searched
configuration. No weights, options, stages, or combinations are selected.

The source store remains dual-source checked but not clean under the codified
2% rule. Results are research evidence, not a trade instruction.

## Carry exclusion and data prerequisite

Carry is excluded, not silently treated as zero and not represented by a proxy.
It is not computable from the current store: bond carry requires yield to
maturity, commodity carry requires a futures curve, and equity carry requires
dividend-yield data. Adding carry requires a separately approved data-layer
decision, ingestion provenance, and dual-source validation before any study
pre-registration. Carry is therefore a data prerequisite, not an S-stage in
v14.
