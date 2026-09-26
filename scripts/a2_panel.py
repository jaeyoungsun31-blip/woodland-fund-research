"""Signed A2 transformations used by the constituent-panel builder.

This module deliberately accepts classifications made elsewhere.  It does not
infer corporate actions from prices: A2's citation requirement belongs upstream.
Successor candidates that do not satisfy the signed Case 4 signature are
quarantined pending the unsigned Amendment 1 rather than treated as an exit or
as a stitch.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

import pandas as pd

PENDING_AMENDMENT_1 = "pending_A2_amendment_1"


@dataclass(frozen=True)
class A2CensusRow:
    record_id: str
    symbol: str
    start: str
    end: str
    a2_case: str
    case2_absent: bool


@dataclass(frozen=True)
class A2Exit:
    """One terminal symbol-year whose return treatment must be disclosed."""

    record_id: str
    symbol: str
    terminal_date: pd.Timestamp


def read_a2_census(path: str) -> list[A2CensusRow]:
    frame = pd.read_csv(path, dtype={"a2_case": str})
    required = {"record_id", "symbol", "start", "end", "a2_case", "case2_absent"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"A2 census missing columns: {sorted(missing)}")
    return [
        A2CensusRow(
            record_id=str(row.record_id), symbol=str(row.symbol), start=str(row.start),
            end=str(row.end), a2_case=str(row.a2_case),
            case2_absent=str(row.case2_absent).casefold() == "true",
        )
        for row in frame.itertuples(index=False)
    ]


def _successor_events(classification_path: str) -> dict[str, set[str]]:
    """Return cited successor-event dates not approved by signed Case 4.

    These are exactly the cases Amendment 1 proposes to redefine.  A cited
    successor test that *did* pass signed Case 4 is not quarantined here.
    """
    frame = pd.read_csv(classification_path, dtype=str).fillna("")
    events: dict[str, set[str]] = {}
    for row in frame.itertuples(index=False):
        try:
            tests = json.loads(row.candidate_tests)
        except (AttributeError, TypeError, json.JSONDecodeError):
            continue
        nested = [test for candidate in tests for test in candidate.get("tests", [])]
        for test in [*tests, *nested]:
            if str(test.get("a2_case")) != "4" or test.get("agrees") is True:
                continue
            if test.get("citation") and test.get("event_date"):
                events.setdefault(str(row.constituent_symbol), set()).add(
                    str(test["event_date"])
                )
    return events


def signed_a2_report(
    census: Iterable[A2CensusRow], classification_path: str
) -> tuple[dict[str, int], set[str]]:
    """Count signed cases and identify symbol-years awaiting Amendment 1.

    Case labels in the census are the signed-base outcome.  A row is quarantined
    only when a cited, failed Case 4 successor test falls *inside that row's
    membership window*.  This prevents a later reused ticker vintage from being
    labelled by an unrelated corporate action.
    """
    rows = list(census)
    cases = Counter(row.a2_case for row in rows)
    successor_events = _successor_events(classification_path)
    pending = {
        row.record_id
        for row in rows
        for event_date in successor_events.get(row.symbol, set())
        if row.start <= event_date <= row.end
    }
    return {
        "case_1": int(cases["1"]),
        "case_2": int(cases["2"]),
        "case_4": int(cases["4"]),
        PENDING_AMENDMENT_1: len(pending),
    }, pending


def apply_case2_terminal(
    series: pd.Series, terminal_date: pd.Timestamp, terminal_return: float
) -> pd.Series:
    """Add a declared Case 2 terminal return without altering price history."""
    if terminal_return < -1.0 or terminal_return > 0.0:
        raise ValueError("A2 terminal return must be in [-1, 0]")
    result = series.copy()
    result.loc[pd.Timestamp(terminal_date)] = terminal_return
    return result.sort_index()


def drop_case4_seam(series: pd.Series, seam_date: pd.Timestamp) -> pd.Series:
    """Drop the return across a signed Case 4 locator seam."""
    result = series.copy()
    result.loc[pd.Timestamp(seam_date)] = float("nan")
    return result


def adverse_absent_case2_panel(
    panel: pd.DataFrame, census: Iterable[A2CensusRow]
) -> tuple[pd.DataFrame, list[dict[str, str]]]:
    """Apply A2's -100% adverse bound to each absent symbol's final year.

    The base panel excludes absent files because no security can be held.  The
    adverse panel records one -100% return on the final available panel session
    in each affected symbol's final membership year, as the signed convention
    requires.  This is a bound, never a base-price observation.
    """
    result = panel.copy()
    absent = [row for row in census if row.a2_case == "2" and row.case2_absent]
    final_by_symbol: dict[str, A2CensusRow] = {}
    for row in absent:
        if row.symbol not in final_by_symbol or row.end > final_by_symbol[row.symbol].end:
            final_by_symbol[row.symbol] = row
    applied: list[dict[str, str]] = []
    for symbol, row in sorted(final_by_symbol.items()):
        eligible = result.index[result.index <= pd.Timestamp(row.end)]
        if eligible.empty:
            raise ValueError(f"no panel session on or before final A2 date for {symbol}")
        terminal_date = eligible[-1]
        if symbol not in result:
            result[symbol] = float("nan")
        result.loc[terminal_date, symbol] = -1.0
        applied.append({"symbol": symbol, "record_id": row.record_id,
                        "terminal_date": str(terminal_date.date())})
    return result.sort_index(axis=1), applied


def classify_exit_coverage(
    exits: Iterable[A2Exit], census: Iterable[A2CensusRow], pending: set[str]
) -> tuple[dict[str, int], list[A2Exit]]:
    """Apply signed A2 labels to terminal symbol-years and assert coverage.

    Amendment 2 defines every exit not covered by signed Cases 1/2/4 as an
    unclassified exit, except the explicitly quarantined Amendment 1 rows.
    """
    labels = {row.record_id: row.a2_case for row in census}
    exits = list(exits)
    if missing := {exit.record_id for exit in exits} - set(labels):
        raise ValueError(f"terminal exits absent from A2 census: {sorted(missing)}")
    by_case = Counter(labels[exit.record_id] for exit in exits)
    quarantined = [exit for exit in exits if exit.record_id in pending]
    treated = [
        exit for exit in exits
        if labels[exit.record_id] in {"1", "2", "4"} and exit.record_id not in pending
    ]
    unclassified = [
        exit for exit in exits
        if exit.record_id not in pending and labels[exit.record_id] not in {"1", "2", "4"}
    ]
    coverage = {
        "exits_total": len(exits),
        "treated": len(treated),
        "by_case": {"case_1": int(by_case["1"]), "case_2": int(by_case["2"]),
                    "case_4": int(by_case["4"])},
        "unclassified": len(unclassified),
        "quarantined": len(quarantined),
    }
    reconciled = coverage["treated"] + coverage["unclassified"] + coverage["quarantined"]
    if reconciled != coverage["exits_total"]:
        raise AssertionError("A2 exit coverage does not reconcile")
    return coverage, unclassified


def _first_session_after(index: pd.DatetimeIndex, date: pd.Timestamp) -> pd.Timestamp:
    following = index[index > pd.Timestamp(date)]
    if following.empty:
        raise ValueError(f"no panel session after terminal date {date.date()}")
    return following[0]


def bounded_exit_panels(
    panel: pd.DataFrame, unclassified: Iterable[A2Exit], census: Iterable[A2CensusRow]
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict[str, str]], list[dict[str, str]]]:
    """Build Amendment 2's favourable and adverse panels through one mechanism.

    The adverse panel retains the signed Case 2 treatment exactly, then adds
    unclassified exits at -100%.  The favourable panel adds the same exits at
    0%, liquidating at their final available close.  Pending Amendment 1 rows
    never reach this function.
    """
    favourable = panel.copy()
    adverse, case2_rows = adverse_absent_case2_panel(panel, census)
    bound_rows: list[dict[str, str]] = []
    for exit in sorted(unclassified, key=lambda item: item.record_id):
        terminal_date = _first_session_after(panel.index, exit.terminal_date)
        favourable.loc[terminal_date, exit.symbol] = 0.0
        adverse.loc[terminal_date, exit.symbol] = -1.0
        bound_rows.append({"symbol": exit.symbol, "record_id": exit.record_id,
                           "terminal_date": str(terminal_date.date())})
    return (
        favourable.sort_index(axis=1), adverse.sort_index(axis=1),
        bound_rows, case2_rows,
    )
