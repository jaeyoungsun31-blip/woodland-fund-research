"""Walk-forward runner: splits + trials ledger + stitched OOS curve (DESIGN.md §7).

The harness is the ONLY component allowed to touch validation windows, and
this is the function that does it. What it guarantees:

  * Parameters for a validate window are chosen using that split's TRAIN
    window only, and the embargo between them is asserted against the signal's
    declared maximum lookback before anything runs.
  * Every configuration scored is written to the trials ledger — the winners,
    the losers, and the ones that errored — so the deflated-Sharpe denominator
    is the truth rather than a recollection.
  * The out-of-sample curve is ONE backtest over a stitched target frame, not
    a concatenation of per-window backtests. That matters: at each seam the
    portfolio really does have to trade from the old config's holdings into
    the new one's, and stitching returns instead of targets would quietly make
    those rebalances free.

Deliberately NOT here (Phase 3, DESIGN.md §8): the promotion gate, any notion
of an incumbent, and the retrain job. This runner produces evidence; it does
not decide anything.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from woodland import backtest, metrics
from woodland.harness import deflated as dfl
from woodland.harness.ledger import TrialsLedger
from woodland.harness.splits import Split, check_embargo_covers_lookback

TargetBuilder = Callable[[pd.DataFrame, dict], pd.DataFrame]
DEFAULT_COSTS = (0.0, 5.0, 10.0)


@dataclass
class WalkForwardResult:
    """Evidence produced by one walk-forward run. Makes no claim by itself."""

    study: str
    oos_returns: dict[float, pd.Series]      # cost_bps -> stitched OOS daily returns
    oos_turnover: dict[float, pd.Series]
    selections: pd.DataFrame                 # one row per split: chosen config + train score
    trial_sharpes: pd.Series                 # one per distinct config, from the ledger
    n_trials: int                            # distinct configs, from the ledger
    n_trial_rows: int                        # evaluations performed
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    splits: list[Split] = field(default_factory=list)

    def summary(self) -> pd.DataFrame:
        """Metrics at every cost scenario (CLAUDE.md rule 5 — never one number)."""
        rows = {f"OOS @{int(c)}bps": metrics.summarize(r, self.oos_turnover[c])
                for c, r in self.oos_returns.items()}
        return pd.DataFrame(rows).T

    def by_subperiod(self, cost_bps: float = 5.0) -> pd.DataFrame:
        return metrics.by_subperiod(self.oos_returns[cost_bps])

    def deflated(self, cost_bps: float = 5.0) -> dict:
        """Deflated Sharpe of the stitched OOS curve, against the FULL trial count."""
        return dfl.deflated_sharpe(self.oos_returns[cost_bps],
                                   n_trials=self.n_trials,
                                   trial_sharpes=self.trial_sharpes)


def run_walkforward(
    prices: pd.DataFrame,
    target_builder: TargetBuilder,
    grid: Sequence[dict],
    *,
    splits: list[Split],
    ledger: TrialsLedger,
    study: str,
    max_lookback_days: int,
    select_cost_bps: float = 5.0,
    report_cost_bps: Sequence[float] = DEFAULT_COSTS,
    objective: str = "sharpe_rf0",
    risk_free: pd.Series | None = None,
) -> WalkForwardResult:
    """Run the walk-forward loop and return the stitched out-of-sample evidence.

    prices            : Date x ticker adjusted closes
    target_builder    : (prices, config) -> sparse target-weight frame
    grid              : every configuration to consider (all of them get logged)
    max_lookback_days : the signal's longest lookback IN BARS. Declared by the
                        caller and checked against the embargo before any
                        window is touched — an understated value here is a
                        silent leak, so it belongs in the study's journal entry.
    """
    if not splits:
        raise ValueError("no splits: history too short for this scheme?")
    if not grid:
        raise ValueError("empty configuration grid")

    index = pd.DatetimeIndex(prices.index)
    check_embargo_covers_lookback(splits, index, max_lookback_days)

    scheme = {
        "train_start": str(splits[0].train_start.date()),
        "n_splits": len(splits),
        "max_lookback_days": max_lookback_days,
        "select_cost_bps": select_cost_bps,
    }

    # Signals are causal (enforced by tests/test_no_lookahead.py), so a config's
    # full-history run can be scored on any window by slicing. Computing it once
    # per config instead of once per (config, split) is a pure saving.
    per_config: dict[int, tuple[pd.DataFrame, pd.Series]] = {}
    for c_i, cfg in enumerate(grid):
        try:
            tgt = target_builder(prices, cfg)
            res = backtest.run(prices, tgt, cost_bps=select_cost_bps,
                               risk_free=risk_free)
            per_config[c_i] = (tgt, res.returns)
        except Exception as e:
            ledger.record(study, cfg, status="error", split_scheme=scheme,
                          notes=f"{type(e).__name__}: {e}")

    if not per_config:
        raise RuntimeError("every configuration in the grid failed to build")

    stitched = pd.DataFrame(np.nan, index=index, columns=prices.columns)
    sel_rows: list[dict[str, object]] = []

    for split in splits:
        v_idx = split.validate_index(index)
        t_idx = split.train_index(index)
        if not len(v_idx) or not len(t_idx):
            continue

        scores: dict[int, float] = {}
        for c_i, (_, rets) in per_config.items():
            window = rets.loc[t_idx[0]:t_idx[-1]]
            m = metrics.summarize(window)
            m["n_obs"] = len(window)
            scores[c_i] = m.get(objective, float("nan"))
            # EVERY configuration evaluated is recorded, not just the winner.
            ledger.record(
                study, grid[c_i], metrics=m, cost_bps=select_cost_bps,
                split_index=split.i, split_scheme=scheme,
                window=f"train {t_idx[0].date()}..{t_idx[-1].date()}",
            )

        ranked = [c for c, v in scores.items() if np.isfinite(v)]
        if not ranked:
            sel_rows.append({"split": split.i, "config": None,
                             "train_score": float("nan"), "note": "no finite score"})
            continue
        best = max(ranked, key=lambda c: scores[c])

        # The winner's instructions for THIS validate window only.
        tgt = per_config[best][0]
        rows = tgt.loc[v_idx[0]:v_idx[-1]].dropna(how="all")
        stitched.loc[rows.index] = rows

        sel_rows.append({
            "split": split.i,
            "validate_start": v_idx[0].date(),
            "validate_end": v_idx[-1].date(),
            "config": grid[best],
            "train_score": scores[best],
            "n_rebalances": len(rows),
        })

    oos_start = min(s.validate_index(index)[0] for s in splits if len(s.validate_index(index)))
    oos_end = max(s.validate_index(index)[-1] for s in splits if len(s.validate_index(index)))

    oos_returns, oos_turnover = {}, {}
    for c in report_cost_bps:
        res = backtest.run(prices, stitched, cost_bps=float(c), risk_free=risk_free)
        oos_returns[float(c)] = res.returns.loc[oos_start:oos_end]
        oos_turnover[float(c)] = res.turnover.loc[oos_start:oos_end]

    return WalkForwardResult(
        study=study,
        oos_returns=oos_returns,
        oos_turnover=oos_turnover,
        selections=pd.DataFrame(sel_rows),
        trial_sharpes=ledger.config_sharpes(study),
        n_trials=ledger.n_trials(study),
        n_trial_rows=ledger.n_trials(study, distinct=False),
        oos_start=oos_start,
        oos_end=oos_end,
        splits=splits,
    )


def with_baselines(prices: pd.DataFrame, result: WalkForwardResult,
                   sixty_forty: dict[str, float] | None = None,
                   risk_free: pd.Series | None = None) -> pd.DataFrame:
    """Side-by-side table over the SAME out-of-sample window (CLAUDE.md rule 5).

    A strategy number without SPY and 60/40 beside it over the identical period
    is not a result, it is a decoration.
    """
    sixty_forty = sixty_forty or {"SPY": 0.6, "IEF": 0.4}
    lo, hi = result.oos_start, result.oos_end
    named = {f"{result.study} OOS @{int(c)}bps": r for c, r in result.oos_returns.items()}
    spy = backtest.buy_and_hold(prices, "SPY", cost_bps=0.0,
                                risk_free=risk_free).returns.loc[lo:hi]
    named["SPY buy&hold"] = spy
    for c in result.oos_returns:
        mix = backtest.fixed_mix(prices, sixty_forty, cost_bps=float(c),
                                 risk_free=risk_free).returns.loc[lo:hi]
        named[f"60/40 @{int(c)}bps"] = mix
    return metrics.compare(named)
