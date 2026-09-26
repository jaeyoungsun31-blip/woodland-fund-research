# Phase 2 training-sample bias corrections — 2026-09-23

The full repository suite passed before inspection: `619 passed, 1 skipped in 106.82s (0:01:46)`. Filings are restricted to 2012-01-01 through 2022-06-30 by the existing holdout guard. `precommit.md` was not changed; [deviations.md](deviations.md) records every post-lock methodological change. All returns and alphas below are **arithmetically computed but not reliable as a strategy finding**, because the newly admitted return paths contain material EODHD adjustment defects described below. No holdout filing was used.

## Future-survival screen and terminal histories

The revised quality screen requires complete EODHD bars from 60 market sessions before entry through the entry session, valid raw/adjusted prices, and no unexplained >80% adjusted jump in that *prior* interval. It does not require any post-entry survival. Of 117,358 verified training events, 100,408 pass this screen. The reported price falls within its transaction-day raw low/high range for 84,063 events. These produce 10,332 cluster starts; 10,261 have executable 60-session paths. Seventy-one starts have an interior price gap and are refused rather than called delistings.

An observed terminal series in EODHD's delisted catalog exits at its last close, with an extra −30% assumed terminal return. The [EODHD delisted-symbol documentation](https://eodhd.com/financial-apis/delisted-stock-companies-data-2) lists `Code`, `Name`, `Country`, `Exchange`, `Currency`, `Type`, and `Isin`, but **no delisting reason**. The local catalog has the same fields. Thus 47 terminal positions use the unknown-reason −30% rule, and **zero** can be identified as a merger/acquisition for the requested 0% rule. A terminal price series may also reflect a ticker change rather than an economic delisting, which this source cannot resolve. Counts are 13 below $300k, 21 at $300k–$2M, and 13 above $2M.

Mean monthly excess returns over IWM, percentages (changes are percentage points from the prior selected-sample run):

| Dollar-volume bucket | Clusters | Old gross → revised gross | Change | Old net → revised net | Change |
|---|---:|---:|---:|---:|---:|
| Below $300k | 3,036 | +1.271 → +3.367 | +2.096 | +0.602 → +2.678 | +2.076 |
| $300k–$2M | 2,594 | +0.734 → +0.772 | +0.038 | +0.144 → +0.180 | +0.036 |
| Above $2M | 4,631 | +0.203 → +0.495 | +0.293 | −0.183 → +0.108 | +0.290 |

The cohort and investable paths changed, so these differences are **not** the isolated effect of the −30% terminal assumption. They combine the removal of post-entry selection, changed cluster starts, early terminal exits, and the data defects. The low-bucket increase is dominated by an impossible observation: ORM's adjusted close jumps about 100-fold (100.013×) on 2014-12-15 while the raw close is unchanged on both days. MCEP's raw and adjusted closes jump about 20× on 2012-12-17. The former makes December 2014's low-bucket gross return +139.4%. We retained these paths to avoid introducing an outcome-dependent exclusion after entry; therefore the low-bucket return and alpha estimates should **not** be used to infer an edge. [survival_trade_audit.csv](survival_trade_audit.csv) exposes each path and its largest daily gain.

## Official factor regressions

The official [Kenneth French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html) supplies the US FF5, momentum, and short-term reversal daily and monthly archives. The six downloaded ZIPs are saved here. Exact URLs and SHA-256 hashes:

| Archive | SHA-256 | Official URL |
|---|---|---|
| FF5 monthly | `b8653b411cc5e28917e7ef643bb42f6d2d3703f84bc170eb6ae38d5267c65807` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip) |
| FF5 daily | `478350b8d60831351fbf754bc593fc0112b013552c24639c10902e1f26d7f306` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_daily_CSV.zip) |
| Momentum monthly | `7ee14e892b0f7044902fdbc4e25cfaf175b73d4eda0ae6f4a0354a4433afe065` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip) |
| Momentum daily | `b039d986db27fc831bcf1f52ba2134916e96fbeba4762fefc942429b0a568a96` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_daily_CSV.zip) |
| Short-term reversal monthly | `8d2b558ca55592ae3a10f3fc39fa2fcd28c1b7d47e807109de0ef0133c326b83` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_ST_Reversal_Factor_CSV.zip) |
| Short-term reversal daily | `5b491fb0d2b412e39e3151edb7e0d8c28f861174ad5dcb77186f1ef084fc970b` | [ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_ST_Reversal_Factor_daily_CSV.zip) |

