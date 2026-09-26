# CLAUDE.md — The Woodland Fund

Systematic ETF strategy research pipeline with a walk-forward retrain loop.
`DESIGN.md` is the contract — read it before non-trivial work. Current
status and phase map: `README.md`. Decision history: `journal/` (append-only).

## How this file works — two-chat protocol

This project is run from two places, and this file is the transfer channel:

* **Planning chat** — Jaeyoung's Cowork "Personal Finances" session. Owns
  DESIGN.md, resolves open decisions, and rewrites the HANDOFF section below
  before each coding session.
* **Coding chat** — Claude Code in this repo. Executes the current handoff,
  keeps README.md's phase table and the journal current, runs git. When a
  decision belongs to planning (design changes, methodology tradeoffs,
  anything touching pre-registered rules), do NOT decide unilaterally —
  append it under QUESTIONS FOR PLANNING and work on what's unblocked.

Only planning edits HANDOFF; only coding edits QUESTIONS FOR PLANNING
(planning clears entries as it answers them, with a journal entry when the
answer is a decision).

## Implemented system and capabilities — through 2026-09-01c

This is the durable engineering handoff. Check here before building: if a
capability is listed as implemented, inspect and extend it rather than creating
a parallel implementation. Study conclusions live in the linked append-only
journal entries; the current HANDOFF below owns only the next work queue.

### Data ingestion and integrity

`woodland/data.py` and `scripts/ingest.py` provide the ETF data pipeline:

* Yahoo is the primary source. Each ticker parquet contains unadjusted OHLCV
  plus `adj_close`; research and backtests use the dividend- and split-adjusted
  series only.
* Tiingo is the independent keyed cross-check. Its token is read from the
  environment or ignored `.env` and travels in the authorization header, never
  in a URL. Provider comparisons operate on aligned adjusted daily returns,
  not differently rebased price levels.
* The planning-owned two-tier policy is implemented: differences over 50 bps
  are counted and printed; any difference over 2% produces `INVESTIGATE`.
  Thresholds are in `config/universe.yaml` and must not be tuned after seeing
  data.
* The planning-approved missing 2026-08-28 Yahoo bars are filled only when the
  date exists at Tiingo. The Tiingo adjusted level is rebased to the nearby
  Yahoo level, and every replacement records date, source, reason, and scale in
  `data/_provenance.json`.
* Adjustment-factor checks, cross-sectional calendar-hole detection, missing
  bar counts, nonpositive/jump/history checks, and per-ticker terminal-date
  freshness versus the store-wide modal last bar are implemented. A failed
  mid-ingest fetch therefore leaves the old parquet intact but is reported as
  stale. Freshness is report-only and does not alter existing verdict logic.
* The last live dual-source ingest fetched all 20 tickers and added 13 approved
  bars. It was not clean: 63 historical observations across 11 tickers exceed
  the 2% hard threshold, so the source-verification caveat remains. Do not
  describe the store as single-source; describe it as dual-source checked but
  not clean under the codified rule. Evidence:
  `journal/2026-09-01-crosscheck-policy-reingest.md`.

`woodland/fama_french.py` and `scripts/ingest_fama_french.py` provide the
deep-history academic pipeline:

* Download the official Ken French 12-industry daily ZIP; select only the
  value-weighted daily section; parse missing sentinels; convert percentages
  to decimal returns; and compound base-100 synthetic index levels.
* Persist archive hash, source URL, construction, dates, dimensions, and the
  explicit limitation that these are frictionless academic constructs—not
  tradeable securities and not net of implementation costs.
* The realized ignored dataset has 26,274 complete rows, 12 industries, and
  dates 1926-07-01 through 2026-06-30. Under the frozen split scheme it can
  produce 95 folds. Evidence:
  `journal/2026-09-01-fama-french-12-industry-ingest.md`.

All parquet/provenance artifacts are rebuildable under ignored `data/`. Never
commit them, and never commit `.env`.

