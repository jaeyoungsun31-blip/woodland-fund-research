"""Walk-forward split correctness (DESIGN.md §7).

These run BEFORE the harness touches real data. The properties asserted here
are the ones whose violation silently invalidates every downstream number:
train/validate overlap, and a lookback reaching across the embargo.
"""

import pandas as pd
import pytest

from woodland.harness import splits as sp

CAL = pd.bdate_range("2000-01-03", "2026-09-01")   # ~stand-in trading calendar


def default_splits(index=CAL, **kw):
    return sp.make_splits(index, **kw)


# ---------------------------------------------------------------- structure

def test_windows_have_the_requested_shape():
    s = default_splits()
    assert len(s) > 15, "27 years at 1y steps should give many folds"
    d = sp.describe(s, CAL)
    # 5 calendar years of business days, allowing for holidays not in bdate_range
    assert d["train_days"].between(1250, 1310).all(), d
    assert (d["embargo_days"] == 210).all(), d
    assert d["validate_days"].iloc[:-1].between(250, 265).all(), d


def test_splits_advance_monotonically():
    s = default_splits()
    for a, b in zip(s, s[1:], strict=False):
        assert b.train_start > a.train_start
        assert b.validate_start > a.validate_start
        assert b.i == a.i + 1


# ---------------------------------------------------------------- no overlap

def test_train_and_validate_never_share_a_bar():
    for s in default_splits():
        tr = set(s.train_index(CAL))
        va = set(s.validate_index(CAL))
        assert not (tr & va), f"train/validate overlap on {s}"
        assert max(tr) < min(va)


def test_embargo_sits_strictly_between_and_is_excluded_from_both():
    for s in default_splits():
        emb = set(s.embargo_index(CAL))
        assert len(emb) == 210
        assert not (emb & set(s.train_index(CAL)))
        assert not (emb & set(s.validate_index(CAL)))
        assert min(emb) >= s.train_end and max(emb) < s.validate_start


def test_validate_windows_tile_without_overlap_so_they_stitch():
    """Consecutive validate windows must not overlap, or the stitched OOS
    curve would double-count days."""
    s = default_splits()
    seen: set = set()
    for split in s:
        days = set(split.validate_index(CAL))
        assert not (days & seen), f"validate windows overlap at split {split.i}"
        seen |= days
    # With step == validate length the windows must be contiguous in BARS, not
    # merely disjoint — any skipped trading day is a hole in the OOS record.
    # (validate_end is a calendar date; the next validate_start snaps to the
    # next bar, so the timestamps differ while the bar coverage does not.)
    covered = sorted(seen)
    first, last = CAL.searchsorted(covered[0]), CAL.searchsorted(covered[-1])
    assert list(covered) == list(CAL[first:last + 1]), "gap between validate windows"


def test_validate_windows_have_a_gap_when_stepping_slower_than_validating():
    s = default_splits(validate_years=1, step_years=2)
    for a, b in zip(s, s[1:], strict=False):
        assert b.validate_start > a.validate_end


# ---------------------------------------------------------------- no leakage

@pytest.mark.parametrize("lookback", [1, 50, 210])
def test_lookback_from_validate_start_never_reaches_the_train_window(lookback):
    """The embargo's whole purpose: a signal's backward reach at the first
    validate bar must land in the embargo, never in train."""
    s = default_splits(embargo_days=210)
    sp.check_embargo_covers_lookback(s, CAL, lookback)     # must not raise
    for split in s:
        v_pos = CAL.searchsorted(split.validate_start)
        assert CAL[v_pos - lookback] >= split.train_end


def test_lookback_longer_than_the_embargo_is_rejected_loudly():
    s = default_splits(embargo_days=210)
    with pytest.raises(ValueError, match="embargo too short"):
        sp.check_embargo_covers_lookback(s, CAL, max_lookback_days=211)


def test_a_shorter_embargo_really_does_leak():
    """Guard against the check being vacuous: with too small an embargo, a
    10-month lookback provably lands inside train."""
    s = default_splits(embargo_days=5)
    leaked = [
        split for split in s
        if CAL[CAL.searchsorted(split.validate_start) - 210] < split.train_end
    ]
    assert leaked, "expected leakage with a 5-day embargo"
    with pytest.raises(ValueError, match="embargo too short"):
        sp.check_embargo_covers_lookback(s, CAL, max_lookback_days=210)


def test_embargo_is_counted_in_trading_days_not_calendar_days():
    """Counting calendar days would silently shorten the embargo across
    holidays and weekends."""
    s = default_splits(embargo_days=210)[0]
    bars = len(s.embargo_index(CAL))
    calendar_days = (s.validate_start - s.train_end).days
    assert bars == 210
    assert calendar_days > 280, "210 bars must span far more than 210 calendar days"


# ---------------------------------------------------------------- edges

def test_no_splits_when_history_is_too_short():
    short = pd.bdate_range("2020-01-01", "2022-01-01")
    assert sp.make_splits(short, train_years=5, embargo_days=210) == []


def test_empty_calendar_yields_no_splits():
    assert sp.make_splits(pd.DatetimeIndex([])) == []


def test_zero_embargo_is_allowed_but_leaves_train_and_validate_adjacent():
    s = sp.make_splits(CAL, embargo_days=0)
    for split in s:
        assert len(split.embargo_index(CAL)) == 0
        assert split.train_end == split.validate_start
    with pytest.raises(ValueError, match="embargo too short"):
        sp.check_embargo_covers_lookback(s, CAL, max_lookback_days=1)


def test_invalid_parameters_rejected():
    with pytest.raises(ValueError, match="embargo_days"):
        sp.make_splits(CAL, embargo_days=-1)
    with pytest.raises(ValueError, match="train_years"):
        sp.make_splits(CAL, train_years=0)


def test_trading_days_for_months_rounds_up():
    assert sp.trading_days_for_months(10) == 210
    assert sp.trading_days_for_months(1, days_per_month=21.5) == 22


def test_splits_are_deterministic():
    assert default_splits() == default_splits()
