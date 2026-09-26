"""Rebuild every journalled headline number from source and verify it.

One command, one pass/fail table, non-zero exit on any mismatch. The point is
that a stranger can check the claim "every number in this repo regenerates
from source" without trusting anyone who wrote it.

Two design choices worth stating.

**Independent reconstruction.** Series are rebuilt from `woodland/` primitives
rather than by importing the study runners, so this verifies the journal
against the library rather than a script against itself. A refactor of the
runners therefore cannot make this pass vacuously — and cannot break it.

**Verified to the precision the record claims.** Each anchor carries the
number of decimals its journal entry states it to, and is checked to half a
unit in the last place. An entry that published 0.700 is held to 0.700, not to
a spurious 0.7002; an entry that published 0.780673 is held to all six.

Nothing here writes to `journal/trials.db`: studies needing the walk-forward
harness get a throwaway ledger in a temporary directory.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import backtest, execution, metrics, pipeline, xsmom
from woodland.config import ROOT, all_tickers, load_config
from woodland.fama_french import INDUSTRIES
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import (
    DEEP_MARKET,
    DEEP_RISK_OFF,
    ETF_RISK_OFF,
    LOOKBACKS,
    MAX_LOOKBACK_DAYS,
    MULTI_ASSET,
    MULTI_ASSET_DBC,
    RISK_COV_WINDOW,
    SECTORS,
    STEP_YEARS,
    TRAIN_YEARS,
    VALIDATE_YEARS,
    VOL_TARGET_ANN,
    VOL_TARGET_WINDOW,
    XSMOM_EMBARGO_DAYS,
    deep_context,
    etf_context,
    oos_window,
    stitch,
)

# A rebuilt series and its turnover, the two things series anchors are measured
# on. A rebuild may also yield a bare scalar — a solved cost crossover is a
# number, not a series — so a group returns either kind.
Rebuilt = tuple[pd.Series, pd.Series]
Built = dict[str, "Rebuilt | float"]


@dataclass(frozen=True)
class Anchor:
    """One journalled number, and how to rebuild it."""

    entry: str          # journal filename that published it
    series: str         # which series, or which derived scalar
    metric: str         # sharpe | turnover | value
    journalled: float
    decimals: int       # precision the entry states, and the precision checked

    @property
    def tolerance(self) -> float:
        return 0.5 * 10.0 ** (-self.decimals)


@dataclass
class Group:
    """Anchors sharing a universe and a rebuild."""

    name: str
    build: Callable[[], Built]
    anchors: list[Anchor] = field(default_factory=list)


# --------------------------------------------------------------- rebuilds

def build_etf() -> Built:
    ctx = etf_context()
    px, folds, lo, hi, rf = ctx.prices, ctx.folds, ctx.lo, ctx.hi, ctx.risk_free
    out: Built = {}

    def add(label: str, targets: pd.DataFrame, *, cash_realistic: bool,
            cost: float = 5.0) -> None:
        """Rebuild one series under the engine convention it was journalled on.

        v1-v5 were published before cash realism landed, with the uninvested
        sleeve earning zero; v6 onward were published with it earning the
        T-bill rate. For a series that holds cash the two differ materially —
        v6 is 0.775 on the old convention and 0.781 on the new — so the
        convention is part of the anchor, not an implementation detail.
        """
        res = backtest.run(px, stitch(px, targets, folds), cost_bps=cost,
                           risk_free=rf if cash_realistic else None)
        out[label] = (res.returns.loc[lo:hi], res.turnover.loc[lo:hi])

    ens = trend.ensemble_targets(px, risk_assets=SECTORS, risk_off=ETF_RISK_OFF,
                                 lookback_months=LOOKBACKS)
    add("v2 ensemble", ens, cash_realistic=False)
    add("v3 voltarget", vol_target_targets(px, ens, window=VOL_TARGET_WINDOW,
                                           target_ann_vol=VOL_TARGET_ANN),
        cash_realistic=False)
    for label, scheme in (("v5 inverse-vol", "inverse_vol"), ("v5 min-variance", "min_variance")):
        add(label, trend.ensemble_targets(px, risk_assets=SECTORS, risk_off=ETF_RISK_OFF,
                                          lookback_months=LOOKBACKS, weighting=scheme,
                                          vol_window=RISK_COV_WINDOW),
            cash_realistic=False)
    for label, sleeves in (("v6 multi-asset", MULTI_ASSET), ("v6 +DBC", MULTI_ASSET_DBC)):
        add(label, trend.ensemble_targets(px, risk_assets=sleeves, risk_off=None,
                                          lookback_months=LOOKBACKS),
            cash_realistic=True)

    # v1 selects a lookback per fold, so it needs the harness. Throwaway ledger.
    with tempfile.TemporaryDirectory() as tmp:
        ledger = TrialsLedger(Path(tmp) / "throwaway.db")
        try:
            result = run_walkforward(
                px,
                lambda p, c: trend.trend_targets(p, risk_assets=SECTORS,
                                                 risk_off=ETF_RISK_OFF,
                                                 lookback_months=c["lookback_months"]),
                [{"lookback_months": m} for m in LOOKBACKS],
                splits=folds, ledger=ledger, study="reproduce-v1",
                max_lookback_days=MAX_LOOKBACK_DAYS,
                select_cost_bps=5.0, report_cost_bps=[5.0],
            )
        finally:
            ledger.close()
        out["v1 selection"] = (result.oos_returns[5.0], result.oos_turnover[5.0])

    spy = backtest.buy_and_hold(px, "SPY")
    out["SPY buy&hold"] = (spy.returns.loc[lo:hi], spy.turnover.loc[lo:hi])
    mix_t = backtest.fixed_mix_targets(px, {"SPY": 0.6, "IEF": 0.4})
    mix = backtest.run(px, mix_t, cost_bps=5.0)
    out["60/40"] = (mix.returns.loc[lo:hi], mix.turnover.loc[lo:hi])
    vt = backtest.run(px, vol_target_targets(px, mix_t, window=VOL_TARGET_WINDOW,
                                             target_ann_vol=VOL_TARGET_ANN),
                      cost_bps=5.0, risk_free=rf)
    out["vol-target 60/40"] = (vt.returns.loc[lo:hi], vt.turnover.loc[lo:hi])

    # v14's nine fixed pipeline states, through the execution policy each implies.
    states = {
        "v14 raw v6": pipeline.PipelineConfig(execution="none"),
        "v14 baseline partial": pipeline.PipelineConfig(execution="partial"),
        "v14 S1 dispersion": pipeline.PipelineConfig(regime_filter=True, execution="partial"),
        "v14 S2 inverse-vol": pipeline.PipelineConfig(sizing="inverse_vol", execution="partial"),
        "v14 S2 min-variance": pipeline.PipelineConfig(sizing="min_variance", execution="partial"),
        "v14 S3 symmetric": pipeline.PipelineConfig(exposure="symmetric", execution="partial"),
        "v14 S3 asymmetric": pipeline.PipelineConfig(exposure="asymmetric", execution="partial"),
        "v14 S4 band": pipeline.PipelineConfig(execution="band"),
        "v14 S4 partial+band": pipeline.PipelineConfig(execution="partial_band"),
    }
    for label, config in states.items():
        built = pipeline.DecisionPipeline(list(MULTI_ASSET), config).build(px)
        res = execution.run(px, stitch(px, built.targets, folds), built.policy,
                            cost_bps=5.0, risk_free=rf)
        out[label] = (res.returns.loc[lo:hi], res.turnover.loc[lo:hi])
    return out


def build_deep() -> Built:
    ctx = deep_context()
    px, folds, lo, hi = ctx.prices, ctx.folds, ctx.lo, ctx.hi
    out: Built = {}

    ens = trend.ensemble_targets(px, risk_assets=list(INDUSTRIES), risk_off=DEEP_RISK_OFF,
                                 lookback_months=LOOKBACKS)
    res = backtest.run(px, stitch(px, ens, folds), cost_bps=5.0)
    out["v4 ensemble"] = (res.returns.loc[lo:hi], res.turnover.loc[lo:hi])

    with tempfile.TemporaryDirectory() as tmp:
        ledger = TrialsLedger(Path(tmp) / "throwaway.db")
        try:
            sel = run_walkforward(
                px,
                lambda p, c: trend.trend_targets(p, risk_assets=list(INDUSTRIES),
                                                 risk_off=DEEP_RISK_OFF,
                                                 lookback_months=c["lookback_months"]),
                [{"lookback_months": m} for m in LOOKBACKS],
                splits=folds, ledger=ledger, study="reproduce-v4",
                max_lookback_days=MAX_LOOKBACK_DAYS,
                select_cost_bps=5.0, report_cost_bps=[5.0],
            )
        finally:
            ledger.close()
    out["v4 selection"] = (sel.oos_returns[5.0], sel.oos_turnover[5.0])

    mkt = backtest.buy_and_hold(px, "MKT")
    out["MKT buy&hold"] = (mkt.returns.loc[lo:hi], mkt.turnover.loc[lo:hi])
    mix = backtest.run(px, backtest.fixed_mix_targets(px, {"MKT": 0.6, DEEP_RISK_OFF: 0.4}),
                       cost_bps=5.0)
    out["60% MKT / 40% CASH"] = (mix.returns.loc[lo:hi], mix.turnover.loc[lo:hi])
    return out


# --------------------------------------------------------------- xsmom (v10)

XSMOM_FORMATION, XSMOM_SKIP, XSMOM_K = 252, 21, 3


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(index.to_series().groupby(index.to_period("M")).max())


def build_xsmom_deep() -> Built:
    """v10: rank 12 industries on the 12-1 momentum characteristic.

    Reimplemented here from primitives rather than imported, so this verifies
    the journal against an independent construction. The 252-bar embargo was
    amended for the momentum studies, so the window differs from v4's.
    """
    ctx = deep_context(XSMOM_EMBARGO_DAYS)
    px, folds, lo, hi = ctx.prices, ctx.folds, ctx.lo, ctx.hi
    industries = list(INDUSTRIES)
    out: Built = {}

    def run(label: str, targets: pd.DataFrame) -> None:
        res = backtest.run(px, stitch(px, targets, folds), cost_bps=5.0)
        out[label] = (res.returns.loc[lo:hi], res.turnover.loc[lo:hi])

    # both lags look backward, so the score at t uses only data <= t
    momentum = px[industries].shift(XSMOM_SKIP) / px[industries].shift(XSMOM_FORMATION) - 1.0
    top = pd.DataFrame(float("nan"), index=px.index, columns=px.columns)
    equal = pd.DataFrame(float("nan"), index=px.index, columns=px.columns)
    first = px[industries].dropna().index[0]
    for day in month_ends(pd.DatetimeIndex(px.index)):
        row = pd.Series(momentum.loc[day]).dropna()
        if len(row) == len(industries):
            weights = pd.Series(0.0, index=px.columns)
            weights[row.nlargest(XSMOM_K).index] = 1.0 / XSMOM_K
            top.loc[day] = weights
        if day >= first:
            weights = pd.Series(0.0, index=px.columns)
            weights[industries] = 1.0 / len(industries)
            equal.loc[day] = weights
    run("xsmom top-3", top)
    run("equal-weight 12", equal)

    mkt = backtest.buy_and_hold(px, DEEP_MARKET)
    out["MKT buy&hold"] = (mkt.returns.loc[lo:hi], mkt.turnover.loc[lo:hi])
    mix = backtest.run(px, backtest.fixed_mix_targets(px, {DEEP_MARKET: 0.6, DEEP_RISK_OFF: 0.4}),
                       cost_bps=5.0)
    out["60% MKT / 40% CASH"] = (mix.returns.loc[lo:hi], mix.turnover.loc[lo:hi])
    return out


# --------------------------------------------------------------- deciles (v15)

DECILE_ARCHIVE = ROOT / "10_Portfolios_Prior_12_2_Daily_CSV.zip"
V15_FREQUENCIES = ("monthly", "quarterly", "semiannual", "annual")


def build_v15() -> Built:
    """v15: the stale-cohort holding-frequency curve.

    Needs the Ken French decile archive, which is downloaded by hand and is
    NOT in the repository — neither sandbox can reach the server. Absent, this
    group reports SKIP rather than passing vacuously.
    """
    if not DECILE_ARCHIVE.exists():
        raise FileNotFoundError(
            f"{DECILE_ARCHIVE.name} not present; download it to the repo root"
        )
    deciles = xsmom.parse_daily_deciles(DECILE_ARCHIVE).dropna()
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    common = deciles.index.intersection(factors.index)
    deciles = deciles.reindex(common).dropna()
    factors = factors.reindex(deciles.index)

    prices = ((1.0 + deciles).cumprod() * 100.0).join(factors, how="inner")
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=XSMOM_EMBARGO_DAYS)
    lo, hi, _ = oos_window(index, folds)
    oos_index = pd.DatetimeIndex(prices.loc[lo:hi].index)
    oos_deciles = deciles.reindex(oos_index)

    out: Built = {}
    for frequency in V15_FREQUENCIES:
        dates = xsmom.formation_dates(oos_index, frequency)
        gross = xsmom.stale_cohort_returns(oos_deciles, dates)
        components = xsmom.holding_period_turnover(oos_index, dates)
        net = xsmom.net_of_internal_cost(gross, components.total, 5.0)
        turnover = pd.Series(components.total / 252.0, index=oos_index)
        out[f"v15 {frequency}"] = (net, turnover)

    controls = {
        "equal-weight 10": {c: 0.1 for c in xsmom.DECILE_COLUMNS},
        "MKT": {DEEP_MARKET: 1.0},
        "60% MKT / 40% CASH": {DEEP_MARKET: 0.6, DEEP_RISK_OFF: 0.4},
    }
    for label, weights in controls.items():
        targets = pd.DataFrame(float("nan"), index=prices.index, columns=prices.columns)
        for day in xsmom.formation_dates(index, "monthly"):
            row = pd.Series(0.0, index=prices.columns)
            for asset, weight in weights.items():
                row[asset] = weight
            targets.loc[day] = row
        res = backtest.run(prices, stitch(prices, targets, folds), cost_bps=5.0)
        out[label] = (res.returns.reindex(oos_index), res.turnover.reindex(oos_index))
    return out


def _decile_prices() -> tuple[pd.DataFrame, pd.DataFrame, list[sp.Split]]:
    """Decile levels joined to the factors, and the frozen 252-embargo folds."""
    if not DECILE_ARCHIVE.exists():
        raise FileNotFoundError(
            f"{DECILE_ARCHIVE.name} not present; download it to the repo root"
        )
    deciles = xsmom.parse_daily_deciles(DECILE_ARCHIVE).dropna()
    factors = pd.read_parquet(ROOT / "data" / "fama_french_factors_daily.parquet")
    common = deciles.index.intersection(factors.index)
    deciles = deciles.reindex(common).dropna()
    factors = factors.reindex(deciles.index)
    prices = ((1.0 + deciles).cumprod() * 100.0).join(factors, how="inner")
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=XSMOM_EMBARGO_DAYS)
    return deciles, prices, folds


def _monthly_gross(prices: pd.DataFrame, folds: list[sp.Split],
                   weights: dict[str, float], lo: pd.Timestamp,
                   hi: pd.Timestamp) -> Rebuilt:
    """Gross returns and engine turnover for a monthly fixed-weight basket."""
    targets = pd.DataFrame(float("nan"), index=prices.index, columns=prices.columns)
    for day in xsmom.formation_dates(pd.DatetimeIndex(prices.index), "monthly"):
        row = pd.Series(0.0, index=prices.columns)
        for asset, weight in weights.items():
            row[asset] = weight
        targets.loc[day] = row
    result = backtest.run(prices, stitch(prices, targets, folds), cost_bps=0.0)
    return result.returns.loc[lo:hi], result.turnover.loc[lo:hi]


def _outer_net(gross: pd.Series, turnover: pd.Series, cost_bps: float) -> pd.Series:
    """Charge engine-observed trading at `cost_bps`."""
    aligned = turnover.reindex(gross.index)
    return (1.0 + gross) * (1.0 - aligned * cost_bps / 10_000.0) - 1.0


def _solve_crossover(net: Callable[[float], pd.Series],
                     reference: Callable[[float], pd.Series]) -> float:
    """Bisect for the cost at which the candidate stops beating its control.

    Same contract as the study runners: 0.0 if it never leads, and a hard
    failure past 500 bps rather than a silent infinity, since every crossover
    the journal publishes is inside that range.
    """
    def difference(cost: float) -> float:
        return metrics.sharpe(net(cost)) - metrics.sharpe(reference(cost))

    if difference(0.0) <= 0.0:
        return 0.0
    if difference(500.0) > 0.0:
        raise ValueError("no crossover below 500 bps")
    low, high = 0.0, 500.0
    while high - low > 0.001:
        midpoint = (low + high) / 2.0
        if difference(midpoint) > 0.0:
            low = midpoint
        else:
            high = midpoint
    return high


def build_crossovers() -> Built:
    """The turnover budget: five (turnover, crossover) pairs and their product.

    These are the numbers the write-up's turnover-budget section rests on, so
    they are rebuilt rather than transcribed. Each crossover is the one-way
    cost at which the candidate's stitched OOS Sharpe stops exceeding
    equal-weight-ten's, solved by bisection.
    """
    deciles, prices, folds = _decile_prices()
    index = pd.DatetimeIndex(prices.index)
    lo, hi, _ = oos_window(index, folds)
    oos_index = pd.DatetimeIndex(prices.loc[lo:hi].index)

    ew_gross, ew_turnover = _monthly_gross(
        prices, folds, {c: 0.1 for c in xsmom.DECILE_COLUMNS}, lo, hi)

    def ew_at(cost: float) -> pd.Series:
        return _outer_net(ew_gross, ew_turnover, cost)

    out: Built = {}

    # v13: the daily-reconstituted top three deciles. Its internal turnover is
    # the Gaussian rank-transition model's, charged on top of engine turnover.
    top3_gross, top3_turnover = _monthly_gross(
        prices, folds, {c: 1.0 / 3.0 for c in xsmom.DECILE_COLUMNS[-3:]}, lo, hi)
    top3_internal = xsmom.model_implied_turnover(0.7, 1.0)
    top3_crossover = _solve_crossover(
        lambda cost: xsmom.net_of_internal_cost(
            _outer_net(top3_gross, top3_turnover, cost), top3_internal, cost),
        ew_at,
    )
    out["v13 top-three turnover"] = top3_internal
    out["v13 top-three crossover"] = top3_crossover
    products = [top3_internal * top3_crossover]

    # v15: the stale-cohort holding frequencies. All trading is internal.
    oos_deciles = deciles.reindex(oos_index)
    for frequency in V15_FREQUENCIES:
        dates = xsmom.formation_dates(oos_index, frequency)
        gross = xsmom.stale_cohort_returns(oos_deciles, dates)
        total = float(xsmom.holding_period_turnover(oos_index, dates).total)

        def sleeve_at(cost: float, g: pd.Series = gross, t: float = total) -> pd.Series:
            return xsmom.net_of_internal_cost(g, t, cost)

        crossover = _solve_crossover(sleeve_at, ew_at)
        out[f"v15 {frequency} crossover"] = crossover
        products.append(total * crossover)

    # `K = crossover x turnover` is the write-up's constant. It is the whole
    # claim of that section, so it is rebuilt from the rebuilt pairs rather
    # than restated.
    out["K mean product"] = sum(products) / len(products)
    out["K minimum product"] = min(products)
    out["K maximum product"] = max(products)
    return out


# --------------------------------------------------------------- registry

V1 = "2026-09-01-trend-study-v1-results.md"
V2 = "2026-09-01-trend-v2-ensemble-results.md"
V3 = "2026-09-01-trend-v3-voltarget-results.md"
V4 = "2026-09-01-trend-v4-deephistory-results.md"
V5 = "2026-09-01-trend-v5-riskweight-results.md"
V6 = "2026-09-02-trend-v6-multiasset-results.md"
V14 = "2026-09-02-pipeline-v14-ablation-results.md"
V10 = "2026-09-02-xsmom-v10-results.md"
V13 = "2026-09-02-xsmom-v13-confirm-results.md"
V15 = "2026-09-03-xsmom-v15-holding-results.md"

BUDGET = "2026-09-03-planning-note-turnover-budget.md"

GROUPS = [
    Group("ETF universe", build_etf, [
        Anchor(V1, "v1 selection", "sharpe", 0.612, 3),
        Anchor(V1, "v1 selection", "turnover", 7.46, 2),
        Anchor(V2, "v2 ensemble", "sharpe", 0.700, 3),
        Anchor(V2, "v2 ensemble", "turnover", 5.783, 3),
        Anchor(V3, "v3 voltarget", "sharpe", 0.709, 3),
        Anchor(V5, "v5 inverse-vol", "sharpe", 0.679, 3),
        Anchor(V5, "v5 min-variance", "sharpe", 0.624, 3),
        Anchor(V6, "v6 multi-asset", "sharpe", 0.781, 3),
        Anchor(V6, "v6 +DBC", "sharpe", 0.738, 3),
        Anchor(V6, "SPY buy&hold", "sharpe", 0.660, 3),
        Anchor(V6, "60/40", "sharpe", 0.806, 3),
        Anchor(V6, "vol-target 60/40", "sharpe", 0.862, 3),
        Anchor(V14, "v14 raw v6", "sharpe", 0.780673, 6),
        Anchor(V14, "v14 raw v6", "turnover", 5.153145, 6),
        Anchor(V14, "v14 baseline partial", "sharpe", 0.804639, 6),
        Anchor(V14, "v14 baseline partial", "turnover", 2.772494, 6),
        Anchor(V14, "v14 S1 dispersion", "sharpe", 0.828044, 6),
        Anchor(V14, "v14 S2 inverse-vol", "sharpe", 0.806791, 6),
        Anchor(V14, "v14 S2 min-variance", "sharpe", 0.884765, 6),
        Anchor(V14, "v14 S3 symmetric", "sharpe", 0.807927, 6),
        Anchor(V14, "v14 S3 asymmetric", "sharpe", 0.803301, 6),
        Anchor(V14, "v14 S4 band", "sharpe", 0.772633, 6),
        Anchor(V14, "v14 S4 partial+band", "sharpe", 0.810613, 6),
    ]),
    Group("deep history: momentum (v10)", build_xsmom_deep, [
        Anchor(V10, "xsmom top-3", "sharpe", 0.827, 3),
        Anchor(V10, "xsmom top-3", "turnover", 5.23, 2),
        Anchor(V10, "equal-weight 12", "sharpe", 0.800, 3),
        Anchor(V10, "equal-weight 12", "turnover", 0.27, 2),
        Anchor(V10, "MKT buy&hold", "sharpe", 0.733, 3),
        Anchor(V10, "60% MKT / 40% CASH", "sharpe", 0.865, 3),
    ]),
    Group("stock deciles: holding frequency (v15)", build_v15, [
        Anchor(V15, "v15 monthly", "sharpe", 0.802, 3),
        Anchor(V15, "v15 quarterly", "sharpe", 0.793, 3),
        Anchor(V15, "v15 semiannual", "sharpe", 0.799, 3),
        Anchor(V15, "v15 annual", "sharpe", 0.791, 3),
        Anchor(V15, "v15 monthly", "turnover", 4.5842, 4),
        Anchor(V15, "v15 quarterly", "turnover", 2.5542, 4),
        Anchor(V15, "v15 semiannual", "turnover", 1.7057, 4),
        Anchor(V15, "v15 annual", "turnover", 1.0896, 4),
        Anchor(V15, "equal-weight 10", "sharpe", 0.688, 3),
        Anchor(V15, "MKT", "sharpe", 0.724, 3),
        Anchor(V15, "60% MKT / 40% CASH", "sharpe", 0.859, 3),
    ]),
    Group("deep history: trend (v4)", build_deep, [
        Anchor(V4, "v4 ensemble", "sharpe", 0.861, 3),
        Anchor(V4, "v4 selection", "sharpe", 0.799, 3),
        Anchor(V4, "MKT buy&hold", "sharpe", 0.710, 3),
        Anchor(V4, "60% MKT / 40% CASH", "sharpe", 0.841, 3),
    ]),
    Group("Turnover budget", build_crossovers, [
        Anchor(V13, "v13 top-three turnover", "value", 21.736, 3),
        Anchor(V13, "v13 top-three crossover", "value", 11.168, 3),
        Anchor(V15, "v15 monthly crossover", "value", 52.516, 3),
        Anchor(V15, "v15 quarterly crossover", "value", 85.991, 3),
        Anchor(V15, "v15 semiannual crossover", "value", 135.550, 3),
        Anchor(V15, "v15 annual crossover", "value", 208.110, 3),
        # The invariant the write-up's budget section is built on. Checked here
        # so the constant cannot drift away from the numbers that produced it.
        Anchor(BUDGET, "K mean product", "value", 232.2, 1),
        Anchor(BUDGET, "K minimum product", "value", 219.6, 1),
        Anchor(BUDGET, "K maximum product", "value", 242.7, 1),
    ]),
]


REPLACED_REASON = (
    "Unavailable earlier input snapshot; superseded by explicitly pinned current data, "
    "not reproduced."
)
# The signed 1e-3 ruling applies only to the disclosed, unreproducible
# replacements.  It is deliberately not used by the 30-anchor gate below.
REPLACED_DISCLOSURE_TOLERANCE = 1e-3
SIGNED_FROZEN_ETF_SHA256 = "4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901"


@dataclass(frozen=True)
class AnchorSetSplit:
    """The signed distinction between real reproductions and replaced values."""

    reproduced_groups: tuple[Group, ...]
    replaced: tuple[Mapping[str, object], ...]

    @property
    def reproduced_count(self) -> int:
        return sum(len(group.anchors) for group in self.reproduced_groups)

    @property
    def replaced_count(self) -> int:
        return len(self.replaced)


def load_anchor_set_split() -> AnchorSetSplit:
    """Load the signed 30 reproduced / 23 replaced anchor partition."""
    path = ROOT / "config/etf-anchors-2026-09-07.json"
    record = json.loads(path.read_text())
    replaced = tuple(record["anchors"])
    if len(replaced) != 23 or any(item.get("reason") != REPLACED_REASON for item in replaced):
        raise ValueError("ETF replacement registry no longer matches the signed 23-anchor split")
    split = AnchorSetSplit(tuple(GROUPS[1:]), replaced)
    if split.reproduced_count != 30:
        raise ValueError(
            f"signed reproduced anchor set must contain 30 anchors, found {split.reproduced_count}"
        )
    return split


@dataclass(frozen=True)
class ReproducedAnchorCheck:
    """One row of the signed, published-precision reproduced-anchor gate."""

    journalled: float
    rebuilt: float
    delta: float
    tolerance: float
    passes: bool


def check_reproduced_anchor(anchor: Anchor, actual: float) -> ReproducedAnchorCheck:
    """Check an anchor at exactly the precision its journal entry published."""
    delta = abs(actual - anchor.journalled)
    tolerance = anchor.tolerance
    return ReproducedAnchorCheck(
        journalled=anchor.journalled,
        rebuilt=actual,
        delta=delta,
        tolerance=tolerance,
        passes=delta <= tolerance,
    )


def anchor_passes(anchor: Anchor, actual: float) -> bool:
    """Compatibility helper for the published-precision reproduced-anchor gate."""
    return check_reproduced_anchor(anchor, actual).passes


def freeze_time_anchor_records(split: AnchorSetSplit) -> list[dict[str, object]]:
    """Return the snapshot-local registry without changing any source values."""
    records: list[dict[str, object]] = []
    for group in split.reproduced_groups:
        for anchor in group.anchors:
            records.append(
                {
                    "classification": "reproduced",
                    "entry": anchor.entry,
                    "series": anchor.series,
                    "metric": anchor.metric,
                    "value": anchor.journalled,
                    "decimals": anchor.decimals,
                }
            )
    for anchor in split.replaced:
        records.append(
            {
                "classification": "replaced",
                "entry": anchor["old_journal"],
                "series": anchor["series"],
                "metric": anchor["metric"],
                    "value": anchor["new"],
                    "decimals": anchor["decimals"],
                    "reason": anchor["reason"],
                }
        )
    return records


def emit_current_freeze_time_anchors(split: AnchorSetSplit) -> Path:
    """Backfill or verify the snapshot-local anchor registry."""
    from woodland.snapshot import emit_freeze_time_anchors, etf_snapshot

    cfg = load_config()
    snapshot = etf_snapshot()
    return emit_freeze_time_anchors(
        ROOT / cfg["data"]["store"],
        snapshot=snapshot,
        anchors=freeze_time_anchor_records(split),
    )


def apply_pinned_etf_anchors(*, verify_snapshot: bool = True) -> AnchorSetSplit:
    """Apply the signed snapshot ruling without treating replacements as passes."""
    from woodland.snapshot import etf_snapshot

    split = load_anchor_set_split()
    current = etf_snapshot()
    if verify_snapshot and current["sha256"] != SIGNED_FROZEN_ETF_SHA256:
        raise ValueError("ETF snapshot differs from the signed frozen hash; refuse reproduction")
    return split


def etf_file_inventory() -> dict[str, dict[str, int]]:
    """Return a read-only inventory of the configured ETF parquet files."""
    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    return {
        symbol: {
            "size": (store / f"{symbol}.parquet").stat().st_size,
            "mtime_ns": (store / f"{symbol}.parquet").stat().st_mtime_ns,
        }
        for symbol in all_tickers(cfg)
    }


def measure(built: Built, anchor: Anchor) -> float:
    value = built[anchor.series]
    if anchor.metric == "value":
        if not isinstance(value, float):
            raise ValueError(f"{anchor.series!r} is a series, not a scalar")
        return value
    if isinstance(value, float):
        raise ValueError(f"{anchor.series!r} is a scalar; use metric 'value'")
    returns, turnover = value
    if anchor.metric == "sharpe":
        return metrics.sharpe(returns)
    if anchor.metric == "turnover":
        return metrics.ann_turnover(turnover)
    raise ValueError(f"unknown metric {anchor.metric!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", help="only run groups whose name contains this")
    parser.add_argument("--strict", action="store_true",
                        help="treat a skipped group as a failure (for CI)")
    parser.add_argument(
        "--measurement-only-json", metavar="PATH",
        help=("measure the registered anchors and write structured JSON; "
              "measurement-only is never the normal regression path"),
    )
    parser.add_argument(
        "--emit-freeze-time-anchors",
        action="store_true",
        help="write or verify snapshot-local anchors without rebuilding series",
    )
    args = parser.parse_args()

    measurement_only = args.measurement_only_json is not None
    if measurement_only and (args.group or args.strict or args.emit_freeze_time_anchors):
        parser.error("--measurement-only-json requires the full run without --group or --strict")
    before_inventory = None
    before_snapshot = None
    if measurement_only:
        from woodland.snapshot import etf_snapshot
        before_inventory = etf_file_inventory()
        before_snapshot = etf_snapshot()
    split = apply_pinned_etf_anchors(verify_snapshot=not measurement_only)
    if args.emit_freeze_time_anchors:
        print(f"Freeze-time anchors: {emit_current_freeze_time_anchors(split)}")
        return 0
    observed_snapshot = None
    if measurement_only:
        from woodland.snapshot import etf_snapshot
        observed_snapshot = etf_snapshot()
    if measurement_only:
        print(
            "Measurement-only mode: registered anchors versus current store; "
            "it is diagnostic output, not the reproduced-anchor gate.\n"
        )
    else:
        print(
            "Checking 30 reproduced anchors at each journalled value's published precision; "
            "23 replaced anchors are disclosed and never counted as passes.\n"
        )
    failures: list[str] = []
    skipped: list[str] = []
    checked = 0
    records: list[dict[str, object]] = []

    groups_to_check = GROUPS if measurement_only else split.reproduced_groups
    replaced_keys = {
        (str(item["old_journal"]), str(item["series"]), str(item["metric"]))
        for item in split.replaced
    }
    for group in groups_to_check:
        if args.group and args.group.lower() not in group.name.lower():
            continue
        started = time.time()
        print(f"=== {group.name} ===")
        try:
            series = group.build()
        except FileNotFoundError as absent:
            skipped.append(f"{group.name}: {absent}")
            print(f"    SKIPPED — {absent}\n")
            continue
        print(f"    rebuilt in {time.time() - started:.1f}s\n")
        print(f"    {'series':24s} {'metric':9s} {'journalled':>11s} "
              f"{'rebuilt':>11s} {'delta':>11s} {'tolerance':>11s}  "
              f"{'entry':46s} result")
        for anchor in group.anchors:
            classification = (
                "replaced"
                if (anchor.entry, anchor.series, anchor.metric) in replaced_keys
                else "reproduced"
            )
            tolerance = (
                REPLACED_DISCLOSURE_TOLERANCE
                if classification == "replaced"
                else anchor.tolerance
            )
            delta = float("nan")
            if anchor.series not in series:
                if classification == "replaced":
                    verdict, got, ok = "REPLACED", float("nan"), None
                else:
                    failures.append(f"{group.name}/{anchor.series}: not rebuilt")
                    verdict, got, ok = "MISSING", float("nan"), False
            else:
                got = measure(series, anchor)
                delta = abs(got - anchor.journalled)
                check = (
                    None
                    if classification == "replaced"
                    else check_reproduced_anchor(anchor, got)
                )
                ok = None if check is None else check.passes
                verdict = "REPLACED" if classification == "replaced" else "pass" if ok else "FAIL"
                if ok is False:
                    failures.append(
                        f"{anchor.entry} {anchor.series} {anchor.metric}: "
                        f"journalled {anchor.journalled}, rebuilt {got:.6f}"
                    )
            if measurement_only:
                records.append({
                    "family": group.name,
                    "journal_source": anchor.entry,
                    "series": anchor.series,
                    "metric": anchor.metric,
                    "expected": anchor.journalled,
                    "actual": None if pd.isna(got) else got,
                    "signed_delta": None if pd.isna(got) else got - anchor.journalled,
                    "absolute_delta": None if pd.isna(got) else delta,
                    "decimals": anchor.decimals,
                    "tolerance": tolerance,
                    "classification": classification,
                    "passes": ok,
                })
            checked += 1
            print(f"    {anchor.series:24s} {anchor.metric:9s} "
                  f"{anchor.journalled:11.6f} {got:11.6f} {delta:11.6f} {tolerance:11.6f}  "
                  f"{anchor.entry:46s} {verdict}")
        print()

    if not measurement_only:
        print(
            "The per-anchor table above is the gate artifact; replaced anchors are "
            "disclosed and never evaluated as passes."
        )
    if skipped:
        print(f"{len(skipped)} group(s) skipped.")
    for line in skipped:
        print(f"  SKIPPED {line}")
    if measurement_only:
        after_inventory = etf_file_inventory()
        after_snapshot = etf_snapshot()
        census_complete = checked == 53 and not skipped and len(records) == 53
        if not census_complete:
            raise RuntimeError(
                f"measurement census incomplete: checked={checked}, "
                f"records={len(records)}, skipped={len(skipped)}"
            )
        output = {
            "mode": "measurement-only",
            "registered_snapshot": json.loads(
                (ROOT / "config/etf-anchors-2026-09-07.json").read_text()
            )["snapshot"],
            "observed_snapshot_before": before_snapshot,
            "observed_snapshot": observed_snapshot,
            "observed_snapshot_after": after_snapshot,
            "source_stable": (
                before_snapshot == after_snapshot and before_inventory == after_inventory
            ),
            "etf_file_inventory_before": before_inventory,
            "etf_file_inventory_after": after_inventory,
            "anchors": records,
            "aggregate": {
                "reproduced_anchors_checked": sum(
                    r["classification"] == "reproduced" for r in records
                ),
                "reproduced_passed": sum(
                    r["classification"] == "reproduced" and r["passes"] is True for r in records
                ),
                "reproduced_failed": sum(
                    r["classification"] == "reproduced" and r["passes"] is False for r in records
                ),
                "replaced_anchors_disclosed": sum(
                    r["classification"] == "replaced" for r in records
                ),
                "groups_skipped": len(skipped),
            },
        }
        destination = Path(args.measurement_only_json)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
        csv_columns = [
            "family", "journal_source", "series", "metric", "expected", "actual",
            "signed_delta", "absolute_delta", "decimals", "tolerance", "classification", "passes",
        ]
        destination.with_suffix(".csv").write_text(
            pd.DataFrame(records, columns=csv_columns).to_csv(index=False)
        )
        print(f"Measurement JSON written: {destination}")
    if failures:
        print("\nFAILURES — the journal and the source disagree:")
        for line in failures:
            print(f"  {line}")
        return 1
    if skipped and args.strict:
        print("\n--strict: a skipped group counts as a failure.")
        return 1
    print("Every checked number regenerates from source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
