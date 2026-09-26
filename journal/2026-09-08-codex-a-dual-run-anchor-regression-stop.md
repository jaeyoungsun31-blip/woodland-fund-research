# Codex A — dual-run anchor regression stop

Date: 2026-09-08
Status: no dual-run arm started after the signed anchor-set split.
Supersedes for the regression reason only:
`2026-09-08-codex-a-dual-run-results-v3.md`.

Codex B's anchor-set split was present and the signed rule required 30
reproduced anchors at the declared 1e-3 tolerance; 23 replaced anchors were
disclosed and not counted. The reproduction run checked all 30 and found 5
failures, so the gate did not pass and the four-arm run was not started.

| journal entry | metric | journalled | rebuilt |
| --- | --- | ---: | ---: |
| 2026-09-02-xsmom-v10-results | xsmom top-3 turnover | 5.230000 | 5.232499 |
| 2026-09-02-xsmom-v10-results | equal-weight-12 turnover | 0.270000 | 0.266288 |
| 2026-09-03-planning-note-turnover-budget | K mean product | 232.200000 | 232.217327 |
| 2026-09-03-planning-note-turnover-budget | K minimum product | 219.600000 | 219.640460 |
| 2026-09-03-planning-note-turnover-budget | K maximum product | 242.700000 | 242.737882 |

Result: 30 checked, 25 passed, 5 failed; 23 replaced anchors disclosed, not
counted. No model fit, validation fold, or arm execution occurred after this
gate failure.
