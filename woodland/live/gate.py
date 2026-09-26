"""Executable form of the binding 2026-09-01 promotion gate."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

import pandas as pd

from woodland import metrics, stats

PRIMARY_COST_BPS = 5.0
STRESS_COST_BPS = 10.0
MIN_SHARPE_ADVANTAGE = 0.10
MAX_DRAWDOWN_MULTIPLE = 1.25
MAX_TURNOVER_MULTIPLE = 1.50


@dataclass(frozen=True)
class PortfolioEvidence:
    """OOS evidence required by every side of the promotion gate."""

    name: str
    returns: Mapping[float, pd.Series]
    turnover: pd.Series

    def series(self, cost_bps: float) -> pd.Series:
        try:
            return self.returns[cost_bps]
        except KeyError as error:
            raise ValueError(f"{self.name} has no {cost_bps:g} bps return series") from error


@dataclass(frozen=True)
class GateCondition:
    number: int
    name: str
    passed: bool
    observed: float
    threshold: float
    comparison: str


@dataclass(frozen=True)
class InferenceResult:
    cost_bps: float
    bootstrap: stats.SharpeComparison
    hac: stats.SharpeComparison


@dataclass(frozen=True)
class GateVerdict:
    challenger: str
    incumbent: str
    completed: bool
    promote: bool
    decision: str
    conditions: tuple[GateCondition, ...]
    inference: tuple[InferenceResult, ...]
    convention: str = "Sharpe on aligned daily excess returns"

    @property
    def passed(self) -> tuple[str, ...]:
        return tuple(condition.name for condition in self.conditions if condition.passed)

    @property
    def failed(self) -> tuple[str, ...]:
        return tuple(condition.name for condition in self.conditions if not condition.passed)

    def to_dict(self) -> dict[str, object]:
        return {
            "challenger": self.challenger,
            "incumbent": self.incumbent,
            "completed": self.completed,
            "promote": self.promote,
            "decision": self.decision,
            "convention": self.convention,
            "conditions": [asdict(condition) for condition in self.conditions],
            "inference": [
                {
                    "cost_bps": item.cost_bps,
                    "bootstrap": asdict(item.bootstrap),
                    "hac": asdict(item.hac),
                }
                for item in self.inference
            ],
        }


def _aligned(
    challenger: pd.Series, incumbent: pd.Series, risk_free: pd.Series
) -> tuple[pd.Series, pd.Series, pd.Series]:
    frame = pd.DataFrame(
        {"challenger": challenger, "incumbent": incumbent, "risk_free": risk_free}
    ).dropna()
    if len(frame) < 30:
        raise ValueError(f"promotion gate needs >=30 aligned observations, got {len(frame)}")
    return frame["challenger"], frame["incumbent"], frame["risk_free"]


def evaluate_gate(
    challenger: PortfolioEvidence,
    incumbent: PortfolioEvidence,
    risk_free: pd.Series,
    *,
    n_resamples: int = stats.DEFAULT_RESAMPLES,
    block_length: float = stats.DEFAULT_BLOCK_LENGTH,
    seed: int | None = 0,
) -> GateVerdict:
    """Apply all four frozen conditions; statistical evidence is descriptive.

    The pre-registration does not make a p-value a fifth condition, so the
    paired bootstrap and HAC results are returned beside, but do not alter,
    the four-condition decision.
    """
    deltas: dict[float, float] = {}
    aligned: dict[float, tuple[pd.Series, pd.Series, pd.Series]] = {}
    for cost in (PRIMARY_COST_BPS, STRESS_COST_BPS):
        values = _aligned(challenger.series(cost), incumbent.series(cost), risk_free)
        aligned[cost] = values
        candidate, current, rf = values
        deltas[cost] = metrics.sharpe(candidate, rf_daily=rf) - metrics.sharpe(
            current, rf_daily=rf
        )

    candidate_primary, current_primary, _ = aligned[PRIMARY_COST_BPS]
    candidate_drawdown = abs(metrics.max_drawdown(candidate_primary))
    current_drawdown = abs(metrics.max_drawdown(current_primary))
    drawdown_limit = current_drawdown * MAX_DRAWDOWN_MULTIPLE
    candidate_turnover = metrics.ann_turnover(challenger.turnover)
    current_turnover = metrics.ann_turnover(incumbent.turnover)
    turnover_limit = current_turnover * MAX_TURNOVER_MULTIPLE

    conditions = (
        GateCondition(
            1,
            "net Sharpe advantage at 5 bps",
            deltas[PRIMARY_COST_BPS] >= MIN_SHARPE_ADVANTAGE,
            deltas[PRIMARY_COST_BPS],
            MIN_SHARPE_ADVANTAGE,
            ">=",
        ),
        GateCondition(
            2,
            "maximum drawdown multiple",
            candidate_drawdown <= drawdown_limit,
            candidate_drawdown,
            drawdown_limit,
            "<=",
        ),
        GateCondition(
            3,
            "net Sharpe advantage at 10 bps",
            deltas[STRESS_COST_BPS] >= MIN_SHARPE_ADVANTAGE,
            deltas[STRESS_COST_BPS],
            MIN_SHARPE_ADVANTAGE,
            ">=",
        ),
        GateCondition(
            4,
            "annualized turnover multiple",
            candidate_turnover <= turnover_limit,
            candidate_turnover,
            turnover_limit,
            "<=",
        ),
    )

    inference: list[InferenceResult] = []
    for cost, (candidate, current, rf) in aligned.items():
        inference.append(
            InferenceResult(
                cost_bps=cost,
                bootstrap=stats.bootstrap_sharpe_difference(
                    candidate,
                    current,
                    name_a=challenger.name,
                    name_b=incumbent.name,
                    block_length=block_length,
                    n_resamples=n_resamples,
                    seed=seed,
                    rf_daily=rf,
                ),
                hac=stats.ledoit_wolf_sharpe_test(
                    candidate,
                    current,
                    name_a=challenger.name,
                    name_b=incumbent.name,
                    rf_daily=rf,
                ),
            )
        )

    promote = all(condition.passed for condition in conditions)
    return GateVerdict(
        challenger=challenger.name,
        incumbent=incumbent.name,
        completed=True,
        promote=promote,
        decision="promote challenger" if promote else "keep incumbent",
        conditions=conditions,
        inference=tuple(inference),
    )
