# 2026-09-02 — xsmom-v13-confirm: results

Append-only factual execution record for the pre-registration in
`2026-09-02-xsmom-v13-confirm-preregistration.md`. Study id:
`xsmom-v13-confirm`. Nothing was promoted.

The complete 636-line stdout record is saved locally at
`reports/xsmom-v13-confirm-stdout.txt`. It contains the full 15-series tables,
all cost levels, all decade sub-periods, every tail-metric confidence interval,
and the exact inference output summarized here.

## Execution and data checks

The value-weighted daily block of
`10_Portfolios_Prior_12_2_Daily_CSV.zip` aligned exactly with the stored MKT
and CASH calendar. The frozen walk-forward produced 94 folds and 24,434 OOS
bars from 1932-09-06 through 2026-06-30. The annualized mean real risk-free
rate on this window was 3.0761%.

Before the v13 analysis, the runner reproduced the v11 anchors: top-three
minus equal-weight-ten Sharpe was +0.1322 under v11's decile-level 5 bps
cost treatment; gross Hi-minus-Lo Sharpe was 0.5121, maximum drawdown was
-85.16%, and the longest underwater spell was 6,404 trading days.

## Part A — cost reality

Exact constituent turnover remains unidentified. The French archive contains
portfolio returns but not stock identifiers, weights, or migration records.
These are the pre-registered Gaussian rank-transition model estimates, not
observed turnover.

| Series | observed outer turnover | model-implied internal turnover | total cost-engine turnover |
|---|---:|---:|---:|
| individual low/high decile | 0.010x | 32.898x | 32.908x |
| individual inner deciles (range) | 0.010x | 85.395x–146.916x | 85.405x–146.926x |
| top-three | 0.150x | 21.736x | 21.886x |
| equal-weight-ten | 0.218x | 0.000x | 0.218x |
| MKT | 0.010x | 0.000x | 0.010x |
| 60% MKT / 40% CASH | 0.212x | 0.000x | 0.212x |
| Hi-minus-Lo | 0.000x | 65.795x | 65.795x |

Equal-weight-ten's zero internal turnover is a favorable lower bound in the
fixed model: migration among the ten decile sleeves cancels. The model assumes
exchangeable value mass within rank bins and omits unequal stock sizes,
corporate entry/exit, breakpoint jumps, impact, tax, borrow, and capacity.

### Main performance curve

All returns below include observed outer turnover plus the model-implied
internal turnover charge. Sharpe is at rf=0; the full stdout also reports
Sharpe against the real risk-free series, maximum drawdown, worst day, left
tail, hit rate, and duration.

| Cost (bps) | top-three CAGR | top-three SR | EW10 CAGR | EW10 SR | MKT CAGR | MKT SR | 60/40 CAGR | 60/40 SR | Hi-Lo CAGR | Hi-Lo SR |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 14.280% | 0.821 | 11.071% | 0.689 | 10.975% | 0.724 | 8.124% | 0.860 | 9.406% | 0.512 |
| 5 | 13.037% | 0.761 | 11.059% | 0.688 | 10.975% | 0.724 | 8.113% | 0.859 | 5.866% | 0.367 |
| 10 | 11.807% | 0.701 | 11.047% | 0.687 | 10.974% | 0.724 | 8.101% | 0.858 | 2.440% | 0.221 |
| 25 | 8.197% | 0.522 | 11.011% | 0.686 | 10.973% | 0.724 | 8.067% | 0.855 | -7.189% | -0.215 |
| 50 | 2.437% | 0.223 | 10.950% | 0.682 | 10.970% | 0.724 | 8.010% | 0.849 | -21.275% | -0.943 |

The top-three Sharpe first ceased to beat equal-weight-ten at **11.168 bps**
under the fixed model. That crossover is an estimate conditional on the model,
not an observed implementation threshold.

The gross high-minus-low decile CAGR spread reconstructed as 13.840 points.
The net spread was 13.615 points at 5 bps (98.7% of the v11 reference), 13.394
at 10 bps (97.1%), 12.752 at 25 bps (92.4%), and 11.749 at 50 bps (85.1%).
The percentage retained does not mean both legs remained investable: at 50
bps the high decile CAGR was -1.004% and the low decile CAGR was -12.753%.

