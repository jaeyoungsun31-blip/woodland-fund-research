# 2026-09-02 — trend-v12: turnover frontier (INTERIM — frontier amendment only)

Append-only. Covers ONLY the frontier amendment to
`journal/2026-09-02-trend-v12-execution-preregistration.md`. The buffering,
tranching, delayed-fill and leave-one-decade-out arms of v12 are still
running; this entry is written now because the frontier result is complete,
self-contained, and decisive. Source:
`reports/trend-v12-execution-turnover-frontier.txt`.

OOS 2004-10-22 .. 2026-09-01, 5,499 bars, 22 folds.

## Result: the strategy has no turnover budget, because it has no gross edge

| cost | v6 GROSS Sharpe (zero turnover) | vol-target 60/40 NET | advantage | max viable turnover |
|---:|---:|---:|---:|---|
| 5 bps | 0.804 | 0.862 | **−0.059** | not funded |
| 10 bps | 0.804 | 0.859 | −0.056 | not funded |
| 25 bps | 0.804 | 0.850 | −0.047 | not funded |
| 50 bps | 0.804 | 0.835 | −0.032 | not funded |

Read the first column carefully: **0.804 is v6 before any trading cost at
all** — the hypothetical case where trading is free. The vol-targeted 60/40
benchmark, paying its own costs, still beats it at every level.

So the question the amendment was written to answer — "how fast can we afford
to trade?" — does not arise. There is nothing to spend. v6 starts behind the
benchmark with a zero-cost head start and never catches up. Monthly, weekly
and daily rotations (24x, 104x, 504x under our convention) are all unfunded,
not because costs are too high but because the gross edge is absent.

Planning's pre-registered guess was that the frontier would land near 10-15x
turnover, permitting biweekly decisions. That was wrong by the entire budget,
and is recorded as wrong.

## Precision about which benchmark

This is measured against **vol-targeted 60/40**, the strongest comparator in
the project. Accuracy, not excuse:

* vs SPY (0.660), v6 wins comfortably.
* vs plain 60/40 (0.806 vs 0.804), it is a dead tie.
* vs vol-targeted 60/40 (0.862), it trails at any turnover.

And the thing that makes that benchmark so hard to beat is **our own v9
result**: the de-levering overlay lifted 60/40 by +0.118 Sharpe. The project
found the thing that beats the project.

## What this settles, and what it does not

**Settles:** the "trade faster" question for this strategy on this window.
Higher-frequency variants of v6 cannot be justified by cost headroom, because
there is none. Execution improvements (bands, tranching) can still reduce
turnover and are worth measuring on their own terms, but they cannot manufacture
an edge that is not there at zero cost.

**Does not settle:** the deep-history picture. On 94 years v4/v7 found trend
significantly ahead of equities and level with a balanced portfolio. The
frontier is an ETF-window result on 21.8 years, where — per our own inference
work — differences of this size are not resolvable anyway (the −0.059 gap has
no confidence interval attached here and should not be read as significant).
The honest statement is that the ETF window offers no evidence of a gross edge
over the best simple benchmark, not that the edge is proven absent.

## Consequence for planning

Any future proposal to increase trading frequency must first demonstrate a
gross edge at zero cost against the vol-targeted benchmark. That is now a
standing requirement, recorded here.
