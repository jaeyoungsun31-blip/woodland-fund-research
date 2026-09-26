"""Matplotlib tear sheets for completed backtests."""

from __future__ import annotations

from pathlib import Path

import matplotlib

# Tear sheets are files written by batch/reporting scripts, including in CI.
# Select a non-interactive backend before pyplot is imported.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from woodland.backtest import BacktestResult
from woodland.metrics import TRADING_DAYS


def save_tear_sheet(
    result: BacktestResult,
    output_path: Path,
    *,
    title: str = "Backtest tear sheet",
    rolling_window: int = TRADING_DAYS,
) -> Path:
    """Save equity, drawdown, rolling Sharpe, and holdings for ``result``.

    This is deliberately a renderer, not a backtest runner: callers provide a
    completed result so reporting cannot alter its inputs or execution path.
    """
    if rolling_window < 2:
        raise ValueError("rolling_window must be at least two bars")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    equity = result.equity.dropna()
    drawdown = equity.div(equity.cummax()).sub(1.0)
    rolling_mean = result.returns.rolling(rolling_window, min_periods=rolling_window).mean()
    rolling_std = result.returns.rolling(rolling_window, min_periods=rolling_window).std()
    rolling_sharpe = rolling_mean.div(rolling_std).mul(np.sqrt(TRADING_DAYS))

    fig, axes = plt.subplots(2, 2, figsize=(14, 9), layout="constrained")
    fig.suptitle(title)

    axes[0, 0].plot(equity.index, equity, color="tab:blue")
    axes[0, 0].set(title="Equity curve", ylabel="Growth of $1")
    # A linear axis over a multi-decade compounding curve hides everything
    # before the last doubling: on the 1932-2026 window the first fifty years
    # render as a flat line at zero. Switch to log once the curve spans more
    # than two orders of magnitude, where equal vertical distance means equal
    # percentage change and every era is legible.
    span = float(equity.max() / max(equity.min(), 1e-12))
    if span > 100:
        axes[0, 0].set_yscale("log")
        axes[0, 0].set_ylabel("Growth of $1 (log scale)")
    axes[0, 0].grid(alpha=0.25, which="both")

    axes[0, 1].fill_between(drawdown.index, drawdown, 0, color="tab:red", alpha=0.35)
    axes[0, 1].set(title="Drawdown", ylabel="Drawdown")
    axes[0, 1].yaxis.set_major_formatter(lambda value, _: f"{value:.0%}")
    axes[0, 1].grid(alpha=0.25)

    axes[1, 0].plot(rolling_sharpe.index, rolling_sharpe, color="tab:green")
    axes[1, 0].axhline(0, color="black", linewidth=0.8)
    axes[1, 0].set(title=f"Rolling {rolling_window}-bar Sharpe", ylabel="Sharpe")
    axes[1, 0].grid(alpha=0.25)

    holdings = result.holdings.fillna(0.0)
    axes[1, 1].stackplot(holdings.index, holdings.T, labels=holdings.columns, alpha=0.85)
    axes[1, 1].set(title="Holdings over time", ylabel="Portfolio weight", ylim=(0, 1))
    axes[1, 1].legend(loc="upper left", fontsize="small", ncols=2)
    axes[1, 1].grid(alpha=0.25)

    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path
