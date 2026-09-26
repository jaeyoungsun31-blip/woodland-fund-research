"""Known-answer tests for statistical inference (HANDOFF 2026-09-01c, step 1).

Written and passing BEFORE any real return series was touched.

The headline test is `test_naive_iid_test_over_rejects_but_bootstrap_does_not`:
it measures the actual size of each test on autocorrelated data under a TRUE
null, which is the only honest way to claim the block bootstrap is buying
something.
"""

import math

import numpy as np
import pandas as pd
import pytest

from woodland import stats


def ar1(n, phi, mu=0.0004, sigma=0.01, rng=None):
    """AR(1) return series with the requested lag-1 autocorrelation."""
    rng = rng or np.random.default_rng(0)
    innovation = rng.normal(0.0, sigma * math.sqrt(1 - phi**2), n)
    out = np.empty(n)
    out[0] = innovation[0]
    for i in range(1, n):
        out[i] = phi * out[i - 1] + innovation[i]
    return out + mu


# ---------------------------------------------------------------- resampler

def test_bootstrap_indices_are_in_range_and_right_shape():
    rng = np.random.default_rng(1)
    idx = stats.stationary_bootstrap_indices(500, 21, 64, rng)
    assert idx.shape == (64, 500)
    assert idx.min() >= 0 and idx.max() < 500


def test_blocks_are_consecutive_and_wrap():
    """Within a block the index must advance by exactly one, modulo n."""
    rng = np.random.default_rng(2)
    n = 200
    idx = stats.stationary_bootstrap_indices(n, block_length=25, n_resamples=40, rng=rng)
    steps = (idx[:, 1:] - idx[:, :-1]) % n
    continuing = steps == 1
    # with mean block length 25, most transitions continue a block
    assert continuing.mean() > 0.8
    assert idx.max() < n                      # wrapping stays in range


def test_expected_block_length_matches_the_parameter():
    rng = np.random.default_rng(3)
    n = 4000
    for target in (5, 21, 60):
        idx = stats.stationary_bootstrap_indices(n, target, 40, rng)
        restarts = ((idx[:, 1:] - idx[:, :-1]) % n) != 1
        observed = 1.0 / restarts.mean()
        assert observed == pytest.approx(target, rel=0.25), (target, observed)


def test_bootstrap_preserves_autocorrelation_that_an_iid_resample_destroys():
    """The property the whole module rests on."""
    series = ar1(4000, phi=0.4, rng=np.random.default_rng(4))
    truth = pd.Series(series).autocorr(1)

    rng = np.random.default_rng(5)
    idx = stats.stationary_bootstrap_indices(len(series), 21, 200, rng)
    block_rho = np.mean([pd.Series(series[row]).autocorr(1) for row in idx])
    iid_idx = rng.integers(0, len(series), (200, len(series)))
    iid_rho = np.mean([pd.Series(series[row]).autocorr(1) for row in iid_idx])

    assert truth > 0.3
    assert block_rho > 0.7 * truth, "block bootstrap must retain most autocorrelation"
    assert abs(iid_rho) < 0.05, "iid resampling must destroy it"


def test_resampler_rejects_bad_arguments():
    rng = np.random.default_rng(6)
    with pytest.raises(ValueError, match="at least two"):
        stats.stationary_bootstrap_indices(1, 21, 10, rng)
    with pytest.raises(ValueError, match="block_length"):
        stats.stationary_bootstrap_indices(100, 0.5, 10, rng)
    with pytest.raises(ValueError, match="n_resamples"):
        stats.stationary_bootstrap_indices(100, 21, 0, rng)


def test_bootstrap_is_reproducible_from_the_seed():
    a = pd.Series(np.random.default_rng(7).normal(0.0005, 0.01, 800))
    b = pd.Series(np.random.default_rng(8).normal(0.0004, 0.01, 800))
    kw = dict(n_resamples=300, seed=42)
    assert (stats.bootstrap_sharpe_difference(a, b, **kw).p_value
            == stats.bootstrap_sharpe_difference(a, b, **kw).p_value)


# ---------------------------------------------------------------- known answers

def test_hac_standard_error_matches_the_iid_formula_on_iid_data():
    """With no autocorrelation the HAC test must collapse to the textbook
    standard error — otherwise it is not a generalization of it."""
    rng = np.random.default_rng(9)
    n = 20_000
    a = pd.Series(rng.normal(0.0005, 0.01, n))
    b = pd.Series(rng.normal(0.0002, 0.01, n))

    hac = stats.ledoit_wolf_sharpe_test(a, b)
    naive = stats.iid_sharpe_test(a, b)
    assert hac.standard_error == pytest.approx(naive.standard_error, rel=0.12)


