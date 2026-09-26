"""Proposed A2 signatures and coverage measurements. Never constructs prices/returns."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from woodland.live.resolver_date_evidence import date_admissibility
from woodland.live.security_resolver import Constituent, Security, SecurityResolver


def identity_coverage(
    s: Security | None, windows: list[Constituent], evidence: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Identity and observed coverage are independent; no name-based inference."""
    e = evidence or {}
    verified = bool(
        e.get("citation")
        and e.get("retrieved")
        and e.get("agrees") is True
        and e.get("predicted_signature")
        and e.get("observed_from_data")
    )
    admissibility = {}
    if e.get("evidence_kind") == "date_match":
        admissibility = date_admissibility(
            e.get("pivot_date", ""),
            e.get("pivot_multiplicity", 0),
            e.get("date_agrees") is True,
            e.get("citation", ""),
            bool(e.get("retrieved")),
            e.get("numeric_check"),
        )
        verified = verified and admissibility["identity_verdict"] == "accept"
    flags = []
    if s is None or not s.available or s.first is None or s.last is None:
        flags = ["absent"]
    else:
        if any(SecurityResolver._interior_gap(w, s) for w in windows):
            flags.append("interior_gap")
        if any(s.last < w.end for w in windows):
            flags.append("truncated_end")
        if any(s.first > w.start for w in windows):
            flags.append("truncated_start")
        if not flags:
            flags = ["complete"]
    return dict(
        identity_verdict="accept" if verified else "unknown",
        identity_confidence=admissibility.get("identity_confidence", "high") if verified else "low",
        coverage_verdict=flags[0],
        coverage_confidence="high",
        coverage_flags=flags,
        identity_missing=""
        if verified
        else admissibility.get("missing_evidence")
        or "Retrieved citation and corroborated "
        "candidate-specific prediction are both required; one or both are missing.",
    )


def sessions_between(a: date, b: date, calendar: list[date]) -> int | None:
    if not calendar or min(a, b) < calendar[0] or max(a, b) > calendar[-1]:
        return None
    return sum(min(a, b) < d <= max(a, b) for d in calendar)


def classify_a2(
    s: Security | None,
    events: list[dict[str, Any]],
    successors: dict[str, Security],
    calendar: list[date],
) -> dict[str, Any]:
    """Order 1,4,2,3; evidence is curated outside this function, never inferred."""
    trials = []
    for case, kind in [(1, "cash"), (4, "successor"), (2, "bankruptcy")]:
        for e in events:
            if e.get("kind") != kind:
                continue
            valid = bool(e.get("citation") and e.get("retrieved"))
            event_date = date.fromisoformat(e["date"]) if e.get("date") else None
            observed: dict[str, Any] = {
                "last": str(s.last) if s else None,
                "last_close": s.price_evidence.get("last_close") if s else None,
            }
            agrees = False
            if case == 1 and s and s.last and event_date and e.get("cash_price"):
                distance = sessions_between(s.last, event_date, calendar)
                close = s.price_evidence.get("last_close")
                deviation = abs(close / e["cash_price"] - 1) if close is not None else None
                observed.update(trading_session_distance=distance, cash_deviation=deviation)
                agrees = bool(
                    valid
                    and distance is not None
                    and distance <= 5
                    and deviation is not None
                    and deviation <= 0.05
                )
            elif case == 4 and s and s.last and event_date:
                successor = successors.get(e.get("successor", ""))
                if successor and successor.available and successor.first:
                    distance = sessions_between(s.last, successor.first, calendar)
                    event_distance = sessions_between(s.last, event_date, calendar)
                    observed.update(
                        successor=e["successor"],
                        successor_first=str(successor.first),
                        trading_session_distance=distance,
                        event_distance=event_distance,
                    )
                    agrees = bool(
                        valid
                        and s.last < successor.first
                        and distance is not None
                        and distance <= 5
                        and event_distance is not None
                        and event_distance <= 5
                    )
            elif case == 2:
                # Absence satisfies the explicitly allowed *case* signature, not identity.
                absent = s is None or not s.available
                observed["price_file_absent"] = absent
                agrees = bool(valid and (absent or e.get("terminal_corroborated") is True))
            trial = dict(
                a2_case=str(case),
                citation=e.get("citation", ""),
                predicted_signature=e.get("prediction", ""),
                observed_from_data=observed,
                agrees=agrees,
                recovery=e.get("recovery"),
                exchange=e.get("exchange", ""),
                exchange_citation=e.get("exchange_citation", ""),
                successor=e.get("successor", ""),
                event_date=e.get("date", ""),
            )
            trials.append(trial)
            if agrees:
                fill = None
                if case == 2 and e.get("recovery") is None and e.get("exchange_citation"):
                    fill = {"NYSE": -0.30, "AMEX": -0.30, "NASDAQ": -0.55}.get(
                        e.get("exchange", "")
                    )
                return {
                    **trial,
                    "shumway_fill": fill,
                    "tests": trials,
                    "proposed_only": True,
                    "case_status": "proposed",
                    "missing": "Noncash/partial recovery cited; terminal return remains uncomputed."
                    if isinstance(e.get("recovery"), dict)
                    else ""
                    if case != 2 or e.get("recovery") is not None or fill is not None
                    else "Recovery amount and/or cited listing exchange not established.",
                }
    # Residual never implies a verified corporate action or permission to exit.
    continued = [
        e
        for e in events
        if e.get("kind") == "continued"
        and e.get("retrieved")
        and e.get("citation")
        and e.get("corroborated") is True
    ]
    return dict(
        a2_case="3" if s and s.available else "unresolved",
        case_status="proposed" if continued else "unresolved",
        citation=continued[0]["citation"] if continued else "",
        predicted_signature="File terminates before membership; no qualifying cited "
        "action explains the end. Continued trading needs independent evidence.",
        observed_from_data={"last": str(s.last) if s else None},
        agrees=bool(continued),
        recovery=None,
        exchange="",
        exchange_citation="",
        shumway_fill=None,
        successor="",
        event_date="",
        tests=trials,
        proposed_only=True,
        missing=""
        if continued
        else "Continued trading/identity not corroborated; "
        "residual is refused, not a verified data-truncation claim.",
    )


