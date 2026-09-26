# Codex A — xsmom-v16 dual-run harness

Date: 2026-09-08
Status: engineering record; no model fit, training, arm execution, data refresh,
or paper submission was performed.

Implements the validate-only wiring required by the signed
`2026-09-08-xsmom-v16-dual-run-preregistration.md` and the signed data
acceptance standard.

## Frozen subset

The runner loads, and never derives, planning's immutable
`reports/cleared-subset-2026-09-07/cleared-subset.csv`. It asserts exactly 220
`cleared == true` symbols and asserts every one appears in the favourable
panel. The frozen list is read at validation/run time.

## Arms and disclosure

The four pre-registered panels assemble as follows, all over 6,736 dates:

| arm | population | A2 bound | symbols |
| --- | --- | --- | ---: |
| A | cleared subset | favourable | 220 |
| B | cleared subset | adverse | 220 |
| C | full panel | favourable | 942 |
| D | full panel | adverse | 950 |

The harness populates the mandatory disclosure block from the frozen panel
artifacts. It preserves the 452-exit A2 census: 8 treated (all Case 2), 441
unclassified, and 3 quarantined pending unsigned Amendment 1 (`2013:JEF`,
`2020:ARNC`, `2020:RTN`). It explicitly reports that the adverse universe has
eight extra Case 2 absent-name columns.

## Gates and refusal

Gate evaluation requires all four arms, a common primary-effect sign, overlap
of the confidence intervals, and every arm passing inherited C1/C2/C3 before
promotion can be eligible. The inference adapter uses the established
stationary block-bootstrap and Ledoit-Wolf HAC functions; it supplies no fit or
backtest path.

Execution authorization is mechanically refused unless a recorded anchor
ruling is found in `config/` or `journal/`: either an accept-under-declared-
tolerance ruling with its tolerance recorded, or a re-anchor ruling. No such
ruling was present during validation, so the harness reported refusal and
stopped at the fit boundary.

## Verification

Focused tests cover frozen-list cardinality, four-arm construction, agreement
and inherited-gate failures, and absent-anchor refusal. `--validate` was run;
it only assembled the panels and disclosure block.
