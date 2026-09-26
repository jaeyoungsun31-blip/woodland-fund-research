"""trend-v5-riskweight: inverse-vol and shrinkage minimum-variance sleeves.

Pre-registered in journal/2026-09-01-trend-v5-riskweight-preregistration.md,
including the declared departure from the handoff's wording (two single-config
studies rather than one two-config grid, because v4 measured per-fold
selection as harmful).

Harness output only. Nothing is promoted; the §8 gate is Phase 3.

Usage:  python scripts/run_trend_riskweight.py [--resamples 10000] [--ledger PATH]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, data, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward
from woodland.signals import trend
from woodland.study import (
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    SECTORS,
    STEP_YEARS,
    TRAIN_YEARS,
    VALIDATE_YEARS,
    stitch,
)

RISK_OFF = "IEF"
VOL_WINDOW = 126

STUDIES = {
    "trend-v5-riskweight-invvol": "inverse_vol",
    "trend-v5-riskweight-minvar": "min_variance",
}


def make_builder(weighting: str) -> Callable[[pd.DataFrame, dict], pd.DataFrame]:
    def build(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
        return trend.ensemble_targets(
            prices, risk_assets=SECTORS, risk_off=RISK_OFF,
            lookback_months=config["lookbacks"],
            weighting=config["weighting"], vol_window=config["vol_window"],
        )
    assert weighting
    return build


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    args = parser.parse_args()

    cfg = load_config()
    costs = [float(c) for c in cfg["backtest"]["cost_bps_scenarios"]]
    prices, _ = data.drop_suspect_dates(
        data.build_matrix(all_tickers(cfg), ROOT / cfg["data"]["store"]))
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=MAX_LOOKBACK_DAYS)
    sp.check_embargo_covers_lookback(folds, index, MAX_LOOKBACK_DAYS)

    ledger = TrialsLedger(args.ledger)
    results = {}
    try:
        for study, weighting in STUDIES.items():
            grid = [{"lookbacks": LOOKBACKS, "aggregation": "equal_weight",
                     "weighting": weighting, "vol_window": VOL_WINDOW}]
            results[study] = run_walkforward(
                prices, make_builder(weighting), grid, splits=folds, ledger=ledger,
                study=study, max_lookback_days=MAX_LOOKBACK_DAYS,
                select_cost_bps=cfg["backtest"]["default_cost_bps"],
                report_cost_bps=costs,
            )
            print(f"{study}: {results[study].n_trials} config, "
                  f"{results[study].n_trial_rows} evaluations")
    finally:
        ledger.close()

    invvol = results["trend-v5-riskweight-invvol"]
    minvar = results["trend-v5-riskweight-minvar"]
    lo, hi = invvol.oos_start, invvol.oos_end

    # v2 incumbent, rebuilt deterministically (no ledger rows)
    v2_targets = trend.ensemble_targets(prices, risk_assets=SECTORS,
                                        risk_off=RISK_OFF, lookback_months=LOOKBACKS)
    v2 = {c: backtest.run(prices, stitch(prices, v2_targets, folds),
                          cost_bps=c).returns.loc[lo:hi] for c in costs}
    if abs(metrics.sharpe(v2[5.0]) - 0.700) > 0.002:
        print(f"v2 rebuild {metrics.sharpe(v2[5.0]):.3f} != journalled 0.700; stopping")
        return 1

    named = {"SPY buy&hold": backtest.buy_and_hold(prices, "SPY").returns.loc[lo:hi]}
    for cost in costs:
        named[f"60/40 @{int(cost)}bps"] = backtest.fixed_mix(
            prices, {"SPY": 0.6, "IEF": 0.4}, cost_bps=cost).returns.loc[lo:hi]
    for cost in costs:
        named[f"v2 equal-weight @{int(cost)}bps"] = v2[cost]
        named[f"v5 inverse-vol @{int(cost)}bps"] = invvol.oos_returns[cost]
        named[f"v5 min-variance @{int(cost)}bps"] = minvar.oos_returns[cost]

    print(f"\nOOS {lo.date()} .. {hi.date()} ({len(v2[5.0])} bars); "
          f"vol window {VOL_WINDOW} bars")
    print("\n=== stitched OOS vs baselines and the v2 incumbent ===")
    print(metrics.compare(named).round(4).to_string())

    print("\n=== annualized turnover @5bps ===")
    v2_run = backtest.run(prices, stitch(prices, v2_targets, folds), cost_bps=5.0)
    print(f"  v2 equal-weight  "
          f"{metrics.ann_turnover(v2_run.turnover.loc[lo:hi]):.3f}")
    print(f"  v5 inverse-vol   {invvol.summary().loc['OOS @5bps', 'ann_turnover']:.3f}")
    print(f"  v5 min-variance  {minvar.summary().loc['OOS @5bps', 'ann_turnover']:.3f}")

    for label, result in (("inverse-vol", invvol), ("min-variance", minvar)):
        print(f"\n=== sub-periods @5bps: v5 {label} ===")
        print(result.by_subperiod(5.0).round(4).to_string())

    print("\n=== deflated Sharpe and effective breadth ===")
    for label, result in (("inverse-vol", invvol), ("min-variance", minvar)):
        print(f"\n-- {label} @5bps")
        print(dfl.report(result.deflated(5.0)))

    print(f"\n=== against the v2 incumbent ({args.resamples} resamples, "
          f"block {stats.DEFAULT_BLOCK_LENGTH}) ===")
    for name, series in (("v2 equal-weight", v2[5.0]),
                         ("v5 inverse-vol", invvol.oos_returns[5.0]),
                         ("v5 min-variance", minvar.oos_returns[5.0])):
        point, low, high = stats.sharpe_confidence_interval(series, n_resamples=args.resamples)
        print(f"  {name:18s} {point:.3f}  95% CI [{low:.3f}, {high:.3f}]")
    for label, series in (("v5 inverse-vol", invvol.oos_returns[5.0]),
                          ("v5 min-variance", minvar.oos_returns[5.0])):
        print(f"\ncorrelation with v2: {series.corr(v2[5.0]):.4f}")
        print(stats.bootstrap_sharpe_difference(series, v2[5.0], name_a=label,
                                                name_b="v2 equal-weight",
                                                n_resamples=args.resamples).summary())
        print(stats.ledoit_wolf_sharpe_test(series, v2[5.0], name_a=label,
                                            name_b="v2 equal-weight").summary())

    print("\nHarness output only; source-verification caveat stands; nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
