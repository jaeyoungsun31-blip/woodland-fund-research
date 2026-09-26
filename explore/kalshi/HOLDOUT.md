# Sealed KXMLBGAME holdout

Written 2026-09-25, before any KXMLBGAME price, quote or candlestick was
requested for any game.

**Every KXMLBGAME game with a scheduled start on or after 2026-01-01 00:00 UTC
is a sealed holdout.** The MLB favourite exploration uses games from the 2025
season only (scheduled start in calendar 2025, UTC, and event-ticker year code
`25`). No price, quote, P&L, calibration or other outcome-conditioned
statistic may be computed on a sealed game. Games before 2025 are out of scope.

Every entry point that requests candlesticks or computes a result must pass
each game through `require_exploration_game` in [holdout.py](holdout.py)
before the request. The guard checks the ticker's year code first, so a
sealed game is refused before any network call. Once the official scheduled
start is known it also checks that. It raises on any refused game and never
filters silently. [test_holdout.py](test_holdout.py) covers it. It sits outside
the repository's `testpaths`, so run it explicitly:

    .venv/bin/python -m pytest -q explore/kalshi/test_holdout.py

## Prior contact with the sealed period (disclosure)

The holdout is **not pristine**. Earlier explorations in this directory, all
before this seal, touched 2026 KXMLBGAME metadata:

- `sports_metadata/KXMLBGAME.jsonl`: a public settled-market census of all
  KXMLBGAME markets, 2025 and 2026, **including each market's settled
  result** and rules text. Results were counted in aggregate (YES/NO/scalar)
  and were never analysed against prices.
- `rank_markets/KXMLBGAME.jsonl` and `top20_status.md`: settled volume per
  market, 2025 and 2026, used only for series ranking.
- `mlb_schedule_cache/` (170 dates, 2026-03-26 to 2026-09-20) and
  `mlb_start_validation.json`: official MLB schedules for 2026, which carry
  final scores, and a 200-game check that Kalshi rules-text start times
  matched them (`sports_start_validation_report.md`).
- `game_start_field_check.md`: a handful of 2026 market and event records.

**No KXMLBGAME price, quote or candlestick was ever fetched, and no
favourite-strategy P&L, hit rate or calibration was computed, for any season.**
The earlier `pilot_*` price files are KXCPI only. The sealed period has
therefore been exposed to outcome and volume metadata, but not to any
price-conditioned result. A later test on it should say so.
