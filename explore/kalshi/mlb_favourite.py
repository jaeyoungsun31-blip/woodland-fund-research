"""Kalshi MLB favourite test, 2025 season, per precommit_mlb.md.

    python explore/kalshi/mlb_favourite.py gate      # schedules, markets, quotes; no outcomes
    python explore/kalshi/mlb_favourite.py analyze   # refuses unless both cutoffs have >= 500

Public unauthenticated GETs only. Raw responses stay under gitignored paths.
"""

import argparse
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

import numpy as np
from holdout import require_exploration_game
from probe import ROOT, get

SERIES = "KXMLBGAME"
CUTOFFS = (60, 10)
MAX_AGE = 300
GATE_MIN = 500
ALIAS = {"ARI": "AZ"}
STATSAPI = "https://statsapi.mlb.com/api/v1"
RAW = ROOT / "mlb2025_raw"
CANDLES = RAW / "candles"
OBS = ROOT / "mlb2025_observations.jsonl"
GATE = ROOT / "mlb2025_gate.json"
RESULTS = ROOT / "mlb2025_results.json"
BAD_STATES = ("Postponed", "Suspended", "Cancelled")
MOVED = ("rescheduleDate", "rescheduledFrom", "resumeDate", "resumedFrom")
BANDS = (("0.50-0.60", 0.50, 0.60), ("0.60-0.70", 0.60, 0.70), ("0.70+", 0.70, 1.0001))


def statsapi(path, params, cache_name):
    path_out = RAW / cache_name
    if path_out.exists():
        return json.loads(path_out.read_text())
    url = f"{STATSAPI}{path}?{urlencode(params)}"
    with urlopen(Request(url, headers={"User-Agent": "kalshi-public-pilot/1.0"}), timeout=60) as r:
        payload = json.load(r)
    RAW.mkdir(exist_ok=True)
    path_out.write_text(json.dumps(payload) + "\n")
    return payload