### Paired inference

Stationary bootstrap: 10,000 paired resamples, expected block 21, seed 0.
HAC is the Ledoit-Wolf delta-method counterpart with its reported automatic
Bartlett bandwidth. Correlations remained 0.916 against EW10 and 0.943 against
MKT.

| Cost | comparison | delta SR | bootstrap 95% CI | bootstrap p | HAC 95% CI | HAC p |
|---:|---|---:|---:|---:|---:|---:|
| 0 | top-three − EW10 | +0.1320 | [+0.0414, +0.2252] | 0.0047 | [+0.0427, +0.2212] | 0.0037 |
| 0 | top-three − MKT | +0.0964 | [+0.0211, +0.1717] | 0.0118 | [+0.0239, +0.1690] | 0.0092 |
| 5 | top-three − EW10 | +0.0729 | [-0.0177, +0.1651] | 0.1158 | [-0.0161, +0.1618] | 0.1082 |
| 5 | top-three − MKT | +0.0367 | [-0.0386, +0.1116] | 0.3381 | [-0.0356, +0.1091] | 0.3195 |
| 10 | top-three − EW10 | +0.0138 | [-0.0764, +0.1050] | 0.7643 | [-0.0749, +0.1025] | 0.7606 |
| 10 | top-three − MKT | -0.0229 | [-0.0983, +0.0519] | 0.5486 | [-0.0952, +0.0493] | 0.5335 |
| 25 | top-three − EW10 | -0.1635 | [-0.2542, -0.0739] | 0.0004 | [-0.2519, -0.0751] | 0.0003 |
| 25 | top-three − MKT | -0.2020 | [-0.2789, -0.1275] | 0.0001 | [-0.2744, -0.1296] | <0.0001 |
| 50 | top-three − EW10 | -0.4590 | [-0.5525, -0.3666] | 0.0001 | [-0.5481, -0.3698] | <0.0001 |
| 50 | top-three − MKT | -0.5004 | [-0.5824, -0.4208] | 0.0001 | [-0.5746, -0.4263] | <0.0001 |

The confirmatory top-three edge was distinguishable only before the internal
cost charge. At 5 bps both paired intervals crossed zero. At 10 bps the point
edge over EW10 was +0.014 Sharpe and the point difference from MKT was -0.023.
At 25 and 50 bps top-three reliably trailed both controls.

The era split did not rescue the result. Gross top-three minus EW10 was
+0.1405 in 1932-1979 (bootstrap CI [+0.0242, +0.2633], p=0.0214) and +0.1221
in 1980-2026 (CI [-0.0149, +0.2582], p=0.0790). At 5 bps the corresponding
CIs were [-0.0359, +0.2007] and [-0.0724, +0.1997]; at 10 bps they were
[-0.0969, +0.1380] and [-0.1303, +0.1423]. The stdout contains the MKT era
comparisons and 25/50 bps stresses as pre-registered.

### Decade behavior at 10 bps

| Period | top-three CAGR | SR | max drawdown | max underwater days |
|---|---:|---:|---:|---:|
| 1932-1940 | 7.41% | 0.391 | -55.83% | 844 |
| 1940s | 9.36% | 0.607 | -35.17% | 1,008 |
| 1950s | 19.25% | 1.478 | -23.29% | 296 |
| 1960s | 12.67% | 1.015 | -29.52% | 428 |
| 1970s | 8.87% | 0.667 | -45.22% | 1,120 |
| 1980s | 16.56% | 0.987 | -36.59% | 491 |
| 1990s | 19.04% | 1.221 | -21.45% | 287 |
| 2000s | 0.52% | 0.131 | -51.84% | 1,339 |
| 2010s | 12.26% | 0.740 | -24.16% | 350 |
| 2020-2026 | 13.66% | 0.658 | -34.17% | 582 |

## Part B — portfolio-level Fama-MacBeth result

The standardised decile-rank proxy had a positive average forward-return
slope in the full sample and both fixed eras.

