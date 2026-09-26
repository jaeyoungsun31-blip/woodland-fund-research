# 2026-09-01 — Trend study v1: pre-registration (BINDING)

Append-only, written BEFORE the study runs (CLAUDE.md rule 3). Everything
below is fixed in advance so the result cannot be reverse-engineered from
what looked good afterwards.

Study id: `trend-v1`. Split scheme: as pre-registered in
`journal/2026-09-01-harness-scheme-preregistration.md` (5y train / 1y validate
/ 1y step / 210-bar embargo, 22 folds, 21.8y stitched OOS from 2004-10-22).

## Strategy

Faber-style time-series trend (DESIGN.md §9 candidate 1). At each month-end
close an asset is "in trend" if its close exceeds its N-month simple moving
average. Risky weight is split equally across in-trend assets; the remainder
goes to the risk-off leg. Executed on the next bar by the engine.

## Fixed design choices (NOT searched)

| Choice | Value | Why fixed |
|---|---|---|
| risk assets | the 9 original SPDR sector ETFs (XLB XLE XLF XLI XLK XLP XLU XLV XLY) | all trade from 1998-12-22, so the universe composition never drifts mid-sample. XLRE (2015-) and XLC (2018-) are excluded for exactly that reason; DBC likewise (2006-). |
| risk-off leg | IEF | DESIGN.md §9 ("else T-bills/IEF") |
| max risk weight | 1.0 | long-only, no leverage (engine v0) |
| rebalance | month-end | DESIGN.md §9 |

Holding the universe fixed keeps the searched surface one-dimensional. Every
extra searched dimension is a multiplier on the trial count and therefore on
the deflation hurdle.

## The search grid — the ONLY searched parameter

`lookback_months ∈ {4, 5, 6, 7, 8, 9, 10}` → **7 configurations**.

Bracketed below the published 10-month Faber rule rather than around it,
because 10 months is the declared `max_lookback_days = 210` and the embargo is
210 bars. A 12-month variant would reach 252 bars, past the embargo, and
`check_embargo_covers_lookback` would (correctly) refuse to run. Extending the
grid upward therefore requires a longer embargo and a NEW journal entry first.

Expected ledger: 7 distinct configs × 22 splits = 154 evaluations. Deflated
Sharpe uses the distinct-config count, 7 (rule 4, per the harness-scheme entry).

## Selection rule

Per split, the config with the highest annualized Sharpe (rf=0) on that
split's train window, at 5 bps. Ties resolve to the lower index, i.e. the
shorter lookback. rf=0 overstates Sharpe in high-rate regimes and no number
from this study leaves the repo without that qualifier.

## Reporting, fixed in advance

Stitched OOS at 0/5/10 bps, beside SPY buy&hold and 60/40 over the identical
window, with `metrics.by_subperiod` and the deflated Sharpe against the full
trial count (CLAUDE.md rules 5 and 7). No single blended headline number.

## What this study cannot conclude

It is one strategy family, one universe, on data resting on a cross-check that
has not yet run clean (`journal/2026-09-01-tiingo-crosscheck-first-run.md`).
It is a harness result, **not** a promotion decision: the §8 gate is Phase 3
and planning has not seen these results yet. Whatever comes out, nothing is
promoted and nothing is traded.
