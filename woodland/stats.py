"""Statistical inference for performance comparisons.

Every comparison this project made before this module was a point estimate.
"Sharpe 0.700 versus 0.806" reads like a fact; it is one draw from a sampling
distribution, and on ~22 years of overlapping, autocorrelated, fat-tailed daily
returns that distribution is wide. This module attaches error bars.

Two independent routes to the same question, deliberately kept side by side so
they can disagree in the open:

  * `stationary_bootstrap` (Politis & Romano 1994) — resample blocks of
    consecutive observations so short-range dependence survives resampling.
    Block starts are geometric, which makes the resampled series stationary;
    the fixed-block bootstrap is not.
  * `ledoit_wolf_sharpe_test` — the analytic counterpart: delta method on the
    four moments a Sharpe difference depends on, with a HAC covariance so
    autocorrelation and heteroskedasticity widen the standard error instead of
    being assumed away (Ledoit & Wolf 2008).

Both are run on the SAME PAIRED observations. Two equity strategies share most
of their risk, so their Sharpe estimates are strongly positively correlated and
the difference is far better determined than either level. Resampling them
independently would inflate the interval by a large factor and is simply the
wrong null.

The naive alternative — treating returns as iid — is also implemented, as
`iid_sharpe_test`. It is here to be shown wrong: `tests/test_stats.py` measures
its rejection rate on autocorrelated data under a true null and finds it far
above nominal size.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

TRADING_DAYS = 252
_N = NormalDist()

# Pre-chosen, not tuned. One trading month of expected block length: long
# enough to carry the daily autocorrelation and short-horizon volatility
# clustering that matter here, short enough that a 5,500-bar sample still
# contains many effectively independent blocks. Fixed before any real series
# was touched; changing it for a specific result would be exactly the kind of
# tuning this module exists to detect.
DEFAULT_BLOCK_LENGTH = 21
DEFAULT_RESAMPLES = 10_000

# Cap on index entries held at once while resampling (~24 MB of int64).
_INDEX_BUDGET = 3_000_000


@dataclass(frozen=True)
class SharpeComparison:
    """Result of comparing two aligned return series."""

    name_a: str
    name_b: str
    sharpe_a: float
    sharpe_b: float
    difference: float
    ci_low: float
    ci_high: float
    p_value: float
    n_obs: int
    method: str
    n_resamples: int | None = None
    block_length: int | None = None
    standard_error: float | None = None

    @property
    def significant_at_05(self) -> bool:
        return self.p_value < 0.05

    def summary(self) -> str:
        detail = (
            f"{self.n_resamples} resamples, block length {self.block_length}"
            if self.n_resamples
            else f"HAC standard error {self.standard_error:.4f}"
        )
        verdict = (
            "distinguishable at 5%" if self.significant_at_05
            else "NOT distinguishable at 5%"
        )
        return (
            f"{self.name_a} {self.sharpe_a:.3f} vs {self.name_b} {self.sharpe_b:.3f}\n"
            f"  difference {self.difference:+.3f}  "
            f"95% CI [{self.ci_low:+.3f}, {self.ci_high:+.3f}]  p = {self.p_value:.3f}\n"
            f"  {self.method}; {detail}; n = {self.n_obs}\n"
            f"  -> {verdict}"
        )


# ---------------------------------------------------------------- bootstrap

def stationary_bootstrap_indices(
    n: int, block_length: float, n_resamples: int, rng: np.random.Generator
) -> np.ndarray:
    """Politis-Romano stationary bootstrap index matrix, shape (n_resamples, n).

    Each position either continues the previous block (wrapping at the end of
    the sample) or starts a new one at a uniformly random point, with
    P(new block) = 1 / block_length. Block lengths are therefore geometric with
    mean `block_length`, which is what makes the resampled series stationary.

    Vectorised over resamples: block starts are located with a running maximum
    rather than a loop over observations.
    """
    if n < 2:
        raise ValueError("need at least two observations to bootstrap")
    if block_length < 1:
        raise ValueError("block_length must be >= 1")
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")

    p = 1.0 / float(block_length)
    positions = np.arange(n)

    starts_new = rng.random((n_resamples, n)) < p
    starts_new[:, 0] = True                       # every path begins a block
    candidate_starts = rng.integers(0, n, size=(n_resamples, n))

    # position at which the block covering each observation began
    block_origin = np.maximum.accumulate(np.where(starts_new, positions, -1), axis=1)
    base = np.take_along_axis(candidate_starts, block_origin, axis=1)
    offset = positions - block_origin
    return (base + offset) % n


def stationary_bootstrap(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float],
    *,
    block_length: float = DEFAULT_BLOCK_LENGTH,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int | None = 0,
) -> np.ndarray:
    """Bootstrap distribution of `statistic` over rows of `data`.

    `data` is (n_obs,) or (n_obs, k). Rows are resampled JOINTLY, so any
    cross-sectional dependence between columns is preserved — essential when
    comparing two strategies that share most of their risk.
    """
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 1:
        arr = arr[:, None]
    rng = np.random.default_rng(seed)

    # Generated in batches: the full index matrix for 10,000 resamples of a
    # 5,500-bar series is ~440 MB, and there is no reason to hold it at once.
    batch = max(1, min(n_resamples, max(1, _INDEX_BUDGET // max(len(arr), 1))))
    out: list[float] = []
    remaining = n_resamples
    while remaining > 0:
        size = min(batch, remaining)
        idx = stationary_bootstrap_indices(len(arr), block_length, size, rng)
        out.extend(statistic(arr[row]) for row in idx)
        remaining -= size
    return np.asarray(out, dtype=float)


def _sharpe_from_columns(sample: np.ndarray) -> np.ndarray:
    """Annualized Sharpe of each column, rf = 0."""
    mean = sample.mean(axis=0)
    sd = sample.std(axis=0, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(sd > 0, mean / sd * math.sqrt(TRADING_DAYS), np.nan)


def _align(
    a: pd.Series,
    b: pd.Series,
    rf_daily: pd.Series | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    columns = {"a": a, "b": b}
    if rf_daily is not None:
        columns["rf"] = rf_daily
    both = pd.DataFrame(columns).dropna()
    if len(both) < 30:
        raise ValueError(f"need >= 30 aligned observations, got {len(both)}")
    if rf_daily is not None:
        both["a"] = both["a"] - both["rf"]
        both["b"] = both["b"] - both["rf"]
    return both["a"].to_numpy(float), both["b"].to_numpy(float)


def bootstrap_sharpe_difference(
    a: pd.Series,
    b: pd.Series,
    *,
    name_a: str = "A",
    name_b: str = "B",
    block_length: float = DEFAULT_BLOCK_LENGTH,
    n_resamples: int = DEFAULT_RESAMPLES,
    confidence: float = 0.95,
    seed: int | None = 0,
    rf_daily: pd.Series | None = None,
) -> SharpeComparison:
    """Block-bootstrap CI and p-value for SR(a) - SR(b), annualized.

    The p-value is a two-sided test of H0: the true difference is zero,
    obtained by recentring the bootstrap distribution on the null and asking
    how often it produces a difference at least as extreme as the observed one.
    """
    x, y = _align(a, b, rf_daily)
    paired = np.column_stack([x, y])

    def difference_of(sample: np.ndarray) -> float:
        sharpes = _sharpe_from_columns(sample)
        return float(sharpes[0] - sharpes[1])

    observed = difference_of(paired)
    draws = stationary_bootstrap(
        paired, difference_of,
        block_length=block_length, n_resamples=n_resamples, seed=seed,
    )
    draws = draws[np.isfinite(draws)]
    if draws.size == 0:
        raise ValueError("every bootstrap resample was degenerate")

    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(draws, [tail, 1.0 - tail])

    # Recentre on the null; +1 correction keeps the p-value away from exactly 0.
    centred = np.abs(draws - observed)
    p_value = float((1 + int(np.sum(centred >= abs(observed)))) / (draws.size + 1))

    sharpes = _sharpe_from_columns(paired)
    return SharpeComparison(
        name_a=name_a, name_b=name_b,
        sharpe_a=float(sharpes[0]), sharpe_b=float(sharpes[1]),
        difference=observed,
        ci_low=float(low), ci_high=float(high), p_value=p_value,
        n_obs=len(x), method="stationary block bootstrap (Politis-Romano)",
        n_resamples=int(draws.size), block_length=int(block_length),
    )


def bootstrap_sharpe_difference_distribution(
    a: pd.Series,
    b: pd.Series,
    *,
    block_length: float = DEFAULT_BLOCK_LENGTH,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int | None = 0,
    rf_daily: pd.Series | None = None,
) -> tuple[float, np.ndarray]:
    """Point estimate and paired block-bootstrap draws of SR(a) - SR(b).

    Unlike :func:`bootstrap_sharpe_difference`, this returns the sampling
    distribution itself.  It exists for downstream decision analysis that
    needs the uncertainty distribution rather than only a confidence interval.
    Rows are still resampled jointly. When ``rf_daily`` is supplied, both
    series are converted to excess returns before any point or resampled
    Sharpe is computed.
    """
    x, y = _align(a, b, rf_daily)
    paired = np.column_stack([x, y])

    def difference_of(sample: np.ndarray) -> float:
        sharpes = _sharpe_from_columns(sample)
        return float(sharpes[0] - sharpes[1])

    observed = difference_of(paired)
    draws = stationary_bootstrap(
        paired,
        difference_of,
        block_length=block_length,
        n_resamples=n_resamples,
        seed=seed,
    )
    draws = draws[np.isfinite(draws)]
    if draws.size == 0:
        raise ValueError("every bootstrap resample was degenerate")
    return observed, draws


# ---------------------------------------------------------------- analytic

def _bartlett_hac(y: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West HAC covariance of the columns of `y` (already de-meaned)."""
    n = len(y)
    psi = y.T @ y / n
    for j in range(1, lags + 1):
        gamma = y[j:].T @ y[:-j] / n
        weight = 1.0 - j / (lags + 1.0)
        psi = psi + weight * (gamma + gamma.T)
    return np.asarray(psi, dtype=float)


