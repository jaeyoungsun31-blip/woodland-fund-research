import numpy as np
import pandas as pd
import pytest

from woodland import backtest
from woodland.snapshot import bound_frame, frame_hash


def test_pin_and_content_hash():
    p = pd.DataFrame(
        {"A": [1.0, 2.0, 3.0]}, index=pd.to_datetime(["2026-09-03", "2026-09-04", "2026-09-08"])
    )
    assert len(bound_frame(p)) == 2
    changed = p.copy()
    changed.iloc[-1] = 900
    assert frame_hash(bound_frame(p)) == frame_hash(bound_frame(changed))
    changed.iloc[0] = 4
    assert frame_hash(bound_frame(p)) != frame_hash(bound_frame(changed))
    t = p * 0 + 1
    assert backtest.run(p, t).returns.index[-1] == pd.Timestamp("2026-09-04")


def test_returns_path_matches_price_path_without_inventing_levels():
    idx = pd.bdate_range("2020-01-01", periods=20)
    p = pd.DataFrame({"A": 100 * np.cumprod(1 + np.sin(np.arange(20)) * 0.02)}, index=idx)
    t = p * 0 + 0.6
    a = backtest.run(p, t)
    b = backtest.run_returns(p.pct_change(), t)
    pd.testing.assert_series_equal(a.returns, b.returns, check_exact=True)


def test_exclusion_cannot_erase_loss_and_only_sells_excluded_asset():
    idx = pd.bdate_range("2020-01-01", periods=5)
    r = pd.DataFrame({"A": [0.0, 0.0, -0.5, 0.1, 0.0], "B": [0.0, 0.0, 0.1, 0.1, 0.0]}, index=idx)
    t = r * float("nan")
    t.iloc[0] = [0.5, 0.5]
    eligible = r.notna()
    eligible.loc[idx[2] :, "A"] = False
    out = backtest.run_returns(r, t, cost_bps=0, eligibility=eligible)
    assert out.returns.iloc[2] == pytest.approx(-0.2)
    # A's proceeds earn zero in cash; B holds 0.55 / 0.8 and returns 10%.
    assert out.returns.iloc[3] == pytest.approx(0.55 / 0.8 * 0.1)
    # Exclusion-day close holdings are post-sale; day 3 drifts B to 0.75625 / 1.06875.
    assert out.holdings.iloc[2]["A"] == 0
    assert out.holdings.iloc[2]["B"] == pytest.approx(0.55 / 0.8)
    assert out.holdings.iloc[3]["A"] == 0
    r.loc[idx[3], "A"] = np.nan
    assert backtest.run_returns(r, t, eligibility=eligible).returns.iloc[3] == pytest.approx(
        0.55 / 0.8 * 0.1
    )
    r.loc[idx[3], "B"] = np.nan
    with pytest.raises(ValueError, match="missing price for held"):
        backtest.run_returns(r, t, eligibility=eligible)
