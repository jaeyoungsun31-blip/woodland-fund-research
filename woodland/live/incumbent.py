"""Declared and durable incumbent state.

The incumbent cannot change through evaluation.  Initialisation and
replacement are separate, explicit methods; replacement requires the journal
entry authorising the change and appends a local promotion audit record.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

BALANCED_NAME = "balanced-60-40"
BALANCED_PARAMETERS: dict[str, object] = {
    "weights": {"SPY": 0.60, "IEF": 0.40},
    "rebalance": "monthly",
    "execution": "next_close",
}
BALANCED_EFFECTIVE_DATE = date(2026, 9, 3)
BALANCED_JOURNAL = "journal/2026-09-03-planning-direction-phase3-the-machine.md"


def _cost_column(cost_bps: float) -> str:
    return f"{float(cost_bps):g}"


@dataclass(frozen=True)
class Incumbent:
    """Complete evidence and provenance for the currently deployed model."""

    name: str
    parameters: Mapping[str, Any]
    effective_date: date
    journal_entry: str
    oos_returns: Mapping[float, pd.Series]
    oos_turnover: Mapping[float, pd.Series]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("incumbent name must not be empty")
        if not self.journal_entry.endswith(".md"):
            raise ValueError("incumbent journal_entry must reference a Markdown journal entry")
        costs = set(self.oos_returns)
        if not costs:
            raise ValueError("incumbent must store at least one OOS return series")
        if costs != set(self.oos_turnover):
            raise ValueError("return and turnover cost scenarios must match")
        for cost in costs:
            returns = self.oos_returns[cost]
            turnover = self.oos_turnover[cost]
            if not returns.index.equals(turnover.index):
                raise ValueError(f"return/turnover calendars differ at {cost:g} bps")
            if returns.empty or returns.isna().any() or turnover.isna().any():
                raise ValueError(f"stored OOS evidence is empty or incomplete at {cost:g} bps")

    @property
    def costs(self) -> tuple[float, ...]:
        return tuple(sorted(float(cost) for cost in self.oos_returns))


def balanced_seed(
    returns: Mapping[float, pd.Series], turnover: Mapping[float, pd.Series]
) -> Incumbent:
    """Build the planning-declared 60/40 incumbent from existing OOS evidence."""
    return Incumbent(
        name=BALANCED_NAME,
        parameters=BALANCED_PARAMETERS,
        effective_date=BALANCED_EFFECTIVE_DATE,
        journal_entry=BALANCED_JOURNAL,
        oos_returns=returns,
        oos_turnover=turnover,
    )


class IncumbentStore:
    """File-backed incumbent registry with an append-only replacement log."""

    def __init__(self, directory: Path | str):
        self.directory = Path(directory)
        self.metadata_path = self.directory / "incumbent.json"
        self.returns_path = self.directory / "incumbent_returns.parquet"
        self.turnover_path = self.directory / "incumbent_turnover.parquet"
        self.audit_path = self.directory / "promotion_log.jsonl"

    @property
    def exists(self) -> bool:
        return (
            self.metadata_path.exists()
            and self.returns_path.exists()
            and self.turnover_path.exists()
        )

    def load(self) -> Incumbent:
        if not self.exists:
            raise FileNotFoundError(f"no complete incumbent state in {self.directory}")
        metadata = json.loads(self.metadata_path.read_text())
        returns_frame = pd.read_parquet(self.returns_path)
        turnover_frame = pd.read_parquet(self.turnover_path)
        costs = [float(value) for value in metadata["costs_bps"]]
        return Incumbent(
            name=str(metadata["name"]),
            parameters=metadata["parameters"],
            effective_date=date.fromisoformat(str(metadata["effective_date"])),
            journal_entry=str(metadata["journal_entry"]),
            oos_returns={cost: returns_frame[_cost_column(cost)] for cost in costs},
            oos_turnover={cost: turnover_frame[_cost_column(cost)] for cost in costs},
        )

    def initialize(self, incumbent: Incumbent) -> None:
        """Persist the first incumbent; never overwrites an existing declaration."""
        if self.exists:
            raise FileExistsError(f"incumbent already initialized in {self.directory}")
        self._write(incumbent)
        self._append_audit("initialize", None, incumbent)

    def replace(self, incumbent: Incumbent, *, journal_entry: str) -> None:
        """Explicitly replace the incumbent under a matching journal authority."""
        if not self.exists:
            raise FileNotFoundError("initialize the incumbent before replacing it")
        if journal_entry != incumbent.journal_entry or not journal_entry.endswith(".md"):
            raise ValueError("replacement requires the incumbent's exact journal reference")
        previous = self.load()
        if incumbent.effective_date < previous.effective_date:
            raise ValueError("replacement effective date predates the current incumbent")
        self._write(incumbent)
        self._append_audit("replace", previous, incumbent)

    def _write(self, incumbent: Incumbent) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        returns = pd.DataFrame(
            {_cost_column(cost): incumbent.oos_returns[cost] for cost in incumbent.costs}
        )
        turnover = pd.DataFrame(
            {_cost_column(cost): incumbent.oos_turnover[cost] for cost in incumbent.costs}
        )
        returns.to_parquet(self.returns_path)
        turnover.to_parquet(self.turnover_path)
        metadata = {
            "name": incumbent.name,
            "parameters": incumbent.parameters,
            "effective_date": incumbent.effective_date.isoformat(),
            "journal_entry": incumbent.journal_entry,
            "costs_bps": list(incumbent.costs),
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    def _append_audit(
        self, operation: str, previous: Incumbent | None, current: Incumbent
    ) -> None:
        event = {
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "operation": operation,
            "from": previous.name if previous else None,
            "to": current.name,
            "effective_date": current.effective_date.isoformat(),
            "journal_entry": current.journal_entry,
        }
        with self.audit_path.open("a") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")
