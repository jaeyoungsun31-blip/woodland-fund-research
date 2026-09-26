"""Portfolio-level Fama-MacBeth cross-sectional prediction tests."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass(frozen=True)
class FamaMacBethResult:
    slopes: pd.Series
    mean_slope_daily: float
    mean_slope_annual: float
    standard_error_daily: float
    standard_error_annual: float
    t_statistic: float
    p_value: float
    fraction_positive: float
    n_periods: int
    n_assets: int
    nw_lags: int


def newey_west_mean_standard_error(values: pd.Series, *, lags: int = 21) -> float:
    """Newey-West standard error of a dependent sample mean."""
    clean = values.dropna().to_numpy(dtype=float)
    if len(clean) < 2:
        raise ValueError("need at least two observations")
    if not 0 <= lags < len(clean):
        raise ValueError("lags must be in [0, n-1)")
    centred = clean - clean.mean()
    n = len(clean)
    long_run_variance = float(centred @ centred / n)
    for lag in range(1, lags + 1):
        covariance = float(centred[lag:] @ centred[:-lag] / n)
        long_run_variance += 2.0 * (1.0 - lag / (lags + 1.0)) * covariance
    return math.sqrt(max(long_run_variance, 0.0) / n)


def fama_macbeth(
    forward_returns: pd.DataFrame,
    characteristic: pd.DataFrame | pd.Series,
    *,
    nw_lags: int = 21,
) -> FamaMacBethResult:
    """Run one cross-sectional OLS per period and HAC-test the average slope.

    Characteristics are standardized separately in every period before the
    regression, so the slope is return per one cross-sectional standard
    deviation of the characteristic.
    """
    if isinstance(characteristic, pd.Series):
        missing = forward_returns.columns.difference(characteristic.index)
        if len(missing):
            raise ValueError(f"characteristic missing assets: {list(missing)}")
        raw_x = pd.DataFrame(
            np.tile(
                characteristic.reindex(forward_returns.columns).to_numpy(dtype=float),
                (len(forward_returns), 1),
            ),
            index=forward_returns.index,
            columns=forward_returns.columns,
        )
    else:
        raw_x = characteristic.reindex(
            index=forward_returns.index, columns=forward_returns.columns
        )
    slopes: dict[pd.Timestamp, float] = {}
    for date in forward_returns.index:
        cross_section = pd.DataFrame(
            {"y": forward_returns.loc[date], "x": raw_x.loc[date]}
        ).dropna()
        if len(cross_section) < 3:
            continue
        x = cross_section["x"].to_numpy(dtype=float)
        y = cross_section["y"].to_numpy(dtype=float)
        x_sd = float(x.std(ddof=1))
        if x_sd <= 0.0:
            continue
        standardized = (x - x.mean()) / x_sd
        denominator = float(standardized @ standardized)
        slopes[pd.Timestamp(date)] = float(
            standardized @ (y - y.mean()) / denominator
        )
    slope_series = pd.Series(slopes, name="fama_macbeth_slope", dtype=float)
    if len(slope_series) <= nw_lags:
        raise ValueError("not enough period slopes for the requested Newey-West lags")
    mean_daily = float(slope_series.mean())
    se_daily = newey_west_mean_standard_error(slope_series, lags=nw_lags)
    t_stat = mean_daily / se_daily if se_daily > 0.0 else float("inf")
    p_value = 2.0 * (1.0 - NormalDist().cdf(abs(t_stat)))
    return FamaMacBethResult(
        slopes=slope_series,
        mean_slope_daily=mean_daily,
        mean_slope_annual=mean_daily * TRADING_DAYS,
        standard_error_daily=se_daily,
        standard_error_annual=se_daily * TRADING_DAYS,
        t_statistic=t_stat,
        p_value=p_value,
        fraction_positive=float((slope_series > 0.0).mean()),
        n_periods=len(slope_series),
        n_assets=int(forward_returns.shape[1]),
        nw_lags=nw_lags,
    )