### Backtest, metrics, and reports

`woodland/backtest.py` implements a transparent long-only, unlevered daily
engine. Sparse target rows are decisions at close t and execute at close t+1;
all-NaN rows mean hold and let weights drift. Adjusted close-to-close returns
accrue before trading, cash earns zero, and one-way costs are charged on
`sum(abs(new_weight - drifted_weight))`. The returned `BacktestResult` contains
net daily returns, equity, post-trade holdings, turnover, and cost assumptions.
Buy-and-hold, fixed-mix targets, and calendar-rebalanced fixed mix are already
available for SPY and 60/40 baselines.

`woodland/metrics.py` supplies CAGR, annualized volatility, Sharpe with an
explicit risk-free assumption, maximum drawdown, drawdown duration, monthly
hit rate, annualized turnover, summary tables, named-result comparisons, and
the fixed sub-period breakdown used by study reports. Empty, single-bar, and
all-negative edge cases are tested.

`woodland/tearsheet.py` plus `scripts/tear_sheet.py` render a completed
`BacktestResult` with Matplotlib only: equity curve, drawdown, rolling 252-bar
Sharpe, and holdings over time. Output belongs under ignored `reports/`.

### Walk-forward research harness

The Phase-2 harness is implemented; it produces evidence but cannot promote a
strategy:

* `woodland/harness/splits.py`: frozen 5-year train / 1-year validate / 1-year
  step with a 210-trading-day embargo; it rejects a declared lookback longer
  than the embargo.
* `woodland/harness/ledger.py`: append-only SQLite trials ledger. Every scored,
  failed, abandoned, winning, and losing configuration must be recorded.
* `woodland/harness/walkforward.py`: scores configurations on each train
  window only, selects without validation leakage, stitches target weights
  across validation folds so seam turnover is charged, and reports one OOS
  curve at 0/5/10 bps. `with_baselines` aligns SPY and 60/40 to the identical
  OOS window.
* `woodland/harness/deflated.py`: probabilistic and deflated Sharpe using the
  distinct-config trial count. Reports include distinct-config count,
  min/max/spread/standard deviation, and an effective-breadth warning because
  near-collinear trials make DSR a weak hurdle.

The ETF history realizes 22 folds and a contiguous stitched OOS window from
2004-10-22 through 2026-09-01. The ledger at `journal/trials.db` is historical
evidence: never delete, rewrite, or reuse an old study id for a changed study.

### Implemented causal signals and completed studies

`woodland/signals/trend.py` implements monthly time-series trend. Each risk
asset is above/below its trailing monthly SMA; active sleeves are equally
weighted and inactive sleeves go to IEF. `ensemble_targets` averages complete
target vectors from fixed lookbacks and refuses to form a partial warm-up
ensemble. `woodland/signals/voltarget.py` scales a complete target vector from
current trailing realized portfolio volatility, caps scale at 1.0, leaves the
remainder in zero-return cash, and never conditions on named crash patterns.
All new signal behavior has future-price perturbation tests proving decisions
through t do not change when prices after t are shocked.

Completed, preregistered harness studies—do not rerun under the same id:

| Study | Implemented capability | Evidence |
|---|---|---|
| `trend-v1` | Per-fold selection across 4–10 month SMA lookbacks | `journal/2026-09-01-trend-study-v1-results.md` |
| `trend-v2-ensemble` | One fixed equal-weight ensemble of all seven lookback portfolios; no per-fold parameter selection | `journal/2026-09-01-trend-v2-ensemble-results.md` |
| `trend-v3-voltarget` | v2 ensemble with fixed 63-bar realized-vol estimate and 10% annual target, reported beside an identically vol-targeted 60/40 | `journal/2026-09-01-trend-v3-voltarget-results.md` |

