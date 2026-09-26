# 2026-09-02 — trend-v9-leverage: pre-registration (BINDING)

Append-only, written BEFORE the study runs (CLAUDE.md rule 3). Executed by the
planning session directly (no coding agent available); the same rules apply.

Study id: `trend-v9-leverage`.

## The question

Every result in this project has been produced under a constraint never
examined: long-only, gross exposure capped at 1.0. That cap is why v7/v8 are
framed as sleeve *weights* — 10% to trend is 10% taken away from something
else. Institutional trend programs are not constrained this way: they trade
futures on margin, hold every sleeve at full risk simultaneously, scale the
book to a volatility target, and hold unused capital in T-bills.

**v9 measures how much of our result is the constraint rather than the
signal.** This is a measurement, not a tradeable strategy — the output is not
implementable in a cash ETF account and must never be reported as if it were.

Its purpose is to make a spending decision evidence-based: if the unconstrained
version is materially better, that quantifies what futures-market access would
buy. If it is not, the money is saved and the constraint is exonerated.

## Method — no engine change

Volatility scaling with borrowing is a linear operation on the excess-return
series, so it is applied as an overlay to the existing stitched OOS series
rather than by modifying the long-only engine:

    k_t      = clip(target_vol / realised_vol_t, 0, L)
    r_lev_t  = rf_t + k_t * (r_t - rf_t) - max(k_t - 1, 0) * spread_t / 252

* `realised_vol_t` uses a **trailing 63-day** window ending at t-1 — the same
  window as v3, lagged so no scaling decision uses same-day information.
* `target_vol` = 10% annualised, fixed, not searched.
* `L` (leverage cap) in {1.0, 2.0, 3.0}. L = 1.0 reproduces the constrained
  case and is the regression check.
* Borrowing spread over the risk-free rate in {0 bps, 100 bps}. 0 bps is the
  institutional idealisation; 100 bps is the honest retail/futures-financing
  case. Both are reported; neither is treated as the headline alone.

## Series tested

1. `v6-multiasset` — the multi-asset trend ensemble (the best pure-trend
   strategy the project has produced).
2. `60/40` and 3. `vol-target 60/40` — the standing baselines.

## The control that decides the study

**The identical leverage overlay is applied to the baselines.** v3 taught this
lesson at cost: volatility targeting improved the trend strategy and improved
60/40 *more*, so an uncontrolled overlay flatters whatever it touches. If
leverage lifts strategy and baseline equally, leverage is not the unlock and
the futures-data case is not made. Any comparison in the results must be
levered-vs-levered.

## Reporting, fixed in advance

Sharpe at rf=0 and against the real risk-free rate; paired bootstrap (10,000
resamples, block 21) and HAC differences, levered-vs-levered; realised
volatility (to confirm the target was hit); max drawdown; worst day; the
realised leverage distribution (mean, median, 95th percentile, % of days at
the cap); and financing cost as a share of gross return. 0/5/10 bps trading
costs as standard.

## Trial accounting

3 leverage caps × 2 spreads × 3 series = 18 configurations, all logged. No cap,
spread, or target is selected or called best; the leverage cap is reported as a
curve. Nothing is fitted, so the deflated Sharpe hurdle is vacuous — the paired
tests are load-bearing.

## What this cannot conclude

It cannot promote anything. It cannot establish tradeability: cash ETF accounts
cannot borrow at these rates, and futures introduce roll, margin, and basis
effects this overlay does not model. A favourable result is an argument for
*acquiring futures data and re-running properly*, never for levering the
existing ETF implementation.

## Pre-declared expectation

Planning expects levering to raise the strategy's absolute return roughly in
proportion to leverage while leaving Sharpe close to unchanged (Sharpe is
scale-invariant; only the financing spread and the cap's interaction with
time-varying vol can move it). The genuinely uncertain part is whether the
strategy benefits *differently* from the baselines — that difference, not the
level, is the finding. Recorded in advance so neither outcome can be reframed.
