# Decision — split the pre-registration: terms versus mechanics

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("just do the second part (b)"), recorded
by planning.
Affects: `2026-09-08-xsmom-v16-dual-run-preregistration.md` and every future
pre-registration.

## Why

Seven blockers stalled the dual run. Classified by cause:

```
volume-screen artifact missing        planning: unpersisted artifact + lane rule
cost schedule 0/5/10 vs C2's 25bps    PRE-REGISTRATION
engine cannot consume a 47%-NaN panel architecture; planning's --validate hid it
liquidate-on-NaN round-trips 1d gaps  planning: a badly written amendment
anchor regression unrunnable          planning: a gate invented in a prompt
flat 1e-3 wrong for non-Sharpe        planning: a badly scoped ruling
30s boundary vs "one invocation"      PRE-REGISTRATION
```

Two of seven. The other five were planning's specification errors in documents
that are not the pre-registration. Loosening the pre-registration would have
prevented two stalls and removed the protection that caught them.

But the two share a signature: **planning wrote implementation mechanics into a
document whose job is to fix scientific terms.** "0/5/10 bps" and "one
invocation" are mechanics. The scientific terms — arms, comparisons, gate,
frozen inputs, window, quarantine — have never stalled anything and have never
been amended.

## Decision

Pre-registrations are split into two documents with different change rules.

**1. Pre-registration — IMMUTABLE.** Lives in `journal/`, append-only.
Contains only: the arms and what each varies; the comparisons and inherited
criteria; the promotion gate and agreement definition; the frozen inputs; the
study window; quarantines and exclusions; the disclosure requirements; the
outcome interpretations. **Requires Jaeyoung's signature.** Changing it after
any arm has produced a result voids the run.

**2. Execution protocol — REVISABLE.** Lives at `EXECUTION-PROTOCOL.md` in the
repo root, deliberately **outside** the append-only journal because a document
meant to be revised cannot live in an immutable record. Contains: cost-level
enumeration, invocation and checkpoint boundaries, file layout, run identifiers,
reproduction tolerances, timeouts, artifact paths. **Planning revises it without
signature.** Every revision is logged in its own changelog.

## The test for which document a clause belongs in

> Would changing this clause change what the study concludes, or only how the
> machine gets there?

Conclusion → pre-registration. Machinery → protocol. A clause that enumerates
cost *levels the criteria require* is machinery; a clause that says *which
criteria apply* is terms.

## Immediate application

The "all four arms in one invocation, or none" clause is mechanics by this
test, so it moves to the protocol and is replaced there by the sealed-arms rule
(`2026-09-08-planning-amendment-execution-mechanics-sealed-arms.md`): execution
may span invocations, **disclosure may not**. The anti-selectivity guarantee it
existed to provide is preserved and made explicit rather than implicit.

Planning sets that under the authority granted here. Stating plainly: planning
asked for a signature on the sealed-arms rule an hour before this split was
authorized, and is now setting it without one. That is legitimate only because
the split's own test classifies it as mechanics, and because it strengthens
rather than weakens the guarantee. It is recorded here so the sequence is not
invisible later.

## What this does not change

Nothing about what the dual run tests. Same four arms, same frozen subset, same
window, same gate, same quarantine, same disclosure. Planning stops bringing
process mechanics for signature and brings only things that change what is
being tested.
