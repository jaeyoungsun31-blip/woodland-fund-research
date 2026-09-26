# 2026-09-02 — Planning review of xsmom-v13-confirm

Append-only. Interpretation of the factual results in
`journal/2026-09-02-xsmom-v13-confirm-results.md`.

## The finding: the anomaly is real, and it is not harvestable

**Momentum predicts.** The Fama-MacBeth slope on the standardised decile-rank
proxy is positive and significant in the full sample (t = 3.73, p = 0.0002) and
in BOTH eras independently (t = 3.16 pre-1980; t = 2.22 post-1980). This is the
strongest predictive evidence the project has ever produced, and unlike the
trend result it does not decay across eras.

**And the cost of harvesting it exceeds its value at 11.2 bps.**

| cost | top-three − EW10 | p |
|---:|---:|---:|
| 0 bps | **+0.132** | **0.005** |
| 5 bps | +0.073 | 0.116 |
| 10 bps | +0.014 | 0.764 |
| 25 bps | **−0.164** | **0.0004** |
| 50 bps | **−0.459** | **<0.0001** |

Significant at zero cost. Gone by 5. Nothing at 10. **Significantly negative at
25 and beyond.** The era split does not rescue it: at 5 bps both eras' intervals
already cross zero.

This is the canonical limits-to-arbitrage result, produced from our own data:
a genuine, statistically significant, era-stable predictive signal whose
harvesting cost destroys it. It is a better answer than a positive one would
have been, because it explains why the anomaly survives in academic data at all.

## Why 11 bps is not a reassuring number

Model-implied internal turnover for top-three is **21.7x annually** (32.9x for
individual deciles, 65.8x for the long-short). The strategy requires trading
hundreds of individual stocks at that rate. Realistic retail all-in cost on
small- and mid-cap names — spread plus impact — sits well above 11 bps, and
plausibly in the 25-50 bps region where v13 shows the strategy **significantly
losing** to simply equal-weighting the same deciles.

The honest reading is not "it works below 11 bps." It is "our achievable cost
is on the wrong side of the crossover."

Caveat recorded: internal turnover is a pre-registered Gaussian rank-transition
ESTIMATE, not observed — the French archive exposes returns, not constituents.
The crossover is conditional on that model. It is unlikely to be conservative:
the model omits size dispersion, entry/exit, breakpoint jumps, impact, borrow
and capacity, all of which push true cost up.

## Cross-sectional momentum is closed on the same criterion as trend

Two research lines, two closures, one shared mechanism:

* **Trend (v1-v14):** no gross edge — trails the vol-targeted benchmark even
  at zero cost.
* **Momentum (v11-v13):** real gross edge, destroyed by cost at ~11 bps.

Different failure modes, same binding constraint: **our cost structure, not our
signal quality, is what limits this project.** That is now demonstrated twice,
by different routes, and it should be stated as the programme's central finding
rather than as a caveat on individual studies.

Note also that 60/40 MKT/CASH scored 0.858 against top-three's 0.701 at 10 bps.
The boring portfolio has now won on every window, in every study, at every
cost level tested.

## One question remains before the search phase closes

If cost is the binding constraint, the direct response is to trade less. **The
holding period has never been varied.** Every momentum test here rebalances
monthly. Quarterly, semi-annual and annual rebalancing cut turnover
dramatically while momentum's signal decays only gradually — the crossover
could move materially.

This is one pre-registered parameter reported as a curve, not a new strategy,
and it is the specific variable this result implicates. It is the last cheap
question. If low-turnover momentum also fails to clear its control at
achievable cost, the search phase is complete and the answer is known.

## Standing conclusion if that fails

Retail systematic equity and ETF strategies, on daily data, at achievable
costs, do not beat a vol-targeted balanced portfolio on this evidence. That is
a real, defensible, well-evidenced conclusion — reached through 15
pre-registered studies with honest negative results — and it is worth more as a
demonstrated research capability than a marginal positive would have been.

Remaining work would then be Phase 3 (promotion gate), Phase 4 (paper trading),
and publication of the record.
