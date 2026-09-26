# Snapshot hardening and broker-error diagnostics — Codex B

Date: 2026-09-08  
Status: engineering maintenance; no cycle execution, model run, re-pin, or anchor change

## Snapshot directory permission

The immutable ETF artifact remains:

`data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/`

Its parquet files were already read-only, but the enclosing directory still
allowed owner writes.  Removed write permission from the directory itself.
An actual `touch` attempt for a new file inside that directory was refused with
`Permission denied`; this was an operation test, not merely a mode inspection.
The directory is now owner read/execute only and the copied parquets remain
read-only.  No content was changed, and the planning stray file at
`_to_delete/claude-stray/_x` was not touched.

Added a focused test that proves both necessary controls using a disposable
snapshot fixture: replacing a read-only parquet fails and creating a new file
in a non-writable snapshot directory fails.

## Broker HTTP failure diagnostics

`PaperBroker` now logs the HTTP method, path, status, provider error `code`,
and provider `message` whenever `raise_for_status()` raises an HTTP error.  It
does not log request headers, payload headers, credentials, or endpoint tokens.
Before logging, known credential values are explicitly replaced with
`[REDACTED]`, and header-shaped `APCA-API-KEY-ID`, `APCA-API-SECRET-KEY`, and
`Authorization` values are redacted as well.

The endpoint guard is unchanged: `assert_paper_base_url` continues to require
hostname exactly `paper-api.alpaca.markets`.  No Alpaca request or credential
inspection was made.  This instruments a future failure; it does not resolve
or infer the cause of the 2026-09-04 403.

Focused verification passed: the snapshot immutability test and the broker
diagnostic/redaction test; Python compilation and Ruff were clean.  The cycle
entrypoint was not executed.
