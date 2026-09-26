"""Execute the pre-registered trend-v12-execution study.

The v6 signal is unchanged.  This script evaluates a fixed surface of
execution policies, records every configuration, and prints without selecting.
"""

from __future__ import annotations

import argparse
import itertools
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, cash, data, execution, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import LOOKBACKS, MAX_LOOKBACK_DAYS, MULTI_ASSET, stitch

STUDY = "trend-v12-execution"
V11_STUDY = "trend-v12-execution-v11-overlay"
STRESS_COSTS = [0.0, 5.0, 10.0, 25.0, 50.0]
BANDS = [0.0, 0.025, 0.05, 0.10]
ADJUSTMENTS = [1.0, 0.5, 0.33]
TRANCHES = [1, 4]
DELAYS = [0, 1, 2]
MISSED = [0.0, 0.05, 0.10]
SEED = 1202
SUCCESS_COST = 10.0
V11_TURNOVER = [1.0, 2.0, 4.0]
V11_LEDGER_COST = 25.0
FRONTIER_COSTS = [5.0, 10.0, 25.0, 50.0]
MONTHLY_ROTATION = 24.0
WEEKLY_ROTATION = 104.0
DAILY_ROTATION = 504.0
DECADES = [("drop_2000s", 2000, 2009), ("drop_2010s", 2010, 2019),
           ("drop_2020s", 2020, 2029)]
BOOTSTRAP_INDEX_BUDGET = 3_000_000
BOOTSTRAP_CONFIG_CHUNK = 4

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 2000)


@dataclass
class ConfigRun:
    config: dict[str, object]
    policy: execution.ExecutionPolicy
    returns_10: pd.Series
    turnover_10: pd.Series
    metrics_10: dict[str, float | int]
    train_metrics: list[tuple[int, str, dict[str, float | int]]]


def execution_grid() -> list[execution.ExecutionPolicy]:
    return [
        execution.ExecutionPolicy(
            band=band,
            adjustment=adjustment,
            tranches=tranches,
            delay=delay,
            missed_rebalance=missed,
            seed=SEED,
        )
        for band, adjustment, tranches, delay, missed in itertools.product(
            BANDS, ADJUSTMENTS, TRANCHES, DELAYS, MISSED
        )
    ]


def config_dict(policy: execution.ExecutionPolicy) -> dict[str, object]:
    return {
        "study_version": STUDY,
        "universe": "ETF",
        "signal": "v6_multiasset_equal_4_10m",
        "band": policy.band,
        "adjustment": policy.adjustment,
        "tranches": policy.tranches,
        "delay": policy.delay,
        "missed_rebalance": policy.missed_rebalance,
        "seed": policy.seed,
        "selection": "none; fixed preregistered surface",
    }


def config_label(policy: execution.ExecutionPolicy) -> str:
    return (
        f"b={policy.band:.3f}|a={policy.adjustment:.2f}|t={policy.tranches}"
        f"|d={policy.delay}|m={policy.missed_rebalance:.2f}"
    )


def oos_bounds(
    index: pd.DatetimeIndex, folds: list[sp.Split]
) -> tuple[pd.Timestamp, pd.Timestamp]:
    windows = [fold.validate_index(index) for fold in folds]
    usable = [window for window in windows if len(window)]
    return min(window[0] for window in usable), max(window[-1] for window in usable)


def result_metrics(
    result: backtest.BacktestResult,
    lo: pd.Timestamp,
    hi: pd.Timestamp,
    rf_daily: pd.Series,
) -> dict[str, float | int]:
    returns = result.returns.loc[lo:hi]
    turnover = result.turnover.loc[lo:hi]
    out = metrics.summarize(returns, turnover, rf_daily=rf_daily.loc[lo:hi])
    out["worst_day"] = float(returns.min())
    out["left_tail_p05"] = float(returns.quantile(0.05))
    return out


def tracking_error(candidate: pd.Series, reference: pd.Series) -> float:
    aligned = pd.DataFrame({"candidate": candidate, "reference": reference}).dropna()
    return float((aligned["candidate"] - aligned["reference"]).std() * np.sqrt(252))


def returns_at_cost(
    gross_returns: pd.Series,
    turnover: pd.Series,
    cost_bps: float,
) -> pd.Series:
    """Apply the backtest engine's exact linear trade-day cost equation."""
    aligned_turnover = turnover.reindex(gross_returns.index)
    if aligned_turnover.isna().any():
        raise ValueError("turnover does not cover gross-return dates")
    net = (1.0 + gross_returns) * (1.0 - aligned_turnover * cost_bps / 1e4) - 1.0
    return net.rename("ret")


