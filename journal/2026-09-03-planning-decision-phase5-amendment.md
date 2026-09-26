# 2026-09-03 — planning decision: amend DESIGN.md §11 to open Phase 5's ML signal layer ahead of Phases 3–4

Append-only. Recorded BEFORE `xsmom-v16-costaware` is pre-registered or run,
per DESIGN.md §8's requirement that gate- and scope-affecting changes are
declared in advance of the cycle in which they apply.

## What is being amended

DESIGN.md §11 orders the roadmap Phase 3 (retrain loop + promotion gate) →
Phase 4 (Alpaca paper) → Phase 5 (second strategy family; ML signal layer;
write-up). §11 also carries the explicit scope-discipline warning that
`[Likely]` the second-largest schedule risk is "Phase 5 starting early."

This decision opens the **ML signal layer of Phase 5 only**, ahead of Phases 3
and 4, which remain unstarted. Nothing else in Phase 5 is opened. The
promotion gate of `2026-09-01-gate-preregistration.md` is unchanged and still
binding: no ML result can promote anything, because Phase 3 does not exist yet.

## Why, stated so it can be judged later

Fifteen studies have all shared one structure: a hand-specified rule with a
handful of free parameters, tested. The search over signal space has therefore
been conducted by hand, one guess at a time. v13 established that the
cross-section carries real predictive structure (Fama-MacBeth t=3.73,
p=0.0002) that the hand-specified rules could not harvest at retail cost.
v15 then showed that the cost obstruction is at least partly a property of
*refresh frequency*, not of the signal — every modeled crossover moved above
50 bps when the cohort was held longer.

The open question those two results jointly raise is whether a *fitted*
signal, trained under an objective that already prices its own turnover, finds
a cheaper-to-hold version of the same structure than hand-specified rules can.
That question cannot be answered inside Phases 3–4, and it is the last
substantive research question the project has. Deferring it until after a
paper-trading loop exists would mean building the loop around a signal already
known not to clear cost.

## Conditions attached — these are binding

1. **No promotion.** v16 and any successor may produce evidence only. The
   §8 gate is untouched and cannot be exercised absent Phase 3.
2. **Full ledger.** Every hyperparameter cell counts as an evaluated
   configuration. The grid is declared before the first fit and is not widened
   after seeing results. A widened grid requires a new dated amendment.
3. **A declared no-fit control.** Every ML study must carry, as a
   pre-registered comparison, the corresponding un-fitted rule. A learned model
   that does not beat the hand-specified rule it replaces is a negative result,
   not an improvement in method.
4. **The no-lookahead perturbation test is a precondition of execution**, as
   for every prior study. Feature construction is where leakage enters a fitted
   model, and features are built from a panel, so the test must perturb the
   panel, not only the returns.
5. **Era stability is a primary criterion, not a footnote.** Every prior study
   that survived the full window failed post-1980. That pattern is now known in
   advance, so a study that does not test against it is not testing the
   hypothesis that matters.

## Explicitly NOT opened

Reinforcement learning and crash-pattern conditioning remain rejected per
`2026-09-01-planning-decisions-crosscheck-dsr.md`. Online/continual learning is
not opened. Phase 4 live paper trading is not opened. This amendment opens a
supervised, offline, walk-forward-fitted signal layer and nothing else.

Signed off by Jaeyoung in planning, 2026-09-03.
