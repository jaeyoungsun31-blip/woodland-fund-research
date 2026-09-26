"""Known-answer tests for diversification measurement."""

import numpy as np
import pandas as pd
import pytest

from woodland import diversification as dv


def independent(n=2000, p=4, seed=0, sd=0.01):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n)
    return pd.DataFrame(rng.normal(0.0, sd, (n, p)), index=idx,
                        columns=[f"A{i}" for i in range(p)])


def identical(n=500, p=4, seed=1, sd=0.01):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2010-01-04", periods=n)
    single = rng.normal(0.0, sd, n)
    return pd.DataFrame({f"A{i}": single for i in range(p)}, index=idx)


# ---------------------------------------------------------------- correlation

def test_independent_sleeves_have_near_zero_average_correlation():
    assert dv.average_pairwise_correlation(independent()) == pytest.approx(0.0, abs=0.05)


def test_identical_sleeves_have_correlation_one():
    assert dv.average_pairwise_correlation(identical()) == pytest.approx(1.0, abs=1e-9)


def test_correlation_summary_names_the_extreme_pairs():
    frame = independent(p=3).copy()
    frame["A2"] = frame["A0"] * 1.0            # A0 and A2 identical
    summary = dv.correlation_summary(frame)
    assert summary["n_sleeves"] == 3
    assert summary["max_pairwise_corr"] == pytest.approx(1.0, abs=1e-9)
    assert set(summary["most_correlated_pair"].split("/")) == {"A0", "A2"}


# ---------------------------------------------------------------- known answers

@pytest.mark.parametrize("p", [2, 4, 9])
def test_uncorrelated_equal_risk_gives_diversification_ratio_sqrt_n(p):
    """The textbook identity: N independent equal-risk sleeves at equal weight
    have DR = sqrt(N) and exactly N effective bets."""
    cov = pd.DataFrame(np.eye(p) * 0.0001,
                       index=[f"A{i}" for i in range(p)],
                       columns=[f"A{i}" for i in range(p)])
    w = np.full(p, 1.0 / p)
    assert dv.diversification_ratio(w, cov) == pytest.approx(np.sqrt(p), rel=1e-12)
    assert dv.effective_bets(w, cov) == pytest.approx(p, rel=1e-12)
    assert dv.effective_bets_pca(w, cov) == pytest.approx(p, rel=1e-12)


def test_perfectly_correlated_sleeves_give_one_bet():
    p = 5
    names = [f"A{i}" for i in range(p)]
    cov = pd.DataFrame(np.full((p, p), 0.0001), index=names, columns=names)
    w = np.full(p, 1.0 / p)
    assert dv.diversification_ratio(w, cov) == pytest.approx(1.0, rel=1e-9)
    assert dv.effective_bets(w, cov) == pytest.approx(1.0, rel=1e-6)


def test_effective_bets_is_not_fooled_by_holding_count():
    """Ten sleeves that all move together must not score as ten bets — the
    failure mode a simple position count cannot see."""
    p = 10
    names = [f"A{i}" for i in range(p)]
    corr = np.full((p, p), 0.95) + np.eye(p) * 0.05
    cov = pd.DataFrame(corr * 0.0001, index=names, columns=names)
    w = np.full(p, 1.0 / p)
    assert dv.effective_bets(w, cov) < 1.5
    assert 1.0 / np.sum(w**2) == pytest.approx(10.0)      # naive count says 10


def test_equicorrelation_matches_the_closed_form():
    """Exact known answer: p equicorrelated equal-risk sleeves at equal weight
    have DR^2 = p / (1 + (p-1)rho)."""
    p = 6
    names = [f"A{i}" for i in range(p)]
    w = np.full(p, 1.0 / p)
    for rho in (0.0, 0.3, 0.6, 0.9):
        corr = np.full((p, p), rho) + np.eye(p) * (1 - rho)
        cov = pd.DataFrame(corr * 0.0001, index=names, columns=names)
        expected = p / (1 + (p - 1) * rho)
        assert dv.effective_bets(w, cov) == pytest.approx(expected, rel=1e-9)


