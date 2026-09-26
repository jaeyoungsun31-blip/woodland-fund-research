"""trend-v4-deephistory: the trend signal on 1926-2026 Fama-French industries.

Pre-registered in journal/2026-09-01-trend-v4-deephistory-preregistration.md,
including the declared deviation from binding rule 5 (SPY and 60/40 do not
exist over this window; MKT and 60% MKT / 40% CASH stand in and are labelled
as such).

Harness output only. Nothing is promoted; the §8 gate is Phase 3.

Usage:  python scripts/run_trend_deephistory.py [--resamples 10000]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, metrics, stats
from woodland.config import ROOT, load_config
from woodland.fama_french import INDUSTRIES
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward
from woodland.signals import trend
from woodland.study import LOOKBACKS, MAX_LOOKBACK_DAYS, STEP_YEARS, TRAIN_YEARS, VALIDATE_YEARS

RISK_ASSETS = list(INDUSTRIES)
RISK_OFF = "CASH"
MARKET = "MKT"

SELECTION_GRID = [{"lookback_months": m} for m in LOOKBACKS]
ENSEMBLE_GRID = [{"lookbacks": LOOKBACKS, "aggregation": "equal_weight"}]


def load_deep_prices() -> pd.DataFrame:
    industries = pd.read_parquet(ROOT / "data" / "fama_french_12_industry_daily.parquet")
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    if not industries.index.equals(factors.index):
        raise ValueError("industry and factor calendars differ; re-run the FF ingest")
    prices = industries.join(factors, how="inner")
    if prices.isna().any().any():
        raise ValueError("deep-history matrix has missing values")
    return prices


def build_single(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    return trend.trend_targets(prices, risk_assets=RISK_ASSETS, risk_off=RISK_OFF,
                               lookback_months=config["lookback_months"])


def build_ensemble(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    return trend.ensemble_targets(prices, risk_assets=RISK_ASSETS, risk_off=RISK_OFF,
                                  lookback_months=config["lookbacks"])


def by_decade(returns: pd.Series) -> pd.DataFrame:
    """Decade breakdown: the default metric breaks were chosen for the ETF era
    and would lump 1932-2008 into a single bucket."""
    rows = {}
    years = pd.DatetimeIndex(returns.index).year
    for decade, chunk in returns.groupby((years // 10) * 10):
        if len(chunk) > 126:
            rows[f"{decade}s"] = metrics.summarize(chunk)
    return pd.DataFrame(rows).T


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument(
        "--ledger", type=Path, default=ROOT / "journal" / "trials.db",
        help="trials ledger path; point elsewhere to re-render a deterministic "
             "run without duplicating the authoritative record",
    )
    args = parser.parse_args()

    cfg = load_config()
    costs = [float(c) for c in cfg["backtest"]["cost_bps_scenarios"]]
    prices = load_deep_prices()
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=MAX_LOOKBACK_DAYS)
    sp.check_embargo_covers_lookback(folds, index, MAX_LOOKBACK_DAYS)
    print(f"deep history {index[0].date()}..{index[-1].date()}  {len(index)} bars; "
          f"{len(folds)} folds")
    print("FRICTIONLESS ACADEMIC SERIES — not tradeable securities.\n")

    ledger = TrialsLedger(args.ledger)
    results = {}
    try:
        for study, grid, builder in (
            ("trend-v4-deephistory-selection", SELECTION_GRID, build_single),
            ("trend-v4-deephistory-ensemble", ENSEMBLE_GRID, build_ensemble),
        ):
            results[study] = run_walkforward(
                prices, builder, grid, splits=folds, ledger=ledger, study=study,
                max_lookback_days=MAX_LOOKBACK_DAYS,
                select_cost_bps=cfg["backtest"]["default_cost_bps"],
                report_cost_bps=costs,
            )
            print(f"{study}: {results[study].n_trials} distinct configs, "
                  f"{results[study].n_trial_rows} evaluations")
    finally:
        ledger.close()

    selection = results["trend-v4-deephistory-selection"]
    ensemble = results["trend-v4-deephistory-ensemble"]
    lo, hi = ensemble.oos_start, ensemble.oos_end
    print(f"\nOOS window {lo.date()} .. {hi.date()} "
          f"({len(ensemble.oos_returns[5.0])} bars, {len(ensemble.oos_returns[5.0])/252:.1f}y)")

    mkt = backtest.buy_and_hold(prices, MARKET).returns.loc[lo:hi]
    mix_targets = backtest.fixed_mix_targets(prices, {MARKET: 0.6, RISK_OFF: 0.4})
    named = {"MKT buy&hold": mkt}
    mix_results = {}
    for cost in costs:
        mix_results[cost] = backtest.run(prices, mix_targets, cost_bps=cost)
        named[f"60% MKT / 40% CASH @{int(cost)}bps"] = mix_results[cost].returns.loc[lo:hi]
    for cost in costs:
        named[f"v4 selection @{int(cost)}bps"] = selection.oos_returns[cost]
        named[f"v4 ensemble @{int(cost)}bps"] = ensemble.oos_returns[cost]

    print("\n=== stitched OOS vs baselines, identical window ===")
    print(metrics.compare(named).round(4).to_string())

    print("\n=== annualized turnover ===")
    print("  selection", selection.summary()["ann_turnover"].round(3).to_dict())
    print("  ensemble ", ensemble.summary()["ann_turnover"].round(3).to_dict())
    print(f"  60/40 analogue @5bps "
          f"{metrics.ann_turnover(mix_results[5.0].turnover.loc[lo:hi]):.3f}")

    print("\n=== does the lookback stabilize with 5x the data? ===")
    chosen = [c["lookback_months"] for c in selection.selections["config"] if c]
    switches = sum(a != b for a, b in zip(chosen, chosen[1:], strict=False))
    print(f"  folds {len(chosen)}; distinct lookbacks chosen {sorted(set(chosen))}")
    print(f"  switches {switches} of {len(chosen)-1} transitions "
          f"({switches/max(len(chosen)-1,1):.1%})")
    print(f"  counts {pd.Series(chosen).value_counts().sort_index().to_dict()}")
    print("  v1 reference on 22 ETF folds: 6 of 7 lookbacks, 10 switches (47.6%)")

    print("\n=== sub-periods @5bps (default breaks), ensemble ===")
    print(ensemble.by_subperiod(5.0).round(4).to_string())
    print("\n=== by decade @5bps, ensemble ===")
    print(by_decade(ensemble.oos_returns[5.0]).round(4).to_string())

    print("\n=== deflated Sharpe and effective breadth ===")
    for label, result in (("selection", selection), ("ensemble", ensemble)):
        print(f"\n-- {label} @5bps")
        print(dfl.report(result.deflated(5.0)))

    print("\n=== Sharpe differences with 95% CIs "
          f"({args.resamples} resamples, block length {stats.DEFAULT_BLOCK_LENGTH}) ===")
    for name, series in (("v4 ensemble", ensemble.oos_returns[5.0]),
                         ("v4 selection", selection.oos_returns[5.0]),
                         ("MKT buy&hold", mkt),
                         ("60% MKT / 40% CASH", named["60% MKT / 40% CASH @5bps"])):
        point, low, high = stats.sharpe_confidence_interval(series, n_resamples=args.resamples)
        print(f"  {name:20s} {point:.3f}  95% CI [{low:.3f}, {high:.3f}]")
    for label_a, a, label_b, b in (
        ("v4 ensemble", ensemble.oos_returns[5.0], "MKT buy&hold", mkt),
        ("v4 ensemble", ensemble.oos_returns[5.0],
         "60% MKT / 40% CASH", named["60% MKT / 40% CASH @5bps"]),
        ("v4 ensemble", ensemble.oos_returns[5.0],
         "v4 selection", selection.oos_returns[5.0]),
    ):
        print()
        print(stats.bootstrap_sharpe_difference(a, b, name_a=label_a, name_b=label_b,
                                                n_resamples=args.resamples).summary())
        print(stats.ledoit_wolf_sharpe_test(a, b, name_a=label_a, name_b=label_b).summary())

    print("\nFrictionless academic series; harness output only; nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