def andrews_bandwidth(y: np.ndarray) -> int:
    """Andrews (1991) AR(1) plug-in bandwidth for a Bartlett kernel.

    Chosen by a published rule from the data's own persistence rather than by
    hand, so the HAC lag length is not a free parameter someone could tune
    until a comparison came out the desired way.
    """
    n, k = int(y.shape[0]), int(y.shape[1])
    numerator = denominator = 0.0
    for i in range(k):
        series = y[:, i]
        denom = float(series[:-1] @ series[:-1])
        rho = float(series[:-1] @ series[1:] / denom) if denom > 0 else 0.0
        rho = float(np.clip(rho, -0.97, 0.97))
        resid = series[1:] - rho * series[:-1]
        sigma2 = float(resid @ resid / max(len(resid), 1))
        numerator += 4.0 * rho**2 * sigma2**2 / ((1 - rho) ** 6 * (1 + rho) ** 2)
        denominator += sigma2**2 / (1 - rho) ** 4
    if denominator <= 0 or numerator <= 0:
        return max(1, int(round(4 * (n / 100.0) ** (2.0 / 9.0))))
    alpha1 = numerator / denominator
    return max(1, min(n - 2, int(round(1.1447 * (alpha1 * n) ** (1.0 / 3.0)))))


def ledoit_wolf_sharpe_test(
    a: pd.Series,
    b: pd.Series,
    *,
    name_a: str = "A",
    name_b: str = "B",
    lags: int | None = None,
    confidence: float = 0.95,
    rf_daily: pd.Series | None = None,
) -> SharpeComparison:
    """HAC-robust test for a Sharpe difference (Ledoit & Wolf 2008).

    A Sharpe ratio is a smooth function of two moments, so the difference of
    two of them is a smooth function of four: (mu_a, mu_b, E[a^2], E[b^2]).
    The delta method turns the HAC covariance of those four moments into a
    standard error for the difference. Autocorrelation and volatility
    clustering therefore widen the interval instead of being assumed away.

    Deviation from the paper, stated rather than buried: Ledoit and Wolf use a
    prewhitened kernel estimator with automatic bandwidth. This uses a Bartlett
    kernel with the Andrews (1991) AR(1) plug-in bandwidth — same delta-method
    statistic, a simpler and still data-driven HAC. On iid data it collapses to
    the textbook standard error, which `tests/test_stats.py` asserts.
    """
    x, y = _align(a, b, rf_daily)
    n = len(x)

    mu_a, mu_b = float(x.mean()), float(y.mean())
    g_a, g_b = float((x**2).mean()), float((y**2).mean())
    var_a, var_b = g_a - mu_a**2, g_b - mu_b**2
    if var_a <= 0 or var_b <= 0:
        raise ValueError("a return series has zero variance")

    sr_a, sr_b = mu_a / math.sqrt(var_a), mu_b / math.sqrt(var_b)

    gradient = np.array([
        g_a / var_a**1.5,
        -g_b / var_b**1.5,
        -0.5 * mu_a / var_a**1.5,
        0.5 * mu_b / var_b**1.5,
    ])

    moments = np.column_stack([x, y, x**2, y**2])
    centred = moments - moments.mean(axis=0)
    lag_count = andrews_bandwidth(centred) if lags is None else int(lags)
    psi = _bartlett_hac(centred, lag_count)

    variance = float(gradient @ psi @ gradient) / n
    if variance < 0:
        # The Bartlett kernel is positive semi-definite, so this should be
        # unreachable; treat it as a bug rather than rounding it away.
        raise ValueError(f"negative HAC variance ({variance:.3e}); estimator is broken")
    se = math.sqrt(variance)

    scale = math.sqrt(TRADING_DAYS)
    difference = (sr_a - sr_b) * scale
    se_annual = se * scale

    # se == 0 is degenerate but meaningful: the two series move identically, so
    # the difference is known exactly. Zero difference is then no evidence of
    # one; a non-zero difference with no sampling error would be certain.
    if se > 0.0:
        z = (sr_a - sr_b) / se
    elif difference == 0.0:
        z = 0.0
    else:
        z = math.inf
    p_value = 2.0 * (1.0 - _N.cdf(abs(z))) if math.isfinite(z) else 0.0
    crit = _N.inv_cdf(1.0 - (1.0 - confidence) / 2.0)

    return SharpeComparison(
        name_a=name_a, name_b=name_b,
        sharpe_a=sr_a * scale, sharpe_b=sr_b * scale,
        difference=difference,
        ci_low=difference - crit * se_annual,
        ci_high=difference + crit * se_annual,
        p_value=p_value, n_obs=n,
        method=f"Ledoit-Wolf HAC delta method (Bartlett, {lag_count} lags)",
        standard_error=se_annual,
    )


