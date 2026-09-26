"""Numerical fingerprint checks and their signed tolerance bands.

Implements the band table in `2026-09-06-phase3-date-admissibility-implementation.md`:

    exact cited close        $0.02 absolute
    fixed cash consideration 5% relative      (A2 Case 1)
    stock consideration      1% relative      (settlement/market differences)
    IPO offering price       +/-30% relative  (ordinary first-day movement)

Three rules the bands do not bend for, all of them load-bearing:

**Raw close only.** Never adjusted close, never an assumed rescaling. The
adjusted series is a vendor construction; a fingerprint computed on it would be
testing the vendor's arithmetic rather than the security's identity.

**A retrieved number with no applicable observed counterpart stays unknown.** It
is not a pass and not a failure. An average valuation price is not a prediction
of a closing price and has no counterpart at all.

**No band widens to accommodate an observation.** A check that misses is
reported as a miss, with the residual stated, and the proposal returns to
`unknown` pending a number that fits or an explanation of the one that did not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BAND_EXACT_CLOSE_ABS = 0.02   # USD, rounding error on an independently cited close
BAND_CASH_REL = 0.05          # A2 Case 1 band on all-cash consideration
BAND_STOCK_REL = 0.01         # stock consideration from a cited same-event close
BAND_IPO_REL = 0.30           # offering price against first close

CheckKind = Literal["exact_close", "cash", "stock", "ipo_offering"]
Outcome = Literal["agrees", "disagrees", "unknown"]

BANDS: dict[CheckKind, tuple[str, float, str]] = {
    "exact_close": ("absolute", BAND_EXACT_CLOSE_ABS, "$0.02 rounding on a cited exact close"),
    "cash": ("relative", BAND_CASH_REL, "5% on fixed cash consideration"),
    "stock": ("relative", BAND_STOCK_REL,
              "1% on stock consideration from a cited same-event acquirer close"),
    "ipo_offering": ("relative", BAND_IPO_REL,
                     "+/-30% on IPO offering price against first close"),
}


@dataclass(frozen=True)
class NumericCheck:
    """One fingerprint: what was predicted, what was observed, and whether it fits."""

    kind: CheckKind
    predicted: float | None
    observed: float | None
    outcome: Outcome
    residual: float | None          # observed - predicted, in the band's own units
    band: float
    band_mode: str
    reason: str

    @property
    def within_band(self) -> bool:
        return self.outcome == "agrees"


def check(
    kind: CheckKind,
    predicted: float | None,
    observed: float | None,
    *,
    counterpart: bool = True,
    note: str = "",
) -> NumericCheck:
    """Compare a retrieved number against a raw-close observation.

    `counterpart=False` declares that the retrieved number has no applicable
    observed counterpart — an average valuation price against a closing price,
    say. That is `unknown` by rule, and is never scored against a band.
    """
    mode, band, label = BANDS[kind]
    if not counterpart:
        return NumericCheck(kind, predicted, observed, "unknown", None, band, mode,
                            note or "retrieved number has no applicable observed counterpart")
    if predicted is None or observed is None:
        missing = "no number retrieved" if predicted is None else "no observation"
        return NumericCheck(kind, predicted, observed, "unknown", None, band, mode,
                            note or f"{missing}; check not performed")
    if mode == "absolute":
        residual = observed - predicted
        fits = abs(residual) <= band
        detail = f"|{residual:+.4f}| vs {label}"
    else:
        if predicted == 0:
            return NumericCheck(kind, predicted, observed, "unknown", None, band, mode,
                                "cited value is zero; no relative band is defined")
        residual = observed / predicted - 1.0
        fits = abs(residual) <= band
        detail = f"{residual:+.4%} vs {label}"
    return NumericCheck(kind, predicted, observed, "agrees" if fits else "disagrees",
                        residual, band, mode, (note + " " if note else "") + detail)
