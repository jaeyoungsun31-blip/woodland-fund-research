# Kalshi calibration feasibility pilot — KXCPI

The repository gate immediately before inspection was `619 passed, 1 skipped in 92.50s (0:01:32)`. This exploration uses only public GET requests and writes only here. No API key was read or sent. The pilot stopped after the single KXCPI series; it did not launch an all-category pull.

## Method

The [historical markets endpoint](https://docs.kalshi.com/api-reference/historical/get-historical-markets) and [recent markets endpoint](https://docs.kalshi.com/api-reference/market/get-markets) supply settled outcomes and event IDs. For each KXCPI market, the cheapest endpoint in **requests per market** that supplies all three horizons is one 1-minute candlestick request over the 48 hours preceding `close_time`: [historical candlesticks](https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks) for archived markets or [recent candlesticks](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) for newer ones. We retain the final candle with positive volume and a non-null `price.close` at or before each cutoff. This is a **YES-side price in dollars per $1 contract**, rounded to the minute's candle close; it is not an exact last-trade timestamp. The [filtered trades endpoint](https://docs.kalshi.com/api-reference/historical/get-historical-trades) would need separate horizon queries, so no trade histories were downloaded. Only three observations and three within-window trade flags per market are retained. The 48-hour lookback means markets with no prior traded candle in that range have missing observations, even if an older trade exists. This is a feasibility limitation, not an imputed zero.

For each horizon, `(close - horizon, close]` is the window used for the no-trade share. Calibration uses one observed market per event, choosing the highest all-time volume (ticker breaks ties). This avoids treating multiple mutually related KXCPI strikes in one event as independent observations. Raw market and event observation counts are both reported. Bins are 5¢ wide; `historical_candlestick_close` and `recent_candlestick_close` are **separate rows** even when they have the same price bin. Wilson 95% intervals are for the event-level YES frequency. The net-edge interval subtracts the observed mean price and mean fee from the Wilson endpoints; it does not account for price selection or clustering uncertainty. No significance claim is made across bins.

## Pilot scale

508 settled markets, 63 events, and 23,845,775.21 reported contracts of market volume; wall-clock public pull time 124.54 seconds (including metadata census), or 0.244 seconds per candlestick request. The horizon market/event observation counts were 323/61 at 24h, 392/63 at 6h, and 392/63 at 1h. No trade in the corresponding window occurred for 132/508 (26.0%), 238/508 (46.9%), and 254/508 (50.0%) markets. Kalshi's [August 2026 research publication](https://kalshi.com/research/publications/calibration) reports 2,243,741 resolved markets across eleven categories through mid-2026. Linear extrapolation at the pilot's 0.244 seconds/market is about **6.34 days** of candle requests, plus metadata, retries, and any rate limiting. That is an illustrative lower-bound scale estimate, not a measured all-category census or schedule.

## Outputs

- `pilot_markets.json`: 508 settled market metadata records.
- `pilot_observations.jsonl`: three price/source/window flags per market, no raw candles or trades.
- `pilot_summary.json`: counts, timing, source split, and interval flags.
- `pilot_calibration.csv`: 5¢ bins, YES frequency, Wilson 95% interval, event count and YES count.
- `pilot_taker_pnl.csv`: net YES-buy P&L per contract and interval.
- `pilot_maker_pnl.csv`: **upper bound, fill not guaranteed**; same fields at the maker fee.

The [current fee schedule](https://kalshi.com/docs/kalshi-fee-schedule.pdf), effective July 7, 2026, lists KXCPI with taker multiplier 1 and maker multiplier 1. We use one-contract fee approximations `ceil_to_cent(0.07 × P × (1-P))` and `ceil_to_cent(0.0175 × P × (1-P))`; no settlement fee. [Kalshi's rounding documentation](https://docs.kalshi.com/getting_started/fee_rounding) notes account-specific precision and order-level fee accumulation, so actual fills can differ. Expected YES-buy net P&L per event is realized YES frequency minus mean YES price minus mean fee. The tables use **today's fees on historical prices**, a counterfactual. A last traded candle close is **not an executable quote**: a taker would generally pay the ask, and a maker at the displayed price may never fill. Event-level fee exceptions, timing, selection, and slippage are not modeled. This is a feasibility probe, not a trading result.

Run `python explore/kalshi/probe.py pilot` to resume the one-series public pull, then `python explore/kalshi/probe.py analyze` after it is complete. The script refuses analysis of an incomplete pilot.
