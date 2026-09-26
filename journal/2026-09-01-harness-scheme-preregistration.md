# 2026-09-01 — Walk-forward scheme pre-registration (Phase 2)

Append-only. Written BEFORE any strategy is run through the harness, which is
the point: the split scheme is a methodological choice, and choosing it after
seeing results is how a walk-forward study becomes a search over walk-forward
studies.

## The scheme (v0)

| Parameter | Value | Why |
|---|---|---|
| train | 5 years | DESIGN.md §7 |
| validate | 1 year | DESIGN.md §7 |
| step | 1 year | validate windows tile with no overlap and no gaps |
| embargo | 210 trading days | 10 months x 21 bars, rounded up |
| costs reported | 0 / 5 / 10 bps | CLAUDE.md rule 5 |
| selection cost | 5 bps | configs are ranked on train at the default cost |
| objective | annualized Sharpe (rf=0) on the train window | v0; rf=0 overstates Sharpe in high-rate regimes and must not leave the repo unqualified |

Realized on the current calendar (1998-12-22 .. 2026-09-01, 6964 bars):
**22 folds**, ~1258 train bars each, exactly 210 embargo bars per fold, and
**21.8 years of contiguous stitched out-of-sample coverage** beginning
2004-10-22. DESIGN.md §7 anticipated ~15 years; we get more because the
universe's history is longer than the doc assumed. Fold 21's validate window
is partial (207 of ~252 bars) because it runs past the end of the data — real
OOS, just short, and it is not padded.

## Embargo rationale

The embargo is counted in TRADING DAYS, not calendar days. A calendar-day
embargo silently shortens itself across holidays and weekends; on this
calendar 210 bars span over 280 calendar days.

Any study must declare `max_lookback_days`, and
`check_embargo_covers_lookback` refuses to run when a signal's backward reach
from the first validate bar would land inside the train window. An understated
declaration is a silent leak, so the declared value belongs in that study's
journal entry. For the Faber-style trend signal (10 monthly closes) the
declared lookback is 210 bars, exactly matching the embargo.

## Trial accounting

`n_trials` for the deflated Sharpe denominator is the count of **distinct
configurations** in the ledger, not the count of ledger rows: re-scoring one
config on 22 splits is one lottery ticket, not 22. Row count is retained
separately as an audit of compute spent. Abandoned and errored configs count
as trials — the researcher still looked.

Choosing the distinct-config count is the less conservative of the two
readings of CLAUDE.md rule 4 ("computed against the full count"), and it is
recorded here rather than left implicit. The reasoning: counting the same
configuration repeatedly inflates N for a reason unrelated to selection bias,
which would make the deflation dishonest in the other direction.

## Caveat inherited from the data layer

Every number this harness produces currently rests on a SINGLE data source —
see `journal/2026-09-01-data-source-stooq-blocked.md`. DESIGN.md §5's
dual-source cross-check is unavailable until a second source is configured.

## Status

The harness is built and unit-tested on synthetic data. **No strategy has been
run through it and no performance claim exists.** The trend signal remains
UNVALIDATED. The promotion gate (§8), the retrain job and the live loop are
Phase 3-4 and are deliberately absent.
