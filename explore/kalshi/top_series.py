"""Rank Kalshi series by settled-market volume using public endpoints only."""

import json
import time
from decimal import Decimal
from pathlib import Path

from probe import ROOT, get

SERIES_FILE = ROOT / "series_volume_listing.json"
RANK_FILE = ROOT / "settled_series_rank.json"


def scan_series(series):
    ticker = series["ticker"]
    path = ROOT / "rank_markets" / f"{ticker}.jsonl"
    if path.exists():
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        return rows
    rows = {}
    for route, endpoint, params in (
        ("historical", "/historical/markets", {"series_ticker": ticker, "limit": 1000}),
        ("recent", "/markets", {"series_ticker": ticker, "status": "settled", "limit": 1000}),
    ):
        cursor = ""
        pages = 0
        while True:
            payload = get(endpoint, {**params, **({"cursor": cursor} if cursor else {})})
            pages += 1
            for m in payload["markets"]:
                if m.get("result") in ("yes", "no"):
                    rows[m["ticker"]] = {
                        "ticker": m["ticker"], "series": ticker,
                        "event": m["event_ticker"], "close": m["close_time"],
                        "result": m["result"], "volume": m.get("volume_fp", "0"),
                        "route": route,
                    }
            cursor = payload.get("cursor") or ""
            if pages % 25 == 0:
                print(ticker, route, pages, len(rows), flush=True)
            if not cursor:
                break
    path.parent.mkdir(exist_ok=True)
    with path.open("w") as out:
        for m in rows.values():
            out.write(json.dumps(m, separators=(",", ":")) + "\n")
    return list(rows.values())


def main():
    start = time.monotonic()
    series = json.loads(SERIES_FILE.read_text()) if SERIES_FILE.exists() else get(
        "/series", {"include_volume": "true"}
    )["series"]
    if not SERIES_FILE.exists():
        SERIES_FILE.write_text(json.dumps(series) + "\n")
    ordered = sorted(series, key=lambda s: Decimal(s.get("volume_fp") or "0"), reverse=True)
    ranking = []
    for i, s in enumerate(ordered):
        rows = scan_series(s)
        total = sum((Decimal(m["volume"]) for m in rows), Decimal(0))
        ranking.append({"ticker": s["ticker"], "category": s.get("category"),
                        "fee_type": s.get("fee_type"), "fee_multiplier": s.get("fee_multiplier"),
                        "settled_volume": str(total), "settled_markets": len(rows),
                        "events": len({m["event"] for m in rows}),
                        "all_event_volume_bound": s.get("volume_fp")})
        ranking.sort(key=lambda r: Decimal(r["settled_volume"]), reverse=True)
        RANK_FILE.write_text(json.dumps({"complete": False, "scanned": i + 1,
                                         "elapsed_seconds": round(time.monotonic() - start, 2),
                                         "ranking": ranking}, indent=2) + "\n")
        print(i + 1, s["ticker"], len(rows), total, flush=True)
        if len(ranking) >= 20 and Decimal(ranking[19]["settled_volume"]) >= Decimal(
            ordered[i + 1].get("volume_fp") or "0"
        ):
            break
    RANK_FILE.write_text(json.dumps({"complete": True, "scanned": i + 1,
                                     "elapsed_seconds": round(time.monotonic() - start, 2),
                                     "ranking": ranking}, indent=2) + "\n")


if __name__ == "__main__":
    main()
