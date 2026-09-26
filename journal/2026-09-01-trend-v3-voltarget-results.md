# 2026-09-01 — trend-v3-voltarget results

Harness output for the preregistered study
`2026-09-01-trend-v3-voltarget-preregistration.md`. Nothing is promoted.
The source-verification caveat remains in force.

## Study accounting

* OOS window: 2004-10-22 through 2026-09-01, 5,499 daily observations.
* Walk-forward folds: 22.
* Trials ledger: 1 distinct fixed configuration, 22 fold evaluations.
* Fixed overlay: 63-day realized vol, 10% annual target, scale capped at 1.
* No parameter selection and no crash-pattern conditioning.

## Stitched OOS result and identical-window baselines

| Portfolio | CAGR | Ann. vol | Sharpe rf=0 | Max DD | DD duration | Monthly hit rate |
|---|---:|---:|---:|---:|---:|---:|
| v3 voltarget @0bps | 7.60% | 10.87% | 0.728 | -22.31% | 619 | 66.16% |
| v3 voltarget @5bps | 7.37% | 10.87% | 0.709 | -22.64% | 623 | 66.16% |
| v3 voltarget @10bps | 7.14% | 10.87% | 0.689 | -22.96% | 665 | 65.78% |
| SPY buy-and-hold | 11.24% | 18.84% | 0.660 | -55.19% | 1,223 | 66.67% |
| 60/40 @0bps | 8.34% | 10.62% | 0.807 | -32.32% | 709 | 67.05% |
| 60/40 @5bps | 8.33% | 10.62% | 0.806 | -32.34% | 709 | 67.05% |
| 60/40 @10bps | 8.31% | 10.62% | 0.805 | -32.35% | 709 | 67.05% |
| vol-target 60/40 @0bps | 7.48% | 8.89% | 0.856 | -20.86% | 585 | 67.42% |
| vol-target 60/40 @5bps | 7.46% | 8.89% | 0.853 | -20.91% | 585 | 67.42% |
| vol-target 60/40 @10bps | 7.43% | 8.89% | 0.850 | -20.96% | 586 | 67.42% |

Annualized turnover is 4.226 for v3 and 0.528 for vol-targeted 60/40.

## Sub-periods, v3 @5bps

| Period | CAGR | Ann. vol | Sharpe rf=0 | Max DD | DD duration | Monthly hit rate |
|---|---:|---:|---:|---:|---:|---:|
| 2004-10-22..2008-01-01 | 9.96% | 10.28% | 0.975 | -9.47% | 114 | 68.42% |
| 2008-01-01..2015-01-01 | 7.60% | 11.00% | 0.721 | -21.01% | 471 | 69.05% |
| 2015-01-01..2020-01-01 | 6.15% | 10.19% | 0.637 | -14.26% | 477 | 70.00% |
| 2020-01-01..2022-01-01 | 9.01% | 13.74% | 0.697 | -18.38% | 257 | 62.50% |
| 2022-01-01..2026-09-01 | 5.90% | 10.38% | 0.604 | -13.15% | 474 | 57.89% |

For the like-for-like vol-targeted 60/40 at 5 bps, sub-period Sharpes are
1.189, 0.832, 1.039, 0.728, and 0.686 respectively. It exceeds v3 in every
sub-period except neither on the 2020-2022 drawdown comparison (v3 -18.38%,
vol-targeted 60/40 -18.85%).

## Deflated Sharpe and effective breadth

DSR is 1.000 / 0.999 / 0.999 at 0 / 5 / 10 bps. Effective breadth is one
fixed configuration; mean train-window Sharpe is 0.635 and cross-config
spread/sd are zero. As in v2, the DSR is essentially evidence against zero,
not a meaningful multiple-selection hurdle.

## Conclusion

The overlay does what it was designed to do mechanically. Relative to v2 at
5 bps, annual volatility falls from 14.82% to 10.87%, maximum drawdown improves
from -37.62% to -22.64%, turnover falls from 5.783 to 4.226, and Sharpe rises
slightly from 0.700 to 0.709. The cost is CAGR, which falls from 9.72% to
7.37%.

It still does not beat the required risk-matched baseline. At 5 bps, ordinary
60/40 has 0.806 Sharpe and the identically vol-targeted 60/40 has 0.853,
versus v3's 0.709. Vol-targeted 60/40 also has a slightly smaller drawdown and
about one eighth the turnover. The improvement is attributable to generic
current-vol scaling, not to a distinctive trend edge.

This is a negative baseline-relative result despite a successful risk-control
mechanism. It does not justify promotion, parameter tuning, crash rules, or
trade-outcome learning.
