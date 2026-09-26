#!/usr/bin/env python3
"""Execute the pre-registered trend-v8-blend study without selecting an arm."""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import run_trend_sleeve as v7  # noqa: E402
from woodland import backtest, bayes, cash, data, metrics, stats  # noqa: E402
from woodland.config import all_tickers, load_config  # noqa: E402
from woodland.harness import splits as split_helpers  # noqa: E402
from woodland.harness.ledger import TrialsLedger  # noqa: E402
from woodland.harness.splits import Split  # noqa: E402
from woodland.harness.walkforward import run_walkforward  # noqa: E402
from woodland.study import COSTS, PRIMARY_COST  # noqa: E402

STUDY = "trend-v8-blend"
MIX_COMPONENTS: dict[str, tuple[str, ...]] = {
    "trend_gold": ("trend", "gold"),
    "trend_defensive": ("trend", "defensive"),
    "gold_defensive": ("gold", "defensive"),
    "trend_gold_defensive": ("trend", "gold", "defensive"),
}
SINGLE_ARMS = ("trend", "gold", "defensive")
DEEP_SINGLE_ARMS = ("trend", "defensive")
DEEP_INFORMED_ARMS = frozenset({"trend", "defensive", "trend_defensive"})
SKEPTICAL_PRIOR = bayes.NormalBelief(0.0, 0.05, "skeptical N(0, 0.05^2)")
NEUTRAL_PRIOR = bayes.NormalBelief(0.0, 0.25, "neutral N(0, 0.25^2)")
LOSS = bayes.AllocationLoss(allocation_penalty=0.01)

ETF_V7_SHARPES = {
    ("trend", 0.1): 0.851378,
    ("trend", 0.2): 0.891745,
    ("trend", 0.3): 0.922157,
    ("gold", 0.1): 0.888777,
    ("gold", 0.2): 0.946354,
    ("gold", 0.3): 0.964911,
    ("defensive", 0.1): 0.815806,
    ("defensive", 0.2): 0.827332,
    ("defensive", 0.3): 0.839194,
}
DEEP_V7_SHARPES = {
    ("trend", 0.1): 0.867823,
    ("trend", 0.2): 0.879940,
    ("trend", 0.3): 0.887542,
    ("defensive", 0.1): 0.861663,
    ("defensive", 0.2): 0.873578,
    ("defensive", 0.3): 0.886349,
}


@dataclass(frozen=True)
class PairEvidence:
    """One paired comparison with a shared bootstrap likelihood and HAC check."""

    name_a: str
    name_b: str
    likelihood: bayes.BootstrapLikelihood
    ci_low: float
    ci_high: float
    p_value: float
    correlation: float
    hac: stats.SharpeComparison


def average_targets(targets: list[pd.DataFrame]) -> pd.DataFrame:
    """Equal-average complete portfolio target streams without selecting one."""
    if not targets:
        raise ValueError("at least one target frame is required")
    first = targets[0]
    if any(
        not frame.index.equals(first.index) or not frame.columns.equals(first.columns)
        for frame in targets[1:]
    ):
        raise ValueError("all target frames must have identical axes")
    decisions = pd.concat(
        [frame.notna().any(axis=1).rename(i) for i, frame in enumerate(targets)],
        axis=1,
    ).any(axis=1)
    output = pd.DataFrame(float("nan"), index=first.index, columns=first.columns)
    total = first.loc[decisions].fillna(0.0)
    for frame in targets[1:]:
        total = total.add(frame.loc[decisions].fillna(0.0))
    output.loc[decisions] = total / len(targets)
    gross = output.loc[decisions].sum(axis=1)
    if bool((gross > 1.0 + 1e-10).any()) or bool((output.loc[decisions] < -1e-10).any().any()):
        raise ValueError("averaged targets violate long-only gross exposure")
    return output


def _arm_key(arm: str, weight: float) -> tuple[str, float]:
    return arm, round(weight, 1)


