# 2026-09-04 — planning decision: Q5, the statistical promotion gate (BINDING once signed)

Append-only. Answers Q5 in `CLAUDE.md`, open since 2026-09-01c. Per DESIGN.md
§8 this amends `2026-09-01-gate-preregistration.md` and takes effect only from
the retrain cycle following sign-off — never retroactively, and never on a
cycle already in progress.

## Q5's dilemma, and why it is false

Q5 posed a bind. Clause (a)'s ">= 0.10 Sharpe" is a point estimate against a
measured standard error of ~0.125, so it fires on noise. But requiring
p < 0.05 appeared to promote nothing ever, because the smallest detectable
difference at 80% power was computed as 0.351 Sharpe.

**That 0.351 is the answer for a low-correlation comparison, and it was
generalised to all comparisons.** The standard error of a *paired* Sharpe
difference collapses as the two series correlate, and a challenger worth
considering is by construction a variant of the incumbent, hence highly
correlated with it. This project's own realised numbers:

| Comparison | pair r | SE | min detectable @80% |
|---|---:|---:|---:|
| v17 A vs 60/40, excess, 10 bps | 0.9985 | 0.0061 | **0.017** |
| v15 monthly vs 60/40, excess | 0.9492 | 0.0360 | 0.101 |
| ETF-era v2 vs 60/40 (rf=0) | 0.7800 | 0.1349 | 0.378 |

v17 detected +0.018 at p = 0.0026 — a difference twenty times smaller than
Q5's stated floor. Statistical significance is therefore **not** prohibitive
for the challengers this gate will actually see. Q5's second horn does not
exist.

## Decision

Clause (a) is replaced, clause (c) follows it, (b) and (d) are unchanged, and
one clause is added.

**(a) — economic and statistical significance, both required.** On stitched
OOS **excess** returns over the aligned real risk-free series at 5 bps, the
challenger's Sharpe advantage over the incumbent must have a point estimate
of at least **0.10** AND a paired stationary-bootstrap 95% CI whose lower
bound is **above zero** (10,000 resamples, expected block 21, seed 0; the
Ledoit-Wolf HAC counterpart reported beside it and required to agree in sign).

**(c) — the same, at 10 bps.**

**(b) and (d) unchanged.** Max drawdown <= 1.25x incumbent; annualised
turnover <= 1.5x incumbent.

**(e) — NEW: era stability.** Condition (a) must also hold on the most recent
era subsample evaluated alone, under the fixed split already used by v15 and
v17. A challenger that passes only on the full window is not promoted.

Ties and marginal wins still keep the incumbent.

## Why this shape

The two halves of (a) fail in opposite directions and are therefore
complementary. The point estimate alone fires on noise, which is Q5's correct
complaint. The interval alone can be gamed: a challenger nearly identical to
the incumbent has correlation near one, a very small standard error, and can
clear significance on a trivial difference — v17's statistically clean +0.018
is worth roughly **$13 a year** on a $7,500 account. Requiring both means a
challenger must be *materially* better and *demonstrably* not noise. Neither
condition substitutes for the other.

0.10 is retained rather than lowered. Against the incumbent's 0.538 excess
Sharpe it demands an 18.6% improvement in risk-adjusted return, which is a
high bar deliberately: inertia is the correct prior and churn is a cost, as
the original pre-registration states. With significance now also required,
0.10 becomes the *binding* constraint in most cases — that is a deliberate
policy choice about how much improvement justifies switching, not an artefact
of statistical power, and it should be argued on those terms if it is ever
revisited.

Clause (e) exists because the single most persistent pattern across all
seventeen studies is a result that holds on the full window and dissolves
post-1980. A gate blind to that would have promoted strategies with no
demonstrated modern effect. Every prior finding this project produced would
have failed (e), which is the point.

## Effect on the current record

Under this gate v17's primary A still does not promote: it meets the interval
condition comfortably (+0.018, CI [+0.0066, +0.0304]) and fails the 0.10
point estimate, and separately fails (e). Nothing changes about the incumbent,
which remains the 60/40 balanced portfolio.

Note that clause (a) now requires excess-return inference by construction, so
the rf=0 defect recorded in
`2026-09-04-planning-review-phase4-execution.md` and
`2026-09-03-planning-finding-rf-zero-sharpe-bias.md` cannot re-enter through
the gate.

## Status

Requires Jaeyoung's sign-off in planning. Until signed, the four original
conditions of 2026-09-01 remain in force unchanged.
