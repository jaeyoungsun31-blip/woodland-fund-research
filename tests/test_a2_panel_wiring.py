from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from scripts.a2_panel import (
    A2CensusRow,
    A2Exit,
    adverse_absent_case2_panel,
    apply_case2_terminal,
    bounded_exit_panels,
    classify_exit_coverage,
    drop_case4_seam,
    read_a2_census,
    signed_a2_report,
)


def _write_classification(path: Path, tests: str) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["constituent_symbol", "candidate_tests"])
        writer.writeheader()
        writer.writerow({"constituent_symbol": "SUCCESSOR", "candidate_tests": tests})


def test_signed_case_counts_and_successor_quarantine(tmp_path: Path) -> None:
    classification = tmp_path / "classification.csv"
    _write_classification(
        classification,
        '[{"a2_case":"4","agrees":false,"citation":"SEC-1","event_date":"2020-06-15"}]',
    )
    census = [
        A2CensusRow("2020:CASH", "CASH", "2020-01-01", "2020-12-31", "1", False),
        A2CensusRow("2020:BK", "BK", "2020-01-01", "2020-12-31", "2", True),
        A2CensusRow("2020:RENAME", "RENAME", "2020-01-01", "2020-12-31", "4", False),
        A2CensusRow("2020:SUCCESSOR", "SUCCESSOR", "2020-01-01", "2020-12-31", "unresolved", False),
    ]
    counts, pending = signed_a2_report(census, str(classification))
    assert counts == {"case_1": 1, "case_2": 1, "case_4": 1,
                      "pending_A2_amendment_1": 1}
    assert pending == {"2020:SUCCESSOR"}


def test_case2_terminal_and_case4_seam_are_explicit() -> None:
    series = pd.Series([0.02], index=pd.to_datetime(["2020-01-02"]))
    terminal = apply_case2_terminal(series, pd.Timestamp("2020-01-03"), -0.55)
    assert terminal.loc[pd.Timestamp("2020-01-03")] == -0.55
    assert pd.isna(drop_case4_seam(terminal, pd.Timestamp("2020-01-03")).iloc[-1])


def test_adverse_bound_uses_final_absent_membership_year() -> None:
    panel = pd.DataFrame({"LIVE": [0.01, 0.02]}, index=pd.to_datetime(["2000-01-03", "2001-12-31"]))
    census = [
        A2CensusRow("2000:BK", "BK", "2000-01-01", "2000-12-31", "2", True),
        A2CensusRow("2001:BK", "BK", "2001-01-01", "2001-12-31", "2", True),
    ]
    adverse, rows = adverse_absent_case2_panel(panel, census)
    assert adverse.loc[pd.Timestamp("2001-12-31"), "BK"] == -1.0
    assert rows == [{"symbol": "BK", "record_id": "2001:BK", "terminal_date": "2001-12-31"}]


def test_case2_adverse_treatment_is_unchanged_by_generalisation() -> None:
    panel = pd.DataFrame({"LIVE": [0.01]}, index=pd.to_datetime(["2001-12-31"]))
    census = [A2CensusRow("2001:BK", "BK", "2001-01-01", "2001-12-31", "2", True)]
    old_adverse, old_rows = adverse_absent_case2_panel(panel, census)
    _, new_adverse, bounds, new_rows = bounded_exit_panels(panel, [], census)
    pd.testing.assert_frame_equal(new_adverse, old_adverse)
    assert new_rows == old_rows
    assert bounds == []


def test_unclassified_exits_get_both_bounds_and_reconcile() -> None:
    panel = pd.DataFrame({"X": [0.01, 0.02]}, index=pd.to_datetime(["2020-01-02", "2020-01-03"]))
    census = [
        A2CensusRow("2020:X", "X", "2020-01-01", "2020-12-31", "unresolved", False),
        A2CensusRow("2020:BK", "BK", "2020-01-01", "2020-12-31", "2", True),
        A2CensusRow("2020:Q", "Q", "2020-01-01", "2020-12-31", "unresolved", False),
    ]
    exits = [
        A2Exit("2020:X", "X", pd.Timestamp("2020-01-02")),
        A2Exit("2020:BK", "BK", pd.Timestamp("2020-01-03")),
        A2Exit("2020:Q", "Q", pd.Timestamp("2020-01-02")),
    ]
    coverage, unclassified = classify_exit_coverage(exits, census, {"2020:Q"})
    assert coverage == {
        "exits_total": 3, "treated": 1,
        "by_case": {"case_1": 0, "case_2": 1, "case_4": 0},
        "unclassified": 1, "quarantined": 1,
    }
    assert (
        coverage["treated"] + coverage["unclassified"] + coverage["quarantined"]
        == coverage["exits_total"]
    )
    favourable, adverse, bounds, case2 = bounded_exit_panels(panel, unclassified, census)
    assert favourable.loc[pd.Timestamp("2020-01-03"), "X"] == 0.0
    assert adverse.loc[pd.Timestamp("2020-01-03"), "X"] == -1.0
    assert "Q" not in favourable
    assert bounds == [{"symbol": "X", "record_id": "2020:X", "terminal_date": "2020-01-03"}]
    assert case2 == [{"symbol": "BK", "record_id": "2020:BK", "terminal_date": "2020-01-03"}]


def test_census_schema_is_required(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("record_id,symbol\n2020:X,X\n")
    try:
        read_a2_census(str(path))
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("schema failure must refuse")
