"""trend-v9-leverage — measurement overlay, not a tradeable strategy.
Pre-registered: journal/2026-09-02-trend-v9-leverage-preregistration.md
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
import numpy as np
import pandas as pd

from woodland import backtest, cash, data, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import splits as sp
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import (
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    MULTI_ASSET,
    PRIMARY_COST,
    VOL_TARGET_ANN,
    VOL_TARGET_WINDOW,
    stitch,
)

PRIMARY = MULTI_ASSET
CAPS = [1.0, 2.0, 3.0]
SPREADS_BPS = [0.0, 100.0]
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)


def lever(
    r: pd.Series, rf: pd.Series, cap: float, spread_bps: float
) -> tuple[pd.Series, pd.Series]:
    """Vol-target with borrowing. Trailing 63d vol, lagged one bar (no lookahead)."""
    rv = r.rolling(VOL_TARGET_WINDOW).std().shift(1) * np.sqrt(252)
    k = (VOL_TARGET_ANN / rv).clip(upper=cap)
    k = k.where(rv.notna())  # warm-up: no scaling decision yet
    k = k.fillna(1.0).clip(lower=0.0)
    borrow = np.maximum(k - 1.0, 0.0) * (spread_bps / 1e4) / 252.0
    lev = rf + k * (r - rf) - borrow
    return lev.rename(r.name), k


cfg = load_config()
store = ROOT / cfg["data"]["store"]
prices = data.build_matrix(all_tickers(cfg), store)
prices, _ = data.drop_suspect_dates(prices)
idx = pd.DatetimeIndex(prices.index)
folds = sp.make_splits(
    idx, train_years=5, validate_years=1, step_years=1, embargo_days=MAX_LOOKBACK_DAYS
)
w = [f.validate_index(idx) for f in folds]
lo, hi = min(x[0] for x in w if len(x)), max(x[-1] for x in w if len(x))

tg = trend.ensemble_targets(prices, risk_assets=PRIMARY, risk_off=None, lookback_months=LOOKBACKS)
v6 = backtest.run(prices, stitch(prices, tg, folds), cost_bps=PRIMARY_COST).returns.loc[lo:hi]
mix_t = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
mix = backtest.run(prices, mix_t, cost_bps=PRIMARY_COST).returns.loc[lo:hi]
vt_t = vol_target_targets(prices, mix_t, window=VOL_TARGET_WINDOW, target_ann_vol=VOL_TARGET_ANN)
vtmix = backtest.run(prices, vt_t, cost_bps=PRIMARY_COST).returns.loc[lo:hi]

rf_raw = cash.load_risk_free_daily(store)
rf, _ = cash.align_risk_free(rf_raw, pd.DatetimeIndex(v6.index))
base = {"v6_multiasset": v6, "60/40": mix, "vt_60/40": vtmix}

print(
    f"OOS {lo.date()}..{hi.date()}  {len(v6)} bars  "
    f"cost {PRIMARY_COST:.0f}bps  target vol {VOL_TARGET_ANN:.0%}"
)
print("\n=== UNLEVERED REFERENCE (regression check: cap=1.0, spread=0 must match) ===")
print(pd.DataFrame({k: metrics.summarize(v) for k, v in base.items()}).T.round(4).to_string())

rows = []
series = {}
for name, r in base.items():
    for cap in CAPS:
        for sp_bps in SPREADS_BPS:
            lv, k = lever(r, rf, cap, sp_bps)
            key = f"{name}|L={cap:.0f}|s={sp_bps:.0f}"
            series[key] = lv
            m = metrics.summarize(lv)
            rows.append(
                {
                    "series": name,
                    "cap": cap,
                    "spread_bps": sp_bps,
                    "sharpe_rf0": metrics.sharpe(lv),
                    "sharpe_real_rf": metrics.sharpe(lv, float(rf.mean() * 252)),
                    "cagr": m["cagr"],
                    "ann_vol": m["ann_vol"],
                    "max_dd": m["max_drawdown"],
                    "worst_day": float(lv.min()),
                    "k_mean": float(k.mean()),
                    "k_med": float(k.median()),
                    "k_p95": float(k.quantile(0.95)),
                    "pct_at_cap": float((k >= cap - 1e-9).mean()),
                }
            )
res = pd.DataFrame(rows)
print("\n=== LEVERED RESULTS ===")
print(res.round(4).to_string(index=False))

print("\n=== PAIRED: strategy vs baseline, LEVERED-vs-LEVERED (same cap & spread) ===")
out = []
for cap in CAPS:
    for sp_bps in SPREADS_BPS:
        a = series[f"v6_multiasset|L={cap:.0f}|s={sp_bps:.0f}"]
        for comp in ["60/40", "vt_60/40"]:
            b = series[f"{comp}|L={cap:.0f}|s={sp_bps:.0f}"]
            bs = stats.bootstrap_sharpe_difference(
                a, b, name_a="v6", name_b=comp, block_length=21, n_resamples=10000
            )
            d = bs.__dict__ if hasattr(bs, "__dict__") else {}
            out.append(
                {
                    "cap": cap,
                    "spread_bps": sp_bps,
                    "vs": comp,
                    "delta": metrics.sharpe(a) - metrics.sharpe(b),
                    "ci_low": d.get("ci_low"),
                    "ci_high": d.get("ci_high"),
                    "p": d.get("p_value"),
                    "corr": float(a.corr(b)),
                }
            )
print(pd.DataFrame(out).round(4).to_string(index=False))
