# 2026-09-01 — First dual-source ingest: Tiingo cross-check results

Append-only. Records the outcome of the first full dual-source ingest, as the
handoff required ("journal the result either way").

## Headline

The two feeds corroborate each other on ~99.6% of observations, and where they
disagree it **does not reach a result**. But the run is **not clean** under the
check as written, so per the handoff **the single-source caveat is NOT lifted**
and remains on every number until planning rules on the threshold policy (see
QUESTIONS FOR PLANNING in CLAUDE.md).

## What ran

Yahoo (primary) vs Tiingo (cross-check), comparing **adjusted closes in return
space**, all 20 tickers, 122,905 day-ticker observations, 1998-12-22..2026-09-01.

Comparing adjusted rather than raw closes is deliberate: the adjusted series is
what the backtest consumes, and Yahoo's raw close is split-adjusted while
Tiingo's is as-traded, so raw comparison would flag every split as a false
disagreement. Comparing returns rather than levels is also deliberate: the two
providers use different adjustment epochs, which scales every level by a
constant and leaves returns identical.

## Results

| | |
|---|---|
| median absolute daily return difference | **1.7e-7** (i.e. identical to rounding) |
| observations > 50 bps apart | 484 / 122,905 = **0.394%** |
| tickers with zero disagreements > 50bps | SPY, XLC |
| worst ticker | XLB — 58 days > 50bps, max 8.7% on 2008-10-13 |

Disagreements are **rare, old, and clustered in volatile sessions** — 2008 for
seven tickers, then 2014, 2007, 2003, 2000. They arrive in consecutive pairs
of opposite sign (2008-10-10/13, 2003-01-29/30, 2006-06-09/12, 2007-02-28/03-01),
which is the signature of a single differing CLOSE price rather than a missed
distribution: one bad close perturbs two consecutive returns. Newer data is
essentially perfect — XLC (2018-) has zero disagreements at any threshold.

Reading: this is normal provider disagreement on closing-price convention
(consolidated vs primary-exchange vs official auction close) plus historical
revisions in old data. It is not evidence that either feed is corrupt.

## Does it reach a result? Measured, not assumed

Same code, two feeds, 6955 common bars 1998-12-22..2026-08-31:

| strategy | Sharpe (Yahoo) | Sharpe (Tiingo) | ΔSharpe | ΔCAGR | ΔmaxDD |
|---|---|---|---|---|---|
| SPY buy&hold | 0.53037 | 0.53051 | 0.00015 | 0.003pp | 0.012pp |
| 60/40 monthly @5bps | 0.77026 | 0.76603 | **0.00423** | 0.046pp | 0.015pp |
| sectors equal-weight @5bps | 0.58100 | 0.58188 | 0.00088 | 0.021pp | 0.017pp |

The largest Sharpe difference across 27.7 years is **0.0042**. The promotion
gate's smallest decision is a **0.10** Sharpe improvement (§8). Source
disagreement is therefore roughly **24x smaller than the finest distinction the
gate can draw**, on the noisiest baseline of the three.

## The cross-check earned its keep immediately

Two findings the second source produced on its first run:

1. **2026-08-28 is confirmed a real trading day.** Tiingo has the bar for all
   20 tickers; Yahoo is missing it for 13. Last session this could only be
   inferred from the cross-sectional calendar check; it is now established.
   That date is a Yahoo defect, not a market event.
2. **A transient Yahoo failure was caught.** SPY's first fetch this session
   returned "possibly delisted; no price data found" — a yfinance rate-limit
   artefact mid-run. Re-fetched clean (6965 rows, cross-check ok, 0 days over
   tolerance, max 17bps). Worth noting that the store can silently retain a
   stale ticker when one fetch fails while others succeed.

## Verdict policy — deliberately NOT decided here

`crosscheck_sources()` currently fails on ANY single day over tolerance. That
rule was written before seeing real data, on the reasoning that silent
corruption is usually a one-day event and a fraction-based rule would wave it
through. Against real data it flags 18 of 20 tickers.

The threshold is a methodology tradeoff, so per the two-chat protocol it goes
to planning rather than being tuned here — tuning a gate until it passes is
precisely the move this project exists to avoid. Recommendation and options
are in QUESTIONS FOR PLANNING.

Until then: **caveat stands.**