Each report includes 0/5/10 bps, literal SPY and 60/40 over the same OOS
window, sub-periods, turnover, trial counts, and effective breadth. The HANDOFF
below summarizes the accepted interpretation; do not promote any of them.

### Verification and available commands

Development configuration for Ruff and mypy is in `pyproject.toml`. As of
commit `3d56f05`, the verified baseline is 94 passing tests, Ruff clean, and
mypy clean across 22 source files. Use the project virtualenv explicitly when
the shell has not activated it:

    .venv/bin/python -m pytest
    .venv/bin/ruff check .
    .venv/bin/mypy woodland scripts
    .venv/bin/python scripts/ingest.py
    .venv/bin/python scripts/ingest.py --report-only
    .venv/bin/python scripts/ingest_fama_french.py
    .venv/bin/python scripts/run_baselines.py
    .venv/bin/python scripts/run_trend_study.py
    .venv/bin/python scripts/run_trend_ensemble.py
    .venv/bin/python scripts/run_trend_voltarget.py

Before and after every commit, `python -m pytest` must pass. For executable
changes, also run Ruff and mypy. Tests cover engine known answers, ingest
failure/malformed paths, stale parquet detection, source security, adjustment
and calendar checks, metric edge cases, ledger accounting, embargo/splits,
walk-forward stitching, tear-sheet output, academic-data parsing, and causal
no-lookahead perturbations.

### Statistical inference (added 2026-09-01c)

`woodland/stats.py` is the inference layer; use it rather than adding a second
one. It provides the Politis-Romano stationary block bootstrap (geometric
block starts, expected length fixed at 21 bars, batched so a 10,000-resample
run on 25,000 bars stays in memory), a paired Sharpe-difference test returning
CI and p-value, the Ledoit-Wolf HAC delta-method counterpart with an Andrews
plug-in bandwidth, a single-series Sharpe CI, and `iid_sharpe_test`, which
exists only as the wrong answer to measure the others against.

Rows are resampled JOINTLY. Strategies sharing risk are highly correlated, so
the DIFFERENCE is far better determined than either level — this is what made
the v5 inverse-vol null informative (correlation 0.9957, SE 0.020).

Measured size at nominal 5% on autocorrelated data under a true null: naive
iid 20.0%, block bootstrap 4.5%, HAC 5.0%. But note the naive test errs in
BOTH directions — it under-rejected on the real v2/v3 comparisons because it
also ignores cross-correlation. Evidence:
`journal/2026-09-01-inference-existing-studies.md`.

Key numbers for planning any future comparison: SE of a Sharpe difference is
~0.125 on the 21.8y ETF window and ~0.058 on the 97.5y deep-history window.
Detecting a 0.10 difference at 80% power needs ~269 years.

### Risk weighting and deep-history data (added 2026-09-01c)

`woodland/signals/riskweight.py` provides inverse-vol weights, Ledoit-Wolf
(2004) shrinkage toward a scaled identity, an exact simplex projection, and
long-only minimum variance by projected gradient — all numpy, no scipy.
`trend.trend_targets` and `ensemble_targets` take `weighting` and `vol_window`
arguments; the default `"equal"` path is byte-identical to v1-v4.

`woodland/fama_french.py` additionally ingests the daily research factors,
giving `MKT` (Mkt-RF + RF, value-weighted market total return) and `CASH`
(the T-bill leg). This is what unblocked v4.

### Completed studies added this session

| Study | Finding | Evidence |
|---|---|---|
| `trend-v4-deephistory-*` | Lookback instability is intrinsic, not small-sample (46.8% switch rate on 95 folds vs 47.6% on 22). Ensemble beats selection (+0.063, p=0.023) and beats MKT (+0.152, p=0.014), ties the balanced baseline. | `journal/2026-09-01-trend-v4-deephistory-results.md` |
| `trend-v5-riskweight-*` | Equal weighting survives: inverse-vol −0.022 (CI rules out any gain above +0.015), min-variance −0.076 with higher turnover. | `journal/2026-09-01-trend-v5-riskweight-results.md` |

