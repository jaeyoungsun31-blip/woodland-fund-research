"""Insider-purchase event, identity, liquidity, and price-quality feasibility checks.

No return or P&L computation. All files written stay beside this script.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STORE = REPO / "data/Woodland-EODHD"


def normalize_name(value: str) -> str:
    words = re.sub(r"[^A-Z0-9 ]", " ", str(value).upper()).split()
    ignored = {
        "INC",
        "INCORPORATED",
        "CORP",
        "CORPORATION",
        "CO",
        "COMPANY",
        "LTD",
        "LIMITED",
        "PLC",
        "LLC",
        "THE",
        "OF",
        "DE",
        "SA",
        "NV",
        "HOLDINGS",
        "HOLDING",
        "GROUP",
        "CLASS",
        "COMMON",
        "STOCK",
        "SHARES",
        "SHARE",
        "ORDINARY",
        "A",
        "B",
        "C",
        "NEW",
        "COM",
        "PAR",
        "VALUE",
        "PER",
    }
    return " ".join(word for word in words if word not in ignored)


def score_name(left: str, right: str) -> float:
    a, b = normalize_name(left), normalize_name(right)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def read_price(symbol: str) -> pd.DataFrame | None:
    path = STORE / f"{symbol}.US.parquet"
    if not path.exists():
        return None
    frame = pd.read_parquet(path, columns=["date", "close", "adjusted_close", "volume"])
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame.dropna(subset=["date"]).drop_duplicates("date", keep="last")
    return frame.sort_values("date").set_index("date")


def cluster_counts(events: pd.DataFrame) -> tuple[int, int]:
    unique = events[["ISSUERCIK", "RPTOWNERCIK", "filing_date"]].drop_duplicates()
    clustered = []
    for _, group in unique.groupby("ISSUERCIK", sort=False):
        group = group.sort_values("filing_date")
        dates = group.filing_date.to_numpy(dtype="datetime64[D]")
        owners = group.RPTOWNERCIK.to_numpy()
        for date in np.unique(dates):
            left = np.searchsorted(dates, date - np.timedelta64(30, "D"), side="left")
            right = np.searchsorted(dates, date, side="right")
            if len(set(owners[left:right])) >= 2:
                clustered.append((str(date), group.ISSUERCIK.iloc[0]))
    return len(clustered), len({date for date, _ in clustered})


def main() -> None:
    source = pd.read_parquet(HERE / "sec_code_p_events.parquet")
    source["filing_date"] = pd.to_datetime(source.FILING_DATE, format="%d-%b-%Y")
    source["transaction_date"] = pd.to_datetime(
        source.TRANS_DATE, format="%d-%b-%Y", errors="coerce"
    )
    source["ticker"] = source.ISSUERTRADINGSYMBOL.fillna("").str.upper().str.strip()
    # One issuer-insider-filing date is one event; retain each as-filed transaction
    # in the SEC source parquet for audit, but do not multiply event counts.
    events = (
        source.sort_values(["transaction_date", "ACCESSION_NUMBER"], na_position="last")
        .drop_duplicates(["ISSUERCIK", "RPTOWNERCIK", "filing_date"])
        .copy()
    )
    events["year"] = events.filing_date.dt.year
    valid_lag = events.transaction_date.notna() & (events.transaction_date <= events.filing_date)
    valid_lag &= events.transaction_date >= pd.Timestamp("2012-01-01")
    events["business_lag"] = np.nan
    events.loc[valid_lag, "business_lag"] = np.busday_count(
        events.loc[valid_lag, "transaction_date"].to_numpy(dtype="datetime64[D]"),
        events.loc[valid_lag, "filing_date"].to_numpy(dtype="datetime64[D]"),
    )
    annual = events.groupby("year", as_index=False).agg(
        events=("ISSUERCIK", "size"),
        distinct_issuers=("ISSUERCIK", "nunique"),
        valid_lags=("business_lag", "count"),
        median_weekday_lag=("business_lag", "median"),
        within_two_weekdays=("business_lag", lambda x: int(x.between(0, 2).sum())),
    )
    annual["within_two_weekdays_share"] = annual.within_two_weekdays / annual.valid_lags
    annual.to_csv(HERE / "events_by_year.csv", index=False)

    active_path = STORE / "active-symbols.json"
    delisted_path = STORE / "delisted-symbols.json"
    active = {row["Code"]: row for row in json.loads(active_path.read_text())}
    delisted = {row["Code"]: row for row in json.loads(delisted_path.read_text())}
    catalog = {**active, **delisted}
    cik_by_ticker = events.groupby("ticker").ISSUERCIK.nunique()
    reused = set(cik_by_ticker[cik_by_ticker > 1].index)
    score_by_key = {}
    for (cik, ticker), group in source.groupby(["ISSUERCIK", "ticker"]):
        if ticker in catalog:
            names = group.ISSUERNAME.dropna().unique()
            if len(names):
                score_by_key[(cik, ticker)] = max(
                    score_name(name, catalog[ticker]["Name"]) for name in names
                )
    names_per_cik = source.groupby("ISSUERCIK").ISSUERNAME.nunique()
    valid_ticker = events.ticker.str.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}")
    events["name_score"] = [
        score_by_key.get((cik, ticker), 0.0)
        for cik, ticker in zip(events.ISSUERCIK, events.ticker, strict=True)
    ]
    events["mapping_status"] = "no_match"
    events.loc[events.ticker.isin(reused), "mapping_status"] = "reused_ticker"
    name_change = (events.ISSUERCIK.map(names_per_cik) > 1) & (events.mapping_status == "no_match")
    events.loc[name_change, "mapping_status"] = "name_change_unverified"
    verified = (
        valid_ticker
        & events.ticker.isin(catalog)
        & ~events.ticker.isin(reused)
        & (events.name_score >= 0.85)
    )
    events.loc[verified, "mapping_status"] = "issuer_name_verified"
    events["delisted_catalog"] = events.ticker.isin(delisted)
    events["price_on_filing"] = False
    events["liquidity_proxy_usd"] = np.nan
    events["liquidity_bucket"] = "unavailable"
    events["full_window_coverage"] = False
    events["gap_over_10_sessions"] = False
    events["unexplained_adjusted_jump_over_80pct"] = False
    events["possible_split_like_jump"] = False
    events["coverage_failure"] = "mapping not verified"
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    if "date" in spy.columns:
        calendar = pd.DatetimeIndex(pd.to_datetime(spy.date)).sort_values().unique()
    else:
        calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()

    for ticker, group in events.loc[verified].groupby("ticker", sort=False):
        price = read_price(ticker)
        if price is None or price.empty:
            events.loc[group.index, "mapping_status"] = "no_match"
            events.loc[group.index, "coverage_failure"] = "no EODHD price file"
            continue
        valid_rows = price[(price.close > 0) & (price.adjusted_close > 0)]
        dates = valid_rows.index
        values = valid_rows[["close", "adjusted_close", "volume"]]
        close = values.close.to_numpy(dtype=float)
        adjusted = values.adjusted_close.to_numpy(dtype=float)
        volume = values.volume.to_numpy(dtype=float)
        for index, event in group.iterrows():
            filing = event.filing_date
            nearby = dates[(dates >= filing - pd.Timedelta(days=5)) & (dates <= filing)]
            if len(nearby) == 0:
                events.at[index, "mapping_status"] = "no_match"
                events.at[index, "coverage_failure"] = "no price on or within 5 days before filing"
                continue
            events.at[index, "price_on_filing"] = True
            price_pos = dates.get_loc(nearby[-1])
            trailing_start = max(0, price_pos - 19)
            dollar_volume = (
                close[trailing_start : price_pos + 1] * volume[trailing_start : price_pos + 1]
            )
            dollar_volume = dollar_volume[np.isfinite(dollar_volume) & (dollar_volume >= 0)]
            if len(dollar_volume):
                liquidity = float(np.median(dollar_volume))
                events.at[index, "liquidity_proxy_usd"] = liquidity
                events.at[index, "liquidity_bucket"] = (
                    "under_300k"
                    if liquidity < 300_000
                    else "300k_to_2m"
                    if liquidity < 2_000_000
                    else "over_2m"
                )
            position = calendar.searchsorted(filing, side="left")
            if position < 60 or position + 120 >= len(calendar):
                events.at[index, "coverage_failure"] = "calendar right/left censored"
                continue
            expected = calendar[position - 60 : position + 121]
            actual = dates[(dates >= expected[0]) & (dates <= expected[-1])]
            missing = expected.difference(actual)
            events.at[index, "full_window_coverage"] = len(missing) == 0
            events.at[index, "coverage_failure"] = (
                "" if len(missing) == 0 else f"{len(missing)} missing sessions"
            )
            session_locs = calendar.searchsorted(actual)
            events.at[index, "gap_over_10_sessions"] = bool(
                len(session_locs) > 1 and np.diff(session_locs).max() > 10
            )
            local = dates.get_indexer(actual)
            if len(local) > 1:
                adj_change = adjusted[local[1:]] / adjusted[local[:-1]] - 1
                ratio = close[local] / adjusted[local]
                ratio_change = ratio[1:] / ratio[:-1]
                jump = (adj_change > 0.8) | (adj_change < -0.8)
                split_factors = np.array([0.1, 0.2, 0.25, 1 / 3, 0.5, 2, 3, 4, 5, 10])
                split_like = (np.abs(ratio_change[:, None] / split_factors - 1) < 0.03).any(axis=1)
                events.at[index, "possible_split_like_jump"] = bool((jump & split_like).any())
                events.at[index, "unexplained_adjusted_jump_over_80pct"] = bool(
                    (jump & ~split_like).any()
                )

    events["quality_pass"] = (
        (events.mapping_status == "issuer_name_verified")
        & events.full_window_coverage
        & ~events.gap_over_10_sessions
        & ~events.unexplained_adjusted_jump_over_80pct
    )
    event_columns = [
        "ACCESSION_NUMBER",
        "ISSUERCIK",
        "ISSUERNAME",
        "ticker",
        "RPTOWNERCIK",
        "RPTOWNER_RELATIONSHIP",
        "filing_date",
        "transaction_date",
        "business_lag",
        "year",
        "mapping_status",
        "name_score",
        "delisted_catalog",
        "price_on_filing",
        "liquidity_proxy_usd",
        "liquidity_bucket",
        "full_window_coverage",
        "gap_over_10_sessions",
        "unexplained_adjusted_jump_over_80pct",
        "possible_split_like_jump",
        "coverage_failure",
        "quality_pass",
    ]
    events[event_columns].to_parquet(HERE / "event_feasibility.parquet", index=False)
    failures = (
        events.loc[events.mapping_status != "issuer_name_verified"]
        .groupby(["ISSUERCIK", "ticker", "mapping_status"], as_index=False)
        .agg(
            issuer_name=("ISSUERNAME", "first"),
            events=("ISSUERCIK", "size"),
            earliest_filing=("filing_date", "min"),
            latest_filing=("filing_date", "max"),
            best_name_score=("name_score", "max"),
            reason=("coverage_failure", "first"),
        )
    )
    failures.to_csv(HERE / "mapping_failures.csv", index=False)
    mapped = events[events.mapping_status == "issuer_name_verified"]
    buckets = mapped.groupby("liquidity_bucket", as_index=False).agg(
        events=("ISSUERCIK", "size"),
        quality_pass=("quality_pass", "sum"),
        full_coverage=("full_window_coverage", "sum"),
        unexplained_jumps=("unexplained_adjusted_jump_over_80pct", "sum"),
        long_gaps=("gap_over_10_sessions", "sum"),
    )
    buckets["quality_pass_rate"] = buckets.quality_pass / buckets.events
    buckets.to_csv(HERE / "quality_by_liquidity.csv", index=False)
    clusters, dates = cluster_counts(events)
    valid = events.business_lag.dropna()
    summary = {
        "source_transaction_rows": len(source),
        "distinct_issuer_insider_filing_events": len(events),
        "distinct_issuer_ciks": int(events.ISSUERCIK.nunique()),
        "valid_filing_lags": len(valid),
        "median_weekday_filing_lag": float(valid.median()),
        "share_within_two_weekdays": float(valid.between(0, 2).mean()),
        "mapping_status_counts": dict(Counter(events.mapping_status)),
        "mapping_success_rate": float((events.mapping_status == "issuer_name_verified").mean()),
        "cluster_issuer_filing_dates": clusters,
        "cluster_distinct_calendar_dates": dates,
        "catalog_active_sha256": hashlib.sha256(active_path.read_bytes()).hexdigest(),
        "catalog_delisted_sha256": hashlib.sha256(delisted_path.read_bytes()).hexdigest(),
        "mapped_delisted_coverage_failure_rate": float(
            1 - mapped.loc[mapped.delisted_catalog, "full_window_coverage"].mean()
        ),
        "mapped_active_coverage_failure_rate": float(
            1 - mapped.loc[~mapped.delisted_catalog, "full_window_coverage"].mean()
        ),
    }
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
