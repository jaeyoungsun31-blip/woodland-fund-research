# Phase 2 offline price rebuild — training filings only

The repository suite was run before inspection: `619 passed, 1 skipped in 107.64s (0:01:47)`. The holdout guard rejected filings outside 2012-01-01 through 2022-06-30 before any return calculation. The operative classification rules were written to [deviations.md](deviations.md) before this run; `precommit.md` is unchanged. Steps 1–4 used only local data and made no network calls.

## Source coverage and rule

For each locally available EODHD symbol, the script computes `f = adjusted_close / raw_close` and raw close-to-close return. It uses factor **steps** only in the locked split/dividend classes; it never substitutes the EODHD adjusted-close return into a position. Entry is raw open; subsequent daily total returns are compounded from the class rule. The fixed defect confirmation is a 50% raw-price reversal within five observed sessions or zero volume, following an unmatched raw move beyond ±75%. An event with a confirmed defect in its observed [−20,+60] session window is excluded, regardless of return.

There were 8,828 distinct SEC ticker strings in the training filings: **7,387** had local EODHD histories classified, **1,288** had no local file, and **153** were malformed strings that were not guessed into symbols. Among 117,358 issuer/name-verified filing events, 83,672 passed the resulting coverage, transaction-price, and fixed-defect checks; 10,281 primary clusters executed. The 14,516 pre/post gap failures and 2 unprocessable-window bars are separately recorded in [offline_rebuild_metadata.json](offline_rebuild_metadata.json).

The class counts below are unique `(bucket, filing year, symbol, symbol-day)` occurrences in verified issuer event windows, so overlapping filings do not multiply one day. “Suspected” excludes confirmed defects; excluded events can exceed confirmed defect days because several events may share a defective day.

| Year | Bucket | Split | Dividend | Adj. error | Suspected | Defect days | Ordinary | Unusable | Excluded events |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2012 | 300k_to_2m | 0 | 490 | 1 | 3 | 0 | 54557 | 0 | 0 |
| 2012 | over_2m | 6 | 1118 | 0 | 8 | 2 | 93705 | 0 | 3 |
| 2012 | under_300k | 1 | 446 | 0 | 38 | 38 | 79503 | 0 | 60 |
| 2013 | 300k_to_2m | 1 | 508 | 1 | 2 | 0 | 45929 | 0 | 0 |
| 2013 | over_2m | 4 | 984 | 0 | 6 | 2 | 88996 | 0 | 4 |
| 2013 | under_300k | 5 | 983 | 2 | 24 | 35 | 70798 | 0 | 58 |
| 2014 | 300k_to_2m | 4 | 712 | 0 | 5 | 0 | 57233 | 0 | 0 |
| 2014 | over_2m | 9 | 1120 | 1 | 2 | 0 | 103057 | 0 | 0 |
| 2014 | under_300k | 8 | 1089 | 1 | 19 | 35 | 67832 | 0 | 55 |
| 2015 | 300k_to_2m | 6 | 775 | 0 | 13 | 4 | 59137 | 0 | 20 |
| 2015 | over_2m | 11 | 1541 | 0 | 9 | 3 | 127593 | 0 | 6 |
| 2015 | under_300k | 7 | 1193 | 3 | 55 | 57 | 76836 | 9 | 78 |
| 2016 | 300k_to_2m | 2 | 539 | 0 | 7 | 2 | 55870 | 0 | 9 |
| 2016 | over_2m | 6 | 1141 | 0 | 1 | 0 | 110572 | 0 | 0 |
| 2016 | under_300k | 9 | 812 | 0 | 38 | 20 | 76787 | 0 | 24 |
| 2017 | 300k_to_2m | 6 | 500 | 2 | 4 | 1 | 51712 | 0 | 1 |
| 2017 | over_2m | 5 | 1055 | 0 | 7 | 0 | 108265 | 0 | 0 |
| 2017 | under_300k | 8 | 595 | 0 | 25 | 32 | 66311 | 0 | 44 |
| 2018 | 300k_to_2m | 0 | 529 | 1 | 2 | 3 | 56663 | 0 | 5 |
| 2018 | over_2m | 7 | 1404 | 0 | 10 | 0 | 131057 | 0 | 0 |
| 2018 | under_300k | 3 | 518 | 1 | 21 | 15 | 65231 | 0 | 25 |
| 2019 | 300k_to_2m | 2 | 504 | 0 | 14 | 0 | 52524 | 0 | 0 |
| 2019 | over_2m | 0 | 1126 | 0 | 9 | 0 | 114522 | 0 | 0 |
| 2019 | under_300k | 3 | 827 | 0 | 39 | 30 | 72931 | 2 | 16 |
| 2020 | 300k_to_2m | 4 | 708 | 0 | 16 | 9 | 67207 | 0 | 15 |
| 2020 | over_2m | 1 | 1435 | 0 | 23 | 7 | 148072 | 0 | 14 |
| 2020 | under_300k | 4 | 686 | 3 | 57 | 48 | 75797 | 0 | 98 |
| 2021 | 300k_to_2m | 2 | 644 | 0 | 11 | 3 | 64008 | 0 | 6 |
| 2021 | over_2m | 1 | 1030 | 0 | 5 | 2 | 122168 | 0 | 2 |
| 2021 | under_300k | 1 | 782 | 0 | 50 | 35 | 65964 | 0 | 33 |
| 2022 | 300k_to_2m | 1 | 281 | 0 | 6 | 0 | 37389 | 0 | 0 |
| 2022 | over_2m | 2 | 717 | 0 | 5 | 0 | 81337 | 0 | 0 |
| 2022 | under_300k | 1 | 560 | 1 | 18 | 9 | 47065 | 0 | 19 |

