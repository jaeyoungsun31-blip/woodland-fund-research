"""xsmom-v10-industry — cross-sectional momentum on FF 12 industries.
Pre-registered: journal/2026-09-02-xsmom-v10-preregistration.md
Embargo amended to 252 bars for this study (declared in advance).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
import numpy as np
import pandas as pd

from woodland import backtest, cash, metrics, stats
from woodland.config import ROOT
from woodland.fama_french import INDUSTRIES
from woodland.harness import splits as sp
from woodland.study import stitch

FORM, SKIP, K, COST = 252, 21, 3, 5.0
EMBARGO = 252
pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)

ind = pd.read_parquet(ROOT / "data" / "fama_french_12_industry_daily.parquet")
fac = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
prices = ind.join(fac, how="inner")
idx = pd.DatetimeIndex(prices.index)
IND = list(INDUSTRIES)


def month_ends(index):
    return pd.DatetimeIndex(index.to_series().groupby(index.to_period("M")).max())


def xsmom_targets(prices, k=K):
    """Rank on cumulative return t-252..t-21 (12-1). Uses only data <= t."""
    px = prices[IND]
    mom = px.shift(SKIP) / px.shift(FORM) - 1.0  # both lags backward-looking
    tgt = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for d in month_ends(idx):
        row = mom.loc[d].dropna()
        if len(row) < len(IND):
            continue
        win = row.nlargest(k).index
        w = pd.Series(0.0, index=prices.columns)
        w[win] = 1.0 / k
        tgt.loc[d] = w
    return tgt


def ew_targets(prices):
    tgt = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    first = prices[IND].dropna().index[0]
    for d in month_ends(idx):
        if d < first:
            continue
        w = pd.Series(0.0, index=prices.columns)
        w[IND] = 1.0 / len(IND)
        tgt.loc[d] = w
    return tgt


folds = sp.make_splits(idx, train_years=5, validate_years=1, step_years=1, embargo_days=EMBARGO)
wins = [f.validate_index(idx) for f in folds]
lo, hi = min(w[0] for w in wins if len(w)), max(w[-1] for w in wins if len(w))
print(
    f"OOS {lo.date()}..{hi.date()}  {len(prices.loc[lo:hi])} bars  "
    f"{len(folds)} folds  embargo {EMBARGO}  cost {COST:.0f}bps"
)

xs = backtest.run(prices, stitch(prices, xsmom_targets(prices), folds), cost_bps=COST)
ew = backtest.run(prices, stitch(prices, ew_targets(prices), folds), cost_bps=COST)
mkt = backtest.buy_and_hold(prices, "MKT")
mix = backtest.run(
    prices, backtest.fixed_mix_targets(prices, {"MKT": 0.6, "CASH": 0.4}), cost_bps=COST
)

S = {"xsmom_top3": xs, "ew_12_industries": ew, "MKT": mkt, "60/40_MKT_CASH": mix}
R = {k: v.returns.loc[lo:hi] for k, v in S.items()}
T = {k: v.turnover.loc[lo:hi] for k, v in S.items()}
rf_raw = cash.load_risk_free_daily(ROOT / "data")
rf, _ = cash.align_risk_free(rf_raw, pd.DatetimeIndex(R["MKT"].index))
rf_ann = float(rf.mean() * 252)

print("\n=== PERFORMANCE (5 bps) ===")
rows = {}
for k, r in R.items():
    m = metrics.summarize(r, T[k])
    m["sharpe_real_rf"] = metrics.sharpe(r, rf_ann)
    m["worst_day"] = float(r.min())
    rows[k] = m
print(pd.DataFrame(rows).T.round(4).to_string())

print("\n=== COST SCENARIOS: xsmom top3 Sharpe ===")
for c in (0.0, 5.0, 10.0):
    rr = backtest.run(prices, stitch(prices, xsmom_targets(prices), folds), cost_bps=c).returns.loc[
        lo:hi
    ]
    print(f"  {c:>4.0f} bps  sharpe_rf0 {metrics.sharpe(rr):.4f}   cagr {metrics.cagr(rr):.4%}")

print("\n=== PAIRED INFERENCE: xsmom top3 vs baselines (5 bps) ===")
out = []
for name in ["ew_12_industries", "MKT", "60/40_MKT_CASH"]:
    a, b = R["xsmom_top3"], R[name]
    bs = stats.bootstrap_sharpe_difference(
        a, b, name_a="xsmom", name_b=name, block_length=21, n_resamples=10000
    )
    d = bs.__dict__ if hasattr(bs, "__dict__") else {}
    hac = stats.ledoit_wolf_sharpe_test(a, b, name_a="xsmom", name_b=name)
    h = hac.__dict__ if hasattr(hac, "__dict__") else {}
    out.append(
        {
            "vs": name,
            "delta": metrics.sharpe(a) - metrics.sharpe(b),
            "ci_low": d.get("ci_low"),
            "ci_high": d.get("ci_high"),
            "p_boot": d.get("p_value"),
            "p_hac": h.get("p_value"),
            "corr": float(a.corr(b)),
        }
    )
print(pd.DataFrame(out).round(4).to_string(index=False))

print("\n=== BY DECADE (xsmom top3 @5bps) ===")
yrs = pd.DatetimeIndex(R["xsmom_top3"].index).year
dec = {}
for d, ch in R["xsmom_top3"].groupby((yrs // 10) * 10):
    if len(ch) > 126:
        dec[f"{d}s"] = metrics.summarize(ch)
print(pd.DataFrame(dec).T.round(4).to_string())

print("\n=== PRE/POST 1980 (paired vs each baseline) ===")
o2 = []
for lbl, sl in [("1932-1979", slice(None, "1979-12-31")), ("1980-2026", slice("1980-01-01", None))]:
    for name in ["ew_12_industries", "MKT"]:
        a, b = R["xsmom_top3"].loc[sl], R[name].loc[sl]
        if len(a) < 500:
            continue
        bs = stats.bootstrap_sharpe_difference(
            a, b, name_a="xsmom", name_b=name, block_length=21, n_resamples=10000
        )
        d = bs.__dict__ if hasattr(bs, "__dict__") else {}
        o2.append(
            {
                "era": lbl,
                "vs": name,
                "years": round(len(a) / 252, 1),
                "sharpe_xsmom": metrics.sharpe(a),
                "sharpe_base": metrics.sharpe(b),
                "delta": metrics.sharpe(a) - metrics.sharpe(b),
                "ci_low": d.get("ci_low"),
                "ci_high": d.get("ci_high"),
                "p": d.get("p_value"),
            }
        )
print(pd.DataFrame(o2).round(4).to_string(index=False))