def _v7_specs_by_arm(
    specs: list[v7.CurveSpec], *, deep: bool
) -> dict[tuple[str, float], v7.CurveSpec]:
    aliases = {"more_defensive": "defensive"}
    allowed = set(DEEP_SINGLE_ARMS if deep else SINGLE_ARMS)
    output: dict[tuple[str, float], v7.CurveSpec] = {}
    for spec in specs:
        arm = aliases.get(spec.curve_type, spec.curve_type)
        if arm in allowed:
            output[_arm_key(arm, spec.weight)] = spec
    return output


def build_etf_blends(
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[tuple[str, float], v7.CurveSpec], list[v7.CurveSpec]]:
    """Reconstruct v7 singles and build all 12 fixed ETF blend cells."""
    base, v7_specs = v7.build_etf_specs(prices)
    singles = _v7_specs_by_arm(v7_specs, deep=False)
    blends: list[v7.CurveSpec] = []
    for weight in v7.BLEND_WEIGHTS:
        for mix, components in MIX_COMPONENTS.items():
            component_specs = [singles[_arm_key(component, weight)] for component in components]
            blends.append(
                v7.CurveSpec(
                    label=f"{mix}:w={weight:.1f}",
                    curve_type=mix,
                    weight=weight,
                    config={
                        "study_version": STUDY,
                        "universe": "ETF",
                        "mix": mix,
                        "components": list(components),
                        "component_weights": [1.0 / len(components)] * len(components),
                        "total_sleeve_weight": weight,
                        "selection": "none; fixed preregistered mix curve",
                    },
                    targets=average_targets([spec.targets for spec in component_specs]),
                )
            )
    return base, singles, blends


def build_deep_blends(
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[tuple[str, float], v7.CurveSpec], list[v7.CurveSpec]]:
    """Build only the three exact deep-history trend+defensive analogues."""
    base, v7_specs = v7.build_deep_specs(prices)
    singles = _v7_specs_by_arm(v7_specs, deep=True)
    blends: list[v7.CurveSpec] = []
    for weight in v7.BLEND_WEIGHTS:
        components = [
            singles[_arm_key("trend", weight)],
            singles[_arm_key("defensive", weight)],
        ]
        blends.append(
            v7.CurveSpec(
                label=f"trend_defensive:w={weight:.1f}",
                curve_type="trend_defensive",
                weight=weight,
                config={
                    "study_version": STUDY,
                    "universe": "FF12",
                    "mix": "trend_defensive",
                    "components": ["trend", "defensive"],
                    "component_weights": [0.5, 0.5],
                    "total_sleeve_weight": weight,
                    "selection": "none; fixed preregistered mix curve",
                },
                targets=average_targets([spec.targets for spec in components]),
            )
        )
    return base, singles, blends


def _fixed_builder(
    targets: pd.DataFrame,
) -> Callable[[pd.DataFrame, dict], pd.DataFrame]:
    def build(_: pd.DataFrame, __: dict) -> pd.DataFrame:
        return targets

    return build


def evaluate_new_specs(
    prices: pd.DataFrame,
    specs: list[v7.CurveSpec],
    folds: list[Split],
    ledger: TrialsLedger,
    *,
    risk_free: pd.Series | None,
) -> list[v7.CurveResult]:
    """Use a one-config grid per arm so cross-arm selection is impossible."""
    output: list[v7.CurveResult] = []
    for spec in specs:
        result = run_walkforward(
            prices,
            _fixed_builder(spec.targets),
            [spec.config],
            splits=folds,
            ledger=ledger,
            study=STUDY,
            max_lookback_days=v7.MAX_LOOKBACK_DAYS,
            select_cost_bps=PRIMARY_COST,
            report_cost_bps=COSTS,
            risk_free=risk_free,
        )
        output.append(v7.CurveResult(spec, result.oos_returns, result.oos_turnover))
    return output


