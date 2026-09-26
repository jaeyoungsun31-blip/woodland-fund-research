"""Numerical fingerprint bands, and the cases that must stay unknown."""

from __future__ import annotations

import pytest

from woodland.live.resolver_numeric import (
    BAND_CASH_REL,
    BAND_EXACT_CLOSE_ABS,
    BAND_IPO_REL,
    BAND_STOCK_REL,
    check,
)


def test_signed_band_values():
    """These are the declared numbers; a silent change here changes every verdict."""
    assert (BAND_EXACT_CLOSE_ABS, BAND_CASH_REL, BAND_STOCK_REL, BAND_IPO_REL) == (
        0.02, 0.05, 0.01, 0.30)


# --------------------------------------------------------------- agreements

def test_dow_reference_row():
    """The template: cited close 66.65 observed exactly."""
    assert check("exact_close", 66.65, 66.65).outcome == "agrees"


def test_exact_close_band_is_two_cents_absolute():
    assert check("exact_close", 66.65, 66.67).outcome == "agrees"
    assert check("exact_close", 66.65, 66.68).outcome == "disagrees"


def test_cash_consideration_uses_five_percent():
    assert check("cash", 44.50, 44.44).outcome == "agrees"       # -0.13%
    assert check("cash", 44.50, 41.00).outcome == "disagrees"    # -7.9%


def test_stock_consideration_uses_one_percent():
    assert check("stock", 120.30 + 0.866 * 83.96, 193.02).outcome == "agrees"
    assert check("stock", 100.0, 102.0).outcome == "disagrees"


def test_ipo_offering_uses_thirty_percent():
    assert check("ipo_offering", 30.0, 31.02).outcome == "agrees"     # HCA, +3.4%
    assert check("ipo_offering", 30.0, 38.9).outcome == "agrees"      # +29.7%
    assert check("ipo_offering", 30.0, 39.1).outcome == "disagrees"   # +30.3%


def test_kmi_tenfold_discrepancy_is_not_accommodated():
    """The declaration refuses to widen the band for KMI. It must stay a miss."""
    result = check("ipo_offering", 30.0, 310.5)
    assert result.outcome == "disagrees"
    assert result.residual == pytest.approx(9.35)


# ------------------------------------------------------------------ unknown

def test_no_counterpart_is_unknown_not_a_miss():
    """An average valuation price does not predict a closing price."""
    result = check("stock", 59.0 + 0.2934 * 46.31, 72.77, counterpart=False)
    assert result.outcome == "unknown"
    assert result.residual is None


def test_missing_retrieved_number_is_unknown():
    assert check("ipo_offering", None, 21.4968).outcome == "unknown"


def test_missing_observation_is_unknown():
    assert check("cash", 44.50, None).outcome == "unknown"


def test_zero_prediction_has_no_relative_band():
    assert check("cash", 0.0, 1.0).outcome == "unknown"


# ------------------------------------------------------------------ shape

def test_residual_units_follow_the_band_mode():
    absolute = check("exact_close", 66.65, 66.66)
    relative = check("cash", 44.50, 44.44)
    assert absolute.residual == pytest.approx(0.01)          # dollars
    assert relative.residual == pytest.approx(-0.0013483, abs=1e-6)   # fraction
