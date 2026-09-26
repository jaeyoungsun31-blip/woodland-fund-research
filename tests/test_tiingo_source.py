"""Tiingo cross-check source (DESIGN.md §5 as amended 2026-09-01).

Built and tested against a mocked response before any live call, per the
handoff. The security property — the API key never reaches a URL — is
asserted, not assumed.
"""

import sys
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from woodland import config, data

CSV = (
    "date,close,high,low,open,volume,adjClose,adjHigh,adjLow,adjOpen,adjVolume,divCash,splitFactor\n"
    "2020-01-02,324.87,325.78,323.91,323.54,59151200,300.11,300.95,299.22,298.88,59151200,0.0,1.0\n"
    "2020-01-03,322.41,323.54,321.72,321.16,77709700,297.84,298.88,297.20,296.68,77709700,0.0,1.0\n"
    "2020-01-06,323.64,323.73,320.36,320.49,55653900,298.98,299.06,295.95,296.07,55653900,0.0,1.0\n"
)


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text, self.status_code = text, status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def captured(monkeypatch):
    """Capture the outgoing request instead of making one."""
    seen = {}

    def fake_get(url, params=None, headers=None, timeout=None):
        seen.update(url=url, params=params or {}, headers=headers or {}, timeout=timeout)
        return FakeResponse(CSV)

    monkeypatch.setattr(data.requests, "get", fake_get)
    return seen


# ---------------------------------------------------------------- security

def test_api_key_travels_in_the_header_never_in_the_url(captured):
    data.fetch_tiingo("SPY", "2020-01-01", token="SECRET-TOKEN")
    assert captured["headers"]["Authorization"] == "Token SECRET-TOKEN"
    assert "SECRET-TOKEN" not in captured["url"]
    assert not any("SECRET-TOKEN" in str(v) for v in captured["params"].values())
    assert "token" not in {k.lower() for k in captured["params"]}


def test_missing_key_fails_with_an_actionable_message(monkeypatch, tmp_path):
    monkeypatch.delenv("TIINGO_API_KEY", raising=False)
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / "absent.env")
    with pytest.raises(RuntimeError, match="TIINGO_API_KEY not set"):
        data.fetch_tiingo("SPY", "2020-01-01")


# ---------------------------------------------------------------- parsing

def test_parses_into_the_shared_schema(captured):
    df = data.fetch_tiingo("SPY", "2020-01-01", token="t")
    assert list(df.columns) == data.OHLCV
    assert df.index.name == "Date" and df.index.tz is None
    assert df.index.is_monotonic_increasing and len(df) == 3
    # adj_close comes from adjClose, close stays as-traded
    assert df.loc["2020-01-02", "adj_close"] == pytest.approx(300.11)
    assert df.loc["2020-01-02", "close"] == pytest.approx(324.87)


def test_ticker_is_lowercased_into_the_path(captured):
    data.fetch_tiingo("SPY", "2020-01-01", token="t")
    assert captured["url"].endswith("/tiingo/daily/spy/prices")
    assert captured["params"]["startDate"] == "2020-01-01"


@pytest.mark.parametrize("code,match", [(404, "no series"), (429, "rate limit")])
def test_http_failures_are_named_not_generic(monkeypatch, code, match):
    monkeypatch.setattr(data.requests, "get",
                        lambda *a, **k: FakeResponse("", code))
    with pytest.raises((ValueError, RuntimeError), match=match):
        data.fetch_tiingo("SPY", "2020-01-01", token="t")


def test_non_csv_body_is_rejected(monkeypatch):
    monkeypatch.setattr(data.requests, "get",
                        lambda *a, **k: FakeResponse("<html>nope</html>"))
    with pytest.raises(ValueError, match="no CSV"):
        data.fetch_tiingo("SPY", "2020-01-01", token="t")


def test_missing_columns_rejected(monkeypatch):
    monkeypatch.setattr(data.requests, "get",
                        lambda *a, **k: FakeResponse("date,close\n2020-01-02,1.0\n"))
    with pytest.raises(ValueError, match="missing"):
        data.fetch_tiingo("SPY", "2020-01-01", token="t")


