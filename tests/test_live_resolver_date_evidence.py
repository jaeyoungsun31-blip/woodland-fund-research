import pytest

from woodland.live.resolver_a2 import identity_coverage
from woodland.live.resolver_date_evidence import (
    date_admissibility,
    endpoint_counts,
    numerical_check,
)


@pytest.mark.parametrize(
    "count,verdict,confidence",
    [
        (0, "unknown", "low"),
        (1, "accept", "high"),
        (2, "accept", "medium"),
        (3, "accept", "medium"),
        (4, "unknown", "low"),
        (11, "unknown", "low"),
    ],
)
def test_signed_multiplicity_boundaries(count, verdict, confidence):
    r = date_admissibility("2019-08-08", count, True, "retrieved-fixture", True)
    assert (r["identity_verdict"], r["identity_confidence"]) == (verdict, confidence)


@pytest.mark.parametrize("floor", ["1997-12-31", "1999-01-04"])
@pytest.mark.parametrize("count", [1, 3, 4000])
def test_floors_never_admissible_even_with_number(floor, count):
    assert (
        date_admissibility(floor, count, True, "fixture", True, {"agrees": True})[
            "identity_verdict"
        ]
        == "unknown"
    )


def test_original_file_counts_do_not_expand_segments():
    manifest = {
        "files": {
            "X": {"state": "readable", "first": "1990-01-01", "last": "2000-01-01"},
            "Y": {"state": "readable", "first": "1999-01-04", "last": "2000-01-01"},
            "empty": {"state": "empty"},
        }
    }
    counts = endpoint_counts(manifest)
    assert counts["last"]["2000-01-01"] == 2
    assert counts["first"]["1999-01-04"] == 1
    assert counts["last"]["1999-06-01"] == 0


def numeric(kind, expected, observed):
    return numerical_check(
        dict(
            kind=kind,
            expected=expected,
            citation="fixture",
            retrieved=True,
            claim="independent number",
        ),
        observed,
    )


def test_dow_numeric_required_and_corrobated():
    good = numeric("exact_close", 66.65, 66.65)
    assert (
        date_admissibility("2017-08-31", 5, True, "fixture", True, good)["identity_verdict"]
        == "accept"
    )
    bad = numeric("exact_close", 66.65, 67)
    assert (
        date_admissibility("2017-08-31", 5, True, "fixture", True, bad)["identity_verdict"]
        == "unknown"
    )
    assert (
        date_admissibility("2017-08-31", 5, True, "fixture", False, good)["identity_verdict"]
        == "unknown"
    )


def test_ipo_band_handles_normal_return_but_does_not_rescale_kmi():
    assert numeric("ipo_offering", 20, 26)["agrees"]
    assert not numeric("ipo_offering", 20, 26.01)["agrees"]
    assert numeric("ipo_offering", 16, 16.2)["confidence"] == "medium"
    assert not numeric("ipo_offering", 30, 310.5)["agrees"]
    assert not numeric("average_valuation_not_close", 72.587, 72.77)["agrees"]


def test_legacy_agrees_flag_cannot_bypass_date_gate_and_coverage_stays_separate():
    proof = dict(
        evidence_kind="date_match",
        citation="fixture",
        retrieved=True,
        agrees=True,
        predicted_signature="last date",
        observed_from_data="last date",
        pivot_date="2019-08-08",
        pivot_multiplicity=10,
        date_agrees=True,
    )
    verdict = identity_coverage(None, [], proof)
    assert verdict["identity_verdict"] == "unknown"
    assert verdict["coverage_verdict"] == "absent"
    proof["pivot_multiplicity"] = 3
    verdict = identity_coverage(None, [], proof)
    assert verdict["identity_confidence"] == "medium"
    assert verdict["coverage_verdict"] == "absent"
