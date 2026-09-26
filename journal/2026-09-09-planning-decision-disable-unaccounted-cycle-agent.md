# Planning decision — disable the unaccounted 15:00 cycle LaunchAgent

Status: SIGNED BY PLANNING, 2026-09-09.

`~/Library/LaunchAgents/com.jaeyoung.woodland.cycle.plist` runs daily near
15:00 with `--execute --emit-targets --submit-paper --refresh-data`. No entry
in this record authorizes it. Asked directly, Jaeyoung does not recognize it.
It is disabled; the plist is preserved under `ops/disabled-launchagents/` and
the decision is reversible.

## What was verified, and how

Read from primary sources, not from a summary.

**Refresh scope.** A firing rewrites the live mutable store only. All twenty
`data/*.parquet` ETF files plus `data/_provenance.json` carry mtimes after
2026-09-09 18:00 UTC, from the 15:15 EDT firing. The frozen snapshot
`data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/`
was not touched: newest member is `freeze-time-anchors.json` at 2026-09-08
19:50, parquets at 2026-09-08 02:05. `scripts/run_cycle.py:101` passes
`refresh=args.refresh_data` into `build_snapshot`, which writes the live store.
The hash guard held. The closed v16 study's evidence is intact.

This is the same mechanism that rewrote the ETF store mid-run on 2026-09-07
and cost a full cycle.

**False success in the operational record.** `validate_submission`
(`woodland/live/broker.py:101-125`) checks phase-3 refusal, market hours,
notional caps and target bounds. It has no empty-order-list check. With zero
planned orders, `submit_rebalance` passes validation at `broker.py:325`, the
POST loop at `broker.py:328` never executes, no `/orders` call is made, and it
returns `SubmissionResult((), (), equity)` normally. `woodland/live/cycle.py:620`
then takes the `else` branch and writes "submitted to Alpaca Paper" with
`paper_order_count = 0`.

Nothing was submitted. The success string is emitted unconditionally on the
non-refusal path. It appears in at least three committed cycle entries whose
header reads "Append-only operational record."

**Alpaca 403 resolved.** No 403, forbidden or unauthorized occurrence in
`data/live/cycle-stdout.log`. `market_open()` and `plan_rebalance()` both
require authenticated calls before validation runs; both succeeded on
2026-09-09. The open item dated 2026-09-04 is closed. When it was fixed was
never recorded.

**INVESTIGATE tolerance at its ceiling.** `STORE_WIDE_INVESTIGATE_BASELINE = 11`
is a hardcoded constant at `woodland/live/cycle.py:40` grandfathering eleven
permanently-failing Tiingo cross-checks. Flagged count was 9 on 2026-09-08
(XLI XLK XLP XLU XLV XLY QQQ EFA DBC) and 11 on 2026-09-09 (adding XLB, XLE).
It is now exactly at the ceiling. One further flagged ticker and the cycle
refuses.

These are verdicts against the live store as of 2026-09-09, not against the
2026-09-04 frozen vintage. Whether the same disagreements exist in the frozen
data is unverified and is not reopened here.

## Deferred, not fixed

Two items are appended to `journal/defect-register.md` rather than fixed now,
per the signed stopping rule:

- the unconditional "submitted to Alpaca Paper" string;
- the INVESTIGATE baseline as a hardcoded constant with no provenance for the
  number 11 and no record of which eleven tickers it was meant to cover.

## Reversal

`launchctl load -w ops/disabled-launchagents/com.jaeyoung.woodland.cycle.plist`
after moving it back to `~/Library/LaunchAgents/`. Do not re-enable until both
deferred items are fixed and an entry in this record states what the job is for.
