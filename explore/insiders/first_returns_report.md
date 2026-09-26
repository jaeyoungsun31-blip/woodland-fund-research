# Phase 2 first returns: sealed training sample

The holdout guard was committed as `f56efeea9b87913f8fa7cf69c9242ef4b7442907`, and the exact study design was committed as `40358c620255392b8b8795e469cce4e7025d5ce1`, both before any return calculation. The source-selection step materialized 153,773 filing events from 2012-01-01 through 2022-06-30 and explicitly excluded 45,610 later events. An audit then found that the earlier feasibility mapping had used later SEC names/CIKs. `rebuild_training_mapping.py` recomputed identity using pre-July-2022 SEC filings only before the final return run: 2,337 events gained verification, 3,537 lost it, and 96,878 passed the resulting price-quality screen. Every return entry point calls the guard before opening prices or factors. Focused holdout and arithmetic tests: 10 passed.

SEC transaction code `P` also includes private purchases; the signal is not verified open-market trading. The identity check uses a 2026 EODHD symbol catalog because no dated historical catalog/CIK mapping is available; removing later SEC filings does not turn it into a point-in-time identity source. The price-quality screen requires **120 post-filing sessions**, creating future-survival selection. Results are exploratory descriptions of that selected population, not a prospective backtest or a significance claim. The low-liquidity bucket is the precommitted primary bucket. Portfolio returns in July–September 2022 come only from positions opened by June 2022; no holdout-dated filings enter the study.

## Primary: two-insider clusters, 60-session exit

All return and spread columns are percentages. Gross/net excess is mean monthly calendar-time portfolio return minus IWM's same-month adjusted return. Alpha is monthly net portfolio return in excess of CASH regressed on pinned MKT−CASH, with Newey–West lag-3 t-statistic. The pinned file contains **MKT and CASH only**, so this is a one-factor market alpha, not FF3. The "worst month" is the portfolio's worst absolute net monthly return.

| Dollar-volume bucket | Clusters | Active months | Gross excess | Net excess | Market alpha | HAC t | Worst net month | Mean round-trip spread charge |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Below $300k (primary) | 2,920 | 129 | +1.271 | +0.602 | +0.505 | +1.29 | −20.610 | 1.783 |
| $300k–$2M | 2,536 | 129 | +0.734 | +0.144 | −0.123 | −0.37 | −19.633 | 1.536 |
| Above $2M | 4,576 | 129 | +0.203 | −0.183 | −0.698 | −1.88 | −32.187 | 0.930 |

The 20-session pre-entry Corwin–Schultz estimate is charged in full at entry and exit, with 5 bp commission each way. The estimator uses raw two-day high–low ranges and no overnight adjustment. Scheduled portfolio reweighting is accounting-only and has no additional transaction cost; net results are therefore optimistic for a monthly rebalanced implementation. See the locked `precommit.md` and the [Corwin–Schultz paper](https://users.nber.org/~confer/2009/mms09/Corwin_Schultz.pdf) for the formula.

## Sensitivities, not primary

| Variant | Dollar-volume bucket | Positions | Active months | Gross excess | Net excess | Market alpha | HAC t |
|---|---|---:|---:|---:|---:|---:|---:|
| All single-insider purchases, 60d | Below $300k | 25,743 | 129 | +1.556 | +0.860 | +0.775 | +2.07 |
| All single-insider purchases, 60d | $300k–$2M | 20,297 | 129 | +0.546 | −0.025 | −0.235 | −0.73 |
| All single-insider purchases, 60d | Above $2M | 35,524 | 129 | +0.297 | −0.082 | −0.588 | −1.66 |
| Clusters, 20d exit | Below $300k | 2,920 | 128 | +1.400 | −0.494 | −0.567 | −1.19 |
| Clusters, 20d exit | $300k–$2M | 2,536 | 127 | +1.134 | −0.577 | −0.878 | −2.23 |
| Clusters, 20d exit | Above $2M | 4,576 | 128 | +0.280 | −0.828 | −1.218 | −3.21 |

The full-precision table is `returns_summary.csv`, the monthly gross/net paths are `monthly_portfolios.csv`, and executed event identities, dates, and spreads are in `executed_trades.parquet`. There were 96,878 mapped quality-screened training events, of which 81,564 had at least one reported purchase price inside the raw transaction-day range. These yielded 10,032 executable primary clusters. No selected position was lost during entry, exit, or spread construction.

## Bias check

Potential starts are constructed from SEC code-P filing events before mapping, quality, and reported-price checks. A potential issuer/date is "kept" only if the filtered cluster starts on that same date; filtering can move a later cluster start, so 10,032 executable starts exceed the 9,407 exact-date survivors below. Mapping or quality loss is a classification of the two-insider trailing window at each potential start.

| Filing year | Potential starts | Mapping failures | Quality-screen failures | Mapping + quality loss share |
|---|---:|---:|---:|---:|
| 2012 | 1,993 | 688 | 274 | 48.3% |
| 2013 | 1,651 | 531 | 261 | 48.0% |
| 2014 | 1,933 | 581 | 308 | 46.0% |
| 2015 | 2,079 | 570 | 318 | 42.7% |
| 2016 | 1,767 | 451 | 203 | 37.0% |
| 2017 | 1,517 | 344 | 213 | 36.7% |
| 2018 | 1,745 | 341 | 215 | 31.9% |
| 2019 | 1,682 | 344 | 212 | 33.1% |
| 2020 | 2,088 | 374 | 230 | 28.9% |
| 2021 | 1,632 | 326 | 254 | 35.5% |
| 2022 through June | 971 | 156 | 96 | 26.0% |

Overall, 7,290/19,058 potential starts (38.3%) are lost to mapping or quality, another 2,309 to the reported-price check, and 52 shift cluster timing. The full year table is `bias_by_year.csv`. For the 60-session pre-filing adjusted return, the **median** among 9,401 price-available kept starts is **−8.25%**; among 2,928 price-available lost starts it is **−0.53%**. Only 30.3% of lost starts have an available CIK/name mapping and complete pre-window to compute this comparison, versus 99.9% of kept starts. Failed-quality price series include extreme adjusted-price observations (for example, FBRX's computed pre-window return exceeds 8,000×), so raw means are not informative. The comparison is not evidence that the lost population has a different return distribution. `bias_events.parquet` records availability and status for every potential start, and `bias_pre60_summary.csv` gives the summary.

No holdout-dated filing was opened for returns. No journal, report, config, trials-ledger, or `data/` file was written.
