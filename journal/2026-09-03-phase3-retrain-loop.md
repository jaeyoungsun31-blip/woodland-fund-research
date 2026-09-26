# 2026-09-03 — Phase 3 retrain loop implementation

Append-only engineering record. This is not a study and adds no strategy
configuration, fitted signal, market data or promotion decision.

## What was built

Phase 3 now has an isolated `woodland/live/` package and a single operational
entrypoint, `scripts/run_cycle.py`.

The incumbent registry stores the incumbent's name, parameters, effective
date, authorising journal entry, and its OOS return and turnover series by cost
scenario. The declared seed is the monthly 60% SPY / 40% IEF balanced
portfolio. Initialisation is explicit and refuses to overwrite an existing
registry. Replacement is a separate operation requiring the candidate's exact
journal reference, and every initialisation or replacement appends an audit
event. Evaluation alone cannot change the incumbent.

The promotion gate implements the four conditions signed on 2026-09-01
without adding a fifth:

1. OOS net Sharpe advantage of at least 0.10 at 5 bps;
2. maximum drawdown no more than 1.25 times the incumbent's;
3. the same 0.10 Sharpe advantage at 10 bps; and
4. annual turnover no more than 1.5 times the incumbent's.

The two Sharpe comparisons use aligned daily excess returns over the stored
real risk-free series, never the rf=0 convention. Paired stationary-bootstrap
and HAC results are returned beside the four-condition verdict, but do not
silently become a new condition. Every verdict is structured, lists each pass
and failure, and marks a failed challenger as completed.

The no-trade implementation computes the ideal target but trades only the
portion of each asset's weight gap outside the band, leaving the portfolio at
the nearest band boundary. The declared operational default is 5 percentage
points, carried from the previously implemented v12/v14 setting and not
searched here. One-way turnover and its daily-cycle annualisation are reported
against planning's 4.6x-9.3x retail budget.

Refusal is a normal result. A cycle emits no target when provenance or calendar
integrity fails, any ticker is stale versus the store consensus, the consensus
terminal bar is more than the declared five calendar days old, the realized
fold count differs from the frozen 22-fold scheme, or the SPY-since-2000 sanity
anchors breach 6%-9% CAGR or -60%..-50% maximum drawdown. Refusal precedes
refitting, gating and band application.

The runner defaults to read-only dry-run. Data refresh, persistence and target
display each require explicit command-line authority. A non-dry cycle writes
completed challenger rows once at the end with SQLite-lock retry, appends a
new `phase3` journal entry, and can replace an incumbent only when a named
challenger passed all four conditions and an exact promotion journal reference
was explicitly supplied. With no registered challenger, `no change` is the
normal output. The 60/40 seed has no estimable signal parameters, so its refit
step revalidates fixed parameters rather than fitting a signal.

## Verification

- Pre-change suite: 363 tests passed.
- Post-change suite: 381 tests passed.
- New focused tests: 16 passed, covering incumbent persistence and audit,
  all-pass and all-fail gate cases, exact ties retaining the incumbent, every
  refusal condition, inside/outside band arithmetic, and an end-to-end stored
  state dry-run that makes no writes and reports `no change`.
- Ruff: clean across the repository.
- Mypy: the new live package and runner are clean. The repository-wide check
  still reports 21 pre-existing errors in five older scripts outside this
  task's exclusive ownership; none was changed.

## Stored-data dry-run

The default runner was executed against the current local store without a
refresh. It completed normally with `decision: no change` and refused before
refit because eleven ticker provenance records still have cross-source
`INVESTIGATE` verdicts: XLB, XLE, XLI, XLK, XLP, XLU, XLV, XLY, QQQ, EFA and
DBC. It emitted no target, wrote no ledger row, wrote no cycle journal, changed
no incumbent state, fitted no signal and promoted nothing. That is the
intended fail-closed result; the integrity evidence was not relaxed to make the
loop run.
