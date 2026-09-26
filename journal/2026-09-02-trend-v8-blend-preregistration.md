# 2026-09-02 — trend-v8-blend: pre-registration (BINDING)

Append-only. Written before any v8 market return is computed. The reusable
Bayesian arithmetic was implemented and tested only on synthetic known-answer
cases first; no v8 price series was touched while choosing the rules below.

Study id: `trend-v8-blend`.

## Question

V7 found that three simple sleeves improved the ETF balanced portfolio:
multi-asset trend, static gold, and a more-defensive stock/bond allocation. It
then ranked them one at a time. This study asks whether the project's most
replicated design choice—averaging rather than choosing—also helps when applied
across those sleeves.

The Bayesian part asks a separate decision question: given the measured
uncertainty and an explicit prior, is the expected loss lower if the sleeve is
allocated than if the unmodified base is retained?

Nothing below selects a weight, sleeve mix, prior, or reported result.

## Fixed constructions

The tradeable ETF window, calendar, execution rule, risk-free series, and
walk-forward folds are identical to v7: 2004-10-22 through 2026-09-01, 5,499
stitched OOS bars, 22 folds, 210-bar embargo, next-close execution, and
uninvested cash earning the real T-bill rate.

The base is 60% SPY / 40% IEF, monthly rebalanced. The three component sleeves
are exactly the v7 versions:

* `trend`: fixed v6 ensemble over SPY, EFA, EEM, TLT, IEF, and GLD; equal
  average of the 4-10 month trend portfolios; residual in cash;
* `gold`: 100% static GLD;
* `defensive`: the v7 more-defensive path, represented inside a total sleeve
  of weight `w` by shifting `0.20w` from SPY to IEF.

At total sleeve weight `w` in `{0.1, 0.2, 0.3}`, the four fixed new mixes are:

| mix | construction |
|---|---|
| `trend_gold` | half of total sleeve budget to trend, half to gold |
| `trend_defensive` | half to trend, half to the defensive shift |
| `gold_defensive` | half to gold, half to the defensive shift |
| `trend_gold_defensive` | one third to each component |

Equivalently, component target streams are combined linearly. For example,
`trend_gold` is `(1-w) * base + (w/2) * trend + (w/2) * GLD`. The defensive
component is defined by its displacement from base: a component allocation
`d` contributes `-0.20d` SPY and `+0.20d` IEF. Thus every blend remains
long-only, fully invested including residual cash, and has gross exposure 1.0.
All streams rebalance on the same last-trading-day monthly calendar.

The three v7 single-sleeve arms (`trend`, `gold`, `defensive`) at each same `w`
are deterministic comparators. They are reconstructed and checked against v7,
not treated as newly searched configurations or re-entered under their old
study ids.

Every one of the four blends is compared, paired, with every one of the three
single sleeves at the same `w`: 12 comparisons per weight, 36 total. The
weights and mixes are curves/reporting cells. None is ranked, selected, called
"best", or used to choose another result.

## Deep history and prior construction

The deep-history calendar and folds are identical to v4/v7: 1932-03-15 through
2026-06-30, 24,579 stitched OOS bars, 95 folds, with a 60% MKT / 40% CASH base.
The v4 12-industry 4-10 month trend ensemble supplies `trend`; shifting
`0.20w` from MKT to CASH supplies `defensive`.

Only the `trend_defensive` blend has an exact deep-history analogue among the
new mixes. Its three weights are run first and logged before any ETF blend is
evaluated. Existing v7 deep `trend` and `defensive` single arms are rebuilt for
their corresponding supplementary priors but are not new configurations.

For each exact arm/weight comparison against its unmodified deep base:

1. jointly resample the paired return rows with the Politis-Romano stationary
   bootstrap, 10,000 resamples, expected block length 21, fixed seed 0;
2. compute the annualized rf=0 Sharpe difference on every draw;
3. approximate that bootstrap sampling distribution by a normal likelihood
   centred at the observed difference with standard deviation equal to the
   bootstrap-draw standard deviation;
4. update the neutral prior defined below; and
5. freeze the resulting posterior mean and standard deviation as the
   deep-history-informed prior before the corresponding ETF posterior is
   computed.

This rule is empirical-Bayes in sequence but not in selection: the source,
mapping, prior used for the deep update, approximation, and order are all fixed
here before either universe is evaluated. Bootstrap mean versus point estimate
is printed as a bias diagnostic.

## Prior asymmetry resolved from Q9

The deep-informed prior is **UNAVAILABLE** for every gold-containing arm:
`gold`, `trend_gold`, `gold_defensive`, and `trend_gold_defensive`. It is not
replaced by the `trend_defensive` posterior or by the static 12-industry arm.
There is no evidence that gold behaves like trend or defensive; v7 found gold
beating trend on the ETF window, so shrinking gold toward a trend-sized effect
would systematically flatter the strategy the project has an interest in.

