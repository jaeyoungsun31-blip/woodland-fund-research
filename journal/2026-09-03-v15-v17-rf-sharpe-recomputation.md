# 2026-09-03 — v15/v17 risk-free Sharpe convention recomputation

Append-only factual correction requested by HANDOFF 2026-09-03d. This is a
metric recomputation, not a new study. No configuration, weight, cost level,
data source, selection rule, or trials-ledger row was added. The original v15
and v17 entries remain unchanged.

The complete 221-line stdout record is saved locally at
`reports/rf-sharpe-convention-recomputation-stdout.txt`. It contains 195
registered comparison/window rows, with rf=0 and aligned-real-risk-free
inference printed side by side for every row.

## Correction and execution

The paired block-bootstrap and HAC paths now accept an aligned daily
risk-free series. When supplied, the same daily rate is subtracted from both
members of each pair before either Sharpe is computed. A synthetic regression
test uses a 60%-risky/40%-cash portfolio and a fully invested portfolio to
assert that rf=0 and excess-return inference produce different answers. This
prevents the cash-allocation convention from being ignored silently again.

The recomputation used the existing 1932-09-06 through 2026-06-30 OOS window,
24,434 bars, existing real risk-free series, four v15 holding frequencies,
four fixed v17 weights, frozen v17 B path, and five registered cost levels.
The mean annualized real risk-free rate was 3.076104%. The bootstrap remained
10,000 paired stationary resamples, expected block length 21, seed 0. HAC
remained the Ledoit-Wolf delta-method counterpart with the existing automatic
bandwidth.

V17 B was not reselected under the corrected convention. It remained the
registered best-in-training path selected on rf=0 at 5 bps. Its selection
counts reproduced exactly: 5% in 59 folds, 10% in one, 20% in two, and 30% in
32. The rf=0 reproduction anchors also matched the journals to six decimals:
v17 primary full-window delta -0.005399, v17 primary post-1980 delta
-0.012484, and v15 monthly-versus-MKT delta +0.065305 at 10 bps.

## V17 primary A — full window at every cost

Both conventions are shown on every row. Confidence intervals and p-values
below are from the paired stationary bootstrap.

| Cost | rf=0 delta | rf=0 95% CI | rf=0 p | Excess delta | Excess 95% CI | Excess p |
|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | -0.000928 | [-0.013256, +0.011273] | 0.8861 | +0.022704 | [+0.011059, +0.034961] | 0.0006 |
| 5 bps | -0.003164 | [-0.015512, +0.009048] | 0.6139 | +0.020466 | [+0.008803, +0.032663] | 0.0010 |
| 10 bps | -0.005399 | [-0.017774, +0.006794] | 0.3889 | +0.018229 | [+0.006552, +0.030398] | 0.0026 |
| 25 bps | -0.012098 | [-0.024556, -0.000003] | 0.0537 | +0.011526 | [-0.000142, +0.023582] | 0.0575 |
| 50 bps | -0.023238 | [-0.035872, -0.011197] | 0.0003 | +0.000377 | [-0.011346, +0.012280] | 0.9544 |

At the registered 10 bps decision cost, the rf=0 levels reproduce the prior
entry: Sharpe 0.852530 for fixed 10% versus 0.857929 for 60/40. Against the
aligned real risk-free series, they are 0.556338 versus 0.538109. The
excess-return paired delta is +0.018229, bootstrap CI
[+0.006552, +0.030398], p=0.0026; HAC CI is
[+0.006563, +0.029897], p=0.0022. Pair correlation is 0.998523 at rf=0 and
0.998524 on excess returns.

Therefore **C1 changes from NOT MET under rf=0 to MET under excess-return
inference**. This was a false negative caused by the convention defect.

## V17 fixed curve, B, and eras

At 10 bps, all four fixed weights have positive full-window excess-return
bootstrap intervals. B does not. No weight is selected from the curve.

| Window | Challenger | rf=0 delta / 95% CI | Excess delta / 95% CI | Excess p |
|---|---|---|---|---:|
| Full | fixed 5% | -0.002481 / [-0.008866, +0.003853] | +0.009666 / [+0.003637, +0.015961] | 0.0024 |
| Full | fixed 10% | -0.005399 / [-0.017774, +0.006794] | +0.018229 / [+0.006552, +0.030398] | 0.0026 |
| Full | fixed 20% | -0.012114 / [-0.035223, +0.010544] | +0.032592 / [+0.010845, +0.055206] | 0.0040 |
| Full | fixed 30% | -0.019478 / [-0.051825, +0.012094] | +0.044004 / [+0.013357, +0.075646] | 0.0059 |
| Full | B selected | -0.020647 / [-0.052027, +0.011719] | +0.018931 / [-0.010829, +0.049859] | 0.2187 |
| 1932–1979 | fixed 10% | +0.001708 / [-0.015217, +0.019208] | +0.023024 / [+0.006028, +0.041022] | 0.0090 |
| 1980–2026 | fixed 10% | -0.012484 / [-0.029674, +0.003650] | +0.012861 / [-0.003471, +0.029022] | 0.1200 |

For primary A in 1932–1979, the excess-return HAC CI is
[+0.005979, +0.040071], p=0.0081. Post-1980 it is
[-0.003365, +0.029088], p=0.1203. Thus **C3 remains NOT MET** under the
corrected convention: the point estimate becomes positive, but both
registered inference routes remain ambiguous. B's full-window corrected CI
also crosses zero.

