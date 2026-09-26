# Top-20 favourite-strategy exploration status

The pre-inspection repository gate was `619 passed, 1 skipped in 91.83s (0:01:31)`.

Kalshi's [historical](https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks) and [recent](https://docs.kalshi.com/api-reference/market/get-market-candlesticks) candlesticks document `yes_bid.close` and `yes_ask.close` (or their `_dollars` forms). `pilot_observations_with_quotes.jsonl` adds the last available YES bid and ask candle closes at or before each cutoff to the existing 508-market KXCPI pilot, along with the quote candle timestamp and age. The enrichment took 124.98 seconds. Both quote fields were present for 411/508 markets at 24h and 456/508 at 6h and 1h within the 48-hour lookback. Median quote ages were 18 minutes, 2.45 hours, and 7.38 hours respectively. Only 34, 37, and 27 markets respectively had a quote candle ending exactly at the 24h, 6h, and 1h cutoff minute. A last available quote candle should not be described as an executable quote at the exact cutoff.

The public [series list](https://docs.kalshi.com/api-reference/market/get-series-list) returned 14,288 series with aggregate all-event volume. Exact settled-volume ranking requires summing settled market volume; the `settled_series_rank.json` file is explicitly incomplete (`complete: false`). Three candidates were fully scanned:

| Series | Settled volume (contracts) | Settled markets | Events |
|---|---:|---:|---:|
| KXBTC15M | 19,384,558,475.44 | 26,701 | 26,701 |
| KXNBAGAME | 11,672,093,033.17 | 2,892 | 1,446 |
| KXMLBGAME | 9,937,286,047.24 | 9,134 | 4,567 |

The KXBTCD census was deliberately stopped after **more than 250,000 archived settled market records**; its count and volume are not final. At the KXCPI pilot rate of 0.244 seconds per market, even those 250,000 markets alone imply more than 16.9 hours of sequential candle requests. The requested top-20 one-candle-per-market pull was not started, and no favourite-strategy P&L or bootstrap inference was run. No partial sample is represented as the top 20.

The earliest public version of Bürgi, Deng and Whelan located was the [UCD July 2025 working paper](https://www.ucd.ie/economics/t4media/WP2025_19.pdf), which gives no exact release day. The proposed 2025-06-01 split remains an assumption; [CEPR dates its version to September 8, 2025](https://cepr.org/publications/dp20631).
