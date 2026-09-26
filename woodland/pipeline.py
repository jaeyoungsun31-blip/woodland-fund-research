"""Composable S0-S4 decision pipeline for the v14 ablation study.

The state machine separates information, regime filtering, portfolio sizing,
exposure control, and execution.  Every transition is causal and ordered; the
study runner can therefore replace one stage without silently changing the
others.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum
from typing import Literal, cast

import numpy as np
import pandas as pd

from woodland import backtest, execution
from woodland.metrics import TRADING_DAYS
from woodland.signals import trend

Sizing = Literal["equal", "inverse_vol", "min_variance"]
Exposure = Literal["none", "symmetric", "asymmetric"]
Execution = Literal["none", "partial", "band", "partial_band"]

DEFAULT_LOOKBACKS = tuple(range(4, 11))
REALIZED_VOL_WINDOW = 63
SIZING_WINDOW = 126
TARGET_ANN_VOL = 0.10
LOW_DISPERSION_QUANTILE = 1.0 / 3.0
DISPERSION_MIN_HISTORY = 12


class Stage(IntEnum):
    """Ordered state-machine stages."""

    START = -1
    FEATURES = 0
    REGIME = 1
    SIZING = 2
    EXPOSURE = 3
    EXECUTION = 4


@dataclass(frozen=True)
class PipelineConfig:
    """One fixed pipeline state from the pre-registered v14 grid."""

    regime_filter: bool = False
    sizing: Sizing = "equal"
    exposure: Exposure = "none"
    execution: Execution = "partial"

    def __post_init__(self) -> None:
        if self.sizing not in {"equal", "inverse_vol", "min_variance"}:
            raise ValueError(f"unknown sizing option {self.sizing!r}")
        if self.exposure not in {"none", "symmetric", "asymmetric"}:
            raise ValueError(f"unknown exposure option {self.exposure!r}")
        if self.execution not in {"none", "partial", "band", "partial_band"}:
            raise ValueError(f"unknown execution option {self.execution!r}")


@dataclass(frozen=True)
class FeatureSet:
    """S0 outputs, all computed from observations available by each date."""

    momentum_scores: pd.DataFrame
    realized_vol: pd.DataFrame
    dispersion: pd.Series
    dispersion_threshold: pd.Series


@dataclass(frozen=True)
class PipelineState:
    """Immutable state carried between ordered stage transitions."""

    stage: Stage = Stage.START
    features: FeatureSet | None = None
    regime_scale: pd.Series | None = None
    targets: pd.DataFrame | None = None
    exposure_scale: pd.Series | None = None
    policy: execution.ExecutionPolicy | None = None


@dataclass(frozen=True)
class PipelineOutput:
    """Completed target stream, execution policy, and auditable stage state."""

    targets: pd.DataFrame
    policy: execution.ExecutionPolicy
    state: PipelineState


class DecisionPipeline:
    """Advance a fixed configuration through S0-S4 exactly once."""

    def __init__(
        self,
        risk_assets: list[str],
        config: PipelineConfig,
        *,
        lookbacks: tuple[int, ...] = DEFAULT_LOOKBACKS,
    ) -> None:
        if not risk_assets:
            raise ValueError("risk_assets must not be empty")
        if not lookbacks or min(lookbacks) < 1:
            raise ValueError("lookbacks must contain positive month counts")
        self.risk_assets = list(risk_assets)
        self.config = config
        self.lookbacks = tuple(lookbacks)

    def build(self, prices: pd.DataFrame) -> PipelineOutput:
        """Run all five ordered transitions and return a completed pipeline."""
        missing = sorted(set(self.risk_assets).difference(prices.columns))
        if missing:
            raise ValueError(f"risk assets not in price matrix: {missing}")
        state = self.features(prices, PipelineState())
        state = self.regime(state)
        state = self.sizing(prices, state)
        state = self.exposure(prices, state)
        state = self.execution(state)
        if state.targets is None or state.policy is None:
            raise RuntimeError("pipeline completed without targets or execution policy")
        return PipelineOutput(state.targets, state.policy, state)

    def features(self, prices: pd.DataFrame, state: PipelineState) -> PipelineState:
        """S0: build momentum, realized-volatility, and dispersion features."""
        self._require_next(state, Stage.FEATURES)
        monthly = prices[self.risk_assets].resample("ME").last()
        horizon_returns = [monthly / monthly.shift(months) - 1.0 for months in self.lookbacks]
        momentum_scores = horizon_returns[0].copy()
        for frame in horizon_returns[1:]:
            momentum_scores = momentum_scores.add(frame)
        momentum_scores = momentum_scores / len(horizon_returns)
        dispersion_monthly = momentum_scores.std(axis=1, ddof=0)
        threshold_monthly = (
            dispersion_monthly.shift(1)
            .expanding(min_periods=DISPERSION_MIN_HISTORY)
            .quantile(LOW_DISPERSION_QUANTILE)
        )

        decisions = trend.month_end_index(prices)
        periods = decisions.to_period("M").to_timestamp("M")
        dispersion = pd.Series(
            dispersion_monthly.reindex(periods).to_numpy(dtype=float),
            index=decisions,
            name="dispersion",
        )
        threshold = pd.Series(
            threshold_monthly.reindex(periods).to_numpy(dtype=float),
            index=decisions,
            name="dispersion_threshold",
        )
        realized_vol = (
            prices[self.risk_assets].pct_change().rolling(REALIZED_VOL_WINDOW).std()
            * np.sqrt(TRADING_DAYS)
        )
        equal_targets = trend.ensemble_targets(
            prices,
            risk_assets=self.risk_assets,
            risk_off=None,
            lookback_months=list(self.lookbacks),
        )
        feature_set = FeatureSet(momentum_scores, realized_vol, dispersion, threshold)
        return replace(state, stage=Stage.FEATURES, features=feature_set, targets=equal_targets)

    def regime(self, state: PipelineState) -> PipelineState:
        """S1: identify the fixed bottom-tercile low-dispersion state."""
        self._require_next(state, Stage.REGIME)
        if state.features is None:
            raise RuntimeError("S1 requires S0 features")
        scale = pd.Series(1.0, index=state.features.dispersion.index, name="regime_scale")
        if self.config.regime_filter:
            low = (
                state.features.dispersion_threshold.notna()
                & (state.features.dispersion <= state.features.dispersion_threshold)
            )
            scale.loc[low] = 0.5
        return replace(state, stage=Stage.REGIME, regime_scale=scale)

    def sizing(self, prices: pd.DataFrame, state: PipelineState) -> PipelineState:
        """S2: form equal, inverse-vol, or shrinkage-minimum-variance targets."""
        self._require_next(state, Stage.SIZING)
        if state.regime_scale is None:
            raise RuntimeError("S2 requires S1 regime state")
        targets = trend.ensemble_targets(
            prices,
            risk_assets=self.risk_assets,
            risk_off=None,
            lookback_months=list(self.lookbacks),
            weighting=self.config.sizing,
            vol_window=SIZING_WINDOW,
        )
        decisions = targets.notna().any(axis=1)
        scale = state.regime_scale.reindex(targets.index).fillna(1.0)
        targets.loc[decisions] = targets.loc[decisions].mul(scale.loc[decisions], axis=0)
        return replace(state, stage=Stage.SIZING, targets=targets)

    def exposure(self, prices: pd.DataFrame, state: PipelineState) -> PipelineState:
        """S3: apply the fixed symmetric or slow-risk-on volatility target."""
        self._require_next(state, Stage.EXPOSURE)
        if state.targets is None:
            raise RuntimeError("S3 requires S2 targets")
        targets = state.targets.copy()
        decisions = targets.notna().any(axis=1)
        desired = _desired_exposure_scale(prices, targets)
        applied = pd.Series(1.0, index=targets.index, name="exposure_scale")
        if self.config.exposure == "symmetric":
            applied.loc[decisions] = desired.loc[decisions]
        elif self.config.exposure == "asymmetric":
            previous = 1.0
            for day in targets.index[decisions]:
                wanted = float(desired.loc[day])
                previous = wanted if wanted < previous else previous + 0.5 * (wanted - previous)
                applied.loc[day] = previous
        if self.config.exposure != "none":
            targets.loc[decisions] = targets.loc[decisions].mul(
                applied.loc[decisions], axis=0
            )
        return replace(
            state,
            stage=Stage.EXPOSURE,
            targets=targets,
            exposure_scale=applied,
        )

    def execution(self, state: PipelineState) -> PipelineState:
        """S4: resolve the execution mechanics without running the backtest."""
        self._require_next(state, Stage.EXECUTION)
        policies = {
            "none": execution.ExecutionPolicy(adjustment=1.0, band=0.0),
            "partial": execution.ExecutionPolicy(adjustment=0.5, band=0.0),
            "band": execution.ExecutionPolicy(adjustment=1.0, band=0.05),
            "partial_band": execution.ExecutionPolicy(adjustment=0.5, band=0.05),
        }
        return replace(state, stage=Stage.EXECUTION, policy=policies[self.config.execution])

    @staticmethod
    def _require_next(state: PipelineState, requested: Stage) -> None:
        expected = Stage(int(state.stage) + 1)
        if requested != expected:
            raise ValueError(
                f"out-of-order pipeline transition: state is {state.stage.name}, "
                f"expected {expected.name}, got {requested.name}"
            )


def _desired_exposure_scale(prices: pd.DataFrame, targets: pd.DataFrame) -> pd.Series:
    """Trailing portfolio-vol scale through each date, capped at one."""
    unscaled = backtest.run(prices, targets, cost_bps=0.0)
    realized = unscaled.returns.rolling(REALIZED_VOL_WINDOW).std() * np.sqrt(TRADING_DAYS)
    scale = (TARGET_ANN_VOL / realized).clip(lower=0.0, upper=1.0)
    return cast(pd.Series, scale.where(np.isfinite(scale), 1.0).fillna(1.0))
