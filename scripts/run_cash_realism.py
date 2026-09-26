"""Cash realism: what changes when the uninvested sleeve earns the T-bill rate.

No new study and no ledger rows. v2 and v3 each have a single pre-registered
configuration, so their stitched OOS series are determined by the frozen split
scheme and are rebuilt exactly; the rebuild is checked against the journalled
Sharpes under the OLD rule before any comparison is reported.

Reports two distinct changes, kept separate because they are separate:
  (a) the RETURN SERIES change — cash earns rf instead of zero;
  (b) the METRIC change — Sharpe measured against rf instead of against zero.

Usage:  python scripts/run_cash_realism.py [--resamples 10000]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, cash, data, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import splits as sp
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import LOOKBACKS, MAX_LOOKBACK_DAYS, SECTORS, stitch

RISK_OFF = "IEF"
VOL_WINDOW, TARGET_ANN_VOL = 63, 0.10
COST = 5.0

# Journalled under the old rule (cash earns 0, Sharpe vs rf=0).
JOURNALLED = {"v2": 0.700, "v3": 0.709, "60/40": 0.806, "vt6040": 0.853}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    args = parser.parse_args()

    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    prices, _ = data.drop_suspect_dates(data.build_matrix(all_tickers(cfg), store))
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=5, validate_years=1, step_years=1,
                           embargo_days=MAX_LOOKBACK_DAYS)
    windows = [f.validate_index(index) for f in folds]
    lo = min(w[0] for w in windows if len(w))
    hi = max(w[-1] for w in windows if len(w))

    rf_daily, prov = cash.align_risk_free(cash.load_risk_free_daily(store), index)
    print("=== risk-free series ===")
    print(json.dumps(prov, indent=2))
    rf_oos = rf_daily.loc[lo:hi]
    print(f"over the OOS window: mean {rf_oos.mean()*252:.2%} annualized, "
          f"compounding to {float((1 + rf_oos).prod()) - 1:.2%} cumulative")

    base = trend.ensemble_targets(prices, risk_assets=SECTORS,
                                  risk_off=RISK_OFF, lookback_months=LOOKBACKS)
    vt = vol_target_targets(prices, base, window=VOL_WINDOW,
                            target_ann_vol=TARGET_ANN_VOL)
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    vt_mix_targets = vol_target_targets(prices, mix_targets, window=VOL_WINDOW,
                                        target_ann_vol=TARGET_ANN_VOL)

    plans = {
        "v2": stitch(prices, base, folds),
        "v3": stitch(prices, vt, folds),
        "60/40": mix_targets,
        "vt6040": vt_mix_targets,
    }

    old = {k: backtest.run(prices, t, cost_bps=COST).returns.loc[lo:hi]
           for k, t in plans.items()}
    new = {k: backtest.run(prices, t, cost_bps=COST, risk_free=rf_daily).returns.loc[lo:hi]
           for k, t in plans.items()}
    spy_old = backtest.buy_and_hold(prices, "SPY").returns.loc[lo:hi]
    spy_new = backtest.buy_and_hold(prices, "SPY", risk_free=rf_daily).returns.loc[lo:hi]

    print("\n=== reconstruction check against the journalled record (old rule) ===")
    ok = True
    for key, expected in JOURNALLED.items():
        got = metrics.sharpe(old[key])
        match = abs(got - expected) < 0.002
        ok &= match
        print(f"  {key:8s} rebuilt {got:.3f}  journalled {expected:.3f}  "
              f"{'MATCH' if match else 'MISMATCH'}")
    if not ok:
        print("\nreconstruction does not match the journal — nothing reported")
        return 1

    print("\n=== average cash weight over the OOS window ===")
    for key, targets in plans.items():
        held = backtest.run(prices, targets, cost_bps=COST).holdings.loc[lo:hi]
        print(f"  {key:8s} {1 - float(held.sum(axis=1).mean()):.3%}")

    print("\n=== (a) return-series change: cash earns rf instead of 0 ===")
    print(f"{'series':10s} {'CAGR old':>9s} {'CAGR new':>9s} "
          f"{'SR_rf0 old':>11s} {'SR_rf0 new':>11s} {'delta':>7s}")
    for key in [*plans, "SPY"]:
        o = spy_old if key == "SPY" else old[key]
        n = spy_new if key == "SPY" else new[key]
        print(f"{key:10s} {metrics.cagr(o):9.2%} {metrics.cagr(n):9.2%} "
              f"{metrics.sharpe(o):11.3f} {metrics.sharpe(n):11.3f} "
              f"{metrics.sharpe(n) - metrics.sharpe(o):+7.3f}")

    print("\n=== (b) metric change: Sharpe vs rf=0 and vs the real rf ===")
    print("    (both computed on the NEW, cash-earning series)")
    named = {**{k: new[k] for k in plans}, "SPY": spy_new}
    print(metrics.compare(named, rf_daily=rf_daily)[
        ["cagr", "ann_vol", "sharpe_rf0", "sharpe_rf", "max_drawdown"]].round(4).to_string())

    print(f"\n=== paired differences, before and after "
          f"({args.resamples} resamples, block {stats.DEFAULT_BLOCK_LENGTH}) ===")
    comparisons = [("v2 ensemble", "v2", "60/40", "60/40"),
                   ("v3 voltarget", "v3", "vol-target 60/40", "vt6040")]
    for label_a, key_a, label_b, key_b in comparisons:
        print(f"\n--- {label_a} vs {label_b}")
        for tag, series, rf_arg in (
            ("OLD (cash=0, SR vs rf=0)", old, None),
            ("NEW (cash=rf, SR vs rf=0)", new, None),
            ("NEW (cash=rf, SR vs real rf)", new, rf_daily),
        ):
            a, b = series[key_a], series[key_b]
            if rf_arg is not None:
                a = metrics.excess_returns(a, rf_arg)
                b = metrics.excess_returns(b, rf_arg)
            result = stats.bootstrap_sharpe_difference(
                a, b, name_a=label_a, name_b=label_b, n_resamples=args.resamples)
            hac = stats.ledoit_wolf_sharpe_test(a, b, name_a=label_a, name_b=label_b)
            print(f"  {tag:30s} d {result.difference:+.3f}  "
                  f"CI [{result.ci_low:+.3f}, {result.ci_high:+.3f}]  "
                  f"p {result.p_value:.3f} (HAC {hac.p_value:.3f})")

    print("\nNo ledger rows written; nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
