from __future__ import annotations

import json
import logging
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
import requests

from woodland.live.broker import PaperBroker, PaperSubmissionRefused, assert_paper_base_url
from woodland.live.cycle import _utc_rfc3339
from woodland.live.drift import (
    DriftRecord,
    append_drift_record,
    pending_drift_records,
    signed_shortfall_bps,
)


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> object:
        return self.payload


class _ForbiddenResponse(_Response):
    status_code = 403

    def raise_for_status(self) -> None:
        raise requests.HTTPError("403 Client Error: Forbidden")


class _ForbiddenSession:
    def post(self, _url: str, **_kwargs: object) -> _ForbiddenResponse:
        return _ForbiddenResponse(
            {
                "code": "40310000",
                "message": (
                    "forbidden key=deliberately-secret-key "
                    "secret=deliberately-secret-value "
                    "Authorization: Bearer independently-provided-token"
                ),
            }
        )


class _Session:
    def __init__(
        self,
        *,
        market_open: bool = True,
        terminal: bool = False,
        orphan: bool = False,
        positions: list[dict[str, str]] | None = None,
        open_orders: list[dict[str, str]] | None = None,
    ) -> None:
        self.market_open = market_open
        self.terminal = terminal
        self.orphan = orphan
        self.posts: list[dict[str, object]] = []
        self.calls: list[str] = []
        self.order_params: dict[str, str] | None = None
        self.positions = positions or []
        self.open_orders = open_orders or []

    def get(self, url: str, **kwargs: object) -> _Response:
        self.calls.append(url)
        if url.endswith("/clock"):
            return _Response({"is_open": self.market_open})
        if url.endswith("/account"):
            return _Response({"equity": "1000"})
        if url.endswith("/positions"):
            return _Response(self.positions)
        if "/orders/order-1" in url:
            if self.terminal:
                return _Response(
                    {"filled_at": "fill", "filled_avg_price": "105", "filled_qty": "1"}
                )
            return _Response({"status": "accepted"})
        if url.endswith("/orders"):
            self.order_params = dict(kwargs["params"])  # type: ignore[arg-type,index]
            if self.order_params == {"status": "open"}:
                return _Response(self.open_orders)
            if self.orphan:
                return _Response(
                    [
                        {
                            "id": "orphan-1",
                            "symbol": "SPY",
                            "side": "buy",
                            "submitted_at": "submitted",
                            "filled_at": "filled",
                            "filled_avg_price": "105",
                            "filled_qty": "2",
                        }
                    ]
                )
            return _Response([])
        if "quotes/latest" in url:
            symbols = str(dict(kwargs["params"])["symbols"]).split(",")  # type: ignore[index]
            return _Response(
                {"quotes": {symbol: {"bp": 104, "ap": 106, "t": "iex-time"} for symbol in symbols}}
            )
        raise AssertionError(url)

    def post(self, url: str, **kwargs: object) -> _Response:
        self.posts.append(dict(kwargs))
        return _Response({"id": "order-1", "submitted_at": "submit"})


def _broker(
    *,
    market_open: bool = True,
    terminal: bool = False,
    orphan: bool = False,
    positions: list[dict[str, str]] | None = None,
    open_orders: list[dict[str, str]] | None = None,
) -> tuple[PaperBroker, _Session]:
    session = _Session(
        market_open=market_open,
        terminal=terminal,
        orphan=orphan,
        positions=positions,
        open_orders=open_orders,
    )
    return PaperBroker("key", "secret", session=session), session


def _submit(broker: PaperBroker, sink: Callable[[DriftRecord], None]) -> DriftRecord:
    return broker.submit_rebalance(
        target_weights={"SPY": 0.60},
        decision_close={"SPY": 100.0},
        decision_timestamp="close-time",
        phase3_refused=False,
        band=0.05,
        record_sink=sink,
    ).records[0]


def test_live_endpoint_is_rejected() -> None:
    with pytest.raises(PaperSubmissionRefused, match="paper-api.alpaca.markets"):
        assert_paper_base_url("https://api.alpaca.markets/v2")
    with pytest.raises(PaperSubmissionRefused):
        PaperBroker("key", "secret", base_url="https://paper-api.alpaca.markets.evil/v2")


