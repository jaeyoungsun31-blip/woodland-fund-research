"""Training-only insider primary rerun using the locked offline factor rules."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import cast

import numpy as np
import pandas as pd
from bias_corrections import factor_rows, load_factors
from first_returns import (
    BUCKETS,
    HERE,
    REPO,
    STORE,
    Trade,
    cluster_starts,
    corwin_schultz_spread,
    load_locked_inputs,
    simulate,
)
from holdout import require_training_events
from offline_adjustments import classify_symbol, event_marks

SERIES = HERE / "cache/offline_series"
TICKER_PATTERN = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}\Z")
PINNED_CASH_SHA256 = "ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7"
CLASS_NAMES = (
    "split",
    "dividend",
    "adjustment_error",
    "suspected_defect",
    "defect",
    "ordinary_raw",
    "unusable",
)


def read_local_raw(ticker: str) -> pd.DataFrame | None:
    path = STORE / f"{ticker}.US.parquet"
    if not path.exists():
        return None
    frame = pd.read_parquet(
        path,
        columns=["date", "open", "high", "low", "close", "adjusted_close", "volume"],
    )
    frame["date"] = pd.to_datetime(frame.date, errors="coerce")
    return (
        frame.dropna(subset=["date"])
        .drop_duplicates("date", keep="last")
        .set_index("date")
        .sort_index()
    )


def classify_training_symbols(events: pd.DataFrame) -> dict[str, int]:
    require_training_events(events.filing_date)
    SERIES.mkdir(parents=True, exist_ok=True)
    symbols = sorted(set(events.ticker.fillna("").astype(str)))
    status: Counter[str] = Counter()
    for index, ticker in enumerate(symbols, 1):
        if not TICKER_PATTERN.fullmatch(ticker):
            status["malformed_ticker"] += 1
            continue
        raw = read_local_raw(ticker)
        if raw is None or raw.empty:
            status["no_local_price"] += 1
            continue
        try:
            classified = classify_symbol(raw)
        except (ValueError, KeyError, TypeError):
            status["unclassifiable_price"] += 1
            continue
        classified.to_parquet(SERIES / f"{ticker}.parquet")
        status["classified"] += 1
        if index % 1000 == 0:
            print(f"Classified {index}/{len(symbols)} training ticker strings", flush=True)
    status["training_ticker_strings"] = len(symbols)
    return dict(status)


def load_classified(ticker: str) -> pd.DataFrame | None:
    path = SERIES / f"{ticker}.parquet"
    return pd.read_parquet(path) if path.exists() else None


def transaction_price_keys(
    transactions: pd.DataFrame, mapped: pd.DataFrame
) -> set[tuple[str, str, pd.Timestamp]]:
    require_training_events(transactions.filing_date)
    keys = ["ISSUERCIK", "RPTOWNERCIK", "filing_date"]
    source = transactions.copy()
    source["transaction_date"] = pd.to_datetime(
        source.TRANS_DATE, format="%d-%b-%Y", errors="coerce"
    )
    source["reported_price"] = pd.to_numeric(source.TRANS_PRICEPERSHARE, errors="coerce")
    joined = source.merge(mapped[keys + ["ticker"]], on=keys, how="inner")
    passed: set[tuple[str, str, pd.Timestamp]] = set()
    for ticker_value, group in joined.groupby("ticker", sort=False):
        ticker = cast(str, ticker_value)
        price = load_classified(ticker)
        if price is None:
            continue
        merged = group.merge(
            price[["low", "high"]].reset_index().rename(columns={"index": "date"}),
            left_on="transaction_date",
            right_on="date",
            how="inner",
        )
        okay = (
            np.isfinite(merged.reported_price)
            & (merged.reported_price > 0)
            & (merged.reported_price >= merged.low)
            & (merged.reported_price <= merged.high)
        )
        passed.update(
            tuple(row) for row in merged.loc[okay, keys].itertuples(index=False, name=None)
        )
    return passed


def screen_events(
    events: pd.DataFrame,
    valid_purchase: set[tuple[str, str, pd.Timestamp]],
    calendar: pd.DatetimeIndex,
    delisted: set[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict, pd.DataFrame]:
    require_training_events(events.filing_date)
    mapped = events.loc[events.mapping_status == "issuer_name_verified"]
    kept = []
    excluded = []
    failures: Counter[str] = Counter()
    class_rows = []
    for ticker_value, group in mapped.groupby("ticker", sort=False):
        ticker = cast(str, ticker_value)
        price = load_classified(ticker)
        if price is None:
            failures["missing_classified_symbol"] += len(group)
            continue
        groups_of_days: dict[tuple[str, int], set[int]] = defaultdict(set)
        for _, event in group.iterrows():
            identity = (event.ISSUERCIK, event.RPTOWNERCIK, event.filing_date)
            entry_loc = calendar.searchsorted(event.filing_date, side="right")
            if entry_loc < 60 or entry_loc + 60 >= len(calendar):
                failures["calendar_boundary"] += 1
                continue
            entry_date = calendar[entry_loc]
            target_date = calendar[entry_loc + 60]
            if entry_date not in price.index:
                failures["missing_entry"] += 1
                continue
            final = min(target_date, price.index[-1])
            terminal = final < target_date and ticker in delisted
            if final < target_date and not terminal:
                failures["short_nonterminal_series"] += 1
                continue
            expected = calendar[entry_loc - 60 : calendar.searchsorted(final, side="right")]
            if not expected.isin(price.index).all():
                failures["pre_or_post_gap"] += 1
                continue
            if not np.isfinite(event.liquidity_proxy_usd):
                failures["missing_liquidity"] += 1
                continue
            start_index = cast(int, price.index.get_loc(calendar[entry_loc - 20]))
            final_index = cast(int, price.index.get_loc(final))
            groups_of_days[(event.liquidity_bucket, event.filing_date.year)].update(
                range(start_index, final_index + 1)
            )
            window = price.iloc[start_index : final_index + 1]
            if window.defect.any():
                excluded.append(
                    {
                        "ticker": ticker,
                        "ISSUERCIK": event.ISSUERCIK,
                        "RPTOWNERCIK": event.RPTOWNERCIK,
                        "filing_date": event.filing_date,
                        "year": event.filing_date.year,
                        "bucket": event.liquidity_bucket,
                        "defect_days": int(window.defect.sum()),
                    }
                )
                continue
            if window.classification.eq("unusable").any():
                failures["unusable_window_bar"] += 1
                continue
            if identity not in valid_purchase:
                failures["reported_price_outside_raw_range"] += 1
                continue
            kept.append(event)
        labels = price.classification.to_numpy(str)
        for (bucket, year), positions in groups_of_days.items():
            counts = Counter(labels[list(positions)])
            for label in CLASS_NAMES:
                class_rows.append(
                    {
                        "bucket": bucket,
                        "filing_year": year,
                        "classification": label,
                        "symbol_days": counts[label],
                    }
                )
    selected = pd.DataFrame(kept)
    if selected.empty:
        raise RuntimeError("No purchases survive the locked offline rule")
    require_training_events(selected.filing_date)
    return selected, pd.DataFrame(excluded), dict(failures), pd.DataFrame(class_rows)


def build_primary_trades(
    starts: pd.DataFrame, calendar: pd.DatetimeIndex, delisted: set[str]
) -> tuple[list[Trade], pd.DataFrame, dict]:
    require_training_events(starts.filing_date)
    trades = []
    terminal_rows = []
    failures: Counter[str] = Counter()
    for ticker_value, group in starts.groupby("ticker", sort=False):
        ticker = cast(str, ticker_value)
        price = load_classified(ticker)
        if price is None:
            failures["missing_classified_symbol"] += len(group)
            continue
        for _, event in group.iterrows():
            entry_loc = calendar.searchsorted(event.filing_date, side="right")
            entry_date = calendar[entry_loc]
            target_date = calendar[entry_loc + 60]
            final = min(target_date, price.index[-1])
            terminal = final < target_date and ticker in delisted
            if final < target_date and not terminal:
                failures["short_nonterminal_series"] += 1
                continue
            expected = calendar[entry_loc : calendar.searchsorted(final, side="right")]
            if not expected.isin(price.index).all():
                failures["interior_gap"] += 1
                continue
            prior = price.loc[calendar[entry_loc - 20 : entry_loc]]
            spread = corwin_schultz_spread(prior.high.to_numpy(float), prior.low.to_numpy(float))
            if spread is None or spread + 0.0005 >= 1:
                failures["invalid_spread"] += 1
                continue
            try:
                opens, closes = event_marks(price, entry_date, final)
            except ValueError:
                failures["unusable_or_defect_path"] += 1
                continue
            trade = Trade(
                issuer_cik=str(event.ISSUERCIK),
                ticker=ticker,
                filing_date=event.filing_date,
                bucket=event.liquidity_bucket,
                entry_idx=entry_loc,
                exit_idx=entry_loc + len(expected) - 1,
                spread=spread,
                opens=opens,
                closes=closes,
                delisting_return=-0.3 if terminal else 0.0,
            )
            trades.append(trade)
            if terminal:
                terminal_rows.append(
                    {
                        "bucket": event.liquidity_bucket,
                        "ticker": ticker,
                        "filing_date": event.filing_date,
                        "last_price_date": final,
                        "in_eodhd_delisted_list": ticker in delisted,
                        "assumed_terminal_return": -0.3,
                    }
                )
    return trades, pd.DataFrame(terminal_rows), dict(failures)


def main() -> None:
    events, transactions = load_locked_inputs()
    require_training_events(events.filing_date)
    require_training_events(transactions.filing_date)
    status = classify_training_symbols(events)
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()
    delisted = {row["Code"] for row in json.loads((STORE / "delisted-symbols.json").read_text())}
    mapped = events.loc[events.mapping_status == "issuer_name_verified"]
    valid_purchase = transaction_price_keys(transactions, mapped)
    eligible, exclusions, screen_failures, class_days = screen_events(
        events, valid_purchase, calendar, delisted
    )
    starts = cluster_starts(eligible)
    trades, terminal, trade_failures = build_primary_trades(starts, calendar, delisted)
    cash_path = REPO / "data/fama_french_factors_daily.parquet"
    if hashlib.sha256(cash_path.read_bytes()).hexdigest() != PINNED_CASH_SHA256:
        raise RuntimeError("Pinned CASH index hash mismatch")
    cash = pd.read_parquet(cash_path).CASH
    official_monthly, _, _ = load_factors()
    iwm = pd.read_parquet(REPO / "data/IWM.parquet").adj_close.resample("ME").last().pct_change()
    summary_rows: list[dict[str, object]] = []
    factor_rows_out: list[dict[str, object]] = []
    portfolio_rows: list[pd.DataFrame] = []
    trade_rows: list[dict[str, object]] = []
    for bucket in BUCKETS:
        subset = [trade for trade in trades if trade.bucket == bucket]
        if not subset:
            continue
        monthly = simulate(subset, calendar, cash)
        aligned = monthly.set_index("month").join(iwm.rename("iwm"), how="inner")
        summary_rows.append(
            {
                "bucket": bucket,
                "clusters": len(subset),
                "active_months": len(aligned),
                "mean_gross_monthly_excess_iwm": float((aligned.gross - aligned.iwm).mean()),
                "mean_net_monthly_excess_iwm": float((aligned.net - aligned.iwm).mean()),
                "terminal_events": sum(trade.delisting_return < 0 for trade in subset),
            }
        )
        factor_rows_out.extend(factor_rows(monthly, official_monthly, bucket, "offline_rebuilt"))
        portfolio_rows.append(monthly.assign(bucket=bucket))
        trade_rows.extend(
            {
                "bucket": bucket,
                "ticker": trade.ticker,
                "filing_date": trade.filing_date,
                "entry_date": calendar[trade.entry_idx],
                "exit_date": calendar[trade.exit_idx],
                "gross_trade_return": trade.closes[-1]
                * (1 + trade.delisting_return)
                / trade.opens[0]
                - 1,
            }
            for trade in subset
        )
    pd.DataFrame(summary_rows).to_csv(HERE / "offline_rebuild_summary.csv", index=False)
    pd.DataFrame(factor_rows_out).to_csv(HERE / "offline_rebuild_factor_models.csv", index=False)
    pd.concat(portfolio_rows, ignore_index=True).to_csv(
        HERE / "offline_rebuild_monthly_portfolios.csv", index=False
    )
    pd.DataFrame(trade_rows).to_csv(HERE / "offline_rebuild_trades.csv", index=False)
    exclusions.to_csv(HERE / "offline_rebuild_exclusions.csv", index=False)
    class_days.groupby(
        ["bucket", "filing_year", "classification"], as_index=False
    ).symbol_days.sum().to_csv(HERE / "offline_rebuild_class_counts.csv", index=False)
    terminal.to_csv(HERE / "offline_rebuild_terminal_audit.csv", index=False)
    unmapped = events.loc[events.mapping_status != "issuer_name_verified"]
    metadata = {
        "symbol_status": status,
        "mapped_events": len(mapped),
        "reported_price_valid_keys": len(valid_purchase),
        "eligible_purchase_events": len(eligible),
        "cluster_starts": len(starts),
        "executed_primary_trades": len(trades),
        "defect_excluded_events": len(exclusions),
        "screen_failures": screen_failures,
        "trade_failures": trade_failures,
        "terminal_events": len(terminal),
        "unmapped_events": len(unmapped),
        "unmapped_sec_ticker_in_delisted_list": int(unmapped.ticker.isin(delisted).sum()),
    }
    (HERE / "offline_rebuild_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2), flush=True)


if __name__ == "__main__":
    main()
