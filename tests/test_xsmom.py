from __future__ import annotations

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from woodland import xsmom


def write_archive(path: Path) -> None:
    body = """preamble
  Average Value Weighted Returns -- Daily
,Lo PRIOR,PRIOR 2,PRIOR 3,PRIOR 4,PRIOR 5,PRIOR 6,PRIOR 7,PRIOR 8,PRIOR 9,Hi PRIOR
20200102,1,2,3,4,5,6,7,8,9,10
20200103,-99.99,2,3,4,5,6,7,8,9,10

  Average Equal Weighted Returns -- Daily
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("momentum.csv", body)


def test_parser_selects_value_weighted_daily_block(tmp_path: Path) -> None:
    path = tmp_path / "momentum.zip"
    write_archive(path)
    result = xsmom.parse_daily_deciles(path)
    assert list(result.columns) == xsmom.DECILE_COLUMNS
    assert result.loc[pd.Timestamp("2020-01-02"), "Hi PRIOR"] == pytest.approx(0.10)
    assert pd.isna(result.loc[pd.Timestamp("2020-01-03"), "Lo PRIOR"])


def test_model_turnover_is_zero_for_all_ranks_and_higher_for_narrow_bin() -> None:
    assert xsmom.model_implied_turnover(0.0, 1.0) == pytest.approx(0.0, abs=1e-8)
    top_three = xsmom.model_implied_turnover(0.7, 1.0)
    top_one = xsmom.model_implied_turnover(0.9, 1.0)
    assert 0.0 < top_three < top_one


def test_internal_cost_drag_is_fixed() -> None:
    returns = pd.Series([0.01, -0.02])
    net = xsmom.net_of_internal_cost(returns, 4.0, 25.0)
    expected_drag = 4.0 * 25.0 / 10_000.0 / 252.0
    pd.testing.assert_series_equal(net, (returns - expected_drag).rename("ret"))


def test_stale_cohort_weights_begin_exactly_in_top_three_and_diffuse() -> None:
    initial = xsmom.stale_cohort_weights(0)
    np.testing.assert_allclose(initial[:7], 0.0)
    np.testing.assert_allclose(initial[7:], 1.0 / 3.0)

    one_month = xsmom.stale_cohort_weights(21)
    one_year = xsmom.stale_cohort_weights(252)
    assert one_month.sum() == pytest.approx(1.0)
    assert one_year.sum() == pytest.approx(1.0)
    assert np.all(one_month >= 0.0)
    assert 0.3 < one_year[-3:].sum() < one_month[-3:].sum() < 1.0


def test_formation_dates_use_last_available_calendar_bar() -> None:
    index = pd.bdate_range("2020-01-20", "2021-01-08")
    assert list(xsmom.formation_dates(index, "monthly")[:2]) == [
        pd.Timestamp("2020-01-31"),
        pd.Timestamp("2020-02-28"),
    ]
    assert list(xsmom.formation_dates(index, "quarterly")[:2]) == [
        pd.Timestamp("2020-03-31"),
        pd.Timestamp("2020-06-30"),
    ]
    assert list(xsmom.formation_dates(index, "semiannual")[:2]) == [
        pd.Timestamp("2020-06-30"),
        pd.Timestamp("2020-12-31"),
    ]
    assert list(xsmom.formation_dates(index, "annual")) == [
        pd.Timestamp("2020-12-31"),
        pd.Timestamp("2021-01-08"),
    ]


def test_stale_cohort_formation_affects_only_the_next_return() -> None:
    index = pd.bdate_range("2020-01-01", periods=5)
    values = np.tile(np.arange(1.0, 11.0), (len(index), 1)) / 100.0
    deciles = pd.DataFrame(values, index=index, columns=xsmom.DECILE_COLUMNS)
    result = xsmom.stale_cohort_returns(deciles, pd.DatetimeIndex([index[1]]))
    assert result.iloc[0] == 0.0
    assert result.iloc[1] == 0.0
    assert result.iloc[2] == pytest.approx(0.09)
    assert result.iloc[3] < 0.09


def test_slower_formation_reduces_annualized_turnover() -> None:
    index = pd.bdate_range("2010-01-01", "2019-12-31")
    monthly = xsmom.holding_period_turnover(
        index, xsmom.formation_dates(index, "monthly")
    )
    annual = xsmom.holding_period_turnover(
        index, xsmom.formation_dates(index, "annual")
    )
    assert 0.0 < annual.internal < monthly.internal
    assert annual.initial_purchase == pytest.approx(monthly.initial_purchase)
    assert annual.total < monthly.total
