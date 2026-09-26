"""Fail-closed Alpaca Paper submission and durable fill reconciliation."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import requests

from woodland.config import get_secret
from woodland.live.drift import (
    DriftRecord,
    iex_half_spread_bps,
    logged_order_ids,
    pending_drift_records,
    signed_shortfall_bps,
)

PAPER_HOST = "paper-api.alpaca.markets"
PAPER_BASE_URL = f"https://{PAPER_HOST}/v2"
DATA_BASE_URL = "https://data.alpaca.markets/v2"
IEX_FEED = "iex"
DEFAULT_MAX_ORDER_NOTIONAL = 10_000.0

log = logging.getLogger(__name__)


class PaperSubmissionRefused(RuntimeError):
    """An expected execution guardrail, rather than a broker failure."""


def _redact_broker_text(value: object, credentials: Sequence[str]) -> str:
    """Render broker diagnostics without leaking supplied credentials or headers."""
    text = str(value)
    for credential in credentials:
        if credential:
            text = text.replace(credential, "[REDACTED]")
    return re.sub(
        r"(?i)(apca-api-(?:key-id|secret-key)|authorization)\s*[:=]\s*"
        r"(?:bearer\s+[^,;\s]+|[^,;\s]+)",
        r"\1=[REDACTED]",
        text,
    )


@dataclass(frozen=True)
class PlannedOrder:
    symbol: str
    side: str
    quantity: float
    notional: float
    decision_timestamp: str
    decision_close: float
    iex_timestamp: str
    iex_bid: float
    iex_ask: float
    iex_mid_quote: float


@dataclass(frozen=True)
class SubmissionResult:
    """Orders actually accepted by Paper, with their execution turnover basis."""

    records: tuple[DriftRecord, ...]
    orders: tuple[PlannedOrder, ...]
    account_equity: float

    @property
    def submitted_notional(self) -> float:
        return sum(order.notional for order in self.orders)

    @property
    def submitted_one_way_turnover(self) -> float:
        return self.submitted_notional / self.account_equity


@dataclass(frozen=True)
class RebalancePlan:
    """Band-respecting orders sized from the current expected exposure."""

    orders: tuple[PlannedOrder, ...]
    account_equity: float


def assert_paper_base_url(base_url: str) -> None:
    """Reject any execution endpoint other than Alpaca's paper trading host."""
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or parsed.hostname != PAPER_HOST:
        raise PaperSubmissionRefused(
            f"submission refused: execution host must be exactly {PAPER_HOST}"
        )


def validate_submission(
    *,
    phase3_refused: bool,
    market_open: bool,
    target_weights: Mapping[str, float],
    orders: Sequence[PlannedOrder],
    max_order_notional: float = DEFAULT_MAX_ORDER_NOTIONAL,
) -> tuple[str, ...]:
    """Return every pre-submit refusal so no order can be partly submitted."""
    reasons: list[str] = []
    if phase3_refused:
        reasons.append("phase3_refusal")
    if not market_open:
        reasons.append("market_closed")
    if max_order_notional <= 0:
        reasons.append("invalid_notional_cap")
    for symbol, weight in target_weights.items():
        if not 0.0 <= float(weight) <= 1.0:
            reasons.append(f"target_out_of_bounds:{symbol}")
    if sum(abs(float(weight)) for weight in target_weights.values()) > 1.0 + 1e-12:
        reasons.append("gross_target_exceeds_100pct")
    for order in orders:
        if order.notional > max_order_notional:
            reasons.append(f"order_notional_cap:{order.symbol}")
    return tuple(reasons)


