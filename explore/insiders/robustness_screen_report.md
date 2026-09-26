# Phase 2 robustness screen — adjusted-close training sample

The pre-inspection repository suite ended: `619 passed, 1 skipped in 100.79s (0:01:40)`. The 2022-07-01 through 2026-06-30 filing holdout remained sealed. No network request was made. The source and both screen rules were recorded in [deviations.md](deviations.md) before running.

The prior offline raw-price/factor rebuild is superseded. Its BW reverse-split misclassification produced a +749.47 pp event-return disagreement with Tiingo; EODHD adjusted close differed from Tiingo by less than 0.02 pp on that event. The source here is local per-symbol EODHD adjusted close, scaled to the raw entry open. The original variant exactly reproduces the prior survival-corrected gross/net excess and FF5+momentum+reversal alpha, t-statistic, and residual SD for all three buckets.

Across all 10,261 executed primary clusters, pooled 1st/99th percentile gross-return cutoffs are **-56.0446% / +111.1698%**; 103 events were clipped below and 103 above. The winsor screen changes only the exit-day mark so each full-window gross event return equals the capped value; interim adjusted-price marks and entry/exit costs are unchanged.

The median screen takes the median of positions active in each month, using each position’s within-month gross/net return. A new entry starts at its adjusted entry open; a carry-in starts at the preceding month’s final close. Entry/exit charges fall in their respective months. Partial-month positions remain partial-month contributions, and this aggregation omits cash and scheduled reweighting, so it is a sensitivity diagnostic rather than an executable portfolio return.

All excess-return and alpha figures below are **percent per month**. Excess is versus same-month IWM. Alpha is the intercept of net return minus official monthly RF on FF5, momentum and short-term reversal; the t-statistic uses Newey–West lag 3. Residual SD and worst net month are also monthly percentages.

| Dollar-volume bucket | Variant | Clusters | Gross excess IWM | Net excess IWM | FF7 alpha | HAC t | Residual SD | Worst net month |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| under_300k | Original | 3036 | +3.367% | +2.678% | +3.327% | +2.36 | 14.310% | -17.086% (2020-03-31) |
| under_300k | Pooled 1/99 winsor | 3036 | +3.493% | +2.799% | +3.434% | +2.46 | 14.226% | -16.645% (2020-03-31) |
| under_300k | Median active positions | 3036 | -0.658% | -1.086% | -0.507% | -3.12 | 1.582% | -10.494% (2020-03-31) |
| 300k_to_2m | Original | 2594 | +0.772% | +0.180% | +0.187% | +0.81 | 2.513% | -20.367% (2020-03-31) |
| 300k_to_2m | Pooled 1/99 winsor | 2594 | +0.777% | +0.185% | +0.191% | +0.84 | 2.538% | -20.367% (2020-03-31) |
| 300k_to_2m | Median active positions | 2594 | -0.303% | -0.687% | -0.228% | -1.46 | 1.669% | -8.275% (2022-04-30) |
| over_2m | Original | 4631 | +0.495% | +0.108% | -0.040% | -0.12 | 3.285% | -32.625% (2020-03-31) |
| over_2m | Pooled 1/99 winsor | 4631 | +0.481% | +0.094% | -0.050% | -0.14 | 3.280% | -32.463% (2020-03-31) |
| over_2m | Median active positions | 4631 | -0.141% | -0.385% | -0.168% | -1.08 | 1.673% | -10.542% (2020-03-31) |

Each row has 129 active calendar months. The three variants retain the same 3,036 / 2,594 / 4,631 clusters by bucket and the same 13 / 21 / 13 early terminal exits with the declared −30% unknown-reason haircut. No survival filter or extra event filter was added. [Exact summary](robustness_screen_summary.csv), [monthly paths](robustness_screen_monthly.csv), and [cutoff metadata](robustness_screen_metadata.json) are retained under this directory.

## Training-sample look count

The prior look register counted 15 bucket-level return configurations: original cluster 60-session, single-insider 60-session, cluster 20-session, survival-corrected cluster 60-session, and IWM-hedged survival-corrected cluster 60-session, each in three buckets. The offline rebuilt source added three bucket-level configurations, bringing the pre-screen total to 18. Re-running the survival-corrected EODHD adjusted-close source above is the already-counted configuration. The two new robustness screens add **6** bucket-level return configurations, bringing the cumulative training-sample total to **24**. Each new variant was fit only to the requested FF5+momentum+short-term-reversal model; the original model was a reproduction check. Earlier market-only, FF5+momentum, period-split, and 2020-exclusion factor fits remain prior looks, not new filters in this run. This is exploratory look accounting, not a significance adjustment.

The raw Tiingo response cache and request timestamps were deleted; [derived validation tables and report](tiingo_validation_report.md) remain. The `cache/tiingo/` directory is empty. No portfolio result from the sealed holdout was computed.
