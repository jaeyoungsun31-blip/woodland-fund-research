# 2026-09-02 — trend-v9-leverage: results

Append-only. Pre-registered in
`journal/2026-09-02-trend-v9-leverage-preregistration.md`; nothing below
deviates from it. Executed by the planning session (no coding agent available);
script delivered as `scripts/run_leverage_study.py`, raw output as
`reports/trend-v9-leverage-stdout.txt`.

OOS 2004-10-22 .. 2026-09-01, 5,499 bars, 5 bps, 10% annual vol target,
trailing 63-day realised vol lagged one bar.

## Headline: the leverage constraint is NOT what is holding this strategy back

Removing the gross-exposure cap does not improve the multi-asset trend
ensemble. It slightly degrades it, and it improves the baselines more.

| series | unlevered | L=2 s=0 | L=3 s=0 | L=2 s=100bp | L=3 s=100bp |
|---|---:|---:|---:|---:|---:|
| **v6 multi-asset** | **0.775** | 0.761 | 0.750 | 0.742 | 0.730 |
| 60/40 | 0.806 | 0.869 | 0.880 | 0.837 | 0.845 |
| vol-target 60/40 | 0.853 | 0.892 | 0.905 | 0.855 | 0.866 |

Levered-vs-levered paired comparisons: v6 trails both baselines at **every**
cap and spread (Δ −0.09 to −0.15), none significant (p 0.38–0.60) — the series
are only 0.55–0.64 correlated here, so the intervals are ±0.4 and this window
resolves nothing, exactly as the ETF window never does at that correlation.

The pre-declared expectation is confirmed on the level (Sharpe is
scale-invariant, so leverage moves it only through financing and the cap's
interaction with time-varying vol) and resolved on the uncertain part: **the
baselines benefit differentially more.**

## The mechanism, and it repeats a lesson this project already paid for

At L = 1.0 the overlay can only DE-lever. That alone lifts 60/40 from 0.806 to
**0.925** and vol-target 60/40 to 0.912, while v6 moves 0.775 → 0.771 — no
change at all.

The reason is that **the trend ensemble already manages its own volatility**:
when assets fall below trend it moves to cash, so exposure is already
vol-responsive and an external overlay is redundant. 60/40 is always fully
invested and has no such mechanism, so de-risking in high-vol regimes helps it
a great deal.

This is the v3 finding again, in a different costume: volatility management is
a portfolio technique that helps whatever lacks it, not an edge. It helped
60/40 more in v3, and it helps 60/40 more here.

## Realised leverage — why the cap barely binds

| series | mean k | median k | 95th pct | % of days at cap (L=2) |
|---|---:|---:|---:|---:|
| v6 multi-asset | 1.09 | 1.00 | 1.99 | 4.9% |
| 60/40 | 1.27 | 1.28 | 2.00 | 9.4% |
| vol-target 60/40 | 1.35 | 1.35 | 2.00 | 11.4% |

v6 wants less leverage than the baselines do, because its realised volatility
already sits near the target. Raising the cap from 2 to 3 changes almost
nothing for it (4.9% → 1.3% of days at the cap).

## What this decides

**It narrows the case for buying futures data, and sharpens it.**

The argument "our results are mediocre because we cannot lever" is now measured
and false for this strategy on this data. Leverage is not the unlock.

It does **not** say futures data is worthless. v6 established that the thing
which measurably helps is *breadth* — 9 US sectors are 1.44 effective bets;
6 asset classes are 2.47. Futures would buy 50-100 markets, and that case
stands untouched by this result. The conclusion is therefore precise: **buy
futures for breadth, not for leverage** — and only when the money is there.

## Trial accounting

18 configurations (3 caps × 2 spreads × 3 series), all reported. Nothing
fitted, nothing selected, no cap or spread called best. Deflation vacuous;
paired tests load-bearing, and they resolve nothing at this correlation.

## What this cannot conclude

Not tradeable, and never to be reported as such: cash ETF accounts cannot
borrow on these terms, and futures introduce roll, margin, and basis effects
this overlay does not model. The L = 1.0 arm is a de-levering overlay only and
IS implementable — that arm is worth planning's attention, since it lifted
60/40 by +0.118 Sharpe and is the single largest free improvement seen in any
study so far. It improves the benchmark, not our strategy.