def utc(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def ticker_date(event):
    return datetime.strptime(event.split("-")[1][:7], "%y%b%d").date().isoformat()


def load_events():
    rows = [
        json.loads(line)
        for line in (ROOT / "sports_metadata" / f"{SERIES}.jsonl").read_text().splitlines()
    ]
    events = defaultdict(list)
    for row in rows:
        if row["event"].split("-")[1][:2] == "25":
            events[row["event"]].append(row)
    return events


def match_games(events, schedule, abbrev):
    by_key = defaultdict(list)
    for day in schedule["dates"]:
        for game in day["games"]:
            pair = frozenset(
                (game["teams"]["away"]["team"]["id"], game["teams"]["home"]["team"]["id"])
            )
            by_key[(game["officialDate"], pair)].append(game)
    kept, excluded = [], Counter()
    for event, markets in sorted(events.items()):
        require_exploration_game(event)
        results = sorted(m["result"] for m in markets)
        if len(markets) != 2 or results != ["no", "yes"]:
            excluded["not clean YES/NO settled"] += 1
            continue
        codes = {m["ticker"].rsplit("-", 1)[1]: m for m in markets}
        ids = {code: abbrev.get(ALIAS.get(code, code)) for code in codes}
        if None in ids.values():
            excluded["unmapped team code"] += 1
            continue
        games = by_key.get((ticker_date(event), frozenset(ids.values())), [])
        if not games:
            excluded["no schedule match"] += 1
            continue
        if len(games) > 1:
            excluded["multiple schedule games same date and teams"] += 1
            continue
        game = games[0]
        if game.get("doubleHeader") in ("Y", "S"):
            excluded["doubleheader"] += 1
            continue
        state = game["status"].get("detailedState", "")
        if (
            any(word in state for word in BAD_STATES)
            or any(game.get(k) for k in MOVED)
            or game["status"].get("startTimeTBD")
        ):
            excluded["postponed/suspended/rescheduled/TBD"] += 1
            continue
        start = utc(game["gameDate"])
        require_exploration_game(event, start)
        home_id = game["teams"]["home"]["team"]["id"]
        home_code = next(code for code, team in ids.items() if team == home_id)
        kept.append(
            {
                "event": event,
                "home_market": codes[home_code]["ticker"],
                "home_result": codes[home_code]["result"],
                "settled": codes[home_code]["close_time"],
                "start": game["gameDate"],
                "gamePk": game["gamePk"],
                "gameType": game["gameType"],
            }
        )
    return kept, excluded


def candles(game, settled_cutoff):
    path = CANDLES / f"{game['home_market']}.json"
    if path.exists():
        payload = json.loads(path.read_text())
    else:
        start = int(utc(game["start"]).timestamp())
        historical = utc(game["settled"]) < settled_cutoff
        route = (
            f"/historical/markets/{quote(game['home_market'])}/candlesticks"
            if historical
            else f"/series/{SERIES}/markets/{quote(game['home_market'])}/candlesticks"
        )
        body = get(
            route,
            {"start_ts": start - 3600 - MAX_AGE - 60, "end_ts": start - 600, "period_interval": 1},
        )
        payload = {"route": "historical" if historical else "live", **body}
        CANDLES.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n")
    return payload


def close(block, key="close"):
    if not block:
        return None
    value = block.get(key, block.get(f"{key}_dollars"))
    return None if value is None else float(value)


def quote_at(payload, cutoff_ts):
    before = [c for c in payload["candlesticks"] if c["end_period_ts"] <= cutoff_ts]
    if not before:
        return None
    candle = max(before, key=lambda c: c["end_period_ts"])
    age = cutoff_ts - candle["end_period_ts"]
    bid, ask = close(candle.get("yes_bid")), close(candle.get("yes_ask"))
    if age > MAX_AGE or bid is None or ask is None:
        return None
    return {"candle_end": candle["end_period_ts"], "age": age, "yes_bid": bid, "yes_ask": ask}


def gate():
    t0 = time.time()
    teams = statsapi("/teams", {"sportId": 1, "season": 2025}, "teams_2025.json")
    abbrev = {t["abbreviation"]: t["id"] for t in teams["teams"]}
    schedule = statsapi(
        "/schedule",
        {"sportId": 1, "startDate": "2025-01-01", "endDate": "2025-12-31"},
        "schedule_2025.json",
    )
    cutoff_info = get("/historical/cutoff")
    settled_cutoff = utc(cutoff_info["market_settled_ts"])
    events = load_events()
    kept, excluded = match_games(events, schedule, abbrev)
    with OBS.open("w") as out:
        for index, game in enumerate(kept, 1):
            payload = candles(game, settled_cutoff)
            start = int(utc(game["start"]).timestamp())
            quotes = {str(m): quote_at(payload, start - 60 * m) for m in CUTOFFS}
            row = {k: v for k, v in game.items() if k != "home_result"}
            out.write(json.dumps({**row, "route": payload["route"], "quotes": quotes}) + "\n")
            if index % 250 == 0:
                print(f"quotes {index}/{len(kept)}", flush=True)
    rows = [json.loads(line) for line in OBS.read_text().splitlines()]
    usable = {str(m): sum(r["quotes"][str(m)] is not None for r in rows) for m in CUTOFFS}
    summary = {
        "events_2025": len(events),
        "eligible_games": len(kept),
        "excluded": dict(excluded),
        "usable": usable,
        "routes": dict(Counter(r["route"] for r in rows)),
        "historical_cutoff": cutoff_info,
        "pull_seconds": round(time.time() - t0, 2),
        "gate_passed": all(v >= GATE_MIN for v in usable.values()),
    }
    GATE.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def fee(price, contracts=100):
    p = Decimal(str(price))
    raw = Decimal("0.5") * Decimal("0.07") * contracts * p * (1 - p)
    cents = (raw * 100).to_integral_value(rounding=ROUND_CEILING) / 100
    return float(cents / contracts)


def favourite(q):
    yes_ask, no_ask = round(q["yes_ask"], 4), round(1 - q["yes_bid"], 4)
    if max(yes_ask, no_ask) <= 0.50 or math.isclose(yes_ask, no_ask):
        return None
    return ("yes", yes_ask) if yes_ask > no_ask else ("no", no_ask)


def bootstrap(values, reps=10_000, seed=0):
    data = np.asarray(values, dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(data), size=(reps, len(data)))
    low, high = np.percentile(data[idx].mean(axis=1), [2.5, 97.5])
    return float(low), float(high)


def wilson(k, n, z=1.959963984540054):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def summarize(trades, pnl_key="pnl"):
    values = [t[pnl_key] for t in trades]
    low, high = bootstrap(values)
    return {"n": len(values), "mean": sum(values) / len(values), "ci95": [low, high]}


def analyze():
    summary = json.loads(GATE.read_text())
    if not summary["gate_passed"]:
        sys.exit(f"sample gate failed: {summary['usable']}; no P&L computed")
    rows = [json.loads(line) for line in OBS.read_text().splitlines()]
    outcome = {}
    for markets in load_events().values():
        for m in markets:
            outcome[m["ticker"]] = m["result"]
    report = {"gate": summary, "cutoffs": {}}
    for minutes in map(str, CUTOFFS):
        trades = []
        for r in rows:
            require_exploration_game(r["event"], utc(r["start"]))
            q = r["quotes"][minutes]
            pick = favourite(q) if q else None
            if pick is None:
                continue
            side, ask = pick
            won = outcome[r["home_market"]] == side
            f100, f1 = fee(ask), fee(ask, contracts=1)
            trades.append(
                {
                    "event": r["event"],
                    "side": side,
                    "ask": ask,
                    "won": won,
                    "fee": f100,
                    "pnl": (1 if won else 0) - ask - f100,
                    "pnl_fee1": (1 if won else 0) - ask - f1,
                }
            )
        bands = {}
        for name, lo, hi in BANDS:
            sub = [
                t
                for t in trades
                if (lo < t["ask"] if lo == 0.50 else lo <= t["ask"]) and t["ask"] < hi
            ]
            bands[name] = summarize(sub) if sub else {"n": 0}
        calibration = []
        for k in range(10):
            lo, hi = 0.50 + 0.05 * k, 0.55 + 0.05 * k + (0.0001 if k == 9 else 0)
            sub = [t for t in trades if lo <= t["ask"] < hi]
            if sub:
                wins = sum(t["won"] for t in sub)
                calibration.append(
                    {
                        "band": f"{lo:.2f}-{min(hi, 1):.2f}",
                        "n": len(sub),
                        "mean_ask": sum(t["ask"] for t in sub) / len(sub),
                        "win_rate": wins / len(sub),
                        "wilson95": list(wilson(wins, len(sub))),
                    }
                )
        worst = min(trades, key=lambda t: t["pnl"])
        report["cutoffs"][minutes] = {
            "primary": summarize(trades),
            "fee_sensitivity_1_contract": summarize(trades, "pnl_fee1"),
            "bands": bands,
            "calibration": calibration,
            "worst_loss": {k: worst[k] for k in ("event", "side", "ask", "fee", "pnl")},
            "share_ask_ge_070": sum(t["ask"] >= 0.70 for t in trades) / len(trades),
            "win_rate": sum(t["won"] for t in trades) / len(trades),
            "mean_ask": sum(t["ask"] for t in trades) / len(trades),
            "mean_fee": sum(t["fee"] for t in trades) / len(trades),
            "sides": dict(Counter(t["side"] for t in trades)),
        }
    fails = [m for m, c in report["cutoffs"].items() if c["primary"]["ci95"][0] <= 0]
    report["kill_rule"] = "CLOSED" if len(fails) == len(CUTOFFS) else "SURVIVES"
    RESULTS.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("gate", "analyze"))
    {"gate": gate, "analyze": analyze}[parser.parse_args().stage]()
