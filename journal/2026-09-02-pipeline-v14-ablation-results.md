# 2026-09-02 — pipeline-v14-ablation: results

Append-only factual report for the study frozen in
`2026-09-02-pipeline-v14-ablation-preregistration.md`. Nothing is promoted and
no stage, option, configuration, or decade is selected.

Canonical stdout: `reports/pipeline-v14-ablation-stdout.txt` (158 lines,
SHA-256 `ddc7b4d2011dd4ae76c04f12468946ca989075d49bc60cdee63b47830de1432f`).

## Reconstruction, window, and accounting

The study used the fixed ETF OOS window 2004-10-22 through 2026-09-01: 5,499
bars and 22 folds. No suspect dates were removed. The real risk-free series
runs through 2026-06-30 and was carried forward for 44 ETF-calendar bars under
the existing bounded rule.

Both preregistered reconstruction anchors matched exactly:

| anchor @5bps | Sharpe | annual turnover |
|---|---:|---:|
| raw v6, rebuilt | 0.780673 | 5.153145 |
| raw v6, v12 record | 0.780673 | 5.153145 |
| partial-adjustment 0.50, rebuilt | 0.804639 | 2.772494 |
| partial-adjustment 0.50, v12 record | 0.804639 | 2.772494 |

The immutable ledger audit is exact: nine distinct configurations x 22 folds
= 198 rows under `pipeline-v14-ablation`, with split indices 0 through 21.

## All fixed pipeline states

Sharpe at rf=0 across the standard cost surface:

| configuration | 0bps | 5bps | 10bps |
|---|---:|---:|---:|
| raw v6 | 0.803704 | 0.780673 | 0.757584 |
| baseline: partial 0.50 | 0.817894 | 0.804639 | 0.791366 |
| S1 dispersion filter | 0.841654 | 0.828044 | 0.814416 |
| S2 inverse-vol | 0.822630 | 0.806791 | 0.790925 |
| S2 min-variance | 0.907556 | 0.884765 | 0.861913 |
| S3 symmetric vol target | 0.821798 | 0.807927 | 0.794036 |
| S3 asymmetric vol target | 0.817090 | 0.803301 | 0.789493 |
| S4 band only | 0.795221 | 0.772633 | 0.749985 |
| S4 partial plus band | 0.823594 | 0.810613 | 0.797613 |

Full 5 bps metrics show what produced those ratios:

| configuration | CAGR | vol | Sharpe rf=0 | Sharpe real-RF | max DD | turnover |
|---|---:|---:|---:|---:|---:|---:|
| raw v6 | 8.41% | 11.14% | 0.781 | 0.621 | -21.96% | 5.153 |
| baseline | 8.15% | 10.41% | 0.805 | 0.634 | -16.94% | 2.772 |
| S1 dispersion | 8.14% | 10.06% | 0.828 | 0.652 | -16.94% | 2.752 |
| S2 inverse-vol | 7.15% | 9.07% | 0.807 | 0.611 | -14.92% | 2.889 |
| S2 min-variance | 6.45% | 7.37% | 0.885 | 0.644 | -13.85% | 3.382 |
| S3 symmetric | 7.09% | 8.98% | 0.808 | 0.610 | -16.54% | 2.504 |
| S3 asymmetric | 6.90% | 8.79% | 0.803 | 0.601 | -16.13% | 2.437 |
| S4 band only | 8.29% | 11.12% | 0.773 | 0.613 | -22.19% | 5.042 |
| S4 partial plus band | 8.22% | 10.42% | 0.811 | 0.640 | -16.89% | 2.717 |

The min-variance state's higher Sharpe is a volatility result, not a return
result: versus the baseline it lowered 5 bps CAGR from 8.15% to 6.45% while
lowering volatility from 10.41% to 7.37%. The paired comparison below does not
distinguish its Sharpe contribution from zero.

## Required baselines

Identical-window rf=0 Sharpe:

| baseline | 0bps | 5bps | 10bps |
|---|---:|---:|---:|
| SPY buy-and-hold | 0.659864 | 0.659864 | 0.659864 |
| monthly 60/40 | 0.807285 | 0.806195 | 0.805104 |
| vol-targeted 60/40 | 0.865270 | 0.862283 | 0.859295 |

At 10 bps the adopted partial-adjustment trend baseline remains below both
ordinary 60/40 (0.791 versus 0.805) and vol-targeted 60/40 (0.791 versus
0.859). The highest point estimate among the nine states, min-variance at
0.862, is effectively level with vol-targeted 60/40 before paired uncertainty
is considered; v14 did not preregister that cross-family point estimate as a
promotion comparison.

