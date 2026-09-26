#!/usr/bin/env python3
"""Measure the four precommitted source-to-target excess-return lag pairs."""

from __future__ import annotations

from math import sqrt
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STOCK_STORE = ROOT / "data" / "Woodland-EODHD"
XLK_PATH = ROOT / "data" / "XLK.parquet"
MACRO_DATES_PATH = ROOT / "explore" / "pooled-macro-dates.csv"

START = pd.Timestamp("2010-01-01")
END = pd.Timestamp("2026-06-30")
PAIRS = (
    ("TSM", "AMD", "+"),
    ("TSM", "NVDA", "+"),
    ("AAPL", "TSM", "+"),
    ("INTC", "AMD", "-"),
)
TRAILING_DAYS = 60
EVENT_THRESHOLD = 2.0
EVENT_SPACING = 5
FORWARD_DAYS = 5
N_BOOTSTRAP = 10_000
SEED = 0
ALPHA = 0.05
POWER = 0.80


def _checked_prices(path: Path, date_column: str, price_column: str) -> pd.Series:
    frame = pd.read_parquet(path, columns=[date_column, price_column])
    if date_column in frame.columns:
        index = pd.DatetimeIndex(pd.to_datetime(frame.pop(date_column)), name="date")
    else:
        index = pd.DatetimeIndex(frame.index, name="date")
    prices = pd.Series(frame[price_column].to_numpy(float), index=index, name=path.stem)
    prices = prices.sort_index()
    if prices.index.has_duplicates:
        raise ValueError(f"duplicate dates in {path}")
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0.0).any():
        raise ValueError(f"non-finite or nonpositive adjusted prices in {path}")
    return prices.loc[:END]


def load_stock(symbol: str) -> pd.Series:
    return _checked_prices(
        STOCK_STORE / f"{symbol}.US.parquet", "date", "adjusted_close"
    ).rename(symbol)


def load_xlk() -> pd.Series:
    frame = pd.read_parquet(XLK_PATH, columns=["adj_close"])
    prices = pd.Series(
        frame["adj_close"].to_numpy(float),
        index=pd.DatetimeIndex(frame.index, name="date"),
        name="XLK",
    ).sort_index()
    if prices.index.has_duplicates:
        raise ValueError(f"duplicate dates in {XLK_PATH}")
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0.0).any():
        raise ValueError(f"non-finite or nonpositive adjusted prices in {XLK_PATH}")
    return prices.loc[:END]


def excess_returns(symbol: str, xlk: pd.Series) -> pd.DataFrame:
    prices = pd.concat([load_stock(symbol), xlk], axis=1, join="inner").dropna()
    returns = prices.pct_change(fill_method=None).dropna()
    returns.columns = ["stock_return", "xlk_return"]
    returns["excess"] = returns.stock_return - returns.xlk_return
    return returns


def source_events(source: pd.DataFrame, macro_dates: set[pd.Timestamp]) -> pd.DatetimeIndex:
    prior_volatility = (
        source.excess.rolling(TRAILING_DAYS, min_periods=TRAILING_DAYS)
        .std(ddof=1)
        .shift(1)
    )
    standardized = source.excess / prior_volatility
    candidates = standardized.index[
        standardized.abs().gt(EVENT_THRESHOLD)
        & standardized.index.to_series().between(START, END).to_numpy()
        & ~standardized.index.isin(macro_dates)
    ]

    positions = source.index.get_indexer(candidates)
    kept: list[pd.Timestamp] = []
    last_position = -EVENT_SPACING
    for date, position in zip(candidates, positions, strict=True):
        if position - last_position >= EVENT_SPACING:
            kept.append(date)
            last_position = int(position)
    return pd.DatetimeIndex(kept, name="date")


