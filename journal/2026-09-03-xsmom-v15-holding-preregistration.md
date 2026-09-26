# 2026-09-03 — xsmom-v15-holding: pre-registration (BINDING)

Append-only. Written and committed before v15 implementation reads the real
decile series through the new holding-period code or computes any v15 result.
Study id: `xsmom-v15-holding`.

## Purpose, prior, and stopping rule

V13 found a real gross cross-sectional momentum relationship but estimated
that the top-three portfolio's Sharpe edge over equal-weight-ten disappeared
at 11.168 bps under 21.736x annual model-implied internal turnover. Planning's
prior is therefore adverse: achievable retail all-in costs are 25-50 bps and
the v13 crossover is on the wrong side of that range. If cost is binding, the
direct response is to refresh the selected cohort less often and accept signal
decay.

V15 varies exactly one pre-registered parameter: cohort refresh frequency in
`{monthly, quarterly, semi-annual, annual}`. All four points are reported as a
CURVE with no selection, ranking, winner, or promotion. Choosing a frequency
after seeing this curve would be selection and must enter a future study's
trial count. The headline asks both whether any cost crossover clears 25 bps
(the lower edge of planning's achievable-retail range) or 50 bps (the upper
edge), and whether gross momentum survives slower refresh at all.

Stop after the fixed curve, standard reports, ledger, saved stdout, and a
factual results entry. Journal positive, null, mixed, or cost-killed results
with equal care. Nothing is promoted by this Phase-2 study.

## Data, window, and walk-forward scheme

Use the existing local Ken French
`10_Portfolios_Prior_12_2_Daily_CSV.zip`, value-weighted daily block only, and
the existing Fama-French factor parquet. Require the same ordered ten columns,
complete MKT/CASH alignment, frozen 5-year train / 1-year validation / 1-year
step / 252-bar embargo scheme, 94 folds, and OOS window 1932-09-06 through
2026-06-30 with 24,434 bars. MKT and 60% MKT/40% CASH remain the disclosed
deep-history analogues for SPY and 60/40; neither is relabeled as the absent
tradeable ETF/bond series.

The fixed return-bearing configurations are four modeled top-three holding
frequencies plus unchanged v13 equal-weight-ten, MKT, and 60% MKT/40% CASH:
seven distinct configurations. Equal-weight-ten is the primary comparator;
MKT and the balanced analogue are mandatory controls.

## Fixed stale-cohort return approximation

The aggregate French series cannot identify returns of stocks held after they
leave the top-three ranks. Planning has separately approved the model-implied
approximation in
`2026-09-03-planning-decision-xsmom-v15-stale-cohort.md`.

Use the v13 stationary Gaussian latent-rank process with daily
`rho = 229/230`. At each scheduled formation close, select latent ranks above
the 70th percentile. The first next-bar return has mass 1/3 in each of current
deciles 8, 9, and 10. At age `k` trading days after that first return, compute

`w_j(k) = P(Z_0 > q_0.70, Z_k in decile j) / 0.30`,

where `(Z_0, Z_k)` is bivariate standard Normal with correlation `rho^k`.
Apply `w_j(k)` to the observed contemporaneous value-weighted return of decile
`j`. Compute probabilities by fixed 256-node Gauss-Legendre quadrature over
the selected source rank interval truncated at +8 standard deviations;
renormalize the ten weights to sum to one. At `k=0`, set the exact vector
directly rather than evaluate a degenerate conditional distribution.

Formation dates are the last available trading date in each calendar month,
quarter, half-year, or year. A close-t formation affects t+1, never t. The
first OOS formation occurs at the first scheduled close inside the stitched
OOS window; preceding OOS bars remain zero-return cash, matching the existing
v13 target-start convention. Folds do not reset the portfolio because their
validation windows form the same continuous stitched OOS record. A future-
return perturbation test must prove that changing data after t cannot change
modeled returns through t before real v15 output is inspected.

This approximation assumes current-decile returns apply exchangeably to the
stale cohort mass that has migrated into that decile. That assumption is new
relative to v13 and is load-bearing. Every table must label the resulting
top-three paths `model-implied stale cohort`; no output may call them observed
stock returns or a reproduction of v13.

## Turnover and transaction costs

At each formation after the first, let `h` be the actual number of trading
bars since the prior formation and compute the surviving fraction
`P(Z_h > q_0.70 | Z_0 > q_0.70)`. Refresh-event turnover under the project's
sum-absolute convention is `2 * (1 - surviving_fraction)`. Annualized
model-implied internal turnover is the sum of those event turnovers divided by
OOS years. Add the one-time initial 1.0 purchase, annualized over the same
window, as observed outer formation turnover. Terminal formation dates with no
following OOS return are excluded. Equal-weight-ten retains v13's favorable
zero internal-migration assumption and observed monthly outer turnover; MKT
and 60/40 use their unchanged v13 observed outer turnover.

Carry the v13 caveat forward verbatim: **it is an estimate, not observed, and
it omits size dispersion, entry/exit, breakpoint jumps, impact, borrow and
capacity, all of which push true cost up.** For v15, gross stale-cohort returns
are modeled too. Exact validation requires constituent-level point-in-time
membership, market equity, and returns; that is a separate licensed data-layer
decision.

Charge the total annual turnover as the same flat daily drag used for v13 at
0, 5, 10, 25, and 50 bps. For each frequency, report model-implied internal
turnover, initial outer turnover, total charged turnover, net CAGR, rf=0 and
real-risk-free Sharpe, maximum drawdown, worst day, and left-tail fifth
percentile.

For each frequency, solve the cost where its rf=0 Sharpe first ceases to exceed
unchanged equal-weight-ten by bisection over [0, 500] bps to 0.001 bps; report
`>500` if no crossing. The crossover is an output of a fixed equation, not a
searched cost configuration.

## Inference, regimes, and tail reporting

At every cost and for every one of the four frequency points, compare against
equal-weight-ten and MKT with joint Politis-Romano stationary block bootstrap
(10,000 resamples, expected block length 21, seed 0), the Ledoit-Wolf HAC
counterpart, and pair correlation. These 40 full-window comparisons are
descriptive points on the frozen curve, not frequency selection.

Repeat the paired comparisons in fixed eras 1932-1979 and 1980-2026 at every
cost. At 10 bps, report `metrics.by_subperiod` with decade breaks for all seven
configurations. Report tail-aware point metrics from `woodland/tailrisk.py` at
all five costs for all seven configurations: CVaR/expected shortfall 95 and 99,
Sortino, Omega, tail ratio, Pezier-White adjusted Sharpe, skew, excess
kurtosis, and the full drawdown-duration distribution. At 10 bps attach the
registered 10,000-resample, block-21, seed-0 percentile interval to every
scalar tail metric.

The headline must distinguish signal survival (gross curve), cost survival
(5/10/25/50 bps), and model uncertainty. Crossing 25 or 50 bps is reported
against planning's pre-existing retail-cost range, not called proof of
tradeability. Failure to cross it closes the cheap holding-frequency question;
success only motivates constituent-level validation and does not promote a
frequency.

## Ledger and deflated Sharpe

Ledger accounting is seven configurations times 94 folds = 658 rows. Record
each portfolio configuration once per validation fold at the standard 5 bps
cost. The additional cost scenarios, bootstrap paths, era slices, and solved
crossovers are reports of the same fixed configurations, not extra lottery
tickets.

Deflated Sharpe uses all seven return-bearing configurations and explicitly
states that the four holding frequencies are highly dependent, as are the
three market controls, so literal breadth materially overstates independent
effective breadth. DSR cannot select a point from the curve or override the
paired cost comparisons.
