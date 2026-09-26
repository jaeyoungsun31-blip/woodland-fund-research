"""Execute the pre-registered sleeve-v17-overlay study."""

from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import (
    backtest,
    cash,
    diversification,
    metrics,
    overlay,
    stats,
    study,
    tailrisk,
    xsmom,
)
from woodland.config import ROOT
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger, config_hash

V17_STUDY = "sleeve-v17-overlay"
V17_SLEEVE_WEIGHTS = (0.05, 0.10, 0.20, 0.30)
V17_PRIMARY_WEIGHT = 0.10
V17_COST_LEVELS = (0.0, 5.0, 10.0, 25.0, 50.0)
V17_LEDGER_COST = 5.0
V17_EXPECTED_BARS = 24_434
V17_EXPECTED_FOLDS = 94
V17_EXPECTED_START = pd.Timestamp("1932-09-06")
V17_EXPECTED_END = pd.Timestamp("2026-06-30")
V17_BOOTSTRAP_RESAMPLES = 10_000
V17_BOOTSTRAP_BLOCK = 21
V17_BOOTSTRAP_SEED = 0
V17_BOOTSTRAP_INDEX_BUDGET = 3_000_000
V17_BOOTSTRAP_PAIR_CHUNK = 2
V17_DECADE_BREAKS = [f"{year}-01-01" for year in range(1940, 2030, 10)]

pd.set_option("display.width", 280)
pd.set_option("display.max_columns", 100)
pd.set_option("display.max_rows", 1_000)


def fixed_targets(
    prices: pd.DataFrame, weights: dict[str, float]
) -> pd.DataFrame:
    """Sparse monthly targets for a fixed-weight control."""
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    dates = xsmom.formation_dates(pd.DatetimeIndex(prices.index), "monthly")
    for date in dates:
        targets.loc[date, list(weights)] = list(weights.values())
    return targets


def apply_outer_cost(
    gross: pd.Series, turnover: pd.Series, cost_bps: float
) -> pd.Series:
    aligned = turnover.reindex(gross.index)
    if aligned.isna().any():
        raise ValueError("outer turnover does not cover gross returns")
    return ((1.0 + gross) * (1.0 - aligned * cost_bps / 10_000.0) - 1.0).rename(
        "ret"
    )


def result_summary(
    returns: pd.Series, turnover: pd.Series, rf_daily: pd.Series
) -> dict[str, float | int]:
    result = metrics.summarize(returns, turnover, rf_daily=rf_daily)
    result["worst_day"] = float(returns.min())
    result["left_tail_p05"] = float(returns.quantile(0.05))
    return result


def component_turnover(
    result: overlay.OverlayResult,
    baseline_turnover: pd.Series,
    sleeve_annual_turnover: float,
    initial_sleeve_weight: float,
) -> pd.Series:
    """Allocation-weighted component turnover plus the top-level re-mix."""
    sleeve_at_start = result.holdings["sleeve"].shift(1)
    sleeve_at_start.iloc[0] = initial_sleeve_weight
    component = (
        (1.0 - sleeve_at_start) * baseline_turnover
        + sleeve_at_start * sleeve_annual_turnover / 252.0
    )
    return (component + result.remix_turnover).rename("turnover")


