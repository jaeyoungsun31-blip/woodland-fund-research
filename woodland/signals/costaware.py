"""The six frozen v16 features and closed-form temporal ridge estimator."""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ("mom_12_2", "rev_1m", "rev_1w", "vol_63", "volvol_63", "dd_252")
GRID = tuple((a, lam) for a in (0.01, 0.1, 1.0, 10.0) for lam in (0.0, 0.5, 2.0, 8.0))


def features(returns: pd.DataFrame, eligible: pd.DataFrame) -> np.ndarray:
    log = pd.DataFrame(np.log1p(returns.to_numpy()), index=returns.index, columns=returns.columns)
    # Internal cumulative log sums cancel in ratios. They are never price bars.
    cumulative = log.fillna(0).cumsum()
    dd = pd.DataFrame(
        np.expm1((cumulative - cumulative.rolling(252, min_periods=252).max()).to_numpy()),
        index=returns.index,
        columns=returns.columns,
    )
    dd = dd.where(returns.notna().rolling(251).sum() == 251)
    raw = [
        pd.DataFrame(
            np.expm1((log.rolling(231).sum().shift(21)).to_numpy()),
            index=returns.index,
            columns=returns.columns,
        ),
        pd.DataFrame(
            np.expm1((log.rolling(21).sum()).to_numpy()),
            index=returns.index,
            columns=returns.columns,
        ),
        pd.DataFrame(
            np.expm1((log.rolling(5).sum()).to_numpy()),
            index=returns.index,
            columns=returns.columns,
        ),
        returns.rolling(63).std(ddof=1),
        returns.rolling(21).std(ddof=1).rolling(63).std(ddof=1),
        dd,
    ]
    result = []
    for frame in raw:
        frame = frame.where(eligible)
        mean = frame.mean(axis=1)
        scale = frame.std(axis=1, ddof=0).replace(0, 1)
        result.append(frame.sub(mean, axis=0).div(scale, axis=0).clip(-3, 3).to_numpy())
    return np.stack(result, axis=2)


def labels(returns: pd.DataFrame) -> np.ndarray:
    log = pd.DataFrame(np.log1p(returns.to_numpy()), index=returns.index, columns=returns.columns)
    return np.expm1(log.rolling(21).sum().shift(-21).to_numpy())


def sufficient_statistics(
    x: np.ndarray, y: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    valid = np.isfinite(x).all(axis=2) & np.isfinite(y)
    xx = x[valid]
    yy = y[valid]
    consecutive = np.isfinite(x[1:]).all(axis=2) & np.isfinite(x[:-1]).all(axis=2)
    delta = (x[1:] - x[:-1])[consecutive]
    return xx.T @ xx, xx.T @ yy, delta.T @ delta, len(yy)


def fit(
    stat: tuple[np.ndarray, np.ndarray, np.ndarray, int], alpha: float, lam: float
) -> np.ndarray:
    xx, xy, dd, n = stat
    if not n:
        raise ValueError("no complete training observations")
    return np.linalg.solve(xx + alpha * np.eye(6) + lam * dd, xy)


def targets(
    returns: pd.DataFrame,
    x: np.ndarray,
    eligible: pd.DataFrame,
    coefficient: np.ndarray | None,
    *,
    kind: str = "fitted",
    formation_days: set[pd.Timestamp] | None = None,
) -> pd.DataFrame:
    index = pd.DatetimeIndex(returns.index)
    result = pd.DataFrame(np.nan, index=index, columns=returns.columns)
    month_ends = (
        set(index.to_series().groupby(index.to_period("M")).max())
        if formation_days is None
        else formation_days
    )
    complete = np.isfinite(x).all(axis=2) & eligible.to_numpy()
    last = np.zeros(len(returns.columns))
    for i, day in enumerate(index):
        if day in month_ends:
            available = np.flatnonzero(complete[i])
            if len(available):
                score = (
                    x[i, :, 0]
                    if kind == "momentum"
                    else x[i] @ coefficient
                    if coefficient is not None
                    else np.zeros(len(last))
                )
                k = len(available) if kind == "equal" else int(np.ceil(0.3 * len(available)))
                chosen = available[np.argsort(-score[available], kind="stable")[:k]]
                last = np.zeros(len(last))
                last[chosen] = 1 / len(chosen)
                result.iloc[i] = last
    return result
