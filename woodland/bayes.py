"""Bayesian decision analysis for paired Sharpe differences.

The walk-forward harness supplies paired daily return series.  Their
stationary block-bootstrap Sharpe-difference distribution supplies a sampling
standard error; a normal approximation turns that distribution into a
likelihood that can be combined with an explicitly declared normal prior.

This module contains no project-wide promotion rule.  Priors, loss weights,
and decision thresholds belong to a pre-registered study or to planning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np
import pandas as pd

from woodland import stats

_STANDARD_NORMAL = NormalDist()


@dataclass(frozen=True)
class NormalBelief:
    """A normal prior, likelihood approximation, or posterior for delta Sharpe."""

    mean: float
    sd: float
    label: str = "normal belief"

    def __post_init__(self) -> None:
        if not math.isfinite(self.mean):
            raise ValueError("mean must be finite")
        if not math.isfinite(self.sd) or self.sd <= 0:
            raise ValueError("sd must be finite and positive")

    def credible_interval(self, mass: float = 0.90) -> tuple[float, float]:
        """Equal-tailed credible interval containing ``mass`` probability."""
        if not 0.0 < mass < 1.0:
            raise ValueError("credible mass must be between zero and one")
        tail = (1.0 - mass) / 2.0
        z = _STANDARD_NORMAL.inv_cdf(1.0 - tail)
        return self.mean - z * self.sd, self.mean + z * self.sd

    def probability_above(self, threshold: float) -> float:
        """Posterior probability that delta Sharpe exceeds ``threshold``."""
        return 1.0 - _STANDARD_NORMAL.cdf((threshold - self.mean) / self.sd)


@dataclass(frozen=True)
class BootstrapLikelihood:
    """Normal likelihood approximation backed by paired bootstrap draws."""

    normal: NormalBelief
    point_estimate: float
    bootstrap_mean: float
    bootstrap_sd: float
    n_resamples: int
    block_length: int
    draws: np.ndarray


@dataclass(frozen=True)
class AllocationLoss:
    """Regret weights for the binary allocate/do-not-allocate decision.

    If allocated, negative true delta incurs ``downside_weight`` times the
    shortfall plus ``allocation_penalty``.  If not allocated, positive true
    delta incurs ``opportunity_weight`` times the foregone improvement.
    All quantities are in annualized Sharpe units.
    """

    downside_weight: float = 1.0
    opportunity_weight: float = 1.0
    allocation_penalty: float = 0.0

    def __post_init__(self) -> None:
        if self.downside_weight <= 0 or not math.isfinite(self.downside_weight):
            raise ValueError("downside_weight must be finite and positive")
        if self.opportunity_weight <= 0 or not math.isfinite(self.opportunity_weight):
            raise ValueError("opportunity_weight must be finite and positive")
        if self.allocation_penalty < 0 or not math.isfinite(self.allocation_penalty):
            raise ValueError("allocation_penalty must be finite and non-negative")


@dataclass(frozen=True)
class DecisionSummary:
    """Posterior diagnostics and expected loss for two available actions."""

    posterior_mean: float
    credible_low: float
    credible_high: float
    probability_positive: float
    probability_above_005: float
    expected_loss_allocate: float
    expected_loss_do_not_allocate: float
    lower_loss_action: str


def likelihood_from_bootstrap(
    point_estimate: float,
    bootstrap_draws: np.ndarray,
    *,
    block_length: int,
    label: str = "paired block-bootstrap likelihood",
) -> BootstrapLikelihood:
    """Approximate a bootstrap sampling distribution by a normal likelihood.

    The likelihood is centred at the observed point estimate, not at the mean
    bootstrap draw.  The latter is retained for bias diagnostics; the draw
    standard deviation supplies the sampling uncertainty.
    """
    draws = np.asarray(bootstrap_draws, dtype=float)
    draws = draws[np.isfinite(draws)]
    if draws.size < 2:
        raise ValueError("need at least two finite bootstrap draws")
    bootstrap_sd = float(draws.std(ddof=1))
    normal = NormalBelief(float(point_estimate), bootstrap_sd, label)
    return BootstrapLikelihood(
        normal=normal,
        point_estimate=float(point_estimate),
        bootstrap_mean=float(draws.mean()),
        bootstrap_sd=bootstrap_sd,
        n_resamples=int(draws.size),
        block_length=int(block_length),
        draws=draws.copy(),
    )


def paired_sharpe_likelihood(
    challenger: pd.Series,
    base: pd.Series,
    *,
    block_length: int = stats.DEFAULT_BLOCK_LENGTH,
    n_resamples: int = stats.DEFAULT_RESAMPLES,
    seed: int | None = 0,
    label: str = "paired block-bootstrap likelihood",
) -> BootstrapLikelihood:
    """Build a likelihood for SR(challenger) - SR(base) from paired returns."""
    point_estimate, draws = stats.bootstrap_sharpe_difference_distribution(
        challenger,
        base,
        block_length=block_length,
        n_resamples=n_resamples,
        seed=seed,
    )
    return likelihood_from_bootstrap(
        point_estimate, draws, block_length=block_length, label=label
    )


def update_normal(likelihood: NormalBelief, prior: NormalBelief) -> NormalBelief:
    """Conjugate normal-normal update with known sampling variance."""
    likelihood_precision = 1.0 / likelihood.sd**2
    prior_precision = 1.0 / prior.sd**2
    posterior_variance = 1.0 / (likelihood_precision + prior_precision)
    posterior_mean = posterior_variance * (
        likelihood.mean * likelihood_precision + prior.mean * prior_precision
    )
    return NormalBelief(
        posterior_mean,
        math.sqrt(posterior_variance),
        label=f"posterior: {prior.label} + {likelihood.label}",
    )


def _expected_positive_part(mean: float, sd: float) -> float:
    """E[max(X, 0)] for X distributed Normal(mean, sd)."""
    z = mean / sd
    density = math.exp(-0.5 * z**2) / math.sqrt(2.0 * math.pi)
    return mean * _STANDARD_NORMAL.cdf(z) + sd * density


def expected_losses(
    posterior: NormalBelief, loss: AllocationLoss
) -> tuple[float, float]:
    """Return expected loss of (allocate, do not allocate)."""
    negative_shortfall = _expected_positive_part(-posterior.mean, posterior.sd)
    positive_opportunity = _expected_positive_part(posterior.mean, posterior.sd)
    allocate = loss.downside_weight * negative_shortfall + loss.allocation_penalty
    do_not_allocate = loss.opportunity_weight * positive_opportunity
    return allocate, do_not_allocate


def summarize_decision(
    posterior: NormalBelief,
    loss: AllocationLoss,
    *,
    credible_mass: float = 0.90,
) -> DecisionSummary:
    """Produce the fixed posterior and expected-loss reporting fields."""
    low, high = posterior.credible_interval(credible_mass)
    allocate, do_not_allocate = expected_losses(posterior, loss)
    action = "allocate" if allocate < do_not_allocate else "do_not_allocate"
    return DecisionSummary(
        posterior_mean=posterior.mean,
        credible_low=low,
        credible_high=high,
        probability_positive=posterior.probability_above(0.0),
        probability_above_005=posterior.probability_above(0.05),
        expected_loss_allocate=allocate,
        expected_loss_do_not_allocate=do_not_allocate,
        lower_loss_action=action,
    )
