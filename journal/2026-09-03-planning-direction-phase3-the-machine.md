# 2026-09-03 — planning direction: build the machine

Append-only. Not a study. This records a change in what the project spends its
time on, and why.

## The diagnosis

Seventeen studies have drawn on the same 24,434 out-of-sample bars. They have
returned substantially the same answer each time, and the natural reading —
"momentum does not work" — is less complete than the structural one: **a fixed
dataset contains a finite amount of independent information, and this one has
been largely extracted.** Seventeen queries against 94 years of daily index
returns is well past the point of diminishing returns, and the trials ledger's
own effective-breadth warning has been saying so in a different vocabulary for
two weeks.

New information is available from exactly two sources, and neither is a study:

1. **New data.** Constituent-level, point-in-time, delisting-inclusive equity
   history. This converts v15's and v17's model-implied results into observed
   ones and closes the standing identification gap. `[Likely]` obtainable free
   through a university WRDS/CRSP subscription.
2. **Forward time.** A live loop, running against dates that did not exist
   when any model was fitted. Every observation it produces is genuinely
   out-of-sample in a way no backtest can be.

## What the project has and has not built

Built: a walk-forward research harness with embargo; an append-only trials
ledger at 10,108 rows; stationary-bootstrap and HAC paired inference;
deflated Sharpe with an honest effective-breadth caveat; a fixed era split;
dual-source data ingestion with integrity checks; a reporting layer; and
seventeen pre-registered studies with their results, corrections and
violations recorded.

Not built: **Phase 3 and Phase 4 — the retrain loop, the promotion gate in
executable form, live paper execution, and the drift monitor.** DESIGN.md's
opening framing was a *self-improving* strategy. The self-improving part has
never existed. The project has spent its time qualifying candidates to place
inside a machine it did not build.

DESIGN.md §11 said this would happen, in its own words: "the biggest schedule
risk is Phase 1 perfectionism and Phase 5 starting early. The loop (Phase 3)
is the point of the project — get there before making anything fancier."
That warning was correct and was not heeded.

## The direction

Research is not being abandoned; it is being **subordinated to the loop**. The
order is: finish the rf=0 correction, then build Phase 3, then Phase 4, and
only then consider new research — by which point a new idea costs a
configuration change and a fold count, not a two-day bespoke study.

The argument for this ordering is not tidiness. It is that **the apparatus
compounds and an individual signal does not.** Every study so far has been
built largely from scratch against the harness. With a loop in place, the
marginal cost of testing an idea falls by an order of magnitude, and the
project stops being seventeen one-off investigations and becomes something
that accumulates.

## What Phase 3 must contain

1. **An incumbent, declared and stored.** Today it is the 60/40 balanced
   portfolio, on the evidence of every study to date. The system must hold a
   named incumbent with its parameters, its stored OOS record, and the date and
   journal entry that made it incumbent.
2. **The promotion gate, as executable code** — the four conditions of
   `2026-09-01-gate-preregistration.md`, plus the statistical test the
   inference layer now supports, run automatically and never by hand. A
   challenger that fails is logged as a challenge, not silently discarded.
3. **The retrain job.** A scheduled cycle that refreshes data, runs integrity
   checks, refits the incumbent's parameters on the current window, evaluates
   registered challengers, applies the gate, writes to the ledger, and appends
   a journal entry. It must be able to run unattended and to decide "no change"
   — which will be its most common correct output.
4. **Refusal conditions.** The cycle must halt rather than trade on: failed
   integrity checks, stale data beyond a declared tolerance, a fold count that
   disagrees with the frozen scheme, or any sanity anchor breach. A loop that
   cannot refuse is not a loop, it is an accident with a schedule.
5. **The no-trade band.** Compute the ideal target every cycle; trade only the
   portion where the gap exceeds a pre-registered band. This is what reconciles
   daily *operation* with a turnover budget of 4.6x-9.3x per year
   (`2026-09-03-planning-note-turnover-budget.md`). The system runs constantly
   and trades rarely, by design.

## What Phase 4 must contain

Alpaca paper account; a daily execution job; and a **drift monitor** comparing
live fills against the simulated fills the backtest assumed. That monitor is
the single most valuable instrument the project can own, because it is the
only thing that measures real implementation cost rather than modelling it —
and modelled cost is the assumption every result in this repo rests on.

The first live paper rebalance executing untouched is the Phase 4 completion
criterion, unchanged from DESIGN.md §11.

## Standard that does not relax

Live operation does not lower the evidentiary bar; it raises it. Nothing is
promoted outside the gate. The journal remains append-only. Live results are
recorded whether or not they flatter the system, and a live period that
underperforms the incumbent is a journal entry, not a reason to intervene by
hand.
