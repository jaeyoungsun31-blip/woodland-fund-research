# 2026-09-02 — trend-v7-sleeve: pre-registration (BINDING)

Append-only, written BEFORE the study runs (CLAUDE.md rule 3). Written by
planning; the coding agent executes it and does not amend it.

Study ids: `trend-v7-sleeve-etf`, `trend-v7-sleeve-deep`.

## The direction change, and why

v1-v6 all asked: does trend BEAT a balanced portfolio? Two findings say that
is the wrong question to keep asking.

1. `journal/2026-09-01-inference-existing-studies.md` established that 21.8
   years cannot resolve a 0.10 Sharpe difference against a weakly correlated
   comparator — the ETF-window SE was 0.125 and nothing resolved.
2. v4 found trend beats equities significantly but **ties** the balanced
   benchmark over 94 years, with low correlation to both. That is the profile
   of a diversifier, not a replacement.

v7 therefore asks the question the evidence supports: **does adding a trend
sleeve IMPROVE a balanced portfolio?**

The change is not cosmetic — it is what makes the question answerable. The
comparison is paired between two portfolios sharing most of their holdings, so
the series will be ~0.98 correlated. v5 resolved a difference of 0.022 at
r = 0.996 (SE 0.020) on this same window, while the v2-vs-SPY comparison at
r = 0.78 resolved nothing (SE 0.125). Same data, same 21.8 years; the power
comes from pairing.

## Fixed design — nothing below is searched

**Sleeve (universe A):** the v6 multi-asset ensemble, unchanged — SPY, EFA,
EEM, TLT, IEF, GLD; 4-10 month equal-weight lookback ensemble; risk-off in
cash at the real T-bill rate. Reuse `trend.ensemble_targets` with the existing
LOOKBACKS. No re-optimisation of lookbacks, weights, or vol targets.

**Sleeve (universe B):** the v4 12-industry ensemble, unchanged. A multi-asset
sleeve cannot be built from Fama-French industries — they are all equities —
and no vetted bond or gold series exists in the store for this window. The
deep-history arm therefore tests the sleeve *question* over 94 years, not the
multi-asset sleeve. It is a robustness check on horizon, not a replication.

**Base:** universe A, 60% SPY / 40% IEF monthly. Universe B, 60% MKT / 40%
CASH. Both at 5 bps.

**Blends:** `combined = (1 - w) * base + w * sleeve` for w in {0.0, 0.1, 0.2,
0.3}. Cash residual in both; gross exposure 1.0; w = 1.0 not tested.

## Controls — the point of the study

Adding *any* diversifier improves a balanced portfolio. Without controls a
positive result says nothing about trend. At each w, matched vol:

| control | universe A | universe B |
|---|---|---|
| more defensive | (0.60 − 0.20w) SPY + (0.40 + 0.20w) IEF | shift 0.20w from MKT to CASH |
| gold | (1−w) × base + w × GLD | **unavailable — omitted, no substitute authorised** |
| static, no timing | (1−w) × base + w × equal-weight six sleeves | (1−w) × base + w × equal-weight 12 industries |

**The static control is load-bearing.** v6 established that the gain came from
diversification (1.44 → 2.47 effective bets). This control asks whether trend
*timing* adds anything beyond simply holding the diversified basket. If the
trend sleeve only ties it, the honest finding is that we built an expensive
way to hold a static allocation, and the results entry must say so plainly.

Universe B's controls are weaker by construction: equal-weight 12 industries
is close to a market proxy and also carries an equal-weight/size effect, so it
is a softer test than universe A's. Universe A is the primary test of timing;
universe B is the horizon check. Do not report B's control as if it were as
demanding as A's.

## Volatility matching — corrected

Sharpe is scale-invariant: multiplying a return series by a constant leaves it
unchanged. Matched-vol Sharpe is therefore identical to unscaled Sharpe and
must not be presented as a separate result.

Vol-matching applies ONLY to CAGR, max drawdown, worst day, and left-tail
(5th percentile daily) comparisons, where scale is real. Match by scaling the
MORE volatile side DOWN to the less volatile one — no cap, no leverage, and
every table names which side was scaled.

## Trial accounting

Configurations, per CLAUDE.md rule 4: universe A, 3 blend weights × 4 sleeve
types = 12; universe B, 3 × 3 = 9. **21 distinct configurations**, all logged,
including controls. The w = 0 base is the incumbent, not a trial.

Blend weights are **reporting points on a curve, not candidates**. No weight
is selected, ranked, or called "best". If a later entry singles one out, that
is selection and the trial count for any claim built on it must reflect it.

Nothing is fitted in this study — every weight is fixed in advance — so the
deflated Sharpe hurdle is vacuous (SR0 ≈ 0, DSR ≈ 1.000) and carries no
evidential weight. **The paired bootstrap and HAC tests are load-bearing.**
Report DSR with that note attached so it is not misread.

## Reporting, fixed in advance

Sharpe at rf = 0 and against the real risk-free rate; paired bootstrap
(10,000 resamples, block length 21) and HAC Sharpe difference vs the
unmodified base; max drawdown, worst day, 5th-percentile day; combined
portfolio turnover; **the correlation of every comparison pair**, so the
power behind each interval is visible; 0/5/10 bps; sub-periods (default
breaks for A, decades for B).

## What this study cannot conclude

It cannot promote anything — the §8 gate is Phase 3. It cannot establish that
trend has alpha; a sleeve that improves a portfolio may be contributing
diversification alone, which is exactly what the static control is there to
detect. Universe B is not a multi-asset replication. A positive result at one
blend weight is not evidence that that weight is optimal.

## Pre-declared expectation

Planning expects a modest, resolvable improvement in drawdown and left-tail
behaviour at w = 0.1-0.2, and considers it genuinely uncertain whether the
trend sleeve separates from the static control. Recording that in advance so
neither outcome can be reframed afterwards as the thing we expected.