def _column_sharpes(values: np.ndarray, *, axis: int) -> np.ndarray:
    means = values.mean(axis=axis)
    deviations = values.std(axis=axis, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(
            deviations > 0.0,
            means / deviations * np.sqrt(stats.TRADING_DAYS),
            np.nan,
        )


def paired_inference(
    comparisons: list[tuple[float, str, pd.Series, pd.Series]],
    rf_daily: pd.Series | None = None,
) -> pd.DataFrame:
    """Common-seed vectorization under rf=0 or an aligned daily risk-free rate."""
    if not comparisons:
        raise ValueError("paired inference needs at least one comparison")
    index = comparisons[0][2].index
    candidates = np.column_stack(
        [candidate.reindex(index).to_numpy(dtype=float) for _, _, candidate, _ in comparisons]
    )
    references = np.column_stack(
        [reference.reindex(index).to_numpy(dtype=float) for _, _, _, reference in comparisons]
    )
    if not np.isfinite(candidates).all() or not np.isfinite(references).all():
        raise ValueError("paired inference inputs must be aligned and finite")
    aligned_rf: pd.Series | None = None
    if rf_daily is not None:
        aligned_rf = rf_daily.reindex(index)
        if not np.isfinite(aligned_rf.to_numpy(dtype=float)).all():
            raise ValueError("paired inference risk-free series must cover the index")
        risk_free = aligned_rf.to_numpy(dtype=float)[:, None]
        candidates = candidates - risk_free
        references = references - risk_free
    observed = _column_sharpes(candidates, axis=0) - _column_sharpes(
        references, axis=0
    )
    draws = np.empty((V17_BOOTSTRAP_RESAMPLES, len(comparisons)), dtype=float)
    rng = np.random.default_rng(V17_BOOTSTRAP_SEED)
    batch = max(
        1,
        min(
            V17_BOOTSTRAP_RESAMPLES,
            V17_BOOTSTRAP_INDEX_BUDGET // len(index),
        ),
    )
    completed = 0
    while completed < V17_BOOTSTRAP_RESAMPLES:
        size = min(batch, V17_BOOTSTRAP_RESAMPLES - completed)
        indices = stats.stationary_bootstrap_indices(
            len(index), V17_BOOTSTRAP_BLOCK, size, rng
        )
        for start in range(0, len(comparisons), V17_BOOTSTRAP_PAIR_CHUNK):
            stop = min(start + V17_BOOTSTRAP_PAIR_CHUNK, len(comparisons))
            candidate_draws = _column_sharpes(
                candidates[:, start:stop][indices], axis=1
            )
            reference_draws = _column_sharpes(
                references[:, start:stop][indices], axis=1
            )
            draws[completed : completed + size, start:stop] = (
                candidate_draws - reference_draws
            )
        completed += size

    rows: list[dict[str, object]] = []
    for column, (cost, challenger, candidate, reference) in enumerate(comparisons):
        finite = draws[np.isfinite(draws[:, column]), column]
        low, high = np.quantile(finite, [0.025, 0.975])
        centred = np.abs(finite - observed[column])
        p_value = (1 + int(np.sum(centred >= abs(observed[column])))) / (
            len(finite) + 1
        )
        hac = stats.ledoit_wolf_sharpe_test(
            candidate,
            reference,
            name_a=challenger,
            name_b="60_40_MKT_CASH",
            rf_daily=aligned_rf,
        )
        candidate_for_correlation = (
            candidate if aligned_rf is None else metrics.excess_returns(candidate, aligned_rf)
        )
        reference_for_correlation = (
            reference if aligned_rf is None else metrics.excess_returns(reference, aligned_rf)
        )
        rows.append(
            {
                "cost_bps": cost,
                "challenger": challenger,
                "sharpe_challenger": metrics.sharpe(candidate, rf_daily=aligned_rf),
                "sharpe_baseline": metrics.sharpe(reference, rf_daily=aligned_rf),
                "delta_sharpe": float(observed[column]),
                "bootstrap_ci_low": float(low),
                "bootstrap_ci_high": float(high),
                "bootstrap_p": float(p_value),
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "hac_method": hac.method,
                "correlation": float(
                    candidate_for_correlation.corr(reference_for_correlation)
                ),
            }
        )
    return pd.DataFrame(rows)


def select_training_weights(
    full_index: pd.DatetimeIndex,
    folds: list[sp.Split],
    candidate_returns: dict[float, pd.Series],
) -> tuple[pd.Series, pd.DataFrame]:
    """Select one registered weight per fold using training Sharpe only."""
    records: list[dict[str, object]] = []
    selections: dict[int, float] = {}
    for split in folds:
        train = split.train_index(full_index)
        scores = {
            weight: metrics.sharpe(series.reindex(train))
            for weight, series in candidate_returns.items()
        }
        chosen = min(scores, key=lambda weight: (-scores[weight], weight))
        selections[split.i] = chosen
        records.append(
            {
                "split": split.i,
                "train_start": split.train_start.date(),
                "train_end": split.train_end.date(),
                "validate_start": split.validate_start.date(),
                "validate_end": split.validate_end.date(),
                **{f"sr_s{weight:.2f}": score for weight, score in scores.items()},
                "selected_s": chosen,
            }
        )

    oos_dates: list[pd.Timestamp] = []
    oos_weights: list[float] = []
    formation = xsmom.formation_dates(full_index, "monthly")
    for split in folds:
        validation = split.validate_index(full_index)
        if not len(validation):
            continue
        dates = formation.intersection(validation)
        oos_dates.extend(cast(list[pd.Timestamp], dates.tolist()))
        oos_weights.extend([selections[split.i]] * len(dates))
    schedule = pd.Series(
        oos_weights,
        index=pd.DatetimeIndex(oos_dates),
        name="selected_s",
        dtype=float,
    )
    if schedule.index.has_duplicates or not schedule.index.is_monotonic_increasing:
        raise ValueError("selected sleeve-weight schedule is not sorted and unique")
    return schedule, pd.DataFrame(records)


def response_shape(deltas: pd.Series) -> str:
    values = deltas.to_numpy(dtype=float)
    differences = np.diff(values)
    tolerance = 1e-12
    if np.all(differences >= -tolerance) or np.all(differences <= tolerance):
        return "monotone"
    peak = int(np.argmax(values))
    rises = np.diff(values[: peak + 1])
    falls = np.diff(values[peak:])
    if peak not in (0, len(values) - 1) and np.all(rises >= -tolerance) and np.all(
        falls <= tolerance
    ):
        return "single-peaked"
    return "ragged/noise"


def write_ledger(
    path: Path,
    folds: list[sp.Split],
    full_index: pd.DatetimeIndex,
    returns_5: dict[float, pd.Series],
    turnovers: dict[float, pd.Series],
) -> tuple[int, int]:
    """Append the four registered cells once, resuming only after a lock."""
    expected: list[tuple[dict[str, object], int, pd.DatetimeIndex]] = []
    for split in folds:
        window = split.validate_index(full_index)
        if not len(window):
            continue
        for weight in V17_SLEEVE_WEIGHTS:
            config: dict[str, object] = {
                "study_version": V17_STUDY,
                "sleeve_weight": weight,
                "formation_frequency": "monthly",
                "selection_role": (
                    "fixed_primary" if weight == V17_PRIMARY_WEIGHT else "candidate"
                ),
            }
            expected.append((config, split.i, window))

    scheme = {
        "train_years": study.TRAIN_YEARS,
        "validate_years": study.VALIDATE_YEARS,
        "step_years": study.STEP_YEARS,
        "embargo_days": study.XSMOM_EMBARGO_DAYS,
    }
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(6):
        try:
            with TrialsLedger(path) as ledger:
                ledger._conn.execute("PRAGMA busy_timeout=30000")
                prior = ledger.trials(V17_STUDY)
                present = {
                    (str(row.config_hash), cast(int, row.split_index))
                    for row in prior.itertuples()
                }
                if prior.duplicated(["config_hash", "split_index"]).any():
                    raise RuntimeError("duplicate v17 ledger rows already exist")
                for config, split_index, window in expected:
                    key = (config_hash(config), split_index)
                    if key in present:
                        continue
                    weight = cast(float, config["sleeve_weight"])
                    part = returns_5[weight].reindex(window)
                    turn = turnovers[weight].reindex(window)
                    ledger.record(
                        V17_STUDY,
                        config,
                        metrics=metrics.summarize(part, turn),
                        cost_bps=V17_LEDGER_COST,
                        split_index=split_index,
                        window=f"{window[0].date()}..{window[-1].date()}",
                        split_scheme=scheme,
                        notes=(
                            "maintained 60/40 plus model-implied monthly stale-cohort "
                            "sleeve; top-level re-mix charged"
                        ),
                    )
                    present.add(key)
                rows = ledger.trials(V17_STUDY)
                return ledger.n_trials(V17_STUDY), len(rows)
        except sqlite3.OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            last_error = error
            time.sleep(0.25 * 2**attempt)
    raise RuntimeError("trials ledger remained locked after six retries") from last_error


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        type=Path,
        default=ROOT / "10_Portfolios_Prior_12_2_Daily_CSV.zip",
    )
    parser.add_argument(
        "--ledger", type=Path, default=ROOT / "journal" / "trials.db"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    deciles = xsmom.parse_daily_deciles(args.archive).dropna()
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
    if (lo, hi, n_bars, len(oos_index), len(folds)) != (
        V17_EXPECTED_START,
        V17_EXPECTED_END,
        V17_EXPECTED_BARS,
        V17_EXPECTED_BARS,
        V17_EXPECTED_FOLDS,
    ):
        raise ValueError(
            "v17 window mismatch: "
            f"got {lo.date()}..{hi.date()}, {n_bars}/{len(oos_index)} bars, "
            f"{len(folds)} folds"
        )

    monthly_dates = xsmom.formation_dates(oos_index, "monthly")
    oos_deciles = deciles.reindex(oos_index)
    sleeve_gross = xsmom.stale_cohort_returns(oos_deciles, monthly_dates)
    sleeve_turnover = xsmom.holding_period_turnover(oos_index, monthly_dates)

    control_weights: dict[str, dict[str, float]] = {
        "equal_weight_10": {column: 0.1 for column in xsmom.DECILE_COLUMNS},
        "MKT": {"MKT": 1.0},
        "60_40_MKT_CASH": {"MKT": 0.6, "CASH": 0.4},
    }
    control_gross: dict[str, pd.Series] = {}
    control_turnover: dict[str, pd.Series] = {}
    full_control_results: dict[str, backtest.BacktestResult] = {}
    for name, weights in control_weights.items():
        targets = fixed_targets(prices, weights)
        full_control_results[name] = backtest.run(prices, targets, cost_bps=0.0)
        stitched = study.stitch(prices, targets, folds)
        result = backtest.run(prices, stitched, cost_bps=0.0)
        control_gross[name] = result.returns.reindex(oos_index)
        control_turnover[name] = result.turnover.reindex(oos_index)

    rf_raw = cash.load_risk_free_daily(ROOT / "data")
    rf_daily, rf_diagnostics = cash.align_risk_free(rf_raw, oos_index)

    control_returns: dict[str, dict[float, pd.Series]] = {
        name: {
            cost: apply_outer_cost(gross, control_turnover[name], cost)
            for cost in V17_COST_LEVELS
        }
        for name, gross in control_gross.items()
    }
    sleeve_returns = {
        cost: xsmom.net_of_internal_cost(
            sleeve_gross, sleeve_turnover.total, cost
        )
        for cost in V17_COST_LEVELS
    }

    fixed_results: dict[float, dict[float, overlay.OverlayResult]] = {}
    fixed_turnover: dict[float, pd.Series] = {}
    for weight in V17_SLEEVE_WEIGHTS:
        fixed_results[weight] = {
            cost: overlay.mix_returns(
                control_returns["60_40_MKT_CASH"][cost],
                sleeve_returns[cost],
                weight,
                monthly_dates,
                cost_bps=cost,
            )
            for cost in V17_COST_LEVELS
        }
        fixed_turnover[weight] = component_turnover(
            fixed_results[weight][V17_LEDGER_COST],
            control_turnover["60_40_MKT_CASH"],
            sleeve_turnover.total,
            weight,
        )

    full_monthly_dates = xsmom.formation_dates(full_index, "monthly")
    full_sleeve_gross = xsmom.stale_cohort_returns(deciles, full_monthly_dates)
    full_sleeve_turnover = xsmom.holding_period_turnover(
        full_index, full_monthly_dates
    )
    full_sleeve_5 = xsmom.net_of_internal_cost(
        full_sleeve_gross, full_sleeve_turnover.total, V17_LEDGER_COST
    )
    full_baseline = full_control_results["60_40_MKT_CASH"]
    full_baseline_5 = apply_outer_cost(
        full_baseline.returns, full_baseline.turnover, V17_LEDGER_COST
    )
    training_candidates = {
        weight: overlay.mix_returns(
            full_baseline_5,
            full_sleeve_5,
            weight,
            full_monthly_dates,
            cost_bps=V17_LEDGER_COST,
        ).returns
        for weight in V17_SLEEVE_WEIGHTS
    }
    selected_schedule, selection_table = select_training_weights(
        full_index, folds, training_candidates
    )
    if not selected_schedule.index.equals(monthly_dates):
        raise ValueError("selected and OOS formation calendars do not match")

    selected_results = {
        cost: overlay.mix_returns(
            control_returns["60_40_MKT_CASH"][cost],
            sleeve_returns[cost],
            selected_schedule,
            monthly_dates,
            cost_bps=cost,
        )
        for cost in V17_COST_LEVELS
    }
    selected_turnover = component_turnover(
        selected_results[V17_LEDGER_COST],
        control_turnover["60_40_MKT_CASH"],
        sleeve_turnover.total,
        float(selected_schedule.iloc[0]),
    )

    print("=== SLEEVE-V17-OVERLAY: DATA AND FROZEN DESIGN ===")
    print(
        f"archive={args.archive}\n"
        f"OOS={lo.date()}..{hi.date()} bars={len(oos_index)} folds={len(folds)}\n"
        f"fixed_sleeve_weights={V17_SLEEVE_WEIGHTS}; primary_s=0.10\n"
        f"costs={V17_COST_LEVELS}; ledger_cost={V17_LEDGER_COST}bps\n"
        f"risk_free={rf_diagnostics}"
    )
    print(
        "A is fixed s=0.10 and is the primary no-free-parameter result. B is a "
        "secondary four-cell best-in-train selection. If A fails and B passes, "
        "the study fails."
    )
    print(
        "B operational rule, recorded before execution: maximize annualized rf=0 "
        "training Sharpe at the 5bps ledger cost; exact ties choose smaller s; a "
        "new choice takes effect at the next monthly formation."
    )
    print(
        "The sleeve gross path and internal turnover are MODEL-IMPLIED, not "
        "observed. A stale sub-cohort is assumed exchangeable with the current "
        "French decile into which its latent rank migrated."
    )

    print("\n=== V15 MONTHLY REPRODUCTION CHECK ===")
    print(
        f"formation_events={int((monthly_dates < oos_index[-1]).sum())}; "
        f"internal_turnover={sleeve_turnover.internal:.6f}; "
        f"initial_purchase={sleeve_turnover.initial_purchase:.6f}; "
        f"total={sleeve_turnover.total:.6f}; "
        f"gross_sharpe={metrics.sharpe(sleeve_gross):.6f}; "
        f"10bps_sharpe={metrics.sharpe(sleeve_returns[10.0]):.6f}"
    )

    print("\n=== B: BEST-IN-TRAIN SELECTIONS (SECONDARY) ===")
    print(selection_table.round(6).to_string(index=False))
    print("\nSelection counts:")
    print(
        selection_table["selected_s"]
        .value_counts()
        .reindex(V17_SLEEVE_WEIGHTS, fill_value=0)
        .rename_axis("sleeve_weight")
        .rename("folds")
        .to_string()
    )

    named_returns: dict[str, dict[float, pd.Series]] = {
        "60_40_MKT_CASH": control_returns["60_40_MKT_CASH"],
        **{
            f"overlay_s{weight:.2f}": {
                cost: fixed_results[weight][cost].returns
                for cost in V17_COST_LEVELS
            }
            for weight in V17_SLEEVE_WEIGHTS
        },
        "B_selected": {
            cost: selected_results[cost].returns for cost in V17_COST_LEVELS
        },
        "monthly_sleeve": sleeve_returns,
        "equal_weight_10": control_returns["equal_weight_10"],
        "MKT": control_returns["MKT"],
    }
    named_turnover: dict[str, pd.Series] = {
        "60_40_MKT_CASH": control_turnover["60_40_MKT_CASH"],
        **{
            f"overlay_s{weight:.2f}": fixed_turnover[weight]
            for weight in V17_SLEEVE_WEIGHTS
        },
        "B_selected": selected_turnover,
        "monthly_sleeve": pd.Series(
            sleeve_turnover.total / 252.0, index=oos_index, name="turnover"
        ),
        "equal_weight_10": control_turnover["equal_weight_10"],
        "MKT": control_turnover["MKT"],
    }

    print("\n=== PERFORMANCE AT 0/5/10/25/50 BPS ===")
    performance_rows: list[dict[str, object]] = []
    for cost in V17_COST_LEVELS:
        for name, by_cost in named_returns.items():
            performance_rows.append(
                {
                    "cost_bps": cost,
                    "series": name,
                    **result_summary(
                        by_cost[cost], named_turnover[name], rf_daily
                    ),
                }
            )
    performance = pd.DataFrame(performance_rows)
    print(performance.round(6).to_string(index=False))

    print("\n=== FULL-WINDOW PAIRED INFERENCE VS 60/40 AT EVERY COST ===")
    inference = paired_inference(
        [
            (
                cost,
                f"overlay_s{weight:.2f}",
                fixed_results[weight][cost].returns,
                control_returns["60_40_MKT_CASH"][cost],
            )
            for cost in V17_COST_LEVELS
            for weight in V17_SLEEVE_WEIGHTS
        ]
        + [
            (
                cost,
                "B_selected",
                selected_results[cost].returns,
                control_returns["60_40_MKT_CASH"][cost],
            )
            for cost in V17_COST_LEVELS
        ]
    )
    print(inference.round(6).to_string(index=False))

    print("\n=== FIXED ERA SPLIT: PAIRED INFERENCE AT EVERY COST ===")
    era_rows: list[dict[str, object]] = []
    for era, date_slice in [
        ("1932-1979", slice(None, "1979-12-31")),
        ("1980-2026", slice("1980-01-01", None)),
    ]:
        era_table = paired_inference(
            [
                (
                    cost,
                    f"overlay_s{weight:.2f}",
                    fixed_results[weight][cost].returns.loc[date_slice],
                    control_returns["60_40_MKT_CASH"][cost].loc[date_slice],
                )
                for cost in V17_COST_LEVELS
                for weight in V17_SLEEVE_WEIGHTS
            ]
            + [
                (
                    cost,
                    "B_selected",
                    selected_results[cost].returns.loc[date_slice],
                    control_returns["60_40_MKT_CASH"][cost].loc[date_slice],
                )
                for cost in V17_COST_LEVELS
            ]
        )
        era_rows.extend(
            {"era": era, **row}
            for row in cast(list[dict[str, object]], era_table.to_dict("records"))
        )
    era_inference = pd.DataFrame(era_rows)
    print(era_inference.round(6).to_string(index=False))

    print("\n=== DECADE SUB-PERIODS AT 10 BPS ===")
    decade_rows: list[dict[str, object]] = []
    for name, by_cost in named_returns.items():
        table = metrics.by_subperiod(by_cost[10.0], breaks=V17_DECADE_BREAKS)
        for period, row in table.iterrows():
            decade_rows.append(
                {
                    "series": name,
                    "period": period,
                    **cast(dict[str, object], row.to_dict()),
                }
            )
    print(pd.DataFrame(decade_rows).round(6).to_string(index=False))

    print("\n=== TAIL-AWARE POINT METRICS AT EVERY COST ===")
    tail_rows: list[dict[str, object]] = []
    for cost in V17_COST_LEVELS:
        for name, by_cost in named_returns.items():
            tail_rows.append(
                {"cost_bps": cost, "series": name, **tailrisk.summarize(by_cost[cost])}
            )
    tail_points = pd.DataFrame(tail_rows)
    print(tail_points.round(6).to_string(index=False))

    print("\n=== 10 BPS TAIL-METRIC 95% BLOCK-BOOTSTRAP INTERVALS ===")
    tail_interval_rows: list[dict[str, object]] = []
    tail_names = [
        "60_40_MKT_CASH",
        *[f"overlay_s{weight:.2f}" for weight in V17_SLEEVE_WEIGHTS],
        "B_selected",
    ]
    for number, name in enumerate(tail_names):
        print(f"bootstrap {number + 1}/{len(tail_names)}: {name}", flush=True)
        intervals = tailrisk.bootstrap_intervals(
            named_returns[name][10.0],
            n_resamples=V17_BOOTSTRAP_RESAMPLES,
            block_length=V17_BOOTSTRAP_BLOCK,
            seed=V17_BOOTSTRAP_SEED,
        )
        for record in cast(
            list[dict[str, object]], intervals.to_dict("records")
        ):
            tail_interval_rows.append({"series": name, **record})
    print(pd.DataFrame(tail_interval_rows).round(6).to_string(index=False))

    print("\n=== DIVERSIFICATION DIAGNOSTIC AT 10 BPS ===")
    components = pd.DataFrame(
        {
            "baseline": control_returns["60_40_MKT_CASH"][10.0],
            "sleeve": sleeve_returns[10.0],
        }
    )
    diversification_rows = [
        {
            "sleeve_weight": weight,
            **diversification.diversification_report(
                components,
                pd.Series({"baseline": 1.0 - weight, "sleeve": weight}),
                label=f"s={weight:.2f}",
            ),
        }
        for weight in V17_SLEEVE_WEIGHTS
    ]
    diversification_table = pd.DataFrame(diversification_rows)
    print(diversification_table.round(6).to_string(index=False))
    print(
        "Diagnostics use 10bps component-net returns. Correlation is a property "
        "of the two return streams and therefore repeats across fixed weights."
    )

    ten_bps_fixed = inference[
        (inference["cost_bps"] == 10.0)
        & inference["challenger"].str.startswith("overlay_s")
    ].copy()
    ten_bps_fixed["sleeve_weight"] = ten_bps_fixed["challenger"].str[-4:].astype(float)
    curve = ten_bps_fixed.set_index("sleeve_weight")["delta_sharpe"].reindex(
        V17_SLEEVE_WEIGHTS
    )
    shape = response_shape(curve)
    print("\n=== FIXED-WEIGHT RESPONSE CURVE AT 10 BPS ===")
    print(ten_bps_fixed.round(6).to_string(index=False))
    print(f"response_shape={shape}")
    if shape == "ragged/noise":
        print("The adjacent-weight response is ragged and is therefore called noise.")

    primary_row = inference[
        (inference["cost_bps"] == 10.0)
        & (inference["challenger"] == "overlay_s0.10")
    ].iloc[0]
    post_primary = era_inference[
        (era_inference["era"] == "1980-2026")
        & (era_inference["cost_bps"] == 10.0)
        & (era_inference["challenger"] == "overlay_s0.10")
    ].iloc[0]
    primary_tail = tail_points[
        (tail_points["cost_bps"] == 10.0)
        & (tail_points["series"] == "overlay_s0.10")
    ].iloc[0]
    baseline_tail = tail_points[
        (tail_points["cost_bps"] == 10.0)
        & (tail_points["series"] == "60_40_MKT_CASH")
    ].iloc[0]
    primary_max_drawdown = metrics.max_drawdown(
        fixed_results[V17_PRIMARY_WEIGHT][10.0].returns
    )
    baseline_max_drawdown = metrics.max_drawdown(
        control_returns["60_40_MKT_CASH"][10.0]
    )
    c1 = bool(primary_row["bootstrap_ci_low"] > 0.0)
    c2_drawdown = abs(primary_max_drawdown) <= 1.25 * abs(baseline_max_drawdown)
    c2_cvar95 = float(primary_tail["cvar_95"]) <= 1.10 * float(
        baseline_tail["cvar_95"]
    )
    c2_cvar99 = float(primary_tail["cvar_99"]) <= 1.10 * float(
        baseline_tail["cvar_99"]
    )
    c2 = bool(c2_drawdown and c2_cvar95 and c2_cvar99)
    c3 = bool(post_primary["bootstrap_ci_low"] > 0.0)

    ledger_returns = {
        weight: fixed_results[weight][V17_LEDGER_COST].returns
        for weight in V17_SLEEVE_WEIGHTS
    }
    distinct_trials, ledger_rows = write_ledger(
        args.ledger, folds, full_index, ledger_returns, fixed_turnover
    )
    if (distinct_trials, ledger_rows) != (
        len(V17_SLEEVE_WEIGHTS),
        len(V17_SLEEVE_WEIGHTS) * V17_EXPECTED_FOLDS,
    ):
        raise ValueError(
            f"ledger accounting mismatch: {distinct_trials} configs, "
            f"{ledger_rows} rows"
        )

    print("\n=== TRIALS LEDGER AND DEFLATED SHARPE ===")
    print(
        f"study={V17_STUDY} distinct_configs={distinct_trials} rows={ledger_rows}"
    )
    primary_dsr = dfl.deflated_sharpe(
        fixed_results[V17_PRIMARY_WEIGHT][V17_LEDGER_COST].returns,
        1,
        trial_sharpes=pd.Series(
            [metrics.sharpe(fixed_results[V17_PRIMARY_WEIGHT][V17_LEDGER_COST].returns)]
        ),
    )
    selected_dsr = dfl.deflated_sharpe(
        selected_results[V17_LEDGER_COST].returns,
        distinct_trials,
        trial_sharpes=pd.Series(
            [
                metrics.sharpe(fixed_results[weight][V17_LEDGER_COST].returns)
                for weight in V17_SLEEVE_WEIGHTS
            ]
        ),
    )
    print(f"\nA fixed s=0.10 (no selection):\n{dfl.report(primary_dsr)}")
    print(f"\nB selected (four-cell selection):\n{dfl.report(selected_dsr)}")
    print(
        "Effective breadth note: literal breadth for B is four closely related "
        "sleeve weights, so it overstates independent breadth. A has no fitted "
        "parameter and its SR0=0 deflation is vacuous."
    )

    selected_row = inference[
        (inference["cost_bps"] == 10.0)
        & (inference["challenger"] == "B_selected")
    ].iloc[0]
    b_pass = bool(selected_row["bootstrap_ci_low"] > 0.0)
    mechanism = diversification_table.loc[
        diversification_table["sleeve_weight"] == V17_PRIMARY_WEIGHT,
        "effective_bets",
    ].iloc[0]
    print("\n=== PRE-REGISTERED OUTCOME ===")
    print(
        f"C1_improves_risk_adjusted_return={c1}; "
        f"delta={primary_row['delta_sharpe']:+.6f}; "
        f"bootstrap_CI=[{primary_row['bootstrap_ci_low']:+.6f}, "
        f"{primary_row['bootstrap_ci_high']:+.6f}]"
    )
    print(
        f"C2_tail_preserved={c2}; drawdown_clause={c2_drawdown}; "
        f"CVaR95_clause={c2_cvar95}; CVaR99_clause={c2_cvar99}; "
        f"maxDD_overlay/base={primary_max_drawdown:.6f}/{baseline_max_drawdown:.6f}; "
        f"CVaR95_overlay/base={float(primary_tail['cvar_95']):.6f}/"
        f"{float(baseline_tail['cvar_95']):.6f}; "
        f"CVaR99_overlay/base={float(primary_tail['cvar_99']):.6f}/"
        f"{float(baseline_tail['cvar_99']):.6f}"
    )
    print(
        f"C3_survives_post_1980={c3}; delta={post_primary['delta_sharpe']:+.6f}; "
        f"bootstrap_CI=[{post_primary['bootstrap_ci_low']:+.6f}, "
        f"{post_primary['bootstrap_ci_high']:+.6f}]"
    )
    print(
        f"A_primary_passes_all_three={c1 and c2 and c3}; "
        f"B_selected_C1_passes={b_pass}; response_shape={shape}; "
        f"primary_effective_bets={mechanism:.6f}"
    )
    if not c1 and b_pass:
        print("A failed and B passed: the study failed.")
    elif not (c1 and c2 and c3):
        print("A did not pass all three primary criteria: the study failed.")
    else:
        print("A passed all three pre-registered criteria; nothing is promoted.")
    if float(mechanism) <= 1.0 + 1e-6 and float(primary_row["delta_sharpe"]) > 0:
        print(
            "Sharpe improved without an effective-bets increase; the mechanism is "
            "not diversification and requires separate explanation."
        )
    else:
        print(
            "The effective-bets diagnostic identifies whether any Sharpe change is "
            "consistent with diversification; it does not establish causality."
        )
    print(
        "\nFinal sleeve-v17-overlay study. Nothing promoted. "
        "Factual journaled results follow."
    )


if __name__ == "__main__":
    main()
