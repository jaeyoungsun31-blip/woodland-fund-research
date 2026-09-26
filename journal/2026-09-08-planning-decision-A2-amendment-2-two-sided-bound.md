# A2 Amendment 2 — two-sided bound for unclassified exits

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung, authorization given verbally in the
planning chat and recorded by planning (he could not sign the file directly).
Countersigned into the record by: Claude (planning). See
`2026-09-08-planning-record-package-signature.md` for the authorization scope.
Extends: `2026-09-06-planning-decision-A2-delisting-and-membership-end-convention.md`
Does not touch: `2026-09-07-planning-decision-A2-amendment-1-successor-cases.md`
(still PROPOSED/unsigned; its quarantine stands)
Cause: `2026-09-08-planning-finding-a2-applied-but-covers-2-percent-of-exits.md`

## Problem

The signed base treats 8 of 430 exiting symbols (1.9%). Case 1 and Case 4
require a **cited corporate action**; no citation source exists in this
pipeline and none is obtainable on the held vendor plan. Case 1 and Case 4 can
therefore never fire. Case 3, the residual, is refuse-not-exit, which under
hard constraint 4 refuses most of the panel. The base convention is
unsatisfiable on the data held.

## Decision

Every symbol-year that **ends before the panel end and is not classified Case
1, 2 or 4 by the signed base** is an *unclassified exit*. Unclassified exits
are not refused and are not left untreated. They are carried in **two bounding
panels**:

- **favourable bound** — the position liquidates at the last available close;
  terminal return **0%**.
- **adverse bound** — the position is a total loss; terminal return **-100%**
  at the terminal date.

Neither bound is a belief about what happened. The pair is a declared interval
containing the truth for every unclassified exit, which is the same move the
signed base already accepts for Case 2.

## Scope and interaction

1. Case 1, 2 and 4 keep their signed treatments unchanged. Case 2 already
   carries base + adverse; that pairing is unaffected.
2. The 3 symbol-years quarantined pending Amendment 1 (`2013:JEF`,
   `2020:ARNC`, `2020:RTN`) **stay quarantined** — excluded from both bounds,
   reported separately. Amendment 2 does not resolve successor cases.
3. Case 3 is no longer the operative residual for exits. It remains the
   residual for anything that is not an exit.
4. The mechanism exists: `panel-returns-a2-adverse.parquet`, built for Case 2,
   generalises. Do not build a parallel implementation.

## Mandatory reporting — coverage denominators

Three status flags in this project have overstated the work behind them by
reporting a numerator with no denominator. From this entry forward, **every A2
status must report coverage as treated/total**:

```
a2_treatment_applied: true
a2_coverage: { exits_total: N, treated: M, by_case: {...}, quarantined: Q }
```

A bare `true` is not an acceptable report.

## What this does not do

It does not clean any data, identify any security, or establish any corporate
action. It bounds an unobtainable quantity so that studies can proceed with the
uncertainty declared rather than hidden.
