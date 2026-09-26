#!/usr/bin/env python3
"""Execute the pre-registered trend-v7 sleeve weight curves.

This script evaluates fixed blend-weight curves.  It never selects a weight,
and it writes only trials-ledger rows: the human-reviewed study result belongs
in the append-only journal after stdout has been reviewed.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from woodland import backtest, cash, data, metrics, stats  # noqa: E402
from woodland.config import all_tickers, load_config  # noqa: E402
from woodland.harness import deflated  # noqa: E402
from woodland.harness import splits as split_helpers  # noqa: E402
from woodland.harness.ledger import TrialsLedger  # noqa: E402
from woodland.harness.splits import Split  # noqa: E402
from woodland.harness.walkforward import run_walkforward  # noqa: E402
from woodland.signals import trend  # noqa: E402
from woodland.study import (  # noqa: E402
    COSTS,
    DEEP_EXPECTED_BARS,
    DEEP_INDUSTRIES,
    ETF_EXPECTED_BARS,
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    MULTI_ASSET,
    PRIMARY_COST,
    SECTORS,
    stitch_targets,
)

ETF_STUDY = "trend-v7-sleeve-etf"
DEEP_STUDY = "trend-v7-sleeve-deep"
BLEND_WEIGHTS = (0.1, 0.2, 0.3)
ETF_CURVE_TYPES = ("trend", "more_defensive", "gold", "static_multiasset")
DEEP_CURVE_TYPES = ("trend", "more_defensive", "static_equity")
ETF_EXPECTED_START = pd.Timestamp("2004-10-22")
ETF_EXPECTED_END = pd.Timestamp("2026-09-01")
DEEP_EXPECTED_START = pd.Timestamp("1932-03-15")
DEEP_EXPECTED_END = pd.Timestamp("2026-06-30")

ETF_SUBPERIODS = {
    "2004-2007": ("2004-10-22", "2007-12-31"),
    "2008-2014": ("2008-01-01", "2014-12-31"),
    "2015-2019": ("2015-01-01", "2019-12-31"),
    "2020-2021": ("2020-01-01", "2021-12-31"),
    "2022-2026": ("2022-01-01", "2026-09-01"),
}


@dataclass(frozen=True)
class CurveSpec:
    """One fixed, pre-registered point on a weight curve."""

    label: str
    curve_type: str
    weight: float
    config: dict[str, Any]
    targets: pd.DataFrame


@dataclass(frozen=True)
class CurveResult:
    """OOS results for one fixed point under every cost assumption."""

    spec: CurveSpec
    returns: dict[float, pd.Series]
    turnover: dict[float, pd.Series]


@dataclass(frozen=True)
class VolMatchedPair:
    """Two series after scaling only the more volatile side's excess returns."""

    a: pd.Series
    b: pd.Series
    scaled_side: str
    scale: float
    matched_vol: float


def monthly_static_targets(
    prices: pd.DataFrame, weights: dict[str, float]
) -> pd.DataFrame:
    """Monthly fixed targets; unavailable assets remain residual cash.

    Missing assets are deliberately not re-normalized.  This makes the ETF
    static controls causal before every constituent's inception and keeps
    gross exposure at or below one.
    """
    unknown = set(weights).difference(prices.columns)
    if unknown:
        raise ValueError(f"target assets absent from price matrix: {sorted(unknown)}")
    if any(weight < 0 for weight in weights.values()) or sum(weights.values()) > 1.0 + 1e-12:
        raise ValueError("weights must be non-negative and sum to at most 1")

    targets = pd.DataFrame(float("nan"), index=prices.index, columns=prices.columns)
    for decision_date in trend.month_end_index(prices):
        row = pd.Series(0.0, index=prices.columns)
        for asset, weight in weights.items():
            if pd.notna(prices.at[decision_date, asset]):
                row[asset] = weight
        targets.loc[decision_date] = row
    return targets