class PaperBroker:
    """Paper-only client; submitted records are persisted before the next POST."""

    def __init__(
        self, key: str, secret: str, *, base_url: str = PAPER_BASE_URL, session: Any = requests
    ) -> None:
        assert_paper_base_url(base_url)
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}

    @classmethod
    def from_environment(cls) -> PaperBroker:
        key = get_secret("ALPACA_API_KEY")
        secret = get_secret("ALPACA_API_SECRET")
        if not key or not secret:
            raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_API_SECRET")
        return cls(key, secret)

    def _raise_for_status(self, response: Any, *, method: str, path: str) -> None:
        """Log the provider's safe diagnostic fields before preserving its HTTP error."""
        try:
            response.raise_for_status()
        except requests.HTTPError:
            payload: object = {}
            with suppress(TypeError, ValueError):
                payload = response.json()
            if isinstance(payload, Mapping):
                code = payload.get("code", "unknown")
                message = payload.get("message", payload.get("error", "unavailable"))
            else:
                code, message = "unknown", "unavailable"
            credentials = tuple(str(value) for value in self._headers.values())
            log.error(
                "Alpaca HTTP failure method=%s path=%s status=%s code=%s message=%s",
                method,
                path,
                getattr(response, "status_code", "unknown"),
                _redact_broker_text(code, credentials),
                _redact_broker_text(message, credentials),
            )
            raise

    def _get(
        self, path: str, *, params: Mapping[str, str] | None = None
    ) -> Mapping[str, Any] | list[Mapping[str, Any]]:
        assert_paper_base_url(self._base_url)
        response = self._session.get(
            f"{self._base_url}{path}", headers=self._headers, params=params, timeout=20
        )
        self._raise_for_status(response, method="GET", path=path)
        return cast(Mapping[str, Any] | list[Mapping[str, Any]], response.json())

    def _post(self, path: str, payload: Mapping[str, object]) -> Mapping[str, Any]:
        assert_paper_base_url(self._base_url)
        response = self._session.post(
            f"{self._base_url}{path}", headers=self._headers, json=payload, timeout=20
        )
        self._raise_for_status(response, method="POST", path=path)
        return cast(Mapping[str, Any], response.json())

    def market_open(self) -> bool:
        clock = self._get("/clock")
        assert isinstance(clock, Mapping)
        return bool(clock.get("is_open", False))

    def _latest_quotes(self, symbols: Sequence[str]) -> dict[str, tuple[float, float, str]]:
        response = self._session.get(
            f"{DATA_BASE_URL}/stocks/quotes/latest",
            headers=self._headers,
            params={"feed": IEX_FEED, "symbols": ",".join(symbols)},
            timeout=20,
        )
        self._raise_for_status(response, method="GET", path="/stocks/quotes/latest")
        raw = response.json()
        assert isinstance(raw, Mapping)
        quotes = raw.get("quotes", {})
        if not isinstance(quotes, Mapping):
            raise PaperSubmissionRefused("submission refused: malformed IEX quote response")
        result: dict[str, tuple[float, float, str]] = {}
        for symbol in symbols:
            quote = quotes.get(symbol)
            if not isinstance(quote, Mapping):
                raise PaperSubmissionRefused(f"submission refused: no IEX quote for {symbol}")
            bid, ask = float(quote["bp"]), float(quote["ap"])
            if bid <= 0 or ask < bid:
                raise PaperSubmissionRefused(f"submission refused: invalid IEX quote for {symbol}")
            result[symbol] = (bid, ask, str(quote.get("t") or datetime.now(UTC).isoformat()))
        return result

    def plan_rebalance(
        self,
        target_weights: Mapping[str, float],
        *,
        decision_close: Mapping[str, float],
        decision_timestamp: str,
        band: float,
    ) -> RebalancePlan:
        account, positions, open_orders = (
            self._get("/account"),
            self._get("/positions"),
            self._get("/orders", params={"status": "open"}),
        )
        assert (
            isinstance(account, Mapping)
            and isinstance(positions, list)
            and isinstance(open_orders, list)
        )
        equity = float(account["equity"])
        if equity <= 0:
            raise PaperSubmissionRefused("submission refused: account equity must be positive")
        if not 0.0 <= band < 1.0:
            raise PaperSubmissionRefused("submission refused: band must be in [0, 1)")
        current = {str(item["symbol"]): float(item["qty"]) for item in positions}
        for order in open_orders:
            symbol = str(order.get("symbol", ""))
            if symbol not in target_weights:
                continue
            quantity = float(order.get("qty", 0.0)) - float(order.get("filled_qty", 0.0))
            if quantity < 0:
                raise PaperSubmissionRefused(
                    f"submission refused: invalid open order quantity for {symbol}"
                )
            side = str(order.get("side", "")).lower()
            if side == "buy":
                current[symbol] = current.get(symbol, 0.0) + quantity
            elif side == "sell":
                current[symbol] = current.get(symbol, 0.0) - quantity
            else:
                raise PaperSubmissionRefused(
                    f"submission refused: invalid open order side for {symbol}"
                )
        quotes = self._latest_quotes(sorted(target_weights))
        orders: list[PlannedOrder] = []
        for symbol, weight in target_weights.items():
            close = float(decision_close[symbol])
            if close <= 0:
                raise PaperSubmissionRefused(
                    f"submission refused: invalid decision close for {symbol}"
                )
            bid, ask, iex_timestamp = quotes[symbol]
            mid_quote = (bid + ask) / 2.0
            live_weight = current.get(symbol, 0.0) * mid_quote / equity
            gap = float(weight) - live_weight
            # The band is the sole trade decision: move only to its nearest
            # boundary from live (positions plus outstanding-order) exposure.
            bounded_weight = (
                float(weight) - band
                if gap > band
                else float(weight) + band
                if gap < -band
                else live_weight
            )
            delta = equity * bounded_weight / mid_quote - current.get(symbol, 0.0)
            if abs(delta) >= 1e-9:
                orders.append(
                    PlannedOrder(
                        symbol,
                        "buy" if delta > 0 else "sell",
                        abs(delta),
                        abs(delta) * mid_quote,
                        decision_timestamp,
                        close,
                        iex_timestamp,
                        bid,
                        ask,
                        mid_quote,
                    )
                )
        return RebalancePlan(tuple(orders), equity)

    def submit_rebalance(
        self,
        *,
        target_weights: Mapping[str, float],
        decision_close: Mapping[str, float],
        decision_timestamp: str,
        phase3_refused: bool,
        band: float,
        max_order_notional: float = DEFAULT_MAX_ORDER_NOTIONAL,
        record_sink: Callable[[DriftRecord], None] | None = None,
    ) -> SubmissionResult:
        """Check clock before quotes, validate before POST, then persist each pending order."""
        market_open = self.market_open()
        plan = self.plan_rebalance(
            target_weights,
            decision_close=decision_close,
            decision_timestamp=decision_timestamp,
            band=band,
        )
        reasons = validate_submission(
            phase3_refused=phase3_refused,
            market_open=market_open,
            target_weights=target_weights,
            orders=plan.orders,
            max_order_notional=max_order_notional,
        )
        if reasons:
            raise PaperSubmissionRefused("submission refused: " + ", ".join(reasons))
        records: list[DriftRecord] = []
        for order in plan.orders:
            response = self._post(
                "/orders",
                {
                    "symbol": order.symbol,
                    "qty": str(order.quantity),
                    "side": order.side,
                    "type": "market",
                    "time_in_force": "day",
                },
            )
            record = DriftRecord(
                order_id=str(response["id"]),
                event="submitted",
                symbol=order.symbol,
                side=order.side,
                decision_timestamp=order.decision_timestamp,
                decision_close=order.decision_close,
                submit_timestamp=str(response.get("submitted_at") or datetime.now(UTC).isoformat()),
                feed=IEX_FEED,
                iex_timestamp=order.iex_timestamp,
                iex_bid=order.iex_bid,
                iex_ask=order.iex_ask,
                iex_spread=order.iex_ask - order.iex_bid,
                iex_mid_quote=order.iex_mid_quote,
                iex_half_spread_bps=iex_half_spread_bps(
                    bid=order.iex_bid, ask=order.iex_ask, reference_price=order.iex_mid_quote
                ),
                fill_timestamp=None,
                fill_price=None,
                fill_quantity=None,
                signed_implementation_shortfall_bps=None,
                signed_shortfall_vs_iex_mid_bps=None,
                reconciliation_reason="awaiting next-cycle reconciliation",
            )
            if record_sink is not None:
                record_sink(record)
            records.append(record)
        return SubmissionResult(tuple(records), plan.orders, plan.account_equity)

    def reconcile(self, records: Sequence[DriftRecord]) -> tuple[DriftRecord, ...]:
        """Resolve pending orders once; non-terminal responses become explicit timeouts."""
        reconciled: list[DriftRecord] = []
        for record in records:
            response = self._get(f"/orders/{record.order_id}")
            assert isinstance(response, Mapping)
            price, filled_at, quantity = (
                response.get("filled_avg_price"),
                response.get("filled_at"),
                response.get("filled_qty"),
            )
            if price is not None and filled_at is not None and quantity is not None:
                fill = float(price)
                if record.iex_mid_quote is None:
                    raise RuntimeError("pending order is missing its IEX mid-quote")
                reconciled.append(
                    replace(
                        record,
                        event="reconciled",
                        fill_timestamp=str(filled_at),
                        fill_price=fill,
                        fill_quantity=float(quantity),
                        reconciliation_reason=None,
                        signed_implementation_shortfall_bps=signed_shortfall_bps(
                            side=record.side,
                            decision_price=_required_decision_close(record),
                            fill_price=fill,
                        ),
                        signed_shortfall_vs_iex_mid_bps=signed_shortfall_bps(
                            side=record.side,
                            decision_price=float(record.iex_mid_quote),
                            fill_price=fill,
                        ),
                    )
                )
            else:
                reconciled.append(
                    replace(
                        record,
                        event="reconciliation_timeout",
                        fill_timestamp=None,
                        fill_price=None,
                        fill_quantity=None,
                        signed_implementation_shortfall_bps=None,
                        signed_shortfall_vs_iex_mid_bps=None,
                        reconciliation_reason="order not terminal before reconciliation timeout",
                    )
                )
        return tuple(reconciled)

    def reconcile_drift_log(
        self,
        path: Path,
        *,
        cycle_start: str,
        record_sink: Callable[[DriftRecord], None],
    ) -> tuple[DriftRecord, ...]:
        records = list(self.reconcile(pending_drift_records(path)))
        known_ids = logged_order_ids(path)
        orders = self._get("/orders", params={"status": "all", "after": cycle_start})
        assert isinstance(orders, list)
        for order in orders:
            order_id = str(order["id"])
            if order_id not in known_ids:
                records.append(_orphan_record(order, cycle_start))
        for record in records:
            record_sink(record)
        return tuple(records)


