# 2026-09-02 — xsmom-v13-confirm: pre-registration (BINDING)

Append-only. Written and committed before v13 code is implemented or any v13
result is computed. Study id: `xsmom-v13-confirm`.

## Purpose, prior, and stopping rule

V11 reported a monotone 94-year stock-level momentum sort, a 13.8 percentage
point top-minus-bottom CAGR spread, and top-three deciles beating equal-weight
ten by +0.132 Sharpe with paired p approximately 0.005. It had no
pre-registration, did not model internal constituent turnover, and wrote no
ledger rows. Every v11 number is exploratory. V13 is the fixed confirmation
study and does not inherit confirmatory status from v11.

Planning has closed the time-series trend family on the tradeable ETF window
and made cross-sectional equity momentum the primary research line. V13 tests
one fixed challenger: the equal-weight average of the highest three French
prior-return deciles. The single highest decile is diagnostic and is not an
alternative candidate. No decile, number held, cost, era, tail metric, or
regression specification is selected.

The study stops after Parts A-C, standard comparisons, ledger, stdout record,
and factual results entry. Journal positive, null, or cost-killed results with
the same detail. Nothing is promoted by this Phase-2 study.

## Data, calendar, and fixed configurations

Use the existing local Ken French
`10_Portfolios_Prior_12_2_Daily_CSV.zip`, value-weighted daily block only, and
the existing Fama-French daily factors parquet. Verify the archive contains
exactly ten ordered columns from `Lo PRIOR` through `Hi PRIOR`, mask -99.99 and
-999, align to complete MKT/CASH dates, and reproduce the v11 OOS window
1932-09-06 through 2026-06-30 (expected 24,434 bars and 94 folds). The frozen
scheme is 5-year train, 1-year validation, 1-year step, and 252-bar embargo,
matching the 12-2 lookback.

Return-bearing configurations are the ten individual deciles plus top-three,
equal-weight-ten, MKT, 60% MKT/40% CASH, and cash-collateralized Hi-minus-Lo:
15 distinct portfolio configurations. Top-three is the confirmatory
challenger. MKT replaces SPY and 60% MKT/40% CASH replaces ETF 60/40 on this
deep-history window under the already disclosed v4 mapping; neither is called
SPY or a Treasury-bond portfolio.

## Part A — model-implied decile-migration turnover and costs

The archive contains portfolio returns but no stock identifiers, constituent
weights, or migration matrix. Exact realized internal turnover is therefore
not identifiable and must not be claimed. V13 estimates the turnover implied
by a fixed rank-transition model and labels it `model-implied`, never
`observed`.

The French characteristic uses returns t-250 through t-21 inclusive: 230
daily observations. Adjacent daily characteristics mechanically share 229 of
those 230 observations. Fix latent standardized ranks as a stationary
bivariate standard Normal with one-day correlation `rho = 229/230`. Fix
decile boundaries at standard-Normal quantiles 0.1 through 0.9. For a sleeve
covering rank interval A, compute the conditional one-day exit probability
`P(Z_t in A, Z_(t+1) outside A) / P(Z_t in A)` by deterministic numerical
quadrature. Model-implied annual cost-engine turnover is twice that exit rate
times 252: one sell plus one replacement buy under the project's
`sum(abs(delta weight))` convention.

For an individual decile A is its 10% bin. For top-three A is the union above
the 70th percentile. Equal-weight-ten is the full rank support and has zero
internal migration turnover because crossings between its ten sleeves cancel
under the model; this is a favorable lower bound for that control. Hi-minus-Lo
charges the sum of the high- and low-decile one-leg turnover. The model assumes
value mass is exchangeable within rank probability bins; unequal stock sizes,
corporate entry/exit, breakpoint jumps, and trading impact are unavailable.
Report these limitations beside every turnover conclusion.

Add exact outer portfolio turnover from the existing monthly-rebalance engine
to the model-implied internal turnover. Charge a flat daily drag
`annual_turnover * cost_bps / 10,000 / 252` at 0, 5, 10, 25, and 50 bps. For
Hi-minus-Lo the two legs are both charged. Report net CAGR and Sharpe at every
cost, the net Hi-minus-Lo-decile CAGR spread and fraction of the v11 13.8-point
reference spread surviving, and the first non-negative cost where top-three's
rf=0 Sharpe is no longer above equal-weight-ten. Solve that crossover by
bisection on [0, 500] bps to 0.001 bps; report `>500` if absent. This fixed
crossover is not a searched trading cost.

