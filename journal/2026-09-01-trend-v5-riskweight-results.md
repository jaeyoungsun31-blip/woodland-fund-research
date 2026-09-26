# 2026-09-01 — trend-v5-riskweight: results

Append-only. Pre-registered in
`journal/2026-09-01-trend-v5-riskweight-preregistration.md`; nothing below
deviates from it, including the expectation of a null, which was recorded in
advance. Ledger: `trend-v5-riskweight-invvol` and `trend-v5-riskweight-minvar`,
1 config x 22 folds each.

Harness output. Nothing is promoted; §8 is Phase 3.

Window: OOS 2004-10-22 .. 2026-09-01, 5,499 bars (21.8y). Universe, risk-off
leg and split scheme identical to v2, so this is a like-for-like test against
the equal-weight incumbent. Risk-estimate window 126 bars.

## Result: equal weighting wins. Neither scheme improves on it.

| Portfolio | CAGR | Ann. vol | Sharpe | Max DD | Turnover |
|---|---:|---:|---:|---:|---:|
| **v2 equal-weight @5bps** | **9.72%** | 14.82% | **0.700** | −37.62% | 5.78 |
| v5 inverse-vol @5bps | 9.07% | 14.30% | 0.679 | −37.77% | 5.82 |
| v5 min-variance @5bps | 7.58% | 13.09% | 0.624 | −36.99% | 7.07 |
| SPY buy&hold | 11.24% | 18.84% | 0.660 | −55.19% | 0.00 |
| 60/40 @5bps | 8.33% | 10.62% | 0.806 | −32.34% | 0.23 |

Both schemes reduce volatility, as designed, and give back more in return than
they save in risk. The ordering is identical at 0 and 10 bps, so costs are not
what decides it — though min-variance also trades **22% more** than equal
weight (7.07 vs 5.78 annually) to arrive somewhere worse, which is the least
defensible combination available.

## The inverse-vol null is a tight one, and that is the interesting part

| comparison | ΔSharpe | 95% CI | p (boot) | p (HAC) | corr with v2 | SE |
|---|---:|---|---:|---:|---:|---:|
| inverse-vol − v2 | −0.022 | [−0.057, **+0.015**] | 0.238 | 0.284 | **0.9957** | 0.020 |
| min-variance − v2 | −0.076 | [−0.240, +0.099] | 0.386 | 0.392 | 0.9204 | 0.089 |

Neither is significant, but "not significant" understates what the first row
says. Inverse-vol is **99.57% correlated** with the equal-weight ensemble, so
the paired standard error collapses to **0.020** — six times tighter than the
0.125 typical of comparisons on this window. The interval therefore rules out
inverse-vol being better by more than **+0.015 Sharpe**.

That is a genuinely informative negative result, not a shrug: we cannot say
inverse-vol is worse, but we *can* say it is not meaningfully better, and the
data is sharp enough to have detected it if it were. The pre-registration
predicted exactly this mechanism — high correlation narrowing the SE of the
paired difference — and it held.

Min-variance is a different case: correlation 0.92 leaves SE at 0.089, so its
−0.076 point estimate cannot be separated from zero. Its interval still leans
clearly negative, and it has no dimension on which it wins.

## Sub-periods @5bps

| Period | inverse-vol | min-variance | v2 (reference) |
|---|---:|---:|---:|
| 2004-10-22..2008-01-01 | 1.003 | 1.188 | 1.020 |
| 2008-01-01..2015-01-01 | 0.646 | 0.657 | 0.626 |
| 2015-01-01..2020-01-01 | 0.696 | 0.728 | 0.691 |
| 2020-01-01..2022-01-01 | 0.924 | 0.633 | 0.979 |
| 2022-01-01..2026-09-01 | — | **0.218** | 0.527 |

Min-variance beats v2 in three of five sub-periods and still loses overall,
because it collapses in the most recent one (Sharpe 0.218, CAGR 2.01%, 940
days in drawdown). Concentrating into whatever has been quiet is a bet that
recent quiet persists; in 2022+ it did not. This is a good illustration of why
rule 5 requires the sub-period table — the blended number alone would have
hidden both the mid-sample strength and the recent failure.

## Deflated Sharpe

inverse-vol 0.68, min-variance 0.62, one config each, SR0 = 0.00, DSR 0.999
and 0.998. Per the Q2 decision the effective-breadth note is attached: a
single-config study has no search breadth, so the DSR hurdle is vacuous here
and carries no evidential weight. The paired comparisons above are the
load-bearing statistics.

## Reading

Equal weighting survives a serious attempt to beat it. That is worth
recording as a positive finding about the incumbent rather than only a
negative one about the challengers: the parameter-free choice is not merely a
convenient default here, it is at least as good as two standard risk-based
alternatives, one of which required estimating and shrinking a 9x9 covariance
at every rebalance.

Consistent with v4's lesson: on this signal, the estimation-light choice keeps
winning. Selecting a lookback lost to averaging them; weighting by estimated
risk lost to not estimating it.

## Caveats

Source-verification caveat stands. rf = 0 flatters all levels. The 126-bar
risk window was pre-chosen and not tuned — a different window could change
these numbers, and a search over windows would need its own pre-registration
and would carry a real deflation cost. Nothing here is promoted.
