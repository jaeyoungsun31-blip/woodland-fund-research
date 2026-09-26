"""Execute the pre-registered xsmom-v15-holding study."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, cash, metrics, stats, tailrisk, xsmom
from woodland.config import ROOT
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.study import stitch

STUDY = "xsmom-v15-holding"
FREQUENCIES = ["monthly", "quarterly", "semiannual", "annual"]
CONTROLS = ["equal_weight_10", "MKT", "60_40_MKT_CASH"]
STRESS_COSTS = [0.0, 5.0, 10.0, 25.0, 50.0]
LEDGER_COST = 5.0
EMBARGO_DAYS = 252
EXPECTED_BARS = 24_434
EXPECTED_FOLDS = 94
EXPECTED_START = pd.Timestamp("1932-09-06")
EXPECTED_END = pd.Timestamp("2026-06-30")
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_BLOCK = 21
BOOTSTRAP_SEED = 0
BOOTSTRAP_INDEX_BUDGET = 3_000_000
BOOTSTRAP_PAIR_CHUNK = 2
DECADE_BREAKS = [f"{year}-01-01" for year in range(1940, 2030, 10)]

pd.set_option("display.width", 280)
pd.set_option("display.max_columns", 100)
pd.set_option("display.max_rows", 800)


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return xsmom.formation_dates(index, "monthly")


def fixed_targets(prices: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    targets = pd.DataFrame(np.nan, index=prices.index, columns=prices.columns)
    for date in month_ends(pd.DatetimeIndex(prices.index)):
        targets.loc[date, list(weights)] = list(weights.values())
    return targets


def oos_bounds(
    index: pd.DatetimeIndex, folds: list[sp.Split]
) -> tuple[pd.Timestamp, pd.Timestamp]:
    windows = [split.validate_index(index) for split in folds]
    usable = [window for window in windows if len(window)]
    return min(window[0] for window in usable), max(window[-1] for window in usable)


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
    out = metrics.summarize(returns, turnover, rf_daily=rf_daily)
    out["worst_day"] = float(returns.min())
    out["left_tail_p05"] = float(returns.quantile(0.05))
    return out


def crossover_cost(
    candidate_gross: pd.Series,
    candidate_turnover: float,
    ew_gross: pd.Series,
    ew_turnover: pd.Series,
) -> float | None:
    def difference(cost: float) -> float:
        candidate = xsmom.net_of_internal_cost(
            candidate_gross, candidate_turnover, cost
        )
        ew = apply_outer_cost(ew_gross, ew_turnover, cost)
        return metrics.sharpe(candidate) - metrics.sharpe(ew)

    if difference(0.0) <= 0.0:
        return 0.0
    if difference(500.0) > 0.0:
        return None
    low, high = 0.0, 500.0
    while high - low > 0.001:
        midpoint = (low + high) / 2.0
        if difference(midpoint) > 0.0:
            low = midpoint
        else:
            high = midpoint
    return high


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
    comparisons: list[tuple[float, str, str, pd.Series, pd.Series]],
    rf_daily: pd.Series | None = None,
) -> pd.DataFrame:
    """Common-seed vectorization under rf=0 or an aligned daily risk-free rate."""
    if not comparisons:
        raise ValueError("paired inference needs at least one comparison")
    index = comparisons[0][3].index
    candidates = np.column_stack(
        [candidate.reindex(index).to_numpy(dtype=float) for *_, candidate, _ in comparisons]
    )
    references = np.column_stack(
        [reference.reindex(index).to_numpy(dtype=float) for *_, reference in comparisons]
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
    draws = np.empty((BOOTSTRAP_RESAMPLES, len(comparisons)), dtype=float)
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    batch = max(1, min(BOOTSTRAP_RESAMPLES, BOOTSTRAP_INDEX_BUDGET // len(index)))
    completed = 0
    while completed < BOOTSTRAP_RESAMPLES:
        size = min(batch, BOOTSTRAP_RESAMPLES - completed)
        indices = stats.stationary_bootstrap_indices(
            len(index), BOOTSTRAP_BLOCK, size, rng
        )
        for start in range(0, len(comparisons), BOOTSTRAP_PAIR_CHUNK):
            stop = min(start + BOOTSTRAP_PAIR_CHUNK, len(comparisons))
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
    for column, (cost, challenger, reference, candidate, benchmark) in enumerate(
        comparisons
    ):
        finite = draws[np.isfinite(draws[:, column]), column]
        low, high = np.quantile(finite, [0.025, 0.975])
        centred = np.abs(finite - observed[column])
        p_value = (1 + int(np.sum(centred >= abs(observed[column])))) / (
            len(finite) + 1
        )
        hac = stats.ledoit_wolf_sharpe_test(
            candidate,
            benchmark,
            name_a=challenger,
            name_b=reference,
            rf_daily=aligned_rf,
        )
        candidate_for_correlation = (
            candidate if aligned_rf is None else metrics.excess_returns(candidate, aligned_rf)
        )
        reference_for_correlation = (
            benchmark if aligned_rf is None else metrics.excess_returns(benchmark, aligned_rf)
        )
        rows.append(
            {
                "cost_bps": cost,
                "challenger": challenger,
                "reference": reference,
                "sharpe_challenger": metrics.sharpe(candidate, rf_daily=aligned_rf),
                "sharpe_reference": metrics.sharpe(benchmark, rf_daily=aligned_rf),
                "delta_sharpe": float(observed[column]),
                "bootstrap_ci_low": float(low),
                "bootstrap_ci_high": float(high),
                "bootstrap_p": float(p_value),
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "hac_lags": hac.method,
                "correlation": float(
                    candidate_for_correlation.corr(reference_for_correlation)
                ),
            }
        )
    return pd.DataFrame(rows)


def write_ledger(
    ledger_path: Path,
    folds: list[sp.Split],
    returns_5: dict[str, pd.Series],
    turnover: dict[str, pd.Series],
    index: pd.DatetimeIndex,
) -> tuple[int, int]:
    scheme = {
        "train_years": 5,
        "validate_years": 1,
        "step_years": 1,
        "embargo_days": EMBARGO_DAYS,
    }
    with TrialsLedger(ledger_path) as ledger:
        if not ledger.trials(STUDY).empty:
            raise RuntimeError(
                f"ledger already contains {STUDY}; refusing to duplicate rows"
            )
        for split_index, split in enumerate(folds):
            window = split.validate_index(index)
            if not len(window):
                continue
            window_label = f"{window[0].date()}..{window[-1].date()}"
            for name, series in returns_5.items():
                part = series.reindex(window).dropna()
                turn = turnover[name].reindex(part.index)
                config = {
                    "study_version": STUDY,
                    "configuration": name,
                    "curve_selection": "none",
                }
                if name in FREQUENCIES:
                    config["formation_frequency"] = name
                    notes = "model-implied stale-cohort returns and turnover"
                else:
                    notes = "unchanged v13 market control"
                ledger.record(
                    STUDY,
                    config,
                    metrics=metrics.summarize(part, turn),
                    cost_bps=LEDGER_COST,
                    split_index=split_index,
                    window=window_label,
                    split_scheme=scheme,
                    notes=notes,
                )
        return ledger.n_trials(STUDY), len(ledger.trials(STUDY))


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
    folds = sp.make_splits(
        full_index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=EMBARGO_DAYS,
    )
    lo, hi = oos_bounds(full_index, folds)
    oos_index = pd.DatetimeIndex(prices.loc[lo:hi].index)
    if (lo, hi, len(oos_index), len(folds)) != (
        EXPECTED_START,
        EXPECTED_END,
        EXPECTED_BARS,
        EXPECTED_FOLDS,
    ):
        raise ValueError(
            "v15 window mismatch: "
            f"got {lo.date()}..{hi.date()}, {len(oos_index)} bars, {len(folds)} folds"
        )

    oos_deciles = deciles.reindex(oos_index)
    gross: dict[str, pd.Series] = {}
    turnover_components: dict[str, xsmom.HoldingTurnover] = {}
    turnover: dict[str, pd.Series] = {}
    formation_counts: dict[str, int] = {}
    for frequency in FREQUENCIES:
        dates = xsmom.formation_dates(oos_index, frequency)
        gross[frequency] = xsmom.stale_cohort_returns(oos_deciles, dates)
        components = xsmom.holding_period_turnover(oos_index, dates)
        turnover_components[frequency] = components
        turnover[frequency] = pd.Series(
            components.total / 252.0,
            index=oos_index,
            name="turnover",
        )
        formation_counts[frequency] = int((dates < oos_index[-1]).sum())

    control_weights: dict[str, dict[str, float]] = {
        "equal_weight_10": {column: 0.1 for column in xsmom.DECILE_COLUMNS},
        "MKT": {"MKT": 1.0},
        "60_40_MKT_CASH": {"MKT": 0.6, "CASH": 0.4},
    }
    for name, weights in control_weights.items():
        targets = stitch(prices, fixed_targets(prices, weights), folds)
        result = backtest.run(prices, targets, cost_bps=0.0)
        gross[name] = result.returns.reindex(oos_index)
        turnover[name] = result.turnover.reindex(oos_index)

    rf_raw = cash.load_risk_free_daily(ROOT / "data")
    rf_daily, rf_diagnostics = cash.align_risk_free(rf_raw, oos_index)

    returns: dict[str, dict[float, pd.Series]] = {}
    for name in gross:
        if name in FREQUENCIES:
            annual_turnover = turnover_components[name].total
            returns[name] = {
                cost: xsmom.net_of_internal_cost(
                    gross[name], annual_turnover, cost
                )
                for cost in STRESS_COSTS
            }
        else:
            returns[name] = {
                cost: apply_outer_cost(gross[name], turnover[name], cost)
                for cost in STRESS_COSTS
            }

    print("=== XSMOM-V15-HOLDING: DATA AND FROZEN DESIGN ===")
    print(
        f"archive={args.archive}\n"
        f"OOS={lo.date()}..{hi.date()} bars={len(oos_index)} folds={len(folds)}\n"
        f"frequencies={FREQUENCIES}; curve_selection=NONE\n"
        f"rank_rho={xsmom.RANK_CORRELATION:.9f}; "
        f"quadrature_nodes={xsmom.QUADRATURE_NODES}\n"
        f"risk_free={rf_diagnostics}"
    )
    print(
        "All four top-three paths are MODEL-IMPLIED STALE COHORTS, not observed "
        "stock portfolios and not reproductions of v13's daily-reconstituted top3."
    )
    print(
        "The single registered parameter is reported as a CURVE. No frequency is "
        "selected or called best; any later choice must enter a new trial count."
    )

    print("\n=== MODEL-IMPLIED HOLDING TURNOVER CURVE ===")
    turnover_rows: list[dict[str, object]] = []
    for frequency in FREQUENCIES:
        component = turnover_components[frequency]
        turnover_rows.append(
            {
                "frequency": frequency,
                "formation_events": formation_counts[frequency],
                "internal_model_implied": component.internal,
                "initial_outer_annualized": component.initial_purchase,
                "total_charged_turnover": component.total,
                "reduction_vs_v13_21_736x": 1.0 - component.total / 21.736,
            }
        )
    print(pd.DataFrame(turnover_rows).round(6).to_string(index=False))
    print(
        "Turnover caveat (verbatim): it is an estimate, not observed, and it omits "
        "size dispersion, entry/exit, breakpoint jumps, impact, borrow and capacity, "
        "all of which push true cost up."
    )
    print(
        "V15 also models the stale cohort's gross return through exchangeable "
        "current-decile returns. Constituent-level data is required for validation."
    )

    performance_rows: list[dict[str, object]] = []
    for cost in STRESS_COSTS:
        for name in gross:
            performance_rows.append(
                {
                    "cost_bps": cost,
                    "series": name,
                    **result_summary(returns[name][cost], turnover[name], rf_daily),
                }
            )
    performance = pd.DataFrame(performance_rows)
    print("\n=== PERFORMANCE AT 0/5/10/25/50 BPS ===")
    print(performance.round(6).to_string(index=False))

    crossover_rows: list[dict[str, object]] = []
    for frequency in FREQUENCIES:
        crossing = crossover_cost(
            gross[frequency],
            turnover_components[frequency].total,
            gross["equal_weight_10"],
            turnover["equal_weight_10"],
        )
        gross_delta = metrics.sharpe(gross[frequency]) - metrics.sharpe(
            gross["equal_weight_10"]
        )
        crossover_rows.append(
            {
                "frequency": frequency,
                "gross_sharpe": metrics.sharpe(gross[frequency]),
                "gross_delta_vs_EW10": gross_delta,
                "cost_crossover_bps": math.inf if crossing is None else crossing,
                "clears_25bps": crossing is None or crossing >= 25.0,
                "clears_50bps": crossing is None or crossing >= 50.0,
            }
        )
    crossovers = pd.DataFrame(crossover_rows)
    print("\n=== HEADLINE COST CROSSOVER VS EQUAL-WEIGHT-10 ===")
    print(crossovers.round(6).to_string(index=False))

    print("\n=== FULL-WINDOW PAIRED INFERENCE AT EVERY COST ===")
    inference = paired_inference(
        [
            (
                cost,
                frequency,
                reference,
                returns[frequency][cost],
                returns[reference][cost],
            )
            for cost in STRESS_COSTS
            for frequency in FREQUENCIES
            for reference in ["equal_weight_10", "MKT"]
        ]
    )
    print(inference.round(6).to_string(index=False))

    print("\n=== PRE/POST-1980 PAIRED INFERENCE AT EVERY COST ===")
    era_rows: list[dict[str, object]] = []
    for era, date_slice in [
        ("1932-1979", slice(None, "1979-12-31")),
        ("1980-2026", slice("1980-01-01", None)),
    ]:
        era_table = paired_inference(
            [
                (
                    cost,
                    frequency,
                    reference,
                    returns[frequency][cost].loc[date_slice],
                    returns[reference][cost].loc[date_slice],
                )
                for cost in STRESS_COSTS
                for frequency in FREQUENCIES
                for reference in ["equal_weight_10", "MKT"]
            ]
        )
        era_rows.extend(
            {"era": era, **record}
            for record in cast(list[dict[str, object]], era_table.to_dict("records"))
        )
    print(pd.DataFrame(era_rows).round(6).to_string(index=False))

    print("\n=== DECADE SUB-PERIODS AT 10 BPS ===")
    subperiod_rows: list[dict[str, object]] = []
    for name, cost_returns in returns.items():
        table = metrics.by_subperiod(cost_returns[10.0], breaks=DECADE_BREAKS)
        for period, row in table.iterrows():
            subperiod = cast(dict[str, object], row.to_dict())
            subperiod_rows.append(
                {"series": name, "period": period, **subperiod}
            )
    print(pd.DataFrame(subperiod_rows).round(6).to_string(index=False))

    print("\n=== TAIL-AWARE POINT METRICS AT EVERY COST ===")
    tail_point_rows: list[dict[str, object]] = []
    for cost in STRESS_COSTS:
        for name in returns:
            tail_point_rows.append(
                {
                    "cost_bps": cost,
                    "series": name,
                    **tailrisk.summarize(returns[name][cost]),
                }
            )
    print(pd.DataFrame(tail_point_rows).round(6).to_string(index=False))

    print("\n=== 10 BPS TAIL-METRIC 95% BLOCK-BOOTSTRAP INTERVALS ===")
    tail_interval_rows: list[dict[str, object]] = []
    for number, name in enumerate(returns):
        print(f"bootstrap {number + 1}/{len(returns)}: {name}", flush=True)
        intervals = tailrisk.bootstrap_intervals(
            returns[name][10.0],
            n_resamples=BOOTSTRAP_RESAMPLES,
            block_length=BOOTSTRAP_BLOCK,
            seed=BOOTSTRAP_SEED,
        )
        interval_records = cast(
            list[dict[str, object]], intervals.to_dict("records")
        )
        for interval_record in interval_records:
            tail_interval_rows.append({"series": name, **interval_record})
    print(pd.DataFrame(tail_interval_rows).round(6).to_string(index=False))

    ledger_returns = {name: values[LEDGER_COST] for name, values in returns.items()}
    distinct_trials, ledger_rows = write_ledger(
        args.ledger, folds, ledger_returns, turnover, full_index
    )
    if (distinct_trials, ledger_rows) != (7, 658):
        raise ValueError(
            f"ledger accounting mismatch: {distinct_trials} configs, {ledger_rows} rows"
        )
    print("\n=== TRIALS LEDGER AND DEFLATED SHARPE ===")
    print(f"study={STUDY} distinct_configs={distinct_trials} rows={ledger_rows}")
    trial_sharpes = pd.Series(
        [metrics.sharpe(returns[name][LEDGER_COST]) for name in returns], dtype=float
    )
    for frequency in FREQUENCIES:
        dsr = dfl.deflated_sharpe(
            returns[frequency][LEDGER_COST],
            7,
            trial_sharpes=trial_sharpes,
        )
        print(f"\n{frequency}:\n{dfl.report(dsr)}")
    print(
        "Effective breadth note: literal breadth is seven return-bearing "
        "configurations. The four holding frequencies are highly dependent, as are "
        "the three market controls, so literal breadth materially overstates "
        "independent effective breadth. DSR cannot select a point from the curve."
    )

    any_gross = bool((crossovers["gross_delta_vs_EW10"] > 0.0).any())
    any_25 = bool(crossovers["clears_25bps"].any())
    any_50 = bool(crossovers["clears_50bps"].any())
    print("\n=== FROZEN HEADLINE ===")
    print(
        f"gross_signal_survives_any_frequency={any_gross}; "
        f"crossover_clears_25bps_any_frequency={any_25}; "
        f"crossover_clears_50bps_any_frequency={any_50}"
    )
    print(
        "Crossing a planning cost threshold is not proof of tradeability: both the "
        "stale-cohort gross path and its turnover remain model-implied."
    )
    print(
        "\nFinal xsmom-v15-holding study. Nothing promoted. "
        "Factual journaled results follow."
    )


if __name__ == "__main__":
    main()