def pair_observations(
    source: pd.DataFrame,
    target: pd.DataFrame,
    events: pd.DatetimeIndex,
) -> pd.DataFrame:
    rows: list[dict[str, float | pd.Timestamp]] = []
    for date in events:
        if date not in source.index or date not in target.index:
            continue
        position = int(target.index.get_loc(date))
        if position + FORWARD_DAYS >= len(target):
            continue
        forward = target.iloc[position + 1 : position + FORWARD_DAYS + 1]
        if forward.index[-1] > END:
            continue
        cumulative_excess = (1.0 + forward.stock_return).prod() - (
            1.0 + forward.xlk_return
        ).prod()
        rows.append(
            {
                "date": date,
                "source_excess": float(source.at[date, "excess"]),
                "target_same_day_excess": float(target.at[date, "excess"]),
                "target_forward_excess": float(cumulative_excess),
            }
        )
    if not rows:
        raise ValueError("pair has no complete event observations")
    return pd.DataFrame(rows).set_index("date")


def _correlation(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.corrcoef(left, right)[0, 1])


def bootstrap_interval(observations: pd.DataFrame) -> tuple[float, float]:
    left = observations.source_excess.to_numpy(float)
    right = observations.target_forward_excess.to_numpy(float)
    rng = np.random.default_rng(SEED)
    draws = np.empty(N_BOOTSTRAP)
    batch_size = 1_000
    for start in range(0, N_BOOTSTRAP, batch_size):
        stop = min(start + batch_size, N_BOOTSTRAP)
        indices = rng.integers(0, len(observations), size=(stop - start, len(observations)))
        sampled_left = left[indices]
        sampled_right = right[indices]
        left_centered = sampled_left - sampled_left.mean(axis=1, keepdims=True)
        right_centered = sampled_right - sampled_right.mean(axis=1, keepdims=True)
        denominator = np.sqrt(
            np.sum(left_centered**2, axis=1)
            * np.sum(right_centered**2, axis=1)
        )
        draws[start:stop] = np.sum(left_centered * right_centered, axis=1) / denominator
    return (
        float(np.nanquantile(draws, ALPHA / 2.0)),
        float(np.nanquantile(draws, 1.0 - ALPHA / 2.0)),
    )


def minimum_detectable_correlation(n_events: int) -> float:
    if n_events <= 3:
        return float("nan")
    normal = NormalDist()
    fisher_effect = (
        normal.inv_cdf(1.0 - ALPHA / 2.0) + normal.inv_cdf(POWER)
    ) / sqrt(n_events - 3.0)
    return float(np.tanh(fisher_effect))


def run() -> pd.DataFrame:
    macro_dates = set(
        pd.to_datetime(pd.read_csv(MACRO_DATES_PATH, usecols=["date"]).date)
    )
    xlk = load_xlk()
    symbols = sorted({symbol for pair in PAIRS for symbol in pair[:2]})
    returns = {symbol: excess_returns(symbol, xlk) for symbol in symbols}
    events = {
        source: source_events(returns[source], macro_dates)
        for source in {source for source, _, _ in PAIRS}
    }

    rows: list[dict[str, float | int | str]] = []
    for source, target, expected_sign in PAIRS:
        observations = pair_observations(
            returns[source], returns[target], events[source]
        )
        source_values = observations.source_excess.to_numpy(float)
        ci_low, ci_high = bootstrap_interval(observations)
        rows.append(
            {
                "source": source,
                "target": target,
                "expected_sign": expected_sign,
                "event_count": len(observations),
                "same_day_correlation": _correlation(
                    source_values,
                    observations.target_same_day_excess.to_numpy(float),
                ),
                "lag_correlation": _correlation(
                    source_values,
                    observations.target_forward_excess.to_numpy(float),
                ),
                "lag_ci_low": ci_low,
                "lag_ci_high": ci_high,
                "minimum_detectable_correlation_80pct": minimum_detectable_correlation(
                    len(observations)
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    print(run().to_string(index=False, float_format=lambda value: f"{value:.6f}"))


if __name__ == "__main__":
    main()