def evaluate_existing_arm(
    prices: pd.DataFrame,
    spec: v7.CurveSpec,
    folds: list[Split],
    *,
    risk_free: pd.Series | None,
) -> v7.CurveResult:
    """Reconstruct a counted v7 comparator without adding ledger rows."""
    index = pd.DatetimeIndex(prices.index)
    start = folds[0].validate_index(index)[0]
    end = folds[-1].validate_index(index)[-1]
    stitched = v7.stitch_targets(spec.targets, folds)
    returns: dict[float, pd.Series] = {}
    turnover: dict[float, pd.Series] = {}
    for cost_bps in COSTS:
        result = backtest.run(prices, stitched, cost_bps=cost_bps, risk_free=risk_free)
        returns[cost_bps] = result.returns.loc[start:end]
        turnover[cost_bps] = result.turnover.loc[start:end]
    arm = "defensive" if spec.curve_type == "more_defensive" else spec.curve_type
    display_spec = v7.CurveSpec(
        label=f"{arm}:w={spec.weight:.1f}",
        curve_type=arm,
        weight=spec.weight,
        config=spec.config,
        targets=spec.targets,
    )
    return v7.CurveResult(display_spec, returns, turnover)


def evaluate_market(
    prices: pd.DataFrame,
    ticker: str,
    folds: list[Split],
    *,
    risk_free: pd.Series | None,
) -> v7.CurveResult:
    index = pd.DatetimeIndex(prices.index)
    start = folds[0].validate_index(index)[0]
    end = folds[-1].validate_index(index)[-1]
    returns: dict[float, pd.Series] = {}
    turnover: dict[float, pd.Series] = {}
    for cost_bps in COSTS:
        result = backtest.buy_and_hold(
            prices, ticker, cost_bps=cost_bps, risk_free=risk_free
        )
        returns[cost_bps] = result.returns.loc[start:end]
        turnover[cost_bps] = result.turnover.loc[start:end]
    spec = v7.CurveSpec(
        label=f"{ticker} buy&hold",
        curve_type="market",
        weight=0.0,
        config={"benchmark": ticker},
        targets=pd.DataFrame(),
    )
    return v7.CurveResult(spec, returns, turnover)


def _result_map(results: list[v7.CurveResult]) -> dict[tuple[str, float], v7.CurveResult]:
    return {_arm_key(result.spec.curve_type, result.spec.weight): result for result in results}


def assert_v7_reconstruction(
    results: list[v7.CurveResult], expected: dict[tuple[str, float], float], label: str
) -> None:
    actual = _result_map(results)
    rows: list[dict[str, Any]] = []
    for key, journaled in expected.items():
        value = metrics.sharpe(actual[key].returns[PRIMARY_COST])
        if not math.isclose(value, journaled, abs_tol=0.0006):
            raise RuntimeError(
                f"{label} {key} reconstruction {value:.6f} != v7 {journaled:.6f}"
            )
        rows.append(
            {
                "arm": key[0],
                "weight": key[1],
                "rebuilt_sharpe_rf0": value,
                "v7_sharpe_rf0": journaled,
            }
        )
    v7.print_frame(f"{label} v7 single-arm reconstruction", pd.DataFrame(rows))


def pair_evidence(
    a: v7.CurveResult,
    b: v7.CurveResult,
    *,
    n_resamples: int,
) -> PairEvidence:
    returns_a = a.returns[PRIMARY_COST]
    returns_b = b.returns[PRIMARY_COST]
    likelihood = bayes.paired_sharpe_likelihood(
        returns_a,
        returns_b,
        n_resamples=n_resamples,
        block_length=21,
        seed=0,
        label=f"{a.spec.label} minus {b.spec.label}",
    )
    low, high = np.quantile(likelihood.draws, [0.025, 0.975])
    centred = np.abs(likelihood.draws - likelihood.point_estimate)
    p_value = float(
        (1 + int(np.sum(centred >= abs(likelihood.point_estimate))))
        / (likelihood.n_resamples + 1)
    )
    correlation = cast(
        float, pd.concat([returns_a, returns_b], axis=1).corr().iloc[0, 1]
    )
    hac = stats.ledoit_wolf_sharpe_test(
        returns_a,
        returns_b,
        name_a=a.spec.label,
        name_b=b.spec.label,
    )
    return PairEvidence(
        a.spec.label,
        b.spec.label,
        likelihood,
        float(low),
        float(high),
        p_value,
        correlation,
        hac,
    )


