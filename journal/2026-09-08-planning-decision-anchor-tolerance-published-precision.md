# Correction — published precision is the tolerance for the 30-anchor gate

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("ok do that"), recorded by planning.
Corrects: the flat 1e-3 in
`2026-09-08-planning-decision-etf-anchor-tolerance.md`, for the 30-anchor gate
only.
Cause: Codex A's fourth refusal — 5 of 30 reproduced anchors failed the flat
1e-3. Correct refusal; the defect was in planning's tolerance, not the code.

## What failed

```
anchor                      journalled     rebuilt    delta   half-ulp
xsmom top-3 turnover            5.23      5.232499   0.0025    0.0050
equal-weight-12 turnover        0.27      0.266288   0.0037    0.0050
K mean product                 232.2    232.217327   0.0173    0.0500
K minimum product              219.6    219.640460   0.0405    0.0500
K maximum product              242.7    242.737882   0.0379    0.0500
```

All five pass at published precision. All five fail a flat 1e-3. None is a
Sharpe. The declared `decimals` are 2, 2, 1, 1, 1.

## Planning's error

The signed ruling declared "1e-3 on Sharpe anchors" and said nothing about
non-Sharpe anchors, so the number was applied to all of them. A single
**absolute** tolerance across metrics spanning 0.27 to 242.7 is incoherent, and
for coarsely-recorded anchors it demands more precision than the journal ever
recorded. A value written as `0.27` carries +/-0.005 of unknown; no tolerance
can recover precision that was never stored.

## The five did not move

The 2026-09-07 drift measurement checked all 53 anchors at published precision:
43 passed, 10 failed, and all 10 failures were Sharpes in the replaced set.
These five were not among them. They passed at published precision then and
pass at published precision now. **Codex A's engine change did not move them.**

## Decision

The 30-anchor gate uses **published precision (half-last-digit at each anchor's
declared decimals) as its sole tolerance.** The 1e-3 floor is dropped there.

This is stricter than the `max(half-ulp, 1e-3)` planning first proposed, and it
restores the convention that predates planning's involvement. The floor is not
needed inside the gate: every restatement-affected anchor is in the 23 replaced
set, which the gate already excludes and discloses.

The 1e-3 ruling remains in force **only** for the 23 replaced anchors.

## Required verification

The gate must report, for all 30, the per-anchor journalled value, rebuilt
value, delta, and tolerance — not a pass count. "30 passed" from a summary is
what allowed an inflated 43/53 to enter this record once already.

## Scope note, recorded because it keeps being conflated

This gate concerns **ETF baseline reproducibility**. It is not a data-quality
control on the constituent panel and does not clean anything. It exists because
`woodland/backtest.py` is shared: the panel work modifies the engine, and the
anchors are how a leak into the ETF path would be detected. Passing it proves
the new membership-mask and short-gap paths do not execute for ETF inputs.
