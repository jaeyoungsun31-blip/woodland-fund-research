# 2026-09-03 — xsmom-v15-holding: results

Append-only factual execution record for
`2026-09-03-xsmom-v15-holding-preregistration.md`. Study id:
`xsmom-v15-holding`. Nothing was promoted and no point on the frequency curve
was selected.

The complete 449-line stdout record is saved locally at
`reports/xsmom-v15-holding-stdout.txt`. It contains every registered cost,
paired comparison, era result, decade result, tail point estimate, and tail
confidence interval summarized here.

## Execution and identification

The value-weighted daily block of
`10_Portfolios_Prior_12_2_Daily_CSV.zip` aligned exactly with stored MKT and
CASH. The frozen walk-forward produced 94 folds and 24,434 OOS bars from
1932-09-06 through 2026-06-30. The annualized mean real risk-free rate was
3.0761%.

The archive has no constituent identities or weights. Planning therefore
approved the fixed Gaussian stale-cohort approximation before this study was
pre-registered. At each scheduled formation, it selects the latent top 30%,
then propagates that cohort through the ten observed current deciles with
daily rank correlation `229/230`. Both the slower-holding gross return path
and its internal turnover are model-implied. Monthly v15 is not a reproduction
of v13's daily-reconstituted top-three index.

The required future-return perturbation test passed before execution: changing
all decile returns after a cutoff left every modeled return through the cutoff
unchanged. The implementation also passed exact-start, diffusion, formation-
timing, and turnover-order unit tests.

## Turnover curve

| Frequency | formation events | internal model-implied | initial purchase annualized | total charged | reduction vs v13 21.736x |
|---|---:|---:|---:|---:|---:|
| Monthly | 1,125 | 4.5739x | 0.0103x | 4.5842x | 78.91% |
| Quarterly | 375 | 2.5439x | 0.0103x | 2.5542x | 88.25% |
| Semi-annual | 187 | 1.6954x | 0.0103x | 1.7057x | 92.15% |
| Annual | 94 | 1.0793x | 0.0103x | 1.0896x | 94.99% |

The carried v13 caveat is unchanged: **it is an estimate, not observed, and
it omits size dispersion, entry/exit, breakpoint jumps, impact, borrow and
capacity, all of which push true cost up.** V15 additionally assumes that the
return of a stale sub-cohort is exchangeable with the contemporaneous return
of the current French decile into which its latent rank migrated.

## Performance and crossover curve

Sharpe below is annualized at rf=0. The complete stdout also reports Sharpe
against the real risk-free series, volatility, maximum drawdown, worst day,
left-tail fifth percentile, hit rate, and underwater duration at every cost.

| Cost | Monthly CAGR / SR | Quarterly CAGR / SR | Semi-annual CAGR / SR | Annual CAGR / SR | EW10 CAGR / SR | MKT CAGR / SR | 60/40 CAGR / SR |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 14.037% / 0.815 | 13.571% / 0.801 | 13.330% / 0.804 | 12.986% / 0.794 | 11.071% / 0.689 | 10.975% / 0.724 | 8.124% / 0.860 |
| 5 bps | 13.776% / 0.802 | 13.426% / 0.793 | 13.233% / 0.799 | 12.925% / 0.791 | 11.059% / 0.688 | 10.975% / 0.724 | 8.113% / 0.859 |
| 10 bps | 13.515% / 0.789 | 13.281% / 0.786 | 13.137% / 0.794 | 12.863% / 0.788 | 11.047% / 0.687 | 10.974% / 0.724 | 8.101% / 0.858 |
| 25 bps | 12.738% / 0.752 | 12.848% / 0.765 | 12.848% / 0.780 | 12.679% / 0.778 | 11.011% / 0.686 | 10.973% / 0.724 | 8.067% / 0.855 |
| 50 bps | 11.454% / 0.688 | 12.130% / 0.729 | 12.368% / 0.755 | 12.373% / 0.763 | 10.950% / 0.682 | 10.970% / 0.724 | 8.010% / 0.849 |

At 10 bps, Sharpe against the real risk-free series was 0.620 monthly, 0.615
quarterly, 0.618 semi-annually, and 0.609 annually, versus 0.511 for EW10,
0.534 for MKT, and 0.538 for 60/40. The balanced control retained the highest
rf=0 Sharpe at every registered cost because its CASH return is included in
the portfolio return before the rf=0 calculation.

The solved cost crossovers versus unchanged equal-weight-ten were:

| Frequency | gross SR | gross delta SR vs EW10 | crossover | clears 25 bps | clears 50 bps |
|---|---:|---:|---:|:---:|:---:|
| Monthly | 0.8147 | +0.1260 | 52.516 bps | yes | yes |
| Quarterly | 0.8006 | +0.1119 | 85.991 bps | yes | yes |
| Semi-annual | 0.8041 | +0.1155 | 135.550 bps | yes | yes |
| Annual | 0.7941 | +0.1054 | 208.110 bps | yes | yes |

