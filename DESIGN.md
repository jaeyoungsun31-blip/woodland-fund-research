# The Woodland Fund — Design Doc v0.1

**Date:** 2026-09-01 · **Author:** Jaeyoung + Claude · **Status:** SIGNED OFF 2026-09-01 (name: Woodland Fund; repo: ~/Documents/Woodland Fund; gate §8 binding — see journal/)
**Decision scope:** US equities/ETFs · walk-forward retrain loop · ~5–10 hrs/week

---

## 1. What this project is

A research pipeline that develops, validates, and paper-trades systematic strategies on US equities/ETFs — where "self-improving" means a **disciplined walk-forward retrain loop**: on a schedule, the system re-fits its parameters on recent data, validates the challenger out-of-sample, and promotes it over the incumbent only if it clears a pre-registered bar. Every retrain decision is logged. The system gets better the way a good researcher gets better — by running honest experiments and keeping score — not by an agent rewriting itself.

Two goals, in priority order:

1. **Become a credible quant** — build the exact artifact (data pipeline → backtester → walk-forward harness → live paper loop) that quant research actually consists of. This is the goal you control.
2. **Be "financially well"** — positive risk-adjusted returns out-of-sample. This is the goal you don't control, and the doc is honest about that below.

## 2. The honest framing

**Steelman of the project.** Retail systematic trading on documented anomalies (momentum, trend, vol-management) is not crazy: these effects have decades of academic evidence, survive transaction costs at monthly rebalance frequency, and don't require speed or expensive data. A student who builds a leak-free backtester and a walk-forward harness has built something 95% of "algo trading" hobbyists never do, and it's precisely the skill set quant firms interview for. The self-improving loop is the legitimate version of adaptivity — real shops re-estimate models on rolling windows constantly.

**Devil's advocate.** `[Certain]` The base rate for retail strategies beating buy-and-hold SPY risk-adjusted, out-of-sample, after costs, is very low. Your edge candidates are the *most* published anomalies, meaning they're the most arbitraged; momentum has had brutal crash episodes (2009, 2020-style whipsaws). `[Certain]` The single most likely failure mode is not the market — it's you overfitting: every parameter you try is a lottery ticket, and a "self-improving" loop built carelessly is an **overfitting machine that automates data snooping**. `[Likely]` With daily bars and monthly rebalancing, 6–12 months of paper trading gives you only ~6–12 independent bets — far too few to statistically distinguish skill from luck. You will not *know* if it works within a year.

**So the resolution:** the P&L is the stretch goal; the pipeline, the methodology discipline, and the written experiment log are the guaranteed return. Treat live-money deployment as a Phase 6 question you're not allowed to ask until the paper loop has run ≥6 months. (Also: none of this is financial advice; when real money enters, the risk decisions are yours.)

## 3. What "self-improving" means here — the loop, precisely

```
                 ┌──────────────────────────────────────────┐
                 │  Monthly retrain job (cron)              │
                 └──────────────────────────────────────────┘
  1. Refresh data → integrity checks (gaps, splits, stale tickers)
  2. Re-fit challenger params on trailing train window
  3. Walk-forward validate challenger on held-out window
  4. Promotion gate: challenger beats incumbent on pre-registered
     criteria (§8)?  → yes: promote, log why
                     → no: keep incumbent, log why
  5. Incumbent trades the paper account until next cycle
  6. Append everything to the experiment journal (append-only)
```

Three properties make this science instead of snooping:

- **Pre-registration.** The promotion criteria are written down *before* any challenger is evaluated, and changing them is itself a logged, versioned event.
- **One-way test data.** The final holdout period is touched once per cycle by the gate — never by you during research.
- **Trial accounting.** Every configuration ever backtested is counted in a trials ledger, so you can compute how impressive a result *isn't* given how many things you tried (deflated Sharpe, §7).

## 4. Architecture

Five components, deliberately decoupled so each is testable alone:

| Component | Responsibility | Key rule |
|---|---|---|
| `data/` | Ingest daily OHLCV → parquet + DuckDB; integrity checks | Point-in-time only; raw data immutable |
| `signals/` | Feature/signal computation from prices | Signals at close *t* may only use data ≤ *t* |
| `backtest/` | Vectorized portfolio simulation with costs | Signal at close *t* → execute at open *t+1*, never same-bar |
| `harness/` | Walk-forward splits, param search, trials ledger, promotion gate | Only component allowed to touch validation/test windows |
| `live/` | Daily paper-trading job against Alpaca paper API; monitoring | Trades only the promoted incumbent's config, read from a versioned file |

