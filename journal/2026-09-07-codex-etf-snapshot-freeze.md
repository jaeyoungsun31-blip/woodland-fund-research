# ETF snapshot freeze — Codex B

Date: 2026-09-07  
Status: engineering record; no study, fit, promotion, re-pinning, or anchor decision

## Frozen artifact

Copied (never moved or overwrote) the 20 configured ETF parquet files from the
mutable live working store into:

`data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/`

The content-address hash protocol is the existing adjusted-close protocol:
ordered configured columns; sorted date-index CSV; `%.17g`; explicit `NA`;
LF; UTF-8.  It was computed from the source immediately before the copy and
again from the copied files.  Both results were:

- SHA-256: `4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901`
- configured ETF files: 20
- rows: 6,968
- first/last bars: 1998-12-22 / 2026-09-04

The snapshot directory and every copied parquet have write permission removed.
This is a storage/control-plane freeze only.  In particular, it does **not**
register this hash as an accepted research baseline, re-pin, alter
`config/etf-anchors-2026-09-07.json`, regenerate anchors, or resolve the ten
anchor failures.  The existing question of whether the prior replacement-anchor
artifact already accepted a changed snapshot remains for planning.

## Store separation

`config/universe.yaml` now makes the frozen artifact `data.store`, so ordinary
research readers resolve to the immutable copy.  It declares `data.live_store:
data/` for the mutable operational store.  `scripts/ingest.py` now defaults to
that live store, and `scripts/run_cycle.py` explicitly passes it to the live
snapshot builder.  Consequently `--refresh-data` refreshes only `data/*.parquet`
and does not mutate the research artifact.  This record did not execute
`run_cycle.py` in any mode.

## Investigation only: the 15:00 invocation

The repository template `ops/com.jaeyoung.woodland.cycle.plist` specifies
15:45, but the loaded LaunchAgent is a distinct installed file at
`<home>/Library/LaunchAgents/com.jaeyoung.woodland.cycle.plist`.
Its `StartCalendarInterval` specifies weekdays at 15:00 and its program
arguments exactly include `--execute --emit-targets --submit-paper
--refresh-data`.  `launchctl print gui/501/com.jaeyoung.woodland.cycle` reports
that installed file as the active job configuration and records two runs.
That installed 15:00 LaunchAgent explains the 15:00:21 EDT invocation.  No
plist was changed in this work.

## Investigation only: Alpaca 403

The recorded failure is a `requests.exceptions.HTTPError` raised by
`PaperBroker._post` after the POST to the correctly guarded Paper endpoint
`https://paper-api.alpaca.markets/v2/orders`.  `assert_paper_base_url` still
requires exactly that hostname.  The captured stderr contains no response body
or Alpaca error code, so the record proves that order submission was forbidden
but cannot distinguish an account-trading restriction from a credential or
authorization change.  No Alpaca request, credential inspection, logging, or
broker change was made here.  The 2026-09-07 cycle was market-closed and made
no submission attempt; therefore Phase 4 has not established successful
submission after the 2026-09-04 403.
