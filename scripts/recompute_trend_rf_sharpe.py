"""Recompute frozen v6/v7/v8 paired Sharpe inference under both RF conventions.

This is an audit recomputation, not a study: it rebuilds only registered return
streams, writes no trials-ledger rows, and makes no selection.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import recompute_rf_sharpe as rf
from scripts import run_trend_blend as v8
from scripts import run_trend_sleeve as v7
from woodland import backtest, cash, data
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import splits
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import (
    COSTS,
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    MULTI_ASSET,
    SECTORS,
    stitch,
)


@dataclass(frozen=True)
class Context:
    name: str
    prices: pd.DataFrame
    folds: list[splits.Split]
    risk_free: pd.Series


def _etf_context(store: Path) -> Context:
    config = load_config()
    etf_prices, _ = data.drop_suspect_dates(data.build_matrix(all_tickers(config), store))
    etf_index = pd.DatetimeIndex(etf_prices.index)
    etf_folds = splits.make_splits(
        etf_index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    splits.check_embargo_covers_lookback(etf_folds, etf_index, MAX_LOOKBACK_DAYS)
    etf_rf, _ = cash.align_risk_free(cash.load_risk_free_daily(store), etf_index)

    return Context("ETF 2004-2026", etf_prices, etf_folds, etf_rf)


def _deep_context(store: Path) -> Context:
    deep_prices = v7.load_deep_prices(store)
    deep_index = pd.DatetimeIndex(deep_prices.index)
    deep_folds = splits.make_splits(
        deep_index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    splits.check_embargo_covers_lookback(deep_folds, deep_index, MAX_LOOKBACK_DAYS)
    deep_rf, _ = cash.align_risk_free(cash.load_risk_free_daily(store), deep_index)
    return Context("FF12 1932-2026", deep_prices, deep_folds, deep_rf)


def _rebuild(
    prices: pd.DataFrame, spec: v7.CurveSpec, folds: list[splits.Split], risk_free: pd.Series
) -> v7.CurveResult:
    index = pd.DatetimeIndex(prices.index)
    start = folds[0].validate_index(index)[0]
    end = folds[-1].validate_index(index)[-1]
    targets = stitch(prices, spec.targets, folds)
    returns: dict[float, pd.Series] = {}
    turnover: dict[float, pd.Series] = {}
    for cost in COSTS:
        result = backtest.run(prices, targets, cost_bps=cost, risk_free=risk_free)
        returns[float(cost)] = result.returns.loc[start:end]
        turnover[float(cost)] = result.turnover.loc[start:end]
    return v7.CurveResult(spec, returns, turnover)


def _comparisons(
    study: str,
    curves: Iterable[v7.CurveResult],
    base: v7.CurveResult,
) -> list[rf.Comparison]:
    return [
        rf.Comparison(
            study,
            float(cost),
            curve.spec.label,
            base.spec.label,
            curve.returns[float(cost)],
            base.returns[float(cost)],
        )
        for curve in curves
        for cost in COSTS
    ]


def _v6_comparisons(context: Context) -> list[rf.Comparison]:
    prices, folds, risk_free = context.prices, context.folds, context.risk_free
    index = pd.DatetimeIndex(prices.index)
    start = folds[0].validate_index(index)[0]
    end = folds[-1].validate_index(index)[-1]

    def run_targets(targets: pd.DataFrame) -> dict[float, pd.Series]:
        return {
            float(cost): backtest.run(
                prices, targets, cost_bps=cost, risk_free=risk_free
            ).returns.loc[start:end]
            for cost in COSTS
        }

    multi = run_targets(
        stitch(
            prices,
            trend.ensemble_targets(prices, MULTI_ASSET, LOOKBACKS, risk_off=None),
            folds,
        )
    )
    multi_dbc = run_targets(
        stitch(
            prices,
            trend.ensemble_targets(prices, [*MULTI_ASSET, "DBC"], LOOKBACKS, risk_off=None),
            folds,
        )
    )
    v2 = run_targets(
        stitch(
            prices,
            trend.ensemble_targets(prices, SECTORS, LOOKBACKS, risk_off="IEF"),
            folds,
        )
    )
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.60, "IEF": 0.40})
    mix = run_targets(mix_targets)
    vol_mix = run_targets(vol_target_targets(prices, mix_targets, window=63, target_ann_vol=0.10))
    spy = {
        float(cost): backtest.buy_and_hold(
            prices, "SPY", cost_bps=cost, risk_free=risk_free
        ).returns.loc[start:end]
        for cost in COSTS
    }
    pairs = [
        ("v6 multi-asset", multi, "v2 9-sector", v2),
        ("v6 multi-asset", multi, "SPY buy&hold", spy),
        ("v6 multi-asset", multi, "60/40", mix),
        ("v6 multi-asset", multi, "vol-target 60/40", vol_mix),
        ("v6 +DBC", multi_dbc, "v6 multi-asset", multi),
    ]
    return [
        rf.Comparison(
            "trend-v6-multiasset",
            float(cost),
            challenger,
            reference,
            candidate[float(cost)],
            benchmark[float(cost)],
        )
        for challenger, candidate, reference, benchmark in pairs
        for cost in COSTS
    ]


def _tables(
    groups: set[str], curves: set[str], costs: set[float], store: Path, date_slice: slice
) -> list[pd.DataFrame]:
    batches: list[tuple[str, str, pd.Series, list[rf.Comparison]]] = []
    if groups.intersection({"v6", "v7-etf", "v8-etf"}):
        etf = _etf_context(store)
        etf_base_targets, etf_specs = v7.build_etf_specs(etf.prices)
        etf_base = v7.evaluate_base(
            prices=etf.prices,
            base_targets=etf_base_targets,
            folds=etf.folds,
            engine_risk_free=etf.risk_free,
        )
        if "v6" in groups:
            batches.append(("v6", etf.name, etf.risk_free, _v6_comparisons(etf)))
        if "v7-etf" in groups:
            etf_v7 = [_rebuild(etf.prices, spec, etf.folds, etf.risk_free) for spec in etf_specs]
            batches.append(
                (
                    "v7-etf",
                    etf.name,
                    etf.risk_free,
                    _comparisons("trend-v7-sleeve-etf", etf_v7, etf_base),
                )
            )
        if "v8-etf" in groups:
            etf_blend_base, _, etf_blends = v8.build_etf_blends(etf.prices)
            if not etf_blend_base.equals(etf_base_targets):
                raise RuntimeError("v8 ETF base does not reproduce v7 base")
            etf_v8 = [_rebuild(etf.prices, spec, etf.folds, etf.risk_free) for spec in etf_blends]
            batches.append(
                (
                    "v8-etf",
                    etf.name,
                    etf.risk_free,
                    _comparisons("trend-v8-blend-etf", etf_v8, etf_base),
                )
            )
    if groups.intersection({"v7-deep", "v8-deep"}):
        deep = _deep_context(store)
        deep_base_targets, deep_specs = v7.build_deep_specs(deep.prices)
        deep_base = v7.evaluate_base(
            prices=deep.prices,
            base_targets=deep_base_targets,
            folds=deep.folds,
            engine_risk_free=deep.risk_free,
        )
        if "v7-deep" in groups:
            deep_v7 = [
                _rebuild(deep.prices, spec, deep.folds, deep.risk_free) for spec in deep_specs
            ]
            batches.append(
                (
                    "v7-deep",
                    deep.name,
                    deep.risk_free,
                    _comparisons("trend-v7-sleeve-deep", deep_v7, deep_base),
                )
            )
        if "v8-deep" in groups:
            deep_blend_base, _, deep_blends = v8.build_deep_blends(deep.prices)
            if not deep_blend_base.equals(deep_base_targets):
                raise RuntimeError("v8 deep base does not reproduce v7 base")
            deep_v8 = [
                _rebuild(deep.prices, spec, deep.folds, deep.risk_free) for spec in deep_blends
            ]
            batches.append(
                (
                    "v8-deep",
                    deep.name,
                    deep.risk_free,
                    _comparisons("trend-v8-blend-deep", deep_v8, deep_base),
                )
            )
    tables: list[pd.DataFrame] = []
    for group, window, risk_free, comparisons in batches:
        if group not in groups:
            continue
        if curves:
            comparisons = [item for item in comparisons if item.challenger in curves]
            if not comparisons:
                continue
        if costs:
            comparisons = [item for item in comparisons if item.cost_bps in costs]
            if not comparisons:
                continue
        window_comparisons = [
            rf.Comparison(
                item.study,
                item.cost_bps,
                item.challenger,
                item.reference,
                item.candidate.loc[date_slice],
                item.benchmark.loc[date_slice],
            )
            for item in comparisons
        ]
        window_risk_free = risk_free.loc[date_slice]
        table = rf.side_by_side_inference(window_comparisons, window_risk_free)
        table.insert(1, "window", window)
        tables.append(table)
    return tables


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--group",
        action="append",
        choices=("v6", "v7-etf", "v7-deep", "v8-etf", "v8-deep"),
        help="one frozen comparison family; defaults to all",
    )
    parser.add_argument("--output", type=Path, help="optional CSV audit artifact")
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / load_config()["data"]["store"],
        help="read-only data-store snapshot; defaults to the current store",
    )
    parser.add_argument(
        "--curve",
        action="append",
        help="exact pre-registered challenger label; repeatable",
    )
    parser.add_argument(
        "--cost",
        action="append",
        type=float,
        choices=COSTS,
        help="registered cost level; repeatable",
    )
    parser.add_argument("--start", help="inclusive reporting-window start")
    parser.add_argument("--end", help="inclusive reporting-window end")
    args = parser.parse_args()
    print("=== TREND FAMILY RF-CONVENTION RECOMPUTATION ===")
    print("Frozen inputs only; no ledger writes, selection, configuration, weight, or cost added.")
    print("bootstrap=10,000 stationary resamples; expected block=21; seed=0")
    selected_groups = set(args.group or ("v6", "v7-etf", "v7-deep", "v8-etf", "v8-deep"))
    results = pd.concat(
        _tables(
            selected_groups,
            set(args.curve or ()),
            set(args.cost or ()),
            args.data,
            slice(args.start, args.end),
        ),
        ignore_index=True,
    )
    if args.output:
        results.to_csv(args.output, index=False)
    for study in (
        "trend-v7-sleeve-etf",
        "trend-v7-sleeve-deep",
        "trend-v6-multiasset",
        "trend-v8-blend-etf",
        "trend-v8-blend-deep",
    ):
        print(f"\n=== {study}: rf=0 and excess-return inference ===")
        print(results[results["study"] == study].round(6).to_string(index=False))


if __name__ == "__main__":
    main()
