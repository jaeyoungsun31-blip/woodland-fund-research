# 2026-09-01 — trend-v2-ensemble results

Harness output for the preregistered study
`2026-09-01-trend-v2-ensemble-preregistration.md`. Nothing is promoted.
The source-verification caveat remains in force.

## Study accounting

* OOS window: 2004-10-22 through 2026-09-01, 5,499 daily observations.
* Walk-forward folds: 22.
* Trials ledger: 1 distinct fixed configuration, 22 fold evaluations.
* No per-fold parameter selection occurred.

## Stitched OOS result and identical-window baselines

| Portfolio | CAGR | Ann. vol | Sharpe rf=0 | Max DD | DD duration | Monthly hit rate |
|---|---:|---:|---:|---:|---:|---:|
| v2 ensemble @0bps | 10.04% | 14.83% | 0.720 | -37.21% | 519 | 65.78% |
| v2 ensemble @5bps | 9.72% | 14.82% | 0.700 | -37.62% | 522 | 65.78% |
| v2 ensemble @10bps | 9.40% | 14.82% | 0.681 | -38.02% | 529 | 65.78% |
| SPY buy-and-hold | 11.24% | 18.84% | 0.660 | -55.19% | 1,223 | 66.67% |
| 60/40 @0bps | 8.34% | 10.62% | 0.807 | -32.32% | 709 | 67.05% |
| 60/40 @5bps | 8.33% | 10.62% | 0.806 | -32.34% | 709 | 67.05% |
| 60/40 @10bps | 8.31% | 10.62% | 0.805 | -32.35% | 709 | 67.05% |

Annualized turnover is 5.783 for the ensemble, versus 0.232 for 60/40
(about 25 times as high). SPY's one initial purchase annualizes to zero over
the reported window.

## Sub-periods, ensemble @5bps

| Period | CAGR | Ann. vol | Sharpe rf=0 | Max DD | DD duration | Monthly hit rate |
|---|---:|---:|---:|---:|---:|---:|
| 2004-10-22..2008-01-01 | 12.36% | 12.14% | 1.020 | -11.24% | 106 | 68.42% |
| 2008-01-01..2015-01-01 | 9.28% | 16.30% | 0.626 | -36.04% | 395 | 67.86% |
| 2015-01-01..2020-01-01 | 7.80% | 11.91% | 0.691 | -15.61% | 444 | 70.00% |
| 2020-01-01..2022-01-01 | 19.47% | 20.28% | 0.979 | -23.42% | 137 | 62.50% |
| 2022-01-01..2026-09-01 | 6.69% | 14.21% | 0.527 | -18.07% | 486 | 57.89% |

## Deflated Sharpe and effective breadth

DSR is 1.000 / 0.999 / 0.999 at 0 / 5 / 10 bps. This is not strong
selection evidence: effective breadth is one fixed configuration, the mean
train-window Sharpe is 0.653, and its cross-config spread and standard
deviation are both zero. The DSR is therefore essentially the probabilistic
Sharpe against zero, not a meaningful multiple-testing hurdle.

## Conclusion

The fixed ensemble removes trend-v1's unstable lookback-selection mechanism
and improves its 5 bps Sharpe from 0.612 to 0.700. It also exceeds SPY's
Sharpe on the identical window and has a smaller drawdown. It still does not
beat 60/40 on risk-adjusted return: 0.700 versus 0.806 Sharpe, with a worse
drawdown and roughly 25 times 60/40's turnover. The most recent sub-period is
also the weakest (0.527 Sharpe).

This is an informative improvement over v1, not a winning result against the
required baselines. It motivates only the already-preregistered next question:
whether current-volatility scaling improves how risk is spent. It does not
justify promotion or a new parameter search.