The through-line across v4 and v5: on this signal the estimation-light choice
keeps winning. Selecting a lookback lost to averaging them; weighting by
estimated risk lost to not estimating it.

### Explicitly not implemented yet

Do not assume the following exist: the automated §8 promotion gate; scheduled
retraining; incumbent comparison; live/paper brokerage execution; drift
monitoring; or any ML/RL layer. The current HANDOFF decides which of these may
be built next. Learning from the strategy's own trade outcomes and
conditioning on historical crash shapes remain planning-rejected directions.

## HANDOFF — 2026-09-03d (from planning) — SUPERSEDES 2026-09-03c

**Stop work on the write-up. A measurement defect has been found in the
inference path and it may have caused a false negative in v17.** Read
`journal/2026-09-03-planning-finding-rf-zero-sharpe-bias.md` in full before
anything else. The termination decision is suspended pending this correction.

Summary: every pre-registered pass/fail in v15 and v17 was evaluated on
Sharpe with `rf = 0`, over a 1932-2026 window whose mean annualized real
risk-free rate is 3.0761%. Because the incumbent holds 40% cash and the
challengers hold none, that convention hands 60/40 roughly **+0.114 Sharpe**
mechanically — about **21x** v17's measured primary effect of -0.0054.
`paired_inference` in `scripts/run_sleeve_overlay.py` computes Sharpes on raw
return series with no risk-free subtraction, even though
`woodland/metrics.py` already accepts `rf_daily`.

### 1. Fix the inference path

Make the paired-inference routines take and use the aligned daily risk-free
series. Add a regression test asserting that a paired comparison between a
cash-heavy and a fully-invested portfolio returns **different** answers under
the two conventions — this defect must not be able to recur silently.

### 2. Recompute — this is a recomputation, NOT a new study

From stored return series, with the pre-registered bootstrap unchanged
(10,000 resamples, expected block 21, seed 0), on excess returns over the
aligned real risk-free series:

* v17 C1 and C3, at all five registered costs, all four fixed weights and B;
* v15's paired comparisons versus 60/40 and versus MKT;
* both era subsamples for each.

**Add no configuration, no weight, no cost level, no data.** If the corrected
inference is ambiguous, report it as ambiguous. Do not search for a framing
that resolves it.

### 3. Report both conventions, side by side, always

The rf=0 numbers are the pre-registered ones and stay on the record exactly as
journalled. The excess-return numbers go **beside** them, never in place of
them. This is a dated correction to a metric, not a revision of history. A new
append-only results entry; do not edit the v15 or v17 entries.

### 4. Then, and only then, the write-up

The 2026-09-03c handoff still stands for the report itself and its items are
unchanged — correct the superseded "cost structure is the binding constraint"
section, add the turnover budget as a standalone result with its log-log
figure, fold in v17, retitle, commit the stray journal entries. But its
conclusion now depends on what the recomputation says, so do the
recomputation first and write the report around the corrected result.

Three things the correction does **not** touch, and the report must still say
so: 60/40's tail advantage (CVaR95, CVaR99, drawdown, underwater duration) is
convention-independent and stands; the identification gap stands — every
sleeve path and turnover figure remains model-implied; and the turnover
budget `K ~ 232` stands, since it derives from crossover costs and turnover,
neither of which involves the risk-free convention.

**Do not run a new study.** If the corrected inference reopens a question,
that is planning''s decision to make, not this session''s.

## QUESTIONS FOR PLANNING

### Q5 (2026-09-01c) — statistical promotion gate: PROPOSAL, not adopted

Requested by HANDOFF step 3. §8 is pre-registered, so this is a draft for
planning to accept, amend or reject; nothing here is in force. Evidence:
`journal/2026-09-01-inference-existing-studies.md`.

