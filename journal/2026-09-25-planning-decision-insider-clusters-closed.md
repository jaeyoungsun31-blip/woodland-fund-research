# 2026-09-25 — planning decision: the insider-cluster exploration is closed

Status: **DECIDED** in planning on Jaeyoung's instruction. Written 2026-09-24
21:38 EDT (2026-09-25 UTC). No prior entry is edited.

Closes the Phase 2 insider-cluster exploration under `explore/insiders/`. Every
figure below is taken from the reports linked at the end; none is re-derived.

## Decision

**The exploration is closed without pre-registration. The holdout was never
opened.**

Filings dated 2022-07-01 through 2026-06-30 were sealed by the guard committed
in `f56efee` before any return was computed, and they stay sealed. No return,
spread, alpha or event-window diagnostic was ever computed on a holdout-dated
filing. Because the holdout is untouched it remains usable, but only by a
pre-registration written before it is read. This closure spends none of it.

## Findings on EODHD per-symbol adjusted close

**Source.** The primary return source is each symbol's local EODHD adjusted
close, scaled to the raw entry open. It was validated against Tiingo on a
fixed, seeded (`default_rng(20260923)`) sample of 300 post-2016 executed
clusters, 100 per dollar-volume bucket. On the events Tiingo could price
exactly, EODHD's adjusted-close event return fell within 1 percentage point of
Tiingo's in **96.4%** (84 comparable, below $300k), **100.0%** (87,
$300k–$2M) and **97.8%** (93, above $2M). 36 of the 300 events were not
comparable; 32 symbols returned no Tiingo bars, and all 32 are in EODHD's
delisted list. The Tiingo ticker was not linked to the SEC issuer CIK, so
ticker reuse is a possible source of disagreement that was not filtered.

**Scope of that validation.** It covers post-2016 filings only. The two known
adjusted-close defects, ORM (2014) and MCEP (2012), sit outside it.

**Specification.** Two-insider code-P clusters, 60-session exit, a −30%
terminal haircut for delistings of unknown reason, the full Corwin–Schultz
spread at entry and exit plus 5 bp commission each way. Alpha is the
intercept of net return minus official monthly RF, regressed on FF5 plus
momentum plus short-term reversal, with a Newey–West lag-3 t-statistic.
Percent per month, over 129 active months.

| Dollar-volume bucket | Clusters | Net excess vs IWM | Alpha | HAC t | Residual SD | Reading |
|---|---:|---:|---:|---:|---:|---|
| Above $2M | 4,631 | +0.108% | −0.040% | −0.12 | 3.285% | **null** |
| $300k–$2M | 2,594 | +0.180% | +0.187% | +0.81 | 2.513% | **null** |
| Below $300k | 3,036 | +2.678% | +3.327% | +2.36 | 14.310% | **unresolved** |

**Below $300k is unresolved rather than positive, and was not pursued.** Taken
together, the reasons are sufficient:

- **The mean is not the typical outcome.** The monthly median of
  active-position returns has an alpha of **−0.507%, t −3.12**. The positive
  mean is carried by a minority of positions.
- **Residual SD of 14.310% per month.** At that noise level, the nominal
  48-month detectable alpha (`2σ/√48`, independent residuals, t = 2) is
  **4.131% per month**, which is above the observed +3.327%. The holdout spans
  48 months, so even a perfectly pre-registered test would probably not have
  resolved this estimate. This is a scale calculation, not a power forecast.
- **Known defects sit in this bucket's return path.** ORM's adjusted close
  rises about 100-fold (100.013×) on 2014-12-15 while its raw close is
  unchanged. That single day makes December 2014's below-$300k gross return
  +139.4%. MCEP's raw and adjusted closes both jump about 20× on 2012-12-17.
  Both paths were kept, to avoid an outcome-dependent exclusion after entry.
  The bias-corrections report states that this bucket's return and alpha
  "should **not** be used to infer an edge."
- **The size is implausible.** +3.327% per month is 39.9% a year of
  factor-adjusted alpha annualized simply, and about 48% compounded. Planning's judgement is that this is far larger than
  the published insider-purchase literature supports. That comparison is an
  interpretation and was not measured here.
- **Capacity.** The bucket is defined by an average daily dollar volume below
  $300,000 at filing. Any real edge could only be harvested in very small
  positions.

## Errors disclosed

