# 2026-09-03 — planning decision: research termination criterion, and withdrawal of v16

Append-only. Two decisions, recorded together because they have the same cause.

## Diagnosis

Twelve studies have been pre-registered and run. None has promoted anything.
That is not, by itself, a failure — pre-registered nulls are the intended
output of this design, and a project whose studies always passed would be
fitting rather than testing.

The failure is structural and it is this: **the project has never had a
stopping rule.** No condition was ever specified under which the research
phase ends. Absent one, the only available response to a null result is
another study, and the sequence v2 through v15 is what that produces. Each
study was individually sound. The sequence was not, because it could not
terminate.

Planning owns this error. Planning generated the next study every time a
result came back null, which kept the project feeling active while deferring
the conclusion its own evidence had already reached.

## Decision 1 — v16 is withdrawn

`journal/2026-09-03-xsmom-v16-costaware-preregistration.md` is withdrawn
before execution. It is retained on the record, unedited, as pre-registrations
always are; it is simply not run.

Reason: its own pre-registered prediction section states `[Likely]` that C2
fails and `[Likely]` that C3 fails. Planning wrote down an expectation of
failure and then scheduled the run anyway. A study whose author expects it to
fail, proposed at the point where the project's problem is diagnosed as
tactic-generation, is the diagnosed problem rather than a response to it.

This is not a claim that the cost-aware-objective hypothesis is false. It is
untested and remains untested. If it is ever revived, the pre-registration
stands as written and the grid may not be widened.

## Decision 2 — the termination criterion (BINDING)

The research phase of this project ends, and the deliverable becomes the
write-up plus Phases 3 and 4, when **either** of the following is true:

**T1 — the last open question closes.** `sleeve-v17-overlay` completes and
its primary comparison A (fixed `s = 0.10`) fails criterion C1. The v17
pre-registration already commits to this in its own words: "the correct
conclusion is that the project's finding is a negative one, and the
deliverable is the write-up."

**T2 — a new study cannot state what it changes.** Any proposed study must
name, in its pre-registration, the specific quantity it expects to move that
prior studies did not: a larger gross edge, a lower cost, a different
incumbent, or an identification gap closed with new data. A study that cannot
name one is a tactic, not a hypothesis, and is refused at proposal.

Under T2, three named directions are closed as of today unless new data
arrives: further trend-family variants (closed 2026-09-02), further parameter
or frequency variation within the existing momentum construction (bounded by
`2026-09-03-planning-note-turnover-budget.md`), and any study whose incumbent
is not the 60/40 control that has outperformed in every study to date.

The one direction that survives T2 is **closing the identification gap** —
obtaining constituent-level, point-in-time, delisting-inclusive equity data,
under which v15's model-implied result becomes an observed one. That is a
data acquisition problem, not a study, and it does not restart the research
phase on its own.

## What this means in practice

Remaining work, in order: v17 → the write-up → Phase 3 (retrain loop and
promotion gate) → Phase 4 (paper trading). DESIGN.md §11's own words apply:
"The loop (Phase 3) is the point of the project — get there before making
anything fancier."

Requires Jaeyoung's sign-off in planning to take effect. Until signed, it is
a proposal.

---

## Addendum, same day — T1's condition is met

`sleeve-v17-overlay` completed. Primary comparison A (fixed `s = 0.10`)
**failed C1**: delta Sharpe -0.005399 at 10 bps, bootstrap 95% CI
[-0.017774, +0.006794], p=0.3889. C3 also failed. Evidence:
`journal/2026-09-03-sleeve-v17-overlay-results.md`.

Three features of that result make it a stronger closure than a bare null:

1. **The response is monotone and adverse, gross as well as net.** Delta
   Sharpe versus 60/40 ran -0.000145, -0.000928, -0.003901, -0.008129 across
   sleeve weights 5/10/20/30% **before any cost**. More sleeve is monotonically
   worse. That is a signal, not noise, and it points the wrong way.
2. **The comparison is unusually well powered.** Paired correlation was
   0.998523, giving a 95% interval roughly 0.024 wide. This is a precise "no",
   not an underpowered "cannot tell". The project has been careful about this
   distinction throughout and it matters here.
3. **The mechanism was measured, not assumed.** The diversification
   diagnostic showed the benefit is real but tiny — 1.0148 effective bets at
   the primary weight. The overlay did not fail because diversification was
   absent; it failed because the diversification was economically
   insufficient. That is a more informative negative than "it didn't work".

The research phase therefore ends on the condition this document specified in
advance, on a result that was pre-registered before it was seen. Remaining
work: fold v17 and the turnover budget into the write-up, then Phase 3, then
Phase 4.

Awaiting Jaeyoung's sign-off to take effect.
