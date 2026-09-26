# 2026-09-03 — planning note: the four axes, and which one this project has been working

Append-only. Not a study. Recorded because the question "how do we make the
model better / more advanced / more complex" has been asked repeatedly, and
because the honest answer is a reframing rather than another study. Future
sessions should read this before proposing sophistication as a remedy.

## The four axes

Whether a systematic strategy works is determined by four things, in
descending order of how much they usually matter:

1. **Information.** Data others do not have, or better processing of data they
   do. This project uses Ken French index portfolios and free ETF history —
   material every finance PhD has had since the early 1990s, in frictionless
   academic form. **This is the project's weakest axis by a wide margin.** The
   identification gap named in v15 and v17 is exactly this axis: constituent
   level, point-in-time, delisting-inclusive data would be the single largest
   improvement available, and `[Likely]` is free through a university
   WRDS/CRSP subscription.

2. **Cost.** The turnover budget is `K / cost`, K ~ 232 bps-turns
   (`2026-09-03-planning-note-turnover-budget.md`). The project's 25-50 bps
   figure is a **planning assumption that has never been measured.** At 5 bps
   the budget is 46x per year; at 25 bps it is 9.3x. That is the difference
   between whole classes of strategy being viable and not. Phase 4's drift
   monitor measures it within weeks.

3. **Structural advantage.** What a small account can do that a fund cannot:
   no mandate, no benchmark, no redemptions, no quarterly reporting, and no
   capacity constraint. **This project has never exploited any of it.** It is
   the only axis on which a retail participant structurally beats a large
   institution, and it points toward strategies too small to be worth a large
   book's attention — which come with their own costs: worse data, thinner
   liquidity, higher not lower implementation cost, and harder validation.

4. **Model sophistication.** More features, more capacity, fancier estimators.
   **This is the least important of the four** and it is the one the project
   has repeatedly been asked to pursue.

## What this says about seventeen studies

The project selected **large-cap US equity cross-sectional momentum** — among
the most researched and most arbitraged phenomena in finance. Decades of
academic attention and enormous deployed capital. Finding no exploitable
residual at retail cost is the expected outcome, and it is not evidence that
the method was insufficiently sophisticated. It is evidence about the choice
of battlefield.

Restated as a standing caution: **when a result disappoints, the first
question is which axis is binding, not whether the model should be more
complex.** Axis 4 has been the default answer and has never been the right
one.

## Consequence for sequencing

The order that follows from this is: build Phase 3 (so any attempt is cheap),
run Phase 4 (so axis 2 stops being an assumption), pursue WRDS/CRSP in
parallel (axis 1), and only then choose an axis deliberately. A study proposed
before those are done should be asked which axis it moves; if the answer is
axis 4, it is very likely the wrong study.

This note does not authorize any study. It is a filter for proposing them.