**The problem with §8 clause (a) as written.** "Net-of-cost Sharpe exceeds the
incumbent's by >= 0.10" is a point-estimate comparison. Measured SE of a
Sharpe difference on our 21.8y OOS window is ~0.125, so 0.10 is well inside
one standard error. Clause (a) currently fires on noise about as often as on
signal.

**The problem with the obvious fix.** Replacing it with "p < 0.05 on the
Sharpe difference" would promote nothing, ever. Power at alpha=0.05:

| difference | years of OOS needed (80% power) |
|---|---:|
| 0.10 | 269 |
| 0.20 | 67 |
| 0.30 | 30 |
| 0.50 | 11 |

Smallest difference detectable today at 80% power: **0.351 Sharpe**. Demanding
significance at the current threshold is a permanent moratorium disguised as
rigour. Demanding p<0.01, as the handoff anticipated, is worse.

**Proposal — a two-part gate that separates "is it better?" from "is it worse?"**

Replace clause (a) with BOTH of:

  a1. **Point estimate, unchanged in spirit:** challenger Sharpe exceeds the
      incumbent's by >= 0.10, net of costs, at 10 bps.
  a2. **Non-inferiority, not superiority:** the 95% CI for
      SR(challenger) - SR(incumbent), by stationary block bootstrap
      (10,000 resamples, block length 21, paired), must have a lower bound
      above **-0.10**.

The asymmetry is the point. We cannot prove a challenger is better — that
needs centuries. We CAN refuse to promote one the data says might be
materially worse, which is a question this sample can answer: a 0.351
difference is detectable, so a challenger that is truly much worse gets
caught. a2 turns the statistics into a veto rather than a hurdle, which is the
only role it has the power to play.

Inertia is preserved and arguably strengthened: a1 keeps the existing bar, a2
adds a way to fail that did not exist before. No challenger that would have
been promoted under today's §8 becomes easier to promote.

**Recommended significance level: 5%, one-sided in effect** (a 95% two-sided
CI whose lower bound clears -0.10). Not 1%: with SE 0.125 a 99% interval is
+-0.32 wide, so a2 would reject nearly every challenger including genuinely
good ones, and the gate would again be a moratorium.

**Honest costs of this proposal.**
* It does not fix the real problem, which is sample size. It makes the gate
  harder to fool, not able to detect small edges.
* a2 can veto a genuinely superior challenger whose CI happens to be wide
  (low power cuts both ways).
* The bootstrap needs the incumbent's and challenger's return series on an
  identical window; the harness produces this today, but the Phase 3 retrain
  job must persist both series, which it does not yet do.
* Sharpe differences are not the only thing worth testing; drawdown and
  turnover clauses (b) and (d) stay point estimates under this proposal.

**Alternative if planning wants a single clause:** drop a1 and require the CI
lower bound above **0.0** — a genuine superiority test at the boundary. Higher
bar, still not p<0.05 significance, promotes more rarely. I do not recommend
it: it inherits a1's arbitrariness without gaining power.

Also for planning, on reporting standards: every Sharpe comparison in past
journal entries is a point estimate. I have not retro-edited them (rule 3);
the inference entry above supplies the error bars for v2 and v3. Should future
study entries be required to carry CIs on every headline comparison? I
recommend yes.

### Q6 (2026-09-01c) — declared deviation from binding rule 5 in trend-v4

Rule 5 requires every result beside "SPY buy&hold and 60/40". Over
1926-2026 **neither exists** — SPY begins 1993, IEF 2002. This blocked v4 last
session. I resolved it from the same academic source rather than leaving the
study owed a second time, and I am flagging rather than assuming the call:

* **Risk-off leg → FF `RF` (one-month T-bill).** I consider this *not* a
  deviation: DESIGN.md §9 specifies "T-bills/IEF", so on this window T-bills
  are the primary reading. v1/v2 used IEF only because T-bills were not in the
  ETF store.