def blend_targets(
    base: pd.DataFrame, sleeve: pd.DataFrame, weight: float
) -> pd.DataFrame:
    """Blend two causal target streams at every union decision date."""
    if not 0.0 <= weight <= 1.0:
        raise ValueError("blend weight must be in [0, 1]")
    if not base.index.equals(sleeve.index) or not base.columns.equals(sleeve.columns):
        raise ValueError("base and sleeve targets must have identical axes")

    decisions = base.notna().any(axis=1) | sleeve.notna().any(axis=1)
    out = pd.DataFrame(float("nan"), index=base.index, columns=base.columns)
    base_rows = base.loc[decisions].fillna(0.0)
    sleeve_rows = sleeve.loc[decisions].fillna(0.0)
    out.loc[decisions] = (1.0 - weight) * base_rows + weight * sleeve_rows
    gross = out.loc[decisions].sum(axis=1)
    if bool((gross > 1.0 + 1e-10).any()):
        raise ValueError("blended targets exceed gross exposure 1.0")
    return out


def _fixed_curve_config(
    *, universe: str, curve_type: str, weight: float, sleeve_assets: list[str]
) -> dict[str, Any]:
    return {
        "study_version": "trend-v7-sleeve",
        "universe": universe,
        "curve_type": curve_type,
        "blend_weight": weight,
        "lookbacks_months": LOOKBACKS if curve_type == "trend" else None,
        "sleeve_assets": sleeve_assets,
        "selection": "none; fixed pre-registered weight curve",
    }


def build_etf_specs(prices: pd.DataFrame) -> tuple[pd.DataFrame, list[CurveSpec]]:
    """Construct the 12 ETF configurations without evaluating or selecting."""
    base = monthly_static_targets(prices, {"SPY": 0.60, "IEF": 0.40})
    trend_sleeve = trend.ensemble_targets(
        prices, MULTI_ASSET, LOOKBACKS, risk_off=None
    )
    gold_sleeve = monthly_static_targets(prices, {"GLD": 1.0})
    static_sleeve = monthly_static_targets(
        prices, {asset: 1.0 / len(MULTI_ASSET) for asset in MULTI_ASSET}
    )
    specs: list[CurveSpec] = []
    for weight in BLEND_WEIGHTS:
        targets_by_type = {
            "trend": blend_targets(base, trend_sleeve, weight),
            "more_defensive": monthly_static_targets(
                prices,
                {"SPY": 0.60 - 0.20 * weight, "IEF": 0.40 + 0.20 * weight},
            ),
            "gold": blend_targets(base, gold_sleeve, weight),
            "static_multiasset": blend_targets(base, static_sleeve, weight),
        }
        sleeve_assets = {
            "trend": MULTI_ASSET,
            "more_defensive": ["SPY", "IEF"],
            "gold": ["GLD"],
            "static_multiasset": MULTI_ASSET,
        }
        for curve_type in ETF_CURVE_TYPES:
            specs.append(
                CurveSpec(
                    label=f"{curve_type}:w={weight:.1f}",
                    curve_type=curve_type,
                    weight=weight,
                    config=_fixed_curve_config(
                        universe="ETF",
                        curve_type=curve_type,
                        weight=weight,
                        sleeve_assets=sleeve_assets[curve_type],
                    ),
                    targets=targets_by_type[curve_type],
                )
            )
    return base, specs


def build_deep_specs(prices: pd.DataFrame) -> tuple[pd.DataFrame, list[CurveSpec]]:
    """Construct the 9 deep-history configurations, with no gold substitute."""
    base = monthly_static_targets(prices, {"MKT": 0.60, "CASH": 0.40})
    trend_sleeve = trend.ensemble_targets(
        prices, DEEP_INDUSTRIES, LOOKBACKS, risk_off="CASH"
    )
    static_sleeve = monthly_static_targets(
        prices, {asset: 1.0 / len(DEEP_INDUSTRIES) for asset in DEEP_INDUSTRIES}
    )
    specs: list[CurveSpec] = []
    for weight in BLEND_WEIGHTS:
        targets_by_type = {
            "trend": blend_targets(base, trend_sleeve, weight),
            "more_defensive": monthly_static_targets(
                prices,
                {"MKT": 0.60 - 0.20 * weight, "CASH": 0.40 + 0.20 * weight},
            ),
            "static_equity": blend_targets(base, static_sleeve, weight),
        }
        sleeve_assets = {
            "trend": DEEP_INDUSTRIES,
            "more_defensive": ["MKT", "CASH"],
            "static_equity": DEEP_INDUSTRIES,
        }
        for curve_type in DEEP_CURVE_TYPES:
            specs.append(
                CurveSpec(
                    label=f"{curve_type}:w={weight:.1f}",
                    curve_type=curve_type,
                    weight=weight,
                    config=_fixed_curve_config(
                        universe="FF12",
                        curve_type=curve_type,
                        weight=weight,
                        sleeve_assets=sleeve_assets[curve_type],
                    ),
                    targets=targets_by_type[curve_type],
                )
            )
    return base, specs


