"""Return paths reject sealed filings before touching market data."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd
import pytest
from first_returns import build_trades, load_locked_inputs


def test_return_loader_refuses_holdout_source() -> None:
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        events_path = Path(directory) / "events.parquet"
        transactions_path = Path(directory) / "transactions.parquet"
        pd.DataFrame({"filing_date": [date(2022, 7, 1)]}).to_parquet(events_path)
        pd.DataFrame({"filing_date": [date(2022, 6, 30)]}).to_parquet(transactions_path)
        with pytest.raises(ValueError, match="Sealed holdout filing"):
            load_locked_inputs(events_path, transactions_path)


def test_trade_builder_refuses_holdout_event() -> None:
    selected = pd.DataFrame({"filing_date": [date(2024, 1, 15)]})
    with pytest.raises(ValueError, match="Sealed holdout filing"):
        build_trades(selected, 60, pd.date_range("2023-01-01", "2025-01-01"))
