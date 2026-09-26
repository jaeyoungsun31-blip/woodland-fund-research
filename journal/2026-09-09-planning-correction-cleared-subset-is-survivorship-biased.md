# Planning correction — cleared subset is survivorship-biased

Corrects: `journal/2026-09-09-planning-ruling-v16-dual-run-closed.md`.

The v16 closure stands. Its claim that the survivorship-free panel does not
support v16 is not supported by arms A/B, which are survivor-skewed.

The frozen cleared-subset artifact excludes 469 symbols carrying
`no_tiingo_series` (including compound exclusion reasons). Of those, 308/469
(65.67%) have their last membership date before 2026; the corresponding
fraction for the cleared 220 is 44/220 (20.00%). Arm A membership names are
64 / 149 / 197 (min / median / max), versus 346 / 439 / 503 for Arm C.

Evidence: `reports/cleared-subset-2026-09-07/cleared-subset.csv`,
`reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet`,
and `reports/xsmom-v16-dual-run/arms/dual-{A,C}/eligibility-by-day.csv`.
