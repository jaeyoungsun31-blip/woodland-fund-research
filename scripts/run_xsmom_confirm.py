"""Execute the pre-registered xsmom-v13-confirm study.

The runner confirms one fixed challenger (top-three prior-return deciles),
models otherwise-unobservable constituent migration costs, runs the fixed
portfolio-level Fama-MacBeth test, and reports tail-aware uncertainty.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import NormalDist
from typing import cast

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, cash, metrics, stats, tailrisk, xsmom, xsreg
from woodland.config import ROOT
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.study import stitch

STUDY = "xsmom-v13-confirm"
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
V11_SPREAD = 0.138
DECADE_BREAKS = [f"{year}-01-01" for year in range(1940, 2030, 10)]

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 500)


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(index.to_series().groupby(index.to_period("M")).max())


def fixed_targets(
    prices: pd.DataFrame, weights: dict[str, float]
) -> pd.DataFrame:
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


def combined_cost_return(
    gross: pd.Series,
    outer_turnover: pd.Series,
    internal_turnover: float,
    cost_bps: float,
) -> pd.Series:
    outer_net = apply_outer_cost(gross, outer_turnover, cost_bps)
    return xsmom.net_of_internal_cost(outer_net, internal_turnover, cost_bps)


def result_summary(
    returns: pd.Series, turnover: pd.Series, rf_daily: pd.Series
) -> dict[str, float | int]:
    out = metrics.summarize(returns, turnover, rf_daily=rf_daily)
    out["worst_day"] = float(returns.min())
    out["left_tail_p05"] = float(returns.quantile(0.05))
    return out


def crossover_cost(
    top_gross: pd.Series,
    top_outer: pd.Series,
    top_internal: float,
    ew_gross: pd.Series,
    ew_outer: pd.Series,
) -> float | None:
    def difference(cost: float) -> float:
        top = combined_cost_return(top_gross, top_outer, top_internal, cost)
        ew = combined_cost_return(ew_gross, ew_outer, 0.0, cost)
        return metrics.sharpe(top) - metrics.sharpe(ew)

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
) -> pd.DataFrame:
    """Exact common-seed vectorization of the registered paired bootstrap."""
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
            candidate, benchmark, name_a=challenger, name_b=reference
        )
        rows.append(
            {
                "cost_bps": cost,
                "challenger": challenger,
                "reference": reference,
                "sharpe_challenger": metrics.sharpe(candidate),
                "sharpe_reference": metrics.sharpe(benchmark),
                "delta_sharpe": float(observed[column]),
                "bootstrap_ci_low": float(low),
                "bootstrap_ci_high": float(high),
                "bootstrap_p": float(p_value),
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "hac_lags": hac.method,
                "correlation": float(candidate.corr(benchmark)),
            }
        )
    return pd.DataFrame(rows)


def fama_macbeth_table(
    decile_returns: pd.DataFrame, characteristic: pd.Series
) -> tuple[pd.DataFrame, dict[str, xsreg.FamaMacBethResult]]:
    periods = {
        "full_oos": decile_returns,
        "1932-1979": decile_returns.loc[:"1979-12-31"],
        "1980-2026": decile_returns.loc["1980-01-01":],
    }
    results: dict[str, xsreg.FamaMacBethResult] = {}
    rows: list[dict[str, object]] = []
    for label, frame in periods.items():
        result = xsreg.fama_macbeth(frame, characteristic, nw_lags=21)
        results[label] = result
        row = asdict(result)
        row.pop("slopes")
        rows.append({"period": label, **row})
    return pd.DataFrame(rows), results


def write_ledger(
    ledger_path: Path,
    folds: list[sp.Split],
    returns_5: dict[str, pd.Series],
    turnover_5: dict[str, pd.Series],
    decile_returns: pd.DataFrame,
    characteristic: pd.Series,
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
            window = split.validate_index(pd.DatetimeIndex(decile_returns.index))
            if not len(window):
                continue
            window_label = f"{window[0].date()}..{window[-1].date()}"
            for name, series in returns_5.items():
                part = series.reindex(window).dropna()
                turn = turnover_5[name].reindex(part.index)
                ledger.record(
                    STUDY,
                    {
                        "study_version": STUDY,
                        "configuration": name,
                        "selection": "top3 confirmatory; other series diagnostic/control",
                    },
                    metrics=metrics.summarize(part, turn),
                    cost_bps=LEDGER_COST,
                    split_index=split_index,
                    window=window_label,
                    split_scheme=scheme,
                    notes="model-implied constituent turnover; academic decile returns",
                )
            regression = xsreg.fama_macbeth(
                decile_returns.reindex(window), characteristic, nw_lags=21
            )
            ledger.record(
                STUDY,
                {
                    "study_version": STUDY,
                    "configuration": "fama_macbeth_rank_proxy",
                    "nw_lags": 21,
                },
                cost_bps=None,
                split_index=split_index,
                window=window_label,
                split_scheme=scheme,
                notes=(
                    f"mean_slope_daily={regression.mean_slope_daily:.12g};"
                    f"t={regression.t_statistic:.8g};"
                    f"fraction_positive={regression.fraction_positive:.8g}"
                ),
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
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(
        index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=EMBARGO_DAYS,
    )
    lo, hi = oos_bounds(index, folds)
    oos_index = prices.loc[lo:hi].index
    if (lo, hi, len(oos_index), len(folds)) != (
        EXPECTED_START,
        EXPECTED_END,
        EXPECTED_BARS,
        EXPECTED_FOLDS,
    ):
        raise ValueError(
            "v11 window mismatch: "
            f"got {lo.date()}..{hi.date()}, {len(oos_index)} bars, {len(folds)} folds"
        )

    columns = list(deciles.columns)
    names_to_weights: dict[str, dict[str, float]] = {
        **{f"decile_{number}": {column: 1.0} for number, column in enumerate(columns, 1)},
        "top3": {column: 1.0 / 3.0 for column in columns[-3:]},
        "equal_weight_10": {column: 0.1 for column in columns},
        "MKT": {"MKT": 1.0},
        "60_40_MKT_CASH": {"MKT": 0.6, "CASH": 0.4},
    }
    gross: dict[str, pd.Series] = {}
    outer_turnover: dict[str, pd.Series] = {}
    for name, weights in names_to_weights.items():
        targets = stitch(prices, fixed_targets(prices, weights), folds)
        result = backtest.run(prices, targets, cost_bps=0.0)
        gross[name] = result.returns.loc[lo:hi]
        outer_turnover[name] = result.turnover.loc[lo:hi]
    gross["hi_minus_lo"] = (deciles.iloc[:, -1] - deciles.iloc[:, 0]).loc[lo:hi]
    outer_turnover["hi_minus_lo"] = pd.Series(0.0, index=oos_index, name="turnover")

    boundaries = xsmom.normal_decile_boundaries()
    internal_turnover = {
        f"decile_{number}": xsmom.model_implied_turnover(
            (number - 1) / 10.0, number / 10.0
        )
        for number in range(1, 11)
    }
    internal_turnover.update(
        {
            "top3": xsmom.model_implied_turnover(0.7, 1.0),
            "equal_weight_10": 0.0,
            "MKT": 0.0,
            "60_40_MKT_CASH": 0.0,
            "hi_minus_lo": (
                xsmom.model_implied_turnover(0.0, 0.1)
                + xsmom.model_implied_turnover(0.9, 1.0)
            ),
        }
    )
    _ = boundaries  # Boundaries are printed for audit below.

    rf_raw = cash.load_risk_free_daily(ROOT / "data")
    rf_daily, rf_diagnostics = cash.align_risk_free(rf_raw, pd.DatetimeIndex(oos_index))

    returns: dict[str, dict[float, pd.Series]] = {}
    total_turnover: dict[str, pd.Series] = {}
    for name in gross:
        returns[name] = {
            cost: combined_cost_return(
                gross[name], outer_turnover[name], internal_turnover[name], cost
            )
            for cost in STRESS_COSTS
        }
        total_turnover[name] = (
            outer_turnover[name] + internal_turnover[name] / 252.0
        ).rename("turnover")

    v11_top3 = combined_cost_return(gross["top3"], outer_turnover["top3"], 0.0, 5.0)
    v11_ew = combined_cost_return(
        gross["equal_weight_10"], outer_turnover["equal_weight_10"], 0.0, 5.0
    )
    v11_delta = metrics.sharpe(v11_top3) - metrics.sharpe(v11_ew)
    v11_ls = gross["hi_minus_lo"]
    v11_duration = metrics.drawdown_duration_days(v11_ls)
    if not (
        abs(v11_delta - 0.132) < 0.002
        and abs(metrics.sharpe(v11_ls) - 0.512) < 0.002
        and abs(metrics.max_drawdown(v11_ls) + 0.852) < 0.003
        and v11_duration == 6_404
    ):
        raise ValueError("v11 sanity anchors do not reproduce")

    print("=== XSMOM-V13-CONFIRM: DATA AND FROZEN DESIGN ===")
    print(
        f"archive={args.archive}\n"
        f"OOS={lo.date()}..{hi.date()} bars={len(oos_index)} folds={len(folds)}\n"
        f"deciles={columns}\n"
        f"normal_decile_boundaries={boundaries}\n"
        f"rank_rho={xsmom.RANK_CORRELATION:.9f}\n"
        f"risk_free={rf_diagnostics}"
    )
    print(
        "V11 sanity reproduced: "
        f"top3-minus-EW10 Sharpe={v11_delta:+.4f}; "
        f"Hi-Lo Sharpe={metrics.sharpe(v11_ls):.4f}; "
        f"maxDD={metrics.max_drawdown(v11_ls):.4f}; "
        f"max underwater={v11_duration} days"
    )
    print(
        "Turnover is MODEL-IMPLIED, not observed: the French archive has no "
        "identifiers, weights, or migration matrix. Exact implementation "
        "requires licensed constituent-level data."
    )

    print("\n=== PART A: MODEL-IMPLIED TURNOVER ===")
    turnover_rows = []
    for name in gross:
        outer = metrics.ann_turnover(outer_turnover[name])
        turnover_rows.append(
            {
                "series": name,
                "outer_observed": outer,
                "internal_model_implied": internal_turnover[name],
                "total_cost_engine_turnover": outer + internal_turnover[name],
            }
        )
    print(pd.DataFrame(turnover_rows).round(4).to_string(index=False))
    print(
        "Limitations: the transition model assumes exchangeable value mass within "
        "rank bins and omits unequal firm sizes, entry/exit, breakpoint jumps, "
        "market impact, taxes, and borrow constraints. EW10 internal turnover=0 "
        "is a favorable lower bound because within-universe crossings cancel."
    )

    performance_rows = []
    for cost in STRESS_COSTS:
        for name in gross:
            summary = result_summary(
                returns[name][cost], total_turnover[name], rf_daily
            )
            performance_rows.append({"cost_bps": cost, "series": name, **summary})
    performance = pd.DataFrame(performance_rows)
    print("\n=== PERFORMANCE AT 0/5/10/25/50 BPS ===")
    print(performance.round(6).to_string(index=False))

    spread_rows = []
    for cost in STRESS_COSTS:
        high_cagr = metrics.cagr(returns["decile_10"][cost])
        low_cagr = metrics.cagr(returns["decile_1"][cost])
        spread = high_cagr - low_cagr
        spread_rows.append(
            {
                "cost_bps": cost,
                "high_cagr": high_cagr,
                "low_cagr": low_cagr,
                "cagr_spread": spread,
                "fraction_of_v11_13_8pt": spread / V11_SPREAD,
            }
        )
    print("\n=== HOW MUCH OF V11'S 13.8-POINT HIGH-LOW CAGR SPREAD SURVIVES? ===")
    print(pd.DataFrame(spread_rows).round(6).to_string(index=False))
    crossover = crossover_cost(
        gross["top3"],
        outer_turnover["top3"],
        internal_turnover["top3"],
        gross["equal_weight_10"],
        outer_turnover["equal_weight_10"],
    )
    print(
        "Top3 Sharpe stops beating EW10 at cost_bps="
        + (f"{crossover:.3f}" if crossover is not None else ">500")
    )

    characteristic = pd.Series(
        [NormalDist().inv_cdf(probability) for probability in np.arange(0.05, 1.0, 0.1)],
        index=columns,
        name="prior_return_rank_score",
    )
    fmb_table, fmb_results = fama_macbeth_table(deciles.loc[lo:hi], characteristic)
    print("\n=== PART B: PORTFOLIO-LEVEL FAMA-MACBETH ===")
    print(fmb_table.round(8).to_string(index=False))
    print(
        "These are portfolio-level rank-proxy regressions, not stock-level "
        "Fama-MacBeth regressions. The dated decile return is the one-period "
        "forward outcome of a portfolio formed from information through t-1."
    )

    print("\n=== PAIRED INFERENCE: TOP3 VS EW10 AND MKT ===")
    inference = paired_inference(
        [
            (
                cost,
                "top3",
                reference,
                returns["top3"][cost],
                returns[reference][cost],
            )
            for cost in STRESS_COSTS
            for reference in ["equal_weight_10", "MKT"]
        ]
    )
    print(inference.round(6).to_string(index=False))

    print("\n=== PRE/POST-1980 PAIRED INFERENCE AT EACH COST ===")
    era_rows: list[dict[str, object]] = []
    for era, date_slice in [
        ("1932-1979", slice(None, "1979-12-31")),
        ("1980-2026", slice("1980-01-01", None)),
    ]:
        era_table = paired_inference(
            [
                (
                    cost,
                    "top3",
                    reference,
                    returns["top3"][cost].loc[date_slice],
                    returns[reference][cost].loc[date_slice],
                )
                for cost in STRESS_COSTS
                for reference in ["equal_weight_10", "MKT"]
            ]
        )
        era_rows.extend(
            {"era": era, **record}
            for record in cast(list[dict[str, object]], era_table.to_dict("records"))
        )
    print(pd.DataFrame(era_rows).round(6).to_string(index=False))

    print("\n=== DECADE SUB-PERIODS AT 10 BPS ===")
    subperiod_rows = []
    for name, cost_returns in returns.items():
        table = metrics.by_subperiod(cost_returns[10.0], breaks=DECADE_BREAKS)
        for period, row in table.iterrows():
            subperiod_rows.append({"series": name, "period": period, **row.to_dict()})
    print(pd.DataFrame(subperiod_rows).round(6).to_string(index=False))

    print("\n=== PART C: TAIL-AWARE POINT METRICS AT EVERY COST ===")
    tail_point_rows = []
    for cost in STRESS_COSTS:
        for name in returns:
            tail_point_rows.append(
                {"cost_bps": cost, "series": name, **tailrisk.summarize(returns[name][cost])}
            )
    print(pd.DataFrame(tail_point_rows).round(6).to_string(index=False))

    print("\n=== PART C: 10 BPS TAIL-METRIC 95% BLOCK-BOOTSTRAP INTERVALS ===")
    tail_interval_rows = []
    for number, name in enumerate(returns):
        print(f"bootstrap {number + 1}/{len(returns)}: {name}", flush=True)
        intervals = tailrisk.bootstrap_intervals(
            returns[name][10.0],
            n_resamples=BOOTSTRAP_RESAMPLES,
            block_length=BOOTSTRAP_BLOCK,
            seed=BOOTSTRAP_SEED,
        )
        for interval_record in intervals.to_dict("records"):
            tail_interval_rows.append({"series": name, **interval_record})
    tail_intervals = pd.DataFrame(tail_interval_rows)
    print(tail_intervals.round(6).to_string(index=False))

    print("\n=== HI-MINUS-LO WORKED TAIL EXAMPLE AT 10 BPS ===")
    hi_lo = performance[
        (performance["cost_bps"] == 10.0) & (performance["series"] == "hi_minus_lo")
    ]
    print(hi_lo.round(6).to_string(index=False))
    print(
        pd.DataFrame(tail_point_rows)
        .query("cost_bps == 10.0 and series == 'hi_minus_lo'")
        .round(6)
        .to_string(index=False)
    )
    print(
        "Sharpe is shown beside expected shortfall, negative-tail asymmetry, "
        "adjusted Sharpe, and drawdown-duration distribution; it is not treated "
        "as a sufficient description of this crash-prone factor."
    )

    ledger_returns = {name: values[LEDGER_COST] for name, values in returns.items()}
    distinct_trials, ledger_rows = write_ledger(
        args.ledger,
        folds,
        ledger_returns,
        total_turnover,
        deciles.loc[lo:hi],
        characteristic,
    )
    if (distinct_trials, ledger_rows) != (16, 1_504):
        raise ValueError(
            f"ledger accounting mismatch: {distinct_trials} configs, {ledger_rows} rows"
        )
    print("\n=== TRIALS LEDGER AND DEFLATED SHARPE ===")
    print(f"study={STUDY} distinct_configs={distinct_trials} rows={ledger_rows}")
    trial_sharpes = pd.Series(
        [metrics.sharpe(returns[name][LEDGER_COST]) for name in returns], dtype=float
    )
    dsr = dfl.deflated_sharpe(
        returns["top3"][LEDGER_COST],
        15,
        trial_sharpes=trial_sharpes,
    )
    print(dfl.report(dsr))
    print(
        "Effective breadth note: the literal Sharpe breadth is 15 return-bearing "
        "configs (the Fama-MacBeth config is excluded), but common market exposure "
        "and nested deciles make the effective independent breadth materially lower."
    )
    print(
        "\nFinal xsmom-v13-confirm study. Nothing promoted. "
        "Factual journaled results follow."
    )


if __name__ == "__main__":
    main()
