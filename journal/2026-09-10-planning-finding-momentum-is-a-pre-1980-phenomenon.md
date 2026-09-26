# 2026-09-10 — finding: momentum is a pre-1980 phenomenon in the examined evidence

Status: **FINDING**. This is not a study, does not alter a pre-registration,
and does not select a parameter.

## Verified source records

`journal/2026-09-03-xsmom-v15-holding-results.md` records the linked complete
execution output for `xsmom-v15-holding`: Fama-French prior-12-2 deciles,
1932-09-06 through 2026-06-30, 24,434 OOS bars. Its stationary-bootstrap
95% confidence intervals compare each modeled holding frequency with
equal-weight-ten.

The intervals excluding zero by era, cost, and frequency are:

| Cost (bps) | 1932–1979 | 1980–2026 |
|---:|---|---|
| 0 (gross) | monthly, quarterly, semi-annual, annual | none |
| 5 | monthly, quarterly, semi-annual, annual | none |
| 10 | quarterly, semi-annual, annual | none |
| 25 | annual | none |
| 50 | annual | none |

`reports/xsmom-v16-universe-control/summary.json` records 5,234 OOS bars for
the completed pre-registered universe-control study. Its return artifacts run
from 2005-01-07 through 2026-06-30. That entire interval lies within the
1980–2026 era.

## Finding

Two studies using unrelated datasets and different methods now indicate no
cross-sectional momentum edge after 1980 in the examined evidence:

- `xsmom-v15-holding` used Fama-French deciles over 1932–2026 (24,434 OOS
  bars) and found no 1980–2026 interval versus equal-weight-ten that excluded
  zero at any registered cost or holding frequency.
- The pre-registered `xsmom-v16-universe-control` used EODHD constituent-panel
  returns over 2005-01-07 through 2026-06-30 (5,234 OOS bars) and failed its
  positive gate.

V16 was pre-registered and run without this cross-study connection having
been made. The result is a finding about the observed era pattern, not a
causal explanation for it. No rerun, universe variation, or next study is
proposed here.
