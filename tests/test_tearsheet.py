import numpy as np
import pandas as pd
import pytest

from woodland import backtest
from woodland.tearsheet import save_tear_sheet


def test_save_tear_sheet_writes_all_backtest_plots(tmp_path):
    index = pd.bdate_range("2024-01-01", periods=260)
    prices = pd.DataFrame(
        {"AAA": 100 * np.cumprod(np.full(len(index), 1.001))}, index=index
    )
    targets = pd.DataFrame({"AAA": 1.0}, index=index)
    result = backtest.run(prices, targets)

    output = save_tear_sheet(result, tmp_path / "tear-sheet.png", title="Test run")

    assert output.exists()
    assert output.stat().st_size > 0


def test_save_tear_sheet_rejects_a_one_bar_sharpe_window(tmp_path):
    result = backtest.run(
        pd.DataFrame({"AAA": [100.0, 101.0]}, index=pd.bdate_range("2024-01-01", periods=2)),
        pd.DataFrame({"AAA": [1.0, 1.0]}, index=pd.bdate_range("2024-01-01", periods=2)),
    )

    with pytest.raises(ValueError, match="at least two"):
        save_tear_sheet(result, tmp_path / "tear-sheet.png", rolling_window=1)
