# OSAP anomaly triage: what survives after publication, and after value-weighting

2026-09-26. **Meta-research only.** No predictor is selected, ranked or
recommended here. This is an exploration under `explore/osap/`, not a harness
study, and it makes no performance claim (binding rule 7). Pre-run suite:
`619 passed, 1 skipped in 87.98s (0:01:27)`.

## Data and licence

- **Source.** Chen & Zimmermann, *Open Source Asset Pricing*, October 2025
  release (v2.0.0), from the [data page](https://www.openassetpricing.com/data/).
  The authors ask that the paper be cited: Chen and Zimmermann (2022),
  "Open Source Cross-Sectional Asset Pricing", *Critical Finance Review*
  11(2).
- **Licence.**
  - The portfolio returns are linked publicly, with no login.
  - Only the three CRSP-derived stock-level signals (Price, Size, STreversal)
    are withheld; the page says they "can be downloaded from CRSP".
  - The [download package](https://github.com/mk0417/open-asset-pricing-download)
    likewise requires WRDS only for those signals.
  - The [code](https://github.com/OpenSourceAP/CrossSection) is GPL-2.0.
  - **The data page states no explicit data licence.** Raw files are
    therefore used privately, kept in gitignored `raw/` and not
    redistributed.
- **Files.** URLs, sizes and sha256 are in [sources.json](sources.json).
  - **OP.** `PredictorLSretWide.csv` holds the monthly long-short returns of
    212 predictors, built as in each original paper (OP): 1926-01 to
    2024-12, percent per month.
  - **VW.** The `LS` leg of
    `PredictorAltPorts_LiqScreen_VWforce.csv` (inside the ZIP) is OSAP's
    alternative implementation with **value-weighting forced** on the OP
    sorts. It is one of the release's "liquidity screen" variants, but the
    file name indicates only forced value-weighting. No other screen (price,
    size or exchange) was verified or is claimed.
  - **Documentation.** `SignalDoc.csv` supplies each predictor's windows and
    categories.
- **How the files were obtained.**
  - Both Drive copies of `SignalDoc.csv` returned "Quota exceeded", so the
    file was taken from the v2.0.0 code tag. Whether it is byte-identical to
    the Drive copy was not verified.
  - The two return files were refused to anonymous download for the same
    reason. Jaeyoung downloaded them in a signed-in browser, and they were
    then hashed.

## Method

- **Sample.** The 212 predictors (`Cat.Signal == Predictor`). All 212 are
  in both files.
- **Windows** (calendar months, inclusive, from `SignalDoc.csv`):
  - **in-sample:** January of `SampleStartYear` to December of
    `SampleEndYear`
  - **post-publication:** January of `Year + 1` to December 2024
  - **2015–2024**
- **Excluded months.** The months between sample end and publication are
  excluded from both of the first two windows.
- **Statistics.** Mean monthly long-short return and
  `t = mean / (sd / √n)`, iid, with at least 12 months required. The
  post/in-sample ratio is `mean_post / mean_in`, defined only when
  `mean_in > 0`.
- **Fields available.** `SignalDoc.csv` has no turnover field. Its
  rebalancing field is `Portfolio Period` in months (109 monthly,
  92 annual, 11 other). Categories come from `Cat.Data`. `Cat.Economic`
  exists but is too fine-grained, with dozens of labels, to tabulate here.
- **Code.** [fetch.py](fetch.py) and [triage.py](triage.py). Derived CSVs
  are written to the gitignored `raw/derived/`.

## Headline: positive mean with t > 2

| Window | OP | VW (forced) | Both | Expected by chance alone | Median months |
|---|---:|---:|---:|---:|---:|
| In-sample | 186/212 (87.7%) | 101/212 (47.6%) | 98 | 4.9 | 336 |
| Post-publication to 2024 | **60/212 (28.3%)** | **22/212 (10.4%)** | 19 | 5.0 | 216 |
| 2015–2024 | **30/208 (14.4%)** | **14/208 (6.7%)** | 6 | 5.0 | 120 |

**What "expected by chance" means.** It is the expected count of positive
means with t > 2 if every true mean were zero, summed over each series'
Student-t tail: 212 × about 2.4%, which is about 5.

- If the series were independent, the count would exceed **10** less than
  2.5% of the time. That figure uses a binomial with p = 0.0239 and
  n = 208.
- The series are correlated, so the real count is more dispersed than that,
  though the expected value is unchanged.
- **With 212 series, about 5 will clear t > 2 by luck, and the report cannot
  say which ones.** Reading any single row of the appendix as a discovery is
  exactly the error this triage is meant to prevent.

**Other headline figures.**

- **Median mean return, in / post / 2015–24, percent per month:**
  - OP: 0.575 / 0.226 / 0.199
  - VW: 0.355 / 0.102 / 0.052
- **Share of positive means, in / post / 2015–24:**
  - OP: 98.1% / 83.5% / 70.3%
  - VW: 92.0% / 66.5% / 54.7%
- **Agreement between OP and VW.** The correlation of per-predictor means
  is 0.71 in-sample, 0.77 post-publication and 0.72 in 2015–2024. Only 6
  predictors have a positive mean with t > 2 in both implementations in
  2015–2024.
- **Four predictors have no 2015–2024 data** (Activism1, Activism2,
  Governance, ProbInformedTrading). The denominators are therefore 208, not
  212.

## Post-publication / in-sample ratio

| | OP | VW (forced) |
|---|---:|---:|
| Predictors with a defined ratio (`mean_in > 0`) | 208 | 195 |
| p10 | −0.11 | −0.90 |
| p25 | 0.14 | −0.09 |
| **Median** | **0.39** | **0.26** |
| p75 | 0.68 | 0.76 |
| p90 | 1.14 | 1.72 |
| Share below 0 | 14.9% | 32.8% |
| Share 0 to 0.5 | 45.2% | 32.3% |
| Share 0.5 to 1 | 27.9% | 18.5% |
| Share at least 1 | 12.0% | 16.4% |

- **The typical OP predictor keeps about 40% of its in-sample mean after
  publication.** The value-weighted version keeps about 25%, and a third of
  VW ratios are negative.
- **The ratio is heavy-tailed.** The VW mean ratio is 0.91 because small
  in-sample denominators produce large ratios. Medians are therefore the
  quantities to read.
- The direction matches the published post-publication-decay literature
  (McLean and Pontiff, 2016). Their magnitudes were not re-derived here.

## By data category (`Cat.Data`)

| Cat.Data | N | OP post: +t>2 | VW post: +t>2 | OP 2015–24: +t>2 | VW 2015–24: +t>2 | OP median mean in / post / 15–24 | VW median mean in / post / 15–24 | Median post/in ratio OP / VW |
|---|---:|---:|---:|---:|---:|---|---|---|
| 13F | 8 | 2/8 | 1/8 | 2/6 | 0/6 | +0.66 / +0.34 / +0.54 | +0.31 / +0.12 / -0.48 | 0.63 / 0.35 |
| Accounting | 99 | 33/99 | 8/99 | 17/99 | 5/99 | +0.50 / +0.22 / +0.20 | +0.32 / +0.10 / +0.06 | 0.47 / 0.28 |
| Analyst | 18 | 5/18 | 2/18 | 0/18 | 1/18 | +0.65 / +0.22 / +0.15 | +0.34 / +0.11 / +0.05 | 0.30 / 0.44 |
| Event | 8 | 6/8 | 2/8 | 2/8 | 1/8 | +0.53 / +0.57 / +0.50 | +0.37 / +0.18 / +0.54 | 0.56 / 0.67 |
| Options | 9 | 4/9 | 3/9 | 3/9 | 2/9 | +0.88 / +0.23 / +0.23 | +0.65 / +0.16 / +0.09 | 0.47 / 0.15 |
| Other | 12 | 0/12 | 0/12 | 0/11 | 0/11 | +0.34 / -0.11 / -0.18 | +0.29 / +0.01 / +0.14 | -0.29 / 0.07 |
| Price | 45 | 8/45 | 5/45 | 4/45 | 5/45 | +0.81 / +0.27 / +0.21 | +0.76 / +0.20 / +0.10 | 0.34 / 0.28 |
| Trading | 13 | 2/13 | 1/13 | 2/12 | 0/12 | +0.63 / +0.26 / -0.01 | +0.34 / +0.01 / -0.20 | 0.29 / 0.04 |

- **Small groups.** 13F, Event, Options, Other and Trading have 8–13
  predictors each. Their shares move by more than 10 points on a single
  predictor.
- **Where the losses concentrate.** Accounting is almost half the sample.
  Its post-publication pass count drops from 33 (OP) to 8 (VW), which
  accounts for most of the loss from value-weighting.
- **Other.** Governance and similar signals: no predictor clears t > 2 in
  any post-publication or recent window, in either implementation.

## By rebalancing frequency (`Portfolio Period`, months)

| Portfolio Period | N | OP post: +t>2 | VW post: +t>2 | OP 2015–24: +t>2 | VW 2015–24: +t>2 | OP median mean in / post / 15–24 | VW median mean in / post / 15–24 | Median post/in ratio OP / VW |
|---|---:|---:|---:|---:|---:|---|---|---|
| 1 (monthly) | 109 | 33/109 | 13/109 | 16/105 | 8/105 | +0.71 / +0.26 / +0.21 | +0.43 / +0.13 / +0.12 | 0.38 / 0.23 |
| 12 (annual) | 92 | 24/92 | 6/92 | 13/92 | 4/92 | +0.46 / +0.19 / +0.17 | +0.30 / +0.07 / -0.02 | 0.37 / 0.26 |
| other (3.0) | 7 | 2/7 | 2/7 | 1/7 | 2/7 | +1.05 / +0.43 / +0.62 | +1.16 / +0.57 / +1.63 | 0.44 / 0.55 |
| other (36.0) | 1 | 0/1 | 0/1 | 0/1 | 0/1 | +0.89 / +0.22 / +0.21 | +0.89 / +0.22 / +0.21 | 0.25 / 0.25 |
| other (6.0) | 2 | 0/2 | 0/2 | 0/2 | 0/2 | +0.36 / +0.26 / +0.21 | +0.16 / +0.06 / -0.04 | 0.82 / 4.41 |
| other (nan) | 1 | 1/1 | 1/1 | 0/1 | 0/1 | +0.57 / +0.63 / +0.25 | +0.36 / +0.32 / -0.13 | 1.10 / 0.90 |

- **Monthly and annual rebalancers decay similarly on OP.** The median ratio
  is 0.38 for monthly and 0.37 for annual.
- **Annual rebalancers fare worse on VW in 2015–2024.** Their median mean is
  −0.02, and 4 of 92 clear t > 2.
- **Turnover.** Annual rebalancing implies lower turnover, and so lower
  trading costs. That favours the annual group once costs are counted, but
  no cost is modelled here.
- **Other periods.** The groups with 3-, 6- and 36-month periods and a
  missing period have 1–7 predictors each and are not interpretable.

## By original weighting (`Stock Weight`)

| Stock Weight | N | OP post: +t>2 | VW post: +t>2 | OP 2015–24: +t>2 | VW 2015–24: +t>2 | OP median mean in / post / 15–24 | VW median mean in / post / 15–24 | Median post/in ratio OP / VW |
|---|---:|---:|---:|---:|---:|---|---|---|
| EW | 184 | 58/184 | 20/184 | 28/183 | 12/183 | +0.59 / +0.25 / +0.20 | +0.34 / +0.09 / +0.05 | 0.43 / 0.25 |
| VW | 28 | 2/28 | 2/28 | 2/25 | 2/25 | +0.50 / +0.16 / +0.18 | +0.50 / +0.16 / +0.18 | 0.28 / 0.28 |

- **The original weighting explains most of the OP–VW gap.** 184 of 212
  original implementations are equal-weighted.
- **Consistency check.** The 28 predictors that were already value-weighted
  in their original papers give identical figures in both files, as they
  should.
- **Equal-weighted predictors lose most of their post-publication strength
  when value-weighted.** 58 of 184 clear t > 2 in OP post-publication, but
  only 20 in VW. That is the signature of returns concentrated in small,
  expensive-to-trade stocks.

## Limitations

1. **Gross of all trading costs.**
   - Every return here is before commissions, spreads, price impact,
     borrowing fees for the short leg, and taxes.
   - `SignalDoc.csv` provides no turnover, so costs cannot even be
     approximated per predictor.
   - A 0.2%-per-month gross long-short spread, near the OP 2015–2024 median,
     is small next to plausible round-trip costs for monthly rebalanced
     small-cap portfolios. This project measured the turnover budget at
     K ≈ 232 (`2026-09-03-planning-note-turnover-budget`).
2. **Multiple testing.**
   - 212 correlated series are examined in three windows each.
   - About 5 positive t > 2 results per window are expected with no true
     effect at all.
   - The in-sample column is also selected: these predictors were published
     *because* they cleared significance in-sample.
   - No multiple-testing adjustment is applied, and no individual result
     should be read as significant.
3. **Equal-weighted and microcap-heavy.**
   - 184 of 212 original implementations are equal-weighted, and their
     returns lean on small and illiquid stocks.
   - The VW file addresses weighting only. Nothing here applies a
     price, size or exchange screen.
   - VW is still gross of costs, and its short legs can still be hard to
     borrow.
4. **iid t-statistics.** No Newey–West or bootstrap correction is applied.
   Monthly long-short returns have mild autocorrelation, but some predictors
   hold positions for 12–36 months. Their t-statistics may be overstated.
5. **Window definitions.**
   - Publication `Year` is the journal year, not the working-paper date.
     Market participants may have known of a signal earlier, which would bias
     the post/in-sample ratio upward.
   - Calendar-year boundaries are coarse.
   - Months between sample end and publication are ignored.
   - Some post-publication windows are short: minimum 14 months, median
     216.
6. **Coverage.**
   - Four predictors have no 2015–2024 returns.
   - Option-implied predictors end early in this release (the data page says
     December 2022). Seven have 97 months in the "2015–2024" window, and the
     two option-volume predictors have 105.
   - The ratio is undefined for 4 OP and 17 VW predictors with a non-positive
     in-sample mean.
7. **Provenance.**
   - `SignalDoc.csv` came from the GitHub v2.0.0 tag, not the Drive copy.
   - The two return files were browser-downloaded by Jaeyoung.
   - The hashes pin exactly what was analysed, but the files were not
     cross-checked against a second source.
   - These are OSAP's reconstructions, not the original authors' data.
8. **No selection, no study.**
   - This triage chooses nothing.
   - Any predictor picked from the appendix would be picked after seeing its
     2015–2024 result. It would need a fresh pre-registration and a genuinely
     unseen sample, and there is essentially none left for US equities
     through 2024.
   - It would also have to pass the standing T2 filter
     (`2026-09-03-planning-decision-termination-and-v16-withdrawal`).

## Appendix: per-predictor results (alphabetical; not a ranking)

Each cell shows the mean monthly long-short return in percent, with the iid
t-statistic in brackets. "Pub." is the publication year from `SignalDoc.csv`.
"—" means fewer than 12 months in the window. **About 5 cells per column
clear t > 2 by chance alone.**

| Predictor | Pub. | OP in | OP post | OP 2015–24 | VW in | VW post | VW 2015–24 |
|---|---:|---:|---:|---:|---:|---:|---:|
| AbnormalAccruals | 2001 | +0.53 (+4.9) | -0.13 (-0.8) | -0.17 (-0.7) | +0.57 (+3.5) | +0.08 (+0.3) | +0.16 (+0.4) |
| Accruals | 1996 | +0.69 (+6.7) | +0.10 (+1.0) | -0.07 (-0.4) | +0.54 (+3.1) | +0.10 (+0.6) | -0.01 (-0.0) |
| AccrualsBM | 2004 | +1.45 (+4.9) | +0.90 (+2.6) | +0.73 (+1.3) | +0.37 (+0.9) | +0.09 (+0.2) | +0.04 (+0.1) |
| Activism1 | 2005 | +0.24 (+1.0) | +0.15 (+0.3) | — | +0.24 (+1.0) | +0.15 (+0.3) | — |
| Activism2 | 2005 | +0.44 (+1.0) | +0.16 (+0.2) | — | +0.44 (+1.0) | +0.16 (+0.2) | — |
| AdExp | 2001 | +0.65 (+3.1) | +0.32 (+1.4) | -0.12 (-0.3) | +0.88 (+4.0) | +0.09 (+0.4) | -0.28 (-0.8) |
| AgeIPO | 1991 | +1.61 (+4.7) | +0.76 (+2.7) | +0.66 (+1.2) | +0.47 (+0.8) | +0.95 (+2.9) | +0.78 (+1.4) |
| AM | 1992 | +0.62 (+3.5) | +0.47 (+1.7) | +0.37 (+0.8) | +0.22 (+1.2) | +0.03 (+0.1) | -0.29 (-0.6) |
| AnalystRevision | 1984 | +0.96 (+5.4) | +0.53 (+6.7) | +0.10 (+0.7) | +0.78 (+3.4) | +0.34 (+2.7) | +0.49 (+2.0) |
| AnalystValue | 1998 | +0.21 (+1.4) | +0.39 (+1.3) | +0.34 (+0.7) | +0.37 (+2.1) | +0.27 (+0.9) | -0.13 (-0.2) |
| AnnouncementReturn | 1996 | +1.15 (+12.7) | +0.80 (+7.2) | +0.35 (+1.8) | +0.77 (+5.1) | +0.34 (+2.0) | +0.27 (+1.0) |
| AOP | 1998 | +0.36 (+2.0) | +0.00 (+0.0) | +0.05 (+0.3) | -0.08 (-0.4) | +0.11 (+0.5) | +0.07 (+0.2) |
| AssetGrowth | 2008 | +1.49 (+7.7) | +0.67 (+2.6) | +0.47 (+1.4) | +0.86 (+4.2) | -0.04 (-0.1) | -0.08 (-0.2) |
| Beta | 1973 | +0.68 (+1.8) | +0.26 (+0.9) | +0.42 (+0.6) | +0.54 (+1.5) | +0.15 (+0.5) | +0.31 (+0.5) |
| BetaFP | 2014 | -0.01 (-0.0) | -0.16 (-0.2) | -0.16 (-0.2) | -0.01 (-0.0) | +1.36 (+1.8) | +1.36 (+1.8) |
| BetaLiquidityPS | 2003 | +0.37 (+2.0) | -0.01 (-0.0) | -0.36 (-1.4) | +0.37 (+2.0) | -0.01 (-0.0) | -0.36 (-1.4) |
| BetaTailRisk | 2014 | +0.46 (+3.3) | +0.28 (+0.8) | +0.28 (+0.8) | +0.45 (+2.3) | +0.81 (+1.7) | +0.81 (+1.7) |
| betaVIX | 2006 | +1.09 (+3.6) | +0.20 (+0.9) | +0.27 (+0.8) | +1.09 (+3.6) | +0.20 (+0.9) | +0.27 (+0.8) |
| BidAskSpread | 1986 | +0.71 (+1.6) | +0.01 (+0.0) | -0.68 (-0.9) | +0.22 (+0.6) | -0.84 (-2.0) | -0.99 (-1.2) |
| BM | 1980 | +1.17 (+3.8) | +0.61 (+3.2) | +0.14 (+0.2) | +0.62 (+1.8) | +0.49 (+2.4) | -0.05 (-0.1) |
| BMdec | 1992 | +0.97 (+5.3) | +0.62 (+3.5) | +0.34 (+1.1) | +0.52 (+2.6) | -0.02 (-0.1) | -0.66 (-1.8) |
| BookLeverage | 1992 | +0.27 (+3.2) | -0.03 (-0.1) | -0.40 (-1.1) | -0.05 (-0.4) | -0.11 (-0.4) | -0.29 (-1.1) |
| BPEBM | 2007 | +0.22 (+2.8) | -0.03 (-0.2) | -0.10 (-0.5) | +0.20 (+2.1) | +0.28 (+1.6) | +0.41 (+1.7) |
| BrandInvest | 2014 | +0.58 (+2.0) | -0.43 (-0.9) | -0.43 (-0.9) | +0.18 (+0.7) | -0.60 (-1.1) | -0.60 (-1.1) |
| Cash | 2012 | +0.72 (+3.1) | -0.13 (-0.2) | -0.25 (-0.4) | +0.37 (+1.4) | +0.66 (+1.2) | +0.54 (+0.8) |
| CashProd | 2009 | +0.52 (+3.2) | +0.20 (+0.8) | +0.21 (+0.6) | +0.11 (+0.7) | -0.36 (-1.4) | -0.55 (-1.6) |
| CBOperProf | 2016 | +0.48 (+3.3) | +0.57 (+1.0) | +0.63 (+1.3) | +0.48 (+3.3) | +0.57 (+1.0) | +0.63 (+1.3) |
| CF | 1994 | +0.83 (+4.0) | +0.39 (+1.3) | +0.24 (+0.4) | +0.73 (+2.4) | +0.30 (+0.9) | +0.12 (+0.2) |
| cfp | 2004 | +0.36 (+2.2) | +0.93 (+3.0) | +1.12 (+2.1) | +0.32 (+1.7) | +0.38 (+1.5) | +0.23 (+0.6) |
| ChangeInRecommendation | 2004 | +1.05 (+6.6) | +0.26 (+2.7) | +0.25 (+1.5) | +0.19 (+0.9) | +0.04 (+0.3) | +0.03 (+0.2) |
| ChAssetTurnover | 2008 | +0.29 (+3.7) | +0.05 (+0.5) | +0.07 (+0.5) | +0.34 (+2.3) | -0.11 (-0.7) | -0.13 (-0.6) |
| ChEQ | 2010 | +0.56 (+4.3) | +0.41 (+2.0) | +0.48 (+1.8) | +0.29 (+2.1) | +0.14 (+0.7) | +0.13 (+0.5) |
| ChForecastAccrual | 2004 | +0.37 (+4.5) | +0.10 (+1.2) | +0.08 (+0.6) | +0.26 (+2.2) | +0.08 (+0.5) | +0.12 (+0.5) |
| ChInv | 2002 | +0.79 (+6.5) | +0.25 (+2.1) | +0.19 (+1.1) | +0.46 (+2.6) | +0.28 (+1.5) | -0.04 (-0.1) |
| ChInvIA | 1998 | +0.50 (+5.6) | +0.18 (+1.5) | -0.22 (-1.0) | +0.19 (+1.4) | +0.23 (+1.3) | +0.11 (+0.4) |
| ChNAnalyst | 2008 | +0.57 (+1.8) | +0.11 (+0.5) | +0.18 (+0.7) | +0.57 (+1.8) | +0.11 (+0.5) | +0.18 (+0.7) |
| ChNNCOA | 2008 | +0.36 (+4.5) | -0.09 (-0.9) | -0.18 (-1.3) | +0.32 (+2.5) | -0.04 (-0.2) | -0.12 (-0.6) |
| ChNWC | 2008 | +0.15 (+2.6) | +0.07 (+1.0) | +0.18 (+1.9) | +0.32 (+2.2) | +0.10 (+0.7) | +0.07 (+0.4) |
| ChTax | 2011 | +1.05 (+9.1) | +0.43 (+2.8) | +0.30 (+1.6) | +0.37 (+2.0) | -0.03 (-0.1) | +0.01 (+0.0) |
| CitationsRD | 2013 | +0.21 (+2.2) | +0.06 (+0.3) | +0.05 (+0.2) | +0.21 (+2.2) | +0.06 (+0.3) | +0.05 (+0.2) |
| CompEquIss | 2006 | +0.24 (+2.2) | +0.34 (+2.3) | +0.31 (+1.5) | +0.22 (+1.3) | +0.57 (+2.4) | +0.58 (+1.7) |
| CompositeDebtIssuance | 2008 | +0.32 (+5.6) | +0.22 (+2.2) | +0.19 (+1.3) | +0.07 (+0.8) | -0.26 (-1.4) | -0.48 (-1.7) |
| ConsRecomm | 2001 | +0.52 (+1.3) | +0.11 (+0.6) | -0.24 (-0.7) | +0.52 (+1.3) | +0.11 (+0.6) | -0.24 (-0.7) |
| ConvDebt | 2016 | +0.38 (+4.3) | +0.30 (+1.5) | +0.40 (+2.3) | +0.20 (+1.7) | -0.02 (-0.1) | +0.06 (+0.2) |
| CoskewACX | 2006 | +0.30 (+2.9) | +0.28 (+1.1) | +0.18 (+0.6) | +0.17 (+1.3) | -0.01 (-0.0) | +0.10 (+0.3) |
| Coskewness | 2000 | +0.29 (+2.3) | +0.27 (+1.7) | +0.52 (+2.2) | +0.29 (+2.3) | +0.27 (+1.7) | +0.52 (+2.2) |
| CPVolSpread | 2009 | +0.98 (+3.2) | +0.46 (+3.2) | +0.31 (+1.6) | +0.98 (+3.2) | +0.46 (+3.2) | +0.31 (+1.6) |
| CredRatDG | 2001 | +0.48 (+2.3) | +0.25 (+1.0) | +0.13 (+0.3) | +0.00 (+0.0) | +0.20 (+1.0) | +0.02 (+0.1) |
| CustomerMomentum | 2008 | +1.09 (+3.1) | +0.39 (+1.5) | +0.23 (+0.7) | +1.09 (+3.1) | +0.39 (+1.5) | +0.23 (+0.7) |
| dCPVolSpread | 2014 | +1.34 (+7.4) | +0.68 (+3.4) | +0.68 (+3.4) | +1.55 (+6.2) | +0.57 (+2.1) | +0.57 (+2.1) |
| DebtIssuance | 1999 | +0.17 (+3.0) | +0.09 (+0.8) | -0.09 (-0.5) | +0.02 (+0.1) | +0.18 (+1.5) | +0.21 (+1.2) |
| DelBreadth | 2002 | +0.68 (+3.7) | +0.30 (+1.4) | +0.55 (+1.6) | +0.13 (+0.7) | +0.11 (+0.5) | +0.41 (+1.2) |
| DelCOA | 2005 | +0.54 (+6.1) | +0.14 (+1.3) | +0.22 (+1.4) | +0.28 (+2.0) | -0.39 (-2.1) | -0.42 (-1.5) |
| DelCOL | 2005 | +0.35 (+4.4) | +0.10 (+0.9) | +0.17 (+1.0) | -0.03 (-0.2) | -0.26 (-1.3) | -0.23 (-0.8) |
| DelDRC | 2013 | +0.70 (+1.6) | +0.23 (+1.2) | +0.22 (+1.1) | +0.12 (+0.2) | +0.53 (+1.8) | +0.56 (+1.7) |
| DelEqu | 2005 | +0.47 (+3.2) | +0.29 (+1.6) | +0.35 (+1.2) | +0.13 (+0.8) | +0.18 (+1.0) | +0.16 (+0.5) |
| DelFINL | 2005 | +0.72 (+12.1) | +0.19 (+2.0) | +0.02 (+0.1) | +0.37 (+4.9) | -0.16 (-1.1) | -0.41 (-1.9) |
| DelLTI | 2005 | +0.16 (+2.5) | +0.12 (+1.7) | +0.15 (+1.3) | +0.06 (+0.9) | +0.15 (+1.4) | +0.22 (+1.4) |
| DelNetFin | 2005 | +0.55 (+8.9) | +0.02 (+0.2) | -0.10 (-0.6) | +0.26 (+2.7) | -0.05 (-0.4) | -0.13 (-0.7) |
| DivInit | 1995 | +0.58 (+5.7) | +0.26 (+1.4) | +0.34 (+1.1) | +0.60 (+2.9) | -0.14 (-0.6) | -0.45 (-1.0) |
| DivOmit | 1995 | +0.48 (+2.9) | +0.85 (+2.9) | +1.37 (+2.6) | +0.11 (+0.5) | +0.15 (+0.5) | +0.73 (+1.3) |
| DivSeason | 2013 | +0.32 (+14.1) | +0.09 (+2.1) | +0.09 (+2.0) | +0.28 (+7.2) | -0.02 (-0.2) | -0.01 (-0.1) |
| DivYieldST | 1979 | +0.57 (+5.4) | +0.63 (+9.6) | +0.25 (+1.7) | +0.36 (+2.5) | +0.32 (+3.1) | -0.13 (-0.6) |
| dNoa | 2004 | +1.05 (+9.3) | +0.20 (+1.7) | +0.08 (+0.5) | +0.55 (+4.5) | +0.11 (+0.7) | +0.05 (+0.2) |
| DolVol | 1998 | +0.76 (+2.8) | +0.39 (+1.9) | -0.04 (-0.2) | +0.14 (+0.7) | +0.01 (+0.1) | -0.66 (-2.2) |
| DownRecomm | 2001 | +0.60 (+5.3) | +0.19 (+2.9) | +0.11 (+0.9) | +0.28 (+2.1) | +0.13 (+1.5) | -0.00 (-0.0) |
| dVolCall | 2014 | +0.88 (+2.9) | +0.59 (+2.4) | +0.59 (+2.4) | +0.65 (+1.5) | +0.62 (+1.4) | +0.62 (+1.4) |
| dVolPut | 2014 | +0.38 (+1.3) | +0.23 (+1.0) | +0.23 (+1.0) | +0.44 (+1.0) | -0.14 (-0.3) | -0.14 (-0.3) |
| EarningsConsistency | 2009 | +0.21 (+2.5) | +0.36 (+2.1) | +0.57 (+2.7) | +0.25 (+1.4) | +0.48 (+1.6) | +0.53 (+1.3) |
| EarningsForecastDisparity | 2011 | +0.66 (+4.3) | +0.15 (+0.7) | +0.02 (+0.1) | +0.20 (+0.9) | +0.43 (+1.4) | +0.36 (+0.9) |
| EarningsStreak | 2012 | +1.09 (+10.6) | +0.68 (+4.3) | +0.67 (+3.6) | +0.71 (+4.5) | +0.25 (+1.3) | +0.26 (+1.2) |
| EarningsSurprise | 1984 | +1.13 (+4.9) | +0.40 (+4.9) | +0.04 (+0.2) | +0.61 (+1.9) | -0.06 (-0.5) | +0.00 (+0.0) |
| EarnSupBig | 2007 | +0.40 (+2.4) | +0.48 (+2.0) | +0.77 (+2.3) | +0.39 (+2.0) | -0.02 (-0.1) | +0.19 (+0.6) |
| EBM | 2007 | +0.30 (+4.1) | +0.21 (+1.7) | +0.34 (+1.9) | +0.31 (+3.0) | +0.07 (+0.3) | +0.20 (+0.7) |
| EntMult | 2011 | +0.86 (+5.6) | +0.28 (+0.8) | +0.26 (+0.6) | +0.52 (+2.6) | -0.57 (-1.2) | -0.71 (-1.2) |
| EP | 1977 | +0.37 (+2.1) | +0.20 (+1.7) | +0.27 (+0.8) | +0.30 (+1.3) | +0.25 (+1.8) | +0.32 (+0.9) |
| EquityDuration | 2004 | +0.60 (+3.3) | +0.01 (+0.0) | -0.10 (-0.3) | +0.60 (+3.3) | +0.01 (+0.0) | -0.10 (-0.3) |
| ExchSwitch | 1995 | +0.45 (+2.9) | +0.77 (+3.8) | +0.84 (+1.9) | +0.34 (+1.5) | +0.59 (+2.6) | +0.88 (+2.0) |
| ExclExp | 2003 | +0.25 (+2.9) | +0.05 (+0.6) | +0.09 (+0.7) | +0.07 (+0.6) | +0.06 (+0.7) | +0.06 (+0.4) |
| FEPS | 2006 | +1.48 (+3.1) | +0.64 (+1.7) | +0.89 (+1.6) | +0.92 (+2.2) | +0.78 (+2.1) | +0.85 (+1.6) |
| fgr5yrLag | 1996 | +0.85 (+2.1) | -0.00 (-0.0) | -0.16 (-0.5) | +0.49 (+1.1) | -0.14 (-0.4) | -0.37 (-0.7) |
| FirmAge | 1984 | -0.01 (-0.1) | -0.14 (-1.1) | -0.26 (-0.8) | +0.06 (+0.7) | +0.01 (+0.1) | -0.15 (-0.4) |
| FirmAgeMom | 2006 | +2.23 (+5.8) | +0.84 (+2.5) | +0.98 (+2.2) | +2.14 (+4.3) | +1.00 (+2.3) | +1.48 (+2.5) |
| ForecastDispersion | 2002 | +0.72 (+3.5) | +0.33 (+1.3) | +0.55 (+1.4) | +0.30 (+1.2) | +0.28 (+0.9) | +0.40 (+0.9) |
| FR | 2006 | +0.30 (+1.7) | -0.44 (-1.5) | -0.32 (-0.8) | +0.18 (+0.7) | -0.31 (-1.2) | -0.07 (-0.2) |
| Frontier | 2009 | +2.08 (+6.2) | +0.49 (+1.1) | +0.35 (+0.5) | +0.33 (+0.8) | -0.25 (-0.5) | -0.68 (-1.1) |
| Governance | 2003 | +0.52 (+2.1) | -0.54 (-1.7) | — | +0.52 (+2.1) | -0.54 (-1.7) | — |
| GP | 2013 | +0.30 (+2.4) | +1.02 (+2.7) | +1.11 (+2.7) | +0.30 (+2.4) | +1.02 (+2.7) | +1.11 (+2.7) |
| GrAdExp | 2014 | +0.41 (+3.8) | +0.11 (+0.5) | +0.11 (+0.5) | +0.43 (+2.1) | -0.01 (-0.0) | -0.01 (-0.0) |
| grcapx | 2006 | +0.52 (+5.2) | +0.19 (+1.5) | +0.30 (+1.6) | +0.26 (+2.2) | +0.10 (+0.4) | +0.31 (+0.8) |
| grcapx3y | 2006 | +0.59 (+4.7) | +0.05 (+0.4) | +0.15 (+0.7) | +0.20 (+1.6) | -0.01 (-0.0) | -0.03 (-0.1) |
| GrLTNOA | 2003 | +0.37 (+3.7) | -0.05 (-0.5) | -0.19 (-1.4) | +0.19 (+1.2) | -0.18 (-1.0) | -0.38 (-1.2) |
| GrSaleToGrInv | 1998 | +0.32 (+3.4) | -0.03 (-0.3) | -0.24 (-1.6) | +0.34 (+2.0) | +0.03 (+0.2) | -0.01 (-0.0) |
| GrSaleToGrOverhead | 1998 | -0.06 (-0.4) | -0.13 (-1.2) | -0.08 (-0.4) | -0.01 (-0.1) | -0.08 (-0.5) | -0.16 (-0.6) |
| Herf | 2006 | +0.21 (+2.3) | -0.31 (-1.7) | -0.42 (-1.4) | +0.31 (+1.9) | +0.02 (+0.1) | +0.14 (+0.3) |
| HerfAsset | 2006 | +0.18 (+1.7) | -0.38 (-2.0) | -0.31 (-1.0) | +0.25 (+1.5) | +0.02 (+0.1) | +0.15 (+0.4) |
| HerfBE | 2006 | +0.22 (+2.1) | -0.34 (-1.9) | -0.32 (-1.1) | +0.28 (+1.8) | -0.00 (-0.0) | +0.20 (+0.5) |
| High52 | 2004 | +0.47 (+1.9) | +0.20 (+0.6) | +0.36 (+0.8) | +0.30 (+2.0) | +0.02 (+0.1) | +0.07 (+0.2) |
| hire | 2014 | +0.51 (+5.6) | +0.19 (+0.8) | +0.19 (+0.8) | +0.15 (+1.3) | -0.50 (-1.4) | -0.50 (-1.4) |
| IdioVol3F | 2006 | +0.97 (+3.2) | +0.27 (+0.7) | +0.25 (+0.5) | +0.97 (+3.2) | +0.27 (+0.7) | +0.25 (+0.5) |
| IdioVolAHT | 2003 | +0.89 (+2.5) | +0.22 (+0.6) | +0.21 (+0.3) | +0.89 (+2.5) | +0.22 (+0.6) | +0.21 (+0.3) |
| Illiquidity | 2002 | +0.39 (+2.8) | +0.04 (+0.4) | -0.10 (-0.6) | +0.38 (+2.4) | +0.08 (+0.5) | -0.27 (-1.2) |
| IndIPO | 1991 | +0.67 (+2.4) | +0.44 (+2.5) | +0.30 (+1.1) | +0.31 (+0.8) | +0.21 (+0.9) | +0.56 (+1.4) |
| IndMom | 1999 | +0.26 (+2.4) | +0.31 (+1.3) | +0.05 (+0.2) | +0.01 (+0.1) | +0.10 (+0.4) | -0.15 (-0.5) |
| IndRetBig | 2007 | +2.33 (+9.5) | +0.59 (+2.3) | +0.21 (+0.7) | +2.29 (+8.8) | +0.24 (+0.9) | -0.07 (-0.2) |
| IntanBM | 2006 | +0.39 (+2.3) | +0.10 (+0.4) | +0.18 (+0.5) | +0.45 (+2.0) | -0.48 (-1.4) | -0.48 (-1.2) |
| IntanCFP | 2006 | +0.39 (+2.3) | +0.30 (+1.1) | +0.30 (+0.8) | +0.44 (+2.1) | -0.39 (-1.1) | -0.61 (-1.3) |
| IntanEP | 2006 | +0.32 (+2.4) | +0.23 (+1.1) | +0.30 (+1.0) | +0.24 (+1.3) | -0.23 (-0.7) | -0.31 (-0.7) |
| IntanSP | 2006 | +0.56 (+2.5) | +0.18 (+0.6) | +0.18 (+0.4) | +0.33 (+1.3) | -0.46 (-1.1) | -0.40 (-0.7) |
| IntMom | 2012 | +1.24 (+5.9) | +0.68 (+1.1) | +0.74 (+1.0) | +1.24 (+5.9) | +0.68 (+1.1) | +0.74 (+1.0) |
| Investment | 2004 | +0.26 (+2.3) | +0.07 (+0.4) | +0.11 (+0.4) | +0.26 (+2.3) | +0.07 (+0.4) | +0.11 (+0.4) |
| InvestPPEInv | 2008 | +0.80 (+7.9) | +0.22 (+2.0) | +0.04 (+0.3) | +0.41 (+3.4) | -0.30 (-1.7) | -0.50 (-2.1) |
| InvGrowth | 2012 | +0.86 (+7.5) | +0.45 (+1.9) | +0.55 (+2.1) | +0.60 (+3.2) | -0.08 (-0.2) | +0.24 (+0.6) |
| IO_ShortInterest | 2005 | +2.23 (+3.1) | +5.79 (+3.1) | +8.43 (+2.5) | +0.64 (+0.8) | +2.60 (+2.2) | +3.31 (+1.7) |
| iomom_cust | 2010 | +0.42 (+1.7) | +0.05 (+0.2) | -0.18 (-0.5) | +0.24 (+1.0) | +0.26 (+1.2) | +0.20 (+0.8) |
| iomom_supp | 2010 | +0.66 (+3.1) | +0.05 (+0.2) | -0.13 (-0.4) | +0.42 (+1.6) | +0.37 (+1.4) | +0.33 (+1.0) |
| Leverage | 1988 | +0.36 (+2.6) | +0.32 (+1.3) | +0.33 (+0.7) | +0.29 (+1.9) | -0.05 (-0.2) | -0.31 (-0.6) |
| LRreversal | 1985 | +0.78 (+3.0) | +0.48 (+2.0) | -0.27 (-0.6) | +0.39 (+1.7) | +0.25 (+1.0) | +0.12 (+0.2) |
| MaxRet | 2011 | +0.89 (+2.7) | +0.20 (+0.4) | +0.37 (+0.6) | +0.89 (+2.7) | +0.20 (+0.4) | +0.37 (+0.6) |
| MeanRankRevGrowth | 1994 | +0.54 (+3.9) | +0.02 (+0.2) | +0.02 (+0.1) | +0.47 (+2.8) | +0.05 (+0.4) | -0.03 (-0.1) |
| Mom12m | 1993 | +1.34 (+4.5) | +0.85 (+1.9) | +1.34 (+1.9) | +2.21 (+6.3) | +1.21 (+2.4) | +1.63 (+1.8) |
| Mom12mOffSeason | 2008 | +1.35 (+4.5) | +0.88 (+1.4) | +1.65 (+2.1) | +1.39 (+4.1) | +0.84 (+1.3) | +1.62 (+2.0) |
| Mom6m | 1993 | +1.02 (+3.6) | +1.04 (+2.4) | +1.13 (+1.8) | +1.53 (+5.0) | +1.37 (+3.0) | +2.10 (+2.9) |
| Mom6mJunk | 2007 | +2.09 (+4.2) | +0.45 (+0.9) | +1.03 (+1.6) | +1.51 (+2.5) | +1.08 (+1.8) | +2.07 (+2.8) |
| MomOffSeason | 2008 | +1.23 (+4.9) | +0.42 (+1.0) | +0.44 (+0.8) | +0.83 (+3.4) | +0.31 (+0.7) | +0.35 (+0.6) |
| MomOffSeason06YrPlus | 2008 | +0.60 (+4.8) | +0.53 (+2.1) | +0.15 (+0.4) | +0.51 (+2.6) | +0.51 (+1.7) | +0.45 (+1.1) |
| MomOffSeason11YrPlus | 2008 | +0.18 (+1.6) | +0.04 (+0.2) | -0.12 (-0.4) | +0.30 (+1.6) | -0.09 (-0.4) | -0.29 (-0.9) |
| MomOffSeason16YrPlus | 2008 | +0.35 (+2.9) | +0.22 (+1.0) | +0.30 (+1.0) | +0.30 (+1.8) | -0.06 (-0.2) | -0.08 (-0.2) |
| MomRev | 2006 | +1.17 (+4.4) | +0.07 (+0.2) | +0.62 (+1.0) | +1.17 (+3.9) | +0.57 (+1.0) | +1.90 (+2.3) |
| MomSeason | 2008 | +0.81 (+5.8) | -0.06 (-0.2) | -0.09 (-0.2) | +0.93 (+4.9) | -0.63 (-1.8) | -0.45 (-0.9) |
| MomSeason06YrPlus | 2008 | +0.75 (+6.2) | +0.08 (+0.3) | -0.32 (-0.9) | +0.87 (+4.9) | +0.24 (+0.9) | -0.05 (-0.2) |
| MomSeason11YrPlus | 2008 | +0.75 (+6.9) | +0.16 (+0.8) | +0.06 (+0.2) | +0.76 (+4.4) | -0.00 (-0.0) | -0.13 (-0.4) |
| MomSeason16YrPlus | 2008 | +0.59 (+5.0) | +0.46 (+2.3) | +0.39 (+1.5) | +0.42 (+2.4) | +0.73 (+3.0) | +0.46 (+1.5) |
| MomSeasonShort | 2008 | +1.36 (+8.6) | +0.12 (+0.4) | +0.18 (+0.4) | +0.98 (+4.1) | -0.17 (-0.4) | -0.25 (-0.5) |
| MomVol | 2000 | +1.59 (+5.0) | +1.14 (+1.9) | +2.49 (+2.7) | +1.16 (+3.6) | +0.83 (+1.4) | +1.67 (+2.0) |
| MRreversal | 1985 | +0.39 (+2.1) | +0.31 (+1.9) | -0.06 (-0.2) | +0.39 (+2.1) | +0.15 (+0.8) | +0.05 (+0.1) |
| MS | 2005 | +1.10 (+5.0) | +0.55 (+2.7) | +0.41 (+1.3) | +0.73 (+2.5) | +0.46 (+2.1) | +0.79 (+2.4) |
| NetDebtFinance | 2006 | +0.72 (+7.7) | +0.36 (+2.7) | +0.21 (+1.0) | +0.18 (+1.2) | -0.41 (-2.1) | -0.77 (-2.5) |
| NetDebtPrice | 2007 | +0.55 (+3.8) | +0.10 (+0.3) | +0.10 (+0.2) | +0.26 (+1.4) | +0.11 (+0.3) | +0.11 (+0.2) |
| NetEquityFinance | 2006 | +0.71 (+3.0) | +1.02 (+3.1) | +1.24 (+2.3) | +0.48 (+1.9) | +0.38 (+1.2) | +0.43 (+0.9) |
| NetPayoutYield | 2007 | +0.88 (+2.6) | +1.49 (+3.8) | +1.76 (+3.0) | +0.75 (+2.2) | +0.80 (+1.8) | +0.97 (+1.4) |
| NOA | 2004 | +1.08 (+7.6) | +0.02 (+0.1) | -0.10 (-0.3) | +0.84 (+5.3) | +0.28 (+1.2) | +0.52 (+1.5) |
| NumEarnIncrease | 2012 | +0.50 (+6.5) | +0.31 (+2.3) | +0.30 (+1.9) | +0.12 (+1.2) | +0.10 (+0.7) | +0.15 (+0.8) |
| OperProf | 2006 | +0.73 (+3.0) | +0.45 (+2.4) | +0.40 (+1.3) | +0.44 (+1.7) | +0.31 (+1.7) | +0.47 (+2.0) |
| OperProfRD | 2016 | +0.32 (+1.9) | +0.98 (+1.7) | +1.01 (+2.0) | +0.32 (+1.9) | +0.98 (+1.7) | +1.01 (+2.0) |
| OPLeverage | 2011 | +0.35 (+2.5) | -0.03 (-0.1) | -0.11 (-0.3) | +0.30 (+2.3) | +0.28 (+1.2) | +0.30 (+1.1) |
| OptionVolume1 | 2012 | +0.75 (+2.1) | +0.10 (+0.4) | +0.11 (+0.4) | +0.39 (+1.2) | -0.28 (-1.4) | -0.37 (-1.6) |
| OptionVolume2 | 2012 | +0.57 (+2.3) | -0.19 (-1.4) | -0.20 (-1.3) | +0.51 (+2.7) | -0.04 (-0.3) | -0.06 (-0.4) |
| OrderBacklog | 2003 | +0.50 (+3.3) | -0.30 (-2.0) | -0.47 (-2.1) | +0.33 (+1.3) | -0.16 (-0.8) | +0.04 (+0.1) |
| OrderBacklogChg | 2007 | +0.36 (+2.4) | +0.66 (+2.6) | +1.06 (+3.0) | -0.17 (-0.6) | +0.60 (+1.8) | +0.71 (+1.5) |
| OrgCap | 2013 | +0.41 (+2.9) | +0.18 (+0.9) | +0.20 (+0.9) | +0.41 (+2.9) | +0.18 (+0.9) | +0.20 (+0.9) |
| OScore | 1998 | +0.99 (+3.3) | +1.11 (+2.9) | +1.92 (+3.0) | +1.38 (+3.5) | +0.01 (+0.0) | +0.35 (+0.7) |
| PatentsRD | 2013 | +0.46 (+2.2) | -5.22 (-2.0) | -5.22 (-2.0) | +0.46 (+2.2) | -5.22 (-2.0) | -5.22 (-2.0) |
| PayoutYield | 2007 | +0.43 (+2.3) | +0.20 (+0.9) | +0.17 (+0.5) | +0.24 (+0.8) | +0.63 (+2.2) | +0.64 (+1.6) |
| PctAcc | 2011 | +0.45 (+3.5) | +0.12 (+1.0) | +0.13 (+0.9) | +0.06 (+0.3) | +0.17 (+0.8) | +0.27 (+1.0) |
| PctTotAcc | 2011 | +0.50 (+4.7) | +0.39 (+2.8) | +0.39 (+2.2) | +0.18 (+0.8) | +0.17 (+0.8) | +0.21 (+0.9) |
| PredictedFE | 1998 | +0.41 (+1.3) | -0.04 (-0.2) | -0.13 (-0.5) | +0.18 (+0.6) | -0.26 (-0.9) | -0.85 (-2.0) |
| Price | 1973 | +1.43 (+3.1) | +0.33 (+1.1) | -0.54 (-0.8) | +0.87 (+2.3) | -0.32 (-1.0) | -0.92 (-1.3) |
| PriceDelayRsq | 2005 | +0.49 (+2.7) | -0.25 (-1.1) | -0.51 (-1.5) | -0.27 (-1.4) | -0.81 (-3.0) | -1.10 (-2.9) |
| PriceDelaySlope | 2005 | +0.16 (+1.9) | -0.11 (-0.6) | -0.34 (-1.4) | -0.04 (-0.3) | -0.25 (-1.1) | -0.39 (-1.2) |
| PriceDelayTstat | 2005 | +0.16 (+1.9) | -0.11 (-0.6) | -0.33 (-1.4) | -0.03 (-0.2) | -0.26 (-1.1) | -0.40 (-1.3) |
| ProbInformedTrading | 2002 | +1.66 (+2.4) | +0.37 (+0.4) | — | +1.39 (+2.3) | +0.02 (+0.0) | — |
| PS | 2000 | +1.05 (+3.6) | +0.59 (+1.2) | -0.53 (-0.9) | +1.05 (+3.6) | +0.59 (+1.2) | -0.53 (-0.9) |
| RD | 2001 | +1.01 (+5.9) | +0.22 (+0.7) | -0.30 (-0.6) | -0.18 (-0.8) | +0.03 (+0.1) | -0.15 (-0.3) |
| RDAbility | 2013 | +0.31 (+1.7) | +0.21 (+0.8) | +0.20 (+0.7) | +0.35 (+1.1) | -0.32 (-0.7) | -0.37 (-0.7) |
| RDcap | 2011 | +0.43 (+2.1) | -0.19 (-0.6) | -0.24 (-0.6) | +0.43 (+2.1) | -0.19 (-0.6) | -0.24 (-0.6) |
| RDIPO | 2006 | +0.90 (+2.9) | +0.70 (+2.9) | +0.85 (+2.3) | +0.55 (+1.5) | +0.36 (+1.2) | +0.51 (+1.3) |
| RDS | 2011 | +0.49 (+3.9) | -0.10 (-0.7) | -0.19 (-1.0) | +0.17 (+1.9) | -0.09 (-0.7) | -0.15 (-1.0) |
| realestate | 2010 | +0.30 (+1.9) | +0.14 (+0.6) | +0.08 (+0.3) | +0.30 (+1.9) | +0.14 (+0.6) | +0.08 (+0.3) |
| RealizedVol | 2006 | +0.85 (+2.6) | +0.05 (+0.1) | -0.20 (-0.3) | +0.85 (+2.6) | +0.05 (+0.1) | -0.20 (-0.3) |
| Recomm_ShortInterest | 2011 | +0.82 (+2.9) | +0.45 (+1.1) | +0.47 (+1.0) | +0.25 (+0.5) | +0.06 (+0.1) | +0.05 (+0.1) |
| ResidualMomentum | 2011 | +0.95 (+8.2) | +0.33 (+1.3) | +0.35 (+1.1) | +0.73 (+5.5) | -0.02 (-0.1) | +0.01 (+0.0) |
| retConglomerate | 2012 | +1.37 (+6.7) | +0.30 (+1.1) | +0.20 (+0.6) | +0.35 (+1.3) | +0.15 (+0.4) | -0.02 (-0.1) |
| ReturnSkew | 2015 | +0.41 (+5.3) | +0.28 (+1.3) | +0.30 (+1.5) | -0.11 (-1.4) | +0.20 (+0.9) | +0.18 (+0.9) |
| ReturnSkew3F | 2015 | +0.29 (+4.4) | +0.21 (+1.2) | +0.20 (+1.2) | -0.13 (-2.0) | +0.03 (+0.2) | -0.00 (-0.0) |
| REV6 | 1996 | +1.13 (+8.9) | +0.55 (+3.1) | +0.59 (+2.0) | +0.38 (+2.3) | +0.43 (+1.8) | +0.90 (+2.0) |
| RevenueSurprise | 2006 | +0.73 (+5.7) | +0.37 (+2.8) | +0.33 (+1.6) | -0.03 (-0.2) | +0.22 (+1.5) | +0.18 (+0.8) |
| RIO_Disp | 2005 | +0.61 (+2.6) | +0.39 (+1.9) | +0.41 (+1.6) | +0.38 (+1.3) | +0.13 (+0.5) | -0.07 (-0.2) |
| RIO_MB | 2005 | +0.88 (+3.7) | +0.08 (+0.4) | +0.01 (+0.0) | +0.39 (+1.2) | -0.46 (-1.8) | -0.89 (-2.3) |
| RIO_Turnover | 2005 | +0.64 (+2.8) | +0.43 (+1.9) | +0.54 (+1.7) | +0.05 (+0.2) | -0.75 (-2.2) | -1.49 (-2.6) |
| RIO_Volatility | 2005 | +1.00 (+4.1) | +0.92 (+3.2) | +1.14 (+3.2) | +0.05 (+0.1) | -0.49 (-1.1) | -1.20 (-1.6) |
| RIVolSpread | 2009 | +1.05 (+2.2) | +0.16 (+0.6) | +0.09 (+0.2) | +1.05 (+2.2) | +0.16 (+0.6) | +0.09 (+0.2) |
| roaq | 2010 | +1.59 (+5.6) | +1.29 (+2.9) | +1.52 (+2.6) | +0.41 (+1.2) | +0.68 (+1.4) | +0.85 (+1.4) |
| RoE | 1996 | +0.32 (+2.8) | +0.38 (+2.1) | +0.37 (+1.4) | -0.01 (-0.1) | +0.23 (+1.2) | +0.25 (+1.0) |
| sfe | 2001 | +0.83 (+2.7) | +0.74 (+1.9) | +0.81 (+1.2) | +1.12 (+3.4) | +0.06 (+0.1) | -0.42 (-0.5) |
| ShareIss1Y | 2008 | +0.71 (+4.4) | +0.85 (+2.6) | +1.22 (+2.6) | +0.56 (+5.1) | +0.30 (+1.4) | +0.43 (+1.5) |
| ShareIss5Y | 2006 | +0.54 (+3.5) | +0.88 (+3.3) | +1.14 (+2.8) | +0.55 (+4.6) | +0.49 (+3.1) | +0.74 (+3.3) |
| ShareRepurchase | 1995 | +0.31 (+3.9) | +0.28 (+2.4) | +0.51 (+2.2) | +0.27 (+2.6) | +0.14 (+1.2) | +0.18 (+0.9) |
| ShareVol | 1998 | +0.74 (+3.9) | +0.05 (+0.3) | -0.11 (-0.3) | +0.23 (+0.9) | -0.08 (-0.3) | -0.06 (-0.2) |
| ShortInterest | 2001 | +0.83 (+5.3) | +0.98 (+4.0) | +0.96 (+2.5) | +0.15 (+0.7) | +0.18 (+0.7) | +0.26 (+0.6) |
| sinAlgo | 2009 | +0.26 (+1.6) | -0.08 (-0.3) | -0.08 (-0.2) | +0.37 (+2.2) | -0.04 (-0.2) | -0.20 (-0.7) |
| Size | 1981 | +0.50 (+2.6) | +0.05 (+0.3) | -0.34 (-1.1) | +0.31 (+1.7) | -0.15 (-0.9) | -0.61 (-1.7) |
| skew1 | 2010 | +0.64 (+3.1) | +0.18 (+1.2) | +0.16 (+0.8) | +0.54 (+1.8) | -0.07 (-0.3) | -0.05 (-0.2) |
| SmileSlope | 2011 | +1.82 (+8.1) | +0.85 (+5.2) | +0.88 (+4.2) | +1.37 (+4.7) | +0.86 (+5.1) | +0.79 (+3.9) |
| SP | 1996 | +0.71 (+2.9) | +0.88 (+3.2) | +0.85 (+1.8) | +0.34 (+1.2) | +0.23 (+0.9) | -0.37 (-0.8) |
| Spinoff | 1993 | +0.40 (+2.2) | -0.03 (-0.2) | -0.60 (-2.1) | +0.40 (+2.2) | -0.03 (-0.2) | -0.60 (-2.1) |
| std_turn | 2001 | +0.77 (+3.3) | -0.03 (-0.1) | +0.27 (+0.4) | +0.77 (+3.3) | -0.29 (-0.6) | -0.06 (-0.1) |
| STreversal | 1990 | +2.97 (+14.2) | +1.61 (+4.2) | +0.72 (+1.2) | +1.23 (+6.3) | -0.05 (-0.1) | -0.64 (-0.9) |
| SurpriseRD | 2004 | +0.29 (+3.0) | -0.03 (-0.3) | -0.03 (-0.2) | +0.17 (+1.8) | +0.14 (+1.2) | +0.35 (+1.9) |
| tang | 2009 | +0.71 (+3.7) | -0.10 (-0.3) | -0.08 (-0.2) | -0.13 (-0.8) | +0.13 (+0.4) | +0.05 (+0.1) |
| Tax | 2004 | +0.44 (+3.5) | +0.37 (+3.2) | +0.35 (+2.0) | +0.22 (+1.4) | +0.40 (+3.0) | +0.71 (+3.8) |
| TotalAccruals | 2005 | +0.28 (+2.6) | +0.02 (+0.1) | -0.06 (-0.2) | +0.19 (+1.7) | +0.05 (+0.3) | -0.03 (-0.1) |
| TrendFactor | 2016 | +1.73 (+13.4) | +0.18 (+0.5) | +0.13 (+0.4) | +1.16 (+7.9) | -0.49 (-1.1) | -0.22 (-0.6) |
| UpRecomm | 2001 | +0.65 (+5.1) | +0.18 (+2.6) | +0.19 (+1.4) | +0.45 (+3.1) | +0.09 (+1.0) | +0.05 (+0.3) |
| VarCF | 1996 | -0.55 (-1.9) | -0.06 (-0.2) | +0.74 (+1.3) | -0.21 (-0.9) | +0.01 (+0.0) | +0.45 (+0.9) |
| VolMkt | 1996 | +0.44 (+1.6) | +0.37 (+1.4) | +0.27 (+1.2) | -0.00 (-0.0) | -0.07 (-0.2) | -0.42 (-1.2) |
| VolSD | 2001 | +0.38 (+2.8) | +0.01 (+0.0) | -0.12 (-0.3) | +0.34 (+2.8) | +0.13 (+0.9) | -0.00 (-0.0) |
| VolumeTrend | 1996 | +0.53 (+2.9) | +0.69 (+5.1) | +0.47 (+2.8) | +0.02 (+0.1) | +0.40 (+2.3) | +0.35 (+1.3) |
| XFIN | 2006 | +1.10 (+4.8) | +1.23 (+3.6) | +1.67 (+3.1) | +0.74 (+2.4) | +0.52 (+1.4) | +0.67 (+1.2) |
| zerotrade12M | 2006 | +0.63 (+3.4) | +0.18 (+0.4) | -0.00 (-0.0) | +0.43 (+2.1) | +0.01 (+0.0) | -0.26 (-0.6) |
| zerotrade1M | 2006 | +0.63 (+3.8) | +0.26 (+0.6) | +0.12 (+0.2) | +0.35 (+1.7) | +0.02 (+0.1) | -0.17 (-0.4) |
| zerotrade6M | 2006 | +0.63 (+3.4) | +0.26 (+0.6) | -0.02 (-0.0) | +0.43 (+2.1) | +0.01 (+0.0) | -0.24 (-0.5) |
