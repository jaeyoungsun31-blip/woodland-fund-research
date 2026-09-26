# 2026-09-05 — planning decision: cost aggregation for the measured-cost protocol

Append-only. Answers the open rule in the cost-calibration protocol: the drift
monitor measures cost per symbol, `config/universe.yaml` declares one
portfolio-wide scenario list, and the protocol did not say how to reconcile
them. Requires sign-off.

## Decision

**Per-symbol costs, added alongside the existing flat scenarios, never
replacing them.**

## Why not the highest per-symbol median

Rejected. It lets the least liquid holding set the rate for the entire
portfolio regardless of how little of it is traded. A strategy holding 95%
SPY and 5% GLD would pay GLD's rate on the SPY turnover, which is not
conservatism but a fabricated penalty. Worse, the severity is unbounded and
arbitrary: adding one illiquid asset to a universe silently re-prices every
other trade in it, so the measure would punish diversification — the one
mechanism this project has actually found to work.

## Why not the equal-weight median across symbols

Rejected, and it is the weakest of the three. Cost is incurred on traded
notional, not on symbol count. An equal-weight average over symbols gives a
symbol that is never traded exactly the same influence as one traded every
cycle. It is an average of the wrong quantity, and it would drift further
from truth as the universe widens.

## The scalar that would be correct, and why it cannot be a config constant

The single rate that makes a scalar model agree with a per-symbol model is
the turnover-weighted mean:

    effective_rate = sum_i( c_i * |dw_i| ) / sum_i( |dw_i| )

This is exact. It is also **strategy-specific**: it depends on how a given
strategy distributes its turnover across symbols, so two strategies evaluated
on the same universe require different scalars. A configuration file holds one
number per scenario and therefore cannot express it. That the only correct
scalar is not a constant is the proof that the scalar model is the wrong
model.

## The decisive argument for per-symbol

The purpose of this protocol is to compare strategies at their true cost. A
single rate charges every strategy the same price regardless of what it
trades, which erases a real and economically meaningful difference: **a
strategy that concentrates its turnover in cheap instruments genuinely costs
less than one that spreads the same turnover into expensive ones.** Under a
scalar the two are indistinguishable, and the gate could promote the more
expensive of them. Measured SPY and IEF already differ by a factor of four
(0.130 vs 0.542 bps); a wider universe will disperse further.

## Specification

1. **Engine.** `woodland/backtest.py` currently charges
   `cost_rate * sum|dw|`. It becomes `sum_i( cost_rate_i * |dw_i| )` — a dot
   product over per-symbol deltas that already exist before the present sum.
   A scalar `cost_bps` remains accepted and is applied uniformly, so every
   existing call site behaves identically.

2. **Configuration.** `cost_bps_scenarios: [0, 5, 10]` is retained unchanged
   and remains mandatory in every report. A new, separately named measured
   scenario carries a per-symbol mapping. **Nothing is replaced.** Every
   result is reported at both the assumed and the measured scenarios, always,
   so no historical number silently changes meaning and any divergence between
   the two is visible rather than inferred.

3. **Unmeasured symbols.** A symbol with fewer than the protocol's minimum
   reconciled observations takes the **highest measured per-symbol value** as
   its rate. The rejected max-rule is correct precisely where the project is
   ignorant, and nowhere else. Every report states the number of symbols
   priced from measurement and the number priced from the fallback; a
   challenger whose universe is mostly fallback is reported as such and its
   cost result is not treated as measured.

4. **Both bias directions on every figure.** IEX quotes bias the measured
   spread upward; the paper simulator biases realised cost downward
   (`2026-09-04-planning-note-what-paper-trading-can-measure.md`). Neither is
   netted. Both are stated wherever a measured cost appears.

5. **Reproducibility is a precondition.** Before the measured scenario is used
   for anything, `scripts/reproduce_all.py` must reproduce every journalled
   number at the flat scenarios to their existing precision. If the engine
   change moves any historical figure at all, the change is wrong and is
   reverted rather than re-baselined.

## Consequence for the turnover budget

`K ~ 232` was derived under a single-rate assumption and remains valid as
stated, on its own terms. Under per-symbol costs the budget becomes
strategy-specific — a strategy trading only SPY has a materially larger budget
than one trading the same turnover across six assets. `2026-09-03-planning-
note-turnover-budget.md` is not amended here; a future entry should record the
generalisation once measured coverage is wide enough to compute it.
