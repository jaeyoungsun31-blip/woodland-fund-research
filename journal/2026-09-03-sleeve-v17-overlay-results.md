# 2026-09-03 — sleeve-v17-overlay: results

Append-only factual execution record for
`2026-09-03-sleeve-v17-overlay-preregistration.md`. Study id:
`sleeve-v17-overlay`. Nothing was promoted.

The complete 525-line stdout record is saved locally at
`reports/sleeve-v17-overlay-stdout.txt`. It contains all five registered cost
levels, all fixed weights, secondary selections, full-window and era paired
inference, decade results, tail point estimates and block-bootstrap intervals,
and the diversification diagnostics summarized here.

## Execution and identification

The value-weighted daily block of
`10_Portfolios_Prior_12_2_Daily_CSV.zip` aligned exactly with stored MKT and
CASH. The frozen 252-day-embargo walk-forward produced 94 folds and 24,434 OOS
bars from 1932-09-06 through 2026-06-30. The annualized mean real risk-free
rate was 3.0761%.

Before execution, the underspecified secondary selection operation was fixed
in `2026-09-03-sleeve-v17-overlay-execution-note.md`: maximize annualized rf=0
training Sharpe at the 5 bps ledger cost, break an exact tie toward the smaller
weight, and apply a changed weight only at the next monthly formation. This
does not affect primary A, whose sleeve weight remained fixed at 10%.

The v15 reproduction check matched the journaled monthly series: 1,125 usable
formations, internal modeled turnover 4.573857x, initial purchase 0.010313x,
total modeled turnover 4.584170x, gross Sharpe 0.814699, and 10 bps Sharpe
0.789455.

The maintained overlay starts at `(1-s)/s`, lets its two components drift,
and restores the registered mix at monthly formation closes. Component costs
are charged inside the baseline and sleeve streams; the incremental re-mix
trade is charged once at the overlay layer. Known-answer tests established
that `s=0` and `s=1` exactly reproduce their component, a two-bar path matches
hand arithmetic, and turnover and cost occur only on registered re-mix dates.
The full suite passed with 357 tests before and after both implementation
commits.

## Primary A — fixed 10% sleeve

At the registered 10 bps decision cost, fixed `s=0.10` produced 8.671% CAGR,
10.389% annualized volatility and Sharpe 0.852530 at rf=0. The 60/40 incumbent
produced 8.101% CAGR, 9.621% volatility and Sharpe 0.857929. Thus the overlay's
higher CAGR came with higher risk and did not improve risk-adjusted return.
Sharpe against the real risk-free series was 0.556338 for the overlay and
0.538109 for 60/40. Estimated total annual turnover was 0.693501x versus
0.211763x.

Primary performance at every registered cost was:

| Cost | Overlay CAGR | Overlay SR | 60/40 CAGR | 60/40 SR | Delta SR |
|---:|---:|---:|---:|---:|---:|
| 0 bps | 8.746% | 0.859198 | 8.124% | 0.860126 | -0.000928 |
| 5 bps | 8.709% | 0.855864 | 8.113% | 0.859028 | -0.003164 |
| 10 bps | 8.671% | 0.852530 | 8.101% | 0.857929 | -0.005399 |
| 25 bps | 8.558% | 0.842535 | 8.067% | 0.854632 | -0.012098 |
| 50 bps | 8.370% | 0.825891 | 8.010% | 0.849129 | -0.023238 |

Stationary bootstrap used 10,000 joint resamples, expected block length 21 and
seed 0. HAC is the Ledoit-Wolf delta-method counterpart.

