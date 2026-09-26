# 2026-09-26 — planning decision: the active research phase is closed

Status: **DECIDED** in planning on Jaeyoung's instruction. No prior entry is
edited.

Records the last evidence: the Open Source Asset Pricing (OSAP) triage
(`0d06055`), the pre-committed composite test (precommit `fe87084`, results
`a1e7169`), and the decision it supports. Earlier closures stand as recorded:
- `2026-09-10-planning-decision-termination-signed.md` (momentum)
- `2026-09-25-planning-decision-insider-clusters-closed.md`
- `2026-09-25-kalshi-mlb-favourite-closed.md`
- `2026-09-26-planning-decision-kalshi-closed.md`

## Evidence

All figures are from `explore/osap/triage_report.md` and
`explore/osap/composite_report.md`. Returns are OSAP monthly long-short
returns, release v2.0.0, in percent per month, **gross of all trading
costs**.

**Triage (descriptive, no selection).** Value-weighted, 2015–2024:
- **14 of 208** predictors have a positive mean with t > 2.
- About **5** would do so by chance alone if every true mean were zero.
- The same count is 30 of 208 on the original, mostly equal-weighted,
  specification.

**Composite (pre-registered, all 212 predictors, none selected).** Newey–West
t-statistics, lag 6.

| Composite | Window | Mean | t |
|---|---|---:|---:|
| **Value-weighted, post-publication (primary)** | 2015–2024 | **+0.103%** | **1.34** |
| Value-weighted, post-publication | 2000–2024 | +0.221% | 3.00 |
| Original specification (equal-weighted), post-publication | 2015–2024 | +0.292% | 3.61 |

The primary fell below its pre-set t ≥ 2. The smallest mean detectable at
t = 2 was 0.153% per month.

**Diversification.** In 2015–2024, the 195 complete value-weighted series
behave like an effective **13.4** independent signals. That is the
participation ratio of the correlation-matrix eigenvalues.

## Conclusion (observed, not causal)

Published cross-sectional signals show little gross value-weighted return in
liquid US stocks after 2015. The primary composite's +0.103% per month is not
distinguishable from zero, and what remains concentrates in equal-weighted,
small-stock portfolios.

Planning judges that return to be below plausible trading costs. **That
comparison is a judgement, not a measurement.** No turnover or cost was
computed for the OSAP portfolios, and a composite of about 200 long-short
books implies very high turnover.

This entry makes no claim about why the return is small. "Already arbitraged"
is one explanation consistent with it, and it was not tested.

## Decision

- **The active research phase is closed.** No study is open or queued.
- **The live cycle stays disabled.** Its launch agent is preserved,
  unloaded, at `ops/disabled-launchagents/com.jaeyoung.woodland.cycle.plist`.
- **No capital is committed.** Nothing has been promoted, and no live-money
  strategy has traded.

## Open avenues: unfunded, not active

These are recorded so they are not lost, not as a queue. Any of them needs a
funding decision and a new pre-registration that passes T2
(`2026-09-03-planning-decision-termination-and-v16-withdrawal.md`) before any
work starts.

1. **Small-cap research with paid data.** What survives is in equal-weighted,
   small-stock portfolios. Testing whether it survives costs needs
   point-in-time small-cap prices, spreads and borrow data that free sources
   do not provide at acceptable quality.
2. **A novel dataset.** A signal not already in the published literature, and
   so not already priced into OSAP's 212.
3. **A live Kalshi maker experiment.** Resting orders cannot be tested
   historically, because fills are not observable in candles
   (`2026-09-26-planning-decision-kalshi-closed.md`). Only a small, live,
   pre-registered experiment could measure fill rates and adverse selection.

## Also recorded today

- **Test fix, `616233e`.**
  `explore/insiders/test_bias_corrections.py::test_official_monthly_archive_has_expected_columns`
  now skips, with a reason, when the gitignored Ken French ZIP is absent.
  With the file present, the assertions are unchanged.
- **`STATE.md` changelog.** Two lines were appended: the agent write-access
  rule, citing `fcf763d`, and a pointer to this entry.