def load_deep_prices(store: Path) -> pd.DataFrame:
    """Load the frozen v4 FF12 price matrix and require identical calendars."""
    industry_path = store / "fama_french_12_industry_daily.parquet"
    factor_path = store / "fama_french_factors_daily.parquet"
    industries = pd.read_parquet(industry_path)
    factors = pd.read_parquet(factor_path)
    if not industries.index.equals(factors.index):
        raise ValueError("Fama-French industry and factor calendars do not match")
    prices = industries.loc[:, DEEP_INDUSTRIES].join(factors.loc[:, ["MKT", "CASH"]])
    if bool(prices.isna().any().any()):
        raise ValueError("deep-history price matrix contains missing values")
    return prices


def _oos_window(
    folds: list[Split],
) -> tuple[pd.Timestamp, pd.Timestamp]:
    return folds[0].validate_start, folds[-1].validate_end


def _check_window(
    prices: pd.DataFrame,
    folds: list[Split],
    *,
    expected_start: pd.Timestamp,
    expected_end: pd.Timestamp,
    expected_bars: int,
) -> None:
    start, end = _oos_window(folds)
    oos_index = prices.index[(prices.index >= start) & (prices.index < end)]
    bars = len(oos_index)
    actual_end = pd.Timestamp(oos_index[-1])
    if start != expected_start or actual_end != expected_end or bars != expected_bars:
        raise RuntimeError(
            "frozen OOS window mismatch: "
            f"got {start.date()}..{actual_end.date()} ({bars:,} bars), expected "
            f"{expected_start.date()}..{expected_end.date()} ({expected_bars:,} bars)"
        )


def evaluate_curves(
    *,
    prices: pd.DataFrame,
    specs: list[CurveSpec],
    folds: list[Split],
    study: str,
    ledger: TrialsLedger,
    engine_risk_free: pd.Series | None,
) -> list[CurveResult]:
    """Run each fixed point as a one-config walk-forward evaluation.

    A one-item grid delegates all validation-window access and ledger writes to
    the project harness while making cross-weight selection impossible.
    """
    if study in ledger.studies():
        raise RuntimeError(
            f"ledger already contains {study!r}; refusing to append duplicate rows"
        )
    output: list[CurveResult] = []
    for spec in specs:
        result = run_walkforward(
            prices,
            _fixed_target_builder(spec.targets),
            [spec.config],
            splits=folds,
            ledger=ledger,
            study=study,
            max_lookback_days=MAX_LOOKBACK_DAYS,
            select_cost_bps=PRIMARY_COST,
            report_cost_bps=COSTS,
            risk_free=engine_risk_free,
        )
        output.append(
            CurveResult(
                spec=spec,
                returns=result.oos_returns,
                turnover=result.oos_turnover,
            )
        )
    return output


def _fixed_target_builder(
    targets: pd.DataFrame,
) -> Callable[[pd.DataFrame, dict], pd.DataFrame]:
    def build(_: pd.DataFrame, __: dict) -> pd.DataFrame:
        return targets

    return build


def evaluate_base(
    *,
    prices: pd.DataFrame,
    base_targets: pd.DataFrame,
    folds: list[Split],
    engine_risk_free: pd.Series | None,
) -> CurveResult:
    """Evaluate w=0 incumbent without recording it as a trial."""
    index = pd.DatetimeIndex(prices.index)
    start = folds[0].validate_index(index)[0]
    end = folds[-1].validate_index(index)[-1]
    returns_by_cost: dict[float, pd.Series] = {}
    turnover_by_cost: dict[float, pd.Series] = {}
    for cost_bps in COSTS:
        result = backtest.run(
            prices, base_targets, cost_bps=cost_bps, risk_free=engine_risk_free
        )
        returns_by_cost[cost_bps] = result.returns.loc[start:end]
        turnover_by_cost[cost_bps] = result.turnover.loc[start:end]
    base_spec = CurveSpec(
        label="base:w=0.0",
        curve_type="base",
        weight=0.0,
        config={"curve_type": "base", "blend_weight": 0.0},
        targets=base_targets,
    )
    return CurveResult(base_spec, returns_by_cost, turnover_by_cost)


