# 2026-09-22 — defect audit: red full suite since snapshot freeze

Authorized by Jaeyoung as defect repair. This entry records test and data-placement facts; it does not amend a study, gate, result, or prior journal entry. No study was run, no result recomputed, and no trials ledger row was changed.

## Current baseline before repair

`.venv/bin/python -m pytest -q` ended `4 failed, 610 passed, 1 skipped in 96.19s (0:01:36)`. The four complete failure messages were:

1. `tests/test_dual_panel_run_controls.py::test_report_refuses_missing_or_mismatched_completed_arms`: `RuntimeError: refused: sealed arm directories lack a combined report artifact` at `woodland/harness/dual_panel.py:346`. The test fixture created four arm directories and summaries but no combined `reports/xsmom-v16-dual-run/summary.json`; `completed_report` requires it.
2. `tests/test_snapshot_and_returns.py::test_exclusion_cannot_erase_loss_and_only_sells_excluded_asset`: `assert np.float64(0.06875) == 0.1 ± 1.0e-07` at line 41; `Obtained: 0.06875`, `Expected: 0.1 ± 1.0e-07`. The same test asserts the surviving asset has weight `0.55 / 0.8 = 0.6875`. Its next 10% return contributes `0.06875` to portfolio return. Producing `0.1` would change return accounting, and changing the assertion would change an expected value. Jaeyoung instructed us to stop rather than make either change.
3. `tests/test_study.py::test_real_universes_realise_their_journalled_shape[etf]`: `FileNotFoundError: <repo>/data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/fama_french_factors_daily.parquet not found — run scripts/ingest_fama_french.py to build the risk-free series` at `woodland/cash.py:39`.
4. `tests/test_study.py::test_etf_context_carries_a_risk_free_series_and_deep_does_not`: the same `FileNotFoundError` and path at `woodland/cash.py:39`.

## Frozen risk-free artifact repair

`shasum -a 256 data/fama_french_factors_daily.parquet` recomputed `ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7`, matching the operator-supplied hash. The provenance JSON identifies the Ken French daily factors source and `fetched_at: 2026-09-01T23:34:41+00:00`. The parquet and provenance JSON were copied into the frozen ETF snapshot without changing its ETF price files. The copied parquet's hash was recomputed and matched again. `config/universe.yaml` now pins `risk_free_sha256`; `cash.load_risk_free_daily` checks the file's SHA-256 when called on the configured research store and refuses a mismatch. A test tampers with a synthetic configured-store factors file and confirms refusal. `tests/test_cash.py`: 10 passed; Ruff and mypy on the changed source passed.

The full suite after this placement and guard ended `2 failed, 613 passed, 1 skipped in 101.62s (0:01:41)`. The two remaining failures are items 1 and 2 above. No test was weakened or deleted.

## Historical full-suite audit

Three detached worktrees were created outside the repository with `git worktree add`, and each was run using the same virtualenv and the original data placement, before copying the factors file. The worktrees were removed afterward. The later two checkouts needed a link, inside each temporary worktree only, to the current ignored `membership-mask.parquet`; without it, two extra test failures were artifacts of the worktree environment. Counts below for those commits are the reruns with that ignored input present.

| Commit | Full-suite result | Failures |
|---|---|---|
| `20ff814` (dual-run harness) | 8 failed, 599 passed, 2 skipped | Four current baseline failures above, plus four `test_anchor_set_split.py` failures because `scripts.reproduce_all` at that commit lacked `load_anchor_set_split` / `freeze_time_anchor_records`. |
| `7308092` (universe-control result) | 4 failed, 609 passed, 2 skipped | The same four current baseline failures above. |
| `e0de82a` (termination signed) | 4 failed, 609 passed, 2 skipped | The same four current baseline failures above. |

The first pass at `7308092` and `e0de82a`, before restoring the ignored membership-mask input in each temporary worktree, was `6 failed, 607 passed, 2 skipped`. Those two additional failures were `test_universe_control_effective_costs_are_the_signed_four_only` and `test_configured_costaware_creates_output_root_not_arm_directory`, both failing at the absent `membership-mask.parquet`. They are not counted as historical repository failures above.

The full suite was red at the dual-run harness checkpoint and at the universe-control and termination checkpoints. The final v16 dual-run record commit `f420350` lies between the first two; the two persistent failure paths (`test_dual_panel_run_controls`/`completed_report` and `test_snapshot_and_returns`/`backtest.run_returns`) were unchanged from `20ff814` through that record. Thus the v16 dual run, universe control, and termination were inspected while the full-suite baseline was red. This audit establishes a verification defect, not that any reported study result is numerically wrong.

The failing `test_snapshot_and_returns` covers `backtest.run_returns`, which `woodland/harness/costaware_panel.py` used for v16 dual-run and universe-control scoring. The failing dual-report test covers `completed_report`, which the v16 final-report command invoked; its fixture omission does not by itself show that the actual combined report was absent. The two `test_study.py` failures cover `etf_context` reading risk-free data from the configured frozen snapshot. The v16 dual/universe scoring paths shown in `costaware_panel.py` and `dual_panel.py` read the risk-free series from the working `data/` store instead, so this particular missing snapshot copy does not show their risk-free inputs were missing. The four extra anchor tests at `20ff814` cover the reproduced-anchor gate used before dual-run execution; they no longer fail at the later checkpoints.

## Stop condition and remaining verification

The backtest failure cannot be repaired under the operator's instruction without changing a result or the expected assertion. Work stops with two full-suite failures. The dual-report fixture was diagnosed but not altered after that stop condition. A repository-wide Ruff run also found five pre-existing import/style errors in three unrelated scripts; repository-wide mypy found 38 errors in nine unrelated files. The changed `woodland/cash.py` passed its focused mypy check. No commit was made while the required full-suite gate remains red.
