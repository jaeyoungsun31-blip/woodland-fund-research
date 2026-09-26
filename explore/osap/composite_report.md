# OSAP composite-signal test

2026-09-26. The test was run exactly as pre-committed in
[composite_precommit.md](composite_precommit.md) (`fe87084`), which was
committed before any composite was computed. Code: [composite.py](composite.py),
which reuses the loader in [triage.py](triage.py). Pre-run suite:
`619 passed, 1 skipped in 84.99s (0:01:24)`. This is meta-research, not a
harness study, and makes no performance claim.

**Returns are gross of all trading costs.** An equal-weighted composite of
about 200 long-short portfolios, most rebalanced monthly or annually,
implies very high turnover. This test measures **whether the published
information still shows up in returns, not whether any strategy is
tradable.**

## Primary result

**VW post-publication composite, 2015–2024:**

| | |
|---|---|
| Mean | **+0.103% per month** |
| Newey–West t (lag 6) | **1.34** |
| Annualized Sharpe | 0.48 |
| Worst 12-month return | −4.0% |
| Months | 120 |
| Breadth | 195–207 predictors per month |

The pre-committed reading is that the result is distinguishable from zero
only if t ≥ 2. **At t = 1.34 it is not.** Value-weighted, the average
published predictor carried no statistically detectable information in
2015–2024, even before any trading cost.

## Sign convention

Verified before the precommit, and documented there with links to the
v2.0.0 code. OSAP multiplies each signal by `SignalDoc`'s `Sign` (+1 for 113
predictors, −1 for 99). The long leg is the top portfolio and the short leg
the bottom, and `LS = long − short`. The VW file comes from the same loop
with value weighting forced. **No series was flipped.** The 4 OP and 17 VW
series with non-positive in-sample means were left as they are.

## All composites

Breadth is the number of predictors available per month; a composite needs
at least 10. The post-publication full sample starts in 1986-01, the first
month with 10 predictors already published. The worst 12-month figure is the
minimum compounded return over any 12 consecutive months.

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1926-03–2024-12) | 1186 | 11/163 | +0.315 | +10.68 | 1.10 | -12.8% |
| VW all | post2000 (2000-01–2024-12) | 300 | 195/208 | +0.239 | +3.50 | 0.89 | -4.0% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 195/207 | +0.105 | +1.36 | 0.49 | -4.0% |
| VW post_pub | full (1986-01–2024-12) | 468 | 11/84 | +0.111 | +1.48 | 0.30 | -21.5% |
| VW post_pub | post2000 (2000-01–2024-12) | 300 | 48/180 | +0.221 | +3.00 | 0.77 | -5.0% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 195/207 | +0.103 | +1.34 | 0.48 | -4.0% |
| OP all | full (1926-03–2024-12) | 1186 | 11/163 | +0.510 | +14.56 | 1.54 | -4.4% |
| OP all | post2000 (2000-01–2024-12) | 300 | 195/208 | +0.406 | +6.24 | 1.50 | -1.9% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 195/207 | +0.293 | +3.61 | 1.38 | -1.9% |
| OP post_pub | full (1986-01–2024-12) | 468 | 11/84 | +0.409 | +5.91 | 1.01 | -7.8% |
| OP post_pub | post2000 (2000-01–2024-12) | 300 | 48/180 | +0.377 | +5.81 | 1.26 | -3.5% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 195/207 | +0.292 | +3.61 | 1.39 | -1.9% |

**Reading the table (secondary; the primary is above).**

- **The information fades toward the present.** The VW post-publication
  composite has t = 3.00 over 2000–2024 but only 1.34 over 2015–2024. That
  pattern is consistent with the information being absorbed by the market
  after 2014, but it was not tested as such.
- **Equal-weighted versions stay strong.** OP post-publication gives
  +0.29% per month (t = 3.61) in 2015–2024, about three times the VW figure.
  As in the triage, the equal-weighted small-stock legs carry most of what
  survives, and they are the most expensive legs to trade.
- **All-predictor and post-publication composites nearly coincide in
  2015–2024.** Only 6 predictors were published in 2015–2016, so the two
  differ by at most 6 predictors in any month of that window.
  - **Post-2000 is different.** Only 48 of the 212 predictors were published
    before 2000, so the post-publication composite starts that window with
    48 predictors and grows to about 200.
  - **Its 2000–2024 t of 3.00 is therefore the cleaner out-of-publication
    reading.** It covers the whole period, but its composition changes over
    it.

## Diversification check (VW, 2015–2024)

| | |
|---|---|
| Predictors with all 120 months | 195 (17 with gaps excluded from this check only) |
| Mean pairwise correlation | 0.026 |
| Median pairwise correlation | 0.017 |
| Mean absolute pairwise correlation | 0.200 |
| First eigenvalue's share of variance | 18.7% |
| Eigenvalues needed for 90% of variance | 44 |
| **Effective number of independent signals** | **13.4** |

