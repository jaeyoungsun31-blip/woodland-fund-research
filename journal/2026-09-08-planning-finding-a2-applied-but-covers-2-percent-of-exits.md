# Planning finding — A2 is "applied" and covers 1.9% of the exits

Date: 2026-09-08
Status: finding (blocking); planning's gap, not a coding error
Reviews: `journal/2026-09-07-codex-a2-panel-wiring.md`

## Codex A executed correctly

It implemented the signed base only, refused to implement the unsigned
Amendment 1, quarantined the three successor-dependent rows
(`2013:JEF`, `2020:ARNC`, `2020:RTN`), wrote the Case 2 adverse bound to a
separate artifact, and ran no model. Nothing below is a criticism of that work.

## The measurement

```
panel symbols                                              942
symbols whose series ends >180d before the panel end       430   (45.6%)

A2 symbol-years by case:  case_1 0 | case_2 58 | case_4 0 | pending 3
Case 2 covers                                                8 symbols
case_3 is not reported at all
panel dimensions after wiring: 942 x 6736  — UNCHANGED
```

**A2 assigns a terminal treatment to 8 of 430 exits — 1.9%.** The other 422
still simply stop. `a2_treatment_applied: true` is true as a flag and false as
a description of the panel. The upward bias A2 exists to remove is still
present for 98% of the exits.

## Why Case 1 is zero

The signed Case 1 requires **a cited corporate action**, all-cash
consideration, and a terminal close within 5% of the cited cash price. No
corporate-action citation source exists anywhere in this pipeline. EODHD's
`/api/eod` carries no corporate actions and Fundamentals is not in the held
plan (standing finding 7).

So Case 1 cannot fire, ever, on the current inputs — not because cash mergers
did not occur, but because nothing cites them. `MOB_old` (Exxon/Mobil,
1999-11-30) and `RAL_old` segment 1 (Nestlé, $33.50 offer, terminal close
0.06% below it) are textbook Case 1 shapes with terminal bars this project has already
verified by opening the files. Both classify as nothing.

Case 4 is zero for the same reason: successor identification has no source.
Case 2 fires only because bankruptcies are self-identifying from an absent
price file.

## The consequence nobody has stated

Case 3 is the declared residual — "what remains when no cited action is
satisfied" — and its rule is **refuse-not-exit**. Applied honestly, the ~422
unclassified exits are refusals. Under hard constraint 4 (an unresolved
constituent is a refusal, not an omission) that refuses most of the panel.

**A2 as signed is unsatisfiable on the data actually held.** Either the panel
collapses, or Case 3 is silently not applied — which is what happened here,
since `case_3` appears in no output and the panel is unchanged at 942 symbols.

## Pattern worth naming

Third instance in two days of a status flag that overstates the work behind it:

1. `a2_treatment_applied: true` covering 1.9% of exits (this entry).
2. "The snapshot directory and every copied parquet have write permission
   removed" — the directory was writable
   (`journal/2026-09-07-codex-etf-snapshot-freeze.md`).
3. Planning's own `STATE.md` v1 asserting "A2 — SIGNED" when Amendment 1 was
   unsigned.

None was dishonest; each was a true-sounding summary of partial work. The
project's §3 failure mode has a second form: not a wrong claim, but a correct
claim at the wrong scope. Status flags need coverage denominators.

## The way out requires no procurement

Codex A has already built the mechanism — `panel-returns-a2-adverse.parquet`,
a −100% terminal on Case 2 names. Extend that same two-sided treatment to
every unclassified exit:

- **favourable bound** — unclassified exits liquidate at the last close, 0%
- **adverse bound** — unclassified exits take −100% at the terminal date

Run the study against both and report the band. Promotion requires the gate to
pass under both. This needs no citation source, no vendor purchase, and no
further classification: it converts an unobtainable fact into a declared
sensitivity, which is the same move already accepted for Case 2.

Recommend this as **A2 Amendment 2**, drafted with the acceptance standard, so
one signature clears both.
