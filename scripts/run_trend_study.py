"""Trend study v1: the Faber trend signal through the walk-forward harness.

Pre-registered in journal/2026-09-01-trend-study-preregistration.md — the grid,
the fixed design choices, the selection rule and the reporting format were all
fixed before this ran.

This produces HARNESS OUTPUT, not a promotion decision. The §8 gate is Phase 3.

Usage:  python scripts/run_trend_study.py [--study trend-v1]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import data, metrics
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward, with_baselines
from woodland.signals import trend
from woodland.study import MAX_LOOKBACK_DAYS, SECTORS, STEP_YEARS, TRAIN_YEARS, VALIDATE_YEARS

# --- everything below is pre-registered; changing it needs a NEW journal entry
RISK_OFF = "IEF"
GRID = [{"lookback_months": m} for m in range(4, 11)]


def build_targets(prices: pd.DataFrame, config: dict[str, int]) -> pd.DataFrame:
    return trend.trend_targets(
        prices,
        risk_assets=SECTORS,
        risk_off=RISK_OFF,
        lookback_months=config["lookback_months"],
        max_risk_weight=1.0,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--study", default="trend-v1")
    args = ap.parse_args()

    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    costs = [float(c) for c in cfg["backtest"]["cost_bps_scenarios"]]

    prices = data.build_matrix(all_tickers(cfg), store)
    prices, dropped = data.drop_suspect_dates(prices)
    if len(dropped):
        print(f"excluded {len(dropped)} incomplete bar(s): "
              + ", ".join(str(d.date()) for d in dropped))

    price_index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(price_index, train_years=TRAIN_YEARS,
                           validate_years=VALIDATE_YEARS, step_years=STEP_YEARS,
                           embargo_days=MAX_LOOKBACK_DAYS)
    sp.check_embargo_covers_lookback(folds, price_index, MAX_LOOKBACK_DAYS)

    print(f"\nstudy '{args.study}': {len(GRID)} configs x {len(folds)} folds; "
          f"embargo {MAX_LOOKBACK_DAYS} bars vs declared lookback {MAX_LOOKBACK_DAYS}")

    ledger = TrialsLedger(ROOT / "journal" / "trials.db")
    result = run_walkforward(
        prices, build_targets, GRID,
        splits=folds, ledger=ledger, study=args.study,
        max_lookback_days=MAX_LOOKBACK_DAYS,
        select_cost_bps=cfg["backtest"]["default_cost_bps"],
        report_cost_bps=costs,
    )

    print(f"\nOOS window: {result.oos_start.date()} .. {result.oos_end.date()} "
          f"({len(result.oos_returns[5.0])} bars)")
    print(f"trials ledger: {result.n_trials} distinct configs, "
          f"{result.n_trial_rows} evaluations recorded")

    print("\n=== stitched OOS vs baselines, same window (CLAUDE.md rule 5) ===")
    print(with_baselines(prices, result).round(4).to_string())

    # turnover is not in the comparison table (baselines carry their own); the
    # §8 gate's condition (d) is a turnover ratio, so report it explicitly.
    print("\nannualized turnover, strategy:")
    print(result.summary()[["ann_turnover"]].round(3).to_string())
    for name, res in [("SPY buy&hold", __import__("woodland.backtest", fromlist=["x"])
                       .buy_and_hold(prices, "SPY")),
                      ("60/40 @5bps", __import__("woodland.backtest", fromlist=["x"])
                       .fixed_mix(prices, {"SPY": 0.6, "IEF": 0.4}, cost_bps=5.0))]:
        w = res.turnover.loc[result.oos_start:result.oos_end]
        print(f"  {name:14s} {metrics.ann_turnover(w):.3f}")

    print("\n=== selected config per fold (is it stable, or chasing?) ===")
    sel = result.selections[["split", "validate_start", "validate_end",
                             "config", "train_score", "n_rebalances"]]
    print(sel.to_string(index=False))
    chosen = [s["lookback_months"] for s in result.selections["config"] if s]
    print("lookback chosen per fold:", chosen)
    print("distinct lookbacks chosen:", sorted(set(chosen)),
          "| switches:", sum(a != b for a, b in zip(chosen, chosen[1:], strict=False)))

    print("\n=== sub-period breakdown @5bps (regime honesty, DESIGN.md §7) ===")
    print(result.by_subperiod(5.0).round(4).to_string())

    print("\n=== deflated Sharpe against the FULL trial count ===")
    for c in costs:
        print(f"\n-- at {int(c)} bps")
        from woodland.harness import deflated as dfl
        print(dfl.report(result.deflated(c)))

    ledger.close()
    print("\nHarness output only. Nothing is promoted; the §8 gate is Phase 3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
