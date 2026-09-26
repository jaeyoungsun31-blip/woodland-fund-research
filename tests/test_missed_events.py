"""The screen for corporate actions the adjusted series never applied.

`check_adjustment` is blind to this defect by construction, and Symantec's file
is the case that proves it: a two-for-one split carried into `adjusted_close`
as a 48.6% loss, with the adjustment factor perfectly flat across it.
See journal 2026-09-07.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from woodland.data import check_adjustment, check_missed_events


def series(closes: list[float], factors: list[float]) -> pd.DataFrame:
    dates = pd.bdate_range("2004-11-01", periods=len(closes))
    close = np.array(closes, float)
    return pd.DataFrame(
        {"close": close, "adj_close": close * np.array(factors, float)}, index=dates
    )


def test_a_missed_split_is_flagged_where_check_adjustment_says_ok() -> None:
    """The SYMC signature: the factor rises normally, but is FLAT across the split.

    The factor has to reach 1.0 at the last bar and never decrease, or
    `check_adjustment` objects for an unrelated reason. That is the whole point
    - this file satisfies every condition `check_adjustment` tests while its
    adjusted series records a two-for-one split as a 48.6% loss.
    """
    closes = [63.81, 63.81, 32.79, 33.24, 33.48, 34.10, 34.55]
    factors = [0.705775, 0.705775, 0.705775, 0.80, 0.88, 0.95, 1.0]
    frame = series(closes, factors)

    assert check_adjustment(frame)["verdict"] == "ok"

    result = check_missed_events(frame)
    assert result["n_candidates"] == 1
    candidate = result["candidates"][0]
    assert candidate["adj_return"] < -0.48
    assert candidate["factor_rel_change"] < 1e-6


def test_a_correctly_applied_split_is_not_flagged() -> None:
    """GEN's shape: the same raw prices, with the factor doubling across them."""
    closes = [63.81, 63.81, 32.79, 33.24, 33.48]
    factors = [0.1774, 0.1774, 0.3549, 0.3549, 0.3549]
    result = check_missed_events(series(closes, factors))
    assert result["n_candidates"] == 0
    assert result["verdict"] == "ok"


def test_a_genuine_crash_is_flagged_too_and_that_is_the_known_limit() -> None:
    """A real crash has the same signature; the screen cannot separate them.

    This is asserted rather than worked around, because the alternative is
    pretending the screen is a detector. Adjudication needs a second source or
    a cited corporate-action calendar.
    """
    closes = [100.0, 100.0, 66.9, 67.5, 68.0]     # a -33% earnings crash
    result = check_missed_events(series(closes, [0.9] * 5))
    assert result["n_candidates"] == 1


def test_the_threshold_is_respected_and_declared() -> None:
    closes = [100.0, 100.0, 78.0, 78.0]           # a -22% move
    assert check_missed_events(series(closes, [0.9] * 4))["n_candidates"] == 0
    loose = check_missed_events(series(closes, [0.9] * 4), move_threshold=0.20)
    assert loose["n_candidates"] == 1
    assert loose["move_threshold"] == 0.20


def test_a_move_the_factor_absorbs_is_not_a_candidate() -> None:
    """A large adjusted move is fine when the factor moved with it."""
    closes = [100.0, 100.0, 50.0, 50.0]
    factors = [0.50, 0.50, 1.00, 1.00]
    assert check_missed_events(series(closes, factors))["n_candidates"] == 0


def test_the_store_column_name_is_accepted() -> None:
    """The store writes `adjusted_close`; `check_adjustment` expects `adj_close`."""
    frame = series([63.81, 63.81, 32.79], [0.705775] * 3).rename(
        columns={"adj_close": "adjusted_close"})
    result = check_missed_events(frame, adj_column="adjusted_close")
    assert result["n_candidates"] == 1


def test_insufficient_data_is_not_a_clean_bill() -> None:
    frame = series([100.0], [0.9])
    assert check_missed_events(frame)["verdict"] == "insufficient data"
