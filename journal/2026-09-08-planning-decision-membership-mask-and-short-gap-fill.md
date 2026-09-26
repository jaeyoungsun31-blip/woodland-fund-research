# Amendment — membership mask, and the short-gap fill

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("ok do that", planning chat), recorded by
planning.
Amends: `2026-09-08-planning-decision-unpriceable-holding-convention.md`
Cause: Codex A refused to implement that convention because it invalidated an
existing regression test. **The refusal was correct and it caught a defect in
the signed convention.**

## The defect planning signed

The prior amendment told the engine to liquidate on a missing price. Measured,
the interior gaps in the panel are bimodal with nothing between:

```
gap length (trading bars)     runs
      1-5                       38     data holes; the name is still a member
     6-250                        0
      >250                       27     genuine index exit and re-entry
```

Liquidating on any NaN would have converted a **one-day missing bar** into a
liquidation and a next-day re-entry, with round-trip costs, 38 times, invisibly.
That is the silent-corruption class this project exists to catch, and planning
signed it. The `missing price for held asset` guard in `woodland/backtest.py`
was protecting exactly this, and the test codifying it was correct to fail.

## Amendment 1 — the trigger is membership, never NaN

The engine is **given** the investable universe; it does not infer it.

- A symbol **in** the declared membership universe on date `t` with no price is
  still an **error and must still raise.** The guard survives unchanged and its
  regression test remains valid for this case.
- A symbol **outside** the universe on date `t` is liquidated per the prior
  amendment: terminal exits take the A2 bound (0% favourable, -100% adverse);
  index exits with later re-entry liquidate at the last close at 0% under both
  bounds, and re-entry is a fresh position.

This requires a **membership mask artifact** — a per-(date, symbol) boolean —
which does not currently exist. The resolver holds the membership records that
built the panel; the mask is emitted from them as its own artifact and passed to
the engine as an input.

## Amendment 2 — short-gap fill

An interior gap of **5 trading bars or fewer, inside the membership window**, is
filled as a **0% return** (the position is held at unchanged value). Filling is
performed in the panel build, not the engine, so the artifact is explicit and
auditable. Every filled cell is written to an audit CSV and counted in the
disclosure block.

Gaps longer than 5 bars are never filled; they are index exits and are handled
by the mask.

Scope, measured:

```
symbols with short gaps       7    CSR BT FTR LUV NXPI SLB SNT
filled cells                 45    of 2,964,872 observations (0.0015%)
in the cleared subset         0    arms A and B are unaffected
```

## Why fill rather than drop

Dropping the 7 symbols would remove names on the basis of a data defect, which
is selective exclusion of exactly the kind this project has spent a week
avoiding. A declared, disclosed, audited fill of 45 cells is the smaller
distortion and it is visible in the record. This project has not filled
anything before; that this is the first is itself a reason it is written down.

## Deferred, at Jaeyoung's request

The 45 cells are a **known open data item**, to be investigated on their merits
later. The fill is a convention that permits the study to run; it is not a
finding that the bars are unrecoverable.
