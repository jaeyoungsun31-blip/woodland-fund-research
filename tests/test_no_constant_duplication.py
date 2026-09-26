"""No study script may define its own value for a shared constant.

This is the test that makes woodland/study.py load-bearing rather than
advisory. Before it existed, MAX_LOOKBACK_DAYS = 210 appeared in ten scripts,
the nine-sector universe in seven, and stitch() was defined eleven times — so
a study whose universe silently disagreed with its predecessor's would run,
print, and be journalled with nothing to catch it.

A script that genuinely needs a variant must give it a DIFFERENT name, so the
divergence is visible instead of being disguised as agreement.
"""

import ast
from pathlib import Path

import pytest

from woodland import study

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
STUDY_SCRIPTS = sorted(SCRIPTS.glob("*.py"))


def assigned_names(path: Path) -> set[str]:
    """Module-level names a script assigns to. Imports are not assignments."""
    tree = ast.parse(path.read_text(), filename=str(path))
    names: set[str] = set()
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Tuple):      # A, B = 1, 2
                names.update(e.id for e in target.elts if isinstance(e, ast.Name))
    return names


def test_there_are_scripts_to_check():
    """Guard against the suite passing because the glob found nothing."""
    assert len(STUDY_SCRIPTS) >= 10


@pytest.mark.parametrize("path", STUDY_SCRIPTS, ids=lambda p: p.name)
def test_script_does_not_redefine_a_shared_constant(path):
    clashes = sorted(assigned_names(path) & study.OWNED_CONSTANTS)
    assert not clashes, (
        f"{path.name} assigns {clashes}, which woodland/study.py owns. "
        f"Import them instead, or rename the local if it is genuinely a "
        f"different quantity."
    )


def test_no_script_defines_its_own_stitch():
    """The helper that was copied eleven times."""
    offenders = []
    for path in STUDY_SCRIPTS:
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in {"stitch", "stitch_targets"}:
                offenders.append(path.name)
    assert not offenders, (
        f"{offenders} define their own stitch(); import it from woodland.study"
    )


# Values a script must not restate under a local alias. Name-collision alone
# is not enough: PRIMARY = ["SPY", "EFA", ...] duplicates MULTI_ASSET exactly
# while dodging a check that only looks at names.
def _literal(node: ast.AST) -> object | None:
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


OWNED_VALUES = {
    name: getattr(study, name)
    for name in study.OWNED_CONSTANTS
    # scalars collide by coincidence far too often to be evidence
    if isinstance(getattr(study, name), (list, tuple, frozenset, set))
}


@pytest.mark.parametrize("path", STUDY_SCRIPTS, ids=lambda p: p.name)
def test_script_does_not_restate_a_shared_value_under_another_name(path):
    """A universe copied verbatim under a local alias is the same divergence
    risk as one copied under the same name, and harder to spot."""
    tree = ast.parse(path.read_text(), filename=str(path))
    offences = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = _literal(node.value)
        if value is None or not isinstance(value, (list, tuple)):
            continue
        for owned_name, owned_value in OWNED_VALUES.items():
            if list(value) == list(owned_value) and len(list(value)) > 2:
                local = [t.id for t in node.targets if isinstance(t, ast.Name)]
                offences.append(f"{local or '?'} restates {owned_name}")
    assert not offences, (
        f"{path.name}: {offences}. Import the shared constant instead of "
        f"restating its value."
    )


def test_owned_constants_all_exist_on_the_module():
    """The registry cannot drift from what the module actually exports."""
    missing = sorted(n for n in study.OWNED_CONSTANTS if not hasattr(study, n))
    assert not missing, f"OWNED_CONSTANTS names nothing: {missing}"
