# Snapshot hash guard — Codex B

Date: 2026-09-08  
Status: engineering control replacement; no study, fit, cycle execution, re-pin, or anchor change

## Permission-based directory immutability abandoned

Directory permission is not a durable control on this mount. The snapshot
directory was observed to revert from non-writable mode to owner-writable mode
after hardening attempts, so a chmod-based claim cannot be relied on. No further
directory chmod attempts will be used as the integrity control. The copied ETF
parquet files remain read-only (0444), which does hold, but file permissions
are now treated as defense in depth rather than the research integrity boundary.

## Content verification on research reads

The configured research store remains:

data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/

The expected adjusted-close content hash is now declared as
data.research_snapshot_sha256 in config/universe.yaml:

4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901

Before any research-mode data.build_matrix read resolving to data.store, the
system recomputes the complete configured 20-ETF adjusted-close hash using the
existing sorted date-index CSV protocol and refuses on a mismatch. The direct
woodland.snapshot.etf_snapshot reader applies the same guard before returning
its result. Thus a delete-and-recreate change in the directory cannot silently
become research input.

Focused verification passed: a full configured-store matrix read returned the
expected hash and 6,968 by 20 shape; tests cover both the matching path and a
constructed mismatch refusal. No snapshot content, anchor file, live cycle,
broker, or planning stray file was changed.
