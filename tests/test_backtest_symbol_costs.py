"""Per-security costs: actual buys/sells after drift, and flat-cost compatibility."""
import numpy as np
import pandas as pd
import pytest

from woodland import backtest


def fixture():
    index = pd.bdate_range('2020-01-01', periods=4)
    prices = pd.DataFrame({'A': [100., 100., 120., 120.],
                           'B': [100., 100., 100., 100.]}, index=index)
    targets = pd.DataFrame(np.nan, index=index, columns=prices.columns)
    targets.iloc[0] = [0.5, 0.5]
    targets.iloc[2] = [0.25, 0.75]
    return prices, targets


def test_costs_follow_labels_and_drifted_sell_and_buy():
    prices, targets = fixture()
    costs = pd.Series({'B': 30., 'A': 10.})  # deliberately reversed
    result = backtest.run(prices, targets, costs)
    assert result.returns.iloc[1] == pytest.approx(-0.002)
    assert result.returns.iloc[2] == pytest.approx(0.10)
    sold_a = 0.6 / 1.1 - 0.25
    bought_b = 0.75 - 0.5 / 1.1
    assert result.returns.iloc[3] == pytest.approx(-(sold_a * 0.001 + bought_b * 0.003))
    assert result.turnover.iloc[3] == pytest.approx(sold_a + bought_b)
    costs.iloc[:] = 999  # result keeps its own cost assumptions
    assert result.cost_bps['A'] == 10


@pytest.mark.parametrize('cost', [0., 5., 10., 25., 50.])
def test_scalar_broadcast_and_constant_labelled_vector_are_bit_identical(cost):
    prices, targets = fixture()
    scalar = backtest.run(prices, targets, cost)
    vector = backtest.run(prices, targets, {'B': cost, 'A': cost})
    for field in ['returns', 'equity', 'turnover']:
        pd.testing.assert_series_equal(
            getattr(scalar, field), getattr(vector, field), check_exact=True
        )
    pd.testing.assert_frame_equal(scalar.holdings, vector.holdings, check_exact=True)


@pytest.mark.parametrize('costs', [
    {'A': 10.}, {'A': 10., 'B': 5., 'C': 1.},
    {'A': -1., 'B': 5.}, {'A': np.nan, 'B': 5.}, {'A': np.inf, 'B': 5.},
    pd.Series([1., 2.], index=['A', 'A']), -1., np.nan, np.inf,
])
def test_missing_ambiguous_or_invalid_costs_refuse(costs):
    prices, targets = fixture()
    with pytest.raises(ValueError, match='cost_bps'):
        backtest.run(prices, targets, costs)
