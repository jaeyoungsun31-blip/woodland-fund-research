"""Time-series trend signal (strategy candidate #1, DESIGN.md §9).

STATUS: Phase 2 — implemented but NOT yet validated through the walk-forward
harness. No performance claim may be made from ad-hoc runs of this signal;
the trials ledger and promotion gate (§7-8) are the only path to a claim.

Rule (Faber-style): at each month-end close, an asset is "in trend" if its
close is above its N-month simple moving average. Risky-asset weight is
split equally across in-trend assets; everything else goes to the risk-off
leg (IEF by default). Signals at close t use only data <= t.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from woodland.signals import riskweight


def month_end_index(prices: pd.DataFrame) -> pd.DatetimeIndex:
    """Last trading day of each month present in the price index."""
    index = pd.DatetimeIndex(prices.index)
    return pd.DatetimeIndex(index.to_series().groupby(index.to_period("M")).max())


def trend_targets(
    prices: pd.DataFrame,
    risk_assets: list[str],
    risk_off: str | None = "IEF",
    lookback_months: int = 10,
    max_risk_weight: float = 1.0,
    weighting: str = "equal",
    vol_window: int = 126,
) -> pd.DataFrame:
    """Sparse target-weight frame (rows only on month-end decision dates).

    Feed to backtest.run(), which executes each row on the NEXT bar.

    `weighting` decides how the risky budget is split across the assets that
    are in trend: "equal" (v1-v4), "inverse_vol", or "min_variance" on a
    Ledoit-Wolf shrunk covariance. The risk estimate uses the trailing
    `vol_window` bars of returns THROUGH the decision date and no later, which
    `tests/test_no_lookahead.py` checks by perturbation.

    vol_window must not exceed the harness embargo (210 bars under the frozen
    scheme) or a decision would reach into its own training window.
    """
    if weighting != "equal" and vol_window < riskweight.MIN_WEIGHT_OBS:
        raise ValueError(
            f"vol_window must be >= {riskweight.MIN_WEIGHT_OBS} for {weighting!r}")
    required = [*risk_assets] if risk_off is None else [*risk_assets, risk_off]
    missing = [t for t in required if t not in prices.columns]
    if missing:
        raise ValueError(f"tickers not in price matrix: {missing}")

    monthly_close = prices.resample("ME").last()
    sma = monthly_close.rolling(lookback_months).mean()
    in_trend = monthly_close > sma  # uses data <= t only: rolling is backward-looking

    decision_days = month_end_index(prices)
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)

    for day in decision_days:
        month = day.to_period("M").to_timestamp("M")
        if month not in in_trend.index:
            continue
        row = in_trend.loc[month, risk_assets]
        if row.isna().any() and not row.fillna(False).any():
            # warm-up: not enough history for any asset yet
            continue
        live = [t for t in risk_assets if bool(row.get(t)) and pd.notna(prices.at[day, t])]
        w = pd.Series(0.0, index=prices.columns)
        if live:
            if weighting == "equal":
                w[live] = max_risk_weight / len(live)
            else:
                # Returns through the decision date only — never past `day`.
                history = prices.loc[:day, live].pct_change().dropna().tail(vol_window)
                if len(history) < riskweight.MIN_WEIGHT_OBS:
                    continue          # warm-up, same convention as the trend filter
                w[live] = max_risk_weight * riskweight.risk_weights(
                    history.to_numpy(dtype=float), weighting)
        # Everything not in risky assets goes to the risk-off leg (or stays in
        # cash if that asset isn't trading yet). `risk_off=None` means the
        # residual IS cash: it is left unallocated and the engine credits it
        # the risk-free rate. That is also the cheaper treatment — an explicit
        # cash column would make going to cash look like two trades and be
        # charged twice.
        if risk_off is not None and pd.notna(prices.at[day, risk_off]):
            w[risk_off] = w[risk_off] + (1.0 - float(w.sum()))
        targets.loc[day] = w
    return targets


def ensemble_targets(
    prices: pd.DataFrame,
    risk_assets: list[str],
    lookback_months: list[int],
    risk_off: str | None = "IEF",
    max_risk_weight: float = 1.0,
    weighting: str = "equal",
    vol_window: int = 126,
) -> pd.DataFrame:
    """Average complete target vectors from several fixed trend lookbacks.

    A row is emitted only after every constituent has a valid instruction, so
    the warm-up period cannot silently use a smaller, changing ensemble.
    """
    if not lookback_months:
        raise ValueError("ensemble requires at least one lookback")
    constituents = [
        trend_targets(
            prices,
            risk_assets=risk_assets,
            risk_off=risk_off,
            lookback_months=lookback,
            max_risk_weight=max_risk_weight,
            weighting=weighting,
            vol_window=vol_window,
        )
        for lookback in lookback_months
    ]
    complete = pd.concat(
        [targets.notna().any(axis=1).rename(i) for i, targets in enumerate(constituents)],
        axis=1,
    ).all(axis=1)
    ensemble = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    if complete.any():
        total = constituents[0].loc[complete].copy()
        for targets in constituents[1:]:
            total = total.add(targets.loc[complete])
        ensemble.loc[complete] = total / len(constituents)
    return ensemble
