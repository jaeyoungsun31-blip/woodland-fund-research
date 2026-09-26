"""Diversification measurement.

Correlation structure is estimable from a 21.8-year sample far better than mean
returns are, so it is the claim this window can actually support. A Sharpe
difference of 0.10 needs centuries to resolve (see
`journal/2026-09-01-inference-existing-studies.md`); an average pairwise
correlation of 0.85 versus 0.35 is visible immediately and is not a close call.

Three measures, deliberately distinct:

  * `average_pairwise_correlation` — the raw input. Blunt, but it is the number
    that decides whether sleeves are different bets or the same bet relabelled.
  * `diversification_ratio` (Choueifaty & Coignard 2008) — weighted average
    sleeve volatility divided by realised portfolio volatility. It answers "how
    much volatility did combining these actually cancel".
  * `effective_bets` (Choueifaty & Coignard 2008) — the SQUARE of the
    diversification ratio, the effective number of independent risk sources.
    For p equicorrelated equal-risk sleeves at equal weight it is exactly
    p / (1 + (p-1)rho): smooth, monotone in correlation, and not fooled by ten
    positions that all move together.

`effective_bets_pca` (Meucci 2009) is provided as a cross-check but is NOT the
headline, and the reason is a pathology worth knowing about: an equally
weighted portfolio of equicorrelated sleeves is exactly the first principal
component, so all its variance loads on one eigenvector and the measure
returns exactly 1.0 for ANY positive correlation — then jumps discontinuously
to p at rho exactly 0. It is informative only when the covariance spectrum is
well separated. `tests/test_diversification.py` pins both behaviours so this
cannot be rediscovered as a surprise.

All three are scale-invariant in the weights, so a portfolio holding a cash
residual can be passed its risky weights unnormalised.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MIN_OBS = 60


def _validate_returns(returns: pd.DataFrame) -> pd.DataFrame:
    frame = returns.dropna()
    if frame.shape[0] < MIN_OBS:
        raise ValueError(f"need >= {MIN_OBS} complete observations, got {frame.shape[0]}")
    if frame.shape[1] < 2:
        raise ValueError("need at least two sleeves to measure diversification")
    return frame


def average_pairwise_correlation(returns: pd.DataFrame) -> float:
    """Mean off-diagonal entry of the sleeve correlation matrix."""
    corr = _validate_returns(returns).corr().to_numpy()
    off_diagonal = ~np.eye(corr.shape[0], dtype=bool)
    return float(corr[off_diagonal].mean())


def correlation_summary(returns: pd.DataFrame) -> dict:
    """Average, minimum and maximum pairwise correlation, and the extreme pair."""
    frame = _validate_returns(returns)
    corr = frame.corr()
    values = corr.to_numpy()
    mask = ~np.eye(values.shape[0], dtype=bool)
    off = values[mask]
    names = list(frame.columns)
    i, j = np.unravel_index(np.argmax(np.where(mask, values, -np.inf)), values.shape)
    lo_i, lo_j = np.unravel_index(np.argmin(np.where(mask, values, np.inf)), values.shape)
    return {
        "n_sleeves": len(names),
        "avg_pairwise_corr": float(off.mean()),
        "min_pairwise_corr": float(off.min()),
        "max_pairwise_corr": float(off.max()),
        "most_correlated_pair": f"{names[i]}/{names[j]}",
        "least_correlated_pair": f"{names[lo_i]}/{names[lo_j]}",
    }


def _as_weight_vector(weights: pd.Series | np.ndarray, columns: pd.Index) -> np.ndarray:
    if isinstance(weights, pd.Series):
        vector = weights.reindex(columns).to_numpy(dtype=float)
    else:
        vector = np.asarray(weights, dtype=float)
    if vector.shape != (len(columns),):
        raise ValueError(f"weights must have one entry per sleeve ({len(columns)})")
    if not np.isfinite(vector).all():
        raise ValueError("weights contain non-finite values")
    if float(np.sum(np.abs(vector))) <= 0:
        raise ValueError("weights are all zero")
    return vector


def diversification_ratio(weights: pd.Series | np.ndarray, covariance: pd.DataFrame) -> float:
    """Weighted average sleeve volatility / portfolio volatility.

    1.0 means combining the sleeves cancelled nothing; higher is better. For N
    uncorrelated equal-risk sleeves at equal weight it equals sqrt(N).
    """
    cov = covariance.to_numpy(dtype=float)
    w = _as_weight_vector(weights, covariance.columns)
    sleeve_vol = np.sqrt(np.diag(cov))
    portfolio_var = float(w @ cov @ w)
    if portfolio_var <= 0:
        raise ValueError("portfolio variance is non-positive")
    return float((w @ sleeve_vol) / np.sqrt(portfolio_var))


def effective_bets(weights: pd.Series | np.ndarray, covariance: pd.DataFrame) -> float:
    """Effective number of independent risk sources = diversification ratio squared.

    Choueifaty & Coignard (2008). Exactly p for p uncorrelated equal-risk
    sleeves at equal weight, exactly 1 for perfectly correlated ones, and
    p / (1 + (p-1)rho) in between — monotone in correlation, which is what
    makes it usable for comparing two universes.
    """
    return float(diversification_ratio(weights, covariance) ** 2)


def effective_bets_pca(weights: pd.Series | np.ndarray, covariance: pd.DataFrame) -> float:
    """Meucci (2009) variant: exp(entropy of principal-component variance shares).

    Cross-check only — see the module docstring. Degenerate for equally
    weighted equicorrelated portfolios, where it returns exactly 1.0 whatever
    the correlation is, because such a portfolio IS the first principal
    component.
    """
    cov = covariance.to_numpy(dtype=float)
    w = _as_weight_vector(weights, covariance.columns)
    symmetric = 0.5 * (cov + cov.T)
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric)

    rotated = eigenvectors.T @ w
    contributions = (rotated**2) * eigenvalues
    total = float(contributions.sum())
    if total <= 0:
        raise ValueError("portfolio variance is non-positive")

    shares = np.clip(contributions / total, 0.0, None)
    shares = shares[shares > 1e-15]
    entropy = float(-np.sum(shares * np.log(shares)))
    return float(np.exp(entropy))


def diversification_report(
    returns: pd.DataFrame,
    weights: pd.Series | np.ndarray | None = None,
    label: str = "",
) -> dict:
    """Correlation summary plus DR and effective bets, at the given weights.

    `weights=None` uses equal weights, which measures the UNIVERSE rather than
    any particular strategy's use of it.
    """
    frame = _validate_returns(returns)
    cov = frame.cov()
    if weights is None:
        weights = pd.Series(1.0 / frame.shape[1], index=frame.columns)
    report = {"label": label, **correlation_summary(frame)}
    report["diversification_ratio"] = diversification_ratio(weights, cov)
    report["effective_bets"] = effective_bets(weights, cov)
    report["effective_bets_pca"] = effective_bets_pca(weights, cov)
    report["n_obs"] = int(frame.shape[0])
    return report
