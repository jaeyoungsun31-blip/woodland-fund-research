import importlib.util
from pathlib import Path

import pytest

from woodland.harness import costaware_panel, universe_control

_NEEDS_PANEL = pytest.mark.skipif(
    not universe_control.MEMBERSHIP.exists(),
    reason="gitignored constituent panel (reports/security-resolver/) is absent",
)


def _runner_module():
    path = Path(__file__).resolve().parents[1] / "scripts/run_xsmom_v16_universe_control.py"
    spec = importlib.util.spec_from_file_location("universe_control_runner", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@_NEEDS_PANEL
def test_universe_control_effective_costs_are_the_signed_four_only() -> None:
    original = costaware_panel.COSTS

    with universe_control.configured_costaware():
        assert costaware_panel.COSTS == (0.0, 5.0, 10.0, 25.0)
        assert len(costaware_panel.COSTS) == 4
        assert 50.0 not in costaware_panel.COSTS

    assert original == costaware_panel.COSTS


@_NEEDS_PANEL
def test_configured_costaware_creates_output_root_not_arm_directory(
    monkeypatch, tmp_path: Path
) -> None:
    output_root = tmp_path / "xsmom-v16-universe-control"
    monkeypatch.setattr(universe_control, "OUT", output_root)

    with universe_control.configured_costaware():
        assert output_root.is_dir()
        assert not (output_root / "universe-control").exists()

    assert output_root.is_dir()
    assert not (output_root / "universe-control").exists()


def test_g2_uses_the_amended_symmetric_25_bps_pair() -> None:
    penalized_25 = object()
    momentum_25 = object()
    runs = {
        ("penalized", 10.0): object(),
        ("penalized", 25.0): penalized_25,
        ("momentum", 10.0): object(),
        ("momentum", 25.0): momentum_25,
    }

    assert universe_control.G2_COST_BPS == 25.0
    assert costaware_panel.momentum_gate_pair(runs, universe_control.G2_COST_BPS) == (
        penalized_25,
        momentum_25,
    )


def test_execute_prints_and_persists_result_without_later_preflight(
    monkeypatch, tmp_path: Path, capsys
) -> None:
    runner = _runner_module()
    result = {"status": "completed", "trials": 352}
    monkeypatch.setattr(runner, "execute", lambda: result)
    monkeypatch.setattr(
        runner,
        "preflight",
        lambda: (_ for _ in ()).throw(AssertionError("preflight must not be called")),
    )
    monkeypatch.setattr(runner, "SUMMARY", tmp_path / "summary.json")

    assert runner.main(["--execute"]) == 0
    assert runner.SUMMARY.read_text() == '{\n  "status": "completed",\n  "trials": 352\n}'
    assert capsys.readouterr().out == '{\n  "status": "completed",\n  "trials": 352\n}\n'
