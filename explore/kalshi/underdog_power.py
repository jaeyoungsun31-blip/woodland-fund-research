"""POST-HOC, IN-SAMPLE power sketch for an underdog confirmation. Not evidence.

Reads the 2025 observations written by mlb_favourite.py (gate stage) and the
2025 settled results already on disk. Mirrors the favourite rule: buy the
other side at its ask (1 - favourite bid), same fee rule. Fetches nothing.
"""

import json
import math
from collections import defaultdict
from decimal import ROUND_CEILING, Decimal

import numpy as np
from holdout import require_exploration_game
from mlb_favourite import OBS, favourite, fee, load_events, ticker_date, utc

Z = 1.959963984540054 + 0.8416212335729143  # two-sided 5%, 80% power
MLB_2026 = 2430  # 30 clubs x 162 / 2, regular season
NHL_2025_26 = 1312  # counted from api-web.nhle.com weekly schedule, gameType 2
KALSHI_2025_EVENTS = 2214


def nhl_fee(price, contracts=100):
    """KXNHLGAME is listed at multiplier 1 (kalshi.com/fee-schedule, 2026-09-25)."""
    p = Decimal(str(price))
    raw = Decimal("0.07") * contracts * p * (1 - p)
    return float((raw * 100).to_integral_value(rounding=ROUND_CEILING) / 100 / contracts)


def underdog_trades(rows, outcome, minutes):
    trades = []
    for r in rows:
        require_exploration_game(r["event"], utc(r["start"]))
        q = r["quotes"][minutes]
        pick = favourite(q) if q else None
        if pick is None:
            continue
        fav_side, _ = pick
        if fav_side == "yes":
            side, ask = "no", round(1 - q["yes_bid"], 4)
        else:
            side, ask = "yes", round(q["yes_ask"], 4)
        won = outcome[r["home_market"]] == side
        gross = (1 if won else 0) - ask
        trades.append(
            {
                "date": ticker_date(r["event"]),
                "ask": ask,
                "gross": gross,
                "pnl": gross - fee(ask),
                "nhl_fee_pnl": gross - nhl_fee(ask),
            }
        )
    return trades


def design_effect(trades, key="pnl"):
    x = np.array([t[key] for t in trades])
    resid = x - x.mean()
    by_date = defaultdict(float)
    for t, e in zip(trades, resid, strict=True):
        by_date[t["date"]] += e
    var_cluster = sum(v * v for v in by_date.values()) / len(x) ** 2
    var_iid = x.var(ddof=1) / len(x)
    return var_cluster / var_iid, len(by_date)


def main():
    rows = [json.loads(line) for line in OBS.read_text().splitlines()]
    outcome = {m["ticker"]: m["result"] for ms in load_events().values() for m in ms}
    out = {}
    for minutes in ("60", "10"):
        trades = underdog_trades(rows, outcome, minutes)
        pnl = np.array([t["pnl"] for t in trades])
        nhl = np.array([t["nhl_fee_pnl"] for t in trades])
        sd = float(pnl.std(ddof=1))
        deff, dates = design_effect(trades)
        yield_ = len(trades) / KALSHI_2025_EVENTS
        edge_mlb, edge_nhl = float(pnl.mean()), float(nhl.mean())
        n_a = MLB_2026 * yield_
        n_b = NHL_2025_26 * yield_
        designs = {
            "a_mlb2026": (n_a, edge_mlb),
            "b_nhl2025_26": (n_b, edge_nhl),
            "c_a_plus_b": (n_a + n_b, (n_a * edge_mlb + n_b * edge_nhl) / (n_a + n_b)),
            "d_a_plus_mlb2027": (2 * n_a, edge_mlb),
        }
        table = {}
        for name, (n, edge) in designs.items():
            se = sd * math.sqrt(deff / n)
            table[name] = {
                "n_games": round(n),
                "assumed_edge": edge,
                "se": se,
                "expected_t": edge / se,
                "mde_80pct": Z * se,
                "mde_80pct_iid": Z * sd / math.sqrt(n),
            }
        out[minutes] = {
            "n_2025": len(trades),
            "yield_per_kalshi_event": yield_,
            "in_sample_edge_mlb_fee": edge_mlb,
            "in_sample_edge_nhl_fee": edge_nhl,
            "mean_gross": float(np.mean([t["gross"] for t in trades])),
            "mean_ask": float(np.mean([t["ask"] for t in trades])),
            "win_rate": float(np.mean([t["gross"] + t["ask"] > 0.5 for t in trades])),
            "sd": sd,
            "design_effect_by_date": deff,
            "dates": dates,
            "t_2025_clustered": edge_mlb / (sd * math.sqrt(deff / len(trades))),
            "designs": table,
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