Plus an append-only `journal/` (markdown + a SQLite table): every experiment, every promotion decision, every bug found. This journal is also your public portfolio artifact — write it like someone at a fund will read it, because ideally one will.

## 5. Data

- **Universe:** liquid US ETFs — the 11 SPDR sector ETFs + SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, DBC (~20 tickers). `[Certain]` An ETF universe sidesteps the single-stock survivorship-bias problem that silently corrupts most hobby backtests — none of these have delisted, and they *are* the tradeable instruments.
- **Source (amended 2026-09-01, see journal/2026-09-01-second-source-decision.md):** primary is Yahoo via yfinance with `auto_adjust=False`, giving unadjusted OHLCV and adjusted close on one calendar; cross-check source is Tiingo (free keyed API, 20+ yrs adjusted EOD) on every ingest. Stooq is retired — its CSV feed now sits behind a JavaScript anti-bot wall (journal/2026-09-01-data-source-stooq-blocked.md) and we do not defeat bot detection. Alpaca's own data feed enters in Phase 4 so research and execution eventually see the same prices. `[Likely]` Free daily-bar data is fully adequate at this frequency; verify current rate limits in Phase 0 — free-tier terms drift.
- **Adjustments:** store both adjusted (for signals/returns) and unadjusted (for realism checks) closes. Splits/dividends handled by the source's adjusted series, spot-checked.
- **Costs model:** commission $0, but assume ~5 bps one-way slippage+spread on these liquid ETFs; make it a config knob and report every backtest at 0/5/10 bps so you see how fragile the edge is.

## 6. Backtest engine

Custom vectorized pandas/polars engine (~300 lines), not a framework. Rationale: at daily frequency with ~20 tickers you don't need vectorbt/zipline machinery, and writing it yourself is half the educational value — plus you can unit-test it, which frameworks make awkward. Requirements:

- Next-bar execution (close-signal → next-open fill) enforced by construction, not convention.
- Costs and cash accounting explicit; no fractional leverage unless configured.
- **Correctness tests before any strategy work:** a buy-and-hold backtest must reproduce SPY's actual total return; a known 12-1 momentum backtest must land near published results. A backtester you haven't validated against known answers produces numbers, not evidence.
- Outputs: equity curve, per-period returns, turnover, exposure — pushed to a metrics module computing CAGR, vol, Sharpe, max drawdown, hit rate, and drawdown duration.

## 7. Walk-forward methodology (the actual science)

- **Splits:** rolling windows — e.g. train 5 yrs → validate 1 yr → step forward 1 yr — stitched into one continuous out-of-sample equity curve covering ~15 yrs. Parameters are chosen on train, evaluated on the *next* window only.
- **Embargo:** a gap (≥ max signal lookback) between train and validate windows so overlapping return windows don't leak.
- **Trials ledger + deflated Sharpe:** log every configuration evaluated; report Bailey & López de Prado's deflated Sharpe ratio so a 1.1 Sharpe found after 400 trials is recognized as noise. `[Certain]` This is the discipline that separates the project from every Medium-post trading bot.
- **Regime honesty:** report performance by sub-period (pre/post 2015, 2020, 2022) rather than one blended number; an edge that lives entirely in 2008–2012 is a history lesson, not a strategy.
- **Reference reading:** López de Prado, *Advances in Financial Machine Learning* (chs. on backtesting/CV); Bailey et al., "The Deflated Sharpe Ratio."

## 8. Promotion gate (pre-registered, v0)

A challenger replaces the incumbent only if, on the walk-forward out-of-sample stitched history: (a) net-of-cost Sharpe exceeds the incumbent's by ≥ 0.1; (b) max drawdown is not more than 1.25× the incumbent's; (c) the result holds at 10 bps costs; and (d) turnover hasn't grown >1.5×. Ties or marginal wins keep the incumbent — churn is a cost, and inertia is the correct prior. Amending these thresholds requires a dated journal entry *before* the cycle runs.

## 9. Strategy candidates for v1

