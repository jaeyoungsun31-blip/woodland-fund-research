# Codex A — sealed dual-run controls — 2026-09-09

Implemented the v4 execution-mechanics controls for the panel harness:

- `--run-all` creates a fresh UUID run identity and records it at the run root.
- Each arm writes exclusively to a hidden, run-specific staging directory and
  is atomically renamed to its completed arm directory only after success.
- `--report` accepts only the four completed arm directories for the current
  run identity; staging paths are not report inputs.

No study arm, fitting operation, or report was run while making this change.
