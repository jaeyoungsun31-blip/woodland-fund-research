"""Render every study's tear sheet and a machine-readable results summary.

This closes the gap that `scripts/tear_sheet.py` left open: that module is a
renderer that must be handed a completed ``BacktestResult``, and until now no
script ever handed it one, so ``reports/`` stayed empty.

Nothing here is a new study. Each series is REBUILT from the frozen,
pre-registered configuration and is checked against the Sharpe recorded in the
journal before anything is written; a mismatch aborts the run rather than
publishing a picture of a different portfolio (same discipline as
``scripts/run_inference.py``). No ledger rows are written.

Usage:  python scripts/generate_reports.py [--skip-deep]
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, data, metrics
from woodland.backtest import BacktestResult
from woodland.config import ROOT, all_tickers, load_config
from woodland.fama_french import INDUSTRIES
from woodland.harness import splits as sp
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import (
    ETF_RISK_OFF,
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    SECTORS,
    STEP_YEARS,
    TRAIN_YEARS,
    VALIDATE_YEARS,
    stitch,
)
from woodland.tearsheet import save_tear_sheet

COST = 5.0
VOL_WINDOW, TARGET_ANN_VOL = 63, 0.10

# Journalled at 5 bps. Reconstruction must reproduce these to 3 decimals.
EXPECTED = {
    "v2_ensemble": 0.700, "v3_voltarget": 0.709, "spy": 0.660,
    "mix_60_40": 0.806, "vt_60_40": 0.853,
    "v4_ensemble": 0.861, "mkt": 0.710, "mkt_cash_60_40": 0.841,
}

REPORTS = ROOT / "reports"


def slice_result(result: BacktestResult, lo, hi) -> BacktestResult:
    """Restrict a result to the stitched OOS window, rebasing equity to $1."""
    returns = result.returns.loc[lo:hi]
    return replace(
        result,
        returns=returns,
        equity=(1.0 + returns).cumprod(),
        holdings=result.holdings.loc[lo:hi],
        turnover=result.turnover.loc[lo:hi],
    )


def oos_window(index: pd.DatetimeIndex, folds: list):
    windows = [f.validate_index(index) for f in folds]
    return (min(w[0] for w in windows if len(w)), max(w[-1] for w in windows if len(w)))


def build_etf_results() -> dict[str, BacktestResult]:
    cfg = load_config()
    prices = data.build_matrix(all_tickers(cfg), ROOT / cfg["data"]["store"])
    prices, _ = data.drop_suspect_dates(prices)
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=MAX_LOOKBACK_DAYS)
    lo, hi = oos_window(index, folds)

    base = trend.ensemble_targets(prices, risk_assets=SECTORS,
                                  risk_off=ETF_RISK_OFF, lookback_months=LOOKBACKS)
    vt = vol_target_targets(prices, base, window=VOL_WINDOW, target_ann_vol=TARGET_ANN_VOL)
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    vt_mix_targets = vol_target_targets(prices, mix_targets, window=VOL_WINDOW,
                                        target_ann_vol=TARGET_ANN_VOL)

    raw = {
        "v2_ensemble": backtest.run(prices, stitch(prices, base, folds), cost_bps=COST),
        "v3_voltarget": backtest.run(prices, stitch(prices, vt, folds), cost_bps=COST),
        "spy": backtest.buy_and_hold(prices, "SPY"),
        "mix_60_40": backtest.run(prices, mix_targets, cost_bps=COST),
        "vt_60_40": backtest.run(prices, vt_mix_targets, cost_bps=COST),
    }
    return {k: slice_result(v, lo, hi) for k, v in raw.items()}


def build_deep_results() -> dict[str, BacktestResult]:
    industries = pd.read_parquet(ROOT / "data" / "fama_french_12_industry_daily.parquet")
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    prices = industries.join(factors, how="inner")
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=MAX_LOOKBACK_DAYS)
    lo, hi = oos_window(index, folds)

    base = trend.ensemble_targets(prices, risk_assets=list(INDUSTRIES),
                                  risk_off="CASH", lookback_months=LOOKBACKS)
    mix_targets = backtest.fixed_mix_targets(prices, {"MKT": 0.6, "CASH": 0.4})
    raw = {
        "v4_ensemble": backtest.run(prices, stitch(prices, base, folds), cost_bps=COST),
        "mkt": backtest.buy_and_hold(prices, "MKT"),
        "mkt_cash_60_40": backtest.run(prices, mix_targets, cost_bps=COST),
    }
    return {k: slice_result(v, lo, hi) for k, v in raw.items()}


TITLES = {
    "v2_ensemble": "trend-v2 ensemble — 9 sector ETFs (5 bps)",
    "v3_voltarget": "trend-v3 vol-targeted ensemble — 9 sector ETFs (5 bps)",
    "spy": "SPY buy & hold — baseline",
    "mix_60_40": "60/40 SPY/IEF monthly — baseline (5 bps)",
    "vt_60_40": "Vol-targeted 60/40 — baseline (5 bps)",
    "v4_ensemble": "trend-v4 ensemble — FF 12 industries, 1932-2026 (5 bps)",
    "mkt": "MKT buy & hold — deep-history baseline",
    "mkt_cash_60_40": "60% MKT / 40% CASH — deep-history baseline (5 bps)",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-deep", action="store_true",
                        help="ETF studies only (deep history is the slow half)")
    args = parser.parse_args()

    results = build_etf_results()
    if not args.skip_deep:
        results |= build_deep_results()

    print("=== reconstruction check against journalled Sharpes ===")
    ok = True
    for key, result in results.items():
        got = metrics.sharpe(result.returns)
        expected = EXPECTED[key]
        match = abs(got - expected) < 0.002
        ok &= match
        print(f"  {key:16s} rebuilt {got:.3f}  journalled {expected:.3f}  "
              f"{'MATCH' if match else 'MISMATCH'}")
    if not ok:
        print("\nreconstruction does not match the journal — NOTHING written")
        return 1

    REPORTS.mkdir(exist_ok=True)
    summary: dict[str, dict] = {}
    for key, result in results.items():
        path = save_tear_sheet(result, REPORTS / f"{key}.png", title=TITLES[key])
        stats_row = metrics.summarize(result.returns, result.turnover)
        equity = result.equity
        # month-end sample keeps the JSON small enough to hand to a viewer
        monthly = equity.resample("ME").last().dropna()
        summary[key] = {
            "title": TITLES[key],
            "start": str(result.returns.index[0].date()),
            "end": str(result.returns.index[-1].date()),
            "bars": int(len(result.returns)),
            "metrics": {k: float(v) for k, v in stats_row.items()},
            "equity_dates": [str(d.date()) for d in monthly.index],
            "equity_values": [round(float(v), 6) for v in monthly.values],
        }
        print(f"  wrote {path.relative_to(ROOT)}")

    (REPORTS / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  wrote {(REPORTS / 'summary.json').relative_to(ROOT)}")
    print(f"\n{len(results)} tear sheets + summary.json in reports/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
