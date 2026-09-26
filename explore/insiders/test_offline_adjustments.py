from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from offline_adjustments import classify_symbol, event_marks


def bars(close: list[float], factor: list[float], volume: list[int]) -> pd.DataFrame:
    dates = pd.date_range("2020-01-02", periods=len(close), freq="B")
    return pd.DataFrame(
        {
            "open": close,
            "close": close,
            "adjusted_close": np.array(close) * factor,
            "volume": volume,
        },
        index=dates,
    )


def test_split_neutral_and_dividend_return() -> None:
    data = bars([100, 50, 49], [0.5, 1.0, 1.02], [100] * 3)
    classified = classify_symbol(data)
    assert classified.classification.iloc[1] == "split"
    assert classified.total_return.iloc[1] == pytest.approx(0)
    assert classified.classification.iloc[2] == "dividend"
    assert classified.total_return.iloc[2] == pytest.approx(49 / 50 * 1.02 - 1)


def test_adjustment_error_uses_raw_return() -> None:
    data = bars([10, 10], [0.01, 1.0], [100, 100])
    classified = classify_symbol(data)
    assert classified.classification.iloc[1] == "adjustment_error"
    assert classified.total_return.iloc[1] == pytest.approx(0)


def test_defect_requires_reversal_or_zero_volume() -> None:
    data = bars([10, 20, 11, 11, 11, 11, 11], [1] * 7, [100] * 7)
    classified = classify_symbol(data)
    assert classified.classification.iloc[1] == "defect"
    with pytest.raises(ValueError, match="defect"):
        event_marks(classified, data.index[0], data.index[-1])
    persistent = bars([10, 20, 20, 20, 20, 20, 20], [1] * 7, [100] * 7)
    assert classify_symbol(persistent).classification.iloc[1] == "suspected_defect"
    persistent.iloc[1, persistent.columns.get_loc("volume")] = 0
    assert classify_symbol(persistent).classification.iloc[1] == "defect"


def test_entry_open_does_not_receive_prior_factor_step() -> None:
    data = bars([100, 50, 51], [0.5, 1, 1], [100] * 3)
    classified = classify_symbol(data)
    opens, closes = event_marks(classified, data.index[1], data.index[2])
    assert closes[-1] / opens[0] - 1 == pytest.approx(0.02)