def test_yahoo_missing_required_columns_is_rejected(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(download=lambda *args, **kwargs: pd.DataFrame({"Close": [1.0]})),
    )

    with pytest.raises(ValueError, match="missing columns"):
        data.fetch_yahoo("SPY", "2020-01-01")


# ---------------------------------------------------------------- wiring

def _yahoo_like(n=600, seed=1, drift=0.0):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-02", periods=n)
    close = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, n))
    factor = np.linspace(0.95, 1.0, n)
    return pd.DataFrame({
        "open": close, "high": close * 1.005, "low": close * 0.995,
        "close": close, "volume": np.full(n, 1e6),
        "adj_close": close * factor * (1 + drift),
    }, index=idx)


def test_ingest_crosschecks_the_adjusted_series_and_reports_ok(tmp_path, monkeypatch):
    """Two providers agreeing on the ADJUSTED series is what lifts the caveat."""
    yahoo = _yahoo_like()
    # a different adjustment epoch: same returns, every level scaled
    tiingo = yahoo.copy()
    tiingo["adj_close"] *= 0.37

    monkeypatch.setattr(data, "fetch_yahoo", lambda t, start: yahoo)
    monkeypatch.setitem(data.SOURCES, "tiingo", lambda t, start: tiingo)

    res = data.ingest_ticker("SPY", "2020-01-01", tmp_path,
                             crosscheck_source="tiingo")
    assert res.provenance["crosscheck"]["verdict"] == "ok"
    assert res.provenance["crosscheck_source"] == "tiingo"
    assert res.ok
    # levels differ hugely; the check is in return space, so that is fine
    assert res.provenance["crosscheck"]["max_abs_ret_diff"] < 1e-12


def test_a_provider_missing_a_dividend_is_caught(tmp_path, monkeypatch):
    """The failure the cross-check exists for: one feed's adjusted series
    silently skips a distribution."""
    yahoo = _yahoo_like()
    tiingo = yahoo.copy()
    tiingo.iloc[300:, tiingo.columns.get_loc("adj_close")] *= 1.03  # missed 3% payout

    monkeypatch.setattr(data, "fetch_yahoo", lambda t, start: yahoo)
    monkeypatch.setitem(data.SOURCES, "tiingo", lambda t, start: tiingo)

    res = data.ingest_ticker("SPY", "2020-01-01", tmp_path,
                             crosscheck_source="tiingo")
    assert res.provenance["crosscheck"]["verdict"] == "INVESTIGATE"
    assert not res.ok


def test_approved_missing_bar_is_backfilled_from_tiingo_with_provenance(tmp_path, monkeypatch):
    tiingo = _yahoo_like(n=600)
    tiingo.index = pd.bdate_range(end="2026-09-01", periods=len(tiingo))
    missing_date = pd.Timestamp("2026-08-28")
    assert missing_date in tiingo.index
    yahoo = tiingo.drop(index=missing_date)

    monkeypatch.setattr(data, "fetch_yahoo", lambda ticker, start: yahoo)
    monkeypatch.setitem(data.SOURCES, "tiingo", lambda ticker, start: tiingo)

    result = data.ingest_ticker("SPY", "2020-01-01", tmp_path, crosscheck_source="tiingo")

    stored = data.load_ticker("SPY", tmp_path)
    pd.testing.assert_series_equal(stored.loc[missing_date], tiingo.loc[missing_date])
    provenance = result.provenance["backfilled_bars"]
    assert provenance[0]["date"] == "2026-08-28"
    assert provenance[0]["source"] == "tiingo"
    assert provenance[0]["reason"] == "primary missing; planning-approved confirmed trading day"
    assert float(provenance[0]["adj_close_scale_to_primary"]) == pytest.approx(1.0)
    assert result.provenance["adjustment"]["verdict"] == "ok"
