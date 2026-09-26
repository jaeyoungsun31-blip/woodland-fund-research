"""Phase 1 validation: run the baselines every strategy must beat.

Produces the side-by-side table (SPY buy-and-hold, 60/40) at the three cost
scenarios, plus sub-period breakdown. This script makes NO strategy claims —
it exists to sanity-check the engine against known market history.

Usage:  python scripts/run_baselines.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, data, metrics
from woodland.config import ROOT, all_tickers, load_config


def main() -> int:
    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    prices = data.build_matrix(["SPY", "IEF"], store)
    prices = prices.dropna(how="all")

    # A date the feed delivered for only part of the universe is excluded, never
    # forward-filled. Judged against the FULL universe calendar, not just these
    # two tickers, so a hole affecting both is still caught.
    full = data.build_matrix(all_tickers(cfg), store)
    _, suspect = data.drop_suspect_dates(full)
    if len(suspect):
        prices = prices.drop(index=suspect, errors="ignore")
        print(f"NOTE: excluded {len(suspect)} incomplete bar(s) from the price matrix: "
              + ", ".join(str(d.date()) for d in suspect))
        print("      (feed holes — see journal/2026-09-01-data-source-stooq-blocked.md)\n")

    spy = backtest.buy_and_hold(prices, "SPY")
    results = {"SPY buy&hold": spy.returns}
    for bps in cfg["backtest"]["cost_bps_scenarios"]:
        r = backtest.fixed_mix(prices, {"SPY": 0.6, "IEF": 0.4}, cost_bps=bps)
        results[f"60/40 monthly @{bps}bps"] = r.returns

    print("=== baselines (full history) ===")
    print(metrics.compare(results).round(3).to_string())

    print("\n=== SPY buy&hold by sub-period (regime honesty, DESIGN.md §7) ===")
    print(metrics.by_subperiod(spy.returns).round(3).to_string())

    print("\nSanity anchors: SPY CAGR since 2000 should land in the ~6-9% region "
          "with max drawdown near -55% (2007-09). If not, the DATA is wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