def test_broker_http_error_logs_provider_code_but_redacts_credentials(
    caplog: pytest.LogCaptureFixture,
) -> None:
    key = "deliberately-secret-key"
    secret = "deliberately-secret-value"
    broker = PaperBroker(key, secret, session=_ForbiddenSession())

    with caplog.at_level(logging.ERROR, logger="woodland.live.broker"), pytest.raises(
        requests.HTTPError
    ):
        broker._post("/orders", {"symbol": "SPY"})

    diagnostic = caplog.text
    assert "code=40310000" in diagnostic
    assert "message=" in diagnostic
    assert "[REDACTED]" in diagnostic
    assert key not in diagnostic
    assert secret not in diagnostic
    assert "independently-provided-token" not in diagnostic
    assert "APCA-API-KEY-ID" not in diagnostic
    assert "APCA-API-SECRET-KEY" not in diagnostic


@pytest.mark.parametrize(
    ("target", "phase3_refused", "market_open", "cap"),
    [
        ({"SPY": 0.60}, True, True, 10_000),
        ({"SPY": 0.60}, False, False, 10_000),
        ({"SPY": 1.01}, False, True, 10_000),
        ({"SPY": 0.60, "IEF": 0.60}, False, True, 10_000),
        ({"SPY": 0.60}, False, True, 100),
    ],
)
def test_every_submission_refusal_blocks_all_posts(
    target: dict[str, float], phase3_refused: bool, market_open: bool, cap: float
) -> None:
    broker, session = _broker(market_open=market_open)
    with pytest.raises(PaperSubmissionRefused):
        broker.submit_rebalance(
            target_weights=target,
            decision_close={symbol: 100.0 for symbol in target},
            decision_timestamp="close-time",
            phase3_refused=phase3_refused,
            band=0.05,
            max_order_notional=cap,
        )
    assert session.posts == []


def test_market_clock_is_read_before_quotes() -> None:
    broker, session = _broker()
    _submit(broker, lambda _record: None)
    assert session.calls.index("https://paper-api.alpaca.markets/v2/clock") < next(
        index for index, url in enumerate(session.calls) if "quotes/latest" in url
    )


def test_submit_then_reconcile_appends_terminal_fill_against_decision_close(tmp_path: Path) -> None:
    broker, _ = _broker(terminal=True)
    path = tmp_path / "drift.jsonl"
    submitted = _submit(broker, lambda record: append_drift_record(path, record))
    assert submitted.fill_price is None
    reconciled = broker.reconcile_drift_log(
        path,
        cycle_start="cycle-start",
        record_sink=lambda record: append_drift_record(path, record),
    )
    assert reconciled[0].event == "reconciled"
    assert reconciled[0].fill_price == 105
    assert reconciled[0].signed_implementation_shortfall_bps == pytest.approx(500)
    assert reconciled[0].signed_shortfall_vs_iex_mid_bps == pytest.approx(0)
    assert pending_drift_records(path) == ()


def test_reconciliation_timeout_appends_nulls_and_reason(tmp_path: Path) -> None:
    broker, _ = _broker(terminal=False)
    path = tmp_path / "drift.jsonl"
    _submit(broker, lambda record: append_drift_record(path, record))
    timeout = broker.reconcile_drift_log(
        path,
        cycle_start="cycle-start",
        record_sink=lambda record: append_drift_record(path, record),
    )[0]
    assert timeout.event == "reconciliation_timeout"
    assert timeout.fill_price is None
    assert timeout.signed_implementation_shortfall_bps is None
    assert "timeout" in str(timeout.reconciliation_reason)


def test_reconciliation_surfaces_broker_order_missing_from_local_log(tmp_path: Path) -> None:
    broker, session = _broker(orphan=True)
    path = tmp_path / "drift.jsonl"
    cycle_start = _utc_rfc3339(pd.Timestamp("2026-09-04T09:30:00"))
    records = broker.reconcile_drift_log(
        path,
        cycle_start=cycle_start,
        record_sink=lambda record: append_drift_record(path, record),
    )
    assert len(records) == 1
    orphan = records[0]
    assert orphan.event == "orphan"
    assert orphan.order_id == "orphan-1"
    assert orphan.decision_close is None
    assert orphan.decision_timestamp == cycle_start
    assert orphan.signed_implementation_shortfall_bps is None
    assert "missing local drift record" in str(orphan.reconciliation_reason)
    order_call = next(url for url in session.calls if url.endswith("/orders"))
    assert order_call.endswith("/orders")
    assert session.order_params == {"status": "all", "after": cycle_start}


