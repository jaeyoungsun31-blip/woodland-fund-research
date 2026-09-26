# 2026-09-01 — Primary data source (Stooq) is blocked; single-source ingest

Append-only. This entry records a data-layer change made during the Phase 1
validation gate, and the methodology debt it creates.

## What happened

`scripts/ingest.py` failed on all 20 universe tickers with HTTP 404 from
`https://stooq.com/q/d/l/?s=<t>.us&i=d`. Manual investigation:

* `curl` to the same URL returns HTTP 200 carrying a JavaScript proof-of-work
  interstitial ("This site requires JavaScript to verify your browser"), not
  CSV. The `.pl` mirror and the index endpoint (`^spx`) serve the same wall.
* So the endpoint is not gone — it is behind bot detection. Stooq's CSV feed is
  no longer scriptable.

We did not attempt to defeat the challenge. Deliberate: solving anti-bot
proof-of-work to take data a provider has decided not to serve to scripts is
both a terms problem and a permanently fragile dependency to build a research
pipeline on.

## What changed

* **Yahoo (yfinance) is now the primary source.** One `auto_adjust=False`
  download returns unadjusted OHLCV *and* `Adj Close`, so `close` and
  `adj_close` share a calendar and split treatment by construction. Research
  returns continue to use `adj_close` only.
* `crosscheck_source` in `config/universe.yaml` is now `null`.
  `woodland.data.crosscheck_sources()` — a genuine two-provider return
  comparison — stays wired and unit-tested, idle until a second source exists.
* New `woodland.data.check_adjustment()`: within one source, the
  `adj_close/close` factor must be non-decreasing through time and equal 1.0 on
  the latest bar. Verified against Yahoo: SPY/IEF/TLT factors are monotone to
  within 1.3e-6 (published-price rounding) and terminate at exactly 1.0.
* Ingest writes `data/_provenance.json` per ticker, and prints a
  NO INDEPENDENT CROSS-CHECK banner naming every ticker that rests on one
  source. A single-source ingest is never reported as "ok".

## The methodology debt, stated plainly

DESIGN.md §5 requires a second source cross-checked on every ingest, and §10
lists silent data corruption as a named failure mode with the dual-source check
as its only guard. **That guard is currently absent.** `check_adjustment` and
`integrity_report` validate internal consistency; neither can detect an error
both series share, which is exactly what a second source is for. Every result
produced before a second source is restored carries this caveat.

DESIGN.md §5's source list is therefore wrong as written and needs amending —
proposed replacement: primary Yahoo, cross-check Tiingo or Alpaca (both keyed;
Alpaca credentials are needed for Phase 4 regardless). Pending Jaeyoung's
decision on which; DESIGN.md is not edited unilaterally.

## Not affected

The backtest engine, metrics, signals and their tests are untouched by this;
the change is confined to `woodland/data.py`, `scripts/ingest.py`,
`config/universe.yaml` and `tests/test_pipeline.py`.