def test_bootstrap_standard_error_matches_analytic_on_iid_data():
    """Bootstrap CI width must match the analytic one when iid holds."""
    rng = np.random.default_rng(10)
    n = 8000
    a = pd.Series(rng.normal(0.0005, 0.01, n))
    b = pd.Series(rng.normal(0.0002, 0.01, n))

    boot = stats.bootstrap_sharpe_difference(a, b, n_resamples=2000)
    naive = stats.iid_sharpe_test(a, b)
    boot_width = boot.ci_high - boot.ci_low
    naive_width = naive.ci_high - naive.ci_low
    assert boot_width == pytest.approx(naive_width, rel=0.15)


def test_single_sharpe_ci_matches_the_analytic_iid_width():
    """Var(SR) ~ (1 + SR^2/2)/n for iid normal returns."""
    rng = np.random.default_rng(11)
    n = 10_000
    r = pd.Series(rng.normal(0.0006, 0.01, n))
    point, low, high = stats.sharpe_confidence_interval(r, n_resamples=2000)

    sr_period = point / math.sqrt(stats.TRADING_DAYS)
    analytic_half = 1.96 * math.sqrt((1 + sr_period**2 / 2) / n) * math.sqrt(stats.TRADING_DAYS)
    assert (high - low) / 2 == pytest.approx(analytic_half, rel=0.15)
    assert low < point < high


def test_identical_series_give_zero_difference_and_no_significance():
    r = pd.Series(np.random.default_rng(12).normal(0.0005, 0.01, 1500))
    boot = stats.bootstrap_sharpe_difference(r, r.copy(), n_resamples=400)
    assert boot.difference == pytest.approx(0.0, abs=1e-12)
    assert boot.p_value > 0.9
    hac = stats.ledoit_wolf_sharpe_test(r, r.copy())
    assert hac.p_value == pytest.approx(1.0, abs=1e-6)


def test_a_large_true_difference_is_detected():
    rng = np.random.default_rng(13)
    n = 4000
    a = pd.Series(rng.normal(0.0010, 0.01, n))
    b = pd.Series(rng.normal(-0.0002, 0.01, n))
    for result in (stats.bootstrap_sharpe_difference(a, b, n_resamples=800),
                   stats.ledoit_wolf_sharpe_test(a, b)):
        assert result.difference > 0
        assert result.p_value < 0.01
        assert result.ci_low > 0, "CI should exclude zero"


def test_paired_resampling_narrows_the_interval_for_correlated_strategies():
    """Two strategies sharing most of their risk have a far better determined
    DIFFERENCE than either level — the reason rows are resampled jointly."""
    rng = np.random.default_rng(14)
    n = 3000
    common = rng.normal(0.0004, 0.01, n)
    a = pd.Series(common + rng.normal(0.0001, 0.002, n))
    b = pd.Series(common + rng.normal(0.0000, 0.002, n))

    paired = stats.bootstrap_sharpe_difference(a, b, n_resamples=1500)
    _, a_low, a_high = stats.sharpe_confidence_interval(a, n_resamples=1500)
    assert (paired.ci_high - paired.ci_low) < 0.5 * (a_high - a_low)


def test_sign_convention_is_a_minus_b():
    rng = np.random.default_rng(15)
    a = pd.Series(rng.normal(0.0009, 0.01, 1200))
    b = pd.Series(rng.normal(0.0001, 0.01, 1200))
    for result in (stats.bootstrap_sharpe_difference(a, b, n_resamples=400),
                   stats.ledoit_wolf_sharpe_test(a, b),
                   stats.iid_sharpe_test(a, b)):
        assert result.difference == pytest.approx(result.sharpe_a - result.sharpe_b, rel=1e-9)


def test_cash_heavy_pair_changes_under_excess_return_convention():
    """A shared risk-free subtraction must not be silently ignored.

    The cash-heavy portfolio is 60% risky asset and 40% cash, plus negligible
    independent noise to keep the HAC covariance non-degenerate. After
    subtracting the risk-free return its excess return is nearly a scaled copy
    of the fully invested portfolio's excess return. At rf=0, the cash return
    mechanically gives the cash-heavy portfolio a different Sharpe.
    """
    index = pd.date_range("2000-01-03", periods=1_500, freq="B")
    rng = np.random.default_rng(150)
    risky = pd.Series(rng.normal(0.0004, 0.01, len(index)), index=index)
    rf_daily = pd.Series(0.03 / stats.TRADING_DAYS, index=index)
    cash_heavy = 0.6 * risky + 0.4 * rf_daily + rng.normal(0.0, 1e-5, len(index))

    rf0_boot = stats.bootstrap_sharpe_difference(
        cash_heavy, risky, n_resamples=400
    )
    excess_boot = stats.bootstrap_sharpe_difference(
        cash_heavy, risky, n_resamples=400, rf_daily=rf_daily
    )
    rf0_hac = stats.ledoit_wolf_sharpe_test(cash_heavy, risky)
    excess_hac = stats.ledoit_wolf_sharpe_test(
        cash_heavy, risky, rf_daily=rf_daily
    )

    assert abs(rf0_boot.difference - excess_boot.difference) > 0.05
    assert abs(rf0_hac.difference - excess_hac.difference) > 0.05
    assert rf0_hac.difference == pytest.approx(rf0_boot.difference, abs=1e-4)
    assert excess_hac.difference == pytest.approx(excess_boot.difference, abs=1e-4)


