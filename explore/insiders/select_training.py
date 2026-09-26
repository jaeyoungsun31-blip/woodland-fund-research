"""Materialize an explicit pre-holdout SEC/identity selection without price reads."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from holdout import TRAINING_END, TRAINING_START, require_training_events

HERE = Path(__file__).resolve().parent


def main() -> None:
    event_source = pd.read_parquet(HERE / "event_feasibility.parquet")
    transaction_source = pd.read_parquet(HERE / "sec_code_p_events.parquet")
    transaction_source["filing_date"] = pd.to_datetime(
        transaction_source.FILING_DATE, format="%d-%b-%Y", errors="raise"
    )
    events = event_source.loc[
        event_source.filing_date.between(pd.Timestamp(TRAINING_START), pd.Timestamp(TRAINING_END))
    ].copy()
    transactions = transaction_source.loc[
        transaction_source.filing_date.between(
            pd.Timestamp(TRAINING_START), pd.Timestamp(TRAINING_END)
        )
    ].copy()
    require_training_events(events.filing_date)
    require_training_events(transactions.filing_date)
    events.to_parquet(HERE / "training_events.parquet", index=False)
    transactions.to_parquet(HERE / "training_transactions.parquet", index=False)
    manifest = {
        "training_start": str(TRAINING_START),
        "training_end": str(TRAINING_END),
        "event_rows": len(events),
        "transaction_rows": len(transactions),
        "excluded_later_event_rows": len(event_source) - len(events),
        "excluded_later_transaction_rows": len(transaction_source) - len(transactions),
    }
    (HERE / "training_selection.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