| Cost | Delta SR | Bootstrap 95% CI | Bootstrap p | HAC 95% CI | HAC p | Pair corr. |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | -0.000928 | [-0.013256, +0.011273] | 0.8861 | [-0.012646, +0.010791] | 0.8767 | 0.998523 |
| 5 | -0.003164 | [-0.015512, +0.009048] | 0.6139 | [-0.014877, +0.008549] | 0.5965 | 0.998523 |
| 10 | -0.005399 | [-0.017774, +0.006794] | 0.3889 | [-0.017108, +0.006309] | 0.3661 | 0.998523 |
| 25 | -0.012098 | [-0.024556, -0.000003] | 0.0537 | [-0.023796, -0.000400] | 0.0427 | 0.998523 |
| 50 | -0.023238 | [-0.035872, -0.011197] | 0.0003 | [-0.034935, -0.011542] | 0.0001 | 0.998523 |

The 10 bps paired estimate was negative and its interval included zero. Costs
made the delta progressively more negative; at 50 bps both inference routes
excluded zero on the negative side.

## Fixed-weight response

The registered 10 bps curve was monotone: every larger sleeve weight reduced
Sharpe further relative to 60/40. No weight was selected from this curve.

| Sleeve weight | Overlay SR | Delta SR | Bootstrap 95% CI | Bootstrap p | HAC p |
|---:|---:|---:|---:|---:|---:|
| 5% | 0.855449 | -0.002481 | [-0.008866, +0.003853] | 0.4439 | 0.4234 |
| 10% | 0.852530 | -0.005399 | [-0.017774, +0.006794] | 0.3889 | 0.3661 |
| 20% | 0.845815 | -0.012114 | [-0.035223, +0.010544] | 0.2960 | 0.2763 |
| 30% | 0.838452 | -0.019478 | [-0.051825, +0.012094] | 0.2278 | 0.2118 |

Gross results had the same direction: delta Sharpe was -0.000145 at 5%,
-0.000928 at 10%, -0.003901 at 20% and -0.008129 at 30%. Therefore the
negative response was not created solely by the 10 bps cost assumption.

## Primary pass criteria

**C1 — it improves risk-adjusted return: NOT MET.** At 10 bps, fixed 10%
Sharpe was 0.852530 versus 0.857929 for 60/40. Delta was -0.005399 with paired
bootstrap 95% CI [-0.017774, +0.006794], p=0.3889. The interval did not exclude
zero and the point estimate was negative.

**C2 — it does not pay for that with the tail: MET under the registered
tolerances.** Maximum drawdown was -37.5292% for the overlay versus -35.9609%
for 60/40, a magnitude ratio of 1.0436 and below the 1.25 ceiling. CVaR95 was
1.5605% versus 1.4417%, a ratio of 1.0824 and below the 1.10 ceiling. CVaR99
was 2.7028% versus 2.4994%, a ratio of 1.0814 and below the 1.10 ceiling.
Every point estimate was nevertheless worse than the incumbent; C2 means only
that the deterioration stayed inside the preregistered allowance.

**C3 — it survives post-1980: NOT MET.** At 10 bps in 1980-2026, fixed 10%
Sharpe was 0.888608 versus 0.901092. Delta was -0.012484 with bootstrap 95% CI
[-0.029674, +0.003650], p=0.1438; HAC CI was
[-0.028755, +0.003786], p=0.1326.

Primary A did not meet all three criteria. The study failed.

## Era and decade behavior

In 1932-1979 at 10 bps, primary delta Sharpe was +0.001708 with bootstrap CI
[-0.015217, +0.019208], p=0.8437. In 1980-2026 it was the negative result
reported under C3. Neither era supported a positive primary effect.

The primary overlay had positive CAGR in every reported decade. Relative to
60/40, its decade Sharpe was higher in the 1940s, 1960s and 2000s and lower in
the other seven reported periods. The largest drawdown for both occurred in
2000-2009: -37.5292% for the overlay and -35.9609% for 60/40. Complete decade
tables for every fixed weight, B, the standalone sleeve, equal-weight-ten and
MKT are in the saved stdout.

## Tail-aware result

At 10 bps, fixed 10% had CVaR95 1.5605%, CVaR99 2.7028%, Sortino 1.209695,
adjusted Sharpe 0.848568, skew -0.3244, excess kurtosis 14.5091 and maximum
underwater duration 1,848 trading days. The corresponding 60/40 values were
1.4417%, 2.4994%, 1.221824, 0.854261, -0.2781, 14.5544 and 1,825 days.

