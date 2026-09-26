"""Performance metrics. Reported side-by-side with baselines, always (DESIGN.md §9)."""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def cagr(returns: pd.Series) -> float:
    r = returns.dropna()
    if r.empty:
        return float("nan")
    total = float(cast(float, (1 + r).prod()))
    years = len(r) / TRADING_DAYS
    return total ** (1 / years) - 1 if years > 0 and total > 0 else float("nan")


def ann_vol(returns: pd.Series) -> float:
    return float(returns.dropna().std() * np.sqrt(TRADING_DAYS))


def excess_returns(returns: pd.Series, rf_daily: pd.Series) -> pd.Series:
    """Returns net of a time-varying daily risk-free rate, on shared dates."""
    aligned = pd.DataFrame({"r": returns, "rf": rf_daily}).dropna()
    return aligned["r"] - aligned["rf"]


def sharpe(
    returns: pd.Series,
    rf_annual: float = 0.0,
    rf_daily: pd.Series | None = None,
) -> float:
    """Sharpe on daily returns vs a risk-free rate.

    `rf_daily` is the honest version: a real, time-varying short rate. The
    constant `rf_annual` (default 0) is kept because the journalled record was
    computed at rf=0 and must stay reproducible — but rf=0 overstates Sharpe
    in high-rate regimes, so no number leaves this repo on it unqualified.
    """
    if rf_daily is not None:
        r = excess_returns(returns, rf_daily)
    else:
        r = returns.dropna() - rf_annual / TRADING_DAYS
    sd = r.std()
    return float(r.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def max_drawdown(returns: pd.Series) -> float:
    eq = (1 + returns.dropna()).cumprod()
    dd = eq / eq.cummax() - 1
    return float(dd.min())


def drawdown_duration_days(returns: pd.Series) -> int:
    """Longest stretch (trading days) below a prior equity high."""
    eq = (1 + returns.dropna()).cumprod()
    at_high = eq >= eq.cummax() - 1e-12
    longest = current = 0
    for ok in at_high:
        current = 0 if ok else current + 1
        longest = max(longest, current)
    return longest


def hit_rate(returns: pd.Series, freq: str = "ME") -> float:
    """Fraction of positive periods at the given resample frequency."""
    per = (1 + returns.dropna()).resample(freq).prod() - 1
    per = per[per != 0]
    return float((per > 0).mean()) if len(per) else float("nan")


def ann_turnover(turnover: pd.Series) -> float:
    t = turnover.dropna()
    years = len(t) / TRADING_DAYS
    return float(t.sum() / years) if years > 0 else float("nan")


def summarize(
    returns: pd.Series,
    turnover: pd.Series | None = None,
    rf_daily: pd.Series | None = None,
) -> dict:
    """Summary statistics. Supplying `rf_daily` adds `sharpe_rf` beside the
    rf=0 figure rather than replacing it, so old and new are always visible
    together."""
    out = {
        "cagr": cagr(returns),
        "ann_vol": ann_vol(returns),
        "sharpe_rf0": sharpe(returns),
        "max_drawdown": max_drawdown(returns),
        "dd_duration_days": drawdown_duration_days(returns),
        "hit_rate_monthly": hit_rate(returns),
    }
    if rf_daily is not None:
        out["sharpe_rf"] = sharpe(returns, rf_daily=rf_daily)
    if turnover is not None:
        out["ann_turnover"] = ann_turnover(turnover)
    return out


def by_subperiod(returns: pd.Series, breaks: list[str] | None = None) -> pd.DataFrame:
    """Regime honesty (DESIGN.md §7): metrics per sub-period, not one blended number."""
    breaks = breaks or ["2008-01-01", "2015-01-01", "2020-01-01", "2022-01-01"]
    edges = [returns.index[0], *[pd.Timestamp(b) for b in breaks], returns.index[-1]]
    rows = {}
    for a, b in zip(edges[:-1], edges[1:], strict=False):
        chunk = returns.loc[a:b]
        if len(chunk) > TRADING_DAYS // 2:
            rows[f"{a.date()}..{b.date()}"] = summarize(chunk)
    return pd.DataFrame(rows).T


def compare(
    named_results: dict[str, pd.Series], rf_daily: pd.Series | None = None
) -> pd.DataFrame:
    """Side-by-side summary table for {name: daily returns}."""
    return pd.DataFrame(
        {k: summarize(v, rf_daily=rf_daily) for k, v in named_results.items()}
    ).T
