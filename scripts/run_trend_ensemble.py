"""Run the preregistered fixed-lookback trend-v2 ensemble through the harness."""

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
from woodland.harness.walkforward import run_walkforward, with_baselines
from woodland.signals import trend
from woodland.study import (
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    SECTORS,
    STEP_YEARS,
    TRAIN_YEARS,
    VALIDATE_YEARS,
)

RISK_OFF = "IEF"
GRID = [{"lookbacks": LOOKBACKS, "aggregation": "equal_weight"}]


def build_targets(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    return trend.ensemble_targets(
        prices,
        risk_assets=SECTORS,
        risk_off=RISK_OFF,
        lookback_months=config["lookbacks"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", default="trend-v2-ensemble")
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

        print(f"study '{args.study}': fixed seven-lookback ensemble; {len(folds)} folds")
        print(f"OOS window: {result.oos_start.date()} .. {result.oos_end.date()}")
        print(f"trials ledger: {result.n_trials} distinct configs, "
              f"{result.n_trial_rows} evaluations")
        print("\n=== stitched OOS vs baselines, identical window ===")
        print(with_baselines(prices, result).round(4).to_string())

        print("\n=== annualized turnover ===")
        print(result.summary()[["ann_turnover"]].round(3).to_string())
        for name, baseline in [
            ("SPY buy&hold", backtest.buy_and_hold(prices, "SPY")),
            ("60/40 @5bps", backtest.fixed_mix(prices, {"SPY": 0.6, "IEF": 0.4})),
        ]:
            window = baseline.turnover.loc[result.oos_start:result.oos_end]
            print(f"  {name:14s} {metrics.ann_turnover(window):.3f}")

        print("\n=== sub-period breakdown @5bps ===")
        print(result.by_subperiod(5.0).round(4).to_string())

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
