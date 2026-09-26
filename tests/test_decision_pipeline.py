from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from woodland.pipeline import (
    DecisionPipeline,
    Execution,
    Exposure,
    PipelineConfig,
    PipelineState,
    Sizing,
    Stage,
)


def make_pipeline_prices(n_days: int = 1500, seed: int = 1400) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2010-01-04", periods=n_days)
    specs = {
        "SPY": (0.0004, 0.011),
        "EFA": (0.0003, 0.013),
        "EEM": (0.0002, 0.016),
        "TLT": (0.0002, 0.009),
        "IEF": (0.0001, 0.004),
        "GLD": (0.00025, 0.012),
    }
    return pd.DataFrame(
        {
            ticker: 100 * np.cumprod(1 + rng.normal(mean, sd, n_days))
            for ticker, (mean, sd) in specs.items()
        },
        index=index,
    )


ASSETS = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"]


@pytest.mark.parametrize("sizing", ["equal", "inverse_vol", "min_variance"])
@pytest.mark.parametrize("exposure", ["none", "symmetric", "asymmetric"])
@pytest.mark.parametrize("execution", ["none", "partial", "band", "partial_band"])
def test_pipeline_options_complete_in_order(
    sizing: Sizing, exposure: Exposure, execution: Execution
) -> None:
    output = DecisionPipeline(
        ASSETS,
        PipelineConfig(sizing=sizing, exposure=exposure, execution=execution),
    ).build(make_pipeline_prices())

    assert output.state.stage is Stage.EXECUTION
    assert output.targets.dropna(how="all").shape[0] > 20
    assert (output.targets.dropna(how="all").sum(axis=1) <= 1.0 + 1e-9).all()


def test_state_machine_rejects_a_skipped_stage() -> None:
    machine = DecisionPipeline(ASSETS, PipelineConfig())
    with pytest.raises(ValueError, match="out-of-order"):
        machine.regime(PipelineState())


def test_bottom_tercile_threshold_uses_only_prior_months() -> None:
    output = DecisionPipeline(
        ASSETS, PipelineConfig(regime_filter=True)
    ).build(make_pipeline_prices())
    features = output.state.features
    assert features is not None
    first = features.dispersion_threshold.first_valid_index()
    assert first is not None
    prior = features.dispersion.loc[:first].iloc[:-1].dropna()
    assert len(prior) >= 12
    assert features.dispersion_threshold.loc[first] == pytest.approx(
        prior.quantile(1.0 / 3.0)
    )


def test_asymmetric_exposure_restores_more_slowly_than_symmetric() -> None:
    prices = make_pipeline_prices(seed=1404)
    symmetric = DecisionPipeline(
        ASSETS, PipelineConfig(exposure="symmetric")
    ).build(prices)
    asymmetric = DecisionPipeline(
        ASSETS, PipelineConfig(exposure="asymmetric")
    ).build(prices)
    sym = symmetric.state.exposure_scale
    asym = asymmetric.state.exposure_scale
    assert sym is not None and asym is not None
    decisions = symmetric.targets.notna().any(axis=1)
    # Risk reductions are immediate; later risk restoration remains below the
    # symmetric desired scale because only half the gap is restored per month.
    assert (asym.loc[decisions] <= sym.loc[decisions] + 1e-12).all()
    assert (asym.loc[decisions] < sym.loc[decisions] - 1e-9).any()


def test_execution_policies_are_exact() -> None:
    prices = make_pipeline_prices()
    expected: dict[Execution, tuple[float, float]] = {
        "none": (1.0, 0.0),
        "partial": (0.5, 0.0),
        "band": (1.0, 0.05),
        "partial_band": (0.5, 0.05),
    }
    for name, pair in expected.items():
        policy = DecisionPipeline(
            ASSETS, PipelineConfig(execution=name)
        ).build(prices).policy
        assert (policy.adjustment, policy.band) == pair
