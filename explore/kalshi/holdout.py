"""Sealed-holdout guard for the KXMLBGAME favourite exploration.

Every KXMLBGAME game with a scheduled start on or after 2026-01-01 00:00 UTC
is sealed. Exploration may use the 2025 season only. See HOLDOUT.md.
"""

import re
from datetime import UTC, datetime

HOLDOUT_START_UTC = datetime(2026, 1, 1, tzinfo=UTC)
EXPLORATION_START_UTC = datetime(2025, 1, 1, tzinfo=UTC)
_EVENT = re.compile(r"^KXMLBGAME-(\d{2})[A-Z]{3}\d{2}")


class HoldoutError(ValueError):
    """Raised when a sealed or out-of-scope game reaches the exploration."""


def require_exploration_game(event_ticker, scheduled_start_utc=None):
    """Raise unless the game is a 2025-season KXMLBGAME game.

    The ticker's year code is checked first, so a game can be refused before
    any schedule or price request is made. When the official scheduled start
    is known it must also fall in calendar 2025 (UTC). Nothing is dropped
    silently: the caller gets an exception, never a filtered list.
    """
    match = _EVENT.match(event_ticker or "")
    if not match:
        raise HoldoutError(f"not a dated KXMLBGAME event ticker: {event_ticker!r}")
    if match.group(1) != "25":
        raise HoldoutError(f"{event_ticker}: ticker year 20{match.group(1)} is not 2025")
    if scheduled_start_utc is not None:
        if scheduled_start_utc.tzinfo is None:
            raise HoldoutError(f"{event_ticker}: scheduled start must be timezone-aware")
        if scheduled_start_utc >= HOLDOUT_START_UTC:
            raise HoldoutError(f"{event_ticker}: scheduled start {scheduled_start_utc} is sealed")
        if scheduled_start_utc < EXPLORATION_START_UTC:
            raise HoldoutError(f"{event_ticker}: start {scheduled_start_utc} precedes 2025")
    return event_ticker


def require_exploration_games(event_tickers):
    """Apply the guard to every ticker; raise on the first refused game."""
    return [require_exploration_game(ticker) for ticker in event_tickers]