Across the full fixed-weight curve, excess-return bootstrap lower bounds were
positive for all four weights at 0, 5, and 10 bps, for only the 5% weight at
25 bps, and for none at 50 bps. In 1932–1979 all four were positive at 0, 5,
and 10 bps and none at 25 or 50. In 1980–2026 three of four were positive only
at 0 bps; none was positive at 5, 10, 25, or 50 bps. The full stdout records
every point, interval, p-value, HAC counterpart, and correlation.

C2 is convention-independent and remains MET under its registered
tolerances. Because corrected C1 is met but corrected C3 is not, primary A
still does not meet all three pre-registered criteria. Nothing is promoted.

## V15 — full-window 10 bps comparisons

Under rf=0, no holding frequency beat 60/40 at 10 bps; the point deltas were
negative. Under excess-return inference, every registered frequency has a
positive paired bootstrap and HAC interval versus both 60/40 and MKT.

| Frequency | Reference | rf=0 delta / 95% CI | Excess delta / 95% CI | Excess p |
|---|---|---|---|---:|
| Monthly | 60/40 | -0.068475 / [-0.141512, +0.002111] | +0.081872 / [+0.011604, +0.152856] | 0.0234 |
| Quarterly | 60/40 | -0.071607 / [-0.138049, -0.006394] | +0.076394 / [+0.013053, +0.141326] | 0.0198 |
| Semi-annual | 60/40 | -0.063565 / [-0.128405, +0.002661] | +0.080077 / [+0.020063, +0.143323] | 0.0123 |
| Annual | 60/40 | -0.070161 / [-0.128072, -0.010654] | +0.071349 / [+0.017306, +0.127729] | 0.0112 |
| Monthly | MKT | +0.065305 / [-0.005683, +0.135985] | +0.085824 / [+0.015666, +0.155829] | 0.0162 |
| Quarterly | MKT | +0.062172 / [-0.002289, +0.126505] | +0.080345 / [+0.016825, +0.144364] | 0.0132 |
| Semi-annual | MKT | +0.070215 / [+0.008527, +0.134317] | +0.084028 / [+0.024212, +0.146618] | 0.0080 |
| Annual | MKT | +0.063618 / [+0.008726, +0.121166] | +0.075301 / [+0.021698, +0.131217] | 0.0078 |

The corresponding excess-return HAC intervals were positive for all eight
rows. At 10 bps, excess-return correlations ranged from 0.949223 to 0.966670
against 60/40 and from 0.950001 to 0.966928 against MKT.

The all-cost full-window count of frequencies with a positive excess-return
bootstrap lower bound was:

| Cost | vs 60/40 (of 4) | vs MKT (of 4) |
|---:|---:|---:|
| 0 bps | 4 | 4 |
| 5 bps | 4 | 4 |
| 10 bps | 4 | 4 |
| 25 bps | 2 | 2 |
| 50 bps | 1 | 0 |

At 25 bps, semi-annual and annual remained positive versus both references.
At 50 bps, only annual versus 60/40 narrowly retained a positive bootstrap
lower bound; no frequency did so versus MKT. All cost rows and HAC
counterparts are in the saved stdout.

## V15 era result

The full-window correction is not era-stable. In 1932–1979 at 10 bps, all
four frequencies had positive excess-return bootstrap intervals versus both
60/40 and MKT. The excess deltas versus 60/40 ranged from +0.095701 to
+0.102354; versus MKT they ranged from +0.103755 to +0.110408.

In 1980–2026 at 10 bps, no frequency excluded zero against either reference.
Excess deltas versus 60/40 ranged from +0.038989 to +0.056770, with lower
bounds from -0.043322 to -0.025615. Excess deltas versus MKT ranged from
+0.038619 to +0.056401, with lower bounds from -0.043764 to -0.025851.

This post-1980 ambiguity held at every registered cost: zero of four
frequencies had a positive excess-return bootstrap lower bound versus either
60/40 or MKT at 0, 5, 10, 25, or 50 bps. In 1932–1979, all four cleared both
references at 0, 5, and 10 bps; two cleared both at 25 bps; and one cleared
both at 50 bps. The aggregate inference is therefore supported by the early
half of the sample and does not establish a post-1980 effect.

## What this correction does and does not change

The rf=0 convention materially understated the risk-adjusted contribution of
fully invested momentum relative to a cash-heavy incumbent. Correcting it
changes v17 C1 to met and changes v15's full-history comparison with 60/40
from negative to positive at 10 bps. It does not establish post-1980
robustness: v17 C3 and every v15 post-1980 comparison remain ambiguous.

Three other findings are unchanged:

* 60/40's tail advantage in CVaR95, CVaR99, maximum drawdown, and underwater
  duration does not depend on the Sharpe convention.
* The identification gap remains: every v15 holding path, v17 sleeve path,
  and associated turnover estimate is model-implied rather than observed.
* The `K ~ 232` turnover budget remains because it derives from crossover
  costs and turnover, neither of which uses the Sharpe risk-free convention.

The correction reopens interpretation but does not authorize a new study or
a promotion. Planning must decide what the corrected evidence means for the
suspended termination decision. Nothing was promoted.