def match_volatility(
    a: pd.Series,
    b: pd.Series,
    risk_free: pd.Series,
    *,
    name_a: str,
    name_b: str,
) -> VolMatchedPair:
    """Scale the more volatile side down via rf + scale * excess return."""
    common = a.index.intersection(b.index)
    aligned = pd.DataFrame(
        {
            "a": a.reindex(common),
            "b": b.reindex(common),
            "rf": risk_free.reindex(common),
        }
    ).dropna()
    vol_a = float(aligned["a"].std(ddof=1) * math.sqrt(252))
    vol_b = float(aligned["b"].std(ddof=1) * math.sqrt(252))
    if vol_a <= 0 or vol_b <= 0:
        raise ValueError("volatility matching requires two non-degenerate series")
    if vol_a > vol_b:
        scale = vol_b / vol_a
        matched_a = aligned["rf"] + scale * (aligned["a"] - aligned["rf"])
        return VolMatchedPair(matched_a, aligned["b"], name_a, scale, vol_b)
    if vol_b > vol_a:
        scale = vol_a / vol_b
        matched_b = aligned["rf"] + scale * (aligned["b"] - aligned["rf"])
        return VolMatchedPair(aligned["a"], matched_b, name_b, scale, vol_a)
    return VolMatchedPair(aligned["a"], aligned["b"], "neither", 1.0, vol_a)


def _distribution_metrics(returns: pd.Series) -> dict[str, float]:
    return {
        "cagr": metrics.cagr(returns),
        "max_drawdown": metrics.max_drawdown(returns),
        "worst_day": float(returns.min()),
        "left_tail_p05": float(returns.quantile(0.05)),
    }


def print_frame(title: str, frame: pd.DataFrame) -> None:
    print(f"\n{title}")
    print("=" * len(title))
    with pd.option_context(
        "display.max_rows", None,
        "display.max_columns", None,
        "display.width", 240,
        "display.float_format", lambda value: f"{value:.6f}",
    ):
        print(frame.to_string(index=False))


