# Codex A — dual-run v3 regression stop

Date: 2026-09-08
Status: no v3 arm run.

Implemented the signed resolver-derived membership-mask artifact and short-gap
fill. The rebuilt panel reports 45 filled zero-return cells, audited at
`reports/security-resolver/2026-09-07-constituent-panel/short-gap-fills.csv`,
and writes the per-date/symbol mask at
`reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet`.

The required ETF anchor regression could not complete. The configured frozen
ETF snapshot has no `fama_french_factors_daily.parquet`, so
`scripts/reproduce_all.py --measurement-only-json ...` skipped the ETF group.
It checked 30 non-ETF anchors with 0 failures, then refused the incomplete
census. Therefore the required 43/53 ETF confirmation within 1e-3 is
unavailable, and all four v3 arms remain unrun.

Question filed in `AGENTS.md` under `[QUESTION][CODEX-A]`.