* **`MKT` (CRSP value-weighted total return) in place of SPY.** A faithful
  equity baseline; labelled MKT throughout, never called SPY.
* **`60% MKT / 40% CASH` in place of 60/40 — this one IS a deviation.**
  T-bills are not ten-year Treasuries. It understates both the return and the
  drawdown of a real bond sleeve, particularly through the 1980s rate decline,
  and it is the weaker comparator as a result.

The v4 conclusion that depends on this is "the ensemble ties the balanced
baseline" (Δ = +0.020, p = 0.747). A real 60/40 with duration would likely
have scored *higher* through 1980-2026, so the deviation if anything flatters
the strategy — the tie is not an artefact favouring us, but planning should
confirm the comparator is acceptable.

Options: (a) accept as declared; (b) source a long US Treasury total-return
series (Ibbotson/SBBI, or FF has none) and rebuild the baseline; (c) restrict
v4 reporting to the post-1962 CRSP-bond era. I recommend (a) with the caveat
carried, and (b) only if planning wants v4 treated as more than signal
evidence.

### Q7 (2026-09-01c) — v5 run as two studies rather than one two-config grid

The handoff said "two configs, both in the ledger". Both are in the ledger,
but as two single-config studies rather than one grid, because a grid makes
the harness select between them per fold — and v4 had just measured per-fold
selection as actively harmful (+0.063 Sharpe to the ensemble, p = 0.023) and
never stabilizing. Running the two schemes head-to-head under a mechanism we
had just shown to be harmful would have confounded the question. Declared in
the v5 pre-registration; trivially re-runnable as a grid if planning prefers.

### Q8 (2026-09-02) — should journalled headline Sharpes be restated on the
### cash-realistic basis?

`journal/2026-09-02-cash-realism.md` fixes a correctness inconsistency: the
ETF window scored cash at zero while the deep-history window earned the
T-bill rate. Engine now supports both; default stays zero so the journalled
record remains reproducible, and it was verified to reproduce exactly.

No conclusion changed. But two reporting facts are now on the table:

* Every published headline Sharpe is 0.09-0.20 too high as a risk-adjusted
  number, because rf=0 ignores a rate that compounded to 47.3% over the OOS
  window.
* v3's figure is additionally understated by its own construction (it held
  22% cash earning nothing): 0.709 -> 0.739.

Options: (a) leave the record as-is, with this entry as the correction — my
default, since rule 3 forbids retro-editing; (b) require future entries to
report `sharpe_rf` beside `sharpe_rf0`, which `metrics.summarize` now emits
when given a rate — I recommend this; (c) additionally publish a one-off
restatement table of prior studies on the new basis, as a NEW entry.

I did (a) plus the plumbing for (b). Say the word for (c).

Related, already actionable without a decision: new ETF-window studies should
pass `risk_free`. The zero default exists for reproducing the record, not for
new work.

### Q9 (2026-09-02) — trend-v8 deep prior for gold-containing ETF blends

The v8 instruction requires the ETF prior to be the deep-history posterior
for the **same comparison**, fixed before any ETF result is computed. That is
well-defined for the two-way `trend + more-defensive` blend: both sleeves and
the 60% MKT / 40% CASH base exist over deep history.

It is not defined for `trend + gold`, `gold + more-defensive`, or the three-way
blend. V7 explicitly recorded that no vetted deep-history gold series exists,
omitted the gold control, and prohibited a substitute. Replacing gold with the
static 12-industry sleeve would not be the same comparison (and that sleeve was
not a diversifier in v7); dropping gold and renormalizing would silently turn
three different ETF mixes into the same two-way deep mix.

Planning needs to specify one of the following before v8 can be pre-registered:
whether the deep `trend + more-defensive` posterior is an intentionally shared
**structural prior** for every ETF mix despite not being the same comparison;
whether deep-informed sensitivity is reported only for the exactly matched
two-way blend and marked unavailable for gold-containing blends; or another
explicit mapping. I recommend the second because it preserves the meaning of
"same comparison" and exposes the unavailable evidence rather than laundering
an analogue into a replication. The skeptical and neutral prior sensitivities
remain available for every ETF mix either way.