The exclusion register, including each event’s ticker and filing date, is [offline_rebuild_exclusions.csv](offline_rebuild_exclusions.csv). Its 595 rows comprise 510 below $300k, 56 at $300k–$2M, and 29 above $2M.

## Primary portfolio and factor arithmetic

Mean monthly excess over IWM is gross/net after the previously locked spread and commission convention; percentages are per month. The unknown-reason terminal haircut is −30% at final available close. No future-survival requirement is imposed.

| Dollar-volume bucket | Clusters | Active months | Terminal exits | Gross excess IWM | Net excess IWM |
| --- | --- | --- | --- | --- | --- |
| under_300k | 3036 | 129 | 13 | +4.824% | +4.120% |
| 300k_to_2m | 2600 | 129 | 22 | +0.917% | +0.325% |
| over_2m | 4645 | 129 | 13 | +0.557% | +0.166% |

Official monthly French `RF` and `Mkt-RF` underlie all three regressions; the official FF5, momentum, and short-term-reversal ZIP URLs and SHA-256 hashes remain in [french_archives_manifest.json](french_archives_manifest.json). Newey–West/HAC lag 3 is used. Alpha, residual standard deviation, and the nominal 48-month t=2 detectable alpha are percent **per month**; factor loadings are dimensionless. The detectable-alpha arithmetic is `2 × residual SD / √48`, assuming independent monthly residuals.

| Bucket | Model | Alpha | HAC t | Residual SD | 48m MDE | Mkt−RF | SMB | HML | RMW | CMA | Mom | ST Rev |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| under_300k | market | +4.008% | +2.30 | 18.736% | 5.409% | +0.933 | — | — | — | — | — | — |
| under_300k | ff5_momentum | +4.418% | +2.58 | 18.300% | 5.283% | +0.472 | +2.467 | -0.265 | +0.941 | -0.644 | +0.213 | — |
| under_300k | ff5_momentum_reversal | +4.437% | +2.39 | 18.374% | 5.304% | +0.488 | +2.470 | -0.252 | +0.925 | -0.681 | +0.183 | -0.107 |
| 300k_to_2m | market | +0.119% | +0.29 | 4.004% | 1.156% | +1.025 | — | — | — | — | — | — |
| 300k_to_2m | ff5_momentum | +0.495% | +1.58 | 3.049% | 0.880% | +0.787 | +0.850 | +0.137 | -0.257 | -0.157 | -0.173 | — |
| 300k_to_2m | ff5_momentum_reversal | +0.468% | +1.54 | 3.041% | 0.878% | +0.764 | +0.846 | +0.117 | -0.235 | -0.103 | -0.130 | +0.153 |
| over_2m | market | -0.352% | -0.82 | 4.482% | 1.294% | +1.331 | — | — | — | — | — | — |
| over_2m | ff5_momentum | +0.056% | +0.16 | 3.449% | 0.996% | +1.098 | +0.765 | +0.347 | -0.416 | -0.207 | -0.181 | — |
| over_2m | ff5_momentum_reversal | +0.007% | +0.02 | 3.404% | 0.983% | +1.056 | +0.756 | +0.311 | -0.376 | -0.111 | -0.104 | +0.275 |