The 95% block-bootstrap intervals were [1.4520%, 1.6754%] for primary CVaR95,
[2.4179%, 3.0070%] for primary CVaR99, and [0.629927, 1.073905] for primary
adjusted Sharpe. For 60/40 they were [1.3395%, 1.5507%],
[2.2308%, 2.7788%], and [0.633404, 1.081254], respectively. The complete tail
block includes Sharpe, Sortino, Omega, tail ratio, skew, excess kurtosis and
the distribution of drawdown durations for the incumbent, all four fixed
weights and B.

## Diversification diagnostic

At 10 bps, the standalone sleeve/base correlation was 0.949189. The two-stream
mix had the following diagnostics:

| Sleeve weight | Diversification ratio | Effective bets | PCA cross-check |
|---:|---:|---:|---:|
| 5% | 1.004203 | 1.008423 | 1.216542 |
| 10% | 1.007362 | 1.014778 | 1.176687 |
| 20% | 1.011254 | 1.022635 | 1.112813 |
| 30% | 1.012803 | 1.025769 | 1.066487 |

The mechanism diagnostic showed a small diversification benefit, including
1.014778 effective bets at the primary weight. It was too small to overcome
the sleeve's lower risk-adjusted return and added cost: Sharpe fell
monotonically while volatility, drawdown and both CVaRs rose. The overlay did
not fail because diversification was literally absent; it failed because the
diversification was economically insufficient.

## Secondary B — selected weight

Training selection chose 5% in 59 folds, 10% in one, 20% in two, and 30% in
32. At 10 bps, B produced 8.968% CAGR, 10.981% volatility, Sharpe 0.837282,
and estimated annual turnover 0.996472x. Against 60/40, delta Sharpe was
-0.020647 with bootstrap CI [-0.052027, +0.011719], p=0.2051; HAC CI was
[-0.051494, +0.010199], p=0.1895. B therefore failed C1 as well as A.

B had Sharpe below 60/40 at all costs. Its deltas were -0.013780, -0.017214,
-0.020647, -0.030944 and -0.048095 at 0, 5, 10, 25 and 50 bps. Its maximum
drawdown at 10 bps was -40.7318%, CVaR95 was 1.6544%, CVaR99 was 2.9373%, and
maximum underwater duration was 2,188 days.

## Ledger, deflation and factual outcome

The shared ledger was written once at the end of calculation and contains
exactly 376 new evaluated rows: four registered fixed weights across 94
validation folds, at the 5 bps ledger cost. It contains four distinct v17
configurations, each with 94 rows and split indexes 0 through 93.

For primary A, literal breadth is one, SR0 is 0.00 and DSR is 1.000; this is
vacuous because A was not selected. For B, literal breadth is four, SR0 is
0.01 and DSR is 1.000. The four weights are extremely dependent, so literal
breadth overstates effective breadth. DSR concerns whether a series' own
Sharpe exceeds its selection hurdle; it does not overturn B's failure to beat
the incumbent.

Factual outcome: a fixed 10% model-implied monthly momentum sleeve raised
CAGR by adding volatility, did not improve Sharpe at any registered cost,
slightly worsened drawdown and tail loss, and failed both the full-window and
post-1980 paired criteria. The response was clean but adverse: higher fixed
sleeve weights monotonically reduced Sharpe relative to 60/40. Training
selection did not rescue the result. The project's repeated conclusion that
momentum does not beat the balanced incumbent now extends to the newly tested
bounded-overlay framing.

The standing limitation remains binding: **the sleeve's gross path and its
internal turnover are model-implied, not observed**, and the construction
assumes a stale sub-cohort's return is exchangeable with the contemporaneous
return of the decile into which its latent rank migrated. This limitation
cannot explain the result into a pass; it only limits how literally either a
positive or negative modeled implementation result may be read.

Nothing was promoted.
