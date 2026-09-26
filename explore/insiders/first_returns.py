"""Locked pre-holdout insider-cluster return probe.

Reads only explicit training selections, calls the holdout guard before any
price/factor access, and writes outputs only beside this script.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from holdout import require_training_events

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STORE = REPO / "data/Woodland-EODHD"
FACTORS = REPO / "data/fama_french_factors_daily.parquet"
FACTORS_SHA256 = "ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7"
BUCKETS = ("under_300k", "300k_to_2m", "over_2m")


@dataclass(slots=True)
class Trade:
    issuer_cik: str
    ticker: str
    filing_date: pd.Timestamp
    bucket: str
    entry_idx: int
    exit_idx: int
    spread: float
    opens: np.ndarray
    closes: np.ndarray
    delisting_return: float = 0.0


def load_locked_inputs(
    events_path: Path = HERE / "training_events_asof.parquet",
    transactions_path: Path = HERE / "training_transactions.parquet",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    events = pd.read_parquet(events_path)
    transactions = pd.read_parquet(transactions_path)
    require_training_events(events.filing_date)
    require_training_events(transactions.filing_date)
    return events, transactions


def load_price(ticker: str) -> pd.DataFrame | None:
    path = STORE / f"{ticker}.US.parquet"
    if not path.exists():
        return None
    frame = pd.read_parquet(
        path, columns=["date", "open", "high", "low", "close", "adjusted_close"]
    )
    frame["date"] = pd.to_datetime(frame.date, errors="coerce")
    frame = frame.dropna(subset=["date"]).drop_duplicates("date", keep="last")
    return frame.sort_values("date").set_index("date")


def verify_transaction_prices(
    events: pd.DataFrame, transactions: pd.DataFrame
) -> tuple[pd.DataFrame, dict[str, int]]:
    eligible = events.loc[events.quality_pass].copy()
    keys = ["ISSUERCIK", "RPTOWNERCIK", "filing_date"]
    matched = transactions.merge(eligible[keys + ["ticker"]], on=keys, how="inner")
    matched["transaction_date"] = pd.to_datetime(
        matched.TRANS_DATE, format="%d-%b-%Y", errors="coerce"
    )
    matched["reported_price"] = pd.to_numeric(matched.TRANS_PRICEPERSHARE, errors="coerce")
    valid_keys = []
    rows_checked = 0
    for ticker, group in matched.groupby("ticker", sort=False):
        price = load_price(ticker)
        if price is None:
            continue
        joined = group.merge(
            price[["low", "high"]].reset_index(),
            left_on="transaction_date",
            right_on="date",
            how="inner",
        )
        rows_checked += len(joined)
        okay = (
            np.isfinite(joined.reported_price)
            & (joined.reported_price > 0)
            & (joined.low > 0)
            & (joined.high >= joined.low)
            & (joined.reported_price >= joined.low)
            & (joined.reported_price <= joined.high)
        )
        valid_keys.append(joined.loc[okay, keys])
    if not valid_keys:
        raise RuntimeError("No SEC purchases passed raw-day price validation")
    valid = pd.concat(valid_keys).drop_duplicates()
    eligible = eligible.merge(valid.assign(reported_price_in_range=True), on=keys, how="inner")
    require_training_events(eligible.filing_date)
    return eligible, {
        "mapped_quality_events": int(events.quality_pass.sum()),
        "transaction_rows_with_matching_price_day": rows_checked,
        "events_passing_reported_price_check": len(eligible),
    }


def cluster_starts(events: pd.DataFrame) -> pd.DataFrame:
    starts = []
    for _, group in events.groupby("ISSUERCIK", sort=False):
        ordered = group.sort_values(["filing_date", "RPTOWNERCIK"])
        history: list[tuple[pd.Timestamp, str]] = []
        last_start: pd.Timestamp | None = None
        for filing, daily in ordered.groupby("filing_date", sort=True):
            history = [
                (day, owner) for day, owner in history if day >= filing - pd.Timedelta(days=30)
            ]
            history.extend((filing, str(owner)) for owner in daily.RPTOWNERCIK)
            if len({owner for _, owner in history}) < 2:
                continue
            if last_start is not None and filing <= last_start + pd.Timedelta(days=90):
                continue
            starts.append(daily.iloc[0])
            last_start = filing
    if not starts:
        return events.iloc[0:0].copy()
    return pd.DataFrame(starts).reset_index(drop=True)


def corwin_schultz_spread(high: np.ndarray, low: np.ndarray) -> float | None:
    if len(high) != 20 or len(low) != 20:
        return None
    if not np.isfinite(high).all() or not np.isfinite(low).all():
        return None
    if (low <= 0).any() or (high < low).any():
        return None
    ranges = np.log(high / low)
    beta = ranges[:-1] ** 2 + ranges[1:] ** 2
    gamma = np.log(np.maximum(high[:-1], high[1:]) / np.minimum(low[:-1], low[1:])) ** 2
    constant = 3 - 2 * np.sqrt(2)
    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / constant - np.sqrt(gamma / constant)
    alpha = np.maximum(alpha, 0)
    spread = 2 * np.expm1(alpha) / (1 + np.exp(alpha))
    estimate = float(np.median(spread))
    return estimate if np.isfinite(estimate) and 0 <= estimate < 1 else None


def build_trades(
    selected: pd.DataFrame, horizon: int, calendar: pd.DatetimeIndex
) -> tuple[list[Trade], dict[str, int]]:
    require_training_events(selected.filing_date)
    trades = []
    failure: dict[str, int] = defaultdict(int)
    for ticker, group in selected.groupby("ticker", sort=False):
        price = load_price(ticker)
        if price is None:
            failure["missing_file"] += len(group)
            continue
        dates = price.index
        for _, row in group.iterrows():
            entry = dates.searchsorted(row.filing_date, side="right")
            exit_ = entry + horizon
            if entry < 20 or exit_ >= len(dates):
                failure["insufficient_bars"] += 1
                continue
            prior = price.iloc[entry - 20 : entry]
            spread = corwin_schultz_spread(prior.high.to_numpy(float), prior.low.to_numpy(float))
            if spread is None:
                failure["invalid_spread"] += 1
                continue
            path = price.iloc[entry : exit_ + 1]
            global_dates = calendar.get_indexer(path.index)
            if (global_dates < 0).any() or (np.diff(global_dates) != 1).any():
                failure["calendar_gap"] += 1
                continue
            raw_open = path.open.to_numpy(float)
            raw_close = path.close.to_numpy(float)
            adjusted_close = path.adjusted_close.to_numpy(float)
            if not (
                np.isfinite(raw_open).all()
                and np.isfinite(raw_close).all()
                and np.isfinite(adjusted_close).all()
                and (raw_open > 0).all()
                and (raw_close > 0).all()
                and (adjusted_close > 0).all()
            ):
                failure["invalid_path_price"] += 1
                continue
            adjusted_open = raw_open * adjusted_close / raw_close
            if not (path.low.iloc[0] <= path.open.iloc[0] <= path.high.iloc[0]):
                failure["invalid_entry_open"] += 1
                continue
            if not (path.low.iloc[-1] <= path.close.iloc[-1] <= path.high.iloc[-1]):
                failure["invalid_exit_close"] += 1
                continue
            if spread + 0.0005 >= 1:
                failure["cost_exceeds_capital"] += 1
                continue
            trades.append(
                Trade(
                    issuer_cik=str(row.ISSUERCIK),
                    ticker=ticker,
                    filing_date=row.filing_date,
                    bucket=row.liquidity_bucket,
                    entry_idx=int(global_dates[0]),
                    exit_idx=int(global_dates[-1]),
                    spread=spread,
                    opens=adjusted_open,
                    closes=adjusted_close,
                )
            )
    return trades, dict(failure)


def nw_alpha(y: np.ndarray, market_excess: np.ndarray, lag: int = 3) -> tuple[float, float]:
    if len(y) < lag + 4:
        return float("nan"), float("nan")
    x = np.column_stack([np.ones(len(y)), market_excess])
    xtx_inv = np.linalg.inv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    residual = y - x @ beta
    score = x * residual[:, None]
    meat = score.T @ score
    for offset in range(1, lag + 1):
        weight = 1 - offset / (lag + 1)
        cross = score[offset:].T @ score[:-offset]
        meat += weight * (cross + cross.T)
    covariance = xtx_inv @ meat @ xtx_inv
    standard_error = float(np.sqrt(max(covariance[0, 0], 0)))
    alpha = float(beta[0])
    return alpha, alpha / standard_error if standard_error > 0 else float("nan")


def simulate(
    trades: list[Trade], calendar: pd.DatetimeIndex, cash_levels: pd.Series
) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=["month", "gross", "net", "active_days"])
    entries: dict[int, list[int]] = defaultdict(list)
    exits: dict[int, list[int]] = defaultdict(list)
    for index, trade in enumerate(trades):
        entries[trade.entry_idx].append(index)
        exits[trade.exit_idx].append(index)
    first = min(entries)
    last = max(exits)
    rf = cash_levels.reindex(calendar).ffill().pct_change().fillna(0).to_numpy(float)
    states = {"gross": {"cash": 1.0, "units": {}}, "net": {"cash": 1.0, "units": {}}}
    rows = []
    previous_month = None
    for day in range(first, last + 1):
        month = calendar[day].to_period("M")
        incoming = entries.get(day, [])
        departing = exits.get(day, [])
        active_today = bool(incoming) or any(state["units"] for state in states.values())
        row = {"date": calendar[day], "month": month, "active": active_today}
        for label, state in states.items():
            cash = float(state["cash"]) * (1 + rf[day])
            units: dict[int, float] = state["units"]
            held = list(units)
            open_values = {
                idx: units[idx] * trades[idx].opens[day - trades[idx].entry_idx] for idx in held
            }
            open_nav = cash + sum(open_values.values())
            if month != previous_month or incoming:
                active = held + incoming
                if active:
                    target = open_nav / len(active)
                    for idx in held:
                        units[idx] = target / trades[idx].opens[day - trades[idx].entry_idx]
                    for idx in incoming:
                        cost = trades[idx].spread + 0.0005 if label == "net" else 0.0
                        units[idx] = target * (1 - cost) / trades[idx].opens[0]
                    cash = 0.0
            close_values = {
                idx: units[idx]
                * trades[idx].closes[day - trades[idx].entry_idx]
                * (1 + trades[idx].delisting_return if idx in departing else 1)
                for idx in list(units)
            }
            for idx in departing:
                value = close_values.pop(idx)
                cost = trades[idx].spread + 0.0005 if label == "net" else 0.0
                cash += value * (1 - cost)
                del units[idx]
            state["cash"] = cash
            row[label] = cash + sum(close_values.values())
        rows.append(row)
        previous_month = month
    daily = pd.DataFrame(rows).set_index("date")
    monthly = daily.groupby("month").agg(
        gross_nav=("gross", "last"),
        net_nav=("net", "last"),
        active_days=("active", "sum"),
    )
    for label in ("gross", "net"):
        prior = monthly[f"{label}_nav"].shift(1).fillna(1)
        monthly[label] = monthly[f"{label}_nav"] / prior - 1
    monthly = monthly.loc[monthly.active_days > 0, ["gross", "net", "active_days"]]
    monthly.index = monthly.index.to_timestamp("M")
    return monthly.reset_index(names="month")


def summarize_portfolio(
    trades: list[Trade], monthly: pd.DataFrame, iwm: pd.Series, factors: pd.DataFrame
) -> dict[str, float | int]:
    frame = monthly.set_index("month").join(iwm.rename("iwm"), how="inner")
    frame = frame.join(factors[["MKT", "CASH"]], how="inner").dropna()
    if frame.empty:
        raise RuntimeError("No complete monthly benchmark/factor observations")
    gross_excess = frame.gross - frame.iwm
    net_excess = frame.net - frame.iwm
    alpha, tstat = nw_alpha(
        (frame.net - frame.CASH).to_numpy(float),
        (frame.MKT - frame.CASH).to_numpy(float),
    )
    return {
        "clusters_or_events": len(trades),
        "active_months": len(frame),
        "mean_gross_monthly_excess_iwm": float(gross_excess.mean()),
        "mean_net_monthly_excess_iwm": float(net_excess.mean()),
        "market_factor_alpha_monthly": alpha,
        "alpha_hac_tstat_lag3": tstat,
        "worst_net_month": float(frame.net.min()),
        "worst_net_excess_iwm_month": float(net_excess.min()),
        "mean_round_trip_spread_charge": float(np.mean([2 * trade.spread for trade in trades])),
    }


def monthly_benchmarks(calendar: pd.DatetimeIndex) -> tuple[pd.Series, pd.DataFrame, pd.Series]:
    observed = hashlib.sha256(FACTORS.read_bytes()).hexdigest()
    if observed != FACTORS_SHA256:
        raise RuntimeError("Pinned Fama-French-derived file hash mismatch")
    factor_levels = pd.read_parquet(FACTORS).sort_index()
    if list(factor_levels.columns) != ["MKT", "CASH"]:
        raise RuntimeError("Unexpected pinned factor columns")
    iwm_frame = pd.read_parquet(REPO / "data/IWM.parquet")
    if "date" in iwm_frame.columns:
        iwm_frame = iwm_frame.set_index(pd.to_datetime(iwm_frame.date))
    iwm_levels = iwm_frame.adj_close.sort_index()
    monthly_iwm = iwm_levels.resample("ME").last().pct_change()
    monthly_factors = factor_levels.resample("ME").last().pct_change()
    return monthly_iwm, monthly_factors, factor_levels.CASH


def bias_diagnostics(
    all_events: pd.DataFrame,
    eligible: pd.DataFrame,
    kept_starts: pd.DataFrame,
    calendar: pd.DatetimeIndex,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    potential = cluster_starts(all_events)
    quality_starts = cluster_starts(all_events.loc[all_events.quality_pass])

    def keys(frame: pd.DataFrame) -> set[tuple[str, pd.Timestamp]]:
        return set(zip(frame.ISSUERCIK, frame.filing_date, strict=True))

    kept_keys = keys(kept_starts)
    quality_keys = keys(quality_starts)
    eligible_keys = keys(cluster_starts(eligible))
    all_events = all_events.sort_values("filing_date")
    issuer_events = {cik: group for cik, group in all_events.groupby("ISSUERCIK")}
    records = []
    for _, row in potential.iterrows():
        identity = (row.ISSUERCIK, row.filing_date)
        if identity in kept_keys:
            status = "kept"
        elif identity in quality_keys and identity not in eligible_keys:
            status = "reported_price_check"
        elif identity in quality_keys:
            status = "execution_or_timing"
        else:
            group = issuer_events[row.ISSUERCIK]
            trail = group.loc[
                group.filing_date.between(row.filing_date - pd.Timedelta(days=30), row.filing_date)
            ]
            mapped = trail.loc[trail.mapping_status == "issuer_name_verified"]
            if mapped.RPTOWNERCIK.nunique() < 2:
                status = "mapping_failure"
            elif trail.loc[trail.quality_pass].RPTOWNERCIK.nunique() < 2:
                status = "quality_screen"
            else:
                status = "cluster_timing_shift"
        records.append(
            {
                "ISSUERCIK": row.ISSUERCIK,
                "ticker": row.ticker,
                "filing_date": row.filing_date,
                "year": row.filing_date.year,
                "status": status,
                "mapping_status": row.mapping_status,
                "pre_60d_return": np.nan,
            }
        )
    bias = pd.DataFrame(records)
    for ticker, group in bias.loc[bias.mapping_status == "issuer_name_verified"].groupby(
        "ticker", sort=False
    ):
        price = load_price(ticker)
        if price is None:
            continue
        adjusted = price.adjusted_close
        for idx, row in group.iterrows():
            last_before = calendar.searchsorted(row.filing_date, side="left") - 1
            if last_before < 60:
                continue
            dates = calendar[last_before - 60 : last_before + 1]
            if not dates.isin(adjusted.index).all():
                continue
            levels = adjusted.loc[dates].to_numpy(float)
            if np.isfinite(levels).all() and (levels > 0).all():
                bias.at[idx, "pre_60d_return"] = levels[-1] / levels[0] - 1
    year = bias.groupby("year").status.value_counts().unstack(fill_value=0)
    for field in (
        "kept",
        "mapping_failure",
        "quality_screen",
        "reported_price_check",
        "execution_or_timing",
        "cluster_timing_shift",
    ):
        if field not in year:
            year[field] = 0
    year["potential_starts"] = year.sum(axis=1)
    year["mapping_or_quality_loss_share"] = (
        year.mapping_failure + year.quality_screen
    ) / year.potential_starts
    return bias, year.reset_index()


def main() -> None:
    events, transactions = load_locked_inputs()
    # The lock has been checked before any price or factor file is opened.
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()
    eligible, validation = verify_transaction_prices(events, transactions)
    starts = cluster_starts(eligible)
    starts.to_parquet(HERE / "eligible_cluster_starts.parquet", index=False)
    eligible.to_parquet(HERE / "eligible_purchase_events.parquet", index=False)
    iwm, factors, cash = monthly_benchmarks(calendar)
    result_rows = []
    monthly_rows = []
    trade_rows = []
    executions = {}
    for variant, selected, horizon in (
        ("primary_clusters_60d", starts, 60),
        ("sensitivity_singles_60d", eligible, 60),
        ("sensitivity_clusters_20d", starts, 20),
    ):
        trades, failed = build_trades(selected, horizon, calendar)
        executions[variant] = {
            "candidate_rows": len(selected),
            "executed_rows": len(trades),
            "failures": failed,
        }
        for bucket in BUCKETS:
            subset = [trade for trade in trades if trade.bucket == bucket]
            if not subset:
                continue
            monthly = simulate(subset, calendar, cash)
            result_rows.append(
                {
                    "variant": variant,
                    "bucket": bucket,
                    **summarize_portfolio(subset, monthly, iwm, factors),
                }
            )
            monthly.insert(0, "bucket", bucket)
            monthly.insert(0, "variant", variant)
            monthly_rows.append(monthly)
            trade_rows.extend(
                {
                    "variant": variant,
                    "bucket": bucket,
                    "ISSUERCIK": trade.issuer_cik,
                    "ticker": trade.ticker,
                    "filing_date": trade.filing_date,
                    "entry_date": calendar[trade.entry_idx],
                    "exit_date": calendar[trade.exit_idx],
                    "spread": trade.spread,
                }
                for trade in subset
            )
        print(f"{variant}: {len(trades)} executable positions", flush=True)
    pd.DataFrame(result_rows).to_csv(HERE / "returns_summary.csv", index=False)
    pd.concat(monthly_rows, ignore_index=True).to_csv(HERE / "monthly_portfolios.csv", index=False)
    pd.DataFrame(trade_rows).to_parquet(HERE / "executed_trades.parquet", index=False)
    bias, by_year = bias_diagnostics(events, eligible, starts, calendar)
    bias.to_parquet(HERE / "bias_events.parquet", index=False)
    by_year.to_csv(HERE / "bias_by_year.csv", index=False)
    bias["kept_or_lost"] = np.where(bias.status == "kept", "kept", "lost")
    pre60 = bias.groupby("kept_or_lost", as_index=False).agg(
        potential_starts=("ISSUERCIK", "size"),
        pre60_available=("pre_60d_return", "count"),
        median_pre60_return=("pre_60d_return", "median"),
        share_positive_pre60=("pre_60d_return", lambda x: float((x.dropna() > 0).mean())),
    )
    pre60.to_csv(HERE / "bias_pre60_summary.csv", index=False)
    metadata = {
        "validation": validation,
        "execution": executions,
        "pinned_factors_sha256": FACTORS_SHA256,
        "training_events_asof_sha256": hashlib.sha256(
            (HERE / "training_events_asof.parquet").read_bytes()
        ).hexdigest(),
        "training_transactions_sha256": hashlib.sha256(
            (HERE / "training_transactions.parquet").read_bytes()
        ).hexdigest(),
    }
    (HERE / "return_run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
