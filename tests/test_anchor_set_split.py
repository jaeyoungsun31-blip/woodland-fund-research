from __future__ import annotations

import json

import pytest

from scripts import reproduce_all
from woodland.snapshot import emit_freeze_time_anchors


def test_signed_anchor_set_split_is_30_reproduced_and_23_replaced() -> None:
    split = reproduce_all.load_anchor_set_split()

    assert split.reproduced_count == 30
    assert split.replaced_count == 23
    records = reproduce_all.freeze_time_anchor_records(split)
    assert sum(record["classification"] == "reproduced" for record in records) == 30
    assert sum(record["classification"] == "replaced" for record in records) == 23


@pytest.mark.parametrize(
    ("decimals", "expected_tolerance"),
    [(1, 0.05), (2, 0.005), (3, 0.0005), (6, 0.0000005)],
)
def test_anchor_tolerance_is_half_of_its_published_last_digit(
    decimals: int, expected_tolerance: float,
) -> None:
    anchor = reproduce_all.Anchor("entry", "series", "value", 1.0, decimals)

    assert anchor.tolerance == pytest.approx(expected_tolerance)


def test_reproduced_gate_refuses_delta_above_its_own_published_tolerance() -> None:
    anchor = reproduce_all.load_anchor_set_split().reproduced_groups[0].anchors[0]
    tolerance = anchor.tolerance

    assert reproduce_all.anchor_passes(anchor, anchor.journalled + tolerance)
    assert not reproduce_all.anchor_passes(anchor, anchor.journalled + tolerance + 0.000001)


def test_reproduced_gate_uses_each_anchor_precision_not_a_flat_floor() -> None:
    split = reproduce_all.load_anchor_set_split()
    coarse = next(
        anchor
        for group in split.reproduced_groups
        for anchor in group.anchors
        if anchor.decimals == 1
    )
    check = reproduce_all.check_reproduced_anchor(coarse, coarse.journalled + 0.01)

    assert check.tolerance == pytest.approx(0.05)
    assert check.passes


def test_replaced_anchors_have_no_pass_field() -> None:
    records = reproduce_all.freeze_time_anchor_records(reproduce_all.load_anchor_set_split())
    replaced = [record for record in records if record["classification"] == "replaced"]

    assert len(replaced) == 23
    assert all("passes" not in record for record in replaced)


def test_freeze_time_anchor_emission_is_snapshot_local_and_non_overwriting(tmp_path) -> None:
    snapshot = {"sha256": "abc123", "as_of": "2026-09-04"}
    snapshot_dir = tmp_path / "etf-abc123"
    snapshot_dir.mkdir()
    anchors = [{"classification": "reproduced", "series": "example", "value": 1.0}]

    path = emit_freeze_time_anchors(snapshot_dir, snapshot=snapshot, anchors=anchors)
    assert json.loads(path.read_text()) == {"snapshot": snapshot, "anchors": anchors}
    assert emit_freeze_time_anchors(snapshot_dir, snapshot=snapshot, anchors=anchors) == path
    with pytest.raises(ValueError, match="already differ"):
        emit_freeze_time_anchors(
            snapshot_dir,
            snapshot=snapshot,
            anchors=[{"classification": "reproduced", "series": "example", "value": 2.0}],
        )
