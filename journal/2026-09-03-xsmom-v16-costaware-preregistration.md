# 2026-09-03 — xsmom-v16-costaware: pre-registration (BINDING)

Study id: `xsmom-v16-costaware`. Written and committed BEFORE any model is
fitted and before any result is looked at. Authorized by
`2026-09-03-planning-decision-phase5-amendment.md`, which opens the Phase 5 ML
signal layer under five binding conditions. Nothing here can promote a
strategy; Phase 3 does not exist.

## Hypothesis

Every signal tested so far has been hand-specified and then charged for its
turnover afterwards. The hypothesis is that a signal **fitted under an
objective that already prices its own turnover** finds a cheaper-to-hold
version of the same cross-sectional structure than a hand-specified rule can.

Stated as a falsifiable claim: a temporally-regularized fitted signal
(`lambda > 0`) delivers a higher net-of-cost Sharpe at 10 bps than the
identically-specified unregularized fit (`lambda = 0`), on the same folds,
paired, and that advantage survives post-1980.

The null this is designed to be able to lose to: fitting adds nothing that
hand-specified 12-2 momentum did not already provide, and temporal
regularization is merely a slower signal that v15 has already characterized
more directly.

## Data

Ken French **49 Industry Portfolios, daily, value-weighted section only**,
ingested through the existing `woodland/fama_french.py` path with the same
archive-hash, sentinel, percentage-conversion and provenance discipline
already applied to the 12-industry set. MKT and CASH come from the stored
`fama_french_factors_daily` series, unchanged.

Forty-nine units is the smallest cross-section on which a fitted model is
meaningfully distinguishable from a hand-specified rule; the 12-industry set
is too narrow to fit anything and the ETF universe (9 sectors) is narrower
still. These are frictionless academic constructs, not tradeable securities —
the standing limitation recorded at the 12-industry ingest applies unchanged
and must be restated in the results entry.

Industries with missing sentinels on a date are excluded from that date's
cross-section, and the count of excluded units per date is reported.

## Panel and features — FROZEN

For each unit `u` and date `t`, using data at or before `t` only:

| Feature | Definition |
|---|---|
| `mom_12_2` | cumulative return from t-252 to t-21 |
| `rev_1m` | cumulative return from t-21 to t |
| `rev_1w` | cumulative return from t-5 to t |
| `vol_63` | realized standard deviation of daily returns over the last 63 bars |
| `volvol_63` | standard deviation of the trailing 21-bar realized vol over the last 63 bars |
| `dd_252` | current level divided by trailing 252-bar maximum, minus one |

Six features. **No feature may be added, removed, or redefined after the first
fit.** Each feature is cross-sectionally z-scored within each date, then
winsorized at +/-3, so the model learns a ranking rule and not a level rule.
Rows with any missing feature are dropped from training and from formation.

## Estimator

Ridge regression with an explicit temporal-smoothness penalty. Written out,
the training objective on a train window is

    minimize over b:   || y - X b ||^2  +  alpha * || b ||^2
                       +  lambda * sum_{u,t} ( x_{u,t} b  -  x_{u,t-1} b )^2

where `y` is the forward 21-bar return of unit `u` measured from `t`, and the
third term penalizes the model for producing predictions that move from one
day to the next. Predictions that jump around are exactly what causes
turnover, so this term prices turnover **inside the fit** rather than charging
for it afterwards. It is not circular: it depends only on features, never on
the realized portfolio.

The third term is quadratic in `b`, so the whole objective is quadratic and
has the closed form

    b = ( X'X + alpha I + lambda D'D )^{-1} X' y ,     D = X_t - X_{t-1}

stacked over all units. The solution is computed directly from that
expression, not by a generic optimizer, so it is auditable and exactly
reproducible. `lambda = 0` recovers ordinary ridge and is the study's control.

Overlapping 21-bar targets induce autocorrelation in the residuals. This is
acknowledged, not corrected in the fit — inference is done on realized
portfolio returns with the stationary bootstrap, which is robust to it.

## Grid — DECLARED IN FULL, NOT TO BE WIDENED

    alpha  in {1e-2, 1e-1, 1, 10}
    lambda in {0, 0.5, 2, 8}

Sixteen cells. Every cell is fitted on every fold and every cell is written to
the trials ledger, including the ones that lose. Selection within a fold uses
the training window only. Widening this grid requires a new dated amendment
before the rerun.

## Walk-forward scheme

The frozen scheme, unchanged: 5-year train, 1-year validate, 1-year step,
**252-trading-day embargo** (the momentum embargo used from v10 onward, which
exceeds the 252-bar feature lookback by construction and must be asserted, not
assumed). Fold and bar counts are recorded as realized and compared against
`woodland/study.py`'s frozen expectations; a mismatch halts the study.

## Portfolio construction

Long-only, unlevered, equal-weighted across the top 30% of units by predicted
value. **Monthly formation**, matching v15's monthly point so the two are
comparable. Weights drift between formations; turnover is charged on the
actual traded difference including seam turnover across fold boundaries.
Costs are evaluated at 0, 5, 10, 25 and 50 bps one-way. Ledger cost is 5 bps.

## Controls — all four are required

1. **`lambda = 0` twin** — the same estimator, same grid over alpha, same
   folds, without the temporal penalty. This is the ablation that isolates the
   study's actual hypothesis.
2. **Hand-specified 12-2 momentum** on the same 49 units, same formation
   frequency, no fitting. This is condition 3 of the authorizing amendment: a
   fitted model that does not beat the rule it replaces is a negative result.
3. **EW49** — equal weight across all units.
4. **MKT** and **60/40**, as in every prior study.

## Pre-registered pass criteria

A criterion is met only if stated exactly as below. All three are primary.

**C1 — fitting under a turnover-aware objective adds something.** The
best-in-train `lambda > 0` configuration beats the `lambda = 0` twin on
stitched OOS returns at 10 bps, paired, stationary bootstrap (10,000
resamples, expected block 21, seed 0), 95% CI excluding zero.

**C2 — it survives a realistic cost.** The same configuration beats **control
2, hand-specified 12-2 momentum**, at 25 bps, paired, 95% CI excluding zero.
Beating EW49 is reported but is not sufficient; the rule is the bar.

**C3 — it survives the era that has killed everything else.** C1 and C2 both
hold on the 1980–2026 subsample alone, using the same fixed era split as v15.

Failing C3 while passing C1 and C2 is recorded as **era-unstable**, and is a
negative result for the project's purposes. Every study so far that passed on
the full window and failed post-1980 was passing on pre-1980 data.

## Deflated Sharpe

Computed against the full evaluated-configuration count, sixteen cells times
folds, not against a remembered subset. The effective-breadth caveat is
restated: the sixteen cells are highly dependent, so literal breadth
overstates independent trials and DSR is a weak hurdle here, as it has been
throughout.

## Precondition of execution

The no-lookahead perturbation test must pass **before** any result is read,
and it must perturb the **panel**: altering all returns after a cutoff must
leave every feature value, every fitted coefficient, and every formation
weight at or before that cutoff bit-identical. Feature construction is where
leakage enters a fitted model. A study that has not passed this test has not
been run.

## Prediction on the record, so it can be wrong

`[Speculative]` C1 passes with a small margin — temporal regularization does
reduce turnover materially and costs little gross. `[Likely]` C2 is the one
that fails: the fitted model beats EW49 but not hand-specified 12-2 momentum,
because with six features and 49 units there is very little for a linear model
to find that 12-2 does not already express. `[Likely]` C3 fails regardless.

If that is how it lands, the finding is that the search method was never the
constraint, and the project's remaining honest move is the write-up.
