# 2026-09-01 — Second data source decision: Tiingo + Alpaca ("both")

Append-only. Resolves the open decision in
journal/2026-09-01-data-source-stooq-blocked.md. Decided by Jaeyoung in the
planning chat, 2026-09-01.

## Decision

* **Tiingo** becomes the cross-check source (DESIGN.md §5, amended today):
  free keyed API with 20+ years of adjusted EOD history, so the corruption
  check covers the FULL backtest period, which is the job the check exists
  to do.
* **Alpaca** account is confirmed for Phase 4 (paper execution + its data
  feed for live-vs-simulated drift monitoring). Not used as the research
  cross-check: its free feed's shorter history would leave the early
  backtest years unguarded.

## What this unblocks / requires

1. Jaeyoung signs up at tiingo.com and puts `TIINGO_API_KEY=...` in `.env`
   (gitignored; never committed).
2. Coding chat wires Tiingo into `woodland/data.py` as `crosscheck_source`
   and re-enables `crosscheck_sources()` in ingest; `config/universe.yaml`
   `crosscheck_source: tiingo`.
3. First full dual-source ingest re-validates the store. Until that run
   completes clean, every result keeps the single-source caveat.
4. Alpaca signup can wait until Phase 4 starts.
