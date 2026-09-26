# 2026-09-04 — planning review: the cycle reports zero turnover while submitting orders

Append-only. A measurement-integrity defect found in the first day of live
paper operation. No order needs undoing; the positions are correct and the
fills were clean. What is wrong is the record.

## Evidence

`journal/2026-09-04-phase3-cycle-145035.md`, the 14:50:35 cycle, states:

    No-trade band: 5.0%
    Realized one-cycle turnover: 0.000000
    Annualized turnover: 0.000x (below 4.6x-9.3x retail budget range)
    Paper orders: 4

Four orders were handled — two reconciled, two newly submitted — in a cycle
whose own record asserts that turnover was exactly zero.

## Mechanism

The no-trade band is applied when bounding the *target*. In that cycle the
bounded target was `SPY 0.6022491, IEF 0.3977509`, a drift of 0.225 points
from 60/40. The band correctly judged that inside its 5-point threshold and
recorded no rebalance.

`PaperBroker.submit_rebalance` then ignored that judgement. It recomputes
share-level deltas from live equity and quote midpoints and submits any delta
larger than `1e-9`. The band and the broker are two independent decisions
about whether to trade, and only the first one is reported.

Consequence: **every cycle will trade, and every cycle will report that it did
not.**

## Scale

About 0.45% of the book per cycle, roughly $450 on the $100k paper account.
Run daily that is approximately **1.13x annualised turnover** — inside the
4.6x-9.3x budget from `2026-09-03-planning-note-turnover-budget.md`, so this
is not a runaway. The severity is not the magnitude.

## Why it is serious anyway

`K ~ 232` makes turnover the binding operational constraint of this entire
project, and the journal's turnover figure is the instrument that polices it.
An instrument that structurally reports zero cannot detect a violation. Had
the drift been 5% rather than 0.45%, the record would have said `0.000000`
just the same.

This is the same failure class as
`2026-09-03-planning-finding-rf-zero-sharpe-bias.md`: the system measuring
itself with a method that cannot see the thing it is meant to measure, and
recording the result as fact in an append-only log. Both were found by
looking at a number and asking what it was actually computed from. Neither
was caught by a passing test suite.

## Required

1. Submission honours the band. A symbol whose live weight gap is inside the
   band is not traded.
2. The reported turnover is the **actually submitted notional over equity**,
   not the bounded-target delta. Where the two could ever disagree, report
   both.
3. Prior cycle journals are not edited. They are the record, including the
   wrong number. This entry is the correction.

## Related, same code path

`plan_rebalance` reads `/positions` but not open orders, so a cycle running
while a previous cycle's orders are unfilled would size against stale
positions and submit again. Sub-second exposure on liquid market orders, but
a genuine double-submit path, and it lives in the function being changed.
Fix it in the same pass.