Start with **one** family end-to-end before adding a second. Ordered recommendation:

1. **Time-series trend on the ETF universe** — long each ETF when above its ~10-month trend measure, else T-bills/IEF; risk-weight positions. *Why first:* simplest to implement leak-free, robust academic record (Faber; Moskowitz et al.), few parameters (small overfitting surface), monthly cadence fits your hours. *Bear case:* trend has whipsawed badly in fast-reversal markets and everyone knows the rule.
2. **Cross-sectional momentum on sector ETFs** — hold top-k sectors by 12-1 return, monthly. Adds ranking logic and higher turnover; good second strategy.
3. **Vol-managed overlay** — scale exposure by inverse realized vol. Not standalone; a modifier that composes with 1 and 2 and teaches risk targeting.

**Baselines every run must beat:** buy-and-hold SPY and a static 60/40 — reported side-by-side in every backtest output, always.

Later (Phase 5+): an ML signal layer (gradient boosting on engineered features predicting cross-sectional forward returns) slots into `signals/` without touching the harness — that's the payoff of the decoupled architecture.

## 10. Failure modes to guard against

Look-ahead bugs (enforced next-bar execution + unit tests); survivorship bias (ETF universe); overfitting (trials ledger, deflated Sharpe, few parameters, pre-registered gate); silent data corruption (ingest integrity checks, dual-source cross-check); **strategy churn** — the self-improving loop degenerating into chasing last year's winner (the gate's inertia bias + monthly-not-daily retraining); and **motivated reasoning** — relaxing the rules after a drawdown (the append-only journal exists so you catch yourself doing it).

## 11. Roadmap at 5–10 hrs/week

| Phase | Weeks | Deliverable | Done when |
|---|---|---|---|
| 0 — Setup | 1 | Repo, uv env, data ingestion → parquet/DuckDB, integrity checks | All tickers load clean with full available history (15+ yrs for the core; note XLRE/XLC only exist since 2015/2018); checks pass |
| 1 — Backtester | 2–3 | Engine + metrics + correctness tests | Reproduces SPY buy-and-hold & a published momentum result |
| 2 — Strategy v1 | 4–6 | Trend strategy + walk-forward harness + trials ledger | Stitched OOS equity curve vs. baselines, at 3 cost levels |
| 3 — The loop | 7–8 | Monthly retrain job + promotion gate + journal | One full automated cycle runs and logs end-to-end |
| 4 — Live paper | 9–10 | Alpaca paper account wired; daily execution job; drift monitor (live vs. simulated fills) | First live paper rebalance executes untouched |
| 5 — Expand | 11+ | Second strategy family; ML signal layer; public write-up | Journal has a publishable post-mortem per experiment |

Scope discipline: `[Likely]` the biggest schedule risk is Phase 1 perfectionism and Phase 5 starting early. The loop (Phase 3) is the point of the project — get there before making anything fancier.

## 12. Stack

Python 3.12 + `uv` · polars/pandas + DuckDB + parquet · matplotlib for tear sheets · `pytest` for engine tests · Alpaca paper API (free) for execution · GitHub repo (public journal, private configs if you prefer) · scheduled monthly retrain via cron or a scheduled task once Phase 3 lands.

## 13. Success criteria

- **Guaranteed-return tier (process):** leak-free validated backtester; ≥ 10 journaled experiments with honest post-mortems; one full automated retrain→gate→trade cycle in production; you can defend every methodology choice in an interview.
- **Stretch tier (financial):** stitched walk-forward OOS Sharpe > SPY's over 15 yrs at 10 bps costs; after 6+ months live paper, realized returns within tolerance of simulation (proves no leak), and only then a conversation about real money — sized as tuition, not income.

## 14. Decisions (resolved 2026-09-01)

1. Repo location & name — `Quant Lab` subfolder here plus a GitHub repo, or code elsewhere with only the journal here?
2. Public or private repo? (Public journal is the career play; public strategy configs are optional.)
3. Sign off on the §8 gate thresholds — they're pre-registered, so this sign-off is the moment they become binding.

*Note: your PLANNING.md gates Finances-domain expansion behind the AI Assistant roadmap. This project is a research/engineering effort, not the "boring core" finances build, so I've treated it as compatible — flag if you disagree.*