1. **The offline price rebuild was retired.** It classified BW's 2019-07-24
   1-for-10 reverse split (Tiingo `splitFactor` 0.1) as `suspected_defect`
   rather than `split`. That produced a +749.47 percentage-point disagreement
   with Tiingo on that event, where EODHD's adjusted close was within
   0.02 point. Across the validation sample the rebuild was never more
   accurate than EODHD's adjustment: 95.2% against 96.4% of events within
   1 point below $300k, and tied in the other two buckets. It also misread
   AAPL's 2020-08-31 4-for-1 split as an ordinary −74.152% day. It is
   superseded as a return source.
2. **The middle-bucket alpha of about +0.47% came from the retired rebuild.**
   The figure was +0.468% (t +1.54) under FF5 plus momentum plus reversal on
   the offline rebuild. On EODHD adjusted close the same bucket is **+0.187%
   (t +0.81)**. The larger figure should not be cited.
3. **The winsorization screen could not remove transient spikes.** It clipped
   each event's full 60-session gross return at the pooled 1st/99th
   percentiles, −56.0446% and +111.1698%, with 103 events clipped on each side.
   It did this by changing only the exit-day mark and left every interim
   adjusted-price mark unchanged. A spike that reverses before exit therefore
   still enters the daily position returns that compound into monthly
   portfolio returns. Consistent with that, the below-$300k residual SD barely
   moved, from 14.310% to 14.226%.
4. **Tiingo responses were cached.** Free-tier Tiingo responses were
   persisted to disk, which the repository's own reports record as prohibited
   by the free-tier terms. The raw response cache and request timestamps have
   been deleted. `explore/insiders/cache/tiingo/` was verified empty on
   2026-09-24, and only derived validation tables and the report are kept.
5. **A proposed kill rule was withdrawn.** It included a monthly-median
   criterion, and that criterion would reject a genuine right-skewed edge,
   since an edge carried by a few large winners has a negative median by
   construction. The rule was withdrawn and no kill decision was taken under
   it. This is distinct from the monthly-median *robustness screen*, which was
   run and is reported above. **Provenance:** the proposal and its withdrawal
   are recorded here from planning. No prior entry or report in the
   repository records either.

## Look count

**24 cumulative training-sample bucket-level return configurations**, per
`robustness_screen_report.md`:

- **15** in the original register: cluster at 60 sessions, single-insider at
  60, cluster at 20, survival-corrected, and IWM-hedged survival-corrected,
  each in three buckets.
- **3** from the offline rebuild.
- **6** from the two robustness screens.

Factor-model alternatives, period splits and the 2020 exclusion are prior
looks within these configurations, not additional ones. This is exploratory
look accounting, not a significance adjustment.

## Context

This is the latest in a run of results that did not find a tradeable edge:

- **Cross-sectional momentum:** not established post-1980. It was closed on
  three independent readings, and the termination criterion was signed on
  2026-09-10.
- **An S&P 500 deletion-rebound feasibility probe** under `explore/deletions/`:
  not a tested null. Its own README makes no significance claim. It is
  data-quality-blocked: the +1 to +20 SPY-relative mean changes sign from
  −0.30% to +0.34% when one defective file (CBE) is excluded. It has no
  journal entry and is uncommitted.
- **Insider clusters:** above.

**Planning's reading of the pattern:** with free or low-cost daily data, the
equity effects this project could test were either absent in large caps or not
measurable at acceptable data quality in microcaps.

That is an observation about outcomes, not a causal claim. "Already
arbitraged" is one explanation it is consistent with, but it was not tested.
The signed termination entry makes no claim of causation for the era pattern,
and this entry does not add one.

## Links

- Design and guard:
  - [precommit.md](../explore/insiders/precommit.md), committed in `40358c6`
    (`40358c620255392b8b8795e469cce4e7025d5ce1`)
  - [HOLDOUT.md](../explore/insiders/HOLDOUT.md) and
    [holdout.py](../explore/insiders/holdout.py), committed in `f56efee`
    (`f56efeea9b87913f8fa7cf69c9242ef4b7442907`), before `40358c6` and before
    any return calculation
- Deviations: [deviations.md](../explore/insiders/deviations.md)
- Reports:
  - [first_returns_report.md](../explore/insiders/first_returns_report.md)
  - [bias_corrections_report.md](../explore/insiders/bias_corrections_report.md)
  - [offline_price_rebuild_report.md](../explore/insiders/offline_price_rebuild_report.md)
  - [tiingo_validation_report.md](../explore/insiders/tiingo_validation_report.md)
  - [robustness_screen_report.md](../explore/insiders/robustness_screen_report.md)

**Provenance gap:** when this entry was committed, `deviations.md` and four of
the five reports (bias corrections, offline rebuild, Tiingo validation and
robustness screen) were **untracked** in git. Until they are committed, the
evidence behind these figures exists only in the working tree.
