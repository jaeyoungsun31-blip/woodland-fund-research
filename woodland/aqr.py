"""AQR Time Series Momentum factor ingestion — external validation only.

The TSMOM factor of Moskowitz, Ooi & Pedersen (2012), published free by AQR and
updated since. It exists here for one purpose: to ask whether this project's
trend implementation reproduces the documented effect, or has quietly built
something else.

Construction differences that matter when reading any correlation against it:

  * AQR's factor is LONG/SHORT across ~60 futures markets, scaled to a constant
    volatility target. Ours is LONG-ONLY, unlevered, on a handful of ETFs.
  * AQR reports EXCESS returns; ours must be put on the same basis before
    comparison.
  * AQR is MONTHLY. Daily series must be compounded to month ends to align.

So a high correlation would be evidence the same phenomenon is being captured;
a beta near 1 would NOT be expected, and its absence is not a failure.

This module is optional: it needs the `external` extra for xlsx support, and
the core pipeline never reads spreadsheets.
"""

from __future__ import annotations

import hashlib
import io
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

TSMOM_URL = (
    "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/"
    "Time-Series-Momentum-Factors-Monthly.xlsx"
)
SHEET = "TSMOM Factors"
HEADLINE = "TSMOM"
BROWSER_UA = "Mozilla/5.0"


@dataclass(frozen=True)
class AqrIngestResult:
    returns: pd.DataFrame
    data_path: Path
    provenance_path: Path
    provenance: dict[str, object]


def fetch_tsmom_monthly(timeout: int = 90) -> bytes:
    """Download the published TSMOM monthly workbook."""
    response = requests.get(TSMOM_URL, timeout=timeout, headers={"User-Agent": BROWSER_UA})
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise ValueError("AQR endpoint did not return an xlsx workbook")
    return response.content


def parse_tsmom_monthly(payload: bytes) -> pd.DataFrame:
    """Parse monthly TSMOM factor excess returns from the workbook payload.

    The sheet carries a dozen lines of preamble before the header, and AQR
    changes its wording, so the header is located by looking for the row whose
    second cell is the headline factor name rather than by a fixed offset.
    """
    try:
        raw = pd.read_excel(io.BytesIO(payload), sheet_name=SHEET, header=None)
    except ImportError as error:                      # openpyxl missing
        raise RuntimeError(
            "reading the AQR workbook needs the 'external' extra: "
            "uv pip install -e '.[external]'"
        ) from error

    if raw.shape[1] < 2:
        raise ValueError(
            f"sheet {SHEET!r} has {raw.shape[1]} column(s); expected a date column "
            "plus at least one factor"
        )
    header_index = None
    for i in range(len(raw)):
        if str(raw.iat[i, 1]).strip() == HEADLINE:
            header_index = i
            break
    if header_index is None:
        raise ValueError(f"{HEADLINE!r} header row not found in sheet {SHEET!r}")

    columns = [str(v).strip() for v in raw.iloc[header_index, 1:].tolist()]
    body = raw.iloc[header_index + 1 :].copy()
    dates = pd.to_datetime(body.iloc[:, 0], errors="coerce")
    values = body.iloc[:, 1:].apply(pd.to_numeric, errors="coerce")
    values.columns = columns
    values.index = pd.DatetimeIndex(dates)

    factors = values[values.index.notna() & values[HEADLINE].notna()]
    if factors.empty:
        raise ValueError("no dated TSMOM observations parsed")
    factors = pd.DataFrame(factors)
    factors.index.name = "Date"
    if factors.index.has_duplicates or not factors.index.is_monotonic_increasing:
        raise ValueError("AQR factor dates must be unique and increasing")
    if float(factors[HEADLINE].abs().max()) > 1.0:
        raise ValueError("TSMOM values look like percentages, not decimals")
    return factors


def ingest_tsmom_monthly(
    data_path: Path, provenance_path: Path | None = None, timeout: int = 90
) -> AqrIngestResult:
    """Download, validate and persist the TSMOM factor with provenance."""
    payload = fetch_tsmom_monthly(timeout=timeout)
    factors = parse_tsmom_monthly(payload)

    data_path = Path(data_path)
    provenance_path = provenance_path or data_path.with_name(f"{data_path.stem}_provenance.json")
    data_path.parent.mkdir(parents=True, exist_ok=True)
    factors.to_parquet(data_path)

    provenance: dict[str, object] = {
        "source": "AQR Capital Management data library",
        "source_url": TSMOM_URL,
        "archive_sha256": hashlib.sha256(payload).hexdigest(),
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "reference": (
            "Moskowitz, Ooi & Pedersen (2012), 'Time Series Momentum', "
            "Journal of Financial Economics 104(2), 228-250"
        ),
        "frequency": "monthly",
        "values": "excess returns, decimal",
        "columns": list(factors.columns),
        "first": str(factors.index[0].date()),
        "last": str(factors.index[-1].date()),
        "rows": int(len(factors)),
        "limitations": (
            "Long/short, volatility-targeted, ~60 futures markets. Not directly "
            "comparable in scale to a long-only unlevered ETF portfolio; use for "
            "correlation of returns, not for level or beta expectations."
        ),
    }
    provenance_path.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n")
    return AqrIngestResult(
        returns=factors, data_path=data_path,
        provenance_path=provenance_path, provenance=provenance,
    )


def load_tsmom_monthly(
    store: Path | str, filename: str = "aqr_tsmom_monthly.parquet"
) -> pd.DataFrame:
    path = Path(store) / filename
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run scripts/ingest_aqr.py")
    return pd.read_parquet(path)


def to_month_end_returns(daily: pd.Series) -> pd.Series:
    """Compound a daily return series to month-end totals, for AQR alignment."""
    return (1.0 + daily.dropna()).resample("ME").prod() - 1.0
