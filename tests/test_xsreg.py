from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from woodland import xsreg


def test_fama_macbeth_recovers_known_standardized_coefficient() -> None:
    rng = np.random.default_rng(1313)
    dates = pd.bdate_range("2000-01-03", periods=700)
    assets = [f"A{i:02d}" for i in range(40)]
    characteristic = pd.Series(np.linspace(-2.0, 2.0, len(assets)), index=assets)
    standardized = (characteristic - characteristic.mean()) / characteristic.std(ddof=1)
    beta = 0.002
    noise = rng.normal(0.0, 0.003, (len(dates), len(assets)))
    returns = pd.DataFrame(
        beta * standardized.to_numpy()[None, :] + noise,
        index=dates,
        columns=assets,
    )

    result = xsreg.fama_macbeth(returns, characteristic, nw_lags=21)

    assert result.mean_slope_daily == pytest.approx(beta, abs=3e-5)
    assert result.t_statistic > 20.0
    assert result.p_value < 1e-10
    assert result.fraction_positive > 0.95


def test_newey_west_rejects_invalid_lag_count() -> None:
    with pytest.raises(ValueError, match="lags"):
        xsreg.newey_west_mean_standard_error(pd.Series([1.0, 2.0]), lags=2)
