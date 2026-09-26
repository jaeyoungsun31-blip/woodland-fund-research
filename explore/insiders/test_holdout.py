"""The sealed filing-date boundary must fail closed."""

from datetime import date

import pytest
from holdout import require_training_events


def test_training_boundary_accepts_last_training_day() -> None:
    require_training_events([date(2012, 1, 1), date(2022, 6, 30)])


@pytest.mark.parametrize("filing", [date(2022, 7, 1), date(2024, 1, 15), date(2026, 6, 30)])
def test_holdout_event_is_refused(filing: date) -> None:
    with pytest.raises(ValueError, match="Sealed holdout filing"):
        require_training_events([date(2022, 6, 30), filing])


def test_missing_and_post_holdout_dates_are_refused() -> None:
    with pytest.raises(ValueError, match="Invalid or missing"):
        require_training_events([None])
    with pytest.raises(ValueError, match="outside locked training"):
        require_training_events([date(2026, 7, 1)])
