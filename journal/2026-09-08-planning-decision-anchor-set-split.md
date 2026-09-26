# Decision — split the anchor set; 43/53 was inflated

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("ok don't paper over it"), recorded by
planning.
Corrects: planning's own framing in
`2026-09-08-planning-decision-etf-anchor-tolerance.md` and STATE.md
Cause: Codex A's third refusal — the required anchor regression is unrunnable.

## What was found

`reproduce_all.py:543` refuses when the store hash differs from the anchors
record. The record holds `7b64be10...`; the configured store is the frozen
`4c6a36b8...`. The only bypass, `verify_snapshot=False`, is documented as
measurement-only. The regression gate planning made binding cannot be satisfied.

Investigating that surfaced the larger fact. All 23 anchors in
`config/etf-anchors-2026-09-07.json` carry:

> "Unavailable earlier input snapshot; superseded by explicitly pinned current
> data, not reproduced."

They are recomputations from the restated store, not reproductions. And the
overlap with the failures is total:

```
53 anchors
  23 replaced with values recomputed from the CHANGED store
  10 fail  — all ten inside those 23
  30 pass against original journalled values
```

The 23 cover exactly the ETF-window series: 60/40, SPY buy&hold, v1, v2, v3,
v5 (both), v6 (both), v14 (all sleeves), vol-target 60/40.

## Planning's error

Planning cited "43 of 53 pass" as evidence the drift was immaterial and
recommended the 1e-3 tolerance on that basis. 23 of those passes were derived
from the store they were validating. The magnitudes of the 10 failures are real
and unchanged; the framing was not. Planning also flagged this exact ambiguity
on 2026-09-07 as item 8b, marked it [Unknown], and did not check it.

## Decision

1. The regression gate is **"30 reproduced anchors pass within 1e-3."** That is
   a real check.
2. The 23 replaced anchors are carried as a **disclosed limitation** and are
   **never counted as passes.**
3. `verify_snapshot` is taught the signed ruling — accept snapshot
   `4c6a36b8...` under the declared 1e-3 tolerance — so the gate passes
   legitimately rather than by bypass. The bypass stays measurement-only.

## Permanent consequence, recorded so it is not rediscovered

The input snapshot behind the 23 no longer exists and cannot be obtained. Every
ETF-window result in Phases 1-2 is now a journal assertion rather than a
reproducible measurement. This is not a defect to fix; it is a limitation to
disclose in any writeup citing those numbers.

Two mitigations of fact, not of process: those results were uniformly negative
("nothing beat 60/40 after costs"), and the only statistically significant
finding — trend-v4 on Fama-French deep history, +0.152, p=0.014 — does not read
the ETF store and is unaffected.

## Forward fix

Every future snapshot freeze must **emit its anchor values into the snapshot
directory at freeze time**, so a frozen snapshot carries its own reproducible
anchor set and never depends on a store that has since moved. Without this,
the next freeze recreates this failure.