def evidence_row(evidence: PairEvidence) -> dict[str, Any]:
    return {
        "challenger": evidence.name_a,
        "comparator": evidence.name_b,
        "delta_sharpe_rf0": evidence.likelihood.point_estimate,
        "bootstrap_mean": evidence.likelihood.bootstrap_mean,
        "bootstrap_sd": evidence.likelihood.bootstrap_sd,
        "bootstrap_ci_low": evidence.ci_low,
        "bootstrap_ci_high": evidence.ci_high,
        "bootstrap_p": evidence.p_value,
        "correlation": evidence.correlation,
        "hac_ci_low": evidence.hac.ci_low,
        "hac_ci_high": evidence.hac.ci_high,
        "hac_p": evidence.hac.p_value,
        "hac_se": evidence.hac.standard_error,
        "n_resamples": evidence.likelihood.n_resamples,
        "block_length": evidence.likelihood.block_length,
    }


def freeze_deep_priors(
    deep_results: list[v7.CurveResult],
    deep_base: v7.CurveResult,
    *,
    n_resamples: int,
) -> tuple[
    dict[tuple[str, float], bayes.NormalBelief],
    dict[tuple[str, float], PairEvidence],
]:
    priors: dict[tuple[str, float], bayes.NormalBelief] = {}
    evidence: dict[tuple[str, float], PairEvidence] = {}
    for result in deep_results:
        key = _arm_key(result.spec.curve_type, result.spec.weight)
        paired = pair_evidence(result, deep_base, n_resamples=n_resamples)
        posterior = bayes.update_normal(paired.likelihood.normal, NEUTRAL_PRIOR)
        priors[key] = bayes.NormalBelief(
            posterior.mean,
            posterior.sd,
            label=f"deep-informed {result.spec.label} vs deep base",
        )
        evidence[key] = paired
    rows = []
    for key, prior in priors.items():
        paired = evidence[key]
        rows.append(
            {
                "arm": key[0],
                "weight": key[1],
                "deep_delta": paired.likelihood.point_estimate,
                "bootstrap_mean": paired.likelihood.bootstrap_mean,
                "likelihood_sd": paired.likelihood.bootstrap_sd,
                "frozen_prior_mean": prior.mean,
                "frozen_prior_sd": prior.sd,
                "n_resamples": paired.likelihood.n_resamples,
                "block_length": paired.likelihood.block_length,
            }
        )
    v7.print_frame(
        "DEEP PRIORS FROZEN — ETF RESULTS HAVE NOT BEEN COMPUTED",
        pd.DataFrame(rows),
    )
    return priors, evidence


