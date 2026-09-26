"""Run the preregistered trend-v3 realized-volatility overlay."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, data, metrics
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import (
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    SECTORS,
    STEP_YEARS,
    TRAIN_YEARS,
    VALIDATE_YEARS,
)

RISK_OFF = "IEF"
VOL_WINDOW = 63
TARGET_ANN_VOL = 0.10
GRID = [{
    "lookbacks": LOOKBACKS,
    "aggregation": "equal_weight",
    "vol_window": VOL_WINDOW,
    "target_ann_vol": TARGET_ANN_VOL,
    "max_scale": 1.0,
}]


def build_targets(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    base = trend.ensemble_targets(
        prices,
        risk_assets=SECTORS,
        risk_off=RISK_OFF,
        lookback_months=config["lookbacks"],
    )
    return vol_target_targets(
        prices,
        base,
        window=config["vol_window"],
        target_ann_vol=config["target_ann_vol"],
        max_scale=config["max_scale"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", default="trend-v3-voltarget")
    args = parser.parse_args()

    cfg = load_config()
    prices = data.build_matrix(all_tickers(cfg), ROOT / cfg["data"]["store"])
    prices, dropped = data.drop_suspect_dates(prices)
    if len(dropped):
        print(f"excluded {len(dropped)} incomplete bar(s)")
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(
        index,
        train_years=TRAIN_YEARS,
        validate_years=VALIDATE_YEARS,
        step_years=STEP_YEARS,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    costs = [float(cost) for cost in cfg["backtest"]["cost_bps_scenarios"]]

    ledger = TrialsLedger(ROOT / "journal" / "trials.db")
    try:
        result = run_walkforward(
            prices,
            build_targets,
            GRID,
            splits=folds,
            ledger=ledger,
            study=args.study,
            max_lookback_days=MAX_LOOKBACK_DAYS,
            select_cost_bps=cfg["backtest"]["default_cost_bps"],
            report_cost_bps=costs,
        )

        lo, hi = result.oos_start, result.oos_end
        named = {
            f"{args.study} OOS @{int(cost)}bps": returns
            for cost, returns in result.oos_returns.items()
        }
        named["SPY buy&hold"] = backtest.buy_and_hold(prices, "SPY").returns.loc[lo:hi]
        mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
        vol_mix_targets = vol_target_targets(
            prices, mix_targets, window=VOL_WINDOW, target_ann_vol=TARGET_ANN_VOL
        )
        vol_mix_results = {}
        for cost in costs:
            mix = backtest.run(prices, mix_targets, cost_bps=cost)
            vol_mix = backtest.run(prices, vol_mix_targets, cost_bps=cost)
            named[f"60/40 @{int(cost)}bps"] = mix.returns.loc[lo:hi]
            named[f"vol-target 60/40 @{int(cost)}bps"] = vol_mix.returns.loc[lo:hi]
            vol_mix_results[cost] = vol_mix

        print(f"study '{args.study}': 63-day vol, 10% target; {len(folds)} folds")
        print(f"OOS window: {lo.date()} .. {hi.date()}")
        print(f"trials ledger: {result.n_trials} distinct configs, "
              f"{result.n_trial_rows} evaluations")
        print("\n=== stitched OOS vs baselines, identical window ===")
        print(metrics.compare(named).round(4).to_string())

        print("\n=== annualized turnover ===")
        print(result.summary()[["ann_turnover"]].round(3).to_string())
        for cost in costs:
            turnover = vol_mix_results[cost].turnover.loc[lo:hi]
            print(f"  vol-target 60/40 @{int(cost)}bps "
                  f"{metrics.ann_turnover(turnover):.3f}")

        print("\n=== sub-period breakdown @5bps: strategy ===")
        print(result.by_subperiod(5.0).round(4).to_string())
        print("\n=== sub-period breakdown @5bps: vol-target 60/40 ===")
        print(metrics.by_subperiod(vol_mix_results[5.0].returns.loc[lo:hi]).round(4).to_string())

        print("\n=== deflated Sharpe and effective breadth ===")
        for cost in costs:
            print(f"\n-- at {int(cost)} bps")
            print(dfl.report(result.deflated(cost)))
    finally:
        ledger.close()

    print("\nSource-verification caveat remains; harness output only, nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