The exact deep-informed prior is supplementary only for `trend`, `defensive`,
and `trend_defensive` at the same `w`. It is never the headline in a comparison
against an arm lacking the same evidence.

Consequently, **all cross-arm comparisons are prior-matched**: blend versus
blend and blend versus single-sleeve Bayesian comparisons use only skeptical
and neutral priors, which exist for every arm. A deep-informed posterior is
never compared with a neutral- or skeptical-prior posterior.

The results must state prominently that the evidence base is uneven: trend has
94 years behind it and gold has 22. This is a finding about available evidence,
not a footnote.

A future deep gold ingest would not erase the asymmetry cleanly. Gold was
pegged under Bretton Woods until 1971, so floating-price history is roughly 55
years, not 94, with a structural break at its start. Any such ingest must be a
separate data-layer decision and dual-source checked before research use. V8
does not ingest or substitute a gold series.

## Bayesian model and sensitivity priors

Let `delta = SR(challenger) - SR(comparator)`, annualized at rf=0. For each
paired comparison, the likelihood is the normal approximation to the fixed
block-bootstrap distribution described above. This approximation is reported
as an assumption; it does not turn resampled draws into independent market
history.

The three fixed sensitivity priors are:

| prior | distribution | interpretation |
|---|---|---|
| skeptical | Normal(0.00, 0.05^2) | effects are probably small and centred at no improvement |
| neutral | Normal(0.00, 0.25^2) | weak information over the scale relevant here |
| deep-informed | exact matching deep posterior | supplementary; only the three non-gold mappings above |

Normal likelihood and normal prior are combined by the standard precision-
weighted conjugate update. Report posterior mean, equal-tailed 90% credible
interval, `P(delta > 0)`, and `P(delta > 0.05)`.

If the lower-expected-loss action changes across skeptical, neutral, and—when
available—deep-informed priors, print `SENSITIVITY FLIP` prominently. That
instability is the finding; no prior is selected after seeing it.

## Fixed allocation loss

For arm-versus-base allocation decisions, in annualized Sharpe units:

* `L(allocate, delta) = max(-delta, 0) + 0.01`
* `L(do_not_allocate, delta) = max(delta, 0)`

The first term is regret from adopting a genuinely worse arm; `0.01` is a
fixed switching/model-complexity penalty preserving the project's incumbent
inertia after trading costs have already been charged in the return series.
The second is regret from foregoing a genuinely positive improvement. Report
both posterior expected losses and the lower-loss action. Equality keeps the
incumbent.

This loss comparison is for the decision framing, not an adopted promotion
gate. A proposed gate is written only under `QUESTIONS FOR PLANNING` after the
study and cannot alter this study's interpretation.

## Classical and standard reporting

At minimum:

* all new blends, every v7 single-sleeve comparator, the unmodified 60/40, and
  SPY buy-and-hold on the identical ETF OOS window;
* deep `trend_defensive`, existing deep singles, 60% MKT / 40% CASH, and MKT
  on the identical deep OOS window;
* 0, 5, and 10 bps one-way costs;
* CAGR, annualized volatility, Sharpe at rf=0 and against real RF, maximum
  drawdown, worst day, 5th-percentile day, and annualized turnover;
* `metrics.by_subperiod` default ETF breaks and decades for deep history;
* paired stationary-bootstrap difference and Ledoit-Wolf HAC counterpart at
  5 bps, with correlation, 10,000 resamples, and block length 21 stated beside
  every interval;
* the Bayesian table above at 5 bps; and
* trial/configuration and row counts, with a DSR effective-breadth note. No
  configuration is selected, so DSR is descriptive and not load-bearing.

Matched-volatility distribution reporting from v7 is retained for blend versus
single comparisons: only CAGR, max drawdown, worst day, and 5th-percentile day
are volatility matched, using real-RF cash-aware scaling of the more volatile
side down. Sharpe is never labelled matched-vol because it is scale invariant.

## Trial accounting

New strategy configurations:

* ETF: 4 mixes x 3 total weights = 12 configurations x 22 folds = 264 rows;
* deep: 1 exactly reproducible mix x 3 weights = 3 configurations x 95 folds
  = 285 rows;
* total: 15 distinct v8 configurations and 549 ledger rows.

The nine ETF and six deep v7 single-sleeve cells are comparators reconstructed
from already counted configurations, not new searches. Prior sensitivities are
inference assumptions applied to every eligible arm, not trade configurations,
and are not entered as strategy trials. If any mix, weight, prior, or loss
parameter is later selected from these curves, the associated claim must add
that selection to its multiplicity accounting.

## Stopping and interpretation

Nothing can be promoted. Positive, negative, prior-sensitive, and unavailable-
prior results are journalled with equal detail. The study stops after all fixed
cells are reported, the results entry is written, and the planning-only gate
proposal is drafted. No mix or weight is carried forward by this script.
