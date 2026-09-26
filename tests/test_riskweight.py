"""Known-answer tests for risk-based weighting (trend-v5)."""

import numpy as np
import pytest

from woodland.signals import riskweight as rw


def sample(n=250, p=4, seed=0, sd=None):
    rng = np.random.default_rng(seed)
    sd = sd if sd is not None else np.full(p, 0.01)
    return rng.normal(0.0, 1.0, (n, p)) * sd


# ---------------------------------------------------------------- simplex

def test_projection_returns_a_valid_simplex_point():
    for vector in ([3.0, -1.0, 0.5], [0.2, 0.2, 0.2], [-5.0, -6.0, -7.0], [10.0]):
        w = rw.project_to_simplex(np.array(vector, dtype=float))
        assert w.sum() == pytest.approx(1.0)
        assert (w >= -1e-15).all()


def test_projection_leaves_a_point_already_on_the_simplex_alone():
    v = np.array([0.5, 0.3, 0.2])
    assert np.allclose(rw.project_to_simplex(v), v)


def test_projection_is_the_nearest_simplex_point():
    rng = np.random.default_rng(1)
    v = rng.normal(size=6)
    w = rw.project_to_simplex(v)
    for _ in range(300):
        candidate = rng.dirichlet(np.ones(6))
        assert np.sum((v - w) ** 2) <= np.sum((v - candidate) ** 2) + 1e-12


# ---------------------------------------------------------------- inverse vol

def test_inverse_vol_is_proportional_to_one_over_sigma():
    sd = np.array([0.005, 0.010, 0.020, 0.040])
    w = rw.inverse_vol_weights(sample(n=4000, p=4, sd=sd, seed=2))
    expected = (1 / sd) / np.sum(1 / sd)
    assert np.allclose(w, expected, rtol=0.05)
    assert w.sum() == pytest.approx(1.0)
    assert w[0] > w[-1], "the quietest asset must get the most weight"


def test_inverse_vol_falls_back_to_equal_on_a_degenerate_column():
    data = sample(n=100, p=3, seed=3)
    data[:, 1] = 0.0
    w = rw.inverse_vol_weights(data)
    assert np.allclose(w, 1 / 3), "a zero-vol asset must not take infinite weight"


# ---------------------------------------------------------------- min variance

def test_min_variance_on_diagonal_covariance_matches_closed_form():
    """With no correlation the long-only optimum is w_i proportional to
    1/sigma_i^2 — an exact answer the solver must reproduce."""
    sd = np.array([0.01, 0.02, 0.04])
    w = rw.min_variance_weights(np.diag(sd**2))
    expected = (1 / sd**2) / np.sum(1 / sd**2)
    assert np.allclose(w, expected, atol=1e-6)


def test_min_variance_on_identity_is_equal_weight():
    w = rw.min_variance_weights(np.eye(5))
    assert np.allclose(w, 0.2, atol=1e-6)


def test_min_variance_concentrates_on_the_quieter_of_two_identical_assets():
    """Perfectly correlated assets differing only in volatility: everything
    belongs in the quieter one."""
    sd = np.array([0.01, 0.03])
    corr = np.array([[1.0, 0.999], [0.999, 1.0]])
    cov = np.outer(sd, sd) * corr
    w = rw.min_variance_weights(cov)
    assert w[0] > 0.95


def test_min_variance_respects_long_only_and_beats_equal_weight_variance():
    rng = np.random.default_rng(4)
    data = sample(n=2000, p=6, seed=5) + rng.normal(0, 0.004, (2000, 1))
    cov, _ = rw.ledoit_wolf_shrinkage(data)
    w = rw.min_variance_weights(cov)
    equal = np.full(6, 1 / 6)
    assert (w >= -1e-12).all() and w.sum() == pytest.approx(1.0)
    assert w @ cov @ w <= equal @ cov @ equal + 1e-15


def test_min_variance_rejects_a_non_square_matrix():
    with pytest.raises(ValueError, match="square"):
        rw.min_variance_weights(np.ones((2, 3)))


# ---------------------------------------------------------------- shrinkage

