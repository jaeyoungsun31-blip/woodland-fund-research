"""Trials ledger (DESIGN.md §7, CLAUDE.md rule 4).

Every configuration the harness evaluates is recorded here — including the
ones abandoned, errored, or tried on a whim. The ledger exists so the
deflated Sharpe denominator counts the trials we actually ran rather than the
trials we felt like remembering: a 1.1 Sharpe found after 400 configurations
is noise, and only a complete ledger can say so.

SQLite because it is a durable, concurrently-readable file with no server,
and because an append-mostly table of trials is exactly what it is good at.

Deliberately NOT here: any notion of promotion or of an incumbent. The
promotion gate is Phase 3 and is pre-registered in the journal; the ledger
only counts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType
from typing import cast

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS trials (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT    NOT NULL,
    study         TEXT    NOT NULL,
    config_hash   TEXT    NOT NULL,
    config_json   TEXT    NOT NULL,
    split_scheme  TEXT,
    split_index   INTEGER,
    window        TEXT,
    status        TEXT    NOT NULL,
    cost_bps      REAL,
    sharpe        REAL,
    cagr          REAL,
    max_drawdown  REAL,
    ann_turnover  REAL,
    n_obs         INTEGER,
    notes         TEXT
);
CREATE INDEX IF NOT EXISTS ix_trials_study ON trials(study);
CREATE INDEX IF NOT EXISTS ix_trials_hash  ON trials(study, config_hash);
"""

VALID_STATUS = {"evaluated", "abandoned", "aborted", "error"}


def config_hash(config: dict) -> str:
    """Stable hash of a configuration, independent of key order."""
    return hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()[:16]


class TrialsLedger:
    """Append-mostly record of every configuration evaluated."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> TrialsLedger:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------ writing

    def record(
        self,
        study: str,
        config: dict,
        *,
        status: str = "evaluated",
        metrics: dict | None = None,
        cost_bps: float | None = None,
        split_index: int | None = None,
        window: str | None = None,
        split_scheme: dict | None = None,
        notes: str | None = None,
    ) -> int:
        """Record one trial. Returns its row id.

        Called for EVERY configuration touched, whatever the outcome — that is
        the whole point. `status="abandoned"` is for configs dropped without a
        full evaluation; they still count against the trial budget, because the
        researcher still looked.
        """
        if status not in VALID_STATUS:
            raise ValueError(f"status must be one of {sorted(VALID_STATUS)}, got {status!r}")
        m = metrics or {}
        cur = self._conn.execute(
            """INSERT INTO trials (created_at, study, config_hash, config_json,
                   split_scheme, split_index, window, status, cost_bps,
                   sharpe, cagr, max_drawdown, ann_turnover, n_obs, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now(UTC).isoformat(timespec="seconds"),
                study,
                config_hash(config),
                json.dumps(config, sort_keys=True, default=str),
                json.dumps(split_scheme, sort_keys=True) if split_scheme else None,
                split_index,
                window,
                status,
                cost_bps,
                _get(m, "sharpe", "sharpe_rf0"),
                _get(m, "cagr"),
                _get(m, "max_drawdown"),
                _get(m, "ann_turnover"),
                _get(m, "n_obs"),
                notes,
            ),
        )
        self._conn.commit()
        return int(cast(int, cur.lastrowid))

    # ------------------------------------------------------------ reading

    def n_trials(self, study: str | None = None, *, distinct: bool = True) -> int:
        """Trial count for the deflated-Sharpe denominator.

        `distinct=True` (default) counts distinct CONFIGURATIONS: re-scoring
        the same config on another split, or re-running it after a crash, is
        not another lottery ticket. `distinct=False` counts rows, which is
        what you want when auditing how much compute was spent.
        """
        col = "DISTINCT config_hash" if distinct else "*"
        sql = f"SELECT COUNT({col}) FROM trials"
        args: tuple = ()
        if study is not None:
            sql += " WHERE study = ?"
            args = (study,)
        return int(self._conn.execute(sql, args).fetchone()[0])

    def has_completed_study(self, study: str) -> bool:
        """Whether a study has an OOS-successful, immutable ledger batch."""
        row = self._conn.execute(
            "SELECT 1 FROM trials WHERE study = ? AND status = 'evaluated' LIMIT 1", (study,)
        ).fetchone()
        return row is not None

    def trials(self, study: str | None = None) -> pd.DataFrame:
        sql = "SELECT * FROM trials"
        args: tuple = ()
        if study is not None:
            sql += " WHERE study = ?"
            args = (study,)
        return pd.read_sql_query(sql + " ORDER BY id", self._conn, params=args)

    def studies(self) -> list[str]:
        return [r[0] for r in self._conn.execute(
            "SELECT DISTINCT study FROM trials ORDER BY study")]

    def config_sharpes(self, study: str | None = None) -> pd.Series:
        """One Sharpe per distinct configuration, for the variance term of the
        deflated Sharpe ratio.

        A config scored on several splits contributes its mean, so that a
        config evaluated more often does not get extra weight in the spread of
        trial outcomes.
        """
        df = self.trials(study)
        df = df[(df["status"] == "evaluated") & df["sharpe"].notna()]
        if df.empty:
            return pd.Series(dtype=float)
        return df.groupby("config_hash")["sharpe"].mean()


def _get(m: dict, *names: str) -> float | int | None:
    for n in names:
        if n in m and m[n] is not None:
            v = m[n]
            return float(v) if not isinstance(v, int) else v
    return None
