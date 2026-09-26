from __future__ import annotations

import pandas as pd
import pytest
import run_offline_rebuild


def test_offline_classification_rejects_holdout_before_creating_cache(
    tmp_path, monkeypatch
) -> None:
    target = tmp_path / "offline_series"
    monkeypatch.setattr(run_offline_rebuild, "SERIES", target)
    events = pd.DataFrame({"filing_date": [pd.Timestamp("2022-07-01")], "ticker": ["TEST"]})
    with pytest.raises(ValueError, match="holdout|training"):
        run_offline_rebuild.classify_training_symbols(events)
    assert not target.exists()
