> **Public export:** `universe.csv` (per-symbol, vendor-derived) are excluded from
> this copy. The counts quoted below are unchanged.

# Defect-excluded universe — frozen 2026-09-09

Authority: `journal/2026-09-09-planning-preregistration-universe-control.md`.

`universe.csv` records every favourable-panel symbol and marks the 27 symbols
excluded for an observed absolute daily return above 1.0. It was formed from
the 942 columns of
`reports/security-resolver/2026-09-07-constituent-panel/panel-returns-a2-favourable.parquet`
minus the 27 symbols enumerated in `journal/defect-register.md`.

Runner verification SHA-256:

```
25d65a86c5f26fa8d68e331b39d5f46e7bc1af270765ef0eba3531194b36dbcd
```

The runner must refuse on any mismatch; this file is frozen and must not be
re-derived during execution.