Thus the gross signal remained positive at all four fixed holding frequencies,
and every model-implied crossover exceeded both edges of planning's 25–50 bps
retail range. This is conditional on the stale-cohort model and is not an
observed implementation-cost frontier.

## Paired inference

Stationary bootstrap used 10,000 joint resamples, expected block length 21,
and seed 0. HAC is the Ledoit-Wolf delta-method counterpart. Pair correlations
were high and stable by cost: 0.924 monthly, 0.936 quarterly, 0.940
semi-annually, and 0.956 annually against EW10; correlations against MKT were
0.950, 0.959, 0.958, and 0.967.

### Against equal-weight-ten

| Cost | Frequency | delta SR | bootstrap 95% CI | bootstrap p | HAC p |
|---:|---|---:|---:|---:|---:|
| 0 | Monthly | +0.1260 | [+0.0400, +0.2139] | 0.0048 | 0.0036 |
| 0 | Quarterly | +0.1119 | [+0.0329, +0.1922] | 0.0061 | 0.0048 |
| 0 | Semi-annual | +0.1155 | [+0.0408, +0.1923] | 0.0025 | 0.0028 |
| 0 | Annual | +0.1054 | [+0.0405, +0.1739] | 0.0016 | 0.0016 |
| 5 | Monthly | +0.1140 | [+0.0281, +0.2017] | 0.0100 | 0.0084 |
| 5 | Quarterly | +0.1054 | [+0.0264, +0.1856] | 0.0101 | 0.0079 |
| 5 | Semi-annual | +0.1112 | [+0.0365, +0.1880] | 0.0036 | 0.0039 |
| 5 | Annual | +0.1029 | [+0.0380, +0.1713] | 0.0021 | 0.0020 |
| 10 | Monthly | +0.1020 | [+0.0164, +0.1894] | 0.0204 | 0.0182 |
| 10 | Quarterly | +0.0989 | [+0.0199, +0.1791] | 0.0150 | 0.0126 |
| 10 | Semi-annual | +0.1070 | [+0.0323, +0.1836] | 0.0061 | 0.0056 |
| 10 | Annual | +0.1004 | [+0.0355, +0.1688] | 0.0030 | 0.0026 |
| 25 | Monthly | +0.0660 | [-0.0198, +0.1527] | 0.1347 | 0.1256 |
| 25 | Quarterly | +0.0794 | [+0.0005, +0.1594] | 0.0492 | 0.0449 |
| 25 | Semi-annual | +0.0942 | [+0.0195, +0.1708] | 0.0158 | 0.0146 |
| 25 | Annual | +0.0928 | [+0.0278, +0.1613] | 0.0062 | 0.0054 |
| 50 | Monthly | +0.0060 | [-0.0792, +0.0920] | 0.8925 | 0.8883 |
| 50 | Quarterly | +0.0468 | [-0.0315, +0.1268] | 0.2473 | 0.2356 |
| 50 | Semi-annual | +0.0729 | [-0.0019, +0.1492] | 0.0591 | 0.0584 |
| 50 | Annual | +0.0801 | [+0.0152, +0.1486] | 0.0174 | 0.0162 |

### Against MKT

All four gross comparisons and all four 5 bps comparisons had positive
bootstrap and HAC intervals. At 10 bps the detailed results were:

| Frequency | delta SR | bootstrap 95% CI | bootstrap p | HAC 95% CI | HAC p |
|---|---:|---:|---:|---:|---:|
| Monthly | +0.0653 | [-0.0057, +0.1360] | 0.0704 | [-0.0029, +0.1335] | 0.0606 |
| Quarterly | +0.0622 | [-0.0023, +0.1265] | 0.0587 | [+0.0002, +0.1241] | 0.0493 |
| Semi-annual | +0.0702 | [+0.0085, +0.1343] | 0.0315 | [+0.0079, +0.1325] | 0.0272 |
| Annual | +0.0636 | [+0.0087, +0.1212] | 0.0268 | [+0.0089, +0.1184] | 0.0227 |

At 25 bps every bootstrap interval versus MKT included zero; annual was the
closest at +0.0542 with CI [-0.0010, +0.1118], p=0.0582. At 50 bps all four
intervals included zero and monthly's point estimate was negative. The full
0/5/10/25/50 table, including every HAC interval, is in the saved stdout.

## Era and decade behavior

