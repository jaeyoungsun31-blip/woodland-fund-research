# 2026-09-01 — trend-v5-riskweight: pre-registration (BINDING)

Append-only, written BEFORE the study ran (CLAUDE.md rule 3). HANDOFF
2026-09-01c step 5.

## Question

v1-v4 split the risky budget equally across whatever is in trend. Equal
weighting is a strong default with no parameters, but it ignores that a
utilities sleeve and an energy sleeve carry very different risk per dollar.
Does risk-based weighting beat it?

## Design

Universe, risk-off leg and split scheme are **identical to v2** so the
comparison is like-for-like against the incumbent equal-weight ensemble:
9 SPDR sector ETFs, IEF, frozen 5y/1y/1y/210-bar scheme, 22 folds, OOS
2004-10-22 .. 2026-09-01. The only thing that changes is how the in-trend
sleeve is weighted.

Both configs wrap the **v2 ensemble** (equal average of the seven fixed
lookbacks 4..10), because v4 established on 95 folds that averaging the
lookbacks beats selecting one.

| Config | In-trend weighting |
|---|---|
| `inverse_vol` | proportional to 1 / trailing standard deviation |
| `min_variance` | long-only minimum variance on a Ledoit-Wolf (2004) shrunk covariance |

**Risk-estimate window: 126 bars, pre-chosen, not tuned.** Six months is long
enough to estimate a 9x9 covariance and short enough to stay well inside the
210-bar embargo — a longer window would reach past it and
`check_embargo_covers_lookback` would refuse to run. Declared
`max_lookback_days` stays 210 (the trend filter's own reach, which dominates).

Implementation notes fixed in advance: Ledoit-Wolf shrinkage is toward a scaled
identity with the analytically optimal intensity, so the shrinkage strength is
not a free parameter. The minimum-variance problem is solved long-only
(`w >= 0, sum w = 1`) by projected gradient with an exact simplex projection;
the long-only constraint matters because unconstrained minimum variance takes
large offsetting positions in near-collinear assets, which is exactly where
estimation error does the most damage.

## Two studies, not one grid — a declared departure from the handoff's wording

The handoff says "two configs, both in the ledger". Both configs ARE in the
ledger. But they are run as **two single-config studies**
(`trend-v5-riskweight-invvol`, `trend-v5-riskweight-minvar`) rather than one
two-config grid, because a grid would make the harness pick between them
per fold — and v4 has just shown, on 95 folds, that per-fold selection is
actively harmful (ensemble beat selection by +0.063 Sharpe, p = 0.023) and
that the selection never stabilizes. Running the two schemes head-to-head
under a mechanism we have just measured as harmful would confound the question
being asked. Raised as Q7; trivially re-runnable as a grid if planning
prefers.

Expected ledger: 1 distinct config x 22 folds each, 44 rows total.

## Reporting, fixed in advance

0/5/10 bps; SPY and 60/40 over the identical window (rule 5, satisfied
literally here — this study is on the ETF universe); `metrics.by_subperiod`;
annualized turnover; deflated Sharpe with the effective-breadth note; and 95%
bootstrap CIs plus Sharpe-difference tests against **the v2 equal-weight
ensemble**, which is the incumbent this must actually beat.

## Expectation stated in advance

On the ETF window the SE of a Sharpe difference is ~0.125, so only a
difference above ~0.35 is detectable at 80% power. Two weighting schemes on
the same signal and universe will be highly correlated with v2 — likely above
0.95 — which sharply narrows the SE of *that particular* paired difference and
may make a small effect measurable. But I expect the honest outcome to be a
difference too small to call, and I am recording that expectation now so a
null result cannot later be framed as a surprise.

## What this study cannot conclude

Nothing is promoted; §8 is Phase 3. The source-verification caveat stands.
