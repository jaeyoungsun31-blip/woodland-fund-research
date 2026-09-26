# Planning review — v8 accepted; two defects before adjudication

Date: 2026-09-06
Status: review (blocking adjudication, not blocking training prep)
Artifact: `reports/security-resolver/2026-09-06-v8-resolver/`

## Confirmed correct

Segment-level verdicts now discriminate within a spliced file:

```
RAL_old::segment1  1997-12-31..2001-12-12  last close 0.06% below offer; vol 7.1x median accept/medium
RAL_old::segment2  2010-02-22..2022-03-02  no overlap with membership                 reject/high
MOB_old            1997-12-31..1999-11-30  last close [redacted]; vol 1.9x median      accept/medium
MOB (live)         2022-08-25..2026-09-04  no overlap                                 reject/high
```

Both of the previous chat's errors are reversed on price evidence, not on names.
Catalog names are display-only, as instructed.

## Defect 1 — `unique_live_candidate` does not check interior gaps

The automatic basis tests date containment against a file's outer bounds but
never asks whether the file has a hole inside the membership window. Measured
across the 948 auto-resolved symbols: 38 have a live file with a gap over 200
days, and for **2 of them the gap falls inside a resolved membership window**:

```
CTXS  1999:CTXS, 2000:CTXS   gap 1998-12-18 -> 2003-09-11  (1,728 days)
JP    1999:JP,   2000:JP     gap 1981-12-24 -> 2015-07-15 (12,256 days)
```

Citrix Systems traded continuously through 1999–2003; the file is missing that
span. Jefferson-Pilot's file contributes a single 1981 bar to a 1999–2000
membership. Both resolutions are contaminated and were produced automatically.

Fix: extend the `unique_live_candidate` predicate to require no qualifying gap
**within** the membership window. Expected effect: 2 symbols move to review.
The other 36 gapped files are unaffected because their gaps fall outside any
resolved window.

## Defect 2 — the confidence column conflates identity with coverage

`BSC_old`, final bars:

```
2008-03-13  close 57.00  vol  70,720,800
2008-03-14  close 30.00  vol 186,986,896   (27x the 60-day median of 6.84M)
```

That is Bear Stearns on the day the Fed/JPMorgan emergency financing was
announced. No other security produces that signature. Identity is not in doubt.

What is missing is 2008-03-17 through the merger close on 2008-05-30 — the file
stops, the membership record runs to 2008-05-29. v8 marked this `unknown/low`
for "partial containment", which reports a **coverage** shortfall as an
**identity** doubt. The remedies differ: identity is settled by evidence,
coverage is settled by the A2 truncation convention.

The bias is not random. It lands hardest on names that were removed from the
index by a crisis event — precisely the population the constituent panel exists
to capture.

Fix: split the packet's verdict into `identity_verdict` and `coverage_verdict`,
each with its own confidence. `BSC` becomes identity `accept/high`, coverage
`truncated_pending_A2`.

## Observation — the partial-containment population fails on the start side

87 of 116 `unknown/low` rows cite partial containment. Sampling the ten with a
terminal-volume ratio at or above 5x shows most exceed the membership end and
fail on `dates_first` instead:

```
WEN_old  last 2008-09-29 (240x)  membership ends 2008-09-26   exceeds
AT_old1  last 2007-11-16 (14.9x) membership ends 2007-11-16   exact
EMC_old  last 2016-09-06  (9.1x) membership ends 2016-09-06   exact
BSC_old  last 2008-03-14 (27.3x) membership ends 2008-05-29   TRUNCATED
DOW_old  last 2017-08-31  (9.1x) membership ends 2026-06-30   TRUNCATED
```

So the dominant unresolved question is whether an earlier archived record or
segment covers the **front** of each membership window — a stitching question,
not an identity question. It should be measured before any hand adjudication.

## Live-file gap scan

8,868 of 49,232 live files carry a qualifying gap. Keeping this report-only was
correct: the population is dominated by thin and halted small caps outside the
constituent set, and only 38 intersect the auto-resolved symbols. Do not act on
it.

## Consequence

**A2 is now blocking adjudication, not only training.** A reviewer cannot
dispose of `BSC` or `DOW` without knowing how a membership window that outlasts
its price history is treated. Sign A2 before the packet is worked by hand.
