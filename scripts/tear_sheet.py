"""Write a PNG tear sheet for an already-computed ``BacktestResult``.

Import ``write`` from a research or reporting script after it has produced a
backtest result.  This module intentionally does not run a strategy itself.
"""

from __future__ import annotations

from pathlib import Path

from woodland.backtest import BacktestResult
from woodland.config import ROOT
from woodland.tearsheet import save_tear_sheet


def write(result: BacktestResult, name: str, title: str | None = None) -> Path:
    """Save ``result`` as ``reports/<name>.png`` and return its path."""
    return save_tear_sheet(
        result,
        ROOT / "reports" / f"{name}.png",
        title=title or name.replace("_", " ").title(),
    )
