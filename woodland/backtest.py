"""Vectorized daily backtest engine.

Execution contract (DESIGN.md §6, enforced by construction):

  * `targets` is a Date x ticker frame of desired portfolio weights. A row is
    a rebalance instruction DECIDED AT THE CLOSE of that date; rows of all-NaN
    mean "no instruction — let holdings drift".
  * An instruction decided at close t is EXECUTED at close t+1 (the engine
    shifts targets by one bar). v0 executes at next close rather than next
    open — slightly more conservative timing; see journal 2026-09-01.
  * Returns accrue close-to-close on dividend-adjusted prices. The uninvested
    portion (1 - sum of weights) earns `risk_free` if one is supplied, and
    zero otherwise. Passing None reproduces the pre-2026-09-02 engine exactly,
    which is what keeps the journalled record verifiable; studies should pass
    the real series (see `woodland/cash.py`).
  * One-way costs: `cost_bps` per unit of turnover sum|w_new - w_drifted|,
    charged on the execution day.
  * v0 constraints: long-only, no leverage (weights >= 0, sum <= 1).

The engine is deliberately a transparent day loop over numpy arrays —
clarity and testability over cleverness. ~20 tickers x 7000 days runs in
well under a second.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from typing import cast

import numpy as np
import pandas as pd

_EPS = 1e-9
CostBps = float | Mapping[str, float] | pd.Series


@dataclass
class BacktestResult:
    returns: pd.Series        # daily net returns
    equity: pd.Series         # cumulative growth of $1
    holdings: pd.DataFrame    # post-trade weights at each close
    turnover: pd.Series       # one-way turnover on execution days, else 0
    cost_bps: CostBps
    liquidations: dict[str, int] | None = None

    def summary(self) -> dict:
        from woodland import metrics
        return metrics.summarize(self.returns, self.turnover)


def _run(
    prices: pd.DataFrame,
    targets: pd.DataFrame,
    cost_bps: CostBps = 5.0,
    risk_free: pd.Series | None = None,
    *, returns_input: bool = False, eligibility: pd.DataFrame | None = None,
) -> BacktestResult:
    """Run the backtest. See module docstring for the execution contract.

    prices    : Date x ticker adjusted closes (NaN before an asset exists is fine)
    targets   : Date x ticker desired weights; all-NaN rows = drift
    cost_bps  : scalar broadcast or complete ticker-labelled mapping/Series of
                nonnegative, finite one-way basis-point costs. No defaults for
                missing tickers; labels are aligned to prices.columns.
    risk_free : daily simple return earned on the uninvested portion. None
                means zero, the historical behaviour. Build one with
                `woodland.cash.align_risk_free`.
    """
    if not prices.index.is_monotonic_increasing:
        raise ValueError("prices index must be sorted ascending")
    extra = targets.index.difference(prices.index)
    if len(extra):
        raise ValueError(f"targets contain dates not in prices: {list(extra[:3])}...")
    unknown = targets.columns.difference(prices.columns)
    if len(unknown):
        raise ValueError(f"targets contain unknown tickers: {list(unknown)}")

    from woodland.snapshot import bound_frame
    prices = bound_frame(prices)
    targets = bound_frame(targets)
    if prices.empty:
        raise ValueError("no price dates at or before research as_of")

    # Align: full price grid; shift instructions one bar (decided t -> executed t+1)
    tgt = targets.reindex(index=prices.index, columns=prices.columns)
    exec_tgt = tgt.shift(1)

    px = prices.to_numpy(dtype=float)
    rets = px.copy() if returns_input else np.full_like(px, np.nan)
    if not returns_input:
        rets[1:] = px[1:] / px[:-1] - 1.0

    allowed = None
    if eligibility is not None:
        aligned = eligibility.reindex(index=prices.index, columns=prices.columns)
        if aligned.isna().any().any():
            raise ValueError("eligibility must cover the full input grid")
        allowed = aligned.to_numpy(dtype=bool)
    exec_rows = exec_tgt.notna().any(axis=1).to_numpy()
    exec_w = exec_tgt.to_numpy(dtype=float)

    if risk_free is None:
        rf = np.zeros(len(prices))
    else:
        missing = prices.index.difference(pd.DatetimeIndex(risk_free.index))
        if len(missing):
            raise ValueError(
                f"risk_free does not cover {len(missing)} price date(s), "
                f"e.g. {list(missing[:3])}"
            )
        rf = risk_free.reindex(prices.index).to_numpy(dtype=float)
        if not np.isfinite(rf).all():
            raise ValueError("risk_free contains non-finite values")
    # The first bar has no prior close, so no asset return is earned on it
    # (rets[0] is NaN); cash is held to the same convention rather than being
    # credited a day the rest of the portfolio does not get.
    rf = rf.copy()
    rf[0] = 0.0

    n_days, n_assets = px.shape
    h = np.zeros(n_assets)
    out_ret = np.zeros(n_days)
    out_turn = np.zeros(n_days)
    out_hold = np.zeros((n_days, n_assets))
    liquidation_counts = {"terminal_exit": 0, "interior_hole": 0, "unpriceable_targets": 0}
    if isinstance(cost_bps, Real):
        costs = np.full(n_assets, float(cost_bps), dtype=float)
        stored_costs: CostBps = float(cost_bps)
    elif isinstance(cost_bps, (Mapping, pd.Series)):
        labelled = pd.Series(cost_bps, dtype=float)
        if not labelled.index.is_unique or not prices.columns.is_unique:
            raise ValueError("cost_bps and price ticker labels must be unique")
        if len(prices.columns.difference(labelled.index)) or len(
            labelled.index.difference(prices.columns)
        ):
            raise ValueError("cost_bps must cover exactly the price tickers")
        labelled = labelled.reindex(prices.columns)
        costs = labelled.to_numpy(dtype=float)
        stored_costs = labelled.copy()
    else:
        raise ValueError("cost_bps must be a scalar or ticker-labelled mapping/Series")
    if not np.isfinite(costs).all() or (costs < 0).any():
        raise ValueError("cost_bps must be finite and nonnegative")
    cost_rates = costs / 1e4
    uniform_cost = bool(n_assets and np.all(cost_rates == cost_rates[0]))

    for i in range(n_days):
        r = rets[i]
        held = h > _EPS
        if np.any(held & np.isnan(r)):
            missing = held & np.isnan(r)
            invalid = missing & allowed[i] if allowed is not None else missing
            if np.any(invalid):
                bad = prices.columns[invalid].tolist()
                raise ValueError(
                    f"missing price for held asset(s) {bad} on {prices.index[i].date()}"
                )
            for j in np.flatnonzero(missing & ~invalid):
                # A later observed bar proves an interior membership hole;
                # otherwise this is the post-terminal liquidated position.
                later = bool(np.isfinite(px[i + 1 :, j]).any())
                liquidation_counts["interior_hole" if later else "terminal_exit"] += 1
            h[missing] = 0.0
        r = np.where(np.isnan(r), 0.0, r)

        # The uninvested remainder is cash. Weights are long-only and sum to
        # <= 1 by construction, so 1 - sum(h) is exactly the cash sleeve; it
        # needs no separate state because the drift below renormalises every
        # sleeve, cash included, by the same total growth.
        cash_weight = 1.0 - float(h.sum())
        gross = float(h @ r) + cash_weight * rf[i]
        growth = 1.0 + gross
        h = h * (1.0 + r) / growth if growth > _EPS else np.zeros(n_assets)

        day_ret = gross
        forced = allowed is not None and bool(np.any((h > _EPS) & ~allowed[i]))
        if exec_rows[i] or forced:
            w = np.where(np.isnan(exec_w[i]), 0.0, exec_w[i]) if exec_rows[i] else h.copy()
            if allowed is not None:
                w = np.where(allowed[i], w, 0.0)
            if (w < -_EPS).any():
                raise ValueError(f"short weight on {prices.index[i].date()}: long-only in v0")
            if w.sum() > 1.0 + 1e-6:
                raise ValueError(
                    f"weights sum {w.sum():.4f} > 1 on {prices.index[i].date()}: no leverage in v0"
                )
            unavailable_target = (w > _EPS) & np.isnan(px[i])
            if np.any(unavailable_target):
                bad = prices.columns[unavailable_target].tolist()
                raise ValueError(
                    f"target weight on missing-price asset(s) {bad} on {prices.index[i].date()}"
                )
            traded = np.abs(w - h)
            turn = float(traded.sum())
            # Dot product against actual per-symbol drifted trades. The constant
            # vector has the exact old reduction order, preserving historical
            # floating-point results as well as the published precision.
            charge = turn * float(cost_rates[0]) if uniform_cost else float(cost_rates @ traded)
            day_ret = (1.0 + day_ret) * (1.0 - charge) - 1.0
            out_turn[i] = turn
            h = w

        out_ret[i] = day_ret
        out_hold[i] = h

    idx = prices.index
    returns = pd.Series(out_ret, index=idx, name="ret")
    return BacktestResult(
        returns=returns,
        equity=(1.0 + returns).cumprod().rename("equity"),
        holdings=pd.DataFrame(out_hold, index=idx, columns=prices.columns),
        turnover=pd.Series(out_turn, index=idx, name="turnover"),
        cost_bps=stored_costs,
        liquidations=liquidation_counts,
    )


def run(
    prices: pd.DataFrame, targets: pd.DataFrame, cost_bps: CostBps = 5.0,
    risk_free: pd.Series | None = None,
) -> BacktestResult:
    """Adjusted-price input; next-close trading, bounded by research as_of."""
    return _run(prices, targets, cost_bps, risk_free)


def run_returns(
    returns: pd.DataFrame, targets: pd.DataFrame, cost_bps: CostBps = 5.0,
    risk_free: pd.Series | None = None, *, eligibility: pd.DataFrame | None = None,
) -> BacktestResult:
    """Observed-return input to the same engine, without synthesizing price bars.

    Missing returns for an existing holding refuse exactly as in the price path.
    Membership eligibility belongs in targets; NaN is never a zero-return fill.
    """
    return _run(returns, targets, cost_bps, risk_free, returns_input=True, eligibility=eligibility)


def buy_and_hold(prices: pd.DataFrame, ticker: str, cost_bps: float = 0.0,
                 risk_free: pd.Series | None = None) -> BacktestResult:
    """Baseline: 100% one ticker from its first valid close, never rebalanced."""
    first = prices[ticker].first_valid_index()
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    targets.loc[first, ticker] = 1.0
    return run(prices, targets, cost_bps=cost_bps, risk_free=risk_free)


def fixed_mix_targets(
    prices: pd.DataFrame,
    weights: dict[str, float],
    rebalance: str = "ME",
) -> pd.DataFrame:
    """Sparse target instructions for a calendar-rebalanced fixed mix."""
    valid_from = max(cast(pd.Timestamp, prices[t].first_valid_index()) for t in weights)
    index = pd.DatetimeIndex(prices.index)
    reb_days = prices.loc[valid_from:].resample(rebalance).last().index
    reb_days = index[index.searchsorted(reb_days).clip(0, len(index) - 1)]
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    first_day = index[int(index.searchsorted(valid_from))]
    for d in {first_day, *reb_days}:
        if d >= valid_from:
            for t, w in weights.items():
                targets.loc[d, t] = w
    return targets


def fixed_mix(prices: pd.DataFrame, weights: dict[str, float],
              rebalance: str = "ME", cost_bps: float = 5.0,
              risk_free: pd.Series | None = None) -> BacktestResult:
    """Baseline: constant weights (e.g. 60/40), rebalanced on a calendar rule."""
    targets = fixed_mix_targets(prices, weights, rebalance=rebalance)
    return run(prices, targets, cost_bps=cost_bps, risk_free=risk_free)
