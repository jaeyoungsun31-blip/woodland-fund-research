"""The Woodland Fund — systematic ETF strategy research pipeline.

Components (DESIGN.md §4):
    data     — ingestion, integrity checks, parquet store (point-in-time, raw immutable)
    backtest — vectorized portfolio simulation with costs (next-bar execution)
    metrics  — performance statistics and tear sheets
    signals  — feature/signal computation (may only use data <= t)
"""

__version__ = "0.1.0"