def union_coverage(
    windows: list[Constituent],
    securities: list[Security],
    calendar: list[date],
    actual_dates: dict[str, set[date]] | None = None,
) -> dict[str, Any]:
    """Geometric interval union, with gaps exposed. Does NOT approve any join."""
    pieces = []
    for s in securities:
        if not s.available or s.first is None or s.last is None:
            continue
        cursor = s.first
        for left, right in sorted(s.trading_gaps):
            pieces.append((s.price_symbol, cursor, left))
            cursor = right
        pieces.append((s.price_symbol, cursor, s.last))
    pieces.sort(key=lambda p: (p[1], p[2], p[0]))
    holes = []
    for w in windows:
        intervals = sorted(
            (max(a, w.start), min(b, w.end)) for _, a, b in pieces if a <= w.end and b >= w.start
        )
        cursor = w.start
        for a, b in intervals:
            if a > cursor:
                holes.append((w.record_id, cursor, a - timedelta(days=1)))
            cursor = max(cursor, b + timedelta(days=1))
        if cursor <= w.end:
            holes.append((w.record_id, cursor, w.end))
    detail = [
        dict(
            record_id=i,
            first=str(a),
            last=str(b),
            calendar_days=(b - a).days + 1,
            trading_sessions=sum(a <= d <= b for d in calendar),
        )
        for i, a, b in holes
    ]
    if actual_dates is not None:
        available = set().union(*(actual_dates.get(s.price_symbol, set()) for s in securities))
        detail = []
        for w in windows:
            run: list[date] = []
            for day in [d for d in calendar if w.start <= d <= w.end]:
                if day not in available:
                    run.append(day)
                elif run:
                    detail.append(
                        dict(
                            record_id=w.record_id,
                            first=str(run[0]),
                            last=str(run[-1]),
                            calendar_days=(run[-1] - run[0]).days + 1,
                            trading_sessions=len(run),
                        )
                    )
                    run = []
            if run:
                detail.append(
                    dict(
                        record_id=w.record_id,
                        first=str(run[0]),
                        last=str(run[-1]),
                        calendar_days=(run[-1] - run[0]).days + 1,
                        trading_sessions=len(run),
                    )
                )
    return dict(
        ordered_segments=[dict(file_or_segment=s, first=str(a), last=str(b)) for s, a, b in pieces],
        covered_span=[str(min(p[1] for p in pieces)), str(max(p[2] for p in pieces))]
        if pieces
        else [],
        remaining_holes=detail,
        contiguous_on_calendar=not detail,
        contiguous_on_trading_sessions=not any(h["trading_sessions"] for h in detail),
        identity_approved=False,
    )
