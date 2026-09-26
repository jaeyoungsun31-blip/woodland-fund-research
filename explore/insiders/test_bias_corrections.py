from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from bias_corrections import hac_fit, read_french_archive
from first_returns import Trade, simulate
from holdout import require_training_events


def test_terminal_haircut_applies_to_last_close() -> None:
    calendar = pd.date_range("2021-01-04", periods=2, freq="B")
    trade = Trade(
        issuer_cik="1",
        ticker="TEST",
        filing_date=pd.Timestamp("2021-01-01"),
        bucket="under_300k",
        entry_idx=0,
        exit_idx=1,
        spread=0,
        opens=np.array([1.0, 1.0]),
        closes=np.array([1.0, 1.0]),
        delisting_return=-0.3,
    )
    monthly = simulate([trade], calendar, pd.Series([1.0, 1.0], index=calendar))
    assert monthly.gross.iloc[0] == pytest.approx(-0.3)
    assert monthly.net.iloc[0] == pytest.approx(0.7 * (1 - 0.0005) ** 2 - 1)


def test_new_return_entry_point_rejects_holdout() -> None:
    with pytest.raises(ValueError, match="holdout|training"):
        require_training_events(pd.Series([pd.Timestamp("2022-07-01")]))


def test_hac_fit_constant_series_has_no_spurious_alpha() -> None:
    market = np.linspace(-0.05, 0.05, 48)
    fit = hac_fit(0.7 * market, market[:, None])
    assert fit["coefficient"][0] == pytest.approx(0, abs=1e-12)
    assert fit["coefficient"][1] == pytest.approx(0.7)


def test_official_monthly_archive_has_expected_columns() -> None:
    from bias_corrections import HERE

    path = HERE / "F-F_Research_Data_5_Factors_2x3_CSV.zip"
    if not path.exists():
        pytest.skip(
            f"{path.name} is gitignored and absent (fresh clone); "
            "download it from the Ken French data library (URL and sha256 in "
            "french_archives_manifest.json) to run this check"
        )
    frame = read_french_archive(path, 6)
    assert list(frame.columns) == ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
    assert frame.index.is_unique
    assert frame.loc["2012-01-31", "RF"] < 0.01