### Q10 (2026-09-02) — Bayesian promotion gate: PROPOSAL, not adopted

Requested after `trend-v8-blend`. This supersedes the proposed answer in Q5
if planning accepts it; it does not amend DESIGN.md, the signed gate, or any
past result. Evidence and the fixed decision model are recorded in
`journal/2026-09-02-trend-v8-blend-results.md`.

**Proposed replacement for §8 clauses (a) and (c).** On the single challenger
fixed before a retrain cycle touches its final stitched OOS comparison, form
`delta = SR(challenger) - SR(incumbent)` at **10 bps one-way costs**. Use the
paired Politis-Romano stationary bootstrap with 10,000 resamples, expected
block length 21, and the same return dates. Approximate the bootstrap
likelihood as Normal at the observed delta with its bootstrap standard
deviation, then update the universal skeptical prior
`delta ~ Normal(0.00, 0.05^2)`.

Promote only when both conditions hold:

1. `P(delta > 0.05 | data) >= 0.50`; and
2. posterior expected loss of promotion is at most 75% of the expected loss
   of keeping the incumbent.

Use the v8 loss in annualized Sharpe units without refitting it:

* `L(promote, delta) = max(-delta, 0) + 0.01`
* `L(keep, delta) = max(delta, 0)`

Condition 1 says a material improvement of 0.05 Sharpe must be more likely
than not; it is a decision threshold, not a disguised p-value. Condition 2
requires a margin beyond merely winning the expected-loss comparison and
prices in the fixed 0.01 switching/model-complexity cost. Equality keeps the
incumbent. Existing drawdown and turnover clauses remain unchanged. Report
the neutral-prior result as sensitivity, and keep the incumbent if the
lower-loss action flips between skeptical and neutral.

**Why the gate prior must be universal.** Deep-informed priors are useful
supplementary evidence only when an exact history exists. V8 made the evidence
asymmetry concrete: trend has 94 years and gold has 22, and gold-containing
arms have no valid deep prior. Letting the gate use deep evidence for some
families but not others would make promotion depend partly on data
availability rather than the common ETF decision record. Therefore the
deep-informed posterior is never the gate headline and cannot be compared
against another arm's neutral posterior.

**What this resolves from Q5.** The old `delta >= 0.10` point estimate ignores
sampling uncertainty, while a p<0.05 superiority test has too little power on
roughly 22 ETF years. This proposal integrates the uncertainty and asks the
allocation question directly. The 0.50 materiality probability is deliberately
not 0.95: the latter would recreate the low-power moratorium documented in Q5.
The 75% expected-loss ratio, universal skeptical prior, 10 bps returns, and
no-flip rule preserve incumbent inertia without pretending the sample can
prove small effects.

**Costs and unresolved implementation details.** The normal likelihood is an
approximation to dependent-data bootstrap draws, not new independent history.
The thresholds and loss ratio are policy choices, not empirical constants.
The automated Phase 3 gate must persist aligned incumbent and challenger
returns, reject a comparison with mismatched calendars, record the complete
posterior and both expected losses, and enforce exactly one pre-registered
challenger per final gate evaluation. If several candidates are screened to
produce that challenger, their selection and trials must already be recorded;
the gate must not choose among them. Planning must accept, amend, or reject
this proposal in a new dated journal entry before it governs any cycle.

### Q11 (2026-09-02) — xsmom-v15 holding-period series is not identified

Planning requested `xsmom-v15-holding` as a frequency curve from monthly to
annual, using the v13 French daily decile data and Gaussian rank-transition
turnover model. The requested economic question is whether selecting the
top-three stocks less often preserves enough momentum while lowering
constituent turnover.