def _required_decision_close(record: DriftRecord) -> float:
    if record.decision_close is None:
        raise RuntimeError("pending order is missing its decision close")
    return record.decision_close


def _orphan_record(order: Mapping[str, Any], cycle_start: str) -> DriftRecord:
    """Record a broker order that survived a crash before its local log write."""
    fill_price = order.get("filled_avg_price")
    return DriftRecord(
        order_id=str(order["id"]),
        event="orphan",
        symbol=str(order.get("symbol", "unknown")),
        side=str(order.get("side", "unknown")),
        decision_timestamp=cycle_start,
        decision_close=None,
        submit_timestamp=str(order.get("submitted_at")) if order.get("submitted_at") else None,
        feed="unknown",
        iex_timestamp=None,
        iex_bid=None,
        iex_ask=None,
        iex_spread=None,
        iex_mid_quote=None,
        iex_half_spread_bps=None,
        fill_timestamp=str(order.get("filled_at")) if order.get("filled_at") else None,
        fill_price=float(fill_price) if fill_price is not None else None,
        fill_quantity=float(order["filled_qty"]) if order.get("filled_qty") else None,
        signed_implementation_shortfall_bps=None,
        signed_shortfall_vs_iex_mid_bps=None,
        reconciliation_reason="broker order missing local drift record",
    )
