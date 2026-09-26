# A2 panel wiring — signed base only

Date: 2026-09-07  
Author: Codex (panel lane)  
Status: engineering record; no study, fit, training, or promotion was run.

## Change

`scripts/build_constituent_panel.py` now consumes the resolver's signed-base
`census-symbol-years.csv` and cited `a2-classification.csv` inputs.  The panel
summary declares `a2_treatment_applied: true` and reports the signed Case 1,
Case 2, and Case 4 symbol-year counts.

The base panel continues to exclude Case 2 names with no price file, as the
signed convention requires.  Its mandatory adverse bound is written separately
as `panel-returns-a2-adverse.parquet`: one -100% terminal return on the final
available panel session of each absent name's final membership year.  The base
price panel is unchanged by that bound.

## Measured construction counts

- Case 1: 0 symbol-years.
- Case 2: 58 symbol-years, all price-file absent.
- Case 4: 0 symbol-years.
- Case 2 adverse-bound terminal rows: 8 (one per absent symbol's final
  membership year).
- `pending_A2_amendment_1`: 3 symbol-years — `2013:JEF`, `2020:ARNC`, and
  `2020:RTN`.

The three successor-dependent rows are quarantined.  No successor history was
stitched, no exit was inferred, and no term from the unsigned 2026-09-07
Amendment 1 was implemented.

## Verification

Focused A2 panel tests passed (4 tests) and lint passed.  The builder was run
against the v10 resolver artifacts only; it did not refresh data and did not
run a model, fit, cycle, or order submission.
