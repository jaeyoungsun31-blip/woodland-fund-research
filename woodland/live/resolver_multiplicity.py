"""Pivot-date multiplicity and the signed date-admissibility rule.

Implements `2026-09-06-planning-decision-date-match-admissibility.md` as declared
in `2026-09-06-phase3-date-admissibility-implementation.md`.

Two things this module refuses to do, both deliberate:

**It counts original manifest files, never expanded segments.** A segment
boundary is manufactured by our own splice logic, so counting it would let the
resolver corroborate itself. Segment locators are resolved back to their storage
symbol, and any boundary that is a segment artifact rather than a file boundary
is reported as unknown multiplicity.

**It never converts unknown into unique.** A pivot absent from the manifest has
unknown multiplicity. Unknown is not 1, so it cannot satisfy the multiplicity-1
branch, and the numeric requirement applies.

Read-only throughout: it reads a manifest and returns counts and verdicts. It
does not touch price files, approve anything, or write.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

# Vendor history floors. Signed rule: never admissible as identity evidence, at
# any multiplicity, in either direction.
VENDOR_FLOORS: frozenset[str] = frozenset({"1997-12-31", "1999-01-04"})

# Signed multiplicity thresholds.
SUFFICIENT_HIGH_MAX = 1      # multiplicity 1: a date match alone is sufficient
SUFFICIENT_MEDIUM_MAX = 3    # multiplicity 2-3: sufficient, medium confidence
                             # multiplicity >= 4: numeric fingerprint required

Boundary = Literal["first", "last"]
Verdict = Literal["sufficient", "numeric_required", "inadmissible"]


@dataclass(frozen=True)
class Multiplicity:
    """How many original files share a boundary date, and how it was obtained."""

    boundary: Boundary
    date: str | None
    count: int | None            # None == unknown, never treated as unique
    basis: str

    @property
    def known(self) -> bool:
        return self.count is not None


@dataclass(frozen=True)
class Admissibility:
    """The signed rule's verdict on one pivot."""

    verdict: Verdict
    confidence: Literal["high", "medium", "low"]
    reason: str


class ManifestBoundaries:
    """Separate first-bar and last-bar counters over the readable manifest files.

    Built once per manifest and queried per packet row. The two counters are kept
    separate because the signed measurement is asymmetric: 37.0% of files share a
    last bar with more than a hundred others, against 13.2% for first bars, so a
    single pooled counter would misstate both.
    """

    def __init__(self, manifest: dict[str, Any]) -> None:
        files: dict[str, dict[str, Any]] = manifest.get("files", {})
        self.readable = {
            symbol: info for symbol, info in files.items() if info.get("state") == "readable"
        }
        self.first_counts: Counter[str] = Counter(
            info["first"] for info in self.readable.values() if info.get("first")
        )
        self.last_counts: Counter[str] = Counter(
            info["last"] for info in self.readable.values() if info.get("last")
        )
        self.listed = manifest.get("listed_parquet_files")

    # ---------------------------------------------------------------- counting

    def counter(self, boundary: Boundary) -> Counter[str]:
        return self.first_counts if boundary == "first" else self.last_counts

    def count(self, boundary: Boundary, pivot: str | None) -> Multiplicity:
        """Multiplicity of a bare date, independent of which file carried it."""
        if not pivot:
            return Multiplicity(boundary, pivot, None, "no pivot date supplied")
        found = self.counter(boundary).get(pivot)
        if found is None:
            return Multiplicity(
                boundary, pivot, None,
                f"date is not a {boundary} bar of any readable manifest file; "
                "unknown multiplicity, not unique",
            )
        return Multiplicity(
            boundary, pivot, found,
            f"{found} readable manifest file(s) share this {boundary} bar",
        )

    # --------------------------------------------------------------- locators

    def storage_symbol(self, locator: str) -> str:
        """Strip a segment suffix to reach the file the manifest actually lists."""
        return locator.split("::", 1)[0]

    def row_counts(self, locator: str, first: str | None, last: str | None) -> dict[str, Any]:
        """Both boundary counts for one packet row, segment-aware.

        `first`/`last` are the candidate's own bounds, which for a segment are
        splice boundaries rather than file boundaries. A bound that does not
        match the storage file's own bound is a segment artifact: it is reported
        as unknown, never counted, and never allowed to look unique.
        """
        storage = self.storage_symbol(locator)
        info = self.readable.get(storage, {})
        segmented = "::" in locator
        out: dict[str, Any] = {
            "locator": locator,
            "storage_symbol": storage,
            "segment_locator": segmented,
            "in_manifest": bool(info),
        }
        pairs: tuple[tuple[Boundary, str | None], ...] = (("first", first), ("last", last))
        for boundary, value in pairs:
            file_bound = info.get(boundary)
            if not info:
                m = Multiplicity(
                    boundary, value, None,
                    f"storage symbol {storage} absent from the readable manifest",
                )
            elif value is not None and file_bound is not None and value != file_bound:
                m = Multiplicity(
                    boundary, value, None,
                    f"segment {boundary} bar {value} is a splice boundary, not file "
                    f"{boundary} bar {file_bound}; expanded segments are never counted",
                )
            else:
                m = self.count(boundary, value or file_bound)
            out[f"{boundary}_bar"] = m.date
            out[f"{boundary}_multiplicity"] = m.count
            out[f"{boundary}_multiplicity_basis"] = m.basis
            out[f"{boundary}_is_vendor_floor"] = (m.date in VENDOR_FLOORS) if m.date else False
        return out


def date_admissibility(pivot: str | None, multiplicity: int | None) -> Admissibility:
    """The signed rule, applied to one pivot date and its multiplicity."""
    if pivot in VENDOR_FLOORS:
        return Admissibility(
            "inadmissible", "low",
            f"{pivot} is a vendor history floor and is never admissible as identity "
            "evidence, at any multiplicity, in either direction",
        )
    if pivot is None:
        return Admissibility("numeric_required", "low", "no pivot date to test")
    if multiplicity is None:
        return Admissibility(
            "numeric_required", "low",
            "unknown multiplicity; an uncounted pivot is not a unique one",
        )
    if multiplicity <= SUFFICIENT_HIGH_MAX:
        return Admissibility(
            "sufficient", "high",
            f"multiplicity {multiplicity}: a date match alone is sufficient",
        )
    if multiplicity <= SUFFICIENT_MEDIUM_MAX:
        return Admissibility(
            "sufficient", "medium",
            f"multiplicity {multiplicity}: sufficient, recorded at medium confidence",
        )
    return Admissibility(
        "numeric_required", "low",
        f"multiplicity {multiplicity}: a numerical fingerprint is required",
    )