- **Method.** The effective number is the participation ratio
  `(Σλ)² / Σλ²` of the eigenvalues of the 195 × 195 correlation matrix. It
  measures how evenly variance spreads across eigen-directions. One
  dominant factor gives 1, and fully independent signals give 195. It is
  conservative: 44 eigenvalues are needed for 90% of variance.
- **Why the correlations look small.** The mean pairwise correlation is
  near zero because correlations of both signs cancel. The absolute value,
  0.20, and the 18.7% first eigenvalue show real common structure. Either
  way, the ~200 series behave like about a dozen independent bets, not 200.
- **Excluded from this check only:** Activism1, Activism2, CPVolSpread,
  dCPVolSpread, dVolCall, dVolPut, Governance, OptionVolume1, OptionVolume2,
  PatentsRD, PriceDelayRsq, PriceDelaySlope, PriceDelayTstat,
  ProbInformedTrading, RIVolSpread, skew1 and SmileSlope.

## Power note (VW post-publication composite, 2015–2024)

- **Observed volatility:** a monthly SD of 0.741% over 120 months.
- **Minimum mean detectable at t = 2** (2 × standard error):
  - **0.153% per month** with the Newey–West lag-6 SE (0.0765)
  - **0.135% per month** with the iid SE (0.0677)
- **Against the observed +0.103%:** the observed mean is about two-thirds of
  the detectable threshold. A real effect of that size could not be
  confirmed in ten years of data.
- **What was not detected:** a gross value-weighted composite mean at or
  above about 0.15% per month, which is 1.8% a year before costs.

## By data category (descriptive only)

Each composite is built within a `Cat.Data` category, with the same rules.
**These are descriptive and cannot rescue or overturn the primary.**

- **Multiple testing.** Eight categories × four composites × three windows
  is 96 cells, so a few t > 2 cells are expected by chance.
- **13F, Event and Options** have 8–9 predictors each. They never reach the
  pre-committed 10-predictor minimum breadth, so they have no composite. The
  rule was not relaxed after the fact.
- **In 2015–2024:**
  - **Price**, the only category with t > 2 in its VW composite, has
    t = 2.45.
  - **Accounting**, the largest category at 99 predictors, has VW t = 0.68
    but OP t = 2.93. That is the equal-weighting gap again.
  - **Other and Trading** are negative in VW.
  - Given the multiple testing, no category result is a finding.

#### 13F (8 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full | 0 | — | — | — | — | — |
| VW all | post2000 | 0 | — | — | — | — | — |
| VW all | 2015_2024 | 0 | — | — | — | — | — |
| VW post_pub | full | 0 | — | — | — | — | — |
| VW post_pub | post2000 | 0 | — | — | — | — | — |
| VW post_pub | 2015_2024 | 0 | — | — | — | — | — |
| OP all | full | 0 | — | — | — | — | — |
| OP all | post2000 | 0 | — | — | — | — | — |
| OP all | 2015_2024 | 0 | — | — | — | — | — |
| OP post_pub | full | 0 | — | — | — | — | — |
| OP post_pub | post2000 | 0 | — | — | — | — | — |
| OP post_pub | 2015_2024 | 0 | — | — | — | — | — |

#### Accounting (99 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1951-07–2024-12) | 882 | 20/97 | +0.240 | +6.60 | 0.92 | -6.7% |
| VW all | post2000 (2000-01–2024-12) | 300 | 98/99 | +0.213 | +2.79 | 0.72 | -6.7% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 99/99 | +0.066 | +0.72 | 0.26 | -6.7% |
| VW post_pub | full (1995-01–2024-12) | 360 | 10/74 | +0.131 | +1.55 | 0.33 | -16.1% |
| VW post_pub | post2000 (2000-01–2024-12) | 300 | 21/86 | +0.191 | +2.16 | 0.48 | -8.2% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 96/99 | +0.062 | +0.68 | 0.24 | -6.7% |
| OP all | full (1951-07–2024-12) | 882 | 20/97 | +0.408 | +12.40 | 1.78 | -4.2% |
| OP all | post2000 (2000-01–2024-12) | 300 | 98/99 | +0.378 | +5.88 | 1.52 | -3.2% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 99/99 | +0.281 | +2.96 | 1.23 | -3.2% |
| OP post_pub | full (1995-01–2024-12) | 360 | 10/74 | +0.319 | +3.72 | 0.81 | -18.6% |
| OP post_pub | post2000 (2000-01–2024-12) | 300 | 21/86 | +0.346 | +4.46 | 0.93 | -4.3% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 96/99 | +0.276 | +2.93 | 1.22 | -3.2% |

