"""Public KXCPI candlestick pilot; no keys or trade-tape downloads."""

import argparse
import csv
import json
import math
import time
from collections import defaultdict
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
API = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = "KXCPI"
HOURS = (24, 6, 1)
MARKETS = ROOT / "pilot_markets.json"
OBS = ROOT / "pilot_observations.jsonl"
META = ROOT / "pilot_metadata.json"


def get(path, params=None):
    url = API + path + ("?" + urlencode(params) if params else "")
    for attempt in range(6):
        try:
            with urlopen(
                Request(url, headers={"User-Agent": "kalshi-public-pilot/1.0"}), timeout=45
            ) as r:
                return json.load(r)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504):
                raise
        except (URLError, TimeoutError):
            pass
        time.sleep(min(20, 2**attempt))
    raise RuntimeError(f"Public GET failed: {path}")


def epoch(text):
    return int(datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp())


def census():
    found = {}
    for route, path, params in (
        ("historical", "/historical/markets", {"series_ticker": SERIES, "limit": 1000}),
        ("recent", "/markets", {"series_ticker": SERIES, "status": "settled", "limit": 1000}),
    ):
        cursor = ""
        while True:
            page = get(path, {**params, **({"cursor": cursor} if cursor else {})})
            for m in page["markets"]:
                if m.get("result") in ("yes", "no"):
                    found[m["ticker"]] = {
                        "ticker": m["ticker"],
                        "event": m["event_ticker"],
                        "close": m["close_time"],
                        "result": m["result"],
                        "volume": m.get("volume_fp", "0"),
                        "route": route,
                    }
            cursor = page.get("cursor") or ""
            if not cursor:
                break
    return sorted(found.values(), key=lambda m: m["ticker"])


def observe(m):
    close = epoch(m["close"])
    path = (
        f"/historical/markets/{quote(m['ticker'])}/candlesticks"
        if m["route"] == "historical"
        else f"/series/{SERIES}/markets/{quote(m['ticker'])}/candlesticks"
    )
    candles = get(path, {"start_ts": close - 48 * 3600, "end_ts": close, "period_interval": 1})[
        "candlesticks"
    ]
    trades = sorted(
        (
            int(c["end_period_ts"]),
            (c.get("price") or {}).get("close_dollars") or (c.get("price") or {}).get("close"),
        )
        for c in candles
        if Decimal(str(c.get("volume_fp", c.get("volume", 0)))) > 0
    )
    trades = [(ts, price) for ts, price in trades if price is not None]
    horizons = {}
    for h in HOURS:
        cutoff = close - h * 3600
        before = [(ts, p) for ts, p in trades if ts <= cutoff]
        horizons[str(h)] = {
            "price": before[-1][1] if before else None,
            "candle_end": before[-1][0] if before else None,
            "source": m["route"] + "_candlestick_close",
            "trade_inside_window": any(cutoff < ts <= close for ts, _ in trades),
        }
    return {"ticker": m["ticker"], "horizons": horizons}


def pilot():
    started = time.monotonic()
    markets = json.loads(MARKETS.read_text()) if MARKETS.exists() else census()
    if not MARKETS.exists():
        MARKETS.write_text(json.dumps(markets, indent=2) + "\n")
    timing = (
        json.loads(META.read_text())
        if META.exists()
        else {"census_seconds": time.monotonic() - started, "candle_seconds": 0.0}
    )
    done = (
        {json.loads(line)["ticker"] for line in OBS.read_text().splitlines()}
        if OBS.exists()
        else set()
    )
    with OBS.open("a") as out:
        for index, market in enumerate(markets, 1):
            if market["ticker"] in done:
                continue
            began = time.monotonic()
            out.write(json.dumps(observe(market), separators=(",", ":")) + "\n")
            out.flush()
            timing["candle_seconds"] += time.monotonic() - began
            META.write_text(json.dumps(timing, indent=2) + "\n")
            if index % 50 == 0:
                print(f"KXCPI candles: {index}/{len(markets)}", flush=True)
    print(f"KXCPI pilot: {len(markets)} markets; pull {sum(timing.values()):.2f}s")


