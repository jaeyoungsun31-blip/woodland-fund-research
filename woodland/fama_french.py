"""Fama-French 12-industry daily portfolio ingestion.

The Ken French Data Library publishes daily percentage returns for twelve
value-weighted US industry portfolios.  They are academic, frictionless
constructs rather than tradeable securities: the derived index levels in this
module contain no spreads, commissions, market impact, or implementation lag.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

FF12_DAILY_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "12_Industry_Portfolios_daily_CSV.zip"
)
FF_FACTORS_DAILY_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_daily_CSV.zip"
)
VALUE_WEIGHTED_HEADING = "Average Value Weighted Returns -- Daily"
FACTOR_COLUMNS = ("Mkt-RF", "SMB", "HML", "RF")
INDUSTRIES = (
    "NoDur",
    "Durbl",
    "Manuf",
    "Enrgy",
    "Chems",
    "BusEq",
    "Telcm",
    "Utils",
    "Shops",
    "Hlth",
    "Money",
    "Other",
)
MISSING_SENTINELS = {-99.99, -999.0}


@dataclass(frozen=True)
class FamaFrenchIngestResult:
    """In-memory result plus the two persisted artifact paths."""

    returns: pd.DataFrame
    levels: pd.DataFrame
    data_path: Path
    provenance_path: Path
    provenance: dict[str, object]


def fetch_12_industry_daily(timeout: int = 60) -> bytes:
    """Download the official Ken French 12-industry daily ZIP archive."""
    response = requests.get(FF12_DAILY_URL, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise ValueError("Fama-French endpoint did not return a ZIP archive")
    return response.content


def _read_csv_member(payload: bytes) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if len(members) != 1:
                raise ValueError(f"expected one CSV in archive, found {len(members)}")
            member = members[0]
            return member, archive.read(member).decode("utf-8-sig")
    except zipfile.BadZipFile as error:
        raise ValueError("invalid Fama-French ZIP archive") from error


def parse_12_industry_daily(payload: bytes) -> pd.DataFrame:
    """Parse decimal value-weighted returns from the official ZIP payload.

    The source file also contains equal-weighted returns.  Parsing stops at
    the end of the first dated block so the two sections cannot be spliced.
    Source percentages are converted to decimal returns.
    """
    _, text = _read_csv_member(payload)
    lines = text.splitlines()
    try:
        heading_index = next(
            index for index, line in enumerate(lines) if line.strip() == VALUE_WEIGHTED_HEADING
        )
    except StopIteration as error:
        raise ValueError("value-weighted daily return section not found") from error

    if heading_index + 1 >= len(lines):
        raise ValueError("value-weighted section has no header")
    header = [value.strip() for value in next(csv.reader([lines[heading_index + 1]]))]
    if header[0] != "" or tuple(header[1:]) != INDUSTRIES:
        raise ValueError(f"unexpected 12-industry header: {header}")

    rows: list[list[str]] = []
    for line in lines[heading_index + 2 :]:
        fields = [value.strip() for value in next(csv.reader([line]))]
        if not fields or re.fullmatch(r"\d{8}", fields[0]) is None:
            break
        if len(fields) != len(INDUSTRIES) + 1:
            raise ValueError(f"malformed 12-industry row for {fields[0]!r}")
        rows.append(fields)
    if not rows:
        raise ValueError("value-weighted section contains no dated rows")

    dates = pd.to_datetime([row[0] for row in rows], format="%Y%m%d", errors="raise")
    values = [[float(value) for value in row[1:]] for row in rows]
    returns = pd.DataFrame(values, index=dates, columns=list(INDUSTRIES), dtype=float)
    returns.index.name = "Date"
    returns = returns.mask(returns.isin(MISSING_SENTINELS)) / 100.0
    if returns.index.has_duplicates or not returns.index.is_monotonic_increasing:
        raise ValueError("Fama-French dates must be unique and increasing")
    return returns


def returns_to_index_levels(returns: pd.DataFrame, base: float = 100.0) -> pd.DataFrame:
    """Compound decimal returns into synthetic index levels starting at ``base``."""
    if base <= 0:
        raise ValueError("index base must be positive")
    if returns.empty:
        raise ValueError("cannot construct index levels from empty returns")
    if returns.isna().any().any():
        raise ValueError("cannot construct index levels across missing returns")
    if (returns <= -1.0).any().any():
        raise ValueError("returns at or below -100% cannot be compounded")
    levels = (1.0 + returns).cumprod() * base
    levels.index.name = returns.index.name
    return levels


def ingest_12_industry_daily(
    data_path: Path,
    provenance_path: Path | None = None,
    timeout: int = 60,
) -> FamaFrenchIngestResult:
    """Download, validate, derive index levels, and persist rebuildable data."""
    payload = fetch_12_industry_daily(timeout=timeout)
    member, _ = _read_csv_member(payload)
    returns = parse_12_industry_daily(payload)
    levels = returns_to_index_levels(returns)
    if returns.index[0] > pd.Timestamp("1926-07-01"):
        raise ValueError(f"deep-history source begins unexpectedly late: {returns.index[0].date()}")

    data_path = Path(data_path)
    provenance_path = provenance_path or data_path.with_name(f"{data_path.stem}_provenance.json")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    levels.to_parquet(data_path)

    provenance: dict[str, object] = {
        "source": "Kenneth R. French Data Library",
        "source_url": FF12_DAILY_URL,
        "archive_member": member,
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "portfolio_weighting": "value weighted",
        "source_values": "daily percentage returns",
        "stored_values": "synthetic index levels from decimal returns, base 100",
        "first": str(returns.index[0].date()),
        "last": str(returns.index[-1].date()),
        "rows": len(returns),
        "industries": list(INDUSTRIES),
        "limitations": (
            "Frictionless academic portfolios; not tradeable securities. "
            "Levels omit spreads, commissions, market impact, and implementation lag."
        ),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return FamaFrenchIngestResult(
        returns=returns,
        levels=levels,
        data_path=data_path,
        provenance_path=provenance_path,
        provenance=provenance,
    )


# --------------------------------------------------------------- factors

def fetch_research_factors_daily(timeout: int = 60) -> bytes:
    """Download the official Ken French daily research-factors ZIP archive."""
    response = requests.get(FF_FACTORS_DAILY_URL, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise ValueError("Fama-French factors endpoint did not return a ZIP archive")
    return response.content


def parse_research_factors_daily(payload: bytes) -> pd.DataFrame:
    """Parse decimal daily Mkt-RF, SMB, HML and RF from the official payload.

    Supplies the two series the 12-industry file lacks: a risk-free (one-month
    Treasury bill) rate for the strategy's defensive leg, and the
    value-weighted market return for a like-for-like equity baseline over the
    full 1926+ window.
    """
    _, text = _read_csv_member(payload)
    lines = text.splitlines()
    try:
        header_index = next(
            index for index, line in enumerate(lines)
            if tuple(value.strip() for value in next(csv.reader([line]))[1:]) == FACTOR_COLUMNS
        )
    except StopIteration as error:
        raise ValueError(f"factor header {FACTOR_COLUMNS} not found") from error

    rows: list[list[str]] = []
    for line in lines[header_index + 1 :]:
        fields = [value.strip() for value in next(csv.reader([line]))]
        if not fields or re.fullmatch(r"\d{8}", fields[0]) is None:
            break
        if len(fields) != len(FACTOR_COLUMNS) + 1:
            raise ValueError(f"malformed factor row for {fields[0]!r}")
        rows.append(fields)
    if not rows:
        raise ValueError("factor section contains no dated rows")

    dates = pd.to_datetime([row[0] for row in rows], format="%Y%m%d", errors="raise")
    values = [[float(value) for value in row[1:]] for row in rows]
    factors = pd.DataFrame(values, index=dates, columns=list(FACTOR_COLUMNS), dtype=float)
    factors.index.name = "Date"
    factors = factors.mask(factors.isin(MISSING_SENTINELS)) / 100.0
    if factors.index.has_duplicates or not factors.index.is_monotonic_increasing:
        raise ValueError("Fama-French factor dates must be unique and increasing")
    return factors


def market_and_cash_returns(factors: pd.DataFrame) -> pd.DataFrame:
    """Derive tradeable-analogue return series from the research factors.

    MKT is the value-weighted market TOTAL return (Mkt-RF + RF); CASH is the
    risk-free rate itself, which is what the defensive leg earns. DESIGN.md §9
    specifies the trend rule's alternative as "T-bills/IEF", so on this
    1926-2026 window the T-bill leg is the more faithful of the two, not a
    substitute forced by data limits.
    """
    missing = {"Mkt-RF", "RF"} - set(factors.columns)
    if missing:
        raise ValueError(f"factors missing {sorted(missing)}")
    frame = factors[["Mkt-RF", "RF"]].dropna()
    if frame.empty:
        raise ValueError("no complete factor observations")
    out = pd.DataFrame(
        {"MKT": frame["Mkt-RF"] + frame["RF"], "CASH": frame["RF"]},
        index=frame.index,
    )
    out.index.name = factors.index.name
    return out


def ingest_research_factors_daily(
    data_path: Path,
    provenance_path: Path | None = None,
    timeout: int = 60,
) -> FamaFrenchIngestResult:
    """Download, validate, derive MKT/CASH index levels, and persist."""
    from woodland.snapshot import refuse_pinned_write

    refuse_pinned_write(data_path)
    payload = fetch_research_factors_daily(timeout=timeout)
    member, _ = _read_csv_member(payload)
    factors = parse_research_factors_daily(payload)
    returns = market_and_cash_returns(factors)
    levels = returns_to_index_levels(returns)
    if returns.index[0] > pd.Timestamp("1926-07-01"):
        raise ValueError(f"factor history begins unexpectedly late: {returns.index[0].date()}")

    data_path = Path(data_path)
    provenance_path = provenance_path or data_path.with_name(f"{data_path.stem}_provenance.json")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    levels.to_parquet(data_path)

    provenance: dict[str, object] = {
        "source": "Kenneth R. French Data Library",
        "source_url": FF_FACTORS_DAILY_URL,
        "archive_member": member,
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_values": "daily percentage factor returns",
        "stored_values": "synthetic index levels, base 100; MKT = Mkt-RF + RF, CASH = RF",
        "first": str(returns.index[0].date()),
        "last": str(returns.index[-1].date()),
        "rows": len(returns),
        "series": ["MKT", "CASH"],
        "limitations": (
            "Frictionless academic constructs; not tradeable securities. MKT is the "
            "CRSP value-weighted market total return, not an index fund, and CASH is "
            "the one-month Treasury bill rate, not a money-market product."
        ),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return FamaFrenchIngestResult(
        returns=returns, levels=levels, data_path=data_path,
        provenance_path=provenance_path, provenance=provenance,
    )
