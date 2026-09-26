"""The risk-free (cash) leg.

Why this module exists: the deep-history universe carries `CASH` as an explicit
asset, so v4's unallocated budget earns the T-bill rate. The ETF universe had
no such asset, and `backtest.run` hardcoded a zero return on the cash portion —
so the same portfolio was scored under two different rules depending on which
universe it ran in. That is a correctness inconsistency, not a modelling
choice, and any study built on the ETF window would have inherited it.

The strategy most affected is any that deliberately holds cash. Volatility
targeting parks unused exposure there by construction, so trend-v3 understated
its own returns by the whole T-bill yield on the un-invested fraction.

Source is the same Ken French daily factors file the deep-history universe
already uses (`RF`, the one-month Treasury bill), so both universes now read
their cash return from one series.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from woodland.config import ROOT, load_config

FACTORS_PARQUET = "fama_french_factors_daily.parquet"
CASH_COLUMN = "CASH"

# The factors file is published with a lag, so the last few weeks of an ETF
# window can sit past its end. Carrying the last known rate forward is
# defensible for a slow-moving one-month bill rate but is still an assumption,
# so it is capped and always reported rather than left implicit.
DEFAULT_MAX_STALE_BARS = 70


def load_risk_free_daily(store: Path | str) -> pd.Series:
    """Daily simple return on cash, from the Fama-French CASH index level."""
    path = Path(store) / FACTORS_PARQUET
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found — run scripts/ingest_fama_french.py to build the "
            "risk-free series"
        )
    cfg = load_config()
    configured = (ROOT / cfg["data"]["store"]).resolve()
    if Path(store).resolve() in {configured, (ROOT / "data").resolve()}:
        expected = str(cfg["data"]["risk_free_sha256"])
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(
                "configured risk-free file hash mismatch: "
                f"expected {expected}, observed {observed}; refuse research read"
            )
    levels = pd.read_parquet(path)
    if CASH_COLUMN not in levels.columns:
        raise ValueError(f"{path} has no {CASH_COLUMN!r} column")
    rf = levels[CASH_COLUMN].pct_change().dropna()
    rf.index = pd.DatetimeIndex(rf.index)
    rf.name = "risk_free"
    if (rf < -1e-12).any():
        raise ValueError("risk-free series contains negative daily rates")
    return rf


def align_risk_free(
    risk_free: pd.Series,
    index: pd.DatetimeIndex,
    *,
    max_stale_bars: int = DEFAULT_MAX_STALE_BARS,
) -> tuple[pd.Series, dict]:
    """Put a risk-free series onto a target trading calendar.

    Returns (series, provenance). Bars carried forward past the end of the
    source are counted in the provenance so every report can disclose them;
    more than `max_stale_bars` of them is an error rather than a footnote,
    because a stale rate applied over a long window is a fabricated return.

    A bar before the source begins earns nothing: there is no rate to carry
    backward, and inventing one would be worse than a zero.
    """
    index = pd.DatetimeIndex(index)
    source_index = pd.DatetimeIndex(risk_free.index)
    source_end = source_index[-1]
    aligned = risk_free.reindex(index.union(source_index)).ffill().reindex(index)

    trailing = index[index > source_end]
    if len(trailing) > max_stale_bars:
        raise ValueError(
            f"risk-free series ends {source_end.date()} but the calendar runs to "
            f"{index[-1].date()}: {len(trailing)} bars would be carried forward, "
            f"over the {max_stale_bars}-bar limit. Re-run the Fama-French ingest."
        )
    leading = int(aligned.isna().sum())
    aligned = aligned.fillna(0.0)
    aligned.name = "risk_free"

    provenance = {
        "source_first": str(source_index[0].date()),
        "source_last": str(source_end.date()),
        "calendar_first": str(index[0].date()),
        "calendar_last": str(index[-1].date()),
        "n_bars": int(len(index)),
        "n_carried_forward": int(len(trailing)),
        "n_before_source_zeroed": leading,
        "mean_annualized": float(aligned.mean() * 252),
    }
    return aligned, provenance