| Period | mean slope/day | annualized slope | NW SE/day | t | two-sided p | fraction positive | periods |
|---|---:|---:|---:|---:|---:|---:|---:|
| full OOS | 0.000112 | 0.028273 | 0.000030 | 3.734 | 0.000188 | 0.5484 | 24,434 |
| 1932-1979 | 0.000117 | 0.029538 | 0.000037 | 3.160 | 0.001575 | 0.5516 | 12,716 |
| 1980-2026 | 0.000107 | 0.026900 | 0.000048 | 2.224 | 0.026182 | 0.5449 | 11,718 |

This confirms prediction at the **portfolio-rank-proxy** level. It is not a
stock-level Fama-MacBeth regression because the archive does not expose the
underlying stock characteristics or constituents.

## Part C — tail-aware result

At the primary 10 bps stress, the main point estimates were:

| Series | SR | CVaR95 | CVaR99 | Sortino | Omega | tail ratio | adjusted SR | skew | ex. kurtosis | max drawdown | max underwater |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| top-three | 0.701 | 2.795% | 4.859% | 0.977 | 1.142 | 0.960 | 0.698 | -0.507 | 14.474 | -58.95% | 2,348 d |
| EW10 | 0.687 | 2.605% | 4.620% | 0.983 | 1.144 | 0.981 | 0.686 | -0.074 | 16.321 | -61.06% | 1,781 d |
| MKT | 0.724 | 2.425% | 4.234% | 1.027 | 1.150 | 0.980 | 0.722 | -0.281 | 16.246 | -54.57% | 1,895 d |
| 60/40 MKT/CASH | 0.858 | 1.442% | 2.499% | 1.222 | 1.178 | 0.994 | 0.854 | -0.278 | 14.554 | -35.96% | 1,825 d |
| Hi-minus-Lo | 0.221 | 3.606% | 6.696% | 0.297 | 1.046 | 0.950 | 0.221 | -1.147 | 20.488 | -92.50% | 10,254 d |

The 10 bps top-three block-bootstrap intervals included: Sharpe
[0.491, 0.918], CVaR95 [2.611%, 2.987%], CVaR99 [4.344%, 5.387%], Sortino
[0.675, 1.301], Omega [1.098, 1.188], tail ratio [0.926, 1.000], adjusted
Sharpe [0.490, 0.913], skew [-0.996, -0.010], and excess kurtosis
[8.463, 21.008]. Its drawdown-duration distribution had 856 spells, mean
26.0 days, median 3, p90 34, and maximum 2,348; the stdout records the wide
bootstrap intervals for every duration statistic.

The Hi-minus-Lo worked example shows why Sharpe was insufficient. At 10 bps,
Sharpe fell from v11's gross 0.512 to 0.221 (95% CI [0.003, 0.458]), while
CVaR99 was 6.696% [5.879%, 7.560%], skew was -1.147 [-1.737, -0.582], excess
kurtosis was 20.488 [12.713, 29.426], maximum drawdown worsened to -92.50%,
and maximum underwater time lengthened from 6,404 to 10,254 trading days.
The adjusted Sharpe remained close to ordinary Sharpe because the
Pezier-White correction is applied to the small daily Sharpe; the direct tail
losses and drawdown durations carried the economically material warning.

## Ledger, deflated Sharpe, and conclusion

The ledger contains exactly 1,504 new rows: 16 distinct configurations across
94 folds (15 return-bearing configurations plus one fixed Fama-MacBeth
specification), split indices 0 through 93. Portfolio rows use the registered
5 bps model-implied cost. The return-config Sharpe range was 0.176 to 0.859.
For top-three at 5 bps, literal-trial DSR used 15 return configurations:
Sharpe 0.761, SR0 0.41, DSR 1.000, and PSR versus zero 1.000. The literal
breadth overstates independent breadth because the deciles are nested and all
series share market exposure; the Fama-MacBeth configuration was excluded.

Factual outcome: the ordered cross-sectional momentum characteristic predicts
future decile-portfolio returns in this academic series, including post-1980.
The separate portfolio-allocation claim did **not** survive realistic-cost
uncertainty under the registered model: the top-three edge was no longer
statistically distinguishable at 5 bps, was economically near zero at 10 bps,
and reversed beyond the 11.168 bps crossover. The long-short factor's tail and
drawdown profile deteriorated further after cost. Because turnover is modeled
rather than observed, this is a cost-sensitivity finding, not proof of exact
tradeability or non-tradeability. Nothing was promoted.