#### Analyst (18 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1977-06–2024-12) | 560 | 10/18 | +0.278 | +3.34 | 0.51 | -20.6% |
| VW all | post2000 (2000-01–2024-12) | 300 | 18/18 | +0.286 | +2.25 | 0.45 | -15.1% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 18/18 | +0.134 | +0.76 | 0.24 | -10.0% |
| VW post_pub | full (2002-01–2024-12) | 276 | 10/18 | +0.187 | +1.46 | 0.34 | -15.9% |
| VW post_pub | post2000 (2002-01–2024-12) | 276 | 10/18 | +0.187 | +1.46 | 0.34 | -15.9% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 18/18 | +0.134 | +0.76 | 0.24 | -10.0% |
| OP all | full (1977-06–2024-12) | 560 | 10/18 | +0.471 | +5.60 | 0.91 | -19.0% |
| OP all | post2000 (2000-01–2024-12) | 300 | 18/18 | +0.370 | +2.98 | 0.63 | -15.7% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 18/18 | +0.247 | +1.36 | 0.47 | -15.7% |
| OP post_pub | full (2002-01–2024-12) | 276 | 10/18 | +0.274 | +2.15 | 0.54 | -16.5% |
| OP post_pub | post2000 (2002-01–2024-12) | 276 | 10/18 | +0.274 | +2.15 | 0.54 | -16.5% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 18/18 | +0.247 | +1.36 | 0.47 | -15.7% |

#### Event (8 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full | 0 | — | — | — | — | — |
| VW all | post2000 | 0 | — | — | — | — | — |
| VW all | 2015_2024 | 0 | — | — | — | — | — |
| VW post_pub | full | 0 | — | — | — | — | — |
| VW post_pub | post2000 | 0 | — | — | — | — | — |
| VW post_pub | 2015_2024 | 0 | — | — | — | — | — |
| OP all | full | 0 | — | — | — | — | — |
| OP all | post2000 | 0 | — | — | — | — | — |
| OP all | 2015_2024 | 0 | — | — | — | — | — |
| OP post_pub | full | 0 | — | — | — | — | — |
| OP post_pub | post2000 | 0 | — | — | — | — | — |
| OP post_pub | 2015_2024 | 0 | — | — | — | — | — |

#### Options (9 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full | 0 | — | — | — | — | — |
| VW all | post2000 | 0 | — | — | — | — | — |
| VW all | 2015_2024 | 0 | — | — | — | — | — |
| VW post_pub | full | 0 | — | — | — | — | — |
| VW post_pub | post2000 | 0 | — | — | — | — | — |
| VW post_pub | 2015_2024 | 0 | — | — | — | — | — |
| OP all | full | 0 | — | — | — | — | — |
| OP all | post2000 | 0 | — | — | — | — | — |
| OP all | 2015_2024 | 0 | — | — | — | — | — |
| OP post_pub | full | 0 | — | — | — | — | — |
| OP post_pub | post2000 | 0 | — | — | — | — | — |
| OP post_pub | 2015_2024 | 0 | — | — | — | — | — |

#### Other (12 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1986-02–2024-12) | 467 | 10/11 | +0.145 | +1.75 | 0.31 | -13.1% |
| VW all | post2000 (2000-01–2024-12) | 300 | 10/11 | +0.006 | +0.05 | 0.01 | -13.1% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 10/10 | -0.143 | -0.74 | -0.28 | -13.1% |
| VW post_pub | full (2015-01–2024-12) | 120 | 10/10 | -0.143 | -0.74 | -0.28 | -13.1% |
| VW post_pub | post2000 (2015-01–2024-12) | 120 | 10/10 | -0.143 | -0.74 | -0.28 | -13.1% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 10/10 | -0.143 | -0.74 | -0.28 | -13.1% |
| OP all | full (1986-02–2024-12) | 467 | 10/11 | +0.157 | +1.78 | 0.37 | -14.0% |
| OP all | post2000 (2000-01–2024-12) | 300 | 10/11 | -0.019 | -0.17 | -0.04 | -14.0% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 10/10 | -0.310 | -1.95 | -0.69 | -14.0% |
| OP post_pub | full (2015-01–2024-12) | 120 | 10/10 | -0.310 | -1.95 | -0.69 | -14.0% |
| OP post_pub | post2000 (2015-01–2024-12) | 120 | 10/10 | -0.310 | -1.95 | -0.69 | -14.0% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 10/10 | -0.310 | -1.95 | -0.69 | -14.0% |