def turnover_frontier(
    prices: pd.DataFrame,
    stitched_targets: pd.DataFrame,
    rf_daily: pd.Series,
    lo: pd.Timestamp,
    hi: pd.Timestamp,
    output_path: Path,
) -> pd.DataFrame:
    """Compute and plot the fixed v12 maximum-viable-turnover diagnostic."""
    strategy_gross_result = execution.run(
        prices,
        stitched_targets,
        execution.ExecutionPolicy(seed=SEED),
        cost_bps=0.0,
        risk_free=rf_daily,
    )
    strategy_gross = strategy_gross_result.returns.loc[lo:hi]
    observed_turnover = metrics.ann_turnover(
        strategy_gross_result.turnover.loc[lo:hi]
    )

    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    benchmark_targets = vol_target_targets(
        prices,
        mix_targets,
        window=63,
        target_ann_vol=0.10,
        max_scale=1.0,
    )
    benchmark_gross_result = backtest.run(
        prices, benchmark_targets, cost_bps=0.0, risk_free=rf_daily
    )
    benchmark_gross = benchmark_gross_result.returns.loc[lo:hi]
    benchmark_turnover = benchmark_gross_result.turnover.loc[lo:hi]

    rows: list[dict[str, object]] = []
    for cost in FRONTIER_COSTS:
        benchmark_net = returns_at_cost(benchmark_gross, benchmark_turnover, cost)
        viable = execution.maximum_viable_turnover(
            strategy_gross, benchmark_net, cost
        )
        rows.append(
            {
                "cost_bps": cost,
                "v6_gross_sharpe": metrics.sharpe(strategy_gross),
                "vt_60_40_net_sharpe": metrics.sharpe(benchmark_net),
                "zero_turnover_advantage": (
                    metrics.sharpe(strategy_gross) - metrics.sharpe(benchmark_net)
                ),
                "maximum_viable_turnover": (
                    viable if viable is not None else "none: zero-turnover v6 trails"
                ),
                "one_leg_holding_days": (
                    252.0 / viable if viable is not None else "not funded"
                ),
                "full_rotation_holding_days": (
                    504.0 / viable if viable is not None else "not funded"
                ),
            }
        )

    turnover_axis = np.linspace(0.0, DAILY_ROTATION, 253)
    cost_axis = np.linspace(FRONTIER_COSTS[0], FRONTIER_COSTS[-1], 181)
    advantage = np.empty((len(cost_axis), len(turnover_axis)), dtype=float)
    for row_number, cost in enumerate(cost_axis):
        benchmark_net = returns_at_cost(benchmark_gross, benchmark_turnover, float(cost))
        benchmark_sharpe = metrics.sharpe(benchmark_net)
        advantage[row_number] = [
            execution.net_sharpe_at_turnover(strategy_gross, turnover, float(cost))
            - benchmark_sharpe
            for turnover in turnover_axis
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(11, 6.5))
    field = axis.contourf(
        turnover_axis,
        cost_axis,
        advantage,
        levels=24,
        cmap="coolwarm",
    )
    figure.colorbar(field, ax=axis, label="v6 net Sharpe − vol-targeted 60/40 net Sharpe")
    has_contour = float(advantage.min()) <= 0.0 <= float(advantage.max())
    if has_contour:
        contour = axis.contour(
            turnover_axis,
            cost_axis,
            advantage,
            levels=[0.0],
            colors="black",
            linewidths=2.2,
        )
        axis.clabel(contour, fmt={0.0: "break-even"})
    else:
        axis.text(
            0.5,
            0.94,
            "No non-negative break-even contour: v6 trails at zero turnover",
            transform=axis.transAxes,
            ha="center",
            va="top",
            bbox={"facecolor": "white", "alpha": 0.9, "edgecolor": "0.4"},
        )
    markers = [
        (observed_turnover, f"observed v6 ({observed_turnover:.2f}x)"),
        (MONTHLY_ROTATION, "monthly full rotation (24x)"),
        (WEEKLY_ROTATION, "weekly full rotation (104x)"),
        (DAILY_ROTATION, "daily full rotation (504x)"),
    ]
    for turnover, label in markers:
        axis.axvline(turnover, linestyle="--", linewidth=1.0, label=label)
    axis.set(
        title="trend-v12-execution: maximum viable turnover frontier",
        xlabel="Annual cost-engine turnover (sum of absolute weight changes)",
        ylabel="One-way implementation cost (bps)",
        xlim=(0.0, DAILY_ROTATION),
        ylim=(FRONTIER_COSTS[0], FRONTIER_COSTS[-1]),
    )
    axis.legend(loc="lower left", fontsize=8)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160)
    plt.close(figure)

    table = pd.DataFrame(rows)
    print("\nMAXIMUM VIABLE TURNOVER FRONTIER — NO STRATEGY SELECTION")
    print(table.to_string(index=False))
    print(f"observed v6 turnover: {observed_turnover:.6f}x/year")
    print(
        "Full-rotation affordability markers under the project's turnover "
        "convention: monthly 24x, weekly 104x, daily 504x."
    )
    if all(isinstance(value, str) for value in table["maximum_viable_turnover"]):
        print(
            "Holding-period implication: none is funded versus the vol-targeted "
            "60/40 benchmark. V6 trails even at zero hypothetical turnover, so "
            "the data do not support claiming monthly, weekly, or shorter full "
            "rotations are affordable on this relative-Sharpe criterion."
        )
    else:
        print(
            "Holding-period implication is an affordability bound only; decision "
            "frequency is not itself turnover and no faster signal was tested."
        )
    print(f"frontier plot: {output_path}")
    return table


