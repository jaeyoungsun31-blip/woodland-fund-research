"""trend-v6-multiasset: the same trend ensemble across asset classes.

Pre-registered in journal/2026-09-02-trend-v6-multiasset-preregistration.md.
Harness output only; nothing is promoted.

Usage:  python scripts/run_trend_multiasset.py [--resamples 10000] [--ledger PATH]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import aqr, backtest, cash, data, diversification, metrics, stats
from woodland.config import ROOT, all_tickers, load_config
from woodland.harness import deflated as dfl
from woodland.harness import splits as sp
from woodland.harness.ledger import TrialsLedger
from woodland.harness.walkforward import run_walkforward
from woodland.signals import trend
from woodland.signals.voltarget import vol_target_targets
from woodland.study import LOOKBACKS, MAX_LOOKBACK_DAYS, MULTI_ASSET, SECTORS, stitch

SECONDARY = [*MULTI_ASSET, "DBC"]
VOL_WINDOW, TARGET_ANN_VOL = 63, 0.10
COST = 5.0

STUDIES = {
    "trend-v6-multiasset": MULTI_ASSET,
    "trend-v6-multiasset-dbc": SECONDARY,
}


def make_builder(sleeves: list[str]) -> Callable[[pd.DataFrame, dict], pd.DataFrame]:
    def build(prices: pd.DataFrame, config: dict) -> pd.DataFrame:
        return trend.ensemble_targets(
            prices, risk_assets=config["sleeves"], risk_off=None,
            lookback_months=config["lookbacks"],
        )
    assert sleeves
    return build


def external_validation(named: dict[str, pd.Series], store: Path) -> None:
    """Correlation and beta against AQR's published TSMOM factor."""
    try:
        factors = aqr.load_tsmom_monthly(store)
    except FileNotFoundError as error:
        print(f"  AQR factor not available ({error}); SKIPPED — no proxy substituted.")
        return
    tsmom = factors["TSMOM"]
    print(f"  AQR TSMOM: {factors.index[0].date()}..{factors.index[-1].date()}, "
          f"{len(factors)} monthly obs (long/short, vol-targeted futures)")
    print(f"  {'series':24s} {'n':>4s} {'corr':>7s} {'beta':>7s} "
          f"{'alpha/yr':>9s} {'R^2':>6s}")
    for label, series in named.items():
        ours = aqr.to_month_end_returns(series)
        joined = pd.DataFrame({"ours": ours, "tsmom": tsmom}).dropna()
        if len(joined) < 24:
            print(f"  {label:24s} too few overlapping months")
            continue
        x, y = joined["tsmom"].to_numpy(), joined["ours"].to_numpy()
        beta, intercept = np.polyfit(x, y, 1)
        corr = float(np.corrcoef(x, y)[0, 1])
        print(f"  {label:24s} {len(joined):4d} {corr:7.3f} {beta:7.3f} "
              f"{intercept * 12:9.2%} {corr**2:6.3f}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resamples", type=int, default=stats.DEFAULT_RESAMPLES)
    parser.add_argument("--ledger", type=Path, default=ROOT / "journal" / "trials.db")
    args = parser.parse_args()

    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    costs = [float(c) for c in cfg["backtest"]["cost_bps_scenarios"]]
    prices, _ = data.drop_suspect_dates(data.build_matrix(all_tickers(cfg), store))
    index = pd.DatetimeIndex(prices.index)
    folds = sp.make_splits(index, train_years=5, validate_years=1, step_years=1,
                           embargo_days=MAX_LOOKBACK_DAYS)
    sp.check_embargo_covers_lookback(folds, index, MAX_LOOKBACK_DAYS)

    rf_daily, rf_prov = cash.align_risk_free(cash.load_risk_free_daily(store), index)
    print(f"risk-free: {rf_prov['source_first']}..{rf_prov['source_last']}, "
          f"{rf_prov['n_carried_forward']} bars carried forward")

    ledger = TrialsLedger(args.ledger)
    results = {}
    try:
        for study, sleeves in STUDIES.items():
            grid = [{"sleeves": sleeves, "lookbacks": LOOKBACKS,
                     "risk_off": "cash", "aggregation": "equal_weight"}]
            results[study] = run_walkforward(
                prices, make_builder(sleeves), grid, splits=folds, ledger=ledger,
                study=study, max_lookback_days=MAX_LOOKBACK_DAYS,
                select_cost_bps=cfg["backtest"]["default_cost_bps"],
                report_cost_bps=costs, risk_free=rf_daily,
            )
            print(f"{study}: {results[study].n_trials} config, "
                  f"{results[study].n_trial_rows} evaluations")
    finally:
        ledger.close()

    primary = results["trend-v6-multiasset"]
    secondary = results["trend-v6-multiasset-dbc"]
    lo, hi = primary.oos_start, primary.oos_end

    # v2 incumbent and baselines, rebuilt deterministically under the SAME
    # (cash-realistic) rules. No ledger rows.
    v2_targets = trend.ensemble_targets(prices, risk_assets=SECTORS, risk_off="IEF",
                                        lookback_months=LOOKBACKS)
    v2_stitched = stitch(prices, v2_targets, folds)
    v2 = {c: backtest.run(prices, v2_stitched, cost_bps=c,
                          risk_free=rf_daily).returns.loc[lo:hi] for c in costs}
    if abs(metrics.sharpe(v2[5.0]) - 0.700) > 0.003:
        print(f"v2 rebuild {metrics.sharpe(v2[5.0]):.3f} != journalled 0.700; stopping")
        return 1

    mix_targets = backtest.fixed_mix_targets(prices, {"SPY": 0.6, "IEF": 0.4})
    vt_mix_targets = vol_target_targets(prices, mix_targets, window=VOL_WINDOW,
                                        target_ann_vol=TARGET_ANN_VOL)
    spy = backtest.buy_and_hold(prices, "SPY", risk_free=rf_daily).returns.loc[lo:hi]

    named = {"SPY buy&hold": spy}
    for cost in costs:
        named[f"60/40 @{int(cost)}bps"] = backtest.run(
            prices, mix_targets, cost_bps=cost, risk_free=rf_daily).returns.loc[lo:hi]
        named[f"vol-target 60/40 @{int(cost)}bps"] = backtest.run(
            prices, vt_mix_targets, cost_bps=cost, risk_free=rf_daily).returns.loc[lo:hi]
    for cost in costs:
        named[f"v2 9-sector @{int(cost)}bps"] = v2[cost]
        named[f"v6 multi-asset @{int(cost)}bps"] = primary.oos_returns[cost]
        named[f"v6 +DBC @{int(cost)}bps"] = secondary.oos_returns[cost]

    print(f"\nOOS {lo.date()} .. {hi.date()} ({len(v2[5.0])} bars, "
          f"{len(v2[5.0])/252:.1f}y) — identical window to v2")
    print("\n=== stitched OOS vs incumbent and baselines, identical window ===")
    print(metrics.compare(named, rf_daily=rf_daily)[
        ["cagr", "ann_vol", "sharpe_rf0", "sharpe_rf", "max_drawdown",
         "dd_duration_days"]].round(4).to_string())

    print("\n=== annualized turnover @5bps ===")
    v2_turn = backtest.run(prices, v2_stitched, cost_bps=5.0, risk_free=rf_daily)
    print(f"  v2 9-sector      {metrics.ann_turnover(v2_turn.turnover.loc[lo:hi]):.3f}")
    print(f"  v6 multi-asset   {primary.summary().loc['OOS @5bps', 'ann_turnover']:.3f}")
    print(f"  v6 +DBC          {secondary.summary().loc['OOS @5bps', 'ann_turnover']:.3f}")

    # ---------------------------------------------------------------- diversification
    print("\n=== diversification: the claim this window can actually support ===")
    sleeve_returns = prices.pct_change().loc[lo:hi]
    holdings = {
        "v2 9-sector": v2_turn.holdings.loc[lo:hi],
        "v6 multi-asset": backtest.run(prices, stitch(
            prices, trend.ensemble_targets(prices, risk_assets=MULTI_ASSET, risk_off=None,
                                           lookback_months=LOOKBACKS), folds),
            cost_bps=5.0, risk_free=rf_daily).holdings.loc[lo:hi],
    }
    universes = {"v2 9-sector": SECTORS, "v6 multi-asset": MULTI_ASSET,
                 "v6 +DBC": SECONDARY}
    rows = []
    for label, sleeves in universes.items():
        window = sleeve_returns[sleeves].dropna()
        rows.append(diversification.diversification_report(
            window, label=f"{label} (equal wt)"))
        if label in holdings:
            avg = holdings[label][sleeves].loc[window.index].mean()
            if float(avg.sum()) > 0:
                rows.append(diversification.diversification_report(
                    window, weights=avg, label=f"{label} (realized wt)"))
    report = pd.DataFrame(rows).set_index("label")
    print(report[["n_sleeves", "n_obs", "avg_pairwise_corr", "min_pairwise_corr",
                  "max_pairwise_corr", "diversification_ratio", "effective_bets",
                  "effective_bets_pca"]].round(3).to_string())
    print("\n  extreme pairs:")
    for row in rows:
        print(f"    {row['label']:30s} most {row['most_correlated_pair']:12s} "
              f"least {row['least_correlated_pair']}")

    print("\n=== sub-periods @5bps: v6 multi-asset ===")
    print(primary.by_subperiod(5.0).round(4).to_string())
    print("\n=== sub-periods @5bps: v2 9-sector (reference) ===")
    print(metrics.by_subperiod(v2[5.0]).round(4).to_string())

    print("\n=== deflated Sharpe and effective breadth ===")
    for label, result in (("multi-asset", primary), ("+DBC", secondary)):
        print(f"\n-- {label} @5bps")
        print(dfl.report(result.deflated(5.0)))

    # ---------------------------------------------------------------- inference
    print(f"\n=== Sharpe with 95% CIs ({args.resamples} resamples, "
          f"block {stats.DEFAULT_BLOCK_LENGTH}) ===")
    for label, series in (("v6 multi-asset", primary.oos_returns[5.0]),
                          ("v6 +DBC", secondary.oos_returns[5.0]),
                          ("v2 9-sector", v2[5.0]),
                          ("SPY buy&hold", spy),
                          ("60/40", named["60/40 @5bps"]),
                          ("vol-target 60/40", named["vol-target 60/40 @5bps"])):
        point, low, high = stats.sharpe_confidence_interval(
            series, n_resamples=args.resamples)
        print(f"  {label:18s} {point:.3f}  95% CI [{low:.3f}, {high:.3f}]")

    print("\n=== paired Sharpe differences ===")
    pairs = [
        ("v6 multi-asset", primary.oos_returns[5.0], "v2 9-sector", v2[5.0]),
        ("v6 multi-asset", primary.oos_returns[5.0], "SPY buy&hold", spy),
        ("v6 multi-asset", primary.oos_returns[5.0], "60/40", named["60/40 @5bps"]),
        ("v6 multi-asset", primary.oos_returns[5.0], "vol-target 60/40",
         named["vol-target 60/40 @5bps"]),
        ("v6 +DBC", secondary.oos_returns[5.0], "v6 multi-asset",
         primary.oos_returns[5.0]),
    ]
    for label_a, a, label_b, b in pairs:
        print(f"\ncorrelation {a.corr(b):.4f}")
        print(stats.bootstrap_sharpe_difference(a, b, name_a=label_a, name_b=label_b,
                                                n_resamples=args.resamples).summary())
        print(stats.ledoit_wolf_sharpe_test(a, b, name_a=label_a,
                                            name_b=label_b).summary())

    print("\n=== external validation vs AQR TSMOM (monthly excess returns) ===")
    excess = {
        "v6 multi-asset": metrics.excess_returns(primary.oos_returns[5.0], rf_daily),
        "v6 +DBC": metrics.excess_returns(secondary.oos_returns[5.0], rf_daily),
        "v2 9-sector": metrics.excess_returns(v2[5.0], rf_daily),
        "SPY buy&hold": metrics.excess_returns(spy, rf_daily),
    }
    external_validation(excess, store)

    print("\nHarness output only; source-verification caveat stands; nothing promoted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
