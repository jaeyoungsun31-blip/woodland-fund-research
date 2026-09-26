"""Risk-based weighting for the in-trend sleeve (trend-v5).

v1-v4 split the risky budget equally across whatever is in trend. That is a
defensible default — equal weighting is famously hard to beat and has no
parameters — but it ignores the fact that an energy sleeve and a utilities
sleeve contribute very different amounts of risk per dollar.

Two alternatives here, both estimated from data through the decision date only:

  * `inverse_vol_weights` — weight inversely to trailing volatility. One
    estimate per asset, no covariances, so nothing to invert and little to
    overfit.
  * `min_variance_weights` on a `ledoit_wolf_shrinkage` covariance — the
    ambitious version. A sample covariance over 126 bars of 12 assets is badly
    conditioned, and a minimum-variance optimiser will happily exploit its
    estimation error; shrinking toward a scaled identity is the standard
    remedy (Ledoit & Wolf 2004).

Both are implemented in numpy rather than pulling in scipy/sklearn for three
functions, following the same reasoning as `woodland/stats.py`.
"""

from __future__ import annotations

import numpy as np

MIN_WEIGHT_OBS = 20


def _validate(returns: np.ndarray) -> np.ndarray:
    arr = np.asarray(returns, dtype=float)
    if arr.ndim != 2:
        raise ValueError("returns must be a 2-D (observations x assets) array")
    if arr.shape[0] < MIN_WEIGHT_OBS:
        raise ValueError(f"need >= {MIN_WEIGHT_OBS} observations, got {arr.shape[0]}")
    if arr.shape[1] < 1:
        raise ValueError("need at least one asset")
    if not np.isfinite(arr).all():
        raise ValueError("returns contain non-finite values")
    return arr


def inverse_vol_weights(returns: np.ndarray) -> np.ndarray:
    """Long-only weights proportional to 1 / trailing standard deviation.

    A zero-variance asset would take infinite weight, so degenerate columns
    fall back to equal weighting rather than silently dominating.
    """
    arr = _validate(returns)
    sd = arr.std(axis=0, ddof=1)
    if not np.all(sd > 0):
        return np.full(arr.shape[1], 1.0 / arr.shape[1])
    raw = 1.0 / sd
    return raw / raw.sum()


def ledoit_wolf_shrinkage(returns: np.ndarray) -> tuple[np.ndarray, float]:
    """Ledoit-Wolf (2004) covariance shrunk toward a scaled identity.

    Returns (covariance, shrinkage_intensity). The intensity is chosen
    analytically to minimise expected squared error, so it is not a tunable
    knob: it goes to 1 when the sample covariance is hopeless (few
    observations, many assets) and to 0 when it is reliable.
    """
    arr = _validate(returns)
    n, p = arr.shape
    centred = arr - arr.mean(axis=0)
    sample = centred.T @ centred / n

    mu = float(np.trace(sample) / p)
    identity_target = mu * np.eye(p)
    d2 = float(np.sum((sample - identity_target) ** 2) / p)
    if d2 <= 0:                              # sample already equals the target
        return sample, 0.0

    # sum_k ||x_k x_k' - S||_F^2 reduces to sum_k ||x_k||^4 - n||S||_F^2
    quartic = float(np.sum(np.sum(centred**2, axis=1) ** 2))
    b2_bar = (quartic - n * float(np.sum(sample**2))) / (n**2 * p)
    b2 = min(max(b2_bar, 0.0), d2)
    intensity = b2 / d2
    return intensity * identity_target + (1.0 - intensity) * sample, intensity


def project_to_simplex(vector: np.ndarray) -> np.ndarray:
    """Euclidean projection onto {w : w >= 0, sum(w) = 1} (Duchi et al. 2008)."""
    v = np.asarray(vector, dtype=float)
    if v.size == 1:
        return np.ones(1)
    descending = np.sort(v)[::-1]
    cumulative = np.cumsum(descending)
    indices = np.arange(1, v.size + 1)
    eligible = descending - (cumulative - 1.0) / indices > 0
    rho = int(np.nonzero(eligible)[0][-1])
    theta = (cumulative[rho] - 1.0) / (rho + 1)
    return np.asarray(np.maximum(v - theta, 0.0), dtype=float)


def min_variance_weights(
    covariance: np.ndarray, *, iterations: int = 1000, tolerance: float = 1e-12
) -> np.ndarray:
    """Long-only minimum-variance weights: min w'Sw s.t. w >= 0, sum(w) = 1.

    Solved by projected gradient descent with an exact simplex projection.
    The long-only constraint matters: unconstrained minimum variance places
    large offsetting long and short positions on near-collinear assets, which
    is where estimation error does its worst damage — and the engine is
    long-only anyway.
    """
    cov = np.asarray(covariance, dtype=float)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError("covariance must be square")
    p = cov.shape[0]
    if p == 1:
        return np.ones(1)

    symmetric = 0.5 * (cov + cov.T)
    curvature = float(np.max(np.abs(np.linalg.eigvalsh(symmetric))))
    if not np.isfinite(curvature) or curvature <= 0:
        return np.full(p, 1.0 / p)
    step = 1.0 / (2.0 * curvature)

    weights = np.full(p, 1.0 / p)
    for _ in range(iterations):
        updated = project_to_simplex(weights - step * (2.0 * symmetric @ weights))
        if float(np.max(np.abs(updated - weights))) < tolerance:
            weights = updated
            break
        weights = updated
    return weights


def risk_weights(returns: np.ndarray, scheme: str) -> np.ndarray:
    """Dispatch to a named weighting scheme over a trailing return window."""
    if scheme == "equal":
        arr = _validate(returns)
        return np.full(arr.shape[1], 1.0 / arr.shape[1])
    if scheme == "inverse_vol":
        return inverse_vol_weights(returns)
    if scheme == "min_variance":
        covariance, _ = ledoit_wolf_shrinkage(returns)
        return min_variance_weights(covariance)
    raise ValueError(f"unknown weighting scheme {scheme!r}")
