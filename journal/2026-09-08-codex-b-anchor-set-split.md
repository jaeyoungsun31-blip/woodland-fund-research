# Anchor-set split and freeze-time anchor registry — Codex B

Date: 2026-09-08  
Status: engineering implementation of signed planning decisions; no fit, dual-run, cycle, re-anchor, or anchor-value change

## Signed regression gate

Implemented the signed 30/23 partition from
2026-09-08-planning-decision-anchor-set-split.md.

- 30 reproduced anchors remain the only pass/fail gate inputs and retain their
  original journalled values.
- 23 replaced ETF-window anchors are identified from their existing
  unavailable-earlier-input reason in config/etf-anchors-2026-09-07.json.
  They are disclosed as replaced and excluded from normal reconstruction,
  failures, pass counts, and every pass summary.
- The normal gate uses the signed inclusive 1e-3 tolerance. A delta exceeding
  1e-3 fails. The frozen configured snapshot hash
  4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901 is
  accepted by normal verification; verify_snapshot=False remains used only by
  the explicit measurement-only command path.

No anchor value or existing anchor registry entry was changed.

## Freeze-time anchor registry

Added the freeze-time emission primitive and backfilled the configured frozen
snapshot with:

data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/freeze-time-anchors.json

The manifest carries the snapshot identity and all 53 anchor values with their
classification: 30 reproduced and 23 replaced. The emitter refuses to replace
an existing manifest with different content. Future freeze callers must use
this emission path, so a snapshot carries its own anchor registry rather than
depending on a later mutable store.

## Read integrity and verification

The prior content-hash guard remains active: any research-mode matrix read
resolving to data.store recomputes the complete 20-ETF adjusted-close hash and
refuses a mismatch. Direct ETF snapshot reads use the same guard. Directory
permission immutability remains abandoned because the mount resets directory
mode; read-only parquet files remain defense in depth.

Focused tests passed for the 30/23 split, an over-1e-3 refusal, exclusion of
replaced anchors from pass fields, freeze-time emission, and configured
snapshot hash verification. Compilation and Ruff were clean. No cycle or
research strategy execution occurred.
