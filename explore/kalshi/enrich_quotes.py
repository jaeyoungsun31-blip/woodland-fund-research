"""Add public historical YES bid/ask candle closes to the bounded KXCPI pilot."""

import json
import time
from urllib.parse import quote

from probe import MARKETS, OBS, ROOT, SERIES, epoch, get

OUTPUT = ROOT / "pilot_observations_with_quotes.jsonl"
TIMING = ROOT / "pilot_quote_enrichment_timing.json"


def close_value(candle, side):
    field = candle.get(side) or {}
    return field.get("close_dollars") or field.get("close")


def enrich(market, old):
    close = epoch(market["close"])
    path = (
        f"/historical/markets/{quote(market['ticker'])}/candlesticks"
        if market["route"] == "historical"
        else f"/series/{SERIES}/markets/{quote(market['ticker'])}/candlesticks"
    )
    candles = get(path, {"start_ts": close - 48 * 3600, "end_ts": close, "period_interval": 1})[
        "candlesticks"
    ]
    candles = sorted(candles, key=lambda c: int(c["end_period_ts"]))
    result = {"ticker": market["ticker"], "horizons": {}}
    for h in (24, 6, 1):
        cutoff = close - h * 3600
        quoted = [
            c
            for c in candles
            if int(c["end_period_ts"]) <= cutoff
            and (close_value(c, "yes_bid") is not None or close_value(c, "yes_ask") is not None)
        ]
        candle = quoted[-1] if quoted else None
        quote_ts = int(candle["end_period_ts"]) if candle else None
        result["horizons"][str(h)] = {
            **old["horizons"][str(h)],
            "yes_bid_close_dollars": close_value(candle, "yes_bid") if candle else None,
            "yes_ask_close_dollars": close_value(candle, "yes_ask") if candle else None,
            "quote_candle_end_ts": quote_ts,
            "quote_age_seconds": cutoff - quote_ts if quote_ts is not None else None,
        }
    return result


def main():
    markets = json.loads(MARKETS.read_text())
    old = {r["ticker"]: r for r in (json.loads(line) for line in OBS.read_text().splitlines())}
    done = (
        {json.loads(line)["ticker"] for line in OUTPUT.read_text().splitlines()}
        if OUTPUT.exists()
        else set()
    )
    started = time.monotonic()
    with OUTPUT.open("a") as out:
        for index, market in enumerate(markets, 1):
            if market["ticker"] in done:
                continue
            out.write(
                json.dumps(enrich(market, old[market["ticker"]]), separators=(",", ":")) + "\n"
            )
            out.flush()
            if index % 50 == 0:
                print(f"KXCPI quotes {index}/{len(markets)}", flush=True)
    elapsed = time.monotonic() - started
    TIMING.write_text(
        json.dumps({"elapsed_seconds": round(elapsed, 2), "markets": len(markets)}) + "\n"
    )
    print(f"KXCPI quote enrichment complete: {len(markets)} markets, {elapsed:.2f}s")


if __name__ == "__main__":
    main()