def test_shrinkage_output_is_symmetric_positive_definite():
    cov, intensity = rw.ledoit_wolf_shrinkage(sample(n=126, p=12, seed=6))
    assert np.allclose(cov, cov.T)
    assert (np.linalg.eigvalsh(cov) > 0).all()
    assert 0.0 <= intensity <= 1.0


def structured(n, p, seed):
    """Data whose true covariance is NOT a scaled identity: a common factor
    plus dispersed volatilities. Shrinkage toward mu*I is only informative
    when the target is wrong — on iid equal-variance data the target IS the
    truth and shrinking fully is the correct answer, not a bug."""
    rng = np.random.default_rng(seed)
    sd = np.linspace(0.005, 0.05, p)
    factor = rng.normal(0.0, 1.0, (n, 1))
    idiosyncratic = rng.normal(0.0, 1.0, (n, p))
    return (0.7 * factor + 0.7 * idiosyncratic) * sd


def test_shrinkage_is_stronger_when_there_is_less_data():
    _, few = rw.ledoit_wolf_shrinkage(structured(30, 10, seed=7))
    _, many = rw.ledoit_wolf_shrinkage(structured(5000, 10, seed=8))
    assert few > many, "a short window must be shrunk harder"
    assert many < 0.25


def test_shrinkage_goes_to_one_when_the_target_is_actually_correct():
    """The converse check, so the test above cannot pass for the wrong reason:
    on iid equal-variance data the scaled identity is the truth, and the
    estimator should hand nearly all the weight to it."""
    _, intensity = rw.ledoit_wolf_shrinkage(sample(n=200, p=10, seed=14))
    assert intensity > 0.9


def test_shrinkage_improves_conditioning():
    data = structured(60, 15, seed=9)
    centred = data - data.mean(axis=0)
    raw = centred.T @ centred / len(data)
    cov, intensity = rw.ledoit_wolf_shrinkage(data)
    # Intensity is deliberately NOT asserted to be large here: these variances
    # span 10x, so the scaled-identity target is a poor fit and shrinking less
    # is the right call. The claim that matters is the conditioning.
    assert intensity > 0.0
    assert np.linalg.cond(cov) < np.linalg.cond(raw)
    assert np.linalg.cond(raw) > 50, "sample covariance should be ill-conditioned here"


def test_shrinkage_preserves_total_variance_direction():
    """Shrinking toward mu*I must not change the average variance."""
    data = sample(n=400, p=5, seed=10)
    cov, _ = rw.ledoit_wolf_shrinkage(data)
    centred = data - data.mean(axis=0)
    raw = centred.T @ centred / len(data)
    assert np.trace(cov) == pytest.approx(np.trace(raw), rel=1e-9)


# ---------------------------------------------------------------- dispatch

def test_dispatch_matches_the_direct_calls():
    data = sample(n=200, p=5, seed=11)
    assert np.allclose(rw.risk_weights(data, "equal"), 0.2)
    assert np.allclose(rw.risk_weights(data, "inverse_vol"), rw.inverse_vol_weights(data))
    cov, _ = rw.ledoit_wolf_shrinkage(data)
    assert np.allclose(rw.risk_weights(data, "min_variance"), rw.min_variance_weights(cov))


def test_every_scheme_produces_a_valid_long_only_allocation():
    data = sample(n=200, p=7, seed=12)
    for scheme in ("equal", "inverse_vol", "min_variance"):
        w = rw.risk_weights(data, scheme)
        assert w.sum() == pytest.approx(1.0)
        assert (w >= -1e-12).all()


def test_unknown_scheme_and_bad_input_are_rejected():
    data = sample(n=100, p=3, seed=13)
    with pytest.raises(ValueError, match="unknown weighting scheme"):
        rw.risk_weights(data, "kelly")
    with pytest.raises(ValueError, match=">= 20 observations"):
        rw.risk_weights(data[:5], "inverse_vol")
    with pytest.raises(ValueError, match="non-finite"):
        rw.risk_weights(np.full((50, 3), np.nan), "inverse_vol")
    with pytest.raises(ValueError, match="2-D"):
        rw.risk_weights(np.zeros(50), "equal")
