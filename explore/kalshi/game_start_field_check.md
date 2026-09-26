# Game-winner scheduled-start field check — stopped before analysis

The required pre-inspection suite ended: `619 passed, 1 skipped in 97.56s (0:01:37)`.

The public [series-list endpoint](https://docs.kalshi.com/api-reference/market/get-series-list) identifies four scoped game-winner tickers: `KXNBAGAME` (NBA Game), `KXMLBGAME` (Professional Baseball Game), `KXNFLGAME` (Professional Football Game), and `KXNHLGAME` (NHL Game). No other series was considered for the requested study.

The [market schema](https://docs.kalshi.com/api-reference/market/get-market) includes `open_time`, `close_time`, `expected_expiration_time`, `expiration_time`, and optional `occurrence_datetime`, but no `scheduled_start_time` or `game_start_time`. The [event schema](https://docs.kalshi.com/api-reference/events/get-event) and [event metadata schema](https://docs.kalshi.com/api-reference/events/get-event-metadata) likewise document no game-start timestamp. Public settled-market and event samples confirmed this is material:

| League | Sample event | `occurrence_datetime` | `expected_expiration_time` | Start-time evidence |
|---|---|---|---|---|
| NBA | `KXNBAGAME-26JUN13NYKSAS` | 2026-06-14 03:30 UTC | 2026-06-14 03:30 UTC | Rules give Jun 13 date, no clock time. |
| MLB | `KXMLBGAME-26JUL231507TBTOR` | 2026-07-23 22:07 UTC | 2026-07-23 22:07 UTC | Rules say 3:07 PM EDT = 19:07 UTC, three hours earlier. |
| NFL | `KXNFLGAME-26JAN25LASEA` | absent | 2026-01-26 02:30 UTC | Rules give no scheduled clock time. |
| NHL | `KXNHLGAME-26JUN14CARVGK` | 2026-06-15 03:00 UTC | 2026-06-15 03:00 UTC | Rules give Jun 14 date, no clock time. |

The MLB example demonstrates that `occurrence_datetime` is not the scheduled start; in all non-null samples it equals expected expiration. The field is absent for the NFL sample. `close_time` is actual market close, not a game-start schedule. Extracting a date from titles or tickers, subtracting an assumed game duration, or importing a third-party schedule would violate the requested metadata-only start-time requirement.

Per the instruction to stop if no start-time field exists, no candles or trades were fetched for this study, no quote-coverage or wash-trade computation was run, and no P&L or bootstrap result was produced. Only public unauthenticated GETs were used. No keys were read or sent.