#### Price (45 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1926-07–2024-12) | 1182 | 11/43 | +0.491 | +11.06 | 1.19 | -25.7% |
| VW all | post2000 (2000-01–2024-12) | 300 | 42/45 | +0.327 | +3.36 | 0.69 | -10.1% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 42/45 | +0.291 | +2.47 | 0.79 | -4.7% |
| VW post_pub | full (2000-01–2024-12) | 300 | 10/38 | +0.350 | +2.97 | 0.48 | -13.0% |
| VW post_pub | post2000 (2000-01–2024-12) | 300 | 10/38 | +0.350 | +2.97 | 0.48 | -13.0% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 42/45 | +0.291 | +2.45 | 0.79 | -4.7% |
| OP all | full (1926-07–2024-12) | 1182 | 11/43 | +0.656 | +16.20 | 1.77 | -6.3% |
| OP all | post2000 (2000-01–2024-12) | 300 | 42/45 | +0.451 | +4.83 | 1.01 | -6.3% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 42/45 | +0.294 | +2.53 | 0.83 | -2.7% |
| OP post_pub | full (2000-01–2024-12) | 300 | 10/38 | +0.447 | +4.27 | 0.76 | -9.7% |
| OP post_pub | post2000 (2000-01–2024-12) | 300 | 10/38 | +0.447 | +4.27 | 0.76 | -9.7% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 42/45 | +0.296 | +2.54 | 0.83 | -2.8% |

#### Trading (13 predictors)

| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) | Sharpe (ann.) | Worst 12m |
|---|---|---:|---:|---:|---:|---:|---:|
| VW all | full (1928-01–2024-12) | 1164 | 10/12 | +0.152 | +2.12 | 0.19 | -25.4% |
| VW all | post2000 (2000-01–2024-12) | 300 | 12/13 | +0.083 | +0.61 | 0.13 | -25.4% |
| VW all | 2015_2024 (2015-01–2024-12) | 120 | 12/12 | -0.211 | -1.00 | -0.37 | -25.4% |
| VW post_pub | full (2003-01–2024-12) | 264 | 10/12 | -0.037 | -0.28 | -0.07 | -25.4% |
| VW post_pub | post2000 (2003-01–2024-12) | 264 | 10/12 | -0.037 | -0.28 | -0.07 | -25.4% |
| VW post_pub | 2015_2024 (2015-01–2024-12) | 120 | 12/12 | -0.211 | -1.00 | -0.37 | -25.4% |
| OP all | full (1928-01–2024-12) | 1164 | 10/12 | +0.501 | +5.63 | 0.48 | -28.6% |
| OP all | post2000 (2000-01–2024-12) | 300 | 12/13 | +0.290 | +1.89 | 0.32 | -28.6% |
| OP all | 2015_2024 (2015-01–2024-12) | 120 | 12/12 | +0.085 | +0.39 | 0.10 | -27.8% |
| OP post_pub | full (2003-01–2024-12) | 264 | 10/12 | +0.206 | +1.31 | 0.24 | -28.6% |
| OP post_pub | post2000 (2003-01–2024-12) | 264 | 10/12 | +0.206 | +1.31 | 0.24 | -28.6% |
| OP post_pub | 2015_2024 (2015-01–2024-12) | 120 | 12/12 | +0.085 | +0.39 | 0.10 | -27.8% |

## Limitations

1. **Gross of costs, very high turnover.**
   - There are no commissions, spreads, price impact or short-borrow fees.
   - `SignalDoc.csv` has no turnover field.
   - The composite rebalances about 200 long-short books, most of them
     monthly.
   - A 0.10–0.29% gross monthly mean is small next to plausible costs for
     that turnover. This project's turnover budget
     (`2026-09-03-planning-note-turnover-budget`, K ≈ 232) is the standing
     test any tradable version would face.
2. **No out-of-sample period.** 2015–2024 was already examined
   predictor-by-predictor in the triage. This test avoids selection by
   using all 212 predictors, but it is not a fresh sample.
3. **Composite construction.** The composite equal-weights predictors, not
   stocks. Its gross exposure is the average of about 200 unit long-short
   books, so it is not a single implementable portfolio, and it double-counts
   stocks that appear in many signals.
4. **Only weighting differs between VW and OP.**
   - VW is OSAP's forced-value-weighting alternative. No price, size or
     exchange screen was verified.
   - OP is mostly equal-weighted: 184 of 212.
5. **Newey–West with lag 6.** This addresses short-horizon autocorrelation.
   Predictors that hold positions for 12–36 months may have longer
   dependence than lag 6 captures.
6. **Publication timing.** The post-publication masks use the journal year
   from `SignalDoc.csv`. Working papers often circulated earlier, so the
   "post-publication" composite may include some pre-publication months.
7. **Breadth rule.** The 10-predictor minimum was fixed in advance. It
   removes three whole categories from the category table.
   - The full sample's first months (1926) rest on as few as 11 predictors.
     Breadth is about 50 by 1930, about 114 by 1960 and about 145 by 1970.
8. **Provenance.** File hashes are in [sources.json](sources.json).
   `SignalDoc.csv` came from the GitHub v2.0.0 tag, and the two return
   files were downloaded by Jaeyoung in a browser. These are OSAP's
   reconstructions of the original studies.
