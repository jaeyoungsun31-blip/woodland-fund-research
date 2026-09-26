"""Signed date-match policy. Pure evidence checks; no security or price mutations."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

VENDOR_FLOORS = frozenset({"1997-12-31", "1999-01-04"})
IPO_RELATIVE_TOLERANCE = 0.30
CLOSE_ABSOLUTE_TOLERANCE = 0.02
CONSIDERATION_RELATIVE_TOLERANCE = 0.01


def endpoint_counts(manifest: dict[str, Any]) -> dict[str, Counter[str]]:
    return {
        side: Counter(
            str(f[side])
            for f in manifest["files"].values()
            if f.get("state") == "readable" and f.get(side)
        )
        for side in ("first", "last")
    }


def numerical_check(e: dict[str, Any], observed: float | None) -> dict[str, Any]:
    """A retrieved number must have a declared, comparable measurement and band."""
    kind = e.get("kind")
    expected = e.get("expected")
    ready = bool(e.get("citation") and e.get("retrieved") and e.get("claim"))
    bands = {
        "exact_close": (CLOSE_ABSOLUTE_TOLERANCE, 0.0),
        "cash_consideration": (0.0, 0.05),
        "stock_consideration": (0.0, CONSIDERATION_RELATIVE_TOLERANCE),
        "ipo_offering": (0.0, IPO_RELATIVE_TOLERANCE),
    }
    if kind not in bands or not ready or not isinstance(expected, (int, float)):
        return dict(agrees=False, missing="Retrieved comparable numerical prediction missing.")
    if (
        not math.isfinite(expected)
        or expected <= 0
        or observed is None
        or not math.isfinite(observed)
    ):
        return dict(agrees=False, missing="Finite positive prediction/observed price missing.")
    absolute, relative = bands[kind]
    tolerance = max(absolute, relative * expected)
    agrees = abs(observed - expected) <= tolerance + 1e-10
    return dict(
        agrees=agrees,
        expected=expected,
        observed=observed,
        lower=expected - tolerance,
        upper=expected + tolerance,
        relative_difference=observed / expected - 1,
        confidence="medium" if kind == "ipo_offering" else "high",
        missing=""
        if agrees
        else "Observed number does not meet the declared band; no rescaling assumed.",
    )


def date_admissibility(
    pivot: str,
    multiplicity: int,
    date_agrees: bool,
    citation: str,
    retrieved: bool,
    numeric: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Floors are never pivots. Multiplicity zero is unknown, not unique."""
    numeric = numeric or {}
    reason = ""
    basis = ""
    confidence = "low"
    if pivot in VENDOR_FLOORS:
        reason = "Vendor coverage floor is not admissible identity evidence."
    elif not citation or not retrieved or not date_agrees:
        reason = "Retrieved citation and exact pivot-date agreement are both required."
    elif multiplicity < 1:
        reason = "Pivot multiplicity is not established in the original-file manifest."
    elif numeric and not numeric.get("agrees"):
        reason = numeric.get("missing", "Numerical prediction is not corroborated.")
    elif numeric.get("agrees"):
        basis, confidence = "date_and_numeric", numeric.get("confidence", "high")
    elif multiplicity <= 3:
        basis, confidence = "date_only", "high" if multiplicity == 1 else "medium"
    else:
        reason = "Multiplicity >=4 requires a retrieved, corroborated numerical fingerprint."
    return dict(
        identity_verdict="unknown" if reason else "accept",
        identity_confidence=confidence,
        evidence_basis=basis,
        missing_evidence=reason,
    )
