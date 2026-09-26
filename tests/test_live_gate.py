from __future__ import annotations

import numpy as np
import pandas as pd

from woodland.live.gate import PortfolioEvidence, evaluate_gate


def _series() -> tuple[pd.DatetimeIndex, pd.Series, pd.Series]:
    index = pd.date_range("2020-01-01", periods=504, freq="B")
    rng = np.random.default_rng(41)
    incumbent = pd.Series(rng.normal(0.00020, 0.008, len(index)), index=index)
    risk_free = pd.Series(0.00005, index=index)
    return index, incumbent, risk_free


def _evidence(name: str, returns: pd.Series, turnover_value: float) -> PortfolioEvidence:
    turnover = pd.Series(turnover_value, index=returns.index)
    return PortfolioEvidence(
        name=name,
        returns={5.0: returns, 10.0: returns - 0.000001},
        turnover=turnover,
    )


def test_gate_promotes_only_when_all_four_registered_conditions_pass() -> None:
    _, incumbent_returns, risk_free = _series()
    incumbent = _evidence("incumbent", incumbent_returns, 0.001)
    challenger = _evidence("challenger", incumbent_returns + 0.00012, 0.0012)

    verdict = evaluate_gate(challenger, incumbent, risk_free, n_resamples=100)

    assert verdict.completed
    assert verdict.promote
    assert verdict.decision == "promote challenger"
    assert len(verdict.passed) == 4
    assert not verdict.failed
    assert verdict.convention == "Sharpe on aligned daily excess returns"
    assert {item.cost_bps for item in verdict.inference} == {5.0, 10.0}


def test_gate_exact_tie_keeps_incumbent_and_records_completed_challenge() -> None:
    _, returns, risk_free = _series()
    incumbent = _evidence("incumbent", returns, 0.001)
    challenger = _evidence("tie", returns.copy(), 0.001)

    verdict = evaluate_gate(challenger, incumbent, risk_free, n_resamples=50)

    assert verdict.completed
    assert not verdict.promote
    assert verdict.decision == "keep incumbent"
    assert "net Sharpe advantage at 5 bps" in verdict.failed
    assert "net Sharpe advantage at 10 bps" in verdict.failed


def test_gate_names_every_failed_condition() -> None:
    index, incumbent_returns, risk_free = _series()
    bad = incumbent_returns.copy()
    bad.iloc[100] = -0.75
    incumbent = _evidence("incumbent", incumbent_returns, 0.001)
    challenger = PortfolioEvidence(
        name="failed",
        returns={5.0: bad, 10.0: bad - 0.000001},
        turnover=pd.Series(0.002, index=index),
    )

    verdict = evaluate_gate(challenger, incumbent, risk_free, n_resamples=50)

    assert verdict.completed and not verdict.promote
    assert set(verdict.failed) == {
        "net Sharpe advantage at 5 bps",
        "maximum drawdown multiple",
        "net Sharpe advantage at 10 bps",
        "annualized turnover multiple",
    }
