# Phase 2 first-return precommit — locked before any return calculation

The sealed holdout is filings dated 2022-07-01 through 2026-06-30. The only
permitted return sample is filings dated 2012-01-01 through 2022-06-30. The
return runner must call `require_training_events` before opening any price or
factor file. All holdout-dated input rows are a hard error, never silently
filtered by the return runner.

## Primary test

- **Events.** SEC non-derivative transaction code `P`, acquired side `A`, on
  non-amended Forms 4/5 by an officer or director. A purchase qualifies only
  if its reported transaction price is finite and lies within that
  transaction day's EODHD *raw* [low, high] range, inclusive. At least one
  such purchase makes the issuer-CIK / insider-CIK / filing-date event
  eligible. Use only events whose identity mapping and Phase 2 price-quality
  screen passed. Code `P` also covers private purchases, so this is a code-P
  proxy, not verified open-market trading.
- **Cluster start.** In issuer-CIK filing-date order, the first filing date on
  which a second distinct insider-CIK has a qualifying purchase within the
  trailing 30 calendar days, including the current date. Count one cluster
  on that issuer/date. Subsequent qualifying filings of that issuer cannot
  start another cluster for 90 calendar days, measured from the last start.
- **Entry and exit.** Buy at the raw open of the first EODHD trading day
  strictly after the cluster filing date. Sell at the raw close exactly 60
  EODHD trading sessions after the entry day (entry day is session 0). No
  fallback to a later entry bar. Mark the holding period using per-symbol
  adjusted closes, scaling the entry raw open by that day's
  adjusted-close/raw-close ratio; refuse invalid or missing bars. This is
  independent of the contaminated constituent-panel adjusted prices.
- **Costs.** Use the Corwin–Schultz high–low estimator over the 20 EODHD
  sessions strictly before entry: for each of 19 adjacent pairs, set
  β = ln(H₁/L₁)² + ln(H₂/L₂)²,
  γ = ln(max(H₁,H₂)/min(L₁,L₂))²,
  α = (√(2β) − √β)/(3 − 2√2) − √(γ/(3 − 2√2)), and
  S = 2(exp(max(0,α)) − 1)/(1 + exp(max(0,α))).
  Take the median S across valid pairs. Require all 20 valid sessions and
  0 ≤ S < 1. Charge **the full estimated spread S at entry and again at
  exit**, plus 5 basis points commission each way. The reported average
  round-trip spread charge is 2S; the additional commission is 10 bp.
  This intentionally follows the requested full-spread convention, rather
  than a half-spread assumption. Formula reference:
  https://users.nber.org/~confer/2009/mms09/Corwin_Schultz.pdf
- **Portfolio.** Form one equal-weight, calendar-time portfolio for each
  dollar-volume bucket. A position becomes active at its entry open and ends
  at its exit close. On the first trading day of each calendar month, set
  equal weights across active positions. A new entrant between scheduled
  rebalances receives the same dollar allocation as an existing position,
  financed pro rata from current holdings and cash; an exit becomes cash
  until the next scheduled rebalance or entry. Cash earns the pinned CASH
  index return. Do not use future signals when determining allocations.
  Scheduled reweighting is accounting-only; the specified spread/commission
  charges apply to signal entry and exit, so net returns remain optimistic
  about any extra rebalancing trades. Compound daily portfolio returns to
  calendar-month returns. Include only months with an active position on at
  least one trading day; report their count.
- **Evaluation.** Compare each gross and net monthly portfolio return to
  IWM's same-month adjusted-close return and report the mean difference.
  Regress net portfolio monthly return in excess of CASH on an intercept
  and pinned monthly MKT−CASH. Report the intercept (monthly alpha) and its
  t-statistic with Newey–West/HAC standard errors, lag 3. The pinned
  `data/fama_french_factors_daily.parquet` SHA256 is
  `ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7`.
  It stores only MKT and CASH index levels, **not SMB or HML**. Accordingly
  this is a one-factor market alpha using the pinned Fama–French-derived
  series, not an FF3 alpha; an FF3 estimate is unavailable from that file.
- **Buckets.** Use the Phase 2 dollar-volume proxy fixed at filing: below
  $300,000 per day (primary); $300,000–$2 million and above $2 million
  (secondary). These are not market-cap buckets. Report cluster count,
  active months, gross and net mean monthly excess over IWM, alpha/t-stat,
  worst net month, and mean 2S for each bucket.

## Sensitivities and bias check

Sensitivity A replaces clusters with every qualifying issuer-insider-filing
event, while preserving the 90-day rule **only in the primary cluster
definition**, not in the single-insider sensitivity. Sensitivity B keeps
clusters but exits 20 trading sessions after entry. All other filters,
costs, portfolio rules, and reporting conventions remain fixed.

For each filing year, report the share of potential cluster starts lost to
mapping failure or the Phase 2 quality screen. Compare 60-session pre-filing
adjusted returns for lost versus kept starts only where a verified
per-symbol mapping and full pre-window price history exist, and report the
available counts; missing mappings cannot be assigned a return. The Phase 2
quality screen itself requires 120 post-filing sessions, which can select on
future survival. This is an exploratory bias diagnostic, not a cure.
