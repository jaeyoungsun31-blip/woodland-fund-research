# Codex A — xsmom-v16 dual-run results

Date: 2026-09-08
Status: completed all-four-arm invocation; all four arms refused before an OOS
result, so C1/C2/C3 and the acceptance gate are unavailable.

## Authorization and fixed inputs

The mechanical anchor gate accepted the signed journal ruling
`2026-09-08-planning-decision-etf-anchor-tolerance.md`, parsing its declared
Sharpe-anchor reproduction tolerance as `1e-3`. The signed cost clarification
set the flat schedule to 0/5/10/25 bps. No per-symbol cost was used.

The one invocation assembled all pre-registered arms: A 220 favourable, B 220
adverse, C 942 favourable, and D 950 adverse columns, each over 6,736 panel
dates. The frozen cleared list was read from its planning artifact. The 3
pending-A2-Amendment-1 symbol-years remained quarantined.

## Outcomes

Each arm reached the first training fold and recorded all 16 registered cells;
each then refused because every cell encountered an unpriceable held or target
asset. No OOS returns, baselines, turnover, subperiod metrics, bootstrap/HAC
comparison, or promotion result was manufactured.

| arm | status | trials | first refusal |
| --- | --- | ---: | --- |
| A | refused | 16 | held `OKE` missing price, 2001-08-30 |
| B | refused | 16 | held `OKE` missing price, 2001-08-30 |
| C | refused | 16 | target `FWLT` missing price, 2000-02-01 |
| D | refused | 16 | held `OI` missing price, 2000-12-11 |

Consequently C1, C2, and C3 are `null` in all four arm summaries and no
same-sign/CI-overlap evaluation exists. This record reports the refused run
only and makes no interpretation.

## Mandatory disclosure carried by the harness

- Cleared / total: 220 / 942.
- A2 exits: 452 total; 8 treated (Case 1: 0, Case 2: 8, Case 4: 0), 441
  unclassified, 3 quarantined.
- Independent Tiingo comparison: 430 / 942; the un-compared population is
  delisted-skewed.
- Universe asymmetry: the favourable panel has 942 columns and adverse has
  950 because eight Case 2 absent-name columns exist only in the adverse bound.

The full refusal artifacts are under `reports/xsmom-v16-dual-run/`.