@pytest.mark.parametrize(
    "timestamp",
    [pd.Timestamp("2026-09-04T09:30:00"), pd.Timestamp("2026-09-04T05:30:00-04:00")],
)
def test_cycle_start_is_utc_aware_rfc3339_for_alpaca_after(timestamp: pd.Timestamp) -> None:
    after = _utc_rfc3339(timestamp)
    assert after.endswith("Z") or after[-6] in {"+", "-"}
    parsed = datetime.fromisoformat(after.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None
    assert parsed.astimezone(UTC).utcoffset() == UTC.utcoffset(parsed)


def test_explicit_submit_flag_is_required_before_any_broker_setup() -> None:
    process = subprocess.run(
        [sys.executable, "scripts/run_cycle.py", "--submit-paper"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert process.returncode != 0
    assert "--submit-paper requires --execute" in process.stderr


def test_shortfall_is_sign_correct_against_decision_close_for_buys_and_sells() -> None:
    assert signed_shortfall_bps(side="buy", decision_price=100, fill_price=101) == pytest.approx(
        100
    )
    assert signed_shortfall_bps(side="sell", decision_price=100, fill_price=99) == pytest.approx(
        100
    )
    assert signed_shortfall_bps(side="buy", decision_price=100, fill_price=99) == pytest.approx(
        -100
    )
    assert signed_shortfall_bps(side="sell", decision_price=100, fill_price=101) == pytest.approx(
        -100
    )


def test_drift_records_use_iex_names_and_state_both_cost_biases(tmp_path: Path) -> None:
    source = (
        Path("woodland/live/broker.py").read_text() + Path("woodland/live/drift.py").read_text()
    ).lower()
    assert "nbbo" not in source
    path = tmp_path / "drift.jsonl"
    broker, _ = _broker()
    _submit(broker, lambda record: append_drift_record(path, record))
    payload = json.loads(path.read_text().strip())
    assert payload["feed"] == "iex"
    assert "lower bound" in payload["cost_label"]
    assert "upward" in payload["cost_label"]


def test_within_band_live_drift_submits_nothing_and_reports_zero_turnover() -> None:
    # At an IEX midpoint of 105, this is a live 58% SPY weight versus a 60% ideal.
    broker, session = _broker(positions=[{"symbol": "SPY", "qty": str(580 / 105)}])
    result = broker.submit_rebalance(
        target_weights={"SPY": 0.60},
        decision_close={"SPY": 100.0},
        decision_timestamp="close-time",
        phase3_refused=False,
        band=0.05,
    )
    assert result.records == ()
    assert result.submitted_notional == 0
    assert result.submitted_one_way_turnover == 0
    assert session.posts == []


def test_outside_band_live_drift_submits_boundary_order_and_true_turnover() -> None:
    # A 50% live SPY weight moves only to the 55% boundary, so it buys $50.
    broker, session = _broker(positions=[{"symbol": "SPY", "qty": str(500 / 105)}])
    result = broker.submit_rebalance(
        target_weights={"SPY": 0.60},
        decision_close={"SPY": 100.0},
        decision_timestamp="close-time",
        phase3_refused=False,
        band=0.05,
    )
    assert len(result.records) == 1
    assert result.records[0].side == "buy"
    assert result.submitted_notional == pytest.approx(50.0)
    assert result.submitted_one_way_turnover == pytest.approx(0.05)
    assert len(session.posts) == 1


def test_reported_turnover_equals_submitted_order_notionals_over_equity() -> None:
    broker, _ = _broker(positions=[{"symbol": "SPY", "qty": str(500 / 105)}])
    result = broker.submit_rebalance(
        target_weights={"SPY": 0.60},
        decision_close={"SPY": 100.0},
        decision_timestamp="close-time",
        phase3_refused=False,
        band=0.05,
    )
    assert result.submitted_one_way_turnover == pytest.approx(
        sum(order.notional for order in result.orders) / result.account_equity
    )


def test_unfilled_open_order_is_existing_exposure_and_prevents_duplicate() -> None:
    # Position is 50%; a pending $50 buy already reaches the same 55% boundary.
    broker, session = _broker(
        positions=[{"symbol": "SPY", "qty": str(500 / 105)}],
        open_orders=[{"symbol": "SPY", "side": "buy", "qty": str(50 / 105), "filled_qty": "0"}],
    )
    result = broker.submit_rebalance(
        target_weights={"SPY": 0.60},
        decision_close={"SPY": 100.0},
        decision_timestamp="close-time",
        phase3_refused=False,
        band=0.05,
    )
    assert result.records == ()
    assert session.posts == []
