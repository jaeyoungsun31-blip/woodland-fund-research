"""Known-answer tests for Bayesian Sharpe-difference decisions."""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pytest

from woodland import bayes


def test_normal_normal_update_matches_conjugate_known_answer() -> None:
    prior = bayes.NormalBelief(mean=0.0, sd=1.0, label="prior")
    likelihood = bayes.NormalBelief(mean=1.0, sd=1.0, label="likelihood")

    posterior = bayes.update_normal(likelihood, prior)

    assert posterior.mean == pytest.approx(0.5)
    assert posterior.sd == pytest.approx(math.sqrt(0.5))


def test_credible_interval_and_threshold_probabilities_are_known_normal_values() -> None:
    posterior = bayes.NormalBelief(mean=0.10, sd=0.05)
    z_95 = NormalDist().inv_cdf(0.95)

    low, high = posterior.credible_interval(0.90)

    assert low == pytest.approx(0.10 - z_95 * 0.05)
    assert high == pytest.approx(0.10 + z_95 * 0.05)
    assert posterior.probability_above(0.10) == pytest.approx(0.5)
    assert posterior.probability_above(0.05) == pytest.approx(NormalDist().cdf(1.0))


def test_bootstrap_likelihood_uses_point_estimate_and_draw_uncertainty() -> None:
    draws = np.array([-0.1, 0.0, 0.1, 0.2])

    likelihood = bayes.likelihood_from_bootstrap(
        0.075, draws, block_length=21, label="synthetic"
    )

    assert likelihood.normal.mean == pytest.approx(0.075)
    assert likelihood.normal.sd == pytest.approx(draws.std(ddof=1))
    assert likelihood.bootstrap_mean == pytest.approx(0.05)
    assert likelihood.n_resamples == 4
    assert likelihood.block_length == 21
    assert likelihood.draws.tolist() == pytest.approx(draws.tolist())


def test_symmetric_zero_posterior_has_equal_expected_regret() -> None:
    posterior = bayes.NormalBelief(mean=0.0, sd=0.1)

    allocate, do_not_allocate = bayes.expected_losses(
        posterior, bayes.AllocationLoss()
    )

    expected = 0.1 / math.sqrt(2.0 * math.pi)
    assert allocate == pytest.approx(expected)
    assert do_not_allocate == pytest.approx(expected)


def test_allocation_penalty_and_asymmetric_downside_enter_loss_exactly() -> None:
    posterior = bayes.NormalBelief(mean=0.08, sd=0.04)
    base_allocate, base_do_not = bayes.expected_losses(
        posterior, bayes.AllocationLoss()
    )
    penalized_allocate, penalized_do_not = bayes.expected_losses(
        posterior,
        bayes.AllocationLoss(
            downside_weight=2.0,
            opportunity_weight=1.0,
            allocation_penalty=0.01,
        ),
    )

    assert penalized_allocate == pytest.approx(2.0 * base_allocate + 0.01)
    assert penalized_do_not == pytest.approx(base_do_not)


def test_decision_summary_reports_lower_expected_loss_action() -> None:
    summary = bayes.summarize_decision(
        bayes.NormalBelief(mean=0.10, sd=0.02),
        bayes.AllocationLoss(allocation_penalty=0.005),
    )

    assert summary.posterior_mean == pytest.approx(0.10)
    assert summary.probability_positive > 0.999
    assert summary.probability_above_005 > 0.99
    assert summary.expected_loss_allocate < summary.expected_loss_do_not_allocate
    assert summary.lower_loss_action == "allocate"


@pytest.mark.parametrize("sd", [0.0, -1.0, float("inf"), float("nan")])
def test_normal_belief_rejects_invalid_standard_deviation(sd: float) -> None:
    with pytest.raises(ValueError, match="sd must be finite and positive"):
        bayes.NormalBelief(mean=0.0, sd=sd)
