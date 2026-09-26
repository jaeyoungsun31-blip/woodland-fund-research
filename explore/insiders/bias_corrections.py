"""Training-only, post-precommit bias diagnostics. Run from this directory."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from first_returns import (
    BUCKETS,
    HERE,
    REPO,
    STORE,
    Trade,
    cluster_starts,
    corwin_schultz_spread,
    load_locked_inputs,
    load_price,
    simulate,
    verify_transaction_prices,
)
from holdout import require_training_events

ARCHIVES = {
    "ff5_monthly": "F-F_Research_Data_5_Factors_2x3_CSV",
    "ff5_daily": "F-F_Research_Data_5_Factors_2x3_daily_CSV",
    "momentum_monthly": "F-F_Momentum_Factor_CSV",
    "momentum_daily": "F-F_Momentum_Factor_daily_CSV",
    "reversal_monthly": "F-F_ST_Reversal_Factor_CSV",
    "reversal_daily": "F-F_ST_Reversal_Factor_daily_CSV",
}
BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FACTOR_NAMES = ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom", "ST_Rev")


def read_french_archive(path: Path, date_digits: int) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != 1:
            raise RuntimeError(f"Unexpected French archive members: {path.name}")
        lines = archive.read(names[0]).decode("latin1").splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith(","))
    data = [lines[header]]
    for line in lines[header + 1 :]:
        first = line.split(",", 1)[0].strip()
        if len(first) != date_digits or not first.isdigit():
            break
        data.append(line)
    frame = pd.read_csv(io.StringIO("\n".join(data))).rename(columns={"Unnamed: 0": "date"})
    frame["date"] = pd.to_datetime(
        frame.date.astype(str), format="%Y%m" if date_digits == 6 else "%Y%m%d"
    )
    if date_digits == 6:
        frame["date"] = frame.date.dt.to_period("M").dt.to_timestamp("M")
    frame = frame.set_index("date")
    frame = frame.apply(pd.to_numeric, errors="coerce") / 100
    frame = frame.mask(frame <= -0.999)
    if frame.index.has_duplicates:
        raise RuntimeError(f"Duplicate factor dates in {path.name}")
    return frame


def load_factors() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    manifest = {}
    for key, stem in ARCHIVES.items():
        path = HERE / f"{stem}.zip"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest[key] = {"file": path.name, "url": BASE_URL + path.name, "sha256": digest}
    monthly = read_french_archive(HERE / f"{ARCHIVES['ff5_monthly']}.zip", 6)
    daily = read_french_archive(HERE / f"{ARCHIVES['ff5_daily']}.zip", 8)
    for key, column in (("momentum", "Mom"), ("reversal", "ST_Rev")):
        for frequency, target in (("monthly", monthly), ("daily", daily)):
            extra = read_french_archive(
                HERE / f"{ARCHIVES[f'{key}_{frequency}']}.zip", 6 if frequency == "monthly" else 8
            )
            target[column] = extra.iloc[:, 0].reindex(target.index)
    if monthly.loc["2012":"2022", FACTOR_NAMES].isna().any().any():
        raise RuntimeError("Missing official monthly factors in training period")
    (HERE / "french_archives_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return monthly, daily, manifest


def pre_entry_screen(events: pd.DataFrame, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    require_training_events(events.filing_date)
    eligible = events.loc[events.mapping_status == "issuer_name_verified"].copy()
    passed = pd.Series(False, index=eligible.index)
    reasons: Counter[str] = Counter()
    for ticker, group in eligible.groupby("ticker", sort=False):
        price = load_price(ticker)
        if price is None:
            reasons["no_price_file"] += len(group)
            continue
        dates = price.index
        for index, row in group.iterrows():
            entry = calendar.searchsorted(row.filing_date, side="right")
            if entry < 60 or entry >= len(calendar):
                reasons["calendar_boundary"] += 1
                continue
            expected = calendar[entry - 60 : entry + 1]
            if not expected.isin(dates).all():
                reasons["pre_entry_gap"] += 1
                continue
            prior = price.loc[expected]
            raw = prior.close.to_numpy(float)
            adj = prior.adjusted_close.to_numpy(float)
            high = prior.high.to_numpy(float)
            low = prior.low.to_numpy(float)
            if not (
                np.isfinite(raw).all()
                and np.isfinite(adj).all()
                and (raw > 0).all()
                and (adj > 0).all()
                and np.isfinite(high).all()
                and np.isfinite(low).all()
                and (low > 0).all()
                and (high >= low).all()
            ):
                reasons["invalid_pre_entry_price"] += 1
                continue
            change = adj[1:] / adj[:-1] - 1
            ratio = raw / adj
            ratio_change = ratio[1:] / ratio[:-1]
            large = (change > 0.8) | (change < -0.8)
            split_factors = np.array([0.1, 0.2, 0.25, 1 / 3, 0.5, 2, 3, 4, 5, 10])
            split_like = (np.abs(ratio_change[:, None] / split_factors - 1) < 0.03).any(axis=1)
            if (large & ~split_like).any():
                reasons["unexplained_pre_entry_jump"] += 1
                continue
            if not np.isfinite(row.liquidity_proxy_usd):
                reasons["missing_liquidity"] += 1
                continue
            passed.at[index] = True
    eligible = eligible.loc[passed].copy()
    eligible["quality_pass"] = True
    require_training_events(eligible.filing_date)
    return eligible, dict(reasons)


def build_trades(
    selected: pd.DataFrame,
    horizon: int,
    calendar: pd.DatetimeIndex,
    delisted_symbols: set[str],
    iwm: pd.DataFrame,
) -> tuple[list[Trade], list[Trade], dict, list[dict]]:
    require_training_events(selected.filing_date)
    trades: list[Trade] = []
    hedged: list[Trade] = []
    failed: Counter[str] = Counter()
    terminal_rows = []
    iwm_close = iwm.adj_close.reindex(calendar).to_numpy(float)
    iwm_open = (iwm.open * iwm.adj_close / iwm.close).reindex(calendar).to_numpy(float)
    for ticker, group in selected.groupby("ticker", sort=False):
        price = load_price(ticker)
        if price is None:
            failed["missing_price_file"] += len(group)
            continue
        dates = price.index
        is_delisted = ticker in delisted_symbols
        for _, row in group.iterrows():
            entry_date = calendar.searchsorted(row.filing_date, side="right")
            if entry_date < 120 or entry_date + horizon >= len(calendar):
                failed["calendar_boundary"] += 1
                continue
            target_date = calendar[entry_date + horizon]
            if calendar[entry_date] not in dates:
                failed["missing_entry"] += 1
                continue
            end_date = min(target_date, dates[-1])
            terminal = end_date < target_date and is_delisted
            if end_date < target_date and not terminal:
                failed["nonterminal_short_history"] += 1
                continue
            path_dates = calendar[entry_date : calendar.searchsorted(end_date, side="right")]
            if not path_dates.isin(dates).all():
                failed["interior_gap"] += 1
                continue
            price_path = price.loc[path_dates]
            prior = price.loc[calendar[entry_date - 20 : entry_date]]
            spread = corwin_schultz_spread(prior.high.to_numpy(float), prior.low.to_numpy(float))
            if spread is None:
                failed["invalid_spread"] += 1
                continue
            raw_open = price_path.open.to_numpy(float)
            raw_close = price_path.close.to_numpy(float)
            adj_close = price_path.adjusted_close.to_numpy(float)
            if not (
                np.isfinite(raw_open).all()
                and np.isfinite(raw_close).all()
                and np.isfinite(adj_close).all()
                and (raw_open > 0).all()
                and (raw_close > 0).all()
                and (adj_close > 0).all()
                and spread + 0.0005 < 1
            ):
                failed["invalid_path"] += 1
                continue
            opens = raw_open * adj_close / raw_close
            trade = Trade(
                issuer_cik=str(row.ISSUERCIK),
                ticker=ticker,
                filing_date=row.filing_date,
                bucket=row.liquidity_bucket,
                entry_idx=entry_date,
                exit_idx=entry_date + len(path_dates) - 1,
                spread=spread,
                opens=opens,
                closes=adj_close,
                delisting_return=-0.3 if terminal else 0.0,
            )
            trades.append(trade)
            if terminal:
                terminal_rows.append(
                    {
                        "bucket": trade.bucket,
                        "ticker": ticker,
                        "filing_date": row.filing_date,
                        "entry_date": calendar[entry_date],
                        "last_close_date": end_date,
                        "delisting_return": -0.3,
                        "reason": "unknown (EODHD symbol list has no reason field)",
                    }
                )
            # Prior 120 close-to-close sessions, ending before entry.
            beta_dates = calendar[entry_date - 120 : entry_date]
            if not beta_dates.isin(dates).all():
                failed["hedge_prior_120_missing"] += 1
                continue
            stock_prior = price.loc[beta_dates].adjusted_close.to_numpy(float)
            benchmark_prior = iwm_close[entry_date - 120 : entry_date]
            if not (np.isfinite(stock_prior).all() and np.isfinite(benchmark_prior).all()):
                failed["hedge_invalid_prior"] += 1
                continue
            stock_ret = np.diff(stock_prior) / stock_prior[:-1]
            iwm_ret = np.diff(benchmark_prior) / benchmark_prior[:-1]
            variance = float(np.var(iwm_ret, ddof=1))
            if variance <= 0:
                failed["hedge_zero_variance"] += 1
                continue
            beta = float(np.cov(stock_ret, iwm_ret, ddof=1)[0, 1] / variance)
            iwm_held_close = iwm_close[entry_date : trade.exit_idx + 1]
            iwm_held_open = iwm_open[entry_date : trade.exit_idx + 1]
            if not (np.isfinite(iwm_held_close).all() and np.isfinite(iwm_held_open).all()):
                failed["hedge_benchmark_path"] += 1
                continue
            stock_day = np.empty(len(path_dates))
            benchmark_day = np.empty(len(path_dates))
            stock_day[0] = adj_close[0] / opens[0] - 1
            benchmark_day[0] = iwm_held_close[0] / iwm_held_open[0] - 1
            if len(path_dates) > 1:
                stock_day[1:] = adj_close[1:] / adj_close[:-1] - 1
                benchmark_day[1:] = iwm_held_close[1:] / iwm_held_close[:-1] - 1
            hedge_day = stock_day - beta * benchmark_day
            if (hedge_day <= -1).any():
                failed["hedge_return_below_minus_one"] += 1
                continue
            synthetic_open = np.ones(len(path_dates))
            synthetic_close = np.ones(len(path_dates))
            for i, daily_return in enumerate(hedge_day):
                synthetic_open[i] = synthetic_close[i - 1] if i else 1.0
                synthetic_close[i] = synthetic_open[i] * (1 + daily_return)
            hedged.append(
                Trade(
                    issuer_cik=trade.issuer_cik,
                    ticker=ticker,
                    filing_date=trade.filing_date,
                    bucket=trade.bucket,
                    entry_idx=trade.entry_idx,
                    exit_idx=trade.exit_idx,
                    spread=spread,
                    opens=synthetic_open,
                    closes=synthetic_close,
                    delisting_return=trade.delisting_return,
                )
            )
    return trades, hedged, dict(failed), terminal_rows


def hac_fit(y: np.ndarray, x: np.ndarray, lag: int = 3) -> dict:
    design = np.column_stack([np.ones(len(y)), x])
    if len(y) <= design.shape[1] + lag:
        raise RuntimeError("Insufficient monthly observations for factor model")
    coefficient = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - design @ coefficient
    score = design * residual[:, None]
    meat = score.T @ score
    for offset in range(1, lag + 1):
        cross = score[offset:].T @ score[:-offset]
        meat += (1 - offset / (lag + 1)) * (cross + cross.T)
    inv = np.linalg.pinv(design.T @ design)
    covariance = inv @ meat @ inv
    se = np.sqrt(np.maximum(np.diag(covariance), 0))
    return {
        "coefficient": coefficient,
        "tstat": np.divide(coefficient, se, out=np.full_like(coefficient, np.nan), where=se > 0),
        "residual_std": float(np.std(residual, ddof=design.shape[1])),
        "n": len(y),
    }


def factor_rows(
    monthly: pd.DataFrame, french: pd.DataFrame, bucket: str, variant: str
) -> list[dict]:
    frame = monthly.set_index("month").join(french, how="inner").dropna()
    rows = []
    for model, names in (
        ("market", ("Mkt-RF",)),
        ("ff5_momentum", FACTOR_NAMES[:-1]),
        ("ff5_momentum_reversal", FACTOR_NAMES),
    ):
        fit = hac_fit((frame.net - frame.RF).to_numpy(float), frame[list(names)].to_numpy(float))
        row = {
            "variant": variant,
            "bucket": bucket,
            "model": model,
            "months": fit["n"],
            "alpha_monthly": fit["coefficient"][0],
            "alpha_t_hac3": fit["tstat"][0],
            "residual_std_monthly": fit["residual_std"],
        }
        row.update({name: value for name, value in zip(names, fit["coefficient"][1:], strict=True)})
        rows.append(row)
    return rows


def main() -> None:
    events, transactions = load_locked_inputs()
    require_training_events(events.filing_date)
    require_training_events(transactions.filing_date)
    french_monthly, _, manifest = load_factors()
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()
    iwm = pd.read_parquet(REPO / "data/IWM.parquet").sort_index()
    eligible_pre, screen_failures = pre_entry_screen(events, calendar)
    eligible, price_validation = verify_transaction_prices(eligible_pre, transactions)
    starts = cluster_starts(eligible)
    delisted = {item["Code"] for item in json.loads((STORE / "delisted-symbols.json").read_text())}
    trades, hedged, execution_failures, terminal_rows = build_trades(
        starts, 60, calendar, delisted, iwm
    )
    trade_audit = pd.DataFrame(
        [
            {
                "ticker": trade.ticker,
                "filing_date": trade.filing_date,
                "bucket": trade.bucket,
                "entry_date": calendar[trade.entry_idx],
                "exit_date": calendar[trade.exit_idx],
                "gross_trade_return": trade.closes[-1]
                * (1 + trade.delisting_return)
                / trade.opens[0]
                - 1,
                "max_daily_gain": float(np.max(trade.closes[1:] / trade.closes[:-1] - 1))
                if len(trade.closes) > 1
                else 0,
            }
            for trade in trades
        ]
    )
    trade_audit.to_csv(HERE / "survival_trade_audit.csv", index=False)
    cash_path = REPO / "data/fama_french_factors_daily.parquet"
    pinned_cash_sha256 = "ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7"
    if hashlib.sha256(cash_path.read_bytes()).hexdigest() != pinned_cash_sha256:
        raise RuntimeError("Pinned CASH index hash mismatch")
    cash = pd.read_parquet(cash_path).CASH
    old = pd.read_csv(HERE / "returns_summary.csv")
    iwm_monthly = iwm.adj_close.resample("ME").last().pct_change()
    summary, monthly_rows, fits = [], [], []
    for bucket in BUCKETS:
        subset = [trade for trade in trades if trade.bucket == bucket]
        monthly = simulate(subset, calendar, cash)
        monthly_rows.append(monthly.assign(bucket=bucket, variant="survival_corrected"))
        frame = monthly.set_index("month").join(iwm_monthly.rename("iwm"), how="inner").dropna()
        baseline = old.loc[(old.variant == "primary_clusters_60d") & (old.bucket == bucket)].iloc[0]
        summary.append(
            {
                "bucket": bucket,
                "clusters": len(subset),
                "months": len(frame),
                "terminal_events": sum(trade.delisting_return < 0 for trade in subset),
                "gross_excess_iwm": float((frame.gross - frame.iwm).mean()),
                "net_excess_iwm": float((frame.net - frame.iwm).mean()),
                "previous_gross_excess_iwm": baseline.mean_gross_monthly_excess_iwm,
                "previous_net_excess_iwm": baseline.mean_net_monthly_excess_iwm,
            }
        )
        fits.extend(factor_rows(monthly, french_monthly, bucket, "survival_corrected"))
    for bucket in BUCKETS:
        subset = [trade for trade in hedged if trade.bucket == bucket]
        monthly = simulate(subset, calendar, cash)
        monthly_rows.append(monthly.assign(bucket=bucket, variant="iwm_hedged"))
        fits.extend(factor_rows(monthly, french_monthly, bucket, "iwm_hedged"))
    primary = next(
        row
        for row in monthly_rows
        if row.bucket.iloc[0] == "under_300k" and row.variant.iloc[0] == "survival_corrected"
    )
    primary_frame = primary.set_index("month").join(french_monthly, how="inner").dropna()
    robustness = []
    for label, sub in (
        ("exclude_2020", primary_frame.loc[primary_frame.index.year != 2020]),
        ("2012_2016", primary_frame.loc[primary_frame.index.year <= 2016]),
        (
            "2017_2022H1_filing_cohort_with_later_exits",
            primary_frame.loc[primary_frame.index.year >= 2017],
        ),
    ):
        fit = hac_fit((sub.net - sub.RF).to_numpy(float), sub[list(FACTOR_NAMES)].to_numpy(float))
        robustness.append(
            {
                "period": label,
                "months": fit["n"],
                "alpha_monthly": fit["coefficient"][0],
                "alpha_t_hac3": fit["tstat"][0],
            }
        )
    summary_frame = pd.DataFrame(summary)
    summary_frame["gross_change"] = (
        summary_frame.gross_excess_iwm - summary_frame.previous_gross_excess_iwm
    )
    summary_frame["net_change"] = (
        summary_frame.net_excess_iwm - summary_frame.previous_net_excess_iwm
    )
    summary_frame.to_csv(HERE / "survival_correction_summary.csv", index=False)
    pd.concat(monthly_rows, ignore_index=True).to_csv(
        HERE / "bias_corrected_monthly.csv", index=False
    )
    pd.DataFrame(fits).to_csv(HERE / "official_factor_regressions.csv", index=False)
    pd.DataFrame(robustness).to_csv(HERE / "primary_bucket_robustness.csv", index=False)
    pd.DataFrame(terminal_rows).to_csv(HERE / "terminal_events.csv", index=False)
    result = {
        "pre_entry_screen_failures": screen_failures,
        "price_validation": price_validation,
        "cluster_starts": len(starts),
        "executed_trades": len(trades),
        "hedged_trades": len(hedged),
        "execution_failures": execution_failures,
        "terminal_events": len(terminal_rows),
        "factor_archives": manifest,
    }
    (HERE / "bias_correction_metadata.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
