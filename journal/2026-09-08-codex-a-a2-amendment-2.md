# A2 Amendment 2 panel bounds

Date: 2026-09-08  
Author: Codex A (panel lane)  
Status: engineering record; no fit, training, dual-run arm, cycle, data refresh,
or order submission was run.

## Implemented signed decision

The panel builder now applies signed A2 Amendment 2 using the existing
Case-2 adverse-panel mechanism. It emits:

- `panel-returns-a2-favourable.parquet`: a 0% terminal liquidation for each
  unclassified exit;
- `panel-returns-a2-adverse.parquet`: the same exits at -100%, retaining the
  existing Case 2 adverse rows unchanged; and
- `a2-unclassified-terminal-bounds.csv`: audit rows for the new bounds.

The signed coverage definition uses one final symbol-year for each panel column
whose last return precedes panel end, plus the final absent Case 2 and pending
Amendment 1 symbol-years. It does not retain the earlier finding's 180-day
diagnostic cutoff, because the signed amendment specifies every exit before
panel end.

## Coverage

```
exits_total: 452
treated: 8
by_case: { case_1: 0, case_2: 8, case_4: 0 }
unclassified: 441
quarantined: 3
```

The asserted reconciliation is `8 + 441 + 3 = 452`.

The 441 unclassified symbol-years enter both bounds. The three unsigned
Amendment 1 rows remain exactly quarantined: `2013:JEF`, `2020:ARNC`, and
`2020:RTN`; they enter neither bound. The existing Case 2 base exclusion and
eight adverse terminal rows are unchanged.

## Verification

Focused panel tests: 6 passed. Ruff passed. The builder was run only to rebuild
the panel artifacts from existing resolver inputs; it did not read or write the
market-data store.