Because the input lacks constituents, the cost result is a model-based stress,
not proof of tradeability. A future exact answer requires CRSP-level daily
identifiers, market equity, and portfolio membership, with licensed ingestion
and provenance; that is a separate data decision.

## Part B — portfolio-level Fama-MacBeth prediction test

Build `woodland/xsreg.py`. At every daily formation period, the characteristic
is the fixed ordered decile midpoint transformed to its standard-Normal score
(probabilities 0.05, 0.15, ..., 0.95), then standardized cross-sectionally to
mean zero and sample standard deviation one. Regress the following daily
value-weighted return of all ten contemporaneous decile portfolios on an
intercept and that characteristic. The archive's portfolios for return date t
are formed from information through t-1 under the French daily construction,
so the dated return is the one-period forward outcome.

Store one cross-sectional slope per day. Report its daily and annualized
average, Newey-West standard error with fixed 21 daily lags, t-statistic for a
zero average slope, two-sided Normal p-value, fraction of daily slopes
positive, and observations/periods. Run the same fixed regression for the full
OOS sample, 1932-1979, and 1980-2026. The pre/post-1980 split is a required
decay diagnostic, not a selection rule.

This is a portfolio-level Fama-MacBeth test using rank proxies because the
archive lacks stock characteristics. It asks whether the ordered momentum
characteristic predicts the next portfolio return cross-section; it is
stronger than a single portfolio path but is not a stock-level regression and
must be labelled accordingly. Unit-test a known synthetic coefficient and
Newey-West inference before reading the real decile matrix through this code.

## Part C — tail-aware metrics and confidence intervals

Build `woodland/tailrisk.py` with fixed definitions:

* 95% and 99% expected shortfall/CVaR are positive loss magnitudes, the
  negative mean return at or below the empirical 5% and 1% quantiles;
* Sortino is annualized mean return divided by the root-mean-square downside
  below a zero daily target, multiplied by square-root 252;
* Omega at threshold zero is total positive return divided by absolute total
  negative return;
* tail ratio is the 95th return percentile divided by the absolute 5th;
* Pezier-White adjusted Sharpe applies
  `SR_d * (1 + skew*SR_d/6 - excess_kurtosis*SR_d^2/24)` to daily Sharpe and
  then annualizes by square-root 252; and
* drawdown durations are every completed below-previous-peak spell plus an
  ongoing terminal spell, reported as count, mean, median, 90th percentile,
  and maximum trading days.

Each scalar metric gets a percentile 95% confidence interval from 10,000
Politis-Romano stationary block-bootstrap resamples, expected block length 21,
seed 0. Degenerate resamples are reported rather than silently coerced. Unit
tests cover known empirical calculations, duration spells, and deterministic
bootstrap output.

At 10 bps, report point estimates and bootstrap intervals for all 15 portfolio
configurations. Report the same point metrics at 0/5/10/25/50 bps. Use
Hi-minus-Lo as the required worked example: v11 recorded Sharpe 0.512, skew
-1.15, excess kurtosis 20.5, -85% maximum drawdown, and 6,404 days underwater;
show explicitly where Sharpe and the tail-aware metrics disagree after the
model-implied cost charge.

## Paired inference, sub-periods, and accounting

At every cost, compare top-three with equal-weight-ten and MKT using paired
stationary-bootstrap Sharpe differences (10,000 resamples, block 21, seed 0),
Ledoit-Wolf HAC, and correlation. Report the ten individual deciles to show
monotonicity without selecting one. Standard reporting includes 0/5/10 bps
and the additional 25/50 bps cost stresses, identical-window MKT and 60%
MKT/40% CASH, `metrics.by_subperiod` with deep-history decade breaks, and the
fixed pre/post-1980 table.

Ledger accounting is 16 configurations x 94 folds = 1,504 rows: the 15
portfolio configurations above plus one fixed Fama-MacBeth specification.
Portfolio rows are scored at the standard 5 bps model-implied cost; regression
rows store the fold slope result in notes because the ledger has no slope
column. Reporting additional costs and bootstrap draws does not add searched
configurations. Deflated Sharpe uses the 15 return-bearing configurations and
states that their strong dependence makes effective breadth smaller than the
literal count; the regression configuration is excluded from Sharpe breadth.

All French decile series are frictionless academic constructs, not securities,
and the source archive is not a constituent-level execution record. The ETF
store's separate dual-source caveat does not validate these academic series.
