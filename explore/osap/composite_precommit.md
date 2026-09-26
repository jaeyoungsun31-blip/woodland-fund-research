# Pre-commitment — OSAP composite-signal test

Written 2026-09-26, **before any composite return was computed**. The
per-predictor triage (`0d06055`, [triage_report.md](triage_report.md)) has
already been seen. That is why this test selects nothing: every one of the 212
predictors enters, whatever its triage result. Deviations will be recorded as
dated additions below, never as edits. This is meta-research, not a harness
study, and makes no performance claim.

## Sign convention (verified before this document)

Every long-short (LS) series is already signed so that a positive return is
the direction the original paper predicted. **No sign is flipped.**

- **Stock-level signals.** The [data page](https://www.openassetpricing.com/data/)
  describes them as "signed so future mean returns increase in
  characteristics".
- **Portfolios.** In the v2.0.0 portfolio code
  ([`Portfolios/Code/01_PortfolioFunction.R`](https://github.com/OpenSourceAP/CrossSection/blob/v2.0.0/Portfolios/Code/01_PortfolioFunction.R)):
  - `import_signal` multiplies each signal by `Sign`.
  - The long leg is the highest portfolio (`longportname = 'max'`) and the
    short leg the lowest (`'min'`).
  - `ret = retL + retS` with `retS = -mean(ret)`.
- **Where `Sign` comes from.** `loop_over_strategies` in
  [`00_SettingsAndTools.R`](https://github.com/OpenSourceAP/CrossSection/blob/v2.0.0/Portfolios/Code/00_SettingsAndTools.R)
  passes `Sign = strategylist$Sign[i]` from `SignalDoc.csv`. That field is
  +1 for 113 predictors and −1 for 99.
- **The VW file uses the same signs.** `PredictorAltPorts_LiqScreen_VWforce`
  is produced in
  [`30_PredictorAltPorts.R`](https://github.com/OpenSourceAP/CrossSection/blob/v2.0.0/Portfolios/Code/30_PredictorAltPorts.R)
  by the same loop over the same `strategylist0`, with `sweight = "VW"`.
- **Negative in-sample means are left as they are.** Four OP series and 17 VW
  series have a non-positive in-sample mean in the triage. That is a failure
  to replicate, not a sign error. Flipping them would be selection on
  outcomes.

## Data

The files and hashes are in [sources.json](sources.json): OP from
`PredictorLSretWide.csv`, and VW from the `LS` leg of
`PredictorAltPorts_LiqScreen_VWforce.csv`. The predictor set is all 212 rows
with `Cat.Signal == Predictor` in `SignalDoc.csv`. Returns are in percent per
month.

## Composites

- **All-predictor composite, month m:** the equal-weighted mean of every
  predictor's LS return that is available (non-missing) in m. It is computed
  separately for **VW (primary)** and **OP (comparison)**.
- **Post-publication composite, month m:** the same, restricted to predictors
  whose `SignalDoc` publication `Year` is earlier than the calendar year of m.
  A predictor therefore counts only from January of `Year + 1`.
- **Minimum breadth:** a composite month exists only if at least **10**
  predictors are available. Months with fewer are missing, not zero. The
  per-month count of predictors is reported.
- **No other weighting, filter, volatility scaling or selection.**

## Windows

- **Full sample:** every month the composite exists, through 2024-12.
- **Post-2000:** 2000-01 to 2024-12.
- **2015–2024:** 2015-01 to 2024-12.

## Statistics (each composite × window)

- **Mean:** mean monthly return.
- **Newey–West t:** Bartlett kernel, lag 6, on the mean.
- **Sharpe:** annualized as `mean / sd × √12`. LS returns are self-financing
  spreads, so no risk-free rate is subtracted.
- **Worst 12-month return:** the minimum compounded return over any 12
  consecutive composite months, `Π(1 + r/100) − 1`. The task called this
  "worst 12-month drawdown", and this is how it is defined here.
- **Months and breadth:** number of months, and the minimum and median
  number of predictors per month.

**Primary statistic, fixed now:** the **VW post-publication composite,
2015–2024**, mean with its Newey–West t. It is described as distinguishable
from zero only if t ≥ 2. Every other cell is secondary.

## By category (descriptive)

The same four composites (VW and OP, each all-predictor and
post-publication) are computed within each `Cat.Data` category, with the same
windows and statistics. They are **descriptive only**. No category is
selected or recommended, and categories cannot rescue or overturn the
primary.

## Diversification check (2015–2024, VW)

- **Sample:** VW LS returns of predictors with all 120 months present in
  2015–2024. Predictors with gaps are excluded from this check only, and are
  listed.
- **Average pairwise correlation:** the mean of the off-diagonal Pearson
  correlations.
- **Effective number of independent signals:**
  - Primary: the participation ratio `N_eff = (Σλ)² / Σλ²` of the
    correlation-matrix eigenvalues λ.
  - Also reported: the number of eigenvalues needed for 90% of total
    variance, and the variance share of the first eigenvalue.

## Power note

For the VW post-publication composite in 2015–2024, the minimum monthly mean
detectable at t = 2 is `2 × SE`. It is reported with the Newey–West (lag 6) SE
and with the iid SE `sd / √n`.

## Limits stated in advance

- All returns are gross of trading costs.
- A composite of about 200 LS portfolios implies very high turnover. This test
  measures whether the information survives, not whether a strategy is
  tradable.
- There is no out-of-sample period. 2015–2024 is inside the data the triage
  already examined.
