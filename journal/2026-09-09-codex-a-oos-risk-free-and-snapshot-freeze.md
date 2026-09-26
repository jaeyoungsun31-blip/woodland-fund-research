# Codex A — OOS risk-free refusal and baseline snapshot freeze — 2026-09-09

Diagnosis recorded before clearing the retained staged Arm A directory.

The refusal originated at `woodland/harness/costaware_panel.py:293` (before
this repair): baseline prices were built from the mutable `ROOT / "data"`
store and their calendar was used to reindex the risk-free series.  That
baseline calendar included dates not present in the declared panel calendar,
so a risk-free series that was complete on the panel calendar acquired
non-finite values during baseline construction.  The panel and signed window
remain unchanged: 1999-01-06 through 2026-06-30.  No risk-free values are
filled or fabricated.

The offending baseline-only calendar dates were:

- 2003-12-26, 2003-12-29 through 2004-01-07;
- 2014-12-26, 2014-12-29 through 2015-01-07;
- 2019-12-24, 2019-12-26 through 2020-01-17, and 2020-01-21 through
  2020-01-28;
- 2020-12-22 through 2020-12-24, and 2020-12-28 through 2021-01-07;
- 2021-12-21 through 2021-12-23, and 2021-12-27 through 2022-01-10;
- 2022-12-23, and 2022-12-27 through 2023-01-04;
- 2023-12-19 through 2023-12-22, and 2023-12-26 through 2024-02-01;
- 2024-12-24, and 2024-12-26 through 2025-03-24;
- 2025-12-23 through 2025-12-24, and 2025-12-26 through 2026-01-14.

The baseline reader now resolves `data.store` from `config/universe.yaml`,
which is the declared frozen research snapshot, and reindexes its baseline
prices to the already-declared panel index before passing the already-aligned
risk-free series.  This fixes a separate snapshot-freeze defect: baselines
previously read the mutable live store.  Existing trial-ledger rows are not
read, modified, deleted, or reused.