def iid_sharpe_test(
    a: pd.Series,
    b: pd.Series,
    *,
    name_a: str = "A",
    name_b: str = "B",
    confidence: float = 0.95,
) -> SharpeComparison:
    """The NAIVE test: assumes returns are iid. Provided to be shown wrong.

    Under iid normality Var(SR) ~ (1 + SR^2/2)/n, and independence between the
    two series would give Var of the difference as the sum. Both assumptions
    fail on real strategy returns — they are autocorrelated and highly
    correlated with each other — so this understates the standard error and
    over-rejects. Never report a decision from it; it exists as the baseline
    the other two tests are measured against.
    """
    x, y = _align(a, b)
    n = len(x)
    sr_a = float(x.mean() / x.std(ddof=1))
    sr_b = float(y.mean() / y.std(ddof=1))
    var = (1 + sr_a**2 / 2) / n + (1 + sr_b**2 / 2) / n
    se = math.sqrt(var)
    z = (sr_a - sr_b) / se
    scale = math.sqrt(TRADING_DAYS)
    difference = (sr_a - sr_b) * scale
    crit = _N.inv_cdf(1.0 - (1.0 - confidence) / 2.0)
    return SharpeComparison(
        name_a=name_a, name_b=name_b,
        sharpe_a=sr_a * scale, sharpe_b=sr_b * scale,
        difference=difference,
        ci_low=difference - crit * se * scale,
        ci_high=difference + crit * se * scale,
        p_value=2.0 * (1.0 - _N.cdf(abs(z))), n_obs=n,
        method="naive iid (WRONG for dependent returns; comparison only)",
        standard_error=se * scale,
    )


def sharpe_confidence_interval(
    returns: pd.Series,
    *,
    block_length: float = DEFAULT_BLOCK_LENGTH,
    n_resamples: int = DEFAULT_RESAMPLES,
    confidence: float = 0.95,
    seed: int | None = 0,
) -> tuple[float, float, float]:
    """Block-bootstrap (point estimate, low, high) for one series' Sharpe."""
    r = pd.Series(returns).dropna().to_numpy(float)
    if len(r) < 30:
        raise ValueError(f"need >= 30 observations, got {len(r)}")
    point = float(_sharpe_from_columns(r[:, None])[0])
    draws = stationary_bootstrap(
        r, lambda s: float(_sharpe_from_columns(s)[0]),
        block_length=block_length, n_resamples=n_resamples, seed=seed,
    )
    draws = draws[np.isfinite(draws)]
    tail = (1.0 - confidence) / 2.0
    low, high = np.quantile(draws, [tail, 1.0 - tail])
    return point, float(low), float(high)
