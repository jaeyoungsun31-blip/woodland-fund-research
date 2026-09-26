"""Public metadata census for the four game-winner series; no volume selection."""

import json

from probe import ROOT, get

SERIES = ("KXNBAGAME", "KXMLBGAME", "KXNFLGAME", "KXNHLGAME")
OUT = ROOT / "sports_metadata"


def collect(series):
    markets = {}
    for route, path, base in (
        ("historical", "/historical/markets", {"series_ticker": series, "limit": 1000}),
        ("recent", "/markets", {"series_ticker": series, "status": "settled", "limit": 1000}),
    ):
        cursor = ""
        while True:
            payload = get(path, {**base, **({"cursor": cursor} if cursor else {})})
            for m in payload["markets"]:
                markets[m["ticker"]] = {
                    "ticker": m["ticker"],
                    "event": m["event_ticker"],
                    "series": series,
                    "result": m.get("result"),
                    "status": m.get("status"),
                    "rules_primary": m.get("rules_primary"),
                    "rules_secondary": m.get("rules_secondary"),
                    "close_time": m.get("close_time"),
                    "route": route,
                }
            cursor = payload.get("cursor") or ""
            if not cursor:
                break
    OUT.mkdir(exist_ok=True)
    with (OUT / f"{series}.jsonl").open("w") as out:
        for row in markets.values():
            out.write(json.dumps(row, separators=(",", ":")) + "\n")
    return len(markets), len({m["event"] for m in markets.values()})


if __name__ == "__main__":
    for series in SERIES:
        path = OUT / f"{series}.jsonl"
        if path.exists():
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            count = (len(rows), len({m["event"] for m in rows}))
        else:
            count = collect(series)
        print(series, *count, flush=True)
