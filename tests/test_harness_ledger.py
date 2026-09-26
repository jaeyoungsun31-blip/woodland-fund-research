"""Trials ledger + deflated Sharpe (DESIGN.md §7, CLAUDE.md rule 4)."""

import math

import numpy as np
import pandas as pd
import pytest

from woodland.harness import deflated as dfl
from woodland.harness.ledger import TrialsLedger, config_hash

# ---------------------------------------------------------------- ledger

def test_config_hash_ignores_key_order_but_not_values():
    assert config_hash({"a": 1, "b": 2}) == config_hash({"b": 2, "a": 1})
    assert config_hash({"a": 1}) != config_hash({"a": 2})


def test_every_config_is_counted_including_abandoned(tmp_path):
    """The rule the ledger exists to enforce: abandoned trials still count."""
    with TrialsLedger(tmp_path / "t.db") as led:
        led.record("trend", {"lb": 10}, metrics={"sharpe_rf0": 0.8})
        led.record("trend", {"lb": 11}, status="abandoned", notes="looked bad, stopped early")
        led.record("trend", {"lb": 12}, status="error", notes="crashed")
        assert led.n_trials("trend") == 3
        assert led.n_trials("trend", distinct=False) == 3


def test_rescoring_one_config_is_not_a_new_lottery_ticket(tmp_path):
    with TrialsLedger(tmp_path / "t.db") as led:
        for split in range(5):
            led.record("trend", {"lb": 10}, split_index=split, metrics={"sharpe_rf0": 0.5})
        led.record("trend", {"lb": 12}, metrics={"sharpe_rf0": 0.9})
        assert led.n_trials("trend") == 2            # distinct configs
        assert led.n_trials("trend", distinct=False) == 6   # rows / compute spent


def test_studies_are_isolated(tmp_path):
    with TrialsLedger(tmp_path / "t.db") as led:
        led.record("trend", {"lb": 10})
        led.record("xsmom", {"k": 3})
        led.record("xsmom", {"k": 4})
        assert led.n_trials("trend") == 1
        assert led.n_trials("xsmom") == 2
        assert led.n_trials() == 3
        assert led.studies() == ["trend", "xsmom"]


def test_ledger_persists_across_reopen(tmp_path):
    path = tmp_path / "t.db"
    with TrialsLedger(path) as led:
        led.record("trend", {"lb": 10}, metrics={"sharpe_rf0": 0.8}, cost_bps=5.0)
    with TrialsLedger(path) as led:
        assert led.n_trials("trend") == 1
        row = led.trials("trend").iloc[0]
        assert row["sharpe"] == pytest.approx(0.8)
        assert row["cost_bps"] == pytest.approx(5.0)
        assert row["status"] == "evaluated"


def test_bad_status_rejected(tmp_path):
    with TrialsLedger(tmp_path / "t.db") as led, pytest.raises(
        ValueError, match="status must be"
    ):
        led.record("trend", {"lb": 10}, status="promoted")


def test_config_sharpes_averages_per_config(tmp_path):
    with TrialsLedger(tmp_path / "t.db") as led:
        led.record("s", {"lb": 10}, metrics={"sharpe_rf0": 0.4})
        led.record("s", {"lb": 10}, metrics={"sharpe_rf0": 0.6})
        led.record("s", {"lb": 20}, metrics={"sharpe_rf0": 1.0})
        led.record("s", {"lb": 30}, status="abandoned")      # no sharpe -> excluded
        sh = led.config_sharpes("s")
        assert len(sh) == 2
        assert sorted(sh.round(6)) == [0.5, 1.0]


# ---------------------------------------------------------------- deflation

def test_selection_hurdle_grows_with_trials_and_spread():
    assert dfl.expected_max_sharpe(0.01, 1) == 0.0        # nothing selected
    a = dfl.expected_max_sharpe(0.01, 10)
    b = dfl.expected_max_sharpe(0.01, 400)
    assert 0 < a < b, "more trials must raise the bar"
    c = dfl.expected_max_sharpe(0.04, 400)
    assert c > b, "a wider spread of trial Sharpes must raise the bar"


def test_psr_rises_with_sample_length():
    kw = dict(sr=0.05, benchmark_sr=0.0, skew=0.0, kurtosis=3.0)
    assert dfl.probabilistic_sharpe(n_obs=250, **kw) < dfl.probabilistic_sharpe(n_obs=2500, **kw)


