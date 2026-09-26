# Per-symbol costs and the v16 reproduction stop

Date: 2026-09-07
Artifacts: reports/xsmom-v16-panel/
Status: Task 0 corrected; cost capability delivered; historical reproduction failed.

**Neither arm was run. C1, C2 and C3 are not evaluated.**
`reproduce_all.py --strict` checked 53 historical anchors: 30 pass and 23 fail,
all failures in the ETF group. The user explicitly required stopping if any
journalled number moves, so no v16 pre-registration or model implementation/fit
was started and no new study trial was written. This is a blocked execution
record, not a negative strategy result or a two-arm comparison.

## Completed work

The Tiingo summary now reports 100 attempted, matching its CSV and coverage
counts, instead of 947. The generator distinguishes planned names from actual
attempts, and describes the selection as longest membership-history first,
with alphabetical tie-breaks. The 68/94 failure fraction describes that selected
sample, not the store. No cross-check or ingest was rerun.

`woodland.backtest.run` now accepts a finite, nonnegative scalar or a complete
ticker-labelled mapping/Series of one-way costs. Costs align to price columns;
missing, extra and duplicate labels refuse. Charges use the per-symbol absolute
weight delta after drift. Scalar costs broadcast; uniform vectors retain the
old arithmetic reduction order so the flat-cost numbers remain bit-identical.
The result retains a copy of labelled cost assumptions. Per-symbol costs were
not assigned to the panel; unsigned cost inputs were not invented.

A saved pre-edit engine was compared with the new engine on ten scenarios:
0/5/10/25/50 bps, each with and without cash interest, monthly rebalancing,
12 assets and 600 dates. Returns, equity, turnover and holdings all match bit for
bit. These are engineering fixtures, not investment results or synthetic market
bars in the store. This does not certify journal reproduction: the required
real-data reconstruction fails. The cause of the ETF anchor differences is not
established by this task; the known bar-count defect is recorded separately and
was not changed or suppressed.

## Which journalled numbers disagree

All 23 are in `reproduction-failures.csv`, with journal filename, series, metric,
recorded value and rebuilt value. `reproduce-all.txt` retains the full output.
Examples: v1 selection Sharpe 0.612 vs 0.613008; v2 ensemble Sharpe 0.700 vs
0.701502; v14 raw-v6 Sharpe 0.780673 vs 0.787768. These are failed replication
checks, not new published strategy performance.

The study remains blocked until this prerequisite is resolved or the user
explicitly amends it. No historical window was clipped, no tolerance relaxed,
and no old journal entry was edited to obtain a pass.

## Validation

Before: 554 passed, one skipped, one known ETF bar-count failure.
After: 569 passed, one skipped, the same failure (5,502 bars vs 5,499; 22 folds).
Focused engine tests: 31 passed. Ruff and mypy pass for changed code.
All 50,889 parquet paths, sizes and modification times are unchanged.
No price changes, synthetic bars, new panel backtest, post-result tuning,
staging or commits by this task. See status.json and saved test logs.

## Required panel reporting block

213 constituents refused / 1,574 symbol-years. Four excluded defects: CTX, DF,
IGT, COG. Five substitutions: SYMC→GEN, NLOK→GEN, WIN→WINMQ, KRFT→KHC,
MMC→MRSH. FCPT has no usable bars. A2's convention is signed, but its treatment
remains a proposal for this panel and is not applied: no terminal return is
imputed for any delisting and no Case 2 adverse bound is computed.
