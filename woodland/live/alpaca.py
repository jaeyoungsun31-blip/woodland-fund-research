"""Read-only Alpaca Paper account snapshots; this module cannot submit orders."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from woodland.config import get_secret

PAPER_URL = "https://paper-api.alpaca.markets/v2"
DATA_URL = "https://data.alpaca.markets/v2"


class PaperClient:
    """Narrow, read-only Paper API client. No POST/PUT/DELETE methods exist."""

    def __init__(self, key: str, secret: str, session: Any = requests):
        self._headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
        self._session = session

    @classmethod
    def from_environment(cls) -> PaperClient:
        key = get_secret("ALPACA_API_KEY")
        secret = get_secret("ALPACA_API_SECRET")
        if not key or not secret:
            raise RuntimeError("Missing ALPACA_API_KEY or ALPACA_API_SECRET")
        return cls(key, secret)

    def _get(self, url: str, **kwargs: Any) -> Any:
        response = self._session.get(url, headers=self._headers, timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()

    def snapshot(self, symbols: list[str]) -> dict[str, Any]:
        """Return account, holdings, recent order status, and IEX decision quotes."""
        quotes = (
            self._get(
                f"{DATA_URL}/stocks/quotes/latest",
                params={"symbols": ",".join(symbols), "feed": "iex"},
            )
            if symbols
            else {"quotes": {}}
        )
        return {
            "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "mode": "paper-read-only",
            "feed": "iex",
            "account": self._get(f"{PAPER_URL}/account"),
            "positions": self._get(f"{PAPER_URL}/positions"),
            "orders": self._get(f"{PAPER_URL}/orders", params={"status": "all", "limit": 100}),
            "quotes": quotes.get("quotes", {}),
        }


def write_snapshot(snapshot: dict[str, Any], directory: Path) -> Path:
    """Write an immutable, timestamped JSON snapshot; collision-safe by construction."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"paper-snapshot-{stamp}.json"
    counter = 1
    while path.exists():
        path = directory / f"paper-snapshot-{stamp}-{counter}.json"
        counter += 1
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")
    return path