def test_study_paired_inference_helpers_use_supplied_risk_free(monkeypatch):
    """The vectorized v15/v17 paths must pass through the same convention."""
    from scripts import run_sleeve_overlay as v17
    from scripts import run_xsmom_holding as v15

    monkeypatch.setattr(v17, "V17_BOOTSTRAP_RESAMPLES", 100)
    monkeypatch.setattr(v15, "BOOTSTRAP_RESAMPLES", 100)
    index = pd.date_range("2000-01-03", periods=1_000, freq="B")
    rng = np.random.default_rng(151)
    risky = pd.Series(rng.normal(0.0004, 0.01, len(index)), index=index)
    rf_daily = pd.Series(0.03 / stats.TRADING_DAYS, index=index)
    cash_heavy = 0.6 * risky + 0.4 * rf_daily + rng.normal(0.0, 1e-5, len(index))

    v17_rf0 = v17.paired_inference([(10.0, "cash_heavy", cash_heavy, risky)])
    v17_excess = v17.paired_inference(
        [(10.0, "cash_heavy", cash_heavy, risky)], rf_daily=rf_daily
    )
    v15_rf0 = v15.paired_inference(
        [(10.0, "cash_heavy", "invested", cash_heavy, risky)]
    )
    v15_excess = v15.paired_inference(
        [(10.0, "cash_heavy", "invested", cash_heavy, risky)],
        rf_daily=rf_daily,
    )

    assert abs(v17_rf0.iloc[0].delta_sharpe - v17_excess.iloc[0].delta_sharpe) > 0.05
    assert abs(v15_rf0.iloc[0].delta_sharpe - v15_excess.iloc[0].delta_sharpe) > 0.05


# ---------------------------------------------------------------- the point

def test_naive_iid_test_over_rejects_but_bootstrap_does_not():
    """Measured size under a TRUE null on autocorrelated data.

    Two independent AR(1) series with identical parameters have identical true
    Sharpes, so every rejection is a false positive. At a nominal 5% the naive
    iid test should reject far too often; the block bootstrap and the HAC test
    should stay near nominal.
    """
    trials, n, phi = 220, 1200, 0.35
    naive_hits = boot_hits = hac_hits = 0

    for trial in range(trials):
        rng = np.random.default_rng(1000 + trial)
        a = pd.Series(ar1(n, phi, rng=rng))
        b = pd.Series(ar1(n, phi, rng=rng))          # same DGP -> true diff is 0
        naive_hits += stats.iid_sharpe_test(a, b).p_value < 0.05
        boot_hits += stats.bootstrap_sharpe_difference(
            a, b, n_resamples=200, seed=trial).p_value < 0.05
        hac_hits += stats.ledoit_wolf_sharpe_test(a, b).p_value < 0.05

    naive_size = naive_hits / trials
    boot_size = boot_hits / trials
    hac_size = hac_hits / trials

    assert naive_size > 0.12, f"naive test should over-reject badly, got {naive_size:.3f}"
    assert boot_size < 0.10, f"block bootstrap should hold size, got {boot_size:.3f}"
    assert hac_size < 0.10, f"HAC test should hold size, got {hac_size:.3f}"
    assert naive_size > 2 * boot_size, (
        f"naive {naive_size:.3f} vs bootstrap {boot_size:.3f} — the whole point"
    )


def test_short_series_are_rejected_not_silently_analysed():
    short = pd.Series(np.random.default_rng(16).normal(0, 0.01, 20))
    with pytest.raises(ValueError, match=">= 30"):
        stats.bootstrap_sharpe_difference(short, short.copy())
    with pytest.raises(ValueError, match=">= 30"):
        stats.ledoit_wolf_sharpe_test(short, short.copy())


def test_zero_variance_series_reports_rather_than_crashes():
    flat = pd.Series([0.0] * 500)
    live = pd.Series(np.random.default_rng(17).normal(0.0005, 0.01, 500))
    with pytest.raises(ValueError, match="zero variance"):
        stats.ledoit_wolf_sharpe_test(flat, live)


def test_summary_states_the_verdict_in_words():
    rng = np.random.default_rng(18)
    a = pd.Series(rng.normal(0.0012, 0.01, 2000))
    b = pd.Series(rng.normal(-0.0003, 0.01, 2000))
    text = stats.bootstrap_sharpe_difference(a, b, n_resamples=400).summary()
    assert "95% CI" in text and "resamples" in text and "block length" in text
    assert "distinguishable" in text