**These numbers are not credible edge or power estimates.** The locked rule retains persistent, unmatched raw-price jumps. The largest retained trade is AMBS at +99.2×; MCEP remains at +21.55× in a later table. The rule also misses [AAPL's documented 4-for-1 split](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes): its raw close fell 74.152% on 2020-08-31 while its factor stepped almost exactly 4×. Because the implied split-neutral return is +3.391%, outside the rule's ±2% match tolerance, that day is classified `ordinary_raw` at −74.152%; it also misses the >75% suspected-defect threshold. This is an uncorrected rule limitation, not a new exclusion. Such days can distort portfolio months and factor fits. The rule was not changed after seeing them, and no significance claim is made. Full paths are in [offline_rebuild_monthly_portfolios.csv](offline_rebuild_monthly_portfolios.csv) and [offline_rebuild_trades.csv](offline_rebuild_trades.csv).

## Terminal-history and mapping audit

The full [terminal-exit audit](offline_rebuild_terminal_audit.csv) gives every ticker and last-price date. The local [EODHD delisted-symbol list](https://eodhd.com/financial-apis/delisted-stock-companies-data-2) has no reason field, so all 48 early terminal positions use the −30% unknown-reason assumption; no 0% merger exception can be identified.

| Mapped primary bucket | Terminal within 60 | Executed clusters | Rate |
| --- | --- | --- | --- |
| under_300k | 13 | 3036 | 0.428% |
| 300k_to_2m | 22 | 2600 | 0.846% |
| over_2m | 13 | 4645 | 0.280% |

Of **36,415** unmapped issuer/insider filings, **9,527** SEC ticker strings appear in the EODHD delisted list (26.16%). Among those, **77** have a local raw series ending within 60 sessions of an available entry bar and **6347** continue 60 sessions: 1.199% of these 6,424 assessable ticker histories are terminal. Another 2,748 lack an entry bar and 355 end before entry. The [unmapped audit](unmapped_delisted_ticker_audit.csv) is a **ticker-level missingness diagnostic**, not a verified CIK-to-security mapping; most unmapped events have no trustworthy dollar-volume bucket, so its rate is not directly comparable with the mapped bucket rates.

| Unmapped ticker's inherited bucket | Terminal within 60 | Assessable ticker histories | Observed terminal rate | No usable entry bar |
| --- | ---: | ---: | ---: | ---: |
| under_300k | 4 | 706 | 0.567% | 70 |
| 300k_to_2m | 17 | 288 | 5.903% | 1 |
| over_2m | 0 | 163 | 0.000% | 0 |
| unavailable | 56 | 5,267 | 1.063% | 3,032 |

The inherited bucket on an unmapped row does **not** verify its issuer identity. The higher observed middle-bucket terminal rate may signal missing delistings, ticker reuse, or both; the 3,103 rows without a usable entry bar make a complete comparison impossible.

## ORM and MCEP spot-check

The [daily spot-check file](spotcheck_orm_mcep_daily.csv) lists every symbol-day in each [−20,+60] window, its raw close, factor step, class, rebuilt return, and defect flag. Each window has 81 observed sessions.

| Window | Key day | Raw return | Factor step | Locked class | Rebuilt daily return | Window treatment |
| --- | --- | --- | --- | --- | --- | --- |
| ORM, entry 2014-11-21 | 2014-12-15 | 0.000% | 100.013× | Adjustment error | 0.000% | Included; no confirmed defect; 60-session trade −15.181% |
| MCEP, entry 2012-11-19 | 2012-12-17 | +1,858.333% | 1.000× | Suspected defect | +1,858.333% | Included; no 50% reversal or zero volume; trade +2,154.667% |
| MCEP, entry 2014-11-24 | 2014-12-16 | +2,140.000% | 1.000× | Suspected defect | +2,140.000% | Included; no 50% reversal or zero volume; trade about +728% |

The absence of confirmation under the fixed rule does not establish that MCEP’s jumps are economically real. This is the principal unresolved price defect.

## Independent validation

The fixed [300-event sample](validation_sample_300.csv) contains 100 post-2016 executed clusters per bucket, drawn with seed 20260923. No Alpaca market-data credentials were present in the task environment. The available `data/audit/tiingo-crosscheck-*` files cover only ETF symbols, with **zero** overlap with the 300 sampled stock tickers. Accordingly, the share within 1 percentage point, median absolute difference, and list of cases more than 10 points apart are **unavailable**; no independent validation is claimed. No Alpaca or other network call was made.
