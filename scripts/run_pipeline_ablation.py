"""Execute the pre-registered pipeline-v14-ablation study.

Nine fixed pipeline states are reported without selection.  The load-bearing
results are eight paired, one-stage-at-a-time comparisons at 10 bps.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, cash, data, execution, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.pipeline import DecisionPipeline, PipelineConfig, PipelineOutput
from woodland.signals.voltarget import vol_target_targets
from woodland.study import COSTS, MAX_LOOKBACK_DAYS, MULTI_ASSET, stitch

STUDY = "pipeline-v14-ablation"
INFERENCE_COST = 10.0
LEDGER_COST = 5.0
EXPECTED_BARS = 5_499
EXPECTED_FOLDS = 22
BOOTSTRAP_INDEX_BUDGET = 3_000_000
DECADES = [("drop_2000s", 2000, 2009), ("drop_2010s", 2010, 2019),
           ("drop_2020s", 2020, 2029)]

pd.set_option("display.width", 280)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 1000)


@dataclass(frozen=True)
class StudyConfig:
    name: str
    pipeline: PipelineConfig


@dataclass
class ConfigRun:
    spec: StudyConfig
    output: PipelineOutput
    results: dict[float, backtest.BacktestResult]
    returns: dict[float, pd.Series]
    turnover: dict[float, pd.Series]


CONFIGS = [
    StudyConfig("raw-v6", PipelineConfig(execution="none")),
    StudyConfig("baseline", PipelineConfig(execution="partial")),
    StudyConfig(
        "s1-dispersion", PipelineConfig(regime_filter=True, execution="partial")
    ),
    StudyConfig(
        "s2-inverse-vol", PipelineConfig(sizing="inverse_vol", execution="partial")
    ),
    StudyConfig(
        "s2-min-variance", PipelineConfig(sizing="min_variance", execution="partial")
    ),
    StudyConfig(
        "s3-symmetric", PipelineConfig(exposure="symmetric", execution="partial")
    ),
    StudyConfig(
        "s3-asymmetric", PipelineConfig(exposure="asymmetric", execution="partial")
    ),
    StudyConfig("s4-band", PipelineConfig(execution="band")),
    StudyConfig("s4-partial-band", PipelineConfig(execution="partial_band")),
]

ABLATIONS = [
    ("S1 regime filter", "s1-dispersion", "baseline"),
    ("S2 inverse-vol", "s2-inverse-vol", "baseline"),
    ("S2 min-variance", "s2-min-variance", "baseline"),
    ("S3 symmetric vol target", "s3-symmetric", "baseline"),
    ("S3 asymmetric vol target", "s3-asymmetric", "baseline"),
    ("S4 partial adjustment", "baseline", "raw-v6"),
    ("S4 no-trade band", "s4-band", "raw-v6"),
    ("S4 band added to partial", "s4-partial-band", "baseline"),
]


def oos_bounds(
    index: pd.DatetimeIndex, folds: list[sp.Split]
) -> tuple[pd.Timestamp, pd.Timestamp]:
    windows = [fold.validate_index(index) for fold in folds]
    usable = [window for window in windows if len(window)]
    return min(window[0] for window in usable), max(window[-1] for window in usable)


def config_dict(spec: StudyConfig) -> dict[str, object]:
    return {
        "study_version": STUDY,
        "universe": "ETF",
        "signal": "v6_multiasset_ensemble_4_10m",
        "name": spec.name,
        **asdict(spec.pipeline),
        "selection": "none; fixed preregistered one-stage ablation",
    }


def summarize_result(
    result: backtest.BacktestResult,
    lo: pd.Timestamp,
    hi: pd.Timestamp,
    rf_daily: pd.Series,
) -> dict[str, float | int]:
    returns = result.returns.loc[lo:hi]
    turnover = result.turnover.loc[lo:hi]
    summary = metrics.summarize(
        returns, turnover, rf_daily=rf_daily.loc[lo:hi]
    )
    summary["worst_day"] = float(returns.min())
    summary["left_tail_p05"] = float(returns.quantile(0.05))
    summary["mean_gross_exposure"] = float(result.holdings.loc[lo:hi].sum(axis=1).mean())
    return summary


def run_configs(
    prices: pd.DataFrame,
    folds: list[sp.Split],
    rf_daily: pd.Series,
    lo: pd.Timestamp,
    hi: pd.Timestamp,
) -> tuple[dict[str, ConfigRun], pd.DataFrame]:
    runs: dict[str, ConfigRun] = {}
    rows: list[dict[str, object]] = []
    for number, spec in enumerate(CONFIGS, start=1):
        output = DecisionPipeline(MULTI_ASSET, spec.pipeline).build(prices)
        stitched_targets = stitch(prices, output.targets, folds)
        results: dict[float, backtest.BacktestResult] = {}
        returns: dict[float, pd.Series] = {}
        turnovers: dict[float, pd.Series] = {}
        for cost in COSTS:
            result = execution.run(
                prices,
                stitched_targets,
                output.policy,
                cost_bps=cost,
                risk_free=rf_daily,
            )
            results[cost] = result
            returns[cost] = result.returns.loc[lo:hi]
            turnovers[cost] = result.turnover.loc[lo:hi]
            decisions = output.targets.notna().any(axis=1)
            target_gross = output.targets.loc[decisions].sum(axis=1)
            rows.append(
                {
                    "config": spec.name,
                    **asdict(spec.pipeline),
                    "cost_bps": cost,
                    **summarize_result(result, lo, hi, rf_daily),
                    "mean_target_exposure": float(target_gross.mean()),
                    "pct_target_below_one": float((target_gross < 1.0 - 1e-9).mean()),
                }
            )
        runs[spec.name] = ConfigRun(spec, output, results, returns, turnovers)
        print(f"pipeline progress: {number}/{len(CONFIGS)} {spec.name}", flush=True)
    return runs, pd.DataFrame(rows)


def _column_sharpes(values: np.ndarray, *, axis: int) -> np.ndarray:
    means = values.mean(axis=axis)
    deviations = values.std(axis=axis, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(deviations > 0, means / deviations * np.sqrt(252), np.nan)


def bootstrap_group(
    candidates: list[pd.Series],
    reference: pd.Series,
    *,
    n_resamples: int,
) -> list[dict[str, float]]:
    """Exact common-seed stationary bootstrap for one comparator group."""
    index = reference.index
    reference_values = reference.to_numpy(dtype=float)
    candidate_values = np.column_stack(
        [candidate.reindex(index).to_numpy(dtype=float) for candidate in candidates]
    )
    if not np.isfinite(reference_values).all() or not np.isfinite(candidate_values).all():
        raise ValueError("bootstrap inputs must be aligned and finite")
    observed = _column_sharpes(candidate_values, axis=0) - metrics.sharpe(reference)
    draws = np.empty((n_resamples, len(candidates)), dtype=float)
    rng = np.random.default_rng(0)
    batch = max(1, min(n_resamples, BOOTSTRAP_INDEX_BUDGET // len(index)))
    completed = 0
    while completed < n_resamples:
        size = min(batch, n_resamples - completed)
        indices = stats.stationary_bootstrap_indices(
            len(index), stats.DEFAULT_BLOCK_LENGTH, size, rng
        )
        reference_draws = _column_sharpes(reference_values[indices], axis=1)
        sampled = candidate_values[indices]
        draws[completed:completed + size] = (
            _column_sharpes(sampled, axis=1) - reference_draws[:, None]
        )
        completed += size

    rows: list[dict[str, float]] = []
    for column, point in enumerate(observed):
        finite = draws[np.isfinite(draws[:, column]), column]
        low, high = np.quantile(finite, [0.025, 0.975])
        centred = np.abs(finite - point)
        p_value = (1 + int(np.sum(centred >= abs(point)))) / (len(finite) + 1)
        rows.append(
            {
                "delta_sharpe": float(point),
                "bootstrap_ci_low": float(low),
                "bootstrap_ci_high": float(high),
                "bootstrap_p": float(p_value),
            }
        )
    return rows


def contribution_table(
    runs: dict[str, ConfigRun], *, n_resamples: int
) -> pd.DataFrame:
    bootstrap_by_pair: dict[tuple[str, str], dict[str, float]] = {}
    for comparator in sorted({comparator for _, _, comparator in ABLATIONS}):
        pairs = [(candidate, comp) for _, candidate, comp in ABLATIONS if comp == comparator]
        bootstrap_rows = bootstrap_group(
            [runs[candidate].returns[INFERENCE_COST] for candidate, _ in pairs],
            runs[comparator].returns[INFERENCE_COST],
            n_resamples=n_resamples,
        )
        bootstrap_by_pair.update(
            {
                (candidate, comp): values
                for (candidate, comp), values in zip(
                    pairs, bootstrap_rows, strict=True
                )
            }
        )

    rows: list[dict[str, object]] = []
    for stage, candidate, comparator in ABLATIONS:
        candidate_returns = runs[candidate].returns[INFERENCE_COST]
        comparator_returns = runs[comparator].returns[INFERENCE_COST]
        candidate_turnover = metrics.ann_turnover(runs[candidate].turnover[INFERENCE_COST])
        comparator_turnover = metrics.ann_turnover(runs[comparator].turnover[INFERENCE_COST])
        hac = stats.ledoit_wolf_sharpe_test(
            candidate_returns,
            comparator_returns,
            name_a=candidate,
            name_b=comparator,
        )
        boot_values = bootstrap_by_pair[(candidate, comparator)]
        statistically_positive = bool(
            boot_values["delta_sharpe"] > 0.0
            and boot_values["bootstrap_p"] < 0.05
            and hac.p_value < 0.05
        )
        candidate_dd = abs(metrics.max_drawdown(candidate_returns))
        comparator_dd = abs(metrics.max_drawdown(comparator_returns))
        current_gate_shape = bool(
            boot_values["delta_sharpe"] >= 0.10
            and boot_values["bootstrap_ci_low"] > -0.10
            and candidate_dd <= 1.25 * comparator_dd
            and candidate_turnover <= 1.5 * comparator_turnover
        )
        rows.append(
            {
                "stage": stage,
                "candidate": candidate,
                "without_stage": comparator,
                **boot_values,
                "hac_delta": hac.difference,
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "correlation": candidate_returns.corr(comparator_returns),
                "turnover_candidate": candidate_turnover,
                "turnover_without": comparator_turnover,
                "turnover_change": candidate_turnover - comparator_turnover,
                "turnover_change_pct": (
                    candidate_turnover / comparator_turnover - 1.0
                    if comparator_turnover > 0 else float("nan")
                ),
                "statistically_positive": statistically_positive,
                "current_gate_shape": current_gate_shape,
            }
        )
    return pd.DataFrame(rows)


def leave_one_decade_out(
    contributions: pd.DataFrame,
    runs: dict[str, ConfigRun],
    *,
    n_resamples: int,
) -> pd.DataFrame:
    qualifying = contributions[
        contributions["statistically_positive"] | contributions["current_gate_shape"]
    ]
    rows: list[dict[str, object]] = []
    for contribution in qualifying.to_dict("records"):
        candidate_name = str(contribution["candidate"])
        comparator_name = str(contribution["without_stage"])
        for label, first, last in DECADES:
            candidate = runs[candidate_name]
            comparator = runs[comparator_name]
            # Construct explicitly: Index boolean arithmetic is clearer and
            # avoids pandas silently aligning unlike objects.
            years = pd.DatetimeIndex(candidate.returns[INFERENCE_COST].index).year
            keep = (years < first) | (years > last)
            candidate_returns = candidate.returns[INFERENCE_COST].loc[keep]
            comparator_returns = comparator.returns[INFERENCE_COST].loc[keep]
            boot = stats.bootstrap_sharpe_difference(
                candidate_returns,
                comparator_returns,
                name_a=candidate_name,
                name_b=comparator_name,
                n_resamples=n_resamples,
            )
            hac = stats.ledoit_wolf_sharpe_test(candidate_returns, comparator_returns)
            candidate_turnover = metrics.ann_turnover(
                candidate.turnover[INFERENCE_COST].loc[keep]
            )
            comparator_turnover = metrics.ann_turnover(
                comparator.turnover[INFERENCE_COST].loc[keep]
            )
            rows.append(
                {
                    "stage": contribution["stage"],
                    "omission": label,
                    "delta_sharpe": boot.difference,
                    "bootstrap_ci_low": boot.ci_low,
                    "bootstrap_ci_high": boot.ci_high,
                    "bootstrap_p": boot.p_value,
                    "hac_delta": hac.difference,
                    "hac_p": hac.p_value,
                    "correlation": candidate_returns.corr(comparator_returns),
                    "turnover_change": candidate_turnover - comparator_turnover,
                }
            )
    return pd.DataFrame(rows)


def baseline_table(
    prices: pd.DataFrame,
    rf_daily: pd.Series,
    lo: pd.Timestamp,
    hi: pd.Timestamp,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    rows: list[dict[str, object]] = []
    at_five: dict[str, pd.Series] = {}
    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    vol_mix_targets = vol_target_targets(
        prices, mix_targets, window=63, target_ann_vol=0.10, max_scale=1.0
    )
    for cost in COSTS:
        results = {
            "SPY buy&hold": backtest.buy_and_hold(
                prices, "SPY", cost_bps=cost, risk_free=rf_daily
            ),
            "60/40": backtest.run(
                prices, mix_targets, cost_bps=cost, risk_free=rf_daily
            ),
            "vol-target 60/40": backtest.run(
                prices, vol_mix_targets, cost_bps=cost, risk_free=rf_daily
            ),
        }
        for label, result in results.items():
            rows.append(
                {"portfolio": label, "cost_bps": cost,
                 **summarize_result(result, lo, hi, rf_daily)}
            )
            if cost == 5.0:
                at_five[label] = result.returns.loc[lo:hi]
    return pd.DataFrame(rows), at_five


def ledger_rows(
    ledger_path: Path,
    runs: dict[str, ConfigRun],
    folds: list[sp.Split],
) -> None:
    scheme = {
        "train_years": 5,
        "validate_years": 1,
        "step_years": 1,
        "embargo_days": MAX_LOOKBACK_DAYS,
        "selection": "none",
    }
    index = pd.DatetimeIndex(next(iter(runs.values())).returns[LEDGER_COST].index)
    with TrialsLedger(ledger_path) as ledger:
        if ledger.n_trials(STUDY, distinct=False):
            raise RuntimeError(f"{STUDY!r} already has ledger rows; refusing duplicate write")
        for run in runs.values():
            full_result = run.results[LEDGER_COST]
            for fold in folds:
                window = fold.validate_index(pd.DatetimeIndex(full_result.returns.index))
                window = window.intersection(index)
                if not len(window):
                    continue
                returns = full_result.returns.loc[window]
                turnover = full_result.turnover.loc[window]
                summary = metrics.summarize(returns, turnover)
                summary["n_obs"] = len(returns)
                ledger.record(
                    STUDY,
                    config_dict(run.spec),
                    status="evaluated",
                    metrics=summary,
                    cost_bps=LEDGER_COST,
                    split_index=fold.i,
                    window=f"validate {window[0].date()}..{window[-1].date()}",
                    split_scheme=scheme,
                    notes="fixed one-stage ablation; no selection",
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    args = parser.parse_args()

    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    prices, dropped = data.drop_suspect_dates(
        data.build_matrix(all_tickers(cfg), store)
    )
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
    n_bars = len(prices.loc[lo:hi])
    print("PIPELINE-V14-ABLATION — FIXED ONE-STAGE COMPARISONS, NO SELECTION")
    print(f"OOS {lo.date()}..{hi.date()}, {n_bars} bars, {len(folds)} folds")
    print(f"suspect dates removed: {len(dropped)}")
    print(
        f"risk-free source {rf_provenance['source_first']}.."
        f"{rf_provenance['source_last']}; "
        f"{rf_provenance['n_carried_forward']} bars carried forward"
    )
    if n_bars != EXPECTED_BARS or len(folds) != EXPECTED_FOLDS:
        print("Frozen v6/v12 window mismatch; stopping before results or ledger")
        return 1

    runs, surface = run_configs(prices, folds, rf_daily, lo, hi)
    raw = runs["raw-v6"]
    baseline = runs["baseline"]
    raw_sharpe = metrics.sharpe(raw.returns[5.0])
    raw_turnover = metrics.ann_turnover(raw.turnover[5.0])
    baseline_sharpe = metrics.sharpe(baseline.returns[5.0])
    baseline_turnover = metrics.ann_turnover(baseline.turnover[5.0])
    print("\nRECONSTRUCTION CHECKS")
    print(f"raw v6 @5bps Sharpe {raw_sharpe:.6f} (journal 0.780673)")
    print(f"raw v6 turnover {raw_turnover:.6f} (journal 5.153145)")
    print(f"partial-0.50 @5bps Sharpe {baseline_sharpe:.6f} (v12 0.804639)")
    print(f"partial-0.50 turnover {baseline_turnover:.6f} (v12 2.772494)")
    if (
        abs(raw_sharpe - 0.780673) > 0.0005
        or abs(raw_turnover - 5.153145) > 0.005
        or abs(baseline_sharpe - 0.804639) > 0.0005
        or abs(baseline_turnover - 2.772494) > 0.005
    ):
        print("Reconstruction mismatch; stopping before inference or ledger")
        return 1

    contributions = contribution_table(runs, n_resamples=args.resamples)
    lodo = leave_one_decade_out(
        contributions, runs, n_resamples=args.resamples
    )
    baselines, baseline_five = baseline_table(prices, rf_daily, lo, hi)

    print("\nALL NINE PIPELINE STATES — 0/5/10 BPS")
    print(surface.round(6).to_string(index=False))
    print("\nREQUIRED BASELINES — IDENTICAL WINDOW")
    print(baselines.round(6).to_string(index=False))
    print(
        f"\nSTAGE CONTRIBUTIONS @10BPS — {args.resamples} PAIRED RESAMPLES, "
        f"BLOCK {stats.DEFAULT_BLOCK_LENGTH}"
    )
    print(contributions.round(6).to_string(index=False))
    print("\nLEAVE-ONE-DECADE-OUT FOR PRE-REGISTERED PASS LABELS")
    if lodo.empty:
        print("No ablation received either pass label; no LODO rows are triggered.")
    else:
        print(lodo.round(6).to_string(index=False))

    print("\nSUB-PERIODS @5BPS — ALL PIPELINE STATES AND BASELINES")
    subperiod_rows: list[dict[str, object]] = []
    for name, run in runs.items():
        periods = metrics.by_subperiod(run.returns[5.0])
        for period, values in periods.iterrows():
            value_dict = {str(key): value for key, value in values.to_dict().items()}
            subperiod_rows.append({"portfolio": name, "period": period, **value_dict})
    for name, returns in baseline_five.items():
        periods = metrics.by_subperiod(returns)
        for period, values in periods.iterrows():
            value_dict = {str(key): value for key, value in values.to_dict().items()}
            subperiod_rows.append({"portfolio": name, "period": period, **value_dict})
    print(pd.DataFrame(subperiod_rows).round(6).to_string(index=False))

    trial_sharpes = pd.Series(
        {name: metrics.sharpe(run.returns[5.0]) for name, run in runs.items()}
    )
    dsr_rows: list[dict[str, object]] = []
    for name, run in runs.items():
        result = dfl.deflated_sharpe(
            run.returns[5.0], n_trials=len(runs), trial_sharpes=trial_sharpes
        )
        dsr_rows.append(
            {
                "config": name,
                "sharpe_rf0": result["sharpe_annual"],
                "sr0": result["sr0_annual"],
                "dsr": result["dsr"],
                "trial_sharpe_sd": result["trial_sharpe_sd_annual"],
                "effective_breadth": len(runs),
                "note": "nine correlated preregistered states; no selection license",
            }
        )
    print("\nDEFLATED SHARPE — NINE-CONFIG EFFECTIVE-BREADTH NOTE")
    print(pd.DataFrame(dsr_rows).round(6).to_string(index=False))

    # Write only after every report table has computed successfully.
    ledger_rows(args.ledger, runs, folds)
    with TrialsLedger(args.ledger) as ledger:
        print("\nLEDGER AUDIT")
        print(
            f"{STUDY}: {ledger.n_trials(STUDY)} configurations, "
            f"{ledger.n_trials(STUDY, distinct=False)} rows"
        )

    print("\nCARRY EXCLUDED — DATA PREREQUISITE")
    print(
        "Bond carry needs YTM, commodity carry needs a futures curve, and equity "
        "carry needs dividend yields. No proxy or zero-carry stage was used."
    )
    print(
        "A compound pipeline result cannot establish or falsify an individual "
        "stage. Only each paired ablation above speaks to that stage."
    )
    print("Nothing promoted. No configuration selected. Journaled results follow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
