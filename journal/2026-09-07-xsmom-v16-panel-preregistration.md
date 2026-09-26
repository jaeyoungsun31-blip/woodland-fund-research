# xsmom-v16 constituent panel — frozen two-arm preregistration

Date: 2026-09-07
ETF as_of: 2026-09-04
ETF adjusted-close SHA256: 7b64be101f62166ed9261a8d51a8894f61310238dfa8d75c2c8e4f3d45c233e6
Panel as_of: 2026-06-30
Panel parquet SHA256: 47d4eee2c5c90a37a731d985148efb85058fae40dc2202a5f4953d04884fcaf5
Study IDs: xsmom-v16-panel-A-20260907, xsmom-v16-panel-B-20260907
Status: registered before any model fitting or portfolio result inspection.

## Frozen design

Implements journal/2026-09-03-xsmom-v16-costaware-preregistration.md on the
existing 942-symbol constituent return panel: 6736 dates, 1999-01-06 through
2026-06-30, 2964872 observations. No panel rebuild and no price writes.
The ETF reproduction prerequisite was explicitly withdrawn for this study.

Six features only: mom_12_2 (t-252 to t-21 cumulative return), rev_1m (t-21 to t),
rev_1w (t-5 to t), vol_63 (63 daily returns' sample standard deviation), volvol_63
(sample standard deviation over 63 values of trailing 21-day sample volatility),
dd_252 (current level / trailing 252-level maximum minus one). Compute cumulative
features from observed returns, never generate or store substitute price bars.
Within each date and arm, cross-sectional z-score (population scale), then clip
to [-3,3]. Missing-feature rows cannot train or form; constant-feature columns
have zero standardized value. No winsorisation of realized returns or labels.

Ridge plus temporal penalty: b = (X'X + alpha I + lambda D'D)^(-1) X'y;
y is forward 21-trading-bar cumulative return. Training labels must finish within
the training window and contain no missing observations. D consists only of
consecutive eligible feature rows for the same symbol, with no bridge over holes.
No intercept. Grid alpha={0.01,0.1,1,10}, lambda={0,0.5,2,8}: all 16 cells per
fold, every evaluated or failed cell recorded in the append-only trials ledger.
Choose best-in-train net excess-return Sharpe at 5 bps, separately over lambda>0
and lambda=0. Ties use ascending alpha then lambda; no widening or post-fit change.

Walk-forward: 5 calendar years train / 1 validate / 1 step, 252 trading-bar embargo.
Assert embargo >=252. Frozen measured realization: 22 folds,
5234 OOS bars, 2005-01-07 through 2026-06-30.
No-lookahead perturbation must pass before any fitted real-panel result is read:
features, fitted coefficients using completed past labels, and formation weights
at/before the cutoff remain bit-identical when future panel returns change.

Long-only, unlevered, monthly formation, equal weight top 30% (ceiling of count)
of complete eligible feature rows. Trades execute next close; weights drift and
seam turnover is charged. Flat costs 0/5/10/25/50 bps; no unsigned per-symbol inputs.
Controls: lambda=0 twin, hand-specified mom_12_2 on the same eligible cross-section,
equal-weight eligible universe, SPY buy/hold, monthly SPY/IEF 60/40 (and MKT reference
where available). Same OOS calendar, costs and aligned stored risk-free returns.
Sharpe and paired inference use excess returns, never rf=0 as the headline.

## Two arms, fixed before fitting

A: all 942 supplied names, subject only to membership and complete features.
A remains the estimate, with its declared data defects, not an endorsed clean panel.
B: remove the 68 Tiingo fail-tolerance names for the whole run, and make
symbols ineligible from each of the 143 flagged dates t through t+252 panel trading
days inclusive. Overlapping windows union. The mask only applies to existing
membership observations; no synthetic observations or zero-return fills.
The screen is return-conditioned even within these windows and cannot distinguish
a real crash from a missed split. B is a sensitivity bound, not an unbiased estimate.
Past holdings continue to earn observed returns until next-close exit. Applying a
flag cannot erase a realized loss retrospectively. An unpriceable held return is
a refusal, never zero, an implicit cash exit, renormalisation, or a skipped day.
Monthly selection and next-close execution are unchanged; daily ineligibility
creates an exit instruction at that close, executed next close. No retrospective
exit before a newly observed flag is permitted.

Record all ineligible symbol-days, overlap with the Tiingo exclusions, daily mask
counts, portfolio-days with >10% of pre-exclusion eligible names excluded, and
minimum eligible universe size (before and after feature availability).
Pre-fit mask census: 477164 membership symbol-days
ineligible; 6736 panel dates >10%; minimum 279
remaining membership-eligible names. These are data-mask counts, not strategy results.

## Gate — unchanged

C1: selected lambda>0 beats lambda=0 on stitched OOS Sharpe at 10 bps, paired
stationary bootstrap 10000 resamples, expected block length21, seed0; 95% CI lower
bound >0. C2: same selected strategy beats hand 12-2 momentum at25bps under the same
paired test. C3: C1 and C2 both hold on the fixed 1980–2026 subsample. This panel is
entirely post1980, so C3 is the conjunction on the same OOS dates, not an independent
era stress test; no substitute cutoff. Report each criterion and arm agreement;
arm-dependent conclusions are the finding and will not be reconciled by tuning.

Report all costs, metrics.by_subperiod, turnover, baselines, inference, trial count
and DSR against 16 times evaluated folds per arm (plus the combined search count).
The cells are correlated, so literal breadth overstates independent trials.
Results, errors and failures are journalled whatever they are. No promotion.
A refused run has unavailable gates, not manufactured pass/fail estimates.

## Mandatory reporting block

213 constituents refused /1574 symbol-years; excluded defects CTX, DF, IGT, COG;
substitutions SYMC→GEN, NLOK→GEN, WIN→WINMQ, KRFT→KHC, MMC→MRSH; FCPT has no usable
bars. A2 convention is SIGNED but its treatment remains a proposal for this panel;
no terminal return is imputed for any delisting and no Case2 adverse bound computed.