def test_negative_skew_and_fat_tails_reduce_confidence():
    base = dfl.probabilistic_sharpe(0.06, 0.0, 1000, skew=0.0, kurtosis=3.0)
    skewed = dfl.probabilistic_sharpe(0.06, 0.0, 1000, skew=-1.5, kurtosis=3.0)
    fat = dfl.probabilistic_sharpe(0.06, 0.0, 1000, skew=0.0, kurtosis=12.0)
    assert skewed < base and fat < base


def test_lucky_winner_from_many_trials_is_deflated_away():
    """The headline case. A pure-noise strategy that happened to score well
    must not survive once the trial count is honest."""
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2010-01-01", periods=252 * 10)
    # a noise series that lucked into a ~0.7 annualized Sharpe
    r = pd.Series(rng.normal(0.7 / 252 * 0.01 / 0.01 * 0.0004, 0.01, len(idx)), index=idx)
    trial_sharpes = pd.Series(rng.normal(0.0, 0.45, 400))   # 400 configs, wide spread

    honest = dfl.deflated_sharpe(r, n_trials=400, trial_sharpes=trial_sharpes)
    naive = dfl.deflated_sharpe(r, n_trials=1, trial_sharpes=trial_sharpes)

    assert honest["sr0_annual"] > 1.0, "400 wide trials should set a high bar"
    assert honest["dsr"] < naive["dsr"], "counting trials must lower confidence"
    assert honest["dsr"] < 0.95, "a lucky winner must not clear the bar"
    assert "lottery tickets" in dfl.report(honest)


def test_single_trial_reduces_to_psr_against_zero():
    rng = np.random.default_rng(4)
    r = pd.Series(rng.normal(0.0005, 0.01, 2520),
                  index=pd.bdate_range("2010-01-01", periods=2520))
    res = dfl.deflated_sharpe(r, n_trials=1, var_trial_sr_annual=0.2)
    assert res["sr0_annual"] == 0.0
    assert res["dsr"] == pytest.approx(res["psr_vs_zero"])


def test_annualization_is_consistent():
    rng = np.random.default_rng(5)
    r = pd.Series(rng.normal(0.0004, 0.01, 2520),
                  index=pd.bdate_range("2010-01-01", periods=2520))
    res = dfl.deflated_sharpe(r, n_trials=50, var_trial_sr_annual=0.25)
    expected = r.mean() / r.std(ddof=1) * math.sqrt(252)
    assert res["sharpe_annual"] == pytest.approx(expected, rel=1e-9)


def test_degenerate_series_reports_rather_than_crashes():
    flat = pd.Series([0.0] * 100, index=pd.bdate_range("2020-01-01", periods=100))
    res = dfl.deflated_sharpe(flat, n_trials=10, var_trial_sr_annual=0.1)
    assert math.isnan(res["dsr"])
    assert "not computable" in dfl.report(res)


def test_deflated_sharpe_requires_a_spread_input():
    r = pd.Series([0.001, -0.002, 0.003] * 200)
    with pytest.raises(ValueError, match="trial_sharpes or var_trial_sr_annual"):
        dfl.deflated_sharpe(r, n_trials=10)


def test_deflated_sharpe_report_discloses_effective_breadth():
    rng = np.random.default_rng(19)
    returns = pd.Series(rng.normal(0.0004, 0.01, 1000))
    trial_sharpes = pd.Series([0.58, 0.62, 0.68])

    result = dfl.deflated_sharpe(returns, n_trials=3, trial_sharpes=trial_sharpes)
    rendered = dfl.report(result)

    assert result["trial_sharpe_spread_annual"] == pytest.approx(0.10)
    assert "Effective breadth: 3 distinct configs" in rendered
    assert "Near-collinear trials" in rendered


def test_ledger_feeds_deflation_end_to_end(tmp_path):
    """The wiring that matters: trial count and spread come FROM the ledger."""
    rng = np.random.default_rng(7)
    with TrialsLedger(tmp_path / "t.db") as led:
        for lb in range(3, 60):
            led.record("trend", {"lookback_months": lb},
                       metrics={"sharpe_rf0": float(rng.normal(0.2, 0.4))})
        n = led.n_trials("trend")
        sharpes = led.config_sharpes("trend")

    assert n == 57 and len(sharpes) == 57
    r = pd.Series(rng.normal(0.0004, 0.01, 2520),
                  index=pd.bdate_range("2010-01-01", periods=2520))
    res = dfl.deflated_sharpe(r, n_trials=n, trial_sharpes=sharpes)
    assert res["n_trials"] == 57
    assert res["sr0_annual"] > 0