The archives say they were created from the **202607 CRSP database**; French notes that historical factor returns can change when data are revised. Monthly factors are used directly for monthly net portfolio excess over official `RF`; daily files are retained as source artifacts. Newey–West/HAC lag 3 is used throughout. Alpha is percentage per month; all factor loadings are dimensionless. Each fit has 129 months. “—” means the regressor is absent.

| Bucket | Model | Alpha | HAC t | Mkt−RF | SMB | HML | RMW | CMA | Mom | ST Rev |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| <$300k | Market | +2.971% | +2.02 | +0.537 | — | — | — | — | — | — |
| <$300k | FF5+Mom | +3.213% | +2.32 | +0.458 | +0.634 | +0.826 | −0.692 | +0.612 | −0.080 | — |
| <$300k | FF5+Mom+ST Rev | +3.327% | +2.36 | +0.558 | +0.654 | +0.911 | −0.785 | +0.386 | −0.260 | −0.650 |
| $300k–$2M | Market | −0.119% | −0.35 | +1.116 | — | — | — | — | — | — |
| $300k–$2M | FF5+Mom | +0.207% | +0.89 | +0.940 | +0.698 | +0.231 | −0.464 | −0.065 | −0.111 | — |
| $300k–$2M | FF5+Mom+ST Rev | +0.187% | +0.81 | +0.922 | +0.695 | +0.216 | −0.448 | −0.024 | −0.079 | +0.116 |
| >$2M | Market | −0.411% | −0.96 | +1.331 | — | — | — | — | — | — |
| >$2M | FF5+Mom | +0.004% | +0.01 | +1.087 | +0.812 | +0.339 | −0.367 | −0.192 | −0.191 | — |
| >$2M | FF5+Mom+ST Rev | −0.040% | −0.12 | +1.049 | +0.804 | +0.306 | −0.331 | −0.105 | −0.121 | +0.251 |

For the primary bucket under the fully augmented model: excluding 2020 gives +3.565% monthly alpha (117 months, HAC t +2.23); 2012–2016 gives +3.885% (60 months, t +1.56); and 2017 through the permitted 2022H1 filing cohort, including its later exits, gives +3.380% (69 months, t +2.14). These subsets **also contain contaminated paths**, so the t-statistics support no significance claim. Full precision is in [official_factor_regressions.csv](official_factor_regressions.csv) and [primary_bucket_robustness.csv](primary_bucket_robustness.csv).

## Holdout-scale detectable alpha

The primary bucket's augmented-model monthly residual standard deviation is **14.310%**. Under independent monthly residuals, `2 × σ / √48` is **4.131% per month**. A position-level IWM hedge, using a beta fit over the prior 120 sessions, has 10,014 executable positions across the buckets (243 lacked the extra history and four produced a return below −100%). In its primary bucket, the augmented-model residual standard deviation is **17.101%**, giving **4.937% per month** by the same calculation. Hedge financing, borrow, and rebalancing costs are absent, and both residual estimates are contaminated by the price defects. The formula is a scale calculation for a nominal t of 2, not a reliable holdout-power forecast or a significance claim.

## Training-sample look count

No new selection filter, entry/exit window, or price threshold was tried in this correction. The configurations evaluated on the training sample are: (1) original code-P two-insider clusters with 60-session exits, in each of three dollar-volume buckets; (2) original every-single-insider 60-session sensitivity in each bucket; (3) original cluster 20-session-exit sensitivity in each bucket; (4) revised pre-entry-only coverage and 60-session/terminal exit in each bucket; and (5) the prior-120-session-beta IWM-hedged version of (4) in each bucket. That is **15 bucket-level return configurations**. The first nine had the original pinned-series one-factor fit; the six new configurations each had market, FF5+momentum, and FF5+momentum+short-term-reversal fits; the primary revised configuration's augmented model was additionally fit excluding 2020 and in the two stated sub-periods. The two outlier-month inspections were data audits, not alternative strategy configurations. None of these runs opened the sealed holdout.
