"""Re-evaluate training identities without consulting later SEC filings.

Uses only the explicit pre-holdout SEC selection. Price-quality flags already
computed from a symbol's bars are reused where identity was already verified;
newly verified historical identities get the same bar-based screen.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from analyze_feasibility import read_price, score_name
from holdout import require_training_events

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STORE = REPO / "data/Woodland-EODHD"


def screen_new_event(row: pd.Series, price: pd.DataFrame, calendar: pd.DatetimeIndex) -> dict:
    valid = price[(price.close > 0) & (price.adjusted_close > 0)]
    dates = valid.index
    filing = row.filing_date
    nearby = dates[(dates >= filing - pd.Timedelta(days=5)) & (dates <= filing)]
    if len(nearby) == 0:
        return {"verified": False}
    last = dates.get_loc(nearby[-1])
    dollar_volume = (
        valid.close.iloc[max(0, last - 19) : last + 1]
        * valid.volume.iloc[max(0, last - 19) : last + 1]
    )
    dollar_volume = dollar_volume[np.isfinite(dollar_volume) & (dollar_volume >= 0)]
    liquidity = float(dollar_volume.median()) if len(dollar_volume) else float("nan")
    bucket = (
        "under_300k"
        if liquidity < 300_000
        else "300k_to_2m"
        if liquidity < 2_000_000
        else "over_2m"
    )
    position = calendar.searchsorted(filing, side="left")
    if position < 60 or position + 120 >= len(calendar):
        return {
            "verified": True,
            "bucket": bucket,
            "liquidity": liquidity,
            "coverage": False,
            "gap": False,
            "jump": False,
            "reason": "calendar right/left censored",
        }
    expected = calendar[position - 60 : position + 121]
    actual = dates[(dates >= expected[0]) & (dates <= expected[-1])]
    missing = expected.difference(actual)
    locations = calendar.searchsorted(actual)
    gap = bool(len(locations) > 1 and np.diff(locations).max() > 10)
    loc = dates.get_indexer(actual)
    jump = False
    split_like_jump = False
    if len(loc) > 1:
        raw = valid.close.to_numpy(float)
        adjusted = valid.adjusted_close.to_numpy(float)
        change = adjusted[loc[1:]] / adjusted[loc[:-1]] - 1
        ratio = raw[loc] / adjusted[loc]
        ratio_change = ratio[1:] / ratio[:-1]
        large = (change > 0.8) | (change < -0.8)
        factors = np.array([0.1, 0.2, 0.25, 1 / 3, 0.5, 2, 3, 4, 5, 10])
        like_split = (np.abs(ratio_change[:, None] / factors - 1) < 0.03).any(axis=1)
        jump = bool((large & ~like_split).any())
        split_like_jump = bool((large & like_split).any())
    return {
        "verified": True,
        "bucket": bucket,
        "liquidity": liquidity,
        "coverage": len(missing) == 0,
        "gap": gap,
        "jump": jump,
        "split_like_jump": split_like_jump,
        "reason": "" if len(missing) == 0 else f"{len(missing)} missing sessions",
    }


def main() -> None:
    events = pd.read_parquet(HERE / "training_events.parquet")
    require_training_events(events.filing_date)
    active = {row["Code"]: row for row in json.loads((STORE / "active-symbols.json").read_text())}
    delisted = {
        row["Code"]: row for row in json.loads((STORE / "delisted-symbols.json").read_text())
    }
    catalog = {**active, **delisted}
    events = events.sort_values(["filing_date", "ISSUERCIK", "RPTOWNERCIK"]).copy()
    firsts = events.groupby(["ticker", "ISSUERCIK"]).filing_date.min().reset_index()
    ticker_firsts = {
        ticker: group.filing_date.sort_values().to_numpy()
        for ticker, group in firsts.groupby("ticker")
    }
    events["asof_reused_ticker"] = [
        np.searchsorted(ticker_firsts[ticker], filing.to_datetime64(), side="right") > 1
        for ticker, filing in zip(events.ticker, events.filing_date, strict=True)
    ]
    events["filing_name_score"] = [
        score_name(name, catalog[ticker]["Name"]) if ticker in catalog else 0.0
        for name, ticker in zip(events.ISSUERNAME, events.ticker, strict=True)
    ]
    events["asof_name_score"] = events.groupby(["ISSUERCIK", "ticker"])[
        "filing_name_score"
    ].cummax()
    prior_status = events.mapping_status.copy()
    valid_symbol = events.ticker.str.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}")
    verified = (
        valid_symbol
        & events.ticker.isin(catalog)
        & ~events.asof_reused_ticker
        & (events.asof_name_score >= 0.85)
    )
    events["mapping_status"] = "no_match"
    events.loc[events.asof_reused_ticker, "mapping_status"] = "reused_ticker"
    events.loc[verified, "mapping_status"] = "issuer_name_verified"
    newly = events.index[verified & (prior_status != "issuer_name_verified")]
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()
    price_cache = {}
    for index in newly:
        ticker = events.at[index, "ticker"]
        if ticker not in price_cache:
            price_cache[ticker] = read_price(ticker)
        price = price_cache[ticker]
        if price is None:
            events.at[index, "mapping_status"] = "no_match"
            continue
        screen = screen_new_event(events.loc[index], price, calendar)
        if not screen["verified"]:
            events.at[index, "mapping_status"] = "no_match"
            continue
        events.at[index, "price_on_filing"] = True
        events.at[index, "liquidity_proxy_usd"] = screen["liquidity"]
        events.at[index, "liquidity_bucket"] = screen["bucket"]
        events.at[index, "full_window_coverage"] = screen["coverage"]
        events.at[index, "gap_over_10_sessions"] = screen["gap"]
        events.at[index, "unexplained_adjusted_jump_over_80pct"] = screen["jump"]
        events.at[index, "possible_split_like_jump"] = screen.get("split_like_jump", False)
        events.at[index, "coverage_failure"] = screen["reason"]
    # Previously verified events retain only bar-derived flags. A historical
    # CIK/name check, recomputed above, determines whether they remain mapped.
    events["quality_pass"] = (
        (events.mapping_status == "issuer_name_verified")
        & events.full_window_coverage
        & ~events.gap_over_10_sessions
        & ~events.unexplained_adjusted_jump_over_80pct
    )
    require_training_events(events.filing_date)
    events.to_parquet(HERE / "training_events_asof.parquet", index=False)
    metadata = {
        "events": len(events),
        "mapping_status": dict(Counter(events.mapping_status)),
        "quality_pass": int(events.quality_pass.sum()),
        "new_name_score_candidates": int(len(newly)),
        "newly_verified_events": int(
            (
                (prior_status != "issuer_name_verified")
                & (events.mapping_status == "issuer_name_verified")
            ).sum()
        ),
        "previously_verified_but_now_refused": int(
            (
                (prior_status == "issuer_name_verified")
                & (events.mapping_status != "issuer_name_verified")
            ).sum()
        ),
        "source_scope": "SEC code-P filings through 2022-06-30 only; no later SEC names or CIKs",
    }
    (HERE / "training_mapping_asof.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
