# Amendment — liquidation convention for unpriceable holdings

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("yes", planning chat), recorded by
planning; he could not sign the file directly.
Amends: `2026-09-08-xsmom-v16-dual-run-preregistration.md`
Cause: `2026-09-08-codex-a-dual-run-results.md` — all four arms refused at the
first training fold.

## This is an amendment, not a correction

The cost-schedule change earlier today resolved a contradiction the document
already answered by its own declared hierarchy. **This one does not.** It adds
a methodology term that did not previously exist and that changes how results
are computed.

Its legitimacy rests on one fact and no other: **no arm has produced an OOS
result.** Codex A recorded that no returns, baselines, turnover, subperiod
metrics, bootstrap/HAC comparison, or promotion outcome was produced. Nothing
has been observed, so nothing can be steered. The identical amendment after any
number existed would be a search wearing a pre-registration's clothes, and the
correct action then would be to void the run.

## The problem

`woodland/backtest.py` raises on a held or target asset with no price. It was
written for a fixed 22-ETF universe, priceable on every date. The constituent
panel is 47% NaN by construction: a name has no price before it joins the index
and after it leaves.

```
panel symbols                      942
  with >=1 interior hole            34   (3.6%; 47,450 cells; 1.4% of all NaN)
  contiguous, terminal exit only   908
panel density                     0.4673
```

Two distinct causes, requiring different treatment:

- **Terminal exit** — the series ends. `FWLT` ends 2000-01-28; the engine still
  held it on 2000-02-01. A2 assigns a terminal return but nothing removes the
  position afterward.
- **Interior hole** — the name leaves the index and later returns. `OKE` is a
  member 1999-2001, absent, and a member again from 2010. `OI` likewise. The
  NaN is correct: point-in-time membership working as designed.

## Decision

A position is liquidated on the loss of a price. Freed weight becomes cash,
which the engine already models as `1 - sum(h)`.

1. **Terminal exits take the A2 bound** — 0% in favourable arms, -100% in
   adverse arms. This is the treatment A2 already defines; the engine now acts
   on it.
2. **Interior holes liquidate at the last available close, 0% terminal, under
   BOTH bounds.** Re-entry is a fresh position with no memory of the prior one.

## Why interior holes must not take the adverse bound

A2 governs **delisting**. An index exit is not a delisting. `OKE` never stopped
trading and is a member again today; marking it -100% would fabricate a loss
for a company that continued to exist. With 34 affected names, applying the
adverse bound to index exits would materially poison arm D and would do so in
the direction that makes the panel look worse than reality — an error of the
same class as the upward bias A2 exists to prevent, pointed the other way.

## Binding regression requirement

`woodland/backtest.py` is shared. Its per-symbol cost change was verified
bit-identical to the pre-edit engine on uniform cost vectors, and 43 of 53 ETF
anchors currently reproduce within the signed 1e-3 tolerance. **This amendment
must not change any ETF result.** ETF series have no unpriceable holdings, so
the new path must not execute for them. Reproduction must be re-run after the
change and must still yield 43 passing anchors within 1e-3.

## Fixed on signature

This convention is fixed. It is not revisited after any arm produces a number.
