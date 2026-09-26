"""The rules that decide which of two locator files the panel should use.

Every test here exists because the corresponding mistake was actually made
while producing `reports/security-resolver/2026-09-07-locator-adjudication/`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_locator_adjudication import (  # noqa: E402
    ABSENCE_MARKERS,
    adjudicate,
    membership_intervals,
    tiingo_ticker_candidates,
)


def test_only_a_definite_absence_may_be_cached_as_one() -> None:
    """Every vendor message that is not "this ticker is not real" is transient.

    The first version of this listed throttle phrases and treated anything else
    as a missing ticker. It failed twice. The vendor caps in prose - "You have
    run over your hourly request allocation" - and ALSO as JSON,
    '{"detail": "You have run over your 50 ..."}', which matched no phrase in
    that list. 470 throttled symbols were cached as "no Tiingo series",
    including BK, EQR, GPS, ULTA and AAL. The classification is now inverted:
    only an explicit absence is cacheable.
    """
    transient = [
        "Error: You have run over your hourly request allocation. Please upgrade.",
        'Tiingo returned no CSV: \'{"detail": "You have run over your 50 symbols"}\'',
        "Error: You have run over your daily request allocation.",
        "HTTPSConnectionPool: Read timed out",
        "500 Server Error: Internal Server Error",
    ]
    for message in transient:
        assert not any(m in message.lower() for m in ABSENCE_MARKERS), message

    definite = [
        "Error: Ticker 'ENDP' not found",
        "Tiingo has no series for 'CTL'",
    ]
    for message in definite:
        assert any(m in message.lower() for m in ABSENCE_MARKERS), message


def test_ticker_candidates_strip_store_local_suffixes_in_order() -> None:
    """`CCE_old` and `IGT1` are our names for a second file, not vendor tickers."""
    assert tiingo_ticker_candidates("CCEP", "CCE_old") == ["CCEP", "CCE_old", "CCE"]
    assert tiingo_ticker_candidates("IGT", "IGT1") == ["IGT", "IGT1"]
    assert tiingo_ticker_candidates("SYMC", "GEN") == ["SYMC", "GEN"]


def test_membership_is_measured_only_where_the_record_asserts_it() -> None:
    """Annual membership rows are joined only across a short break.

    A twelve-day turn of the year is NOT bridged, so those days are excluded
    from measurement rather than assumed. That is deliberate: the record
    asserts membership on the spans it carries and nowhere else. The cost is
    that a defect landing inside such a break is invisible - 1.17% of hull days
    across the contending pairs, 14.69% on the shortest window.
    """
    rows = [
        {"price_symbol": "X", "start": "2004-01-07", "end": "2004-12-24"},
        {"price_symbol": "X", "start": "2005-01-05", "end": "2005-12-23"},
        {"price_symbol": "X", "start": "2015-01-07", "end": "2015-12-23"},
    ]
    assert membership_intervals(rows)["X"] == [
        ("2004-01-07", "2004-12-24"),
        ("2005-01-05", "2005-12-23"),
        ("2015-01-07", "2015-12-23"),
    ]

    close = [
        {"price_symbol": "Y", "start": "2004-01-07", "end": "2004-12-24"},
        {"price_symbol": "Y", "start": "2004-12-30", "end": "2005-12-23"},
    ]
    assert membership_intervals(close)["Y"] == [("2004-01-07", "2005-12-23")]


def test_a_negative_implied_distribution_decides_with_no_third_source() -> None:
    verdict, defective, status, evidence = adjudicate(
        {"locator": "SW", "contender": "SMFTF", "negative_distribution_by": "SMFTF",
         "implied_distribution_contender": "-0.0207;-0.0111"}
    )
    assert (verdict, defective) == ("SW", "SMFTF")
    assert status == "resolved_on_store_internal_evidence"
    assert "NEGATIVE" in evidence


def test_an_unapplied_split_decides_with_no_third_source() -> None:
    verdict, defective, status, _ = adjudicate(
        {"locator": "SYMC", "contender": "GEN", "missed_corporate_action_by": "SYMC",
         "days_adjustment_only": 1, "days_raw_price_differs": 2}
    )
    assert (verdict, defective) == ("GEN", "SYMC")
    assert status == "resolved_on_store_internal_evidence"


def test_conflicting_evidence_is_reported_rather_than_quietly_resolved() -> None:
    """The step-date test and the monotonicity condition naming different files
    is a result, not something to break in favour of the stronger channel."""
    verdict, defective, status, evidence = adjudicate({
        "locator": "DF", "contender": "DFODQ",
        "locator_monotonicity_violation_in_window": True,
        "locator_worst_factor_drop_in_window": -1.22e-4,
        "locator_worst_drop_date_in_window": "2011-08-22",
        "contender_monotonicity_violation_in_window": False,
        "tiingo_ticker": "DFODQ", "steps_tested": 1,
        "steps_matching_locator": 1, "steps_matching_contender": 0,
    })
    assert (verdict, defective, status) == ("undetermined", "", "conflicted")
    assert "CONFLICT" in evidence


def test_throttled_lookup_is_deferred_not_reported_as_unreachable() -> None:
    _, _, status, evidence = adjudicate(
        {"locator": "MMC", "contender": "MRSH", "tiingo_throttled": True}
    )
    assert status == "tiingo_deferred"
    assert "rate-limited" in evidence
