# 2026-09-03 — planning note: the turnover budget

Append-only. Not a study and not a pre-registration. This is an arithmetic
consolidation of numbers already journalled in v13 and v15, recorded because
it converts five scattered results into one design constraint that should
govern every future study's choice of trading frequency.

## The observation

For each configuration whose model-implied turnover and solved cost crossover
are both already on the record, the **product** of the two is close to constant:

| Configuration | annual turnover | crossover (bps) | product |
|---|---:|---:|---:|
| v13, daily-reconstituted top three | 21.736 | 11.168 | 242.7 |
| v15, monthly | 4.5842 | 52.516 | 240.7 |
| v15, quarterly | 2.5542 | 85.991 | 219.6 |
| v15, semi-annual | 1.7057 | 135.550 | 231.2 |
| v15, annual | 1.0896 | 208.110 | 226.8 |

Mean `K = 232 bps-turns`; the whole spread is 220–243, about 10% of the mean.

## Why it holds, and what would break it

Net Sharpe falls approximately linearly in cost with slope proportional to
turnover, so the crossover cost `c*` at which the gross edge is exactly
consumed satisfies `c* x turnover ~ gross_edge / k`. Across v15 the gross
Sharpe advantage barely moved (+0.1054 to +0.1260 versus EW10), so the
right-hand side is near-constant and the product is too. The invariant is
therefore a restatement of "the gross edge is frequency-insensitive over this
range", which is itself the v15 finding.

`[Certain]` the arithmetic. `[Likely]` the invariant holds within this
project's studied range. `[Speculative]` and importantly, it should **not** be
extrapolated far above 22x turnover: at higher frequencies the gross edge is
not the same edge, market impact stops being linear in traded notional, and
the estimate would understate cost. It is an upper bound out there, not a
forecast.

Inherits every limitation of its inputs: both v13's and v15's turnover figures
are model-implied, not observed, and omit size dispersion, entry/exit,
breakpoint jumps, impact, borrow and capacity — all of which push true cost
up and the sustainable turnover down.

## The constraint, stated usefully

    maximum sustainable annual turnover  ~  232 / (all-in one-way cost in bps)

| All-in one-way cost | Max turnover | ~ % of book traded per day |
|---:|---:|---:|
| 1 bps | 232x | 92% |
| 5 bps | 46x | 18% |
| 10 bps | 23x | 9.2% |
| 25 bps | 9.3x | 3.7% |
| 50 bps | 4.6x | 1.8% |

Planning's standing retail cost range is 25–50 bps. **The turnover budget for
this project is therefore roughly 4.6x to 9.3x per year.** v15 monthly, at
4.58x, sits at the 50 bps edge and comfortably inside the 25 bps one. Weekly
(~25x) and daily reconstitution (~22x) both require costs near 10 bps and are
outside the budget. Anything trading multiple times per day is two to three
orders of magnitude outside it.

## Consequence for study design

Trading frequency is not a free design choice to be explored study by study.
It is bounded above by the cost structure the project actually faces, and that
bound is now quantified. A future study proposing a frequency above roughly
9x annual turnover must state, in its pre-registration, what specifically it
believes changes `K` — a larger gross edge, or a lower cost — and it must be
tested against this note rather than around it.
