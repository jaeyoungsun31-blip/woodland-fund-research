# Security identity evidence — first 25 symbols, calibration checkpoint

Date: 2026-09-06
Status: proposed decisions only; no resolver approvals applied

User authorized retrieved external evidence with falsifiable price-file predictions and separate identity/coverage verdicts. This is a read-only corporate-action evidence audit, not a strategy study. Selection follows descending distinct membership-year count in the v8 packet (alphabetical ties), stopping at 25 symbols as requested.

Artifact: `reports/security-resolver/2026-09-06-evidence-batch01/`.

The 25 symbols contain 40 candidate rows across 39 files. Proposed identity counts: accept 16, unknown 24. Of the proposed accepts, 10 have bounds shorter than the symbol membership envelope and 6 span that envelope. Coverage is separate: an IPO-era acceptance does not establish the old same-symbol security or attribute pre-IPO absence to a vendor defect. No constituent-days measure is claimed here.

Every row contains a retrieved citation, a prediction, an observed value, agreement, and missing evidence for unknowns. Acceptance is scoped to the cited corporate-event vintage. The calibration issue is explicit: the proposed accepts use exact listing/terminal-date corroboration; DOW_old additionally reproduces the SEC-cited 2017-08-31 close of $66.65 exactly. Fifteen other proposed accepts do not yet require a second numerical fingerprint. Approximate deal-price matches are displayed as approximate and are not silently treated as exact. The packet README asks for calibration before extending to the tail.

Data were re-read from parquet, restricted to existing candidate segments. SHA-256 hashes of the 39 measured files agreed before and after measurement. Artifact checks passed: 25 distinct symbols, 40 rows, every accepted row has exact date agreement, every unknown names missing corroboration. No executable project behavior changed; no strategy test or backtest was run. Existing reported ETF bar-count test failure is untouched.

No panel built, no price data changed, no ingest run, no acceptance predicates changed, no manual rules ingested, nothing staged or committed. The remaining symbols have not been researched in this batch.
