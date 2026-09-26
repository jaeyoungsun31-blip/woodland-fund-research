# Pre-commitment — Kalshi MLB favourite test (2025 season)

Written 2026-09-25, after the holdout seal (`5c8a205`, [HOLDOUT.md](HOLDOUT.md))
and **before any KXMLBGAME price, quote or candlestick was requested**. This is
an exploration, not a harness study. Nothing below may be changed after
results are seen. Any deviation will be recorded as a dated addition beneath
this document, and never as an edit.

## Events

- **Universe:** KXMLBGAME events that settled cleanly as YES/NO, with
  event-ticker year code `25`. Each event must have exactly two markets, one
  settled `yes` and one `no`. Events with a `scalar` or any other result are
  excluded. Every event passes `holdout.require_exploration_game` before any
  schedule match or price request, and again once its scheduled start is known.
- **Scheduled start:** `gameDate` (UTC) from the official MLB Stats API
  schedule, [statsapi.mlb.com/api/v1/schedule](https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2025-03-01&endDate=2025-11-30)
  (`sportId=1`, public, no key). Kalshi timestamps are never used as the start.
- **Matching:** by game date and both teams. The date is the ticker's date,
  compared with the schedule's `officialDate`. Teams come from the two market
  suffixes, matched to the schedule's team abbreviations from
  [statsapi.mlb.com/api/v1/teams](https://statsapi.mlb.com/api/v1/teams?sportId=1&season=2025).
  The only alias is `ARI` to `AZ`, since the tickers use both codes for
  Arizona. Matching is unordered on the team pair. Home and away come from
  the schedule.
- **Exclusions**, each counted in the report:
  - no schedule match, or an unmapped team code (for example the All-Star
    `ALHS`/`NLHS` style codes)
  - more than one schedule game for the same date and team pair
  - a doubleheader (`doubleHeader` of `Y` or `S`)
  - a status showing postponement, suspension, rescheduling or cancellation:
    `detailedState` containing `Postponed`, `Suspended` or `Cancelled`, or any
    non-null `rescheduleDate`, `rescheduledFrom`, `resumeDate` or
    `resumedFrom`, or `startTimeTBD` true

  Games of every `gameType`, both regular season and postseason, are
  eligible.
- **One observation per game**, taken from one fixed order book: **the home
  team's market** (YES means the home team wins). The other market is never
  read. This is fixed now, and the other book will not be tried.

## Cutoffs and quotes

- **Cutoffs:** 60 and 10 minutes before the scheduled start.
- **Candles:** one-minute Kalshi candlesticks for the home market. Markets
  settled before `market_settled_ts` from
  [GET /historical/cutoff](https://docs.kalshi.com/api-reference/historical/get-historical-cutoff-timestamps)
  use
  [GET /historical/markets/{ticker}/candlesticks](https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks).
  Later markets use
  [GET /series/{series_ticker}/markets/{ticker}/candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks).
  The endpoint is chosen by each market's settlement relative to the cutoff,
  and the route used is recorded per game.
- **Usable quote:** the latest candle with `end_period_ts` at or before the
  cutoff. Its age is `cutoff − end_period_ts`, and it is used only if the age
  is **300 seconds or less**. The candle's `yes_bid` close and `yes_ask` close
  must both be present. Otherwise the game has **no observation** at that
  cutoff. Nothing is imputed, and no earlier candle is substituted.

## Strategy

- YES ask = `yes_ask` close; NO ask = 1 − `yes_bid` close.
- **Favourite:** the side whose ask is above 0.50. If both asks are above
  0.50, which happens when the spread straddles 0.50, the favourite is the
  side with the higher ask. That is the same as the side with the higher
  midpoint. If the two asks are equal, there is no observation.
- Buy one contract of the favourite at its ask, and hold it to settlement.
  P&L per contract is `1 − ask − fee` if the favourite side settles in the
  money, and `−ask − fee` otherwise.
- **Fee:** the standard taker fee from Kalshi's current
  [fee schedule](https://kalshi.com/fee-schedule), read 2026-09-25, with no
  upcoming changes listed. The formula is
  `round up(M × 0.07 × C × P × (1 − P))`, from *Fee Schedule for July 2026
  – 7.7.26 Update* ([PDF](https://kalshi.com/docs/kalshi-fee-schedule.pdf)).
  - **KXMLBGAME is listed with multiplier M = 0.5 pre-live** (1 live). Both
    cutoffs are pre-live, so M = 0.5.
  - The fee is charged for a C = 100 contract order rounded up to the cent,
    then divided by 100. That reproduces the schedule's published
    KXMLBGAME 100-contract taker range of $0.04–$0.88.
  - **Counterfactual:** this applies 2026 fees to 2025 prices. The fee in
    force in 2025 may have differed, and account-level rounding
    ([fee rounding](https://docs.kalshi.com/getting_started/fee_rounding)) is
    not modelled.
- **Fee sensitivity (declared now, descriptive only):** the same primary
  metric with the fee on a single-contract order rounded up to the cent,
  which is $0.01 on every trade. It is strictly more costly, so it cannot
  rescue a failed primary.
- **Honest limits:** a one-minute candle's closing ask is not a guaranteed
  fill, and depth is not observed. The P&L is for one contract at the quoted
  ask.

## Metrics

- **Primary, per cutoff:** mean net P&L per contract across games, with a 95%
  bootstrap interval. The bootstrap is iid over games, 10,000 resamples,
  seed 0, percentile interval. It is reported separately at 60 and 10
  minutes.
- **Secondary, descriptive only:**
  - The same metric by favourite ask band: (0.50, 0.60), [0.60, 0.70) and
    [0.70, 1.00]. Each band gets n, mean P&L and a bootstrap interval with the
    same settings.
  - A calibration table: realized favourite win rate against ask, in 5¢
    bands [0.50, 0.55) … [0.95, 1.00]. Each band gets n, mean ask, win rate
    and a Wilson 95% interval.
- **Also reported:**
  - eligible games
  - usable games per cutoff
  - pull time
  - the worst single-game loss
  - the share of observations whose favourite ask is at least 0.70

## Sample gate

After schedules and markets are fetched and exclusions applied, and before any
P&L is computed: if **either** cutoff has fewer than **500** usable games, stop
and report the counts only.

## Kill rule

If the primary metric's 95% interval **includes zero or lies below it at both
cutoffs**, the Kalshi favourite line is **closed**. Price bands, calibration
and the fee sensitivity cannot rescue a failed primary. No other windows,
filters, thresholds, markets or fee assumptions may be added after results
are seen.

## Data handling

Public unauthenticated GETs only. `.env` is not opened. Raw API responses are
kept only under gitignored paths in `explore/kalshi/`. Only `.py` and `.md`
files are committed.