def performance_table(
    results: list[v7.CurveResult], risk_free: pd.Series
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in results:
        for cost_bps in COSTS:
            returns = result.returns[cost_bps]
            rf = risk_free.reindex(returns.index).fillna(0.0)
            summary = metrics.summarize(
                returns,
                turnover=result.turnover[cost_bps],
                rf_daily=rf,
            )
            rows.append(
                {
                    "arm": result.spec.label,
                    "cost_bps": cost_bps,
                    "cagr": summary["cagr"],
                    "ann_vol": summary["ann_vol"],
                    "sharpe_rf0": summary["sharpe_rf0"],
                    "sharpe_real_rf": summary["sharpe_rf"],
                    "max_drawdown": summary["max_drawdown"],
                    "worst_day": returns.min(),
                    "left_tail_p05": returns.quantile(0.05),
                    "ann_turnover": summary["ann_turnover"],
                }
            )
    return pd.DataFrame(rows)


def posterior_rows(
    evidence: PairEvidence,
    *,
    deep_prior: bayes.NormalBelief | None,
) -> list[dict[str, Any]]:
    priors = [SKEPTICAL_PRIOR, NEUTRAL_PRIOR]
    if deep_prior is not None:
        priors.append(deep_prior)
    summaries: list[tuple[bayes.NormalBelief, bayes.DecisionSummary]] = []
    for prior in priors:
        posterior = bayes.update_normal(evidence.likelihood.normal, prior)
        summaries.append((prior, bayes.summarize_decision(posterior, LOSS)))
    flip = len({summary.lower_loss_action for _, summary in summaries}) > 1
    rows: list[dict[str, Any]] = []
    for prior, summary in summaries:
        prior_kind = (
            "deep_informed"
            if prior.label.startswith("deep-informed")
            else prior.label.split()[0]
        )
        rows.append(
            {
                "arm": evidence.name_a,
                "comparator": evidence.name_b,
                "prior": prior_kind,
                "prior_mean": prior.mean,
                "prior_sd": prior.sd,
                "posterior_mean": summary.posterior_mean,
                "credible_90_low": summary.credible_low,
                "credible_90_high": summary.credible_high,
                "p_delta_gt_0": summary.probability_positive,
                "p_delta_gt_005": summary.probability_above_005,
                "loss_allocate": summary.expected_loss_allocate,
                "loss_do_not_allocate": summary.expected_loss_do_not_allocate,
                "lower_loss_action": summary.lower_loss_action,
                "sensitivity_flip": "SENSITIVITY FLIP" if flip else "no",
                "comparison_status": (
                    "SUPPLEMENTARY; not cross-arm comparable"
                    if prior_kind == "deep_informed"
                    else "PRIOR-MATCHED"
                ),
            }
        )
    if deep_prior is None and "gold" in evidence.name_a:
        rows.append(
            {
                "arm": evidence.name_a,
                "comparator": evidence.name_b,
                "prior": "deep_informed",
                "prior_mean": float("nan"),
                "prior_sd": float("nan"),
                "posterior_mean": float("nan"),
                "credible_90_low": float("nan"),
                "credible_90_high": float("nan"),
                "p_delta_gt_0": float("nan"),
                "p_delta_gt_005": float("nan"),
                "loss_allocate": float("nan"),
                "loss_do_not_allocate": float("nan"),
                "lower_loss_action": "UNAVAILABLE",
                "sensitivity_flip": "not assessed",
                "comparison_status": (
                    "UNAVAILABLE — no vetted same-comparison deep gold evidence"
                ),
            }
        )
    return rows


def cross_arm_pairs(
    blends: list[v7.CurveResult], singles: list[v7.CurveResult]
) -> list[tuple[v7.CurveResult, v7.CurveResult, str]]:
    blend_map = _result_map(blends)
    single_map = _result_map(singles)
    pairs: list[tuple[v7.CurveResult, v7.CurveResult, str]] = []
    mix_names = list(MIX_COMPONENTS)
    for weight in v7.BLEND_WEIGHTS:
        for mix in mix_names:
            for single in SINGLE_ARMS:
                pairs.append(
                    (
                        blend_map[_arm_key(mix, weight)],
                        single_map[_arm_key(single, weight)],
                        "blend_vs_single",
                    )
                )
        for mix_a, mix_b in itertools.combinations(mix_names, 2):
            pairs.append(
                (
                    blend_map[_arm_key(mix_a, weight)],
                    blend_map[_arm_key(mix_b, weight)],
                    "blend_vs_blend",
                )
            )
    return pairs


def cross_arm_tables(
    pairs: list[tuple[v7.CurveResult, v7.CurveResult, str]],
    risk_free: pd.Series,
    *,
    n_resamples: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    classical: list[dict[str, Any]] = []
    posterior: list[dict[str, Any]] = []
    matched: list[dict[str, Any]] = []
    for challenger, comparator, category in pairs:
        evidence = pair_evidence(challenger, comparator, n_resamples=n_resamples)
        classical.append({"category": category, **evidence_row(evidence)})
        for prior in (SKEPTICAL_PRIOR, NEUTRAL_PRIOR):
            belief = bayes.update_normal(evidence.likelihood.normal, prior)
            low, high = belief.credible_interval(0.90)
            posterior.append(
                {
                    "category": category,
                    "challenger": evidence.name_a,
                    "comparator": evidence.name_b,
                    "prior": prior.label.split()[0],
                    "posterior_mean": belief.mean,
                    "credible_90_low": low,
                    "credible_90_high": high,
                    "p_delta_gt_0": belief.probability_above(0.0),
                    "p_delta_gt_005": belief.probability_above(0.05),
                    "prior_match": "YES — deep-informed excluded",
                }
            )
        if category == "blend_vs_single":
            for cost_bps in COSTS:
                matched_pair = v7.match_volatility(
                    challenger.returns[cost_bps],
                    comparator.returns[cost_bps],
                    risk_free,
                    name_a=challenger.spec.label,
                    name_b=comparator.spec.label,
                )
                a_metrics = _distribution_metrics(matched_pair.a)
                b_metrics = _distribution_metrics(matched_pair.b)
                matched.append(
                    {
                        "challenger": challenger.spec.label,
                        "comparator": comparator.spec.label,
                        "cost_bps": cost_bps,
                        "scaled_side": matched_pair.scaled_side,
                        "scale": matched_pair.scale,
                        "matched_vol": matched_pair.matched_vol,
                        **{f"challenger_{key}": value for key, value in a_metrics.items()},
                        **{f"comparator_{key}": value for key, value in b_metrics.items()},
                    }
                )
    return pd.DataFrame(classical), pd.DataFrame(posterior), pd.DataFrame(matched)


def _distribution_metrics(returns: pd.Series) -> dict[str, float]:
    return {
        "cagr": metrics.cagr(returns),
        "max_drawdown": metrics.max_drawdown(returns),
        "worst_day": float(returns.min()),
        "left_tail_p05": float(returns.quantile(0.05)),
    }


def base_inference_tables(
    arms: list[v7.CurveResult],
    base: v7.CurveResult,
    *,
    n_resamples: int,
    deep_priors: dict[tuple[str, float], bayes.NormalBelief] | None = None,
    existing_evidence: dict[tuple[str, float], PairEvidence] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[tuple[str, float], PairEvidence]]:
    classical: list[dict[str, Any]] = []
    posterior: list[dict[str, Any]] = []
    evidence_map: dict[tuple[str, float], PairEvidence] = {}
    for arm in arms:
        key = _arm_key(arm.spec.curve_type, arm.spec.weight)
        evidence = (
            existing_evidence[key]
            if existing_evidence is not None and key in existing_evidence
            else pair_evidence(arm, base, n_resamples=n_resamples)
        )
        evidence_map[key] = evidence
        classical.append(evidence_row(evidence))
        deep_prior = deep_priors.get(key) if deep_priors is not None else None
        posterior.extend(posterior_rows(evidence, deep_prior=deep_prior))
    return pd.DataFrame(classical), pd.DataFrame(posterior), evidence_map


def _subperiod_table(
    results: list[v7.CurveResult],
    risk_free: pd.Series,
    periods: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for period, (start, end) in periods.items():
        for result in results:
            returns = result.returns[PRIMARY_COST].loc[start:end]
            rf = risk_free.reindex(returns.index).fillna(0.0)
            summary = metrics.summarize(
                returns,
                turnover=result.turnover[PRIMARY_COST].reindex(returns.index),
                rf_daily=rf,
            )
            rows.append(
                {
                    "period": period,
                    "arm": result.spec.label,
                    "n_obs": len(returns),
                    "cagr": summary["cagr"],
                    "sharpe_rf0": summary["sharpe_rf0"],
                    "sharpe_real_rf": summary["sharpe_rf"],
                    "max_drawdown": summary["max_drawdown"],
                    "ann_turnover": summary["ann_turnover"],
                }
            )
    return pd.DataFrame(rows)


def _print_sensitivity_alerts(table: pd.DataFrame, universe: str) -> None:
    available = table[table["lower_loss_action"] != "UNAVAILABLE"]
    flips = available.loc[
        available["sensitivity_flip"] == "SENSITIVITY FLIP", "arm"
    ].unique()
    if len(flips):
        print(f"\nSENSITIVITY FLIP — {universe}: lower-loss action changes by prior for:")
        for arm in flips:
            print(f"  {arm}")
    else:
        print(f"\nNo sensitivity flip in lower-loss action for {universe} arms.")


def _prepare_folds(index: pd.DatetimeIndex, expected: int) -> list[Split]:
    folds = split_helpers.make_splits(
        index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=v7.MAX_LOOKBACK_DAYS,
    )
    split_helpers.check_embargo_covers_lookback(folds, index, v7.MAX_LOOKBACK_DAYS)
    if len(folds) != expected:
        raise RuntimeError(f"expected {expected} folds, got {len(folds)}")
    return folds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    parser.add_argument("--resamples", type=int, default=10_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.resamples < 2:
        raise ValueError("--resamples must be at least two")

    with TrialsLedger(args.ledger) as ledger:
        if STUDY in ledger.studies():
            raise RuntimeError(f"ledger already contains {STUDY!r}; refusing duplicate rows")

        print("PHASE 1: DEEP HISTORY — priors must freeze before ETF evaluation")
        deep_prices = v7.load_deep_prices(args.data)
        deep_index = pd.DatetimeIndex(deep_prices.index)
        deep_folds = _prepare_folds(deep_index, 95)
        v7._check_window(  # noqa: SLF001
            deep_prices,
            deep_folds,
            expected_start=v7.DEEP_EXPECTED_START,
            expected_end=v7.DEEP_EXPECTED_END,
            expected_bars=v7.DEEP_EXPECTED_BARS,
        )
        deep_rf = deep_prices["CASH"].pct_change().fillna(0.0)
        deep_base_targets, deep_single_specs, deep_blend_specs = build_deep_blends(
            deep_prices
        )
        deep_base = v7.evaluate_base(
            prices=deep_prices,
            base_targets=deep_base_targets,
            folds=deep_folds,
            engine_risk_free=None,
        )
        deep_singles = [
            evaluate_existing_arm(
                deep_prices, spec, deep_folds, risk_free=None
            )
            for spec in deep_single_specs.values()
        ]
        assert_v7_reconstruction(deep_singles, DEEP_V7_SHARPES, "Deep history")
        deep_blends = evaluate_new_specs(
            deep_prices, deep_blend_specs, deep_folds, ledger, risk_free=None
        )
        deep_prior_arms = [*deep_singles, *deep_blends]
        frozen_priors, deep_evidence = freeze_deep_priors(
            deep_prior_arms, deep_base, n_resamples=args.resamples
        )

        print("\nPHASE 2: ETF — beginning only after deep priors are frozen above")
        config = load_config()
        etf_prices, _ = data.drop_suspect_dates(
            data.build_matrix(all_tickers(config), args.data)
        )
        etf_index = pd.DatetimeIndex(etf_prices.index)
        etf_folds = _prepare_folds(etf_index, 22)
        v7._check_window(  # noqa: SLF001
            etf_prices,
            etf_folds,
            expected_start=v7.ETF_EXPECTED_START,
            expected_end=v7.ETF_EXPECTED_END,
            expected_bars=v7.ETF_EXPECTED_BARS,
        )
        etf_rf, rf_provenance = cash.align_risk_free(
            cash.load_risk_free_daily(args.data), etf_index
        )
        print(
            f"risk-free: {rf_provenance['source_first']}..{rf_provenance['source_last']}; "
            f"{rf_provenance['n_carried_forward']} bars carried forward"
        )
        etf_base_targets, etf_single_specs, etf_blend_specs = build_etf_blends(
            etf_prices
        )
        etf_base = v7.evaluate_base(
            prices=etf_prices,
            base_targets=etf_base_targets,
            folds=etf_folds,
            engine_risk_free=etf_rf,
        )
        etf_singles = [
            evaluate_existing_arm(etf_prices, spec, etf_folds, risk_free=etf_rf)
            for spec in etf_single_specs.values()
        ]
        assert_v7_reconstruction(etf_singles, ETF_V7_SHARPES, "ETF")
        etf_blends = evaluate_new_specs(
            etf_prices, etf_blend_specs, etf_folds, ledger, risk_free=etf_rf
        )

        deep_market = evaluate_market(
            deep_prices, "MKT", deep_folds, risk_free=None
        )
        etf_market = evaluate_market(etf_prices, "SPY", etf_folds, risk_free=etf_rf)

        print("\n\nUNIVERSE B — DEEP-HISTORY PRIOR ARM REPORT")
        print("#" * 49)
        print("Frictionless academic data; 60% MKT / 40% CASH is not a duration 60/40.")
        deep_all = [deep_base, deep_market, *deep_singles, *deep_blends]
        v7.print_frame(
            "Deep performance — 0/5/10 bps",
            performance_table(deep_all, deep_rf),
        )
        deep_classical, deep_posteriors, _ = base_inference_tables(
            deep_prior_arms,
            deep_base,
            n_resamples=args.resamples,
            existing_evidence=deep_evidence,
        )
        v7.print_frame("Deep paired inference vs base — 5 bps", deep_classical)
        v7.print_frame(
            "Deep posterior under skeptical and neutral priors — 5 bps",
            deep_posteriors,
        )
        v7.print_frame(
            "Deep decades — 5 bps",
            _subperiod_table(
                deep_all,
                deep_rf,
                v7.decade_periods(pd.DatetimeIndex(deep_base.returns[PRIMARY_COST].index)),
            ),
        )
        v7.print_frame(
            "Deep DSR diagnostics — new fixed blends only",
            v7.dsr_table(deep_blends, ledger, STUDY),
        )

        print("\n\nUNIVERSE A — ETF BLEND REPORT")
        print("#" * 31)
        print(
            "EVIDENCE BASE UNEVEN: trend has 94 years behind it; gold has 22. "
            "Deep-informed priors are unavailable for every gold-containing arm."
        )
        print(
            "All cross-arm tables are PRIOR-MATCHED using skeptical and neutral "
            "priors only. No mix or weight is selected or called best."
        )
        etf_all = [etf_base, etf_market, *etf_singles, *etf_blends]
        v7.print_frame(
            "ETF performance — 0/5/10 bps",
            performance_table(etf_all, etf_rf),
        )
        etf_base_classical, etf_posteriors, _ = base_inference_tables(
            [*etf_singles, *etf_blends],
            etf_base,
            n_resamples=args.resamples,
            deep_priors=frozen_priors,
        )
        v7.print_frame("ETF paired inference vs base — 5 bps", etf_base_classical)
        v7.print_frame(
            "ETF allocation posteriors and expected loss vs base — 5 bps",
            etf_posteriors,
        )
        _print_sensitivity_alerts(etf_posteriors, "ETF")

        pairs = cross_arm_pairs(etf_blends, etf_singles)
        if len(pairs) != 54:
            raise RuntimeError(f"expected 54 ETF cross-arm pairs, got {len(pairs)}")
        cross_classical, cross_posteriors, matched = cross_arm_tables(
            pairs, etf_rf, n_resamples=args.resamples
        )
        v7.print_frame(
            "ETF cross-arm paired inference — 5 bps, 54 fixed pairs",
            cross_classical,
        )
        v7.print_frame(
            "ETF cross-arm Bayesian posteriors — PRIOR-MATCHED ONLY",
            cross_posteriors,
        )
        v7.print_frame(
            "ETF blend vs single matched-vol distributions — Sharpe excluded",
            matched,
        )
        v7.print_frame(
            "ETF default sub-periods — 5 bps",
            _subperiod_table(etf_all, etf_rf, v7.ETF_SUBPERIODS),
        )
        v7.print_frame(
            "ETF DSR diagnostics — new fixed blends only",
            v7.dsr_table(etf_blends, ledger, STUDY),
        )

        print(
            f"\nLedger audit: {ledger.n_trials(STUDY)} distinct configurations; "
            f"{ledger.n_trials(STUDY, distinct=False)} fold rows."
        )
        if ledger.n_trials(STUDY) != 15 or ledger.n_trials(STUDY, distinct=False) != 549:
            raise RuntimeError("v8 ledger count differs from preregistered 15/549")

    print("\nGold deep prior remains UNAVAILABLE; no substitute or new data was used.")
    print(
        "Bretton Woods warning: future floating-gold history is ~55 years with a "
        "1971 structural break and requires a separate dual-source data decision."
    )
    print("Final Phase 2 blend study. Nothing selected or promoted.")


if __name__ == "__main__":
    main()
