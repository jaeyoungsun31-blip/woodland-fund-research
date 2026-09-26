# Phase 3 finding — current ETF store drifts from registered anchors

Date: 2026-09-07  
Scope: Step 1 measurement only; no snapshot freeze, panel run, or model fit

The registered ETF snapshot is `as_of: 2026-09-04` with SHA256
`7b64be101f62166ed9261a8d51a8894f61310238dfa8d75c2c8e4f3d45c233e6`.
The observed current store has the same as-of date and dimensions but SHA256
`4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901`.
The observed hash was explicitly **not** accepted or registered.

Measurement used the registered replacement anchor values from
`config/etf-anchors-2026-09-07.json`, checked at each anchor's published
precision using a half-last-digit tolerance. The measurement-only path retained
the normal hash guard for default reproduction and bypassed it only to measure
the changed current store. It checked all 53 registered anchors: 43 passed, 10
failed, and 0 groups were skipped. The ETF snapshot hash and complete file
inventory were stable before, during, and after the run.

The ten failures are:

| Series | Metric | Expected | Actual | Signed delta | Absolute delta | Decimals | Tolerance |
|---|---|---:|---:|---:|---:|---:|---:|
| v6 multi-asset | sharpe | 0.787767842778 | 0.788352952877 | 0.000585110099 | 0.000585110099 | 3 | 0.0005 |
| v14 raw v6 | sharpe | 0.787767842778 | 0.788352952877 | 0.000585110099 | 0.000585110099 | 6 | 0.0000005 |
| v14 baseline partial | sharpe | 0.811950268130 | 0.812515261753 | 0.000564993623 | 0.000564993623 | 6 | 0.0000005 |
| v14 S1 dispersion | sharpe | 0.835597681879 | 0.836181628475 | 0.000583946596 | 0.000583946596 | 6 | 0.0000005 |
| v14 S2 inverse-vol | sharpe | 0.814324844379 | 0.814797548605 | 0.000472704226 | 0.000472704226 | 6 | 0.0000005 |
| v14 S2 min-variance | sharpe | 0.891258209197 | 0.891179830112 | -0.000078379085 | 0.000078379085 | 6 | 0.0000005 |
| v14 S3 symmetric | sharpe | 0.812705546606 | 0.813078056439 | 0.000372509833 | 0.000372509833 | 6 | 0.0000005 |
| v14 S3 asymmetric | sharpe | 0.808055555025 | 0.808425411589 | 0.000369856563 | 0.000369856563 | 6 | 0.0000005 |
| v14 S4 band | sharpe | 0.779748464390 | 0.780335029572 | 0.000586565182 | 0.000586565182 | 6 | 0.0000005 |
| v14 S4 partial+band | sharpe | 0.817918963538 | 0.818483822443 | 0.000564858904 | 0.000564858904 | 6 | 0.0000005 |

The remaining 43 anchors pass; the full per-anchor CSV is included beside the
machine-readable JSON report:

- `reports/anchor-measurement-2026-09-07/current-store.json`
- `reports/anchor-measurement-2026-09-07/current-store.csv`

This is retrospective reproducibility drift, not evidence of lookahead or
leakage. The likely source provenance has already been identified in
`journal/2026-09-07-planning-finding-etf-snapshot-writer-identified.md`; this
measurement makes no independent causal inference. Work stopped before any
snapshot freeze or model fitting. No data were written, no synthetic bars were
created, and no v16 gate result exists.

Validation before and after the measurement: 165 focused tests passed and Ruff
reported clean. No files were staged or committed by this task.