def metrics_table(
    curves: list[CurveResult], base: CurveResult, risk_free: pd.Series
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in [base, *curves]:
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
                    "curve": result.spec.label,
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


def inference_vs_base_table(
    curves: list[CurveResult],
    base: CurveResult,
    *,
    n_resamples: int,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    base_returns = base.returns[PRIMARY_COST]
    for result in curves:
        returns = result.returns[PRIMARY_COST]
        bootstrap = stats.bootstrap_sharpe_difference(
            returns,
            base_returns,
            name_a=result.spec.label,
            name_b=base.spec.label,
            n_resamples=n_resamples,
            block_length=21,
        )
        hac = stats.ledoit_wolf_sharpe_test(
            returns,
            base_returns,
            name_a=result.spec.label,
            name_b=base.spec.label,
        )
        correlation = cast(
            float, pd.concat([returns, base_returns], axis=1).corr().iloc[0, 1]
        )
        rows.append(
            {
                "curve": result.spec.label,
                "cost_bps": PRIMARY_COST,
                "correlation_vs_base": correlation,
                "delta_sharpe_rf0": bootstrap.difference,
                "bootstrap_ci_low": bootstrap.ci_low,
                "bootstrap_ci_high": bootstrap.ci_high,
                "bootstrap_p": bootstrap.p_value,
                "hac_ci_low": hac.ci_low,
                "hac_ci_high": hac.ci_high,
                "hac_p": hac.p_value,
                "hac_se": hac.standard_error,
            }
        )
    return pd.DataFrame(rows)


def matched_vs_base_table(
    curves: list[CurveResult], base: CurveResult, risk_free: pd.Series
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for result in curves:
        for cost_bps in COSTS:
            pair = match_volatility(
                result.returns[cost_bps],
                base.returns[cost_bps],
                risk_free,
                name_a=result.spec.label,
                name_b=base.spec.label,
            )
            a_metrics = _distribution_metrics(pair.a)
            b_metrics = _distribution_metrics(pair.b)
            rows.append(
                {
                    "curve": result.spec.label,
                    "cost_bps": cost_bps,
                    "scaled_side": pair.scaled_side,
                    "scale": pair.scale,
                    "matched_vol": pair.matched_vol,
                    **{f"curve_{key}": value for key, value in a_metrics.items()},
                    **{f"base_{key}": value for key, value in b_metrics.items()},
                }
            )
    return pd.DataFrame(rows)


def _result_lookup(curves: list[CurveResult]) -> dict[tuple[str, float], CurveResult]:
    return {(result.spec.curve_type, result.spec.weight): result for result in curves}


def controls_vs_trend_table(
    curves: list[CurveResult], risk_free: pd.Series
) -> pd.DataFrame:
    """Matched-vol distribution and unscaled Sharpe for every same-w control."""
    lookup = _result_lookup(curves)
    control_types = sorted({result.spec.curve_type for result in curves}.difference({"trend"}))
    rows: list[dict[str, Any]] = []
    for weight in BLEND_WEIGHTS:
        trend_result = lookup[("trend", weight)]
        for control_type in control_types:
            control = lookup[(control_type, weight)]
            for cost_bps in COSTS:
                trend_returns = trend_result.returns[cost_bps]
                control_returns = control.returns[cost_bps]
                pair = match_volatility(
                    trend_returns,
                    control_returns,
                    risk_free,
                    name_a=trend_result.spec.label,
                    name_b=control.spec.label,
                )
                trend_metrics = _distribution_metrics(pair.a)
                control_metrics = _distribution_metrics(pair.b)
                rf = risk_free.reindex(trend_returns.index).fillna(0.0)
                rows.append(
                    {
                        "weight": weight,
                        "control": control_type,
                        "cost_bps": cost_bps,
                        "correlation": cast(
                            float,
                            pd.concat([trend_returns, control_returns], axis=1)
                            .corr()
                            .iloc[0, 1]
                        ),
                        "trend_sharpe_rf0_unscaled": metrics.sharpe(trend_returns),
                        "control_sharpe_rf0_unscaled": metrics.sharpe(control_returns),
                        "trend_sharpe_real_rf_unscaled": metrics.sharpe(
                            metrics.excess_returns(trend_returns, rf)
                        ),
                        "control_sharpe_real_rf_unscaled": metrics.sharpe(
                            metrics.excess_returns(control_returns, rf)
                        ),
                        "scaled_side": pair.scaled_side,
                        "scale": pair.scale,
                        "matched_vol": pair.matched_vol,
                        **{f"trend_{key}": value for key, value in trend_metrics.items()},
                        **{
                            f"control_{key}": value
                            for key, value in control_metrics.items()
                        },
                    }
                )
    return pd.DataFrame(rows)


def subperiod_table(
    curves: list[CurveResult],
    base: CurveResult,
    risk_free: pd.Series,
    periods: dict[str, tuple[str, str]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, (start, end) in periods.items():
        for result in [base, *curves]:
            returns = result.returns[PRIMARY_COST].loc[start:end]
            rf = risk_free.reindex(returns.index).fillna(0.0)
            summary = metrics.summarize(
                returns,
                turnover=result.turnover[PRIMARY_COST].reindex(returns.index),
                rf_daily=rf,
            )
            rows.append(
                {
                    "period": name,
                    "curve": result.spec.label,
                    "n_obs": len(returns),
                    "cagr": summary["cagr"],
                    "sharpe_rf0": summary["sharpe_rf0"],
                    "sharpe_real_rf": summary["sharpe_rf"],
                    "max_drawdown": summary["max_drawdown"],
                    "ann_turnover": summary["ann_turnover"],
                }
            )
    return pd.DataFrame(rows)


def decade_periods(index: pd.DatetimeIndex) -> dict[str, tuple[str, str]]:
    periods: dict[str, tuple[str, str]] = {}
    first_decade = int(index.min().year // 10 * 10)
    last_decade = int(index.max().year // 10 * 10)
    for decade in range(first_decade, last_decade + 1, 10):
        start = max(index.min(), pd.Timestamp(f"{decade}-01-01"))
        end = min(index.max(), pd.Timestamp(f"{decade + 9}-12-31"))
        periods[f"{decade}s"] = (str(start.date()), str(end.date()))
    return periods


def dsr_table(
    curves: list[CurveResult], ledger: TrialsLedger, study: str
) -> pd.DataFrame:
    ledger_trials = ledger.n_trials(study)
    rows: list[dict[str, Any]] = []
    for result in curves:
        observed_sharpe = metrics.sharpe(result.returns[PRIMARY_COST])
        report = deflated.deflated_sharpe(
            result.returns[PRIMARY_COST],
            1,
            trial_sharpes=pd.Series([observed_sharpe]),
        )
        rows.append(
            {
                "curve": result.spec.label,
                "dsr_effective_trials": report["n_trials"],
                "ledger_curve_configs": ledger_trials,
                "sharpe_rf0": report["sharpe_annual"],
                "sr0": report["sr0_annual"],
                "dsr": report["dsr"],
                "trial_sharpe_sd": report["trial_sharpe_sd_annual"],
                "effective_breadth_note": (
                    "one pre-registered config per row, no selection: SR0=0 and "
                    "DSR is vacuous; paired tests are load-bearing"
                ),
            }
        )
    return pd.DataFrame(rows)


def _run_sanity_check(
    prices: pd.DataFrame,
    folds: list[Split],
    risk_free: pd.Series,
) -> None:
    v2_targets = trend.ensemble_targets(prices, SECTORS, LOOKBACKS, risk_off="IEF")
    v6_targets = trend.ensemble_targets(prices, MULTI_ASSET, LOOKBACKS, risk_off=None)
    start, end = _oos_window(folds)
    rows: list[dict[str, float | str]] = []
    for name, targets, expected in (
        ("trend-v2-ensemble", v2_targets, 0.700),
        ("trend-v6-multiasset", v6_targets, 0.781),
    ):
        result = backtest.run(
            prices,
            stitch_targets(targets, folds),
            cost_bps=PRIMARY_COST,
            risk_free=risk_free,
        )
        oos = (result.returns.index >= start) & (result.returns.index < end)
        returns = result.returns.loc[oos]
        sharpe_rf0 = metrics.sharpe(returns)
        sharpe_real_rf = metrics.sharpe(
            metrics.excess_returns(returns, risk_free.reindex(returns.index).fillna(0.0))
        )
        if not math.isclose(sharpe_rf0, expected, abs_tol=0.003):
            raise RuntimeError(
                f"{name} sanity mismatch: got {sharpe_rf0:.6f}, expected {expected:.3f}"
            )
        rows.append(
            {
                "series": name,
                "cost_bps": PRIMARY_COST,
                "sharpe_rf0": sharpe_rf0,
                "sharpe_real_rf": sharpe_real_rf,
                "journaled_sharpe_rf0": expected,
            }
        )
    print_frame("ETF v2/v6 reconstruction sanity check", pd.DataFrame(rows))


def _print_universe_results(
    *,
    title: str,
    curves: list[CurveResult],
    base: CurveResult,
    risk_free: pd.Series,
    ledger: TrialsLedger,
    study: str,
    n_resamples: int,
    periods: dict[str, tuple[str, str]],
) -> None:
    print(f"\n\n{title}")
    print("#" * len(title))
    print(
        "Blend weights are reported as a CURVE with no selection. Calling any "
        "single weight 'best' later is selection and requires adding that choice "
        "to the trials count. w=0.0 is the incumbent and is not a trial."
    )
    print_frame(
        "Unscaled metrics and turnover — all cost scenarios",
        metrics_table(curves, base, risk_free),
    )
    print_frame(
        "Paired Sharpe inference vs unmodified base — 5 bps, unscaled, rf=0",
        inference_vs_base_table(curves, base, n_resamples=n_resamples),
    )
    print_frame(
        "Vol-matched distribution metrics vs base — more volatile side scaled down",
        matched_vs_base_table(curves, base, risk_free),
    )
    print_frame(
        "Trend sleeve vs same-weight controls — Sharpes unscaled; distribution matched",
        controls_vs_trend_table(curves, risk_free),
    )
    print_frame("Sub-periods — 5 bps", subperiod_table(curves, base, risk_free, periods))
    print_frame("Deflated Sharpe diagnostics — 5 bps", dsr_table(curves, ledger, study))
    print(
        f"\nLedger audit for {study}: {ledger.n_trials(study)} distinct configurations, "
        f"{len(ledger.trials(study))} fold rows."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data")
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    parser.add_argument(
        "--resamples",
        type=int,
        default=10_000,
        help="paired stationary-bootstrap resamples (authoritative run: 10000)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.resamples < 1:
        raise ValueError("--resamples must be positive")

    config = load_config()
    etf_prices, _ = data.drop_suspect_dates(
        data.build_matrix(all_tickers(config), args.data)
    )
    etf_index = pd.DatetimeIndex(etf_prices.index)
    etf_folds = split_helpers.make_splits(
        etf_index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    split_helpers.check_embargo_covers_lookback(etf_folds, etf_index, MAX_LOOKBACK_DAYS)
    if len(etf_folds) != 22:
        raise RuntimeError(f"expected 22 ETF folds, got {len(etf_folds)}")
    _check_window(
        etf_prices,
        etf_folds,
        expected_start=ETF_EXPECTED_START,
        expected_end=ETF_EXPECTED_END,
        expected_bars=ETF_EXPECTED_BARS,
    )
    etf_rf, etf_rf_provenance = cash.align_risk_free(
        cash.load_risk_free_daily(args.data), etf_index
    )
    print(
        "risk-free: "
        f"{etf_rf_provenance['source_first']}..{etf_rf_provenance['source_last']}, "
        f"{etf_rf_provenance['n_carried_forward']} bars carried forward"
    )
    _run_sanity_check(etf_prices, etf_folds, etf_rf)
    etf_base_targets, etf_specs = build_etf_specs(etf_prices)
    if len(etf_specs) != 12:
        raise RuntimeError(f"expected 12 ETF curve configs, got {len(etf_specs)}")

    deep_prices = load_deep_prices(args.data)
    deep_index = pd.DatetimeIndex(deep_prices.index)
    deep_folds = split_helpers.make_splits(
        deep_index,
        train_years=5,
        validate_years=1,
        step_years=1,
        embargo_days=MAX_LOOKBACK_DAYS,
    )
    split_helpers.check_embargo_covers_lookback(deep_folds, deep_index, MAX_LOOKBACK_DAYS)
    if len(deep_folds) != 95:
        raise RuntimeError(f"expected 95 deep-history folds, got {len(deep_folds)}")
    _check_window(
        deep_prices,
        deep_folds,
        expected_start=DEEP_EXPECTED_START,
        expected_end=DEEP_EXPECTED_END,
        expected_bars=DEEP_EXPECTED_BARS,
    )
    deep_rf = deep_prices["CASH"].pct_change().fillna(0.0)
    deep_base_targets, deep_specs = build_deep_specs(deep_prices)
    if len(deep_specs) != 9:
        raise RuntimeError(f"expected 9 deep-history curve configs, got {len(deep_specs)}")

    with TrialsLedger(args.ledger) as ledger:
        etf_base = evaluate_base(
            prices=etf_prices,
            base_targets=etf_base_targets,
            folds=etf_folds,
            engine_risk_free=etf_rf,
        )
        etf_curves = evaluate_curves(
            prices=etf_prices,
            specs=etf_specs,
            folds=etf_folds,
            study=ETF_STUDY,
            ledger=ledger,
            engine_risk_free=etf_rf,
        )
        _print_universe_results(
            title="Universe A — ETF sleeve study",
            curves=etf_curves,
            base=etf_base,
            risk_free=etf_rf,
            ledger=ledger,
            study=ETF_STUDY,
            n_resamples=args.resamples,
            periods=ETF_SUBPERIODS,
        )

        deep_base = evaluate_base(
            prices=deep_prices,
            base_targets=deep_base_targets,
            folds=deep_folds,
            engine_risk_free=None,
        )
        deep_curves = evaluate_curves(
            prices=deep_prices,
            specs=deep_specs,
            folds=deep_folds,
            study=DEEP_STUDY,
            ledger=ledger,
            engine_risk_free=None,
        )
        print(
            "\nDeep-history gold control: UNAVAILABLE and omitted by "
            "preregistration; no substitute used."
        )
        _print_universe_results(
            title="Universe B — Fama-French 12-industry deep history",
            curves=deep_curves,
            base=deep_base,
            risk_free=deep_rf,
            ledger=ledger,
            study=DEEP_STUDY,
            n_resamples=args.resamples,
            periods=decade_periods(
                pd.DatetimeIndex(deep_base.returns[PRIMARY_COST].index)
            ),
        )

    print("\nTrials accounting: 12 ETF + 9 deep-history = 21 fixed configurations.")
    print("Expected ledger rows: 12 x 22 + 9 x 95 = 1,119.")
    print("Final Phase 2 study. Nothing promoted. Journaled results follow.")


if __name__ == "__main__":
    main()
