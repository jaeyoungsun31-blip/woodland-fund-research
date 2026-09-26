# 2026-09-02 — Planning decision: the trend family is closed on the ETF window

Append-only. Follows the v14 ablation result (no stage passed either
pre-registered criterion) and the v12 frontier (no turnover budget at zero
cost). This is a research-programme decision, not a study.

## The complete record on the tradeable window

| study | question | answer |
|---|---|---|
| v1 | does per-fold lookback selection work? | no — 0.612, lost to both baselines |
| v2 | does averaging lookbacks beat selecting? | **yes** — 0.700, confirmed significant in v4 |
| v3 | does vol targeting help? | helps the benchmark more |
| v5 | does risk-based weighting beat equal weight? | no — inverse-vol 0.679, min-var 0.624 vs 0.700 |
| v6 | does multi-asset breadth help? | **yes on risk** — 1.44 → 2.47 effective bets, drawdown halved |
| v7 | does trend improve a balanced portfolio? | yes, and beats the static control — but loses to a gold sleeve |
| v8 | do blended sleeves add edge? | no — none reliably beat static gold |
| v9 | is leverage the binding constraint? | no — levering made it worse, helped baselines more |
| v12 | how fast can we afford to trade? | **no budget at any cost, including zero** |
| v14 | do any pipeline stages contribute? | **no — 0 of 8 ablations passed** |

## The v14 result

S1 dispersion +0.023 (CI crosses zero) — the one genuinely new idea, and
planning's own nominated best bet. It failed. S2 inverse-vol ~0. S3 symmetric
and asymmetric vol targeting ~0. No-trade bands added little. **S4 partial
adjustment retained v12's 46.2% turnover reduction with no measurable Sharpe
loss** — the only stage that did anything, and it does efficiency, not edge.
No LODO was triggered because nothing passed. Ledger: 9 configurations, 198
fold rows.

**Caution on S2 min-variance (+0.071, CI [−0.095, +0.241], turnover +22%).**
This is the largest point estimate in the study and it will be tempting. It
should not be acted on. Its interval spans zero by a wide margin, it costs 22%
more turnover, and **v5 found min-variance the WORST standalone configuration
(0.624 against equal weight's 0.700)**. Two studies producing opposite signs on
the same component is what a null field looks like when sampled twice. Treating
this as a lead would be selection from noise, and it is recorded here so that
no later entry can pick it up as a finding.

## The decision

**The time-series trend family is closed for further research on the ETF
window.** No further studies will be commissioned to improve it there.

Justification: ten studies, no gross edge against the vol-targeted 60/40
benchmark even at zero trading cost, and every stage-level improvement has now
failed under pre-registered test. This is a completed research programme with
an answer, not an abandoned one.

**What remains adopted from it**, because these earned their place:
* the lookback ensemble (v2, confirmed in v4 at p = 0.023)
* the multi-asset universe (v6)
* partial adjustment at 0.50 (v12, re-confirmed in v14)

**What this decision does NOT say.** On the 94-year deep-history window, v4
found trend significantly ahead of equities (+0.152, p = 0.014) and level with
a balanced portfolio. That result stands and is not overturned. The closure is
specific: **the effect is not harvestable by us, on this universe, at these
costs, over the window we can actually trade.** The distinction between "the
effect does not exist" and "we cannot harvest it" is preserved deliberately.

## What the whole programme found

Three things worked across thirteen studies: **don't select a parameter**
(average instead), **hold more genuinely different things** (breadth), and
**trade less** (partial adjustment). Every one is a form of doing less. Every
attempt to do more — selection, risk weighting, vol targeting, leverage,
regime conditioning, blending, pipelining — failed or helped the benchmark
more.

That is the project's substantive finding and it should be stated as such in
any write-up, ahead of any individual Sharpe number.

## Next

Primary line is now `xsmom-v13-confirm`: cross-sectional equity momentum, the
only strategy in the project with a demonstrated gross edge (monotone 94-year
decile spread, control cleared at p = 0.005 — exploratory, costs unmodelled).
Phases 3 and 4 (promotion gate, paper trading) remain unstarted and are the
largest gap between this research and a system.