## Stage contribution table

All comparisons use 10 bps returns, 10,000 joint stationary-bootstrap
resamples, expected block length 21, seed 0, and the Ledoit-Wolf HAC
counterpart. Turnover change is candidate minus the otherwise identical
pipeline without the named mechanic.

| stage ablation | delta Sharpe | bootstrap 95% CI | p boot | p HAC | corr | turnover change |
|---|---:|---|---:|---:|---:|---:|
| S1 dispersion - baseline | +0.0231 | [-0.0218, +0.0739] | 0.354 | 0.375 | 0.9933 | -0.020 (-0.7%) |
| S2 inverse-vol - baseline | -0.0004 | [-0.0765, +0.0771] | 0.991 | 0.992 | 0.9796 | +0.117 (+4.2%) |
| S2 min-variance - baseline | +0.0705 | [-0.0948, +0.2407] | 0.417 | 0.439 | 0.9041 | +0.609 (+22.0%) |
| S3 symmetric - baseline | +0.0027 | [-0.0590, +0.0652] | 0.932 | 0.943 | 0.9842 | -0.269 (-9.7%) |
| S3 asymmetric - baseline | -0.0019 | [-0.0655, +0.0618] | 0.955 | 0.961 | 0.9837 | -0.336 (-12.1%) |
| S4 partial - raw v6 | +0.0338 | [-0.0703, +0.1348] | 0.517 | 0.565 | 0.9563 | -2.381 (-46.2%) |
| S4 band only - raw v6 | -0.0076 | [-0.0216, +0.0050] | 0.263 | 0.295 | 0.9994 | -0.111 (-2.1%) |
| S4 band added to partial | +0.0062 | [-0.0001, +0.0141] | 0.078 | 0.075 | 0.9999 | -0.056 (-2.0%) |

No row met `statistically_positive`: every bootstrap interval includes zero
and neither inference method has p < 0.05. No row met `current_gate_shape`:
none reached the required +0.10 Sharpe point difference. Therefore the
pre-registered leave-one-decade-out trigger fired for no stage, and the script
printed that fact rather than widening the rule after seeing results.

The tight band-plus-partial comparison is an informative null: its upper
bootstrap endpoint is only +0.014 Sharpe, while it reduces turnover by only
2.0%. The no-trade band does not reproduce the economically material turnover
reduction of partial adjustment.

## Reading against the registered priors

* S1 reduced volatility and risky exposure, but its incremental Sharpe was
  +0.023 with both intervals crossing zero. This study does not establish a
  low-dispersion regime edge.
* S2 inverse-vol again contributes essentially zero and raises turnover. The
  min-variance direction differs from v5's sector result, but its wide
  [-0.095, +0.241] interval and 22% turnover increase do not overturn the
  prior negative conclusion. Its point estimate is not a selection license.
* S3 symmetric and asymmetric volatility targeting contribute +0.003 and
  -0.002 Sharpe. This confirms the prior v3/v9 reading at the stage level:
  exposure scaling is risk control, not distinctive trend edge, and the same
  technique still leaves the vol-targeted balanced benchmark stronger.
* S4 partial adjustment repeats v12 mechanically: 46.2% less turnover, a
  smaller drawdown, and no measurable Sharpe loss. It remains an adopted
  implementation-efficiency decision rather than return edge. Banding alone
  does little; adding it to partial adjustment also contributes no reliable
  edge or material extra turnover reduction.

All five standard sub-periods for every state and baseline are preserved in
stdout. They are descriptive because no stage passed the preregistered trigger
for the stronger leave-one-decade-out analysis.

Deflated Sharpe is 0.9996-0.9999 across the nine states, with SR0 0.0488 and
trial-Sharpe standard deviation 0.0321. These are nine highly correlated,
preregistered states; the DSR is descriptive and does not license selecting
the highest point estimate.

## Falsification boundary and disposition

V14 intentionally did not construct or rank a compound monolith. A failure of
a full pipeline would falsify nothing about any individual stage, and a
passing individual stage would not establish the compound. Only the eight
pre-specified paired ablations speak to their named mechanics. None passes.

Carry remains excluded as a data prerequisite, not set to zero or proxied:
bond carry needs YTM, commodity carry needs a futures curve, and equity carry
needs dividend yields. Any future carry work requires a separate data-layer
decision and dual-source verification.

The market store remains dual-source checked but not clean under the codified
2% rule. Nothing is promoted. Stop after v14.
