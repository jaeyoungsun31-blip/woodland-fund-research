"""Run with: .venv/bin/python -m pytest -q explore/kalshi/test_holdout.py"""

import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from holdout import HoldoutError, require_exploration_game, require_exploration_games  # noqa: E402


def test_2025_game_passes_with_and_without_start():
    ticker = "KXMLBGAME-25JUN01TBHOU"
    assert require_exploration_game(ticker) == ticker
    start = datetime(2025, 6, 1, 18, 10, tzinfo=UTC)
    assert require_exploration_game(ticker, start) == ticker


@pytest.mark.parametrize(
    "ticker", ["KXMLBGAME-26JUL231507TBTOR", "KXMLBGAME-26MAR26NYYSF", "KXMLBGAME-27APR01BOSNYY"]
)
def test_holdout_tickers_are_refused(ticker):
    with pytest.raises(HoldoutError):
        require_exploration_game(ticker)


def test_start_on_or_after_2026_is_refused_even_with_2025_ticker():
    ticker = "KXMLBGAME-25DEC31ATLTOR"
    with pytest.raises(HoldoutError):
        require_exploration_game(ticker, datetime(2026, 1, 1, tzinfo=UTC))
    # 2025-12-31 20:00 in UTC-5 is 2026-01-01 01:00 UTC: sealed.
    late = datetime(2025, 12, 31, 20, 0, tzinfo=timezone(timedelta(hours=-5)))
    with pytest.raises(HoldoutError):
        require_exploration_game(ticker, late)
    ok = datetime(2025, 12, 31, 23, 59, tzinfo=UTC)
    assert require_exploration_game(ticker, ok) == ticker


def test_pre_2025_naive_and_malformed_inputs_are_refused():
    with pytest.raises(HoldoutError):
        require_exploration_game("KXMLBGAME-24SEP01NYYBOS")
    with pytest.raises(HoldoutError):
        require_exploration_game("KXMLBGAME-25JUN01TBHOU", datetime(2025, 6, 1, 18, 10))
    for bad in ("", None, "KXNBAGAME-25JUN01NYKSAS", "KXMLBGAME-XX"):
        with pytest.raises(HoldoutError):
            require_exploration_game(bad)


def test_batch_guard_raises_rather_than_filters():
    with pytest.raises(HoldoutError):
        require_exploration_games(["KXMLBGAME-25JUN01TBHOU", "KXMLBGAME-26JUL231507TBTOR"])
