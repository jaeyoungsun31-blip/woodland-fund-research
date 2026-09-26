# Data acceptance standard — the stopping rule

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung, authorization given verbally in the
planning chat and recorded by planning (he could not sign the file directly).
Countersigned into the record by: Claude (planning). See
`2026-09-08-planning-record-package-signature.md` for the authorization scope.
Framing: HYBRID (materiality gates; coverage discloses) — selected by Jaeyoung
2026-09-08

## Why this exists

Every gate in this project has been defined negatively — "no unresolved
constituent", "stop if any journalled number moves", "do not fit on partial
data". Negative gates never close, because the standard is *no known defects*
and searching harder always finds more. 120 journal entries in seven days and
zero fits on the constituent data is the observable consequence. This entry
supplies the positive gate.

## The standard

**Materiality is the gate. Coverage is disclosure, not a threshold.**

There is no minimum percentage of symbols that must be verified clean. The
question is not *how much dirt is there* but *does the dirt change the answer*.
That is testable, and it is tested by the dual run.

### The gate

A result is admissible when the pre-registered study is run across all declared
arms and the arms **agree**. Agreement is defined as, on the study's own
primary metric:

1. the **sign** of the primary effect is the same in every arm, and
2. the arms' **confidence intervals overlap**, computed by this project's
   existing block-bootstrap + Ledoit-Wolf HAC machinery.

Both conditions. Promotion additionally requires the study's own
pre-registered gate to pass **in every arm**, not on average and not in the
best arm.

### The disclosure

Every result carries a block reporting, with denominators:

- symbols cleared / total, per `STATE.md` §13 method
- unclassified exits / total exits, and A2 coverage by case
- symbols independently cross-checked / total, with the coverage skew named
- the count and nature of known-unresolved defects at run time

Disclosure is mandatory and unlimited. There is no defect too embarrassing to
report and no defect that, once disclosed, blocks the run.

## The stopping rule — the operative clause

**When all declared arms have been run and the gate evaluated, the data
question for that study is CLOSED.**

Defects discovered afterward are recorded in a defect register and addressed in
the *next* study. They do not reopen a completed one. A completed study is
amended only if a defect is shown to be **material** — meaning it would flip
the gate — and that showing is itself a measurement, not an argument.

This clause is the entire point of this entry. Without it, any finding by any
agent can restart the process indefinitely, which is the state the project has
been in since 2026-09-01.

## What this standard does not license

It does not license fitting on data known to be wrong where the wrongness is
cheap to fix. Tier 1 items that are one commit of work are done before the run,
not disclosed around. It does not license skipping the pre-registration. It
does not license running one arm and reporting it.

## Confidence

The agreement band (sign + overlapping CIs) is planning's proposal, not
Jaeyoung's stated preference — he selected the hybrid framing and left the band
to planning. It is chosen because this project's own inference work measured
Sharpe CIs of roughly +/-0.4 on 21.8 years, so a tighter band would be
unmeetable and a looser one meaningless. **Change it before signature or not at
all**: once signed and run, altering it converts a pre-registration into a
search.
