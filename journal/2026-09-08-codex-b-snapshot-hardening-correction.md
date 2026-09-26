# Snapshot hardening correction — Codex B

Date: 2026-09-08  
Status: correction record; supersedes nothing

The prior hardening entry remains in the append-only record. A later check
correctly found that the real snapshot directory had reverted to owner-writable
mode (0700), so its claim could not be relied on as a current artifact property.

Re-applied chmod a-w to the exact configured artifact:

data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/

The final mode is directory 0500 (dr-x------) and parquet 0444
(-r--r--r--). A direct touch attempt inside that exact directory was refused
with Permission denied. The test was changed from a disposable fixture to the
configured snapshot itself: it attempts append-open on a real configured
parquet and unique-file creation in the real configured directory, expecting
PermissionError for both. This test passed while the real directory was mode
0500.

No snapshot content, anchors, configuration, cycle, broker behavior, or
planning stray file was changed. Two short-lived diagnostic probe files that
this correction created during the observed writable interval were removed;
the planning file at _to_delete/claude-stray/_x was not touched.
