"""The signed date-admissibility rule, and the two ways it refuses to be flattered."""

from __future__ import annotations

import pytest

from woodland.live.resolver_multiplicity import (
    VENDOR_FLOORS,
    ManifestBoundaries,
    date_admissibility,
)


def manifest(files: dict[str, tuple[str, str]], unreadable: dict[str, str] | None = None):
    entries = {
        symbol: {"state": "readable", "first": first, "last": last}
        for symbol, (first, last) in files.items()
    }
    for symbol, state in (unreadable or {}).items():
        entries[symbol] = {"state": state, "first": "2000-01-03", "last": "2000-12-29"}
    return {"files": entries, "listed_parquet_files": len(entries)}


# ----------------------------------------------------------------- counting

def test_first_and_last_counters_are_separate():
    """A date common as a last bar must not inflate its first-bar multiplicity."""
    boundaries = ManifestBoundaries(manifest({
        "A": ("2001-01-02", "2019-12-06"),
        "B": ("2002-01-02", "2019-12-06"),
        "C": ("2019-12-06", "2024-01-02"),
    }))
    assert boundaries.count("last", "2019-12-06").count == 2
    assert boundaries.count("first", "2019-12-06").count == 1


def test_unreadable_files_are_not_counted():
    boundaries = ManifestBoundaries(manifest(
        {"A": ("1998-01-02", "2020-01-02")}, unreadable={"B": "unreadable", "C": "missing"}))
    assert len(boundaries.readable) == 1
    assert boundaries.count("first", "2000-01-03").count is None


def test_absent_pivot_is_unknown_not_unique():
    """The rule this module exists to enforce: unknown never collapses to 1."""
    boundaries = ManifestBoundaries(manifest({"A": ("2001-01-02", "2019-12-06")}))
    result = boundaries.count("last", "2007-05-14")
    assert result.count is None
    assert not result.known
    assert date_admissibility("2007-05-14", result.count).verdict == "numeric_required"


# ----------------------------------------------------------------- segments

def test_segment_boundary_is_never_counted():
    """A splice boundary is our own construction; counting it is self-corroboration."""
    boundaries = ManifestBoundaries(manifest({
        "LB_old1": ("1982-04-01", "2021-08-02"),
        "OTHER": ("2003-09-10", "2011-06-28"),
    }))
    row = boundaries.row_counts("LB_old1::segment2", "2003-09-10", "2021-08-02")
    assert row["segment_locator"] is True
    assert row["storage_symbol"] == "LB_old1"
    assert row["first_multiplicity"] is None          # splice boundary, not a file bound
    assert "splice boundary" in row["first_multiplicity_basis"]
    assert row["last_multiplicity"] == 1              # genuine file last bar


def test_segment_bound_matching_the_file_is_counted():
    boundaries = ManifestBoundaries(manifest({"LB_old1": ("1982-04-01", "2021-08-02")}))
    row = boundaries.row_counts("LB_old1::segment1", "1982-04-01", "2011-06-28")
    assert row["first_multiplicity"] == 1
    assert row["last_multiplicity"] is None


def test_symbol_absent_from_manifest_yields_unknown_on_both_boundaries():
    boundaries = ManifestBoundaries(manifest({"A": ("2001-01-02", "2019-12-06")}))
    row = boundaries.row_counts("GHOST", "2001-01-02", "2019-12-06")
    assert row["in_manifest"] is False
    assert row["first_multiplicity"] is None and row["last_multiplicity"] is None


# --------------------------------------------------------------------- rule

@pytest.mark.parametrize(
    "multiplicity,verdict,confidence",
    [(1, "sufficient", "high"), (2, "sufficient", "medium"), (3, "sufficient", "medium"),
     (4, "numeric_required", "low"), (11, "numeric_required", "low")],
)
def test_multiplicity_thresholds(multiplicity, verdict, confidence):
    result = date_admissibility("2012-03-12", multiplicity)
    assert (result.verdict, result.confidence) == (verdict, confidence)


@pytest.mark.parametrize("floor", sorted(VENDOR_FLOORS))
def test_vendor_floors_are_inadmissible_at_every_multiplicity(floor):
    for multiplicity in (1, 2, 3, 4, 3760, None):
        assert date_admissibility(floor, multiplicity).verdict == "inadmissible"


def test_ceg_case_the_declaration_names():
    """Multiplicity 3 is the one date-only accept the signed rule still permits."""
    result = date_admissibility("2012-03-12", 3)
    assert result.verdict == "sufficient" and result.confidence == "medium"