The full-window finding was not stable under the fixed era split. In
1932–1979, gross bootstrap intervals versus EW10 excluded zero for all four
frequencies. At 10 bps, monthly crossed zero, while quarterly, semi-annual,
and annual remained positive; annual was +0.1153 with CI
[+0.0272, +0.2150]. At 50 bps only annual narrowly excluded zero: +0.0937,
CI [+0.0055, +0.1937], p=0.0499.

In 1980–2026, **every** registered bootstrap interval versus EW10 included
zero, including gross. Gross deltas ranged from +0.0900 to +0.1188; their
lower confidence bounds ranged from -0.0154 to -0.0008. At 10 bps, deltas
ranged from +0.0852 to +0.0990 but lower bounds ranged from -0.0357 to
-0.0064. At 50 bps, deltas ranged from +0.0027 to +0.0667 and all intervals
again crossed zero. Every post-1980 comparison versus MKT also included zero.

At 10 bps, all four modeled holding frequencies had positive CAGR in every
reported decade. The weakest decade was 2000–2009: CAGR 1.82% monthly, 1.46%
quarterly, 1.91% semi-annually, and 1.97% annually, with Sharpes from 0.174
to 0.198. In that decade EW10 returned 1.87% with Sharpe 0.198, while MKT
returned -0.39% with Sharpe 0.094. Complete decade tables for all seven
configurations are in stdout.

## Tail-aware result at 10 bps

| Series | SR | CVaR95 | CVaR99 | Sortino | Omega | tail ratio | adjusted SR | skew | ex. kurtosis | max drawdown | max underwater |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Monthly | 0.789 | 2.759% | 4.810% | 1.105 | 1.161 | 0.973 | 0.785 | -0.491 | 14.861 | -54.77% | 1,871 d |
| Quarterly | 0.786 | 2.718% | 4.749% | 1.101 | 1.161 | 0.971 | 0.782 | -0.487 | 14.958 | -55.41% | 1,850 d |
| Semi-annual | 0.794 | 2.643% | 4.596% | 1.116 | 1.163 | 0.973 | 0.790 | -0.446 | 15.183 | -54.65% | 1,849 d |
| Annual | 0.788 | 2.602% | 4.537% | 1.111 | 1.162 | 0.979 | 0.784 | -0.360 | 15.369 | -53.51% | 1,825 d |
| EW10 | 0.687 | 2.605% | 4.620% | 0.983 | 1.144 | 0.981 | 0.686 | -0.074 | 16.321 | -61.06% | 1,781 d |
| MKT | 0.724 | 2.425% | 4.234% | 1.027 | 1.150 | 0.980 | 0.722 | -0.281 | 16.246 | -54.57% | 1,895 d |
| 60/40 | 0.858 | 1.442% | 2.499% | 1.222 | 1.178 | 0.994 | 0.854 | -0.278 | 14.554 | -35.96% | 1,825 d |

The 10 bps Sharpe bootstrap intervals were [0.577, 1.010] monthly,
[0.573, 1.007] quarterly, [0.581, 1.016] semi-annually, and
[0.573, 1.011] annually. The corresponding CVaR99 intervals were
[4.304%, 5.339%], [4.249%, 5.270%], [4.115%, 5.113%], and
[4.053%, 5.049%]. Every adjusted-Sharpe, skew, kurtosis, tail-ratio, and
drawdown-duration confidence interval for all seven configurations is in the
saved stdout.

Slower refresh modestly improved the modeled left-tail point estimates, but
none matched the balanced control's tail loss or drawdown. Maximum underwater
duration also did not improve materially; its bootstrap interval was very
wide for every series.

## Ledger, deflated Sharpe, and factual outcome

The ledger contains exactly 658 new evaluated rows: seven distinct
return-bearing configurations across 94 validation folds, at the registered
5 bps ledger cost. All four modeled stale-cohort configurations had DSR 1.000
and PSR versus zero 1.000 using literal breadth seven. The selection hurdle
was SR0 0.08; the seven-config Sharpe range was 0.688 to 0.859.

Literal breadth materially overstates independent effective breadth because
the four holding frequencies are highly dependent and the three controls
share the same market history. DSR does not select a point from the curve.

Factual outcome: under the fixed Gaussian stale-cohort approximation, trading
less reduced estimated turnover by 79%–95% versus v13, retained a positive
gross momentum edge at every registered frequency, and moved every point
crossover above 50 bps. The aggregate paired evidence versus EW10 remained
positive at 10 bps for all four frequencies and at 50 bps only for annual.
However, no post-1980 paired comparison excluded zero, the 60/40 control kept
the highest rf=0 Sharpe and materially better tail loss, and neither gross
returns nor internal turnover is observed. The result supports obtaining
constituent-level data to validate slower refresh; it does not establish
tradeability, select a frequency, or promote a strategy. Nothing was promoted.
