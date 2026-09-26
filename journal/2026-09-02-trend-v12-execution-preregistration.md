# 2026-09-02 — trend-v12-execution: pre-registration (BINDING)

Append-only. Written and committed before any v12 market result is computed.
Study id: `trend-v12-execution`.

## Question and stopping rule

This is an execution study, not a new strategy. The signal is the fixed v6
multi-asset ensemble over SPY, EFA, EEM, TLT, IEF, and GLD: the equal-weight
average of the 4-10 month trend target portfolios, with risk-off capital in
cash earning the real T-bill rate. No signal, universe, lookback, risk weight,
or forecast parameter is changed or selected.

V6 turns over 5.15 times per year versus approximately 0.23 for the balanced
benchmark. Every cost conclusion so far rests on an untested 5 bps assumption.
The exploratory, unregistered v11 decile result is also entirely gross of the
stock turnover internal to Ken French's daily momentum portfolios. Cost
realism is therefore the binding uncertainty on every current conclusion and
gates any decision to invest in broader futures data.

The study asks whether mechanical execution policies reduce turnover without
materially degrading the unchanged v6 signal. Every setting is reported as a
surface. No setting is selected, ranked, promoted, or carried forward. The
study stops after the fixed surface, exploratory v11 cost overlay, ledger, and
results entry are complete.

## Universe, signal, and walk-forward scheme

Use the same ETF matrix, real daily risk-free series, suspect-date treatment,
and frozen walk-forward scheme as v6: 5-year train, 1-year validation, 1-year
step, 210-bar embargo, 22 realized folds, and the stitched OOS window
2004-10-22 through 2026-09-01 (5,499 bars). Signal targets are computed once
with `trend.ensemble_targets`, then validation-window instructions are
stitched exactly as in v6. Unbuffered v6 is rebuilt as the reference and its
5 bps rf=0 Sharpe and annualized turnover must match the journal within
rounding before the surface proceeds.

The existing contract is close-t signal and next-close fill. In the grid,
`delay=0` means that existing next-close fill; `delay=1` and `delay=2` mean
one and two additional trading bars late. No target may be filled before its
decision date.

## Fixed execution surface

The full Cartesian product is evaluated:

* no-trade band `b in {0.00, 0.025, 0.05, 0.10}`;
* partial-adjustment fraction `a in {1.00, 0.50, 0.33}`;
* calendar tranching `tranches in {1, 4}`;
* additional fill delay `d in {0, 1, 2}` bars; and
* missed-rebalance probability `m in {0.00, 0.05, 0.10}`.

This is `4 x 3 x 2 x 3 x 3 = 216` configurations. The cell
`b=0, a=1, tranches=1, d=0, m=0` is unbuffered v6 and is the comparator.
Every cell is run independently through the fixed OOS windows; the harness
does not select among them per fold.

Definitions fixed before execution:

1. At a scheduled fill, compare the desired weights with the portfolio's
   post-return, pre-trade drifted weights. The no-trade band is a
   portfolio-wide L-infinity rule: if the largest absolute asset-weight
   change is less than `b`, skip the entire instruction. This preserves the
   desired portfolio's long-only, unlevered constraint rather than allowing
   unmatched buys and sells from per-asset suppression.
2. If the instruction is not skipped, trade to
   `current + a * (desired - current)`. Cash is the residual, so this convex
   update remains long-only and unlevered. This is the fixed
   Garleanu-Pedersen aim-portfolio implementation used here.
3. `tranches=4` creates four separately accounted sub-portfolios, initially
   25% of capital each. The month-end target observed at close t is queued for
   those books at offsets 0, 5, 10, and 15 trading bars; each then receives
   the common additional delay and the engine's next-bar lag. Offsets are
   fixed at approximately one week and are not tuned. Sub-portfolio NAVs are
   allowed to drift; aggregate returns, holdings, and dollar turnover are
   NAV-weighted, with no free daily rebalance among tranches.
4. Missed rebalances apply to the original monthly decision, before
   tranching, so a missed month suppresses all four queued instructions.
   PCG64 seed `1202` generates one Bernoulli mask for each nonzero `m`; that
   mask is reused by every other grid setting at the same `m`. The realized
   skipped count and fraction are printed. The random seed is not searched.
5. When queued instructions would collide, each tranche executes the most
   recently decided target available on that fill date. This rule is causal
   and deterministic.

## Costs and crossover

