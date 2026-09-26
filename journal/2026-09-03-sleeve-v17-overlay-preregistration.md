# 2026-09-03 — sleeve-v17-overlay: pre-registration (BINDING)

Study id: `sleeve-v17-overlay`. Written and committed BEFORE any run and
before any result is looked at. This study uses only data already ingested;
no new source is added. Nothing here can promote a strategy; Phase 3 does not
exist and the §8 gate of `2026-09-01-gate-preregistration.md` is untouched.

## Why this study exists — the question nobody has asked

Across every study this project has run — v2, v3, v4, v6 through v13, and
v15 — the balanced 60/40 control has beaten the strategy on Sharpe, and in
v15 it also beat every configuration on CVaR95, CVaR99, maximum drawdown and
adjusted Sharpe simultaneously. That is fifteen studies of consistent evidence
pointing at one conclusion, and the project has consistently drawn the wrong
inference from it.

The question asked fifteen times was **"does momentum beat 60/40?"** The
answer is settled: no, and the confidence intervals are not close. The
question never asked is **"does a bounded momentum sleeve improve 60/40?"**
Those are different hypotheses with different nulls. A signal can be a poor
standalone portfolio and a good diversifier of a different portfolio; that is
the ordinary case, not an exotic one, and it is what the correlation structure
in v15 (0.950–0.967 against MKT) is consistent with.

The framing error is worth recording plainly: fifteen studies asked whether
the candidate could *replace* the best thing in the repo, when the natural
use of a weak-but-real signal is to be *added* to it in small size.

## Construction

    portfolio(s) = (1 - s) * [60/40 MKT/CASH]  +  s * [momentum sleeve]

rebalanced back to the mix at each formation date, so `s` is a maintained
allocation and not a drifting one. The re-mix trade is charged.

**Momentum sleeve** is the v15 **monthly** stale-cohort construction exactly
as specified in `2026-09-03-planning-decision-xsmom-v15-stale-cohort.md` and
implemented in `scripts/run_xsmom_holding.py`. It is reused unmodified. Its
standing limitation carries with it and must be restated in the results entry:
**the sleeve's gross path and its internal turnover are model-implied, not
observed**, and it assumes a stale sub-cohort's return is exchangeable with
the contemporaneous return of the decile its latent rank migrated into.

**Baseline** is `60_40_MKT_CASH` as already defined in that runner
(`{MKT: 0.6, CASH: 0.4}`), on the identical window and folds.

Sleeve weights: `s in {0.05, 0.10, 0.20, 0.30}`. Long-only, unlevered.
Costs 0, 5, 10, 25, 50 bps one-way. Ledger cost 5 bps. Frozen walk-forward
scheme, 252-day embargo, as in v15.

## Two comparisons, deliberately separated

**A — no free parameter.** Fixed `s = 0.10`, chosen here, before any run,
never re-selected. This is the honest test: nothing is fitted, so nothing is
selected, and deflation is irrelevant to it. **A is the study's primary
result.**

**B — selected.** Best-in-train `s` from the four, selected on training
windows only. Reported with the full four-cell ledger and DSR. B is secondary
and is expected to look better than A for reasons that are not evidence.

If A fails and B passes, the study has failed. Say so in those words.

## Pre-registered pass criteria — all three primary, evaluated on A

**C1 — it improves risk-adjusted return.** `s = 0.10` beats the 60/40
baseline on stitched OOS Sharpe at **10 bps**, paired, stationary bootstrap
(10,000 resamples, expected block 21, seed 0), 95% CI excluding zero.

**C2 — it does not pay for that with the tail.** At 10 bps, the overlay's
maximum drawdown is at most 1.25x the baseline's, **and** its CVaR95 and
CVaR99 are each no worse than 1.10x the baseline's. The tail clause is not
borrowed decoration: 60/40's tail dominance is the single most repeated
finding in this repo, and a Sharpe improvement bought by giving that up is
not an improvement.

**C3 — it survives post-1980.** C1 holds on the 1980–2026 subsample alone,
using the same fixed era split as v15.

Reported alongside but explicitly **not** pass criteria: CAGR (an overlay that
raises CAGR by raising volatility is not the hypothesis), and any comparison
against MKT or EW10 (they are not the incumbent; 60/40 is).

## Diagnostic required regardless of outcome

Report the **correlation of the sleeve's returns to the baseline's** and the
**diversification ratio / effective bets** of the two-component mix at each
`s`, using `woodland/diversification.py`. If the overlay helps, the mechanism
should be visible there; if Sharpe improves while effective bets do not, the
improvement is coming from something other than diversification and the
results entry must say what.

Also report the response across all four `s`. A clean monotone or
single-peaked response is consistent with a real effect. A ragged response
across four adjacent values is noise, and must be called noise even if one
cell passes.

## Prediction on the record, so it can be wrong

`[Likely]` C1 passes at `s = 0.10` with a small positive delta — the sleeve
has a positive gross edge and imperfect correlation to a 60/40 whose equity
leg is the same market, so a small allocation should help slightly.
`[Speculative]` C2 passes; the sleeve's drawdowns are equity-like and 60/40's
are not, but at 10% weight the dilution should dominate. `[Speculative]` C3 is
the coin flip, and it is the one that decides whether this line continues.

If C1 fails at `s = 0.10`, then momentum does not help this project even as a
diversifier, and the correct conclusion — after fifteen studies and this one —
is that the project's finding is a negative one, and the deliverable is the
write-up.
