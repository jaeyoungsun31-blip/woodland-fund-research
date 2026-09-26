from dataclasses import replace
from datetime import date

import pandas as pd
import pytest

from woodland.live.resolver_a2 import classify_a2, identity_coverage, union_coverage
from woodland.live.security_resolver import Constituent, Security, SecurityResolver


def security(symbol="X", first="1990-01-01", last="2026-06-30", **kwargs):
    return Security(
        symbol,
        symbol,
        "DISPLAY ONLY",
        "NYSE",
        "Common Stock",
        date.fromisoformat(first),
        date.fromisoformat(last),
        True,
        **kwargs,
    )


def member(start="1999-01-05", end="1999-12-31", symbol="X"):
    return Constituent(
        start[:4] + ":" + symbol, symbol, date.fromisoformat(start), date.fromisoformat(end)
    )


@pytest.mark.parametrize(
    "symbol,left,right", [("CTXS", "1998-12-18", "2003-09-11"), ("JP", "1981-12-24", "2015-07-15")]
)
def test_gap_prevents_automatic_acceptance_without_relaxing_dates(symbol, left, right):
    s = security(
        symbol,
        first="1980-01-01",
        trading_gaps=((date.fromisoformat(left), date.fromisoformat(right)),),
    )
    c = member(symbol=symbol)
    assert SecurityResolver._dates(c, s)
    r = SecurityResolver([s]).audit_one(c)
    assert r.status == "candidates_unmatched"
    assert "interior_gap" in r.failures[symbol]
    assert SecurityResolver([replace(s, trading_gaps=())]).audit_one(c).status == "resolved"


def test_gap_outside_window_and_observed_endpoint_do_not_reject():
    s = security(trading_gaps=((date(1990, 1, 1), date(1991, 1, 1)),))
    assert SecurityResolver([s]).audit_one(member()).status == "resolved"
    assert not SecurityResolver._interior_gap(member("1991-01-01", "1991-01-01"), s)


def test_bsc_identity_is_independent_of_short_coverage():
    s = security("BSC_old", last="2008-03-14", price_evidence={"last_close": 30})
    proof = dict(
        citation="https://www.sec.gov/Archives/edgar/data/19617/000119312508079987/ds4.htm",
        retrieved=True,
        agrees=True,
        predicted_signature="March 14 stock decline rounds to 47%",
        observed_from_data="57 -> 30; decline rounds to 47%",
    )
    verdict = identity_coverage(s, [member("2008-01-01", "2008-05-29", "BSC")], proof)
    assert verdict["identity_verdict"] == "accept"
    assert verdict["identity_confidence"] == "high"
    assert verdict["coverage_verdict"] == "truncated_end"
    assert identity_coverage(s, [member()], {})["identity_verdict"] == "unknown"


def test_a2_order_and_uncited_residual():
    cal = [x.date() for x in pd.bdate_range("2008-01-01", "2008-12-31")]
    s = security(last="2008-03-14", price_evidence={"last_close": 30})
    cash = dict(
        kind="cash",
        date="2008-03-14",
        cash_price=30,
        prediction="30 cash",
        citation="fixture",
        retrieved=True,
    )
    bk = dict(
        kind="bankruptcy",
        date="2008-03-14",
        citation="fixture",
        retrieved=True,
        terminal_corroborated=True,
    )
    successor = security("Y", first="2008-03-17")
    stock = dict(
        kind="successor", date="2008-03-17", successor="Y", citation="fixture", retrieved=True
    )
    assert classify_a2(s, [bk, stock, cash], {"Y": successor}, cal)["a2_case"] == "1"
    assert classify_a2(s, [bk, stock], {"Y": successor}, cal)["a2_case"] == "4"
    assert classify_a2(s, [bk], {}, cal)["a2_case"] == "2"
    assert (
        classify_a2(s, [dict(cash, citation=""), dict(bk, citation="")], {}, cal)["a2_case"] == "3"
    )
    assert classify_a2(s, [], {}, cal)["case_status"] == "unresolved"
    assert classify_a2(None, [], {}, cal)["a2_case"] == "unresolved"


def test_stock_deal_and_old_backfilled_successor_do_not_pass_cash_or_stitch():
    s = security(last="2008-03-14", price_evidence={"last_close": 30})
    cal = [x.date() for x in pd.bdate_range("1990-01-01", "2026-06-30")]
    e = dict(
        kind="successor",
        date="2008-03-17",
        successor="Y",
        cash_price=30,
        citation="fixture",
        retrieved=True,
    )
    assert classify_a2(s, [e], {"Y": security("Y")}, cal)["a2_case"] == "3"


def test_union_does_not_hide_interior_holes_or_approve_identity():
    s = security(trading_gaps=((date(1998, 1, 1), date(2001, 1, 1)),))
    cal = [x.date() for x in pd.bdate_range("1999-01-05", "1999-12-31")]
    result = union_coverage([member()], [s], cal)
    assert not result["contiguous_on_trading_sessions"]
    assert result["remaining_holes"][0]["trading_sessions"] == len(cal)
    assert not result["identity_approved"]


def test_incomplete_calendar_cannot_make_distant_cash_event_look_adjacent():
    from woodland.live.resolver_a2 import sessions_between

    cal = [date(2008, 1, 2), date(2008, 1, 3)]
    assert sessions_between(date(1999, 1, 1), date(2000, 1, 1), cal) is None
    s = security(last="1999-01-01", price_evidence={"last_close": 30})
    e = dict(kind="cash", date="2000-01-01", cash_price=30, citation="fixture", retrieved=True)
    assert classify_a2(s, [e], {}, cal)["a2_case"] == "3"