def test_diversification_increases_as_correlation_falls():
    p = 6
    names = [f"A{i}" for i in range(p)]
    w = np.full(p, 1.0 / p)
    previous_dr = previous_bets = 0.0
    for rho in (0.9, 0.6, 0.3, 0.0):
        corr = np.full((p, p), rho) + np.eye(p) * (1 - rho)
        cov = pd.DataFrame(corr * 0.0001, index=names, columns=names)
        dr = dv.diversification_ratio(w, cov)
        bets = dv.effective_bets(w, cov)
        assert dr > previous_dr and bets > previous_bets
        previous_dr, previous_bets = dr, bets


def test_pca_variant_is_degenerate_for_equicorrelated_equal_weights():
    """Recorded, not hidden: this is why the PCA measure is a cross-check and
    not the headline. An equally weighted equicorrelated portfolio IS the first
    principal component, so it scores exactly one bet at ANY positive
    correlation, then jumps to p at rho exactly zero."""
    p = 6
    names = [f"A{i}" for i in range(p)]
    w = np.full(p, 1.0 / p)
    for rho in (0.2, 0.5, 0.9):
        corr = np.full((p, p), rho) + np.eye(p) * (1 - rho)
        cov = pd.DataFrame(corr * 0.0001, index=names, columns=names)
        assert dv.effective_bets_pca(w, cov) == pytest.approx(1.0, abs=1e-9)
        assert dv.effective_bets(w, cov) > 1.0        # the headline still moves

    identity = pd.DataFrame(np.eye(p) * 0.0001, index=names, columns=names)
    assert dv.effective_bets_pca(w, identity) == pytest.approx(p, rel=1e-9)


def test_measures_are_scale_invariant_in_the_weights():
    """A portfolio holding a cash residual can pass unnormalised risky weights."""
    frame = independent(p=5)
    cov = frame.cov()
    w = np.array([0.3, 0.2, 0.1, 0.15, 0.05])          # sums to 0.8, not 1
    assert dv.diversification_ratio(w, cov) == pytest.approx(
        dv.diversification_ratio(w / w.sum(), cov))
    assert dv.effective_bets(w, cov) == pytest.approx(
        dv.effective_bets(w / w.sum(), cov))


def test_concentrated_weights_reduce_effective_bets():
    frame = independent(p=5)
    cov = frame.cov()
    equal = np.full(5, 0.2)
    concentrated = np.array([0.9, 0.025, 0.025, 0.025, 0.025])
    assert dv.effective_bets(concentrated, cov) < dv.effective_bets(equal, cov)


# ---------------------------------------------------------------- report + guards

def test_report_defaults_to_equal_weights_and_labels_itself():
    report = dv.diversification_report(independent(p=4), label="universe")
    assert report["label"] == "universe"
    assert report["n_sleeves"] == 4
    assert report["diversification_ratio"] == pytest.approx(2.0, rel=0.1)
    assert report["effective_bets"] == pytest.approx(4.0, rel=0.2)
    assert "effective_bets_pca" in report


def test_report_accepts_a_weight_series_aligned_by_name():
    frame = independent(p=4)
    weights = pd.Series({"A3": 0.7, "A0": 0.1, "A1": 0.1, "A2": 0.1})
    report = dv.diversification_report(frame, weights)
    assert report["effective_bets"] < 4.0


def test_bad_inputs_are_rejected():
    frame = independent(p=3)
    with pytest.raises(ValueError, match=">= 60 complete observations"):
        dv.average_pairwise_correlation(frame.iloc[:10])
    with pytest.raises(ValueError, match="at least two sleeves"):
        dv.average_pairwise_correlation(frame[["A0"]])
    with pytest.raises(ValueError, match="one entry per sleeve"):
        dv.diversification_ratio(np.ones(2), frame.cov())
    with pytest.raises(ValueError, match="all zero"):
        dv.diversification_ratio(np.zeros(3), frame.cov())
