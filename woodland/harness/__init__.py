"""Walk-forward harness (DESIGN.md §7).

The only component permitted to touch validation windows.

    splits      — rolling train/embargo/validate folds over a trading calendar
    ledger      — SQLite trials ledger; every configuration counted
    deflated    — deflated Sharpe ratio (Bailey & Lopez de Prado)
    walkforward — the runner that stitches one out-of-sample curve

Phase 3 (NOT here): the promotion gate and the retrain job. This package
produces evidence; it decides nothing.

Note on layout: DESIGN.md §4 names the components `data/`, `signals/`,
`backtest/`, `harness/`, `live/`. Those are logical names, not paths — on disk
they are modules under `woodland/`, because `data/` at the repo root is
already the (gitignored) parquet store. `harness/` follows `signals/` as a
subpackage of `woodland/`.
"""

from woodland.harness.deflated import deflated_sharpe
from woodland.harness.ledger import TrialsLedger
from woodland.harness.splits import Split, check_embargo_covers_lookback, make_splits
from woodland.harness.walkforward import run_walkforward, with_baselines

__all__ = [
    "Split", "make_splits", "check_embargo_covers_lookback",
    "TrialsLedger", "deflated_sharpe", "run_walkforward", "with_baselines",
]
