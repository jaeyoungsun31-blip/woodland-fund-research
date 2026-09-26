# Codex B — anchor tolerance correction

Date: 2026-09-08
Scope: snapshot-lane regression gate only.

Implemented the signed decision in
`2026-09-08-planning-decision-anchor-tolerance-published-precision.md`.

- The normal reproduced-anchor gate now evaluates only the signed 30-anchor
  set using each anchor's declared published precision: half of the final
  reported digit (`Anchor.tolerance`).  The former flat `1e-3` floor is not
  used by that gate.
- The 23 ETF replacement anchors remain disclosure-only and are never
  evaluated or counted as passes.  The signed `1e-3` ruling remains associated
  only with that replaced set; it is not applied to reproduced anchors.
- Normal gate output is a per-anchor table containing the journalled value,
  rebuilt value, absolute delta, tolerance, source entry, and pass/fail
  verdict.  It deliberately has no aggregate pass-count summary.
- Added focused tests for half-last-digit tolerances across published decimal
  precisions, rejection above an individual anchor's own tolerance, use of a
  coarse anchor's published tolerance rather than a flat floor, and the
  replacement set remaining without pass fields.

No anchor values or `config/etf-anchors-*.json` files were modified.  No
snapshot was re-pinned, no model or dual-run arm was run, and
`scripts/run_cycle.py` was not invoked.

Verification: `.venv/bin/python -m pytest tests/test_anchor_set_split.py
tests/test_live_snapshot_hardening.py` — 11 passed.
