# 2026-09-01 — Planning decisions: cross-check verdict policy, DSR breadth, 2026-08-28 repair

Append-only. Resolves Q1 and Q2 from QUESTIONS FOR PLANNING (raised in
journal/2026-09-01-tiingo-crosscheck-first-run.md and the trend-v1 results).
Decided in the planning chat, 2026-09-01, BEFORE the next ingest or study.

## Q1 — cross-check verdict: two-tier (option b)

* FAIL: any single day where the two feeds' adjusted returns differ by more
  than 2% (would still catch a missed dividend or a corrupt bar).
* MONITOR: the count of days differing by >50 bps is reported per ticker on
  every ingest and must not grow materially above the recorded baseline
  (484 / 122,905 observations as of 2026-09-01). Growth = investigate.
* With this policy, the 2026-09-01 dual-source run is CLEAN except for the
  known historical disagreements, and the single-source caveat is LIFTED
  once the next ingest passes under the codified rule.

## 2026-08-28 repair: approved

Fill Yahoo's missing 2026-08-28 bar (13 tickers) from Tiingo. Any bar whose
provenance is the cross-check source must be flagged in data/_provenance.json.
General rule: the cross-check source may fill a bar the primary is missing
only when the bar is confirmed real; it never overrides a bar both have.

## Q2 — deflated Sharpe: option (c)

Keep train-window Sharpes as the variance input, and report an explicit
"effective breadth" note beside every DSR (number of distinct configs, their
Sharpe spread/sd) so a narrow one-parameter sweep cannot masquerade as a wide
search. Every reported DSR carries the caveat that near-collinear trials make
it a weak hurdle.

## Also decided: rejected directions (do not build)

* Reinforcement-style learning from the strategy's own trade outcomes.
* Any rule conditioned on the shapes/patterns of specific historical crashes
  (n≈3 crash episodes in sample; that is memorization, not learning).
* Responsiveness to CURRENT conditions (realized-vol targeting, drawdown-
  responsive exposure) is the approved form of "caution" — see trend-v3.