Report every configuration at one-way costs `0, 5, 10, 25, 50` bps. Costs
are charged on realized one-way turnover, including all tranche books.
Unbuffered v6 is charged the same cost in each comparison.

The primary output is the **cost crossover**. At every configuration, compute
`SR_variant(c) - SR_unbuffered(c)` at the five fixed costs. If the difference
is already positive at zero, report crossover `0 bps`. Otherwise, where the
sign first changes, report the piecewise-linear interpolation between the two
adjacent fixed cost levels. If it never becomes positive through 50 bps,
report `>50 bps / not observed`. The comparison uses rf=0 Sharpe for
continuity and also prints real-RF Sharpe. Crossover is descriptive; it does
not select a cell or add a strategy configuration.

Tracking error is annualized standard deviation of the daily net-return
difference from unbuffered v6 at the same cost. It is printed at every grid
cell and every cost.

## Pre-registered economic success criteria

Each configuration receives an independent pass/fail result at 10 bps. It
succeeds only if all of the following hold:

1. annualized turnover is at least 40% below unbuffered v6;
2. the lower endpoint of the paired 95% stationary-block-bootstrap interval
   for `SR_variant - SR_unbuffered` is above -0.10; and
3. maximum drawdown is no more than 2.0 percentage points worse, and the
   fifth-percentile daily return is no more than 5 bps worse, than unbuffered
   v6.

The drawdown and tail tolerances make “no material increase” numeric before
results are seen. The paired bootstrap uses 10,000 resamples, expected block
length 21, and fixed seed 0; the Ledoit-Wolf HAC counterpart and pairwise
correlation are also reported. Passing does not authorize selecting or
promoting a configuration.

## Leave-one-decade-out dependence

For every configuration, remove in turn all OOS observations in calendar
2000-2009, 2010-2019, and 2020-2029. On each remaining sample recompute the
10 bps Sharpe difference versus unbuffered v6, correlation, tracking error,
turnover reduction, maximum-drawdown difference, fifth-percentile difference,
and the same 10,000-resample paired bootstrap interval. These are diagnostic
slices of the same configurations, not additional trials. No decade is
selected or assigned greater weight.

## Exploratory v11 momentum-cost overlay

This section does **not** confirm v11. V11 used a different, unregistered
universe and remains explicitly exploratory. The Ken French 10 prior-return
decile data are loaded from the existing local archive; no external data are
ingested and the archive is not committed.

To expose the turnover omitted inside those daily reconstituted series, apply
fixed annual one-way turnover assumptions of `1x, 2x, and 4x per leg` to the
gross Hi-minus-Lo daily spread. At costs `0, 5, 10, 25, 50` bps per one-way
turnover, subtract the flat daily drag
`2 * assumed_turnover * cost_bps / 10,000 / 252`; the factor two charges both
winner and loser legs. Report annualized mean, volatility, Sharpe, maximum
drawdown, cumulative return, and the simple cost-adjusted estimate of the
13.8 percentage-point gross CAGR spread. These assumptions bracket cost
exposure; they are not observed turnover and do not make the decile products
tradeable.

The three turnover assumptions are three exploratory configurations. They
are logged under `trend-v12-execution-v11-overlay` on v11's 94 frozen folds,
scored at the pre-declared 25 bps midpoint: 3 configurations x 94 = 282 rows.
They are kept separate from the v6 execution surface and its DSR.

## Standard reporting and trials

Print the complete 216-cell surface at all five costs with CAGR, annualized
volatility, Sharpe at rf=0 and against real RF, maximum drawdown, worst day,
fifth-percentile day, annualized turnover, tracking error, and crossover.
Print SPY buy-and-hold and monthly 60/40 on the identical window at
0/5/10/25/50 bps. Print `metrics.by_subperiod` for unbuffered v6 and grouped
surface diagnostics at the standard ETF breaks. Print paired bootstrap/HAC
inference, leave-one-decade-out results, trials counts, and deflated-Sharpe
effective-breadth diagnostics. Positive, null, and negative cells receive the
same output.

Ledger accounting is fixed at:

* v6 execution surface: 216 configurations x 22 folds = 4,752 rows;
* exploratory v11 overlay: 3 configurations x 94 folds = 282 rows; and
* total: 219 configurations and 5,034 new rows across the two study ids.

The source store remains dual-source checked but not clean under the codified
2% rule. No futures series is purchased or ingested, and no futures-data
decision is made. Journal the result either way, then stop.
