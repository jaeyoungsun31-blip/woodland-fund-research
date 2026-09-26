"""Offline EODHD raw-price/factor reconciliation under the locked rules."""

from __future__ import annotations

import numpy as np
import pandas as pd


def classify_symbol(frame: pd.DataFrame) -> pd.DataFrame:
    """Classify every daily raw bar without using adjusted-close *returns*."""
    required = {"open", "close", "adjusted_close", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError("Missing EODHD raw/factor fields")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Price dates must be unique and ordered")
    result = frame.copy()
    close = result.close.to_numpy(float)
    adjusted = result.adjusted_close.to_numpy(float)
    volume = result.volume.to_numpy(float)
    raw = np.full(len(result), np.nan)
    factor = np.full(len(result), np.nan)
    step = np.full(len(result), np.nan)
    valid_level = np.isfinite(close) & np.isfinite(adjusted) & (close > 0) & (adjusted > 0)
    factor[valid_level] = adjusted[valid_level] / close[valid_level]
    raw[1:] = (
        np.divide(close[1:], close[:-1], out=np.full(len(result) - 1, np.nan), where=close[:-1] > 0)
        - 1
    )
    step[1:] = np.divide(
        factor[1:], factor[:-1], out=np.full(len(result) - 1, np.nan), where=factor[:-1] > 0
    )
    valid = (
        np.isfinite(raw)
        & np.isfinite(step)
        & np.isfinite(volume)
        & valid_level
        & np.roll(valid_level, 1)
    )
    valid[0] = False
    labels = np.full(len(result), "ordinary_raw", dtype=object)
    labels[0] = "no_prior"
    labels[~valid & (np.arange(len(result)) > 0)] = "unusable"
    total = raw.copy()
    match = np.zeros(len(result), dtype=bool)
    match[valid] = np.abs((1 + raw[valid]) * step[valid] - 1) <= 0.02
    split = valid & (np.abs(raw) > 0.25) & match
    labels[split] = "split"
    total[split] = (1 + raw[split]) * step[split] - 1
    dividend = (
        valid
        & ~split
        & (np.abs(step - 1) >= 0.001)
        & (np.abs(step - 1) <= 0.10)
        & (np.abs(raw) < 0.25)
    )
    labels[dividend] = "dividend"
    total[dividend] = raw[dividend] + (1 + raw[dividend]) * (step[dividend] - 1)
    adjustment_error = valid & ~split & ~dividend & (np.abs(step - 1) > 0.25) & (np.abs(raw) < 0.05)
    labels[adjustment_error] = "adjustment_error"
    suspected = valid & ~split & ~dividend & ~adjustment_error & (np.abs(raw) > 0.75)
    labels[suspected] = "suspected_defect"
    defect = np.zeros(len(result), dtype=bool)
    for i in np.flatnonzero(suspected):
        if volume[i] == 0:
            defect[i] = True
            continue
        before, current = close[i - 1], close[i]
        future = close[i + 1 : i + 6]
        midpoint = current - 0.5 * (current - before)
        if (current > before and np.any(future <= midpoint)) or (
            current < before and np.any(future >= midpoint)
        ):
            defect[i] = True
    labels[defect] = "defect"
    total[~valid] = np.nan
    result["adjustment_factor"] = factor
    result["factor_step"] = step
    result["raw_return"] = raw
    result["total_return"] = total
    result["classification"] = labels
    result["defect"] = defect
    return result


def event_marks(
    classified: pd.DataFrame, entry: pd.Timestamp, exit_date: pd.Timestamp
) -> tuple[np.ndarray, np.ndarray]:
    """Synthetic total-return marks from a raw-open entry, without adjusted closes."""
    path = classified.loc[entry:exit_date]
    if path.empty or path.index[0] != entry or path.index[-1] != exit_date:
        raise ValueError("Missing entry or exit raw bar")
    if path.defect.any() or path.classification.eq("unusable").any():
        raise ValueError("Unusable or defect-affected event path")
    raw_open = path.open.to_numpy(float)
    raw_close = path.close.to_numpy(float)
    total = path.total_return.to_numpy(float)
    classes = path.classification.to_numpy(str)
    steps = path.factor_step.to_numpy(float)
    if not (np.isfinite(raw_open).all() and np.isfinite(raw_close).all()):
        raise ValueError("Invalid raw open or close")
    opens = np.empty(len(path))
    closes = np.empty(len(path))
    opens[0] = raw_open[0]
    closes[0] = raw_close[0]
    for i in range(1, len(path)):
        applied_step = steps[i] if classes[i] in ("split", "dividend") else 1.0
        opens[i] = closes[i - 1] * raw_open[i] / raw_close[i - 1] * applied_step
        closes[i] = closes[i - 1] * (1 + total[i])
    return opens, closes
