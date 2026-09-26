"""Append-only paper-execution drift records and pending-order discovery."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PAPER_COST_LABEL = (
    "lower bound: paper fills omit impact, latency slippage, queue position, "
    "price improvement, fees, and liquidity constraints; IEX quoted spreads are "
    "biased upward versus the consolidated quote"
)


@dataclass(frozen=True)
class DriftRecord:
    order_id: str
    event: str
    symbol: str
    side: str
    decision_timestamp: str
    decision_close: float | None
    submit_timestamp: str | None
    feed: str
    iex_timestamp: str | None
    iex_bid: float | None
    iex_ask: float | None
    iex_spread: float | None
    iex_mid_quote: float | None
    iex_half_spread_bps: float | None
    fill_timestamp: str | None
    fill_price: float | None
    fill_quantity: float | None
    signed_implementation_shortfall_bps: float | None
    signed_shortfall_vs_iex_mid_bps: float | None
    reconciliation_reason: str | None = None
    cost_label: str = PAPER_COST_LABEL


def signed_shortfall_bps(*, side: str, decision_price: float, fill_price: float) -> float:
    """Positive values are adverse for both buys and sells."""
    if decision_price <= 0 or fill_price <= 0:
        raise ValueError("decision and fill prices must be positive")
    normalized = side.lower()
    if normalized == "buy":
        return (fill_price / decision_price - 1.0) * 10_000
    if normalized == "sell":
        return (1.0 - fill_price / decision_price) * 10_000
    raise ValueError("side must be buy or sell")


def iex_half_spread_bps(*, bid: float, ask: float, reference_price: float) -> float:
    """IEX-only half-spread; it is upward-biased versus a consolidated quote."""
    if bid <= 0 or ask <= 0 or reference_price <= 0 or ask < bid:
        raise ValueError("invalid IEX quote or reference price")
    return ((ask - bid) / 2.0) / reference_price * 10_000


def append_drift_record(path: Path, record: DriftRecord) -> None:
    """Append one immutable JSONL observation outside the research trials ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(record)
    payload["recorded_at"] = datetime.now(UTC).isoformat(timespec="seconds")
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def pending_drift_records(path: Path) -> tuple[DriftRecord, ...]:
    """Return records whose latest append-only event has not reached a terminal state."""
    if not path.exists():
        return ()
    latest: dict[str, DriftRecord] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        payload: dict[str, Any] = json.loads(line)
        payload.pop("recorded_at", None)
        record = DriftRecord(**payload)
        latest[record.order_id] = record
    return tuple(
        record
        for record in latest.values()
        if record.event in {"submitted", "reconciliation_timeout"}
    )


def logged_order_ids(path: Path) -> set[str]:
    """Return every order ID already represented by an append-only observation."""
    if not path.exists():
        return set()
    return {
        str(json.loads(line)["order_id"]) for line in path.read_text(encoding="utf-8").splitlines()
    }