def bootstrap_surface(
    candidates: list[pd.Series],
    reference: pd.Series,
    *,
    n_resamples: int,
) -> pd.DataFrame:
    """Evaluate paired Sharpe intervals using one common seed-0 index stream.

    ``stats.bootstrap_sharpe_difference`` starts the same RNG from seed zero
    for every comparison. Reusing those indices across candidate columns is
    therefore an exact computational de-duplication, not a change in the
    bootstrap. Candidate columns are chunked to cap temporary memory.
    """
    if not candidates:
        raise ValueError("bootstrap surface needs at least one candidate")
    if n_resamples < 1:
        raise ValueError("n_resamples must be positive")
    index = reference.index
    reference_values = reference.to_numpy(dtype=float)
    candidate_values = np.column_stack(
        [candidate.reindex(index).to_numpy(dtype=float) for candidate in candidates]
    )
    if not np.isfinite(reference_values).all() or not np.isfinite(candidate_values).all():
        raise ValueError("bootstrap surface inputs must be aligned and finite")
    if len(index) < 30:
        raise ValueError(f"need >= 30 aligned observations, got {len(index)}")

    def column_sharpes(values: np.ndarray, *, axis: int) -> np.ndarray:
        means = values.mean(axis=axis)
        standard_deviations = values.std(axis=axis, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(
                standard_deviations > 0,
                means / standard_deviations * np.sqrt(stats.TRADING_DAYS),
                np.nan,
            )

    observed = column_sharpes(candidate_values, axis=0) - metrics.sharpe(reference)
    draws = np.empty((n_resamples, len(candidates)), dtype=float)
    rng = np.random.default_rng(0)
    batch_size = max(
        1,
        min(n_resamples, max(1, BOOTSTRAP_INDEX_BUDGET // len(index))),
    )
    completed = 0
    while completed < n_resamples:
        size = min(batch_size, n_resamples - completed)
        indices = stats.stationary_bootstrap_indices(
            len(index), stats.DEFAULT_BLOCK_LENGTH, size, rng
        )
        reference_draws = column_sharpes(reference_values[indices], axis=1)
        for start in range(0, len(candidates), BOOTSTRAP_CONFIG_CHUNK):
            stop = min(start + BOOTSTRAP_CONFIG_CHUNK, len(candidates))
            sampled = candidate_values[:, start:stop][indices]
            draws[completed:completed + size, start:stop] = (
                column_sharpes(sampled, axis=1) - reference_draws[:, None]
            )
        completed += size

    rows: list[dict[str, float]] = []
    for column, point in enumerate(observed):
        finite = draws[np.isfinite(draws[:, column]), column]
        if not len(finite):
            raise ValueError(f"candidate {column} produced only degenerate resamples")
        ci_low, ci_high = np.quantile(finite, [0.025, 0.975])
        centred = np.abs(finite - point)
        p_value = (1 + int(np.sum(centred >= abs(point)))) / (len(finite) + 1)
        rows.append(
            {
                "delta_sharpe": float(point),
                "bootstrap_ci_low": float(ci_low),
                "bootstrap_ci_high": float(ci_high),
                "bootstrap_p": float(p_value),
            }
        )
    return pd.DataFrame(rows)


def train_rows(
    result: backtest.BacktestResult,
    index: pd.DatetimeIndex,
    folds: list[sp.Split],
) -> list[tuple[int, str, dict[str, float | int]]]:
    rows: list[tuple[int, str, dict[str, float | int]]] = []
    for fold in folds:
        window = fold.train_index(index)
        if not len(window):
            continue
        returns = result.returns.loc[window[0]:window[-1]]
        turnover = result.turnover.loc[window[0]:window[-1]]
        summary = metrics.summarize(returns, turnover)
        summary["n_obs"] = len(returns)
        rows.append(
            (
                fold.i,
                f"train {window[0].date()}..{window[-1].date()}",
                summary,
            )
        )
    return rows


def run_surface(
    prices: pd.DataFrame,
    full_targets: pd.DataFrame,
    stitched_targets: pd.DataFrame,
    folds: list[sp.Split],
    rf_daily: pd.Series,
    missed_masks: dict[float, pd.Series],
    lo: pd.Timestamp,
    hi: pd.Timestamp,
) -> tuple[list[ConfigRun], pd.DataFrame, dict[float, backtest.BacktestResult]]:
    policies = execution_grid()
    assert len(policies) == 216
    reference_policy = execution.ExecutionPolicy(seed=SEED)
    reference: dict[float, backtest.BacktestResult] = {}
    for cost in STRESS_COSTS:
        reference[cost] = execution.run(
            prices,
            stitched_targets,
            reference_policy,
            cost_bps=cost,
            risk_free=rf_daily,
            missed_mask=missed_masks[reference_policy.missed_rebalance],
        )

    surface_rows: list[dict[str, object]] = []
    runs: list[ConfigRun] = []
    for number, policy in enumerate(policies, start=1):
        label = config_label(policy)
        cost_results: dict[float, backtest.BacktestResult] = {}
        differences: list[float] = []
        for cost in STRESS_COSTS:
            if policy == reference_policy:
                result = reference[cost]
            else:
                result = execution.run(
                    prices,
                    stitched_targets,
                    policy,
                    cost_bps=cost,
                    risk_free=rf_daily,
                    missed_mask=missed_masks[policy.missed_rebalance],
                )
            cost_results[cost] = result
            candidate = result.returns.loc[lo:hi]
            candidate_turnover = result.turnover.loc[lo:hi]
            reference_returns = reference[cost].returns.loc[lo:hi]
            summary = metrics.summarize(
                candidate,
                candidate_turnover,
                rf_daily=rf_daily.loc[lo:hi],
            )
            summary["worst_day"] = float(candidate.min())
            summary["left_tail_p05"] = float(candidate.quantile(0.05))
            delta = metrics.sharpe(candidate) - metrics.sharpe(reference_returns)
            differences.append(delta)
            surface_rows.append(
                {
                    "config": label,
                    **asdict(policy),
                    "cost_bps": cost,
                    **summary,
                    "delta_sharpe_vs_v6": delta,
                    "tracking_error": tracking_error(candidate, reference_returns),
                }
            )

        crossover = execution.cost_crossover(STRESS_COSTS, differences)
        for row in surface_rows[-len(STRESS_COSTS):]:
            row["cost_crossover_bps"] = crossover
            row["crossover_status"] = (
                "reference"
                if policy == reference_policy
                else (">50 / not observed" if crossover is None else "observed")
            )

        full_10 = execution.run(
            prices,
            full_targets,
            policy,
            cost_bps=SUCCESS_COST,
            risk_free=rf_daily,
            missed_mask=missed_masks[policy.missed_rebalance],
        )
        oos_10 = cost_results[SUCCESS_COST]
        runs.append(
            ConfigRun(
                config=config_dict(policy),
                policy=policy,
                returns_10=oos_10.returns.loc[lo:hi],
                turnover_10=oos_10.turnover.loc[lo:hi],
                metrics_10=result_metrics(oos_10, lo, hi, rf_daily),
                train_metrics=train_rows(full_10, pd.DatetimeIndex(prices.index), folds),
            )
        )
        if number % 12 == 0 or number == len(policies):
            print(f"surface progress: {number}/{len(policies)} configurations", flush=True)

    return runs, pd.DataFrame(surface_rows), reference


def inference_table(
    runs: list[ConfigRun],
    reference_returns: pd.Series,
    *,
    n_resamples: int,
) -> pd.DataFrame:
    print(
        f"paired bootstrap surface: {len(runs)} configurations x "
        f"{n_resamples} common resamples",
        flush=True,
    )
    bootstrap = bootstrap_surface(
        [run.returns_10 for run in runs],
        reference_returns,
        n_resamples=n_resamples,
    )
    rows: list[dict[str, object]] = []
    for number, run in enumerate(runs, start=1):
        label = config_label(run.policy)
        boot_row = bootstrap.iloc[number - 1]
        boot_values = {
            "delta_sharpe": float(boot_row["delta_sharpe"]),
            "bootstrap_ci_low": float(boot_row["bootstrap_ci_low"]),
            "bootstrap_ci_high": float(boot_row["bootstrap_ci_high"]),
            "bootstrap_p": float(boot_row["bootstrap_p"]),
        }
        if run.policy == execution.ExecutionPolicy(seed=SEED):
            rows.append(
                {
                    "config": label,
                    "delta_sharpe": 0.0,
                    "bootstrap_ci_low": 0.0,
                    "bootstrap_ci_high": 0.0,
                    "bootstrap_p": 1.0,
                    "correlation": 1.0,
                    "hac_ci_low": 0.0,
                    "hac_ci_high": 0.0,
                    "hac_p": 1.0,
                    "hac_se": 0.0,
                }
            )
            continue
        hac = stats.ledoit_wolf_sharpe_test(
            run.returns_10,
            reference_returns,
            name_a=label,
            name_b="unbuffered_v6",
        )
        rows.append(
            {
                "config": label,
                **boot_values,
                "correlation": float(run.returns_10.corr(reference_returns)),
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "hac_se": hac.standard_error,
            }
        )
        if number % 24 == 0 or number == len(runs):
            print(f"inference progress: {number}/{len(runs)} configurations", flush=True)
    return pd.DataFrame(rows)


def success_table(
    runs: list[ConfigRun],
    inference: pd.DataFrame,
    reference_metrics: dict[str, float | int],
) -> pd.DataFrame:
    inference_by_label = inference.set_index("config")
    reference_turnover = float(reference_metrics["ann_turnover"])
    rows: list[dict[str, object]] = []
    for run in runs:
        label = config_label(run.policy)
        bootstrap_ci_low = cast(float, inference_by_label.at[label, "bootstrap_ci_low"])
        turnover_reduction = 1.0 - float(run.metrics_10["ann_turnover"]) / reference_turnover
        drawdown_change = (
            float(run.metrics_10["max_drawdown"])
            - float(reference_metrics["max_drawdown"])
        )
        tail_change = (
            float(run.metrics_10["left_tail_p05"])
            - float(reference_metrics["left_tail_p05"])
        )
        turnover_pass = turnover_reduction >= 0.40
        inference_pass = bootstrap_ci_low > -0.10
        drawdown_pass = drawdown_change >= -0.02
        tail_pass = tail_change >= -0.0005
        rows.append(
            {
                "config": label,
                **asdict(run.policy),
                "turnover_reduction": turnover_reduction,
                "bootstrap_ci_low": bootstrap_ci_low,
                "drawdown_change": drawdown_change,
                "left_tail_change": tail_change,
                "turnover_pass": turnover_pass,
                "inference_pass": inference_pass,
                "drawdown_pass": drawdown_pass,
                "left_tail_pass": tail_pass,
                "all_success_criteria": (
                    turnover_pass and inference_pass and drawdown_pass and tail_pass
                ),
            }
        )
    return pd.DataFrame(rows)


def leave_one_decade_out(
    runs: list[ConfigRun],
    reference_returns: pd.Series,
    reference_turnover: pd.Series,
    *,
    n_resamples: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for decade, start, end in DECADES:
        years = pd.DatetimeIndex(reference_returns.index).year
        keep = ~years.isin(range(start, end + 1))
        reference = reference_returns.loc[keep]
        print(
            f"LODO bootstrap {decade}: {len(runs)} configurations x "
            f"{n_resamples} common resamples",
            flush=True,
        )
        bootstrap = bootstrap_surface(
            [run.returns_10.loc[keep] for run in runs],
            reference,
            n_resamples=n_resamples,
        )
        for number, run in enumerate(runs, start=1):
            candidate = run.returns_10.loc[keep]
            candidate_turn = run.turnover_10.loc[keep]
            reference_turn = reference_turnover.loc[keep]
            boot_row = bootstrap.iloc[number - 1]
            corr = float(candidate.corr(reference))
            ref_turn = metrics.ann_turnover(reference_turn)
            rows.append(
                {
                    "config": config_label(run.policy),
                    **asdict(run.policy),
                    "omitted_decade": decade,
                    "n_obs": len(candidate),
                    "delta_sharpe": boot_row["delta_sharpe"],
                    "bootstrap_ci_low": boot_row["bootstrap_ci_low"],
                    "bootstrap_ci_high": boot_row["bootstrap_ci_high"],
                    "correlation": corr,
                    "tracking_error": tracking_error(candidate, reference),
                    "turnover_reduction": (
                        1.0 - metrics.ann_turnover(candidate_turn) / ref_turn
                        if ref_turn > 0
                        else float("nan")
                    ),
                    "drawdown_change": (
                        metrics.max_drawdown(candidate) - metrics.max_drawdown(reference)
                    ),
                    "left_tail_change": (
                        float(candidate.quantile(0.05))
                        - float(reference.quantile(0.05))
                    ),
                }
            )
    return pd.DataFrame(rows)


def parse_v11_archive(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} is required for the explicitly exploratory v11 overlay"
        )
    with zipfile.ZipFile(path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV in {path}, found {members}")
        lines = archive.read(members[0]).decode("utf-8", errors="replace").splitlines()
    header_index = next(
        i for i, line in enumerate(lines) if line.lstrip().startswith(",Lo PRIOR")
    )
    columns = [value.strip() for value in lines[header_index].split(",")][1:]
    rows: list[list[object]] = []
    for line in lines[header_index + 1:]:
        parts = [value.strip() for value in line.split(",")]
        if not parts or len(parts[0]) != 8 or not parts[0].isdigit():
            if rows:
                break
            continue
        values = [float(value) for value in parts[1:len(columns) + 1]]
        rows.append([pd.Timestamp(parts[0]), *values])
    returns = pd.DataFrame(rows, columns=["date", *columns]).set_index("date")
    return returns.replace([-99.99, -999.0], np.nan).dropna() / 100.0


def v11_overlay(
    archive_path: Path,
) -> tuple[
    pd.DataFrame,
    list[tuple[dict[str, object], list[tuple[int, str, dict[str, float | int]]]]],
    int,
]:
    returns = parse_v11_archive(archive_path)
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    returns = returns.loc[returns.index.intersection(factors.index)].sort_index()
    index = pd.DatetimeIndex(returns.index)
    folds = sp.make_splits(
        index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=252,
    )
    lo, hi = oos_bounds(index, folds)
    gross = returns["Hi PRIOR"] - returns["Lo PRIOR"]
    rows: list[dict[str, object]] = []
    ledger_rows: list[
        tuple[dict[str, object], list[tuple[int, str, dict[str, float | int]]]]
    ] = []
    for assumed_turnover in V11_TURNOVER:
        config = {
            "study_version": STUDY,
            "universe": "FF_10_prior_return_deciles",
            "section": "v11_exploratory_cost_overlay",
            "annual_one_way_turnover_per_leg": assumed_turnover,
            "selection": "none; diagnostic assumption only",
        }
        for cost in STRESS_COSTS:
            daily_drag = 2.0 * assumed_turnover * cost / 1e4 / 252.0
            net = gross - daily_drag
            oos = net.loc[lo:hi]
            rows.append(
                {
                    "assumed_turnover_per_leg": assumed_turnover,
                    "cost_bps": cost,
                    "ann_mean": float(oos.mean() * 252),
                    "ann_vol": metrics.ann_vol(oos),
                    "sharpe_rf0": metrics.sharpe(oos),
                    "max_drawdown": metrics.max_drawdown(oos),
                    "cumulative_return": float(np.prod(1.0 + oos.to_numpy()) - 1.0),
                    "gross_13_8pt_spread_after_simple_drag": (
                        0.138 - 2.0 * assumed_turnover * cost / 1e4
                    ),
                }
            )
        primary_net = gross - 2.0 * assumed_turnover * V11_LEDGER_COST / 1e4 / 252.0
        config_train: list[tuple[int, str, dict[str, float | int]]] = []
        for fold in folds:
            window = fold.train_index(index)
            if not len(window):
                continue
            sample = primary_net.loc[window[0]:window[-1]]
            summary = metrics.summarize(sample)
            summary["n_obs"] = len(sample)
            config_train.append(
                (
                    fold.i,
                    f"train {window[0].date()}..{window[-1].date()}",
                    summary,
                )
            )
        ledger_rows.append((config, config_train))
    return pd.DataFrame(rows), ledger_rows, len(folds)


def grouped_subperiods(
    runs: list[ConfigRun], reference_returns: pd.Series
) -> pd.DataFrame:
    reference = metrics.by_subperiod(reference_returns)
    rows: list[dict[str, object]] = []
    for run in runs:
        periods = metrics.by_subperiod(run.returns_10)
        for period in periods.index.intersection(reference.index):
            rows.append(
                {
                    "period": period,
                    **asdict(run.policy),
                    "delta_sharpe": (
                        float(periods.loc[period, "sharpe_rf0"])
                        - float(reference.loc[period, "sharpe_rf0"])
                    ),
                }
            )
    raw = pd.DataFrame(rows)
    grouped: list[pd.DataFrame] = []
    for parameter in ["band", "adjustment", "tranches", "delay", "missed_rebalance"]:
        part = (
            raw.groupby(["period", parameter])["delta_sharpe"]
            .agg(["mean", "median", "min", "max"])
            .reset_index()
            .rename(columns={parameter: "setting"})
        )
        part.insert(1, "parameter", parameter)
        grouped.append(part)
    return pd.concat(grouped, ignore_index=True)


def write_ledger(
    path: Path,
    runs: list[ConfigRun],
    v11_rows: list[tuple[dict[str, object], list[tuple[int, str, dict[str, float | int]]]]],
    *,
    n_folds: int,
    v11_folds: int,
) -> None:
    scheme = {
        "n_splits": n_folds,
        "max_lookback_days": MAX_LOOKBACK_DAYS,
        "selection": "none",
        "ledger_cost_bps": SUCCESS_COST,
    }
    v11_scheme = {
        "n_splits": v11_folds,
        "embargo_days": 252,
        "selection": "none; exploratory overlay",
        "ledger_cost_bps": V11_LEDGER_COST,
    }
    with TrialsLedger(path) as ledger:
        if ledger.n_trials(STUDY) or ledger.n_trials(V11_STUDY):
            raise RuntimeError(
                "v12 study rows already exist; refusing to duplicate append-only ledger rows"
            )
        for run in runs:
            for split_index, window, summary in run.train_metrics:
                ledger.record(
                    STUDY,
                    run.config,
                    metrics=summary,
                    cost_bps=SUCCESS_COST,
                    split_index=split_index,
                    split_scheme=scheme,
                    window=window,
                )
        for config, config_rows in v11_rows:
            for split_index, window, summary in config_rows:
                ledger.record(
                    V11_STUDY,
                    config,
                    metrics=summary,
                    cost_bps=V11_LEDGER_COST,
                    split_index=split_index,
                    split_scheme=v11_scheme,
                    window=window,
                    notes="EXPLORATORY v11 cost overlay; does not confirm v11",
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    parser.add_argument(
        "--v11-archive",
        type=Path,
        default=ROOT / "10_Portfolios_Prior_12_2_Daily_CSV.zip",
    )
    parser.add_argument(
        "--frontier-output",
        type=Path,
        default=ROOT / "reports" / "trend-v12-execution-turnover-frontier.png",
    )
    parser.add_argument(
        "--frontier-only",
        action="store_true",
        help="compute the preregistered turnover frontier without rerunning the surface",
    )
    args = parser.parse_args()

    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    prices, _ = data.drop_suspect_dates(data.build_matrix(all_tickers(cfg), store))
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(
        index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    sp.check_embargo_covers_lookback(folds, index, MAX_LOOKBACK_DAYS)
    lo, hi = oos_bounds(index, folds)
    rf_daily, rf_provenance = cash.align_risk_free(
        cash.load_risk_free_daily(store), index
    )
    print(
        f"risk-free: {rf_provenance['source_first']}..{rf_provenance['source_last']}; "
        f"{rf_provenance['n_carried_forward']} bars carried forward"
    )
    print(f"OOS: {lo.date()}..{hi.date()}, {len(prices.loc[lo:hi])} bars, {len(folds)} folds")

    full_targets = trend.ensemble_targets(
        prices,
        risk_assets=MULTI_ASSET,
        risk_off=None,
        lookback_months=LOOKBACKS,
    )
    stitched_targets = stitch(prices, full_targets, folds)
    if args.frontier_only:
        turnover_frontier(
            prices,
            stitched_targets,
            rf_daily,
            lo,
            hi,
            args.frontier_output,
        )
        return 0
    missed_masks = {
        probability: execution.decision_mask(
            full_targets, probability, seed=SEED
        )
        for probability in MISSED
    }
    print("\nMISSED-REBALANCE MASKS — common across all other settings")
    stitched_decisions = stitched_targets.notna().any(axis=1)
    for probability in MISSED:
        decisions = int(stitched_decisions.sum())
        missed = int((missed_masks[probability] & stitched_decisions).sum())
        print(
            f"m={probability:.2f}: {missed}/{decisions} "
            f"({missed / decisions if decisions else 0.0:.2%})"
        )

    runs, surface, reference = run_surface(
        prices,
        full_targets,
        stitched_targets,
        folds,
        rf_daily,
        missed_masks,
        lo,
        hi,
    )
    reference_5 = reference[5.0]
    reference_5_returns = reference_5.returns.loc[lo:hi]
    reference_5_turnover = reference_5.turnover.loc[lo:hi]
    rebuilt_sharpe = metrics.sharpe(reference_5_returns)
    rebuilt_turnover = metrics.ann_turnover(reference_5_turnover)
    print("\nV6 RECONSTRUCTION CHECK")
    print(f"Sharpe @5bps: rebuilt {rebuilt_sharpe:.6f}, journal 0.781")
    print(f"turnover: rebuilt {rebuilt_turnover:.6f}, journal 5.15")
    if abs(rebuilt_sharpe - 0.781) > 0.003 or abs(rebuilt_turnover - 5.15) > 0.02:
        print("V6 reconstruction failed; stopping before inference or ledger write")
        return 1

    reference_10_returns = reference[SUCCESS_COST].returns.loc[lo:hi]
    reference_10_turnover = reference[SUCCESS_COST].turnover.loc[lo:hi]
    reference_metrics = result_metrics(reference[SUCCESS_COST], lo, hi, rf_daily)
    inference = inference_table(
        runs, reference_10_returns, n_resamples=args.resamples
    )
    success = success_table(runs, inference, reference_metrics)
    lodo = leave_one_decade_out(
        runs,
        reference_10_returns,
        reference_10_turnover,
        n_resamples=args.resamples,
    )
    v11, v11_ledger_rows, v11_folds = v11_overlay(args.v11_archive)

    print("\nCOMPLETE EXECUTION SURFACE — NO SELECTION")
    print(surface.round(6).to_string(index=False))
    print("\nCOST CROSSOVER — one row per configuration")
    crossover_columns = [
        "config", "band", "adjustment", "tranches", "delay",
        "missed_rebalance", "cost_crossover_bps", "crossover_status",
    ]
    crossover = surface.loc[surface["cost_bps"] == 10.0, crossover_columns]
    print(crossover.round(6).to_string(index=False))

    print("\nBASELINES — IDENTICAL OOS WINDOW")
    baseline_rows: list[dict[str, object]] = []
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    for cost in STRESS_COSTS:
        spy = backtest.buy_and_hold(
            prices, "SPY", cost_bps=cost, risk_free=rf_daily
        )
        mix = backtest.run(prices, mix_targets, cost_bps=cost, risk_free=rf_daily)
        for label, baseline_result in [("SPY buy&hold", spy), ("60/40", mix)]:
            baseline_summary = result_metrics(baseline_result, lo, hi, rf_daily)
            baseline_rows.append(
                {"portfolio": label, "cost_bps": cost, **baseline_summary}
            )
    print(pd.DataFrame(baseline_rows).round(6).to_string(index=False))

    print(f"\nPAIRED INFERENCE @10BPS — {args.resamples} RESAMPLES, BLOCK 21")
    print(inference.round(6).to_string(index=False))
    print("\nECONOMIC SUCCESS CRITERIA @10BPS — INDEPENDENT FLAGS, NO SELECTION")
    print(success.round(6).to_string(index=False))
    print(
        f"success count: {int(success['all_success_criteria'].sum())}/"
        f"{len(success)} (reported only; no survivor selected)"
    )

    print("\nLEAVE-ONE-DECADE-OUT @10BPS — NO DECADE OR CONFIG SELECTED")
    print(lodo.round(6).to_string(index=False))
    print("\nUNBUFFERED V6 SUB-PERIODS @10BPS")
    print(metrics.by_subperiod(reference_10_returns).round(6).to_string())
    print("\nGROUPED SURFACE SUB-PERIOD DIAGNOSTICS @10BPS")
    print(grouped_subperiods(runs, reference_10_returns).round(6).to_string(index=False))

    train_sharpes = pd.Series(
        [
            float(np.mean([float(row[2]["sharpe_rf0"]) for row in run.train_metrics]))
            for run in runs
        ]
    )
    dsr_rows = []
    for run in runs:
        dsr_result = dfl.deflated_sharpe(
            run.returns_10,
            n_trials=len(runs),
            trial_sharpes=train_sharpes,
        )
        dsr_rows.append(
            {
                "config": config_label(run.policy),
                "sharpe_rf0": dsr_result["sharpe_annual"],
                "sr0": dsr_result["sr0_annual"],
                "dsr": dsr_result["dsr"],
                "trial_sharpe_sd": dsr_result["trial_sharpe_sd_annual"],
                "effective_breadth": len(runs),
                "note": (
                    "216 highly correlated execution trials; DSR descriptive, "
                    "not a selection license"
                ),
            }
        )
    print("\nDEFLATED SHARPE — FULL 216-CONFIG EXECUTION BREADTH")
    print(pd.DataFrame(dsr_rows).round(6).to_string(index=False))

    print("\nV11 EXPLORATORY MOMENTUM-COST OVERLAY — DOES NOT CONFIRM V11")
    print(v11.round(6).to_string(index=False))
    print(
        "The 1x/2x/4x turnover assumptions are stresses, not observed decile "
        "turnover. V11 remains unregistered and gross evidence only."
    )

    turnover_frontier(
        prices,
        stitched_targets,
        rf_daily,
        lo,
        hi,
        args.frontier_output,
    )

    # Append to the immutable ledger only after every result table has been
    # computed and formatted successfully. A reporting failure can then be
    # fixed and rerun without leaving an incomplete, non-repeatable study.
    write_ledger(
        args.ledger,
        runs,
        v11_ledger_rows,
        n_folds=len(folds),
        v11_folds=v11_folds,
    )

    with TrialsLedger(args.ledger) as ledger:
        print("\nLEDGER AUDIT")
        print(
            f"{STUDY}: {ledger.n_trials(STUDY)} configs, "
            f"{ledger.n_trials(STUDY, distinct=False)} rows"
        )
        print(
            f"{V11_STUDY}: {ledger.n_trials(V11_STUDY)} configs, "
            f"{ledger.n_trials(V11_STUDY, distinct=False)} rows"
        )
    print(
        "\nSurface reported with NO selection. Nothing promoted. "
        "Futures-data decision remains gated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
