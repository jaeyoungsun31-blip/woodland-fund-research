# 2026-09-02 — trend-v6-multiasset: pre-registration (BINDING)

Append-only, written BEFORE the study ran (CLAUDE.md rule 3, AGENTS.md).
Study ids `trend-v6-multiasset` and `trend-v6-multiasset-dbc`. (Planning
named this v7 and then renamed it to v6 mid-session; no v6 previously existed
in the ledger, so the numbering is contiguous.)

## Question

Every study so far ran on one asset class: nine US equity sectors, which are
different labels on substantially the same bet. Does applying the *same*
trend rule across genuinely different asset classes do better — and, more
importantly, is the diversification real and measurable?

The framing matters. A 0.10 Sharpe difference needs ~269 years to resolve
(`journal/2026-09-01-inference-existing-studies.md`). **Correlation structure
is estimable from 21.8 years; mean returns are not.** So the diversification
evidence is the claim this window can actually support, and it is reported as
a first-class result rather than as colour beside a Sharpe.

## Universe

**Primary (`trend-v6-multiasset`)** — six broad, non-overlapping sleeves:

| sleeve | exposure | first bar | first 4m / 10m signal |
|---|---|---|---|
| SPY | US equity | 1998-12-22 | before window |
| EFA | intl developed equity | 2001-08-27 | before window |
| EEM | emerging equity | 2003-04-14 | before window |
| TLT | long Treasuries | 2002-07-30 | before window |
| IEF | intermediate Treasuries | 2002-07-30 | before window |
| GLD | gold | 2004-11-18 | 2005-02-28 / 2005-08-31 |

**Secondary (`trend-v6-multiasset-dbc`)** — the same plus DBC (commodities),
first bar 2006-02-06, first signal 2006-05-31 (4m) / 2006-11-30 (10m).

Both run on the **identical OOS window**, not a truncated one. A sleeve that
does not yet trade is simply not in trend and takes no weight; GLD is absent
for the first ~4 months of the window and DBC for the first ~19. Declaring the
secondary separately is what keeps the headline free of a sleeve that is
missing for the first 7% of the record. This is deliberate: shortening the
window to DBC's start would forfeit comparability with v2 and, by this
project's own power arithmetic, a ~20-year window still cannot resolve a 0.10
Sharpe difference, so nothing would be gained.

**Risk-off leg: cash at the real risk-free rate.** IEF and TLT are risk
sleeves here, held only when in trend — the defensive allocation is genuine
cash, earning the T-bill rate through the mechanism added in
`journal/2026-09-02-cash-realism.md`. Cash is left unallocated rather than
modelled as a synthetic asset, because an explicit cash column would make a
move to cash look like two trades and be charged twice.

## Signal — unchanged, and not re-optimized

The same equal-weight ensemble of 4-10 month lookbacks used by v2. **No
re-optimization of lookbacks, covariance, or volatility targets**: v4 showed
the lookback never stabilizes and averaging beats selecting (+0.063, p=0.023),
and v5 showed equal weighting beats inverse-vol and shrinkage minimum
variance. Those questions are settled; re-opening them here would spend trials
on answers we already have.

Frozen split scheme: 5y train / 1y validate / 1y step / 210-bar embargo,
declared `max_lookback_days=210`. Realized: **22 folds, OOS 2004-10-22 ..
2026-09-01, 5,499 bars — identical to v2 by construction.**

## Two studies, not one grid

Per the Q7 precedent: a two-config grid would make the harness select between
universes per fold, and v4 measured per-fold selection as actively harmful.
Expected ledger: 1 distinct config x 22 folds each, 44 rows total.

## Reporting, fixed in advance

* 0/5/10 bps; sub-periods; annualized turnover; deflated Sharpe with the
  effective-breadth note.
* Sharpe at rf=0 **and** against the real risk-free rate, per the cash-realism
  entry. All series — including the v2 incumbent — run through the
  cash-realistic engine so both sides are scored under the same rules.
* **Headline:** multi-asset ensemble vs the 9-sector v2 ensemble on the
  identical window, paired, through `woodland/stats.py` (10,000 resamples,
  block length 21) plus the HAC counterpart. Also vs SPY, 60/40, and
  vol-targeted 60/40.
* **Diversification, for both universes:** average pairwise correlation (with
  the most- and least-correlated pairs named), diversification ratio, and
  effective number of independent bets. Reported at equal weights (a property
  of the universe) and at realized average strategy weights (a property of
  what the strategy did with it).
* **External validation:** correlation and beta of our monthly series against
  AQR's published Time Series Momentum factor (Moskowitz, Ooi & Pedersen
  2012). Retrieved and stored with a source hash. If it had not been
  retrievable the study would say so and skip it — no proxy substituted.

### Measurement choices fixed now, not after seeing results

"Effective number of independent bets" is **DR²** (Choueifaty & Coignard
2008), which equals p/(1+(p-1)ρ) for p equicorrelated equal-risk sleeves and
is monotone in correlation. Meucci's (2009) PCA-entropy variant is reported
only as a cross-check, because an equally weighted equicorrelated portfolio is
exactly its own first principal component and the measure therefore returns
1.0 for *any* positive correlation before jumping to p at ρ=0. Both behaviours
are pinned in `tests/test_diversification.py`.

AQR's factor is long/short, volatility-targeted, across ~60 futures markets;
ours is long-only and unlevered on ETFs. A high **correlation** would be
evidence we capture the same phenomenon; a **beta near 1 is not expected** and
its absence is not a failure. Comparison is on monthly excess returns.

## Expectations recorded in advance

* Diversification statistics should improve **clearly** — six asset classes
  cannot plausibly be as correlated as nine US equity sectors. If they do not,
  something is wrong with the implementation, not with the idea.
* The Sharpe difference may well be **unresolvable**. Its standard error
  depends on the realized correlation between the two strategies, which is
  unknown before running: v5's schemes correlated 0.9957 with v2 and gave an
  SE of 0.020, but different universes will correlate far less, so the
  interval will be wider than that. I am recording now that a null on Sharpe
  alongside a clear diversification improvement is a plausible and honest
  outcome, not a disappointment to be explained away.

## What this study cannot conclude

Nothing is promoted; §8 is Phase 3. The source-verification caveat stands
(63 historical observations over the 2% cross-check threshold). ETF sleeves
carry real-world tracking and cost characteristics the FF deep-history series
do not, so this is not comparable to v4's 97.5-year result.
