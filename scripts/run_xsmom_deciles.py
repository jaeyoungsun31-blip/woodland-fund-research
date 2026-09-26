"""xsmom-v11-deciles — stock-level cross-sectional momentum (FF 10 prior-return deciles)."""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
import numpy as np
import pandas as pd

from woodland import backtest, cash, metrics, stats
from woodland.config import ROOT
from woodland.harness import splits as sp
from woodland.study import stitch

pd.set_option("display.width", 210)
pd.set_option("display.max_columns", 60)
COST, EMBARGO = 5.0, 252


def parse_ff(path, start_line, end_line):
    rows = []
    with open(path) as f:
        lines = f.readlines()
    hdr = [c.strip() for c in lines[start_line].split(",")][1:]
    for ln in lines[start_line + 1 : end_line]:
        p = ln.strip().split(",")
        if len(p) < 2 or not p[0].strip().isdigit() or len(p[0].strip()) != 8:
            continue
        vals = [float(x) for x in p[1 : len(hdr) + 1]]
        rows.append([pd.Timestamp(p[0].strip())] + vals)
    df = pd.DataFrame(rows, columns=["Date"] + hdr).set_index("Date").sort_index()
    return df.replace([-99.99, -999], np.nan) / 100.0


rets = parse_ff("raw/10_Portfolios_Prior_12_2_Daily.csv", 9, 26184)
rets = rets.dropna()
DEC = list(rets.columns)
print(f"deciles: {DEC}\nrows {len(rets)}  {rets.index[0].date()}..{rets.index[-1].date()}")

lev = (1 + rets).cumprod() * 100.0
fac = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
prices = lev.join(fac, how="inner")
idx = pd.DatetimeIndex(prices.index)


def month_ends(i):
    return pd.DatetimeIndex(i.to_series().groupby(i.to_period("M")).max())


def fixed(cols_w):
    t = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for d in month_ends(idx):
        w = pd.Series(0.0, index=prices.columns)
        for c, x in cols_w.items():
            w[c] = x
        t.loc[d] = w
    return t


folds = sp.make_splits(idx, train_years=5, validate_years=1, step_years=1, embargo_days=EMBARGO)
wins = [f.validate_index(idx) for f in folds]
lo, hi = min(w[0] for w in wins if len(w)), max(w[-1] for w in wins if len(w))
print(f"OOS {lo.date()}..{hi.date()}  {len(prices.loc[lo:hi])} bars  {len(folds)} folds\n")

HI, LO3 = DEC[-1], DEC[0]
TOP3 = {c: 1 / 3 for c in DEC[-3:]}
EW10 = {c: 0.1 for c in DEC}
strats = {
    "top_decile": fixed({HI: 1.0}),
    "top3_deciles": fixed(TOP3),
    "EW_10_deciles": fixed(EW10),
    "MKT": fixed({"MKT": 1.0}),
    "60/40_MKT_CASH": fixed({"MKT": 0.6, "CASH": 0.4}),
}
R = {}
T = {}
for k, t in strats.items():
    r = backtest.run(prices, stitch(prices, t, folds), cost_bps=COST)
    R[k] = r.returns.loc[lo:hi]
    T[k] = r.turnover.loc[lo:hi]
# long-short factor: Hi - Lo, unlevered, cash-collateralised
R["LS_hi_minus_lo"] = (rets[HI] - rets[LO3]).loc[lo:hi]
T["LS_hi_minus_lo"] = pd.Series(0.0, index=R["LS_hi_minus_lo"].index)

rf_raw = cash.load_risk_free_daily(ROOT / "data")
rf, _ = cash.align_risk_free(rf_raw, pd.DatetimeIndex(R["MKT"].index))
rf_ann = float(rf.mean() * 252)
print("=== PERFORMANCE (5 bps on the decile-level rebalance only) ===")
rows = {}
for k, r in R.items():
    m = metrics.summarize(r, T[k])
    m["sharpe_real_rf"] = metrics.sharpe(r, rf_ann)
    m["worst_day"] = float(r.min())
    m["skew"] = float(r.skew())
    m["exkurt"] = float(r.kurtosis())
    rows[k] = m
print(pd.DataFrame(rows).T.round(4).to_string())

print("\n=== PAIRED INFERENCE (5 bps) ===")
pairs = [
    ("top_decile", "EW_10_deciles"),
    ("top_decile", "MKT"),
    ("top_decile", "60/40_MKT_CASH"),
    ("top3_deciles", "EW_10_deciles"),
    ("EW_10_deciles", "MKT"),
]
out = []
for a_, b_ in pairs:
    a, b = R[a_], R[b_]
    bs = stats.bootstrap_sharpe_difference(
        a, b, name_a=a_, name_b=b_, block_length=21, n_resamples=10000
    )
    d = bs.__dict__ if hasattr(bs, "__dict__") else {}
    h = stats.ledoit_wolf_sharpe_test(a, b, name_a=a_, name_b=b_)
    hh = h.__dict__ if hasattr(h, "__dict__") else {}
    out.append(
        {
            "challenger": a_,
            "vs": b_,
            "delta": metrics.sharpe(a) - metrics.sharpe(b),
            "ci_low": d.get("ci_low"),
            "ci_high": d.get("ci_high"),
            "p_boot": d.get("p_value"),
            "p_hac": hh.get("p_value"),
            "corr": float(a.corr(b)),
        }
    )
print(pd.DataFrame(out).round(4).to_string(index=False))

print("\n=== ERA SPLIT: top_decile vs EW_10_deciles ===")
o2 = []
for lbl, sl in [("1932-1979", slice(None, "1979-12-31")), ("1980-2026", slice("1980-01-01", None))]:
    a, b = R["top_decile"].loc[sl], R["EW_10_deciles"].loc[sl]
    bs = stats.bootstrap_sharpe_difference(
        a, b, name_a="top", name_b="ew", block_length=21, n_resamples=10000
    )
    d = bs.__dict__ if hasattr(bs, "__dict__") else {}
    o2.append(
        {
            "era": lbl,
            "years": round(len(a) / 252, 1),
            "sharpe_top": metrics.sharpe(a),
            "sharpe_ew": metrics.sharpe(b),
            "delta": metrics.sharpe(a) - metrics.sharpe(b),
            "ci_low": d.get("ci_low"),
            "ci_high": d.get("ci_high"),
            "p": d.get("p_value"),
        }
    )
print(pd.DataFrame(o2).round(4).to_string(index=False))

print("\n=== DECILE MONOTONICITY (annualised, full OOS) — is the sort real? ===")
mono = {}
for c in DEC:
    r = backtest.run(prices, stitch(prices, fixed({c: 1.0}), folds), cost_bps=COST).returns.loc[
        lo:hi
    ]
    mono[c] = {
        "cagr": metrics.cagr(r),
        "vol": metrics.ann_vol(r),
        "sharpe": metrics.sharpe(r),
        "maxdd": metrics.max_drawdown(r),
    }
print(pd.DataFrame(mono).T.round(4).to_string())