def wilson(yes, n):
    z = 1.959963984540054
    p = yes / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def fee(price, rate):
    return (rate * price * (1 - price)).quantize(Decimal("0.01"), rounding=ROUND_CEILING)


def write_csv(name, rows):
    with (ROOT / name).open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze():
    markets = json.loads(MARKETS.read_text())
    observed = {r["ticker"]: r for r in (json.loads(line) for line in OBS.read_text().splitlines())}
    if len(observed) != len(markets):
        raise RuntimeError(f"Pilot incomplete: {len(observed)}/{len(markets)} markets")
    lookup = {m["ticker"]: m for m in markets}
    calibration, taker, maker = [], [], []
    summary = {
        "series": SERIES,
        "category": "Economics",
        "settled_markets": len(markets),
        "events": len({m["event"] for m in markets}),
        "horizons": {},
    }
    for h in HOURS:
        rows = [(lookup[t], o["horizons"][str(h)]) for t, o in observed.items()]
        eligible = [(m, o) for m, o in rows if o["price"] is not None]
        reps = {}
        for m, o in eligible:
            old = reps.get(m["event"])
            if old is None or (Decimal(m["volume"]), m["ticker"]) > (
                Decimal(old[0]["volume"]),
                old[0]["ticker"],
            ):
                reps[m["event"]] = (m, o)
        summary["horizons"][str(h)] = {
            "market_observations": len(eligible),
            "event_observations": len(reps),
            "markets_without_trade_in_window": sum(not o["trade_inside_window"] for _, o in rows),
            "markets_total": len(rows),
            "source_counts": {
                s: sum(o["source"] == s for _, o in eligible)
                for s in {o["source"] for _, o in eligible}
            },
        }
        bins = defaultdict(list)
        for m, o in reps.values():
            bins[(min(19, int(Decimal(o["price"]) * 20)), o["source"])].append((m, o))
        for (bucket, source), members in sorted(bins.items()):
            prices = [Decimal(o["price"]) for _, o in members]
            n = len(members)
            yes = sum(m["result"] == "yes" for m, _ in members)
            low, high = wilson(yes, n)
            mean_price = sum(prices) / n
            common = {
                "horizon_h": h,
                "bin": f"{bucket * 5:02d}-{(bucket + 1) * 5:02d}¢",
                "source": source,
                "events": n,
                "yes": yes,
                "mean_yes_price_dollars": f"{mean_price:.5f}",
            }
            calibration.append(
                {
                    **common,
                    "yes_frequency": f"{yes / n:.5f}",
                    "wilson_low": f"{low:.5f}",
                    "wilson_high": f"{high:.5f}",
                }
            )
            for kind, rate, target in (
                ("taker", Decimal("0.07"), taker),
                ("maker_upper_bound_fill_not_guaranteed", Decimal("0.0175"), maker),
            ):
                mean_fee = sum(fee(p, rate) for p in prices) / n
                edge = Decimal(yes) / n - mean_price - mean_fee
                lo = Decimal(str(low)) - mean_price - mean_fee
                hi = Decimal(str(high)) - mean_price - mean_fee
                target.append(
                    {
                        **common,
                        "kind": kind,
                        "mean_fee_dollars": f"{mean_fee:.5f}",
                        "net_pnl_dollars": f"{edge:.5f}",
                        "edge_interval_low": f"{lo:.5f}",
                        "edge_interval_high": f"{hi:.5f}",
                        "interval_excludes_zero": lo > 0 or hi < 0,
                    }
                )
    write_csv("pilot_calibration.csv", calibration)
    write_csv("pilot_taker_pnl.csv", taker)
    write_csv("pilot_maker_pnl.csv", maker)
    timing = json.loads(META.read_text())
    summary.update(
        pull_seconds=round(sum(timing.values()), 2),
        seconds_per_market=round(timing["candle_seconds"] / len(markets), 3),
        taker_bins_interval_excludes_zero=sum(r["interval_excludes_zero"] for r in taker),
        maker_bins_interval_excludes_zero=sum(r["interval_excludes_zero"] for r in maker),
    )
    (ROOT / "pilot_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("pilot", "analyze"))
    args = parser.parse_args()
    pilot() if args.command == "pilot" else analyze()