The current archive cannot produce that return path. Its ten columns are
aggregate decile returns whose underlying stocks are reconstituted daily. A
monthly, quarterly, semi-annual, or annual target schedule in the existing
backtester changes only the weights among three **daily refreshed academic
indices**. Their internal membership still changes daily, so internal turnover
remains v13's 21.7x and the signal never becomes stale. Calling that a holding-
period test would not answer the pre-registered question.

There are two honest ways forward:

1. Obtain constituent-level point-in-time membership, returns, and market
   equity (for example licensed CRSP), then form and hold each selected cohort
   at the four calendar frequencies. This identifies both realized gross
   decay and turnover, but is a new data-layer decision and not the proposed
   cheap follow-up.
2. Approve a wholly model-implied stale-cohort approximation. At each scheduled
   rebalance select latent ranks above the 70th percentile; between rebalances,
   propagate their probability mass across the ten current deciles with the
   same Gaussian AR(1) rank model (`rho = 229/230`), and apply those fixed
   transition weights to the observed contemporaneous decile returns. Turnover
   is two times the cohort exit probability at the scheduled interval times
   rebalances per year. This yields a deterministic curve, but both the gross
   slower-holding return and its turnover are model outputs. It adds a strong
   exchangeability assumption not present in v13, and the monthly point will
   not reproduce v13's daily-reconstituted top-three result.

A third mechanically possible run—only reducing outer rebalances among the
three daily-refreshed decile columns—is rejected as mislabeled: it does not
trade the underlying momentum portfolio less and cannot measure momentum
decay.

Recommendation: planning must explicitly choose constituent data or the
stale-cohort approximation, and approve the latter's return-model assumption
if chosen. Do not pre-register or run v15 until that choice is recorded.

## Binding rules (outrank convenience, and outrank user-of-the-moment vibes)

1. `python -m pytest` passes before any research result is looked at.
2. Signals may use data <= t only. Every new signal gets a perturbation
   test in `tests/test_no_lookahead.py` (shock future prices, assert the
   past doesn't move) before its first backtest is inspected.
3. The promotion gate in `journal/2026-09-01-gate-preregistration.md` and
   the walk-forward scheme in
   `journal/2026-09-01-harness-scheme-preregistration.md` are
   pre-registered. Never edit past journal entries; amendments are NEW
   dated entries, written BEFORE the cycle/study they apply to.
4. Every configuration evaluated goes in the trials ledger — including
   abandoned and errored ones. Deflated Sharpe uses the distinct-config
   count (per the harness-scheme journal entry).
5. Results are always reported at 0/5/10 bps costs, beside SPY buy&hold
   and 60/40, with the sub-period breakdown (`metrics.by_subperiod`).
   Never a single blended number.
6. Phase discipline (DESIGN.md §11): no ML layer (Phase 5) before the
   harness + retrain loop (Phase 2-3) and live paper loop (Phase 4) exist.
7. No performance claims from ad-hoc runs. A claim exists only after the
   walk-forward harness + gate produce it.
8. Never commit market data (`data/` is gitignored, rebuildable) or
   secrets (`.env`, Tiingo/Alpaca keys).

## Commands

    source .venv/bin/activate          # after: uv venv && uv pip install -e ".[crosscheck,dev]"
    python -m pytest                   # must be green first
    python scripts/ingest.py           # refresh data (network required)
    python scripts/run_baselines.py    # sanity anchors vs known SPY history

## Sanity anchors (if these fail, the DATA is wrong — stop)

SPY since 2000: CAGR ~6-9%, max drawdown ~ -55% (2007-09).

## Notes

- Research returns use `adj_close` (dividend-adjusted) only. Raw `close`
  is for realism checks (bond ETF returns are mostly yield).
- Engine v0 executes at next CLOSE, not next open (journal 2026-09-01).
- Data currently rests on Yahoo alone until the Tiingo cross-check runs
  clean — carry the caveat on every number until then.
