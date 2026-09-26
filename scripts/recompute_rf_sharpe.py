"""Recompute v15/v17 paired Sharpe inference under two risk-free conventions.

This is the dated 2026-09-03d measurement correction, not a study. It rebuilds
only the already-registered return streams and never writes to the trials
ledger.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import run_sleeve_overlay as v17
from scripts import run_xsmom_holding as v15
from woodland import backtest, cash, metrics, overlay, stats, study, xsmom
from woodland.config import ROOT

pd.set_option("display.width", 420)
pd.set_option("display.max_columns", 100)
pd.set_option("display.max_rows", 1_000)


@dataclass(frozen=True)
class Comparison:
    study: str
    cost_bps: float
    challenger: str
    reference: str
    candidate: pd.Series
    benchmark: pd.Series


@dataclass(frozen=True)
class RecomputedReturns:
    index: pd.DatetimeIndex
    risk_free: pd.Series
    v15: dict[str, dict[float, pd.Series]]
    v17: dict[str, dict[float, pd.Series]]
    selection_counts: pd.Series


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "10_Portfolios_Prior_12_2_Daily_CSV.zip",
    )
    return parser.parse_args()


def build_registered_returns(archive: Path) -> RecomputedReturns:
    """Rebuild the frozen v15 and v17 streams without adding ledger rows."""
    deciles = xsmom.parse_daily_deciles(archive).dropna()
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    common_index = deciles.index.intersection(factors.index)
    deciles = deciles.reindex(common_index).dropna()
    factors = factors.reindex(deciles.index)
    if not deciles.index.equals(factors.index) or factors.isna().any().any():
        raise ValueError("decile and factor calendars do not match after alignment")

    prices = ((1.0 + deciles).cumprod() * 100.0).join(factors, how="inner")
    full_index = pd.DatetimeIndex(prices.index)
    folds = study.make_folds(full_index, study.XSMOM_EMBARGO_DAYS)
    lo, hi, n_bars = study.oos_window(full_index, folds)
    oos_index = pd.DatetimeIndex(prices.loc[lo:hi].index)
    expected = (
        v17.V17_EXPECTED_START,
        v17.V17_EXPECTED_END,
        v17.V17_EXPECTED_BARS,
        v17.V17_EXPECTED_BARS,
        v17.V17_EXPECTED_FOLDS,
    )
    if (lo, hi, n_bars, len(oos_index), len(folds)) != expected:
        raise ValueError(
            "registered window mismatch: "
            f"got {lo.date()}..{hi.date()}, {n_bars}/{len(oos_index)} bars, "
            f"{len(folds)} folds"
        )

    risk_free, _ = cash.align_risk_free(
        cash.load_risk_free_daily(ROOT / "data"), oos_index
    )
    oos_deciles = deciles.reindex(oos_index)

    control_weights = {
        "MKT": {"MKT": 1.0},
        "60_40_MKT_CASH": {"MKT": 0.6, "CASH": 0.4},
    }
    control_gross: dict[str, pd.Series] = {}
    control_turnover: dict[str, pd.Series] = {}
    full_control_results: dict[str, backtest.BacktestResult] = {}
    for name, weights in control_weights.items():
        targets = v17.fixed_targets(prices, weights)
        full_control_results[name] = backtest.run(prices, targets, cost_bps=0.0)
        stitched = study.stitch(prices, targets, folds)
        result = backtest.run(prices, stitched, cost_bps=0.0)
        control_gross[name] = result.returns.reindex(oos_index)
        control_turnover[name] = result.turnover.reindex(oos_index)

    control_returns = {
        name: {
            cost: v17.apply_outer_cost(gross, control_turnover[name], cost)
            for cost in v17.V17_COST_LEVELS
        }
        for name, gross in control_gross.items()
    }

    holding_gross: dict[str, pd.Series] = {}
    holding_turnover: dict[str, xsmom.HoldingTurnover] = {}
    for frequency in v15.FREQUENCIES:
        dates = xsmom.formation_dates(oos_index, frequency)
        holding_gross[frequency] = xsmom.stale_cohort_returns(oos_deciles, dates)
        holding_turnover[frequency] = xsmom.holding_period_turnover(oos_index, dates)

    v15_returns = {
        frequency: {
            cost: xsmom.net_of_internal_cost(
                holding_gross[frequency], holding_turnover[frequency].total, cost
            )
            for cost in v17.V17_COST_LEVELS
        }
        for frequency in v15.FREQUENCIES
    }
    v15_returns.update(control_returns)

    monthly_dates = xsmom.formation_dates(oos_index, "monthly")
    sleeve_returns = v15_returns["monthly"]
    fixed = {
        f"overlay_s{weight:.2f}": {
            cost: overlay.mix_returns(
                control_returns["60_40_MKT_CASH"][cost],
                sleeve_returns[cost],
                weight,
                monthly_dates,
                cost_bps=cost,
            ).returns
            for cost in v17.V17_COST_LEVELS
        }
        for weight in v17.V17_SLEEVE_WEIGHTS
    }

    full_monthly_dates = xsmom.formation_dates(full_index, "monthly")
    full_sleeve_gross = xsmom.stale_cohort_returns(deciles, full_monthly_dates)
    full_sleeve_turnover = xsmom.holding_period_turnover(
        full_index, full_monthly_dates
    )
    full_sleeve_5 = xsmom.net_of_internal_cost(
        full_sleeve_gross,
        full_sleeve_turnover.total,
        v17.V17_LEDGER_COST,
    )
    full_baseline = full_control_results["60_40_MKT_CASH"]
    full_baseline_5 = v17.apply_outer_cost(
        full_baseline.returns, full_baseline.turnover, v17.V17_LEDGER_COST
    )
    training_candidates = {
        weight: overlay.mix_returns(
            full_baseline_5,
            full_sleeve_5,
            weight,
            full_monthly_dates,
            cost_bps=v17.V17_LEDGER_COST,
        ).returns
        for weight in v17.V17_SLEEVE_WEIGHTS
    }
    selected_schedule, selection_table = v17.select_training_weights(
        full_index, folds, training_candidates
    )
    if not selected_schedule.index.equals(monthly_dates):
        raise ValueError("registered B schedule does not match the OOS calendar")
    selected = {
        cost: overlay.mix_returns(
            control_returns["60_40_MKT_CASH"][cost],
            sleeve_returns[cost],
            selected_schedule,
            monthly_dates,
            cost_bps=cost,
        ).returns
        for cost in v17.V17_COST_LEVELS
    }
    v17_returns = {**fixed, "B_selected": selected}
    counts = (
        selection_table["selected_s"]
        .value_counts()
        .reindex(v17.V17_SLEEVE_WEIGHTS, fill_value=0)
        .astype(int)
    )
    return RecomputedReturns(oos_index, risk_free, v15_returns, v17_returns, counts)


def comparisons_for_window(
    rebuilt: RecomputedReturns, date_slice: slice
) -> list[Comparison]:
    comparisons: list[Comparison] = []
    for cost in v17.V17_COST_LEVELS:
        for challenger, by_cost in rebuilt.v17.items():
            comparisons.append(
                Comparison(
                    "sleeve-v17-overlay",
                    cost,
                    challenger,
                    "60_40_MKT_CASH",
                    by_cost[cost].loc[date_slice],
                    rebuilt.v15["60_40_MKT_CASH"][cost].loc[date_slice],
                )
            )
        for challenger in v15.FREQUENCIES:
            for reference in ("60_40_MKT_CASH", "MKT"):
                comparisons.append(
                    Comparison(
                        "xsmom-v15-holding",
                        cost,
                        challenger,
                        reference,
                        rebuilt.v15[challenger][cost].loc[date_slice],
                        rebuilt.v15[reference][cost].loc[date_slice],
                    )
                )
    return comparisons


def side_by_side_inference(
    comparisons: list[Comparison], risk_free: pd.Series
) -> pd.DataFrame:
    """Compute both conventions from one common set of bootstrap paths."""
    if not comparisons:
        raise ValueError("paired inference needs at least one comparison")
    index = comparisons[0].candidate.index
    aligned_rf = risk_free.reindex(index)
    rf_values = aligned_rf.to_numpy(dtype=float)
    series_by_key: dict[tuple[str, str, float], np.ndarray] = {}
    candidate_keys: list[tuple[str, str, float]] = []
    reference_keys: list[tuple[str, str, float]] = []
    for item in comparisons:
        candidate_key = (item.study, item.challenger, item.cost_bps)
        reference_key = ("control", item.reference, item.cost_bps)
        candidate_keys.append(candidate_key)
        reference_keys.append(reference_key)
        series_by_key.setdefault(
            candidate_key, item.candidate.reindex(index).to_numpy(dtype=float)
        )
        series_by_key.setdefault(
            reference_key, item.benchmark.reindex(index).to_numpy(dtype=float)
        )
    if not np.isfinite(rf_values).all() or not all(
        np.isfinite(values).all() for values in series_by_key.values()
    ):
        raise ValueError("paired inference inputs and risk-free must be aligned")

    def column_sharpes(values: np.ndarray, axis: int) -> np.ndarray:
        means = values.mean(axis=axis)
        deviations = values.std(axis=axis, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(
                deviations > 0.0,
                means / deviations * sqrt(stats.TRADING_DAYS),
                np.nan,
            )

    keys = list(series_by_key)
    key_positions = {key: position for position, key in enumerate(keys)}
    raw_values = np.column_stack([series_by_key[key] for key in keys])
    observed_series_rf0 = column_sharpes(raw_values, 0)
    observed_series_excess = column_sharpes(raw_values - rf_values[:, None], 0)
    observed_rf0 = np.array(
        [
            observed_series_rf0[key_positions[candidate_key]]
            - observed_series_rf0[key_positions[reference_key]]
            for candidate_key, reference_key in zip(
                candidate_keys, reference_keys, strict=True
            )
        ]
    )
    observed_excess = np.array(
        [
            observed_series_excess[key_positions[candidate_key]]
            - observed_series_excess[key_positions[reference_key]]
            for candidate_key, reference_key in zip(
                candidate_keys, reference_keys, strict=True
            )
        ]
    )
    draws_rf0 = np.empty(
        (v17.V17_BOOTSTRAP_RESAMPLES, len(comparisons)), dtype=float
    )
    draws_excess = np.empty_like(draws_rf0)
    rng = np.random.default_rng(v17.V17_BOOTSTRAP_SEED)
    batch = max(
        1,
        min(
            v17.V17_BOOTSTRAP_RESAMPLES,
            v17.V17_BOOTSTRAP_INDEX_BUDGET // len(index),
        ),
    )
    completed = 0
    while completed < v17.V17_BOOTSTRAP_RESAMPLES:
        size = min(batch, v17.V17_BOOTSTRAP_RESAMPLES - completed)
        indices = stats.stationary_bootstrap_indices(
            len(index), v17.V17_BOOTSTRAP_BLOCK, size, rng
        )
        sampled_rf = rf_values[indices]
        series_rf0 = np.empty((size, len(keys)), dtype=float)
        series_excess = np.empty_like(series_rf0)
        for position, key in enumerate(keys):
            sampled = series_by_key[key][indices]
            series_rf0[:, position] = column_sharpes(sampled, 1)
            sampled -= sampled_rf
            series_excess[:, position] = column_sharpes(sampled, 1)
        for column, (candidate_key, reference_key) in enumerate(
            zip(candidate_keys, reference_keys, strict=True)
        ):
            candidate_position = key_positions[candidate_key]
            reference_position = key_positions[reference_key]
            draws_rf0[completed : completed + size, column] = (
                series_rf0[:, candidate_position] - series_rf0[:, reference_position]
            )
            draws_excess[completed : completed + size, column] = (
                series_excess[:, candidate_position]
                - series_excess[:, reference_position]
            )
        completed += size

    def interval_and_p(draws: np.ndarray, observed: float) -> tuple[float, float, float]:
        finite = draws[np.isfinite(draws)]
        low, high = np.quantile(finite, [0.025, 0.975])
        centred = np.abs(finite - observed)
        p_value = (1 + int(np.sum(centred >= abs(observed)))) / (len(finite) + 1)
        return float(low), float(high), float(p_value)

    rows: list[dict[str, object]] = []
    for column, item in enumerate(comparisons):
        row: dict[str, object] = {
            "study": item.study,
            "cost_bps": item.cost_bps,
            "challenger": item.challenger,
            "reference": item.reference,
            "n_obs": len(index),
        }
        for convention, observed, draws, convention_rf in (
            ("rf0", observed_rf0[column], draws_rf0[:, column], None),
            (
                "excess",
                observed_excess[column],
                draws_excess[:, column],
                aligned_rf,
            ),
        ):
            low, high, p_value = interval_and_p(draws, float(observed))
            hac = stats.ledoit_wolf_sharpe_test(
                item.candidate,
                item.benchmark,
                name_a=item.challenger,
                name_b=item.reference,
                rf_daily=convention_rf,
            )
            candidate_for_correlation = (
                item.candidate
                if convention_rf is None
                else metrics.excess_returns(item.candidate, convention_rf)
            )
            benchmark_for_correlation = (
                item.benchmark
                if convention_rf is None
                else metrics.excess_returns(item.benchmark, convention_rf)
            )
            row.update(
                {
                    f"{convention}_sr_challenger": metrics.sharpe(
                        item.candidate, rf_daily=convention_rf
                    ),
                    f"{convention}_sr_reference": metrics.sharpe(
                        item.benchmark, rf_daily=convention_rf
                    ),
                    f"{convention}_delta": float(observed),
                    f"{convention}_boot_low": low,
                    f"{convention}_boot_high": high,
                    f"{convention}_boot_p": p_value,
                    f"{convention}_hac_low": hac.ci_low,
                    f"{convention}_hac_high": hac.ci_high,
                    f"{convention}_hac_p": hac.p_value,
                    f"{convention}_correlation": float(
                        candidate_for_correlation.corr(benchmark_for_correlation)
                    ),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def assert_reproduction_anchors(results: pd.DataFrame) -> None:
    anchors = [
        ("full", "sleeve-v17-overlay", "overlay_s0.10", "60_40_MKT_CASH", -0.005399),
        ("1980-2026", "sleeve-v17-overlay", "overlay_s0.10", "60_40_MKT_CASH", -0.012484),
        ("full", "xsmom-v15-holding", "monthly", "MKT", 0.065305),
    ]
    for window, study_name, challenger, reference, expected in anchors:
        row = results[
            (results["window"] == window)
            & (results["study"] == study_name)
            & (results["cost_bps"] == 10.0)
            & (results["challenger"] == challenger)
            & (results["reference"] == reference)
        ]
        if len(row) != 1:
            raise ValueError(f"missing reproduction anchor for {window}/{challenger}")
        actual = float(row.iloc[0]["rf0_delta"])
        if round(actual, 6) != expected:
            raise ValueError(
                f"rf=0 reproduction failed for {window}/{challenger}: "
                f"expected {expected:+.6f}, got {actual:+.6f}"
            )


def criterion_table(results: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    definitions = [
        ("C1", "full", "overlay_s0.10"),
        ("C3", "1980-2026", "overlay_s0.10"),
        ("B C1 (secondary)", "full", "B_selected"),
    ]
    for criterion, window, challenger in definitions:
        row = results[
            (results["window"] == window)
            & (results["study"] == "sleeve-v17-overlay")
            & (results["cost_bps"] == 10.0)
            & (results["challenger"] == challenger)
        ].iloc[0]
        rows.append(
            {
                "criterion": criterion,
                "window": window,
                "challenger": challenger,
                "rf0_delta": row["rf0_delta"],
                "rf0_boot_low": row["rf0_boot_low"],
                "rf0_met": bool(row["rf0_boot_low"] > 0.0),
                "excess_delta": row["excess_delta"],
                "excess_boot_low": row["excess_boot_low"],
                "excess_met": bool(row["excess_boot_low"] > 0.0),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    rebuilt = build_registered_returns(args.archive)
    print("=== RF CONVENTION CORRECTION: FROZEN INPUTS ===")
    print(
        f"archive={args.archive}\n"
        f"OOS={rebuilt.index[0].date()}..{rebuilt.index[-1].date()} "
        f"bars={len(rebuilt.index)}\n"
        f"costs={v17.V17_COST_LEVELS}; v17_weights={v17.V17_SLEEVE_WEIGHTS}; "
        "v15_frequencies=monthly/quarterly/semiannual/annual\n"
        f"bootstrap=resamples={v17.V17_BOOTSTRAP_RESAMPLES}, "
        f"expected_block={v17.V17_BOOTSTRAP_BLOCK}, seed={v17.V17_BOOTSTRAP_SEED}\n"
        f"mean_annualized_real_rf="
        f"{rebuilt.risk_free.mean() * stats.TRADING_DAYS:.6%}"
    )
    print(
        "This is a metric recomputation, not a study: no configuration, weight, "
        "cost, data, selection rule, or ledger row is added."
    )
    print(
        "B remains the registered best-in-training path selected on rf=0 at 5 bps; "
        f"selection_counts={rebuilt.selection_counts.to_dict()}"
    )

    all_results: list[pd.DataFrame] = []
    windows = [
        ("full", slice(None, None)),
        ("1932-1979", slice(None, "1979-12-31")),
        ("1980-2026", slice("1980-01-01", None)),
    ]
    for window, date_slice in windows:
        comparisons = comparisons_for_window(rebuilt, date_slice)
        window_rf = rebuilt.risk_free.loc[date_slice]
        print(
            f"computing {window}: {len(comparisons)} pairs x two conventions",
            flush=True,
        )
        table = side_by_side_inference(comparisons, window_rf)
        table.insert(1, "window", window)
        all_results.append(table)

    results = pd.concat(all_results, ignore_index=True)
    assert_reproduction_anchors(results)

    for study_name in ("sleeve-v17-overlay", "xsmom-v15-holding"):
        print(f"\n=== {study_name.upper()}: BOTH CONVENTIONS SIDE BY SIDE ===")
        print(
            results[results["study"] == study_name]
            .drop(columns="study")
            .round(6)
            .to_string(index=False)
        )

    criteria = criterion_table(results)
    print("\n=== V17 REGISTERED C1/C3 DECISIONS UNDER BOTH CONVENTIONS ===")
    print(criteria.round(6).to_string(index=False))
    print(
        "C2 is unchanged: drawdown, CVaR95, and CVaR99 do not depend on the "
        "Sharpe risk-free convention."
    )
    print(
        "The identification gap is unchanged: v15 holding paths, v17 sleeve paths, "
        "and their turnover remain model-implied. The K~232 turnover budget is "
        "also unchanged because it uses crossover cost and turnover, not Sharpe's "
        "risk-free convention."
    )
    print(
        "Correction complete. Both conventions remain on record side by side; "
        "nothing was promoted and no ledger row was written."
    )


if __name__ == "__main__":
    main()
