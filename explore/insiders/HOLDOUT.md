# Sealed insider-purchase holdout

Filings dated **2022-07-01 through 2026-06-30, inclusive**, are a sealed
holdout. This Phase 2 return study may calculate or inspect returns only for
filings dated **2012-01-01 through 2022-06-30, inclusive**. No return,
portfolio, spread, alpha, or event-window diagnostic may use a holdout-dated
filing, even if that filing already appears in the earlier source-feasibility
census. Events after 2026-06-30 are also outside the training interval.

Every return-analysis entry point must call `require_training_events` from
`holdout.py` before reading price bars or factors. It raises on any event whose
filing date is missing, invalid, or outside the training interval; it never
silently drops events. Source-acquisition and source-census artifacts created
before this lock may retain later filings, but they cannot be supplied to a
return-analysis script without first constructing an explicitly dated training
selection and passing the guard. The holdout remains unopened in this study.
