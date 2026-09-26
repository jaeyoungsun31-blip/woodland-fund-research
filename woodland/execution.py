"""Execution overlays for sparse target-weight instructions.

The signal remains a frame of decisions made at close ``t``.  This module
changes only how those already-made decisions are implemented: buffering,
partial adjustment, delayed fills, calendar tranches, and deterministic
missed rebalances.  The default policy is exactly ``backtest.run``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from woodland.backtest import BacktestResult

_EPS = 1e-9
TRANCHE_OFFSETS = (0, 5, 10, 15)


@dataclass(frozen=True)
class ExecutionPolicy:
    """Fixed mechanics applied to an existing target stream."""

    band: float = 0.0
    adjustment: float = 1.0
    tranches: int = 1
    delay: int = 0
    missed_rebalance: float = 0.0
    seed: int = 1202

    def __post_init__(self) -> None:
        if not 0.0 <= self.band <= 1.0:
            raise ValueError("band must be between 0 and 1")
        if not 0.0 < self.adjustment <= 1.0:
            raise ValueError("adjustment must be in (0, 1]")
        if self.tranches not in (1, 4):
            raise ValueError("tranches must be 1 or 4")
        if self.delay not in (0, 1, 2):
            raise ValueError("delay must be 0, 1, or 2 additional bars")
        if not 0.0 <= self.missed_rebalance < 1.0:
            raise ValueError("missed_rebalance must be in [0, 1)")


@dataclass(frozen=True)
class MissedRebalanceSummary:
    decisions: int
    missed: int

    @property
    def realized_fraction(self) -> float:
        return self.missed / self.decisions if self.decisions else 0.0


def decision_mask(
    targets: pd.DataFrame,
    probability: float,
    *,
    seed: int = 1202,
) -> pd.Series:
    """Return a reproducible mask over decision rows.

    The same uniforms and seed are used for every policy, so masks are common
    (and nested by probability) across otherwise unrelated grid settings.
    """
    if not 0.0 <= probability < 1.0:
        raise ValueError("probability must be in [0, 1)")
    decisions = targets.notna().any(axis=1)
    out = pd.Series(False, index=targets.index, dtype=bool)
    n = int(decisions.sum())
    if n and probability:
        uniforms = np.random.Generator(np.random.PCG64(seed)).random(n)
        out.loc[decisions] = uniforms < probability
    return out


def missed_rebalance_summary(
    targets: pd.DataFrame,
    probability: float,
    *,
    seed: int = 1202,
) -> MissedRebalanceSummary:
    mask = decision_mask(targets, probability, seed=seed)
    return MissedRebalanceSummary(
        decisions=int(targets.notna().any(axis=1).sum()),
        missed=int(mask.sum()),
    )


def cost_crossover(costs: list[float], sharpe_differences: list[float]) -> float | None:
    """Piecewise-linear first cost where a variant's Sharpe difference is > 0.

    ``None`` means no positive difference was observed through the final cost.
    An exactly identical reference curve therefore returns ``None`` and should
    be labelled as the reference by its caller.
    """
    if len(costs) != len(sharpe_differences) or not costs:
        raise ValueError("costs and differences must be non-empty and equal length")
    if any(right <= left for left, right in zip(costs, costs[1:], strict=False)):
        raise ValueError("costs must be strictly increasing")
    if sharpe_differences[0] > 0.0:
        return float(costs[0])
    for left, right, d_left, d_right in zip(
        costs, costs[1:], sharpe_differences, sharpe_differences[1:], strict=False
    ):
        if d_right > 0.0 and d_left <= 0.0:
            if d_right == d_left:
                return float(right)
            fraction = -d_left / (d_right - d_left)
            return float(left + fraction * (right - left))
    return None


def net_sharpe_at_turnover(
    gross_returns: pd.Series,
    annual_turnover: float,
    cost_bps: float,
) -> float:
    """Sharpe after a fixed linear daily drag for a turnover/cost pair."""
    if annual_turnover < 0.0:
        raise ValueError("annual_turnover must be non-negative")
    if cost_bps < 0.0:
        raise ValueError("cost_bps must be non-negative")
    values = gross_returns.dropna().to_numpy(dtype=float)
    if len(values) < 2:
        raise ValueError("gross_returns must contain at least two observations")
    standard_deviation = float(values.std(ddof=1))
    if standard_deviation <= 0.0:
        raise ValueError("gross_returns must have positive volatility")
    daily_drag = annual_turnover * cost_bps / 1e4 / 252.0
    return float((values.mean() - daily_drag) / standard_deviation * np.sqrt(252))


def maximum_viable_turnover(
    gross_returns: pd.Series,
    benchmark_net_returns: pd.Series,
    cost_bps: float,
) -> float | None:
    """Annual turnover where net Sharpe first equals a benchmark's Sharpe.

    ``None`` means the gross strategy already trails the benchmark at zero
    turnover, so no non-negative turnover is viable under the fixed model.
    """
    if cost_bps <= 0.0:
        raise ValueError("cost_bps must be positive for a finite frontier")
    aligned = pd.DataFrame(
        {"strategy": gross_returns, "benchmark": benchmark_net_returns}
    ).dropna()
    if len(aligned) < 2:
        raise ValueError("need at least two aligned observations")
    strategy = aligned["strategy"].to_numpy(dtype=float)
    benchmark = aligned["benchmark"].to_numpy(dtype=float)
    strategy_volatility = float(strategy.std(ddof=1))
    benchmark_volatility = float(benchmark.std(ddof=1))
    if strategy_volatility <= 0.0 or benchmark_volatility <= 0.0:
        raise ValueError("strategy and benchmark must have positive volatility")
    benchmark_sharpe = (
        float(benchmark.mean()) / benchmark_volatility * np.sqrt(252)
    )
    break_even_daily_drag = float(strategy.mean()) - (
        benchmark_sharpe * strategy_volatility / np.sqrt(252)
    )
    if break_even_daily_drag <= 0.0:
        return None
    return float(break_even_daily_drag * 252.0 * 1e4 / cost_bps)


def run(
    prices: pd.DataFrame,
    targets: pd.DataFrame,
    policy: ExecutionPolicy,
    *,
    cost_bps: float = 5.0,
    risk_free: pd.Series | None = None,
    missed_mask: pd.Series | None = None,
) -> BacktestResult:
    """Run target instructions through a fixed execution policy."""
    from woodland.snapshot import bound_frame
    prices = bound_frame(prices)
    targets = bound_frame(targets)
    if prices.empty:
        raise ValueError("no price dates at or before research as_of")
    _validate_inputs(prices, targets, risk_free)
    offsets = (0,) if policy.tranches == 1 else TRANCHE_OFFSETS
    if missed_mask is None:
        resolved_mask = decision_mask(
            targets, policy.missed_rebalance, seed=policy.seed
        )
    else:
        missing_dates = prices.index.difference(missed_mask.index)
        if len(missing_dates):
            raise ValueError(
                f"missed_mask does not cover {len(missing_dates)} price date(s)"
            )
        resolved_mask = missed_mask.reindex(prices.index).astype(bool)
    missed = resolved_mask.to_numpy(dtype=bool)
    books = [
        _run_book(
            prices,
            targets,
            policy,
            offset=offset,
            missed=missed,
            cost_bps=cost_bps,
            risk_free=risk_free,
        )
        for offset in offsets
    ]
    return _aggregate_books(books, cost_bps=cost_bps)


def _validate_inputs(
    prices: pd.DataFrame,
    targets: pd.DataFrame,
    risk_free: pd.Series | None,
) -> None:
    if not prices.index.is_monotonic_increasing:
        raise ValueError("prices index must be sorted ascending")
    extra = targets.index.difference(prices.index)
    if len(extra):
        raise ValueError(f"targets contain dates not in prices: {list(extra[:3])}...")
    unknown = targets.columns.difference(prices.columns)
    if len(unknown):
        raise ValueError(f"targets contain unknown tickers: {list(unknown)}")
    if risk_free is not None:
        missing = prices.index.difference(pd.DatetimeIndex(risk_free.index))
        if len(missing):
            raise ValueError(f"risk_free does not cover {len(missing)} price date(s)")
        aligned = risk_free.reindex(prices.index).to_numpy(dtype=float)
        if not np.isfinite(aligned).all():
            raise ValueError("risk_free contains non-finite values")


def _scheduled_targets(
    prices: pd.DataFrame,
    targets: pd.DataFrame,
    *,
    offset: int,
    delay: int,
    missed: np.ndarray,
) -> dict[int, np.ndarray]:
    aligned = targets.reindex(index=prices.index, columns=prices.columns)
    raw = aligned.to_numpy(dtype=float)
    decisions = aligned.notna().any(axis=1).to_numpy()
    schedule: dict[int, np.ndarray] = {}
    for decided_at in np.flatnonzero(decisions & ~missed):
        fill_at = int(decided_at + 1 + delay + offset)
        if fill_at < len(prices):
            # Ascending decisions overwrite earlier ones on a collision, so
            # the most recently known target is the one implemented.
            schedule[fill_at] = np.where(np.isnan(raw[decided_at]), 0.0, raw[decided_at])
    return schedule


def _run_book(
    prices: pd.DataFrame,
    targets: pd.DataFrame,
    policy: ExecutionPolicy,
    *,
    offset: int,
    missed: np.ndarray,
    cost_bps: float,
    risk_free: pd.Series | None,
) -> BacktestResult:
    px = prices.to_numpy(dtype=float)
    asset_returns = np.full_like(px, np.nan)
    asset_returns[1:] = px[1:] / px[:-1] - 1.0
    if risk_free is None:
        rf = np.zeros(len(prices))
    else:
        rf = risk_free.reindex(prices.index).to_numpy(dtype=float).copy()
    rf[0] = 0.0

    schedule = _scheduled_targets(
        prices, targets, offset=offset, delay=policy.delay, missed=missed
    )
    n_days, n_assets = px.shape
    holdings = np.zeros(n_assets)
    out_returns = np.zeros(n_days)
    out_turnover = np.zeros(n_days)
    out_holdings = np.zeros((n_days, n_assets))
    cost_rate = cost_bps / 1e4

    for i in range(n_days):
        daily = asset_returns[i]
        held = holdings > _EPS
        if np.any(held & np.isnan(daily)):
            bad = prices.columns[held & np.isnan(daily)].tolist()
            raise ValueError(
                f"missing price for held asset(s) {bad} on {prices.index[i].date()}"
            )
        daily = np.where(np.isnan(daily), 0.0, daily)
        cash_weight = 1.0 - float(holdings.sum())
        gross = float(holdings @ daily) + cash_weight * rf[i]
        holdings = holdings * (1.0 + daily) / (1.0 + gross)

        net = gross
        desired = schedule.get(i)
        if desired is not None:
            if (desired < -_EPS).any() or desired.sum() > 1.0 + 1e-6:
                raise ValueError("execution target violates long-only/unlevered constraints")
            if np.any((desired > _EPS) & np.isnan(px[i])):
                bad = prices.columns[(desired > _EPS) & np.isnan(px[i])].tolist()
                raise ValueError(
                    f"target weight on missing-price asset(s) {bad} "
                    f"on {prices.index[i].date()}"
                )
            change = desired - holdings
            if float(np.abs(change).max()) >= policy.band:
                new_holdings = holdings + policy.adjustment * change
                turnover = float(np.abs(new_holdings - holdings).sum())
                net = (1.0 + gross) * (1.0 - turnover * cost_rate) - 1.0
                out_turnover[i] = turnover
                holdings = new_holdings

        out_returns[i] = net
        out_holdings[i] = holdings

    returns = pd.Series(out_returns, index=prices.index, name="ret")
    return BacktestResult(
        returns=returns,
        equity=(1.0 + returns).cumprod().rename("equity"),
        holdings=pd.DataFrame(out_holdings, index=prices.index, columns=prices.columns),
        turnover=pd.Series(out_turnover, index=prices.index, name="turnover"),
        cost_bps=cost_bps,
    )


def _aggregate_books(books: list[BacktestResult], *, cost_bps: float) -> BacktestResult:
    if len(books) == 1:
        return books[0]
    equity = pd.concat([book.equity for book in books], axis=1)
    combined_equity = equity.mean(axis=1).rename("equity")
    combined_returns = combined_equity.pct_change().fillna(combined_equity.iloc[0] - 1.0)
    combined_returns.name = "ret"

    nav = equity.to_numpy(dtype=float)
    total_nav = nav.sum(axis=1)
    weighted_holdings = [
        book.holdings.mul(nav[:, i], axis=0) for i, book in enumerate(books)
    ]
    holdings = weighted_holdings[0].copy()
    for frame in weighted_holdings[1:]:
        holdings = holdings.add(frame)
    holdings = holdings.div(total_nav, axis=0)

    cost_rate = cost_bps / 1e4
    pretrade_nav = np.empty_like(nav)
    dollar_turnover = np.zeros(len(equity))
    for i, book in enumerate(books):
        turn = book.turnover.to_numpy(dtype=float)
        denominator = 1.0 - turn * cost_rate
        pretrade_nav[:, i] = nav[:, i] / denominator
        dollar_turnover += pretrade_nav[:, i] * turn
    combined_turnover = pd.Series(
        dollar_turnover / pretrade_nav.sum(axis=1),
        index=equity.index,
        name="turnover",
    )

    return BacktestResult(
        returns=combined_returns,
        equity=combined_equity,
        holdings=holdings,
        turnover=combined_turnover,
        cost_bps=cost_bps,
    )
