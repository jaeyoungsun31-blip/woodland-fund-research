"""Statistical inference over the EXISTING trend studies (HANDOFF 2026-09-01c step 2).

Runs no new study and writes no ledger rows. v2 and v3 each have a single
pre-registered configuration, so their stitched out-of-sample series are fully
determined by the frozen split scheme and can be rebuilt exactly — the
reconstruction is checked against the Sharpe ratios already journalled before
any inference is reported.

Usage:  python scripts/run_inference.py [--resamples 10000] [--block 21]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, data, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import splits as sp
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
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
VOL_WINDOW, TARGET_ANN_VOL = 63, 0.10
COST = 5.0

# Journalled at 5 bps; the reconstruction must reproduce these or the
# inference below would be describing a different portfolio.
EXPECTED = {"v2": 0.700, "v3": 0.709, "SPY": 0.660, "60/40": 0.806, "vt6040": 0.853}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument("--block", type=int, default=stats.DEFAULT_BLOCK_LENGTH)
    args = parser.parse_args()

    cfg = load_config()
    prices = data.build_matrix(all_tickers(cfg), ROOT / cfg["data"]["store"])
    prices, _ = data.drop_suspect_dates(prices)
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=MAX_LOOKBACK_DAYS)
    windows = [f.validate_index(index) for f in folds]
    lo = min(w[0] for w in windows if len(w))
    hi = max(w[-1] for w in windows if len(w))

    base = trend.ensemble_targets(prices, risk_assets=SECTORS,
                                  risk_off=RISK_OFF, lookback_months=LOOKBACKS)
    v2 = backtest.run(prices, stitch(prices, base, folds), cost_bps=COST).returns.loc[lo:hi]

    vt = vol_target_targets(prices, base, window=VOL_WINDOW, target_ann_vol=TARGET_ANN_VOL)
    v3 = backtest.run(prices, stitch(prices, vt, folds), cost_bps=COST).returns.loc[lo:hi]

    spy = backtest.buy_and_hold(prices, "SPY").returns.loc[lo:hi]
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    mix = backtest.run(prices, mix_targets, cost_bps=COST).returns.loc[lo:hi]
    vt_mix_targets = vol_target_targets(prices, mix_targets, window=VOL_WINDOW,
                                        target_ann_vol=TARGET_ANN_VOL)
    vt_mix = backtest.run(prices, vt_mix_targets, cost_bps=COST).returns.loc[lo:hi]

    series = {"v2": v2, "v3": v3, "SPY": spy, "60/40": mix, "vt6040": vt_mix}

    print(f"OOS window {lo.date()} .. {hi.date()}  ({len(v2)} bars)  cost {int(COST)} bps")
    print("\n=== reconstruction check against journalled Sharpes ===")
    ok = True
    for key, expected in EXPECTED.items():
        got = metrics.sharpe(series[key])
        match = abs(got - expected) < 0.002
        ok &= match
        print(f"  {key:8s} rebuilt {got:.3f}  journalled {expected:.3f}  "
              f"{'MATCH' if match else 'MISMATCH'}")
    if not ok:
        print("\nreconstruction does not match the journal — inference NOT reported")
        return 1

    print("\n=== Sharpe with 95% bootstrap confidence intervals ===")
    for name, r in series.items():
        point, low, high = stats.sharpe_confidence_interval(
            r, block_length=args.block, n_resamples=args.resamples)
        print(f"  {name:8s} {point:.3f}   95% CI [{low:.3f}, {high:.3f}]   width {high-low:.3f}")

    comparisons = [
        ("v2 ensemble", "60/40", "v2", "60/40"),
        ("v2 ensemble", "SPY buy&hold", "v2", "SPY"),
        ("v3 voltarget", "vol-target 60/40", "v3", "vt6040"),
    ]
    print("\n=== Sharpe differences ===")
    for label_a, label_b, key_a, key_b in comparisons:
        a, b = series[key_a], series[key_b]
        print(f"\n--- {label_a} vs {label_b}  (correlation {a.corr(b):.3f})")
        for result in (
            stats.bootstrap_sharpe_difference(a, b, name_a=label_a, name_b=label_b,
                                              block_length=args.block,
                                              n_resamples=args.resamples),
            stats.ledoit_wolf_sharpe_test(a, b, name_a=label_a, name_b=label_b),
            stats.iid_sharpe_test(a, b, name_a=label_a, name_b=label_b),
        ):
            print(result.summary())
    print("\nInference only; no ledger rows written and nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
