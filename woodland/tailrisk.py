"""Tail-aware performance metrics with dependent-data confidence intervals."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from woodland import stats


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """Positive loss magnitude in the empirical lower tail."""
    clean = returns.dropna()
    if clean.empty or not 0.0 < confidence < 1.0:
        raise ValueError("returns must be non-empty and confidence in (0, 1)")
    values = clean.to_numpy(dtype=float)
    cutoff = float(np.quantile(values, 1.0 - confidence))
    return float(-clean[clean <= cutoff].mean())


def sortino(returns: pd.Series, target_daily: float = 0.0) -> float:
    clean = returns.dropna().to_numpy(dtype=float)
    if not len(clean):
        raise ValueError("returns must be non-empty")
    downside = np.minimum(clean - target_daily, 0.0)
    deviation = float(np.sqrt(np.mean(downside**2)))
    return (
        float((clean.mean() - target_daily) / deviation * np.sqrt(252))
        if deviation > 0.0 else float("nan")
    )


def omega(returns: pd.Series, threshold: float = 0.0) -> float:
    clean = returns.dropna().to_numpy(dtype=float)
    if not len(clean):
        raise ValueError("returns must be non-empty")
    gains = float(np.maximum(clean - threshold, 0.0).sum())
    losses = float(np.maximum(threshold - clean, 0.0).sum())
    return gains / losses if losses > 0.0 else float("nan")


def tail_ratio(returns: pd.Series) -> float:
    clean = returns.dropna()
    if clean.empty:
        raise ValueError("returns must be non-empty")
    values = clean.to_numpy(dtype=float)
    lower = abs(float(np.quantile(values, 0.05)))
    return float(np.quantile(values, 0.95)) / lower if lower > 0.0 else float("nan")


def adjusted_sharpe(returns: pd.Series) -> float:
    """Pezier-White adjustment applied at daily frequency, then annualized."""
    values = returns.dropna().to_numpy(dtype=float)
    if len(values) < 4:
        raise ValueError("need at least four returns")
    sd = float(values.std(ddof=1))
    if sd <= 0.0:
        return float("nan")
    daily_sharpe = float(values.mean()) / sd
    skewness, excess_kurtosis = _sample_shape(values)
    correction = (
        1.0
        + skewness * daily_sharpe / 6.0
        - excess_kurtosis * daily_sharpe**2 / 24.0
    )
    return daily_sharpe * correction * math.sqrt(252)


def drawdown_durations(returns: pd.Series) -> np.ndarray:
    """Lengths of completed drawdowns plus an ongoing terminal spell."""
    clean = returns.dropna()
    if clean.empty:
        return np.asarray([], dtype=int)
    equity = (1.0 + clean).cumprod().to_numpy(dtype=float)
    underwater = equity < np.maximum.accumulate(equity) - 1e-12
    padded = np.concatenate(([False], underwater, [False])).astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    return (ends - starts).astype(int)


def summarize(returns: pd.Series) -> dict[str, float]:
    values = returns.dropna().to_numpy(dtype=float)
    if len(values) < 4:
        raise ValueError("need at least four returns")
    return dict(zip(_METRIC_NAMES, _summarize_array(values), strict=True))


_METRIC_NAMES = [
    "sharpe_rf0",
    "cvar_95",
    "cvar_99",
    "sortino",
    "omega",
    "tail_ratio",
    "adjusted_sharpe",
    "skew",
    "excess_kurtosis",
    "drawdown_count",
    "drawdown_mean_days",
    "drawdown_median_days",
    "drawdown_p90_days",
    "drawdown_max_days",
]


def _sample_shape(values: np.ndarray) -> tuple[float, float]:
    """Pandas-compatible unbiased sample skew and excess kurtosis."""
    n = len(values)
    centred = values - values.mean()
    m2 = float(np.mean(centred**2))
    if m2 <= 0.0 or n < 4:
        return float("nan"), float("nan")
    m3 = float(np.mean(centred**3))
    m4 = float(np.mean(centred**4))
    skewness = math.sqrt(n * (n - 1.0)) / (n - 2.0) * m3 / m2**1.5
    excess = (n - 1.0) / ((n - 2.0) * (n - 3.0)) * (
        (n + 1.0) * m4 / m2**2 - 3.0 * (n - 1.0)
    )
    return skewness, excess


def _summarize_array(values: np.ndarray) -> np.ndarray:
    sd = float(values.std(ddof=1))
    mean = float(values.mean())
    sharpe = mean / sd * math.sqrt(252) if sd > 0.0 else float("nan")
    q01, q05, q95 = np.quantile(values, [0.01, 0.05, 0.95])
    downside = np.minimum(values, 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)))
    gains = float(np.maximum(values, 0.0).sum())
    losses = float(np.maximum(-values, 0.0).sum())
    skewness, excess = _sample_shape(values)
    adjusted = sharpe * (
        1.0
        + skewness * (sharpe / math.sqrt(252)) / 6.0
        - excess * (sharpe / math.sqrt(252)) ** 2 / 24.0
    )
    equity = np.cumprod(1.0 + values)
    underwater = equity < np.maximum.accumulate(equity) - 1e-12
    padded = np.concatenate(([False], underwater, [False])).astype(np.int8)
    changes = np.diff(padded)
    durations = np.flatnonzero(changes == -1) - np.flatnonzero(changes == 1)
    if len(durations):
        duration_stats = [
            float(len(durations)),
            float(durations.mean()),
            float(np.median(durations)),
            float(np.quantile(durations, 0.90)),
            float(durations.max()),
        ]
    else:
        duration_stats = [0.0] * 5
    return np.asarray(
        [
            sharpe,
            -float(values[values <= q05].mean()),
            -float(values[values <= q01].mean()),
            mean / downside_deviation * math.sqrt(252)
            if downside_deviation > 0.0
            else float("nan"),
            gains / losses if losses > 0.0 else float("nan"),
            float(q95) / abs(float(q05)) if q05 != 0.0 else float("nan"),
            adjusted,
            skewness,
            excess,
            *duration_stats,
        ],
        dtype=float,
    )


def _summarize_samples(samples: np.ndarray) -> np.ndarray:
    """Vectorized summaries for bootstrap paths stored one path per row."""
    n = samples.shape[1]
    means = samples.mean(axis=1)
    deviations = samples.std(axis=1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        sharpes = means / deviations * math.sqrt(252)
    quantiles = np.quantile(samples, [0.01, 0.05, 0.95], axis=1).T
    q01, q05, q95 = quantiles.T
    cvar95 = -np.sum(np.where(samples <= q05[:, None], samples, 0.0), axis=1) / np.sum(
        samples <= q05[:, None], axis=1
    )
    cvar99 = -np.sum(np.where(samples <= q01[:, None], samples, 0.0), axis=1) / np.sum(
        samples <= q01[:, None], axis=1
    )
    downside = np.minimum(samples, 0.0)
    downside_deviation = np.sqrt(np.mean(downside**2, axis=1))
    gains = np.maximum(samples, 0.0).sum(axis=1)
    losses = np.maximum(-samples, 0.0).sum(axis=1)
    centred = samples - means[:, None]
    m2 = np.mean(centred**2, axis=1)
    m3 = np.mean(centred**3, axis=1)
    m4 = np.mean(centred**4, axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        skewness = math.sqrt(n * (n - 1.0)) / (n - 2.0) * m3 / m2**1.5
        excess = (n - 1.0) / ((n - 2.0) * (n - 3.0)) * (
            (n + 1.0) * m4 / m2**2 - 3.0 * (n - 1.0)
        )
        daily_sharpes = sharpes / math.sqrt(252)
        adjusted = sharpes * (
            1.0
            + skewness * daily_sharpes / 6.0
            - excess * daily_sharpes**2 / 24.0
        )
        sortinos = means / downside_deviation * math.sqrt(252)
        omegas = gains / losses
        tail_ratios = q95 / np.abs(q05)

    equity = np.cumprod(1.0 + samples, axis=1)
    underwater = equity < np.maximum.accumulate(equity, axis=1) - 1e-12
    duration_stats = np.empty((len(samples), 5), dtype=float)
    for row_number, row in enumerate(underwater):
        changes = np.diff(
            np.concatenate(([False], row, [False])).astype(np.int8)
        )
        durations = np.flatnonzero(changes == -1) - np.flatnonzero(changes == 1)
        if len(durations):
            duration_stats[row_number] = [
                len(durations),
                durations.mean(),
                np.median(durations),
                np.quantile(durations, 0.90),
                durations.max(),
            ]
        else:
            duration_stats[row_number] = 0.0
    return np.column_stack(
        [
            sharpes,
            cvar95,
            cvar99,
            sortinos,
            omegas,
            tail_ratios,
            adjusted,
            skewness,
            excess,
            duration_stats,
        ]
    )
def bootstrap_intervals(
    returns: pd.Series,
    *,
    n_resamples: int = stats.DEFAULT_RESAMPLES,
    block_length: float = stats.DEFAULT_BLOCK_LENGTH,
    seed: int | None = 0,
) -> pd.DataFrame:
    """Percentile intervals for every scalar in :func:`summarize`."""
    clean = returns.dropna()
    if len(clean) < 30:
        raise ValueError("need at least 30 returns")
    point = summarize(clean)
    names = _METRIC_NAMES
    draws = np.empty((n_resamples, len(names)), dtype=float)
    rng = np.random.default_rng(seed)
    batch = max(1, min(n_resamples, 3_000_000 // len(clean)))
    values = clean.to_numpy(dtype=float)
    completed = 0
    while completed < n_resamples:
        size = min(batch, n_resamples - completed)
        indices = stats.stationary_bootstrap_indices(
            len(values), block_length, size, rng
        )
        draws[completed : completed + size] = _summarize_samples(values[indices])
        completed += size
    rows: list[dict[str, float | str]] = []
    for column, name in enumerate(names):
        finite = draws[np.isfinite(draws[:, column]), column]
        if not len(finite):
            rows.append({"metric": name, "estimate": point[name],
                         "ci_low": float("nan"), "ci_high": float("nan")})
            continue
        low, high = np.quantile(finite, [0.025, 0.975])
        rows.append(
            {"metric": name, "estimate": point[name],
             "ci_low": float(low), "ci_high": float(high)}
        )
    return pd.DataFrame(rows)
