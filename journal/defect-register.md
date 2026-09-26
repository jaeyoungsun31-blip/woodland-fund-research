# Defect register

Append-only register. Every item below is deferred to next study, not this one.

## 2026-09-09 — full-panel >100% daily cells

Scope: 27 symbols, 348 cells: ACS 56; AYE 1; BCR 1; BLL 3; CBE 210; CERN 2;
CFC 29; CSR 1; FBF 7; GR 2; HIG 1; HPC 1; JWN 1; KATE 1; MRO 1; NCR 1; QLGC
1; RAI 1; RRD 3; RX 5; SOV 12; STJ 1; TIN 1; TWX 2; UVN 2; WMB 1; X 1.
Evidence: `reports/security-resolver/2026-09-07-constituent-panel/panel-returns-a2-favourable.parquet`.
Deferred to next study, not this one.

## 2026-09-09 — C3 feasibility

Scope: C3 was unachievable by panel construction. Evidence:
`journal/2026-09-08-xsmom-v16-dual-run-preregistration.md`. A pre-run
feasibility check is required. Deferred to next study, not this one.

## 2026-09-09 — null sign concordance

Scope: `evaluate_gate` has no minimum effect size and can agree on a null.
Evidence: `woodland/harness/dual_panel.py`. Requires an equivalence-band
formulation. Deferred to next study, not this one.

## 2026-09-09 — unclassified A2 exits

Scope: 441 unclassified A2 exits. Evidence:
`reports/security-resolver/2026-09-07-constituent-panel/panel-summary.json`.
Deferred to next study, not this one.

## 2026-09-09 — unconditional paper-submission success string

Scope: `woodland/live/cycle.py:620` writes "submitted to Alpaca Paper" whenever
`submit_rebalance` returns without raising, including when zero orders were
planned and no `/orders` call was made. `validate_submission`
(`woodland/live/broker.py:101-125`) has no empty-order-list check. Evidence:
`journal/2026-09-08-phase3-cycle-151116.md`, `journal/2026-09-09-phase3-cycle-151514.md`.
Deferred to next study, not this one.

## 2026-09-09 — INVESTIGATE baseline is an unprovenanced constant

Scope: `STORE_WIDE_INVESTIGATE_BASELINE = 11` at `woodland/live/cycle.py:40`
grandfathers eleven cross-check failures with no record of which eleven tickers
it was meant to cover or when it was set. Flagged count reached 11 of 11 on
2026-09-09. Evidence: `journal/2026-09-08-phase3-cycle-151116.md`,
`journal/2026-09-09-phase3-cycle-151514.md`. Deferred to next study, not this one.

## 2026-09-22 — unpinned ignored study inputs at v16 and universe-control execution

| Defect | Affected ignored inputs | Resolution and historical limit |
|---|---|---|
| Raw SHA-256 was not enforced before v16 and universe-control results were inspected | `reports/security-resolver/2026-09-07-constituent-panel/{membership-mask.parquet,panel-returns.parquet,panel-returns-a2-favourable.parquet,panel-returns-a2-adverse.parquet,panel-summary.json}`; `reports/security-resolver/2026-09-07-tiingo-crosscheck/crosscheck.csv`; `reports/security-resolver/2026-09-07-missed-event-screen/missed-event-candidates.csv`; `reports/xsmom-v16-panel/pinned-run/inputs.json`; `data/SPY.parquet`; both working/frozen `fama_french_factors_daily.parquet`; all 20 frozen ETF parquets (their aggregate adjusted-close frame was pinned, but raw bytes were not) | Raw hashes and guard paths are recorded in `journal/2026-09-22-codex-defect-resolution-input-pins.md` and `config/universe.yaml`. Current `panel-returns.parquet` differs from its historical recorded hash and is now refused. Retrospective identity of other inputs without historical raw hashes cannot be established from today's bytes. |

## 2026-09-24 — unverified lane-completion claims in uncommitted `STATE.md` edits

Scope: on or before 2026-09-25, uncommitted edits to `STATE.md` inserted two
near-duplicate §10 changelog entries attributed to "Qwen (coding)" and dated
2026-09-07, placed between existing 2026-09-07 and 2026-09-08 lines. They
claimed a volume-plausibility screen, a sub-threshold seam flag and a
currency-plausibility screen had been added to a `unique_live_candidate`
function, and the second added a Tiingo panel cross-check. These are the four
items §12 assigned to Qwen as its Tier 3 lane (§12 committed in `f420350`), so
the edits read as completion claims for an authorized agent's lane.
Verification: `unique_live_candidate` is a match-basis string
(`woodland/live/security_resolver.py:277`), not a function; no
volume-plausibility, currency-plausibility or seam-flag code exists in
`woodland/`, `scripts/` or `tests/`; no commit is attributed to Qwen. The
Tiingo cross-check exists but was written and run by Claude Code in `53e1572`,
not as part of any `unique_live_candidate` function; §12's own changelog
already records that lane collision.
Resolution: the edits were discarded unmerged with `git restore STATE.md`. No
committed content was changed. Not deferred.
Mitigation: agents other than Claude Code and Codex may not write to
`STATE.md` or `journal/`, and every changelog claim must cite a commit hash.
This supersedes the write access implied by Qwen's §12 lane. `STATE.md` §12
itself still lists that lane and was not edited here.
