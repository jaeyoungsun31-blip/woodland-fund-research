#!/usr/bin/env python3
"""Explore scheduled macro-event reversals; this is not a registered study.

Fixed definitions:
* FOMC events are scheduled meeting panels with actual statement links;
* CPI and jobs events are BLS annual-calendar entries named Consumer Price
  Index and Employment Situation;
* day 0 is adjusted-close-to-adjusted-close return on the release date;
* days +1..+5 are the next five available shared ETF/SPY trading days;
* excess correlations use ETF-minus-SPY on both day 0 and days +1..+5;
* bootstrap intervals are 10,000 paired event resamples, seed 0;
* minimum detectable correlation differences use a two-sided 5% Fisher-z
  approximation for two equal-size independent correlations at 80% power.
"""

from __future__ import annotations

import argparse
import csv
import html
import re
from math import sqrt
from pathlib import Path
from statistics import NormalDist
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "explore"
FED = "https://www.federalreserve.gov"
FOMC_CALENDAR_URL = f"{FED}/monetarypolicy/fomccalendars.htm"
BLS = "https://www.bls.gov"
ETFS = ("XLK", "XLE", "XLI", "XLB")
MARKET = "SPY"
N_BOOTSTRAP = 10_000
SEED = 0
POWER = 0.80
ALPHA = 0.05

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?\.?|Feb(?:ruary)?\.?|Mar(?:ch)?\.?|Apr(?:il)?\.?|May|"
    r"Jun(?:e)?\.?|Jul(?:y)?\.?|Aug(?:ust)?\.?|Sep(?:t(?:ember)?)?\.?|"
    r"Oct(?:ober)?\.?|Nov(?:ember)?\.?|Dec(?:ember)?\.?)"
)


def _download(url: str) -> str:
    agent = "Mozilla/5.0 (compatible; macro-reversal-research/1.0; +https://www.bls.gov/)"
    request = Request(url, headers={"User-Agent": agent})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed https .gov sources
        return response.read().decode("utf-8")


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment)).replace("\xa0", " ")


def _statement_url(fragment: str) -> str | None:
    match = re.search(
        r"Statement:</strong>\s*<br\s*/?>\s*<a href=\"[^\"]+\">PDF</a>\s*\|\s*"
        r"<a href=\"([^\"]+)\">HTML</a>",
        fragment,
        flags=re.IGNORECASE,
    )
    if match:
        return f"{FED}{html.unescape(match.group(1))}"
    historical = re.search(
        r"<a href=\"([^\"]+)\">Statement</a>", fragment, flags=re.IGNORECASE
    )
    return f"{FED}{html.unescape(historical.group(1))}" if historical else None


def _date_from_statement_url(url: str) -> str:
    match = re.search(r"(\d{8})(?:[a-z]?\.htm|/)", url, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"cannot extract statement date from {url}")
    value = match.group(1)
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def scheduled_fomc_statements() -> pd.DataFrame:
    events: list[dict[str, str]] = []
    for year in range(1999, 2021):
        calendar_url = f"{FED}/monetarypolicy/fomchistorical{year}.htm"
        page = _download(calendar_url)
        panels = re.findall(
            r"<h5[^>]*>(.*?)</h5>(.*?)(?=<h5[^>]*>|</main>|<footer)",
            page,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for heading_html, panel in panels:
            heading = _text(heading_html).casefold()
            excluded = ("conference", "unscheduled", "cancelled")
            if "meeting" not in heading or any(value in heading for value in excluded):
                continue
            statement = _statement_url(panel)
            if statement:
                events.append(
                    {
                        "date": _date_from_statement_url(statement),
                        "source_url": statement,
                        "calendar_url": calendar_url,
                    }
                )

    current = _download(FOMC_CALENDAR_URL)
    pattern = (
        r"Statement:</strong>\s*<br\s*/?>\s*<a href=\"[^\"]+\">PDF</a>\s*\|\s*"
        r"<a href=\"([^\"]+)\">HTML</a>"
    )
    for statement in re.findall(pattern, current, flags=re.IGNORECASE):
        url = f"{FED}{html.unescape(statement)}"
        date = _date_from_statement_url(url)
        if 2021 <= int(date[:4]) <= 2026:
            events.append(
                {"date": date, "source_url": url, "calendar_url": FOMC_CALENDAR_URL}
            )

    frame = pd.DataFrame(events).drop_duplicates("date").sort_values("date")
    if frame.empty or not frame.date.iloc[0].startswith("1999"):
        raise ValueError("Federal Reserve scheduled-statement parse is incomplete")
    return frame.reset_index(drop=True)


def _parse_bls_date(value: str, year: int) -> str:
    cleaned = " ".join(value.replace("Sept.", "Sep.").split())
    if not re.search(r"\b\d{4}\b", cleaned):
        cleaned = f"{cleaned}, {year}"
    return pd.Timestamp(cleaned).strftime("%Y-%m-%d")


def _bls_preformatted_events(page: str, year: int) -> list[tuple[str, str]]:
    soup = BeautifulSoup(page, "html.parser")
    events: list[tuple[str, str]] = []
    date_pattern = re.compile(
        rf"({MONTH_PATTERN}\s+\d{{1,2}}(?!\d)(?:,\s*\d{{4}})?)"
    )
    for pre in soup.find_all("pre"):
        for line in pre.get_text("\n").splitlines():
            normalized = " ".join(line.split())
            lower = normalized.casefold()
            if lower.startswith("consumer price index"):
                event_type = "cpi"
            elif lower.startswith("the employment situation") or lower.startswith(
                "employment situation"
            ):
                event_type = "jobs"
            else:
                continue
            match = date_pattern.search(normalized)
            if match:
                release_text = match.group(1)
                release_year = year
                if (
                    not re.search(r"\b\d{4}\b", release_text)
                    and re.search(rf"\bDecember\s+{year}\b", normalized)
                    and re.match(r"Jan", release_text, flags=re.IGNORECASE)
                ):
                    release_year += 1
                events.append((event_type, _parse_bls_date(release_text, release_year)))
    return events


def scheduled_bls_releases() -> dict[str, pd.DataFrame]:
    rows: dict[str, list[dict[str, str]]] = {"cpi": [], "jobs": []}
    for year in range(1999, 2027):
        calendar_url = f"{BLS}/schedule/{year}/home.htm"
        page = _download(calendar_url)
        soup = BeautifulSoup(page, "html.parser")
        found = 0
        for row in soup.select("table.release-list tbody tr"):
            date_cell = row.select_one("td.date-cell")
            release_cell = row.select_one("td.desc-cell strong")
            if not date_cell or not release_cell:
                continue
            release = " ".join(release_cell.get_text(" ", strip=True).split())
            event_type = {
                "Consumer Price Index": "cpi",
                "Employment Situation": "jobs",
            }.get(release)
            if event_type:
                rows[event_type].append(
                    {
                        "date": _parse_bls_date(date_cell.get_text(" ", strip=True), year),
                        "source_url": calendar_url,
                    }
                )
                found += 1
        if not found:
            for event_type, date in _bls_preformatted_events(page, year):
                rows[event_type].append({"date": date, "source_url": calendar_url})

    result: dict[str, pd.DataFrame] = {}
    for event_type, values in rows.items():
        frame = pd.DataFrame(values).drop_duplicates("date").sort_values("date")
        if frame.empty or not frame.date.iloc[0].startswith("1999"):
            raise ValueError(f"BLS {event_type} calendar parse is incomplete")
        result[event_type] = frame.reset_index(drop=True)
    return result


def _write_dates(filename: str, frame: pd.DataFrame) -> None:
    frame.to_csv(OUT / filename, index=False, quoting=csv.QUOTE_MINIMAL)


def pooled_events(events: dict[str, pd.DataFrame]) -> pd.DataFrame:
    all_dates = sorted(set().union(*(set(frame.date) for frame in events.values())))
    date_sets = {name: set(frame.date) for name, frame in events.items()}
    rows: list[dict[str, object]] = []
    for date in all_dates:
        flags = {name: date in values for name, values in date_sets.items()}
        sources = sorted(
            {
                str(url)
                for frame in events.values()
                for url in frame.loc[frame.date == date, "source_url"].tolist()
            }
        )
        rows.append(
            {
                "date": date,
                "fomc": flags["fomc"],
                "cpi": flags["cpi"],
                "jobs": flags["jobs"],
                "overlap": sum(flags.values()) > 1,
                "source_urls": " | ".join(sources),
            }
        )
    return pd.DataFrame(rows)


def _prices(symbol: str) -> pd.Series:
    frame = pd.read_parquet(ROOT / "data" / f"{symbol}.parquet")
    return pd.Series(frame["adj_close"], index=pd.DatetimeIndex(frame.index), name=symbol)


def event_frame(symbol: str, event_dates: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.Series]:
    prices = pd.concat([_prices(symbol), _prices(MARKET)], axis=1).dropna()
    returns = prices.pct_change().dropna()
    rows: list[dict[str, float | pd.Timestamp]] = []
    for event_date in event_dates:
        if event_date not in returns.index:
            continue
        position = int(returns.index.get_loc(event_date))
        if position + 5 >= len(returns.index):
            continue
        etf_forward = (1.0 + returns[symbol].iloc[position + 1 : position + 6]).prod() - 1.0
        spy_forward = (1.0 + returns[MARKET].iloc[position + 1 : position + 6]).prod() - 1.0
        rows.append(
            {
                "date": event_date,
                "day0": float(returns[symbol].iloc[position]),
                "forward_1_5": float(etf_forward),
                "day0_excess_spy": float(
                    returns[symbol].iloc[position] - returns[MARKET].iloc[position]
                ),
                "forward_1_5_excess_spy": float(etf_forward - spy_forward),
            }
        )
    event = pd.DataFrame(rows).set_index("date").sort_index()
    other = returns.loc[~returns.index.isin(event.index), symbol]
    return event, other


def correlation(frame: pd.DataFrame, excess: bool) -> float:
    left = "day0_excess_spy" if excess else "day0"
    right = "forward_1_5_excess_spy" if excess else "forward_1_5"
    return float(frame[left].corr(frame[right]))


def minimum_detectable_difference(n_events: int) -> float:
    if n_events <= 3:
        return float("nan")
    normal = NormalDist()
    critical = normal.inv_cdf(1.0 - ALPHA / 2.0) + normal.inv_cdf(POWER)
    fisher_gap = critical * sqrt(2.0 / (n_events - 3.0))
    return float(np.tanh(fisher_gap))


def bootstrap_difference(
    xlk: pd.DataFrame, physical: pd.DataFrame, label: str, *, excess: bool
) -> dict[str, float | int | str]:
    columns = ["day0", "forward_1_5", "day0_excess_spy", "forward_1_5_excess_spy"]
    paired = xlk[columns].join(
        physical[columns], how="inner", lsuffix="_xlk", rsuffix="_physical"
    )

    def pair_correlation(frame: pd.DataFrame, suffix: str) -> float:
        left = f"day0_excess_spy_{suffix}" if excess else f"day0_{suffix}"
        right = (
            f"forward_1_5_excess_spy_{suffix}" if excess else f"forward_1_5_{suffix}"
        )
        return float(frame[left].corr(frame[right]))

    observed = pair_correlation(paired, "xlk") - pair_correlation(paired, "physical")
    left_base = "day0_excess_spy" if excess else "day0"
    right_base = "forward_1_5_excess_spy" if excess else "forward_1_5"
    xlk_left = paired[f"{left_base}_xlk"].to_numpy(float)
    xlk_right = paired[f"{right_base}_xlk"].to_numpy(float)
    physical_left = paired[f"{left_base}_physical"].to_numpy(float)
    physical_right = paired[f"{right_base}_physical"].to_numpy(float)

    def sampled_correlations(left: np.ndarray, right: np.ndarray, index: np.ndarray) -> np.ndarray:
        sampled_left = left[index]
        sampled_right = right[index]
        left_centered = sampled_left - sampled_left.mean(axis=1, keepdims=True)
        right_centered = sampled_right - sampled_right.mean(axis=1, keepdims=True)
        numerator = np.sum(left_centered * right_centered, axis=1)
        denominator = np.sqrt(
            np.sum(left_centered**2, axis=1) * np.sum(right_centered**2, axis=1)
        )
        return numerator / denominator

    rng = np.random.default_rng(SEED)
    draws = np.empty(N_BOOTSTRAP)
    batch_size = 500
    for start in range(0, N_BOOTSTRAP, batch_size):
        stop = min(start + batch_size, N_BOOTSTRAP)
        index = rng.integers(0, len(paired), size=(stop - start, len(paired)))
        draws[start:stop] = sampled_correlations(xlk_left, xlk_right, index) - sampled_correlations(
            physical_left, physical_right, index
        )
    return {
        "comparison": f"XLK-minus-{label}",
        "measure": "excess" if excess else "raw",
        "n_events": int(len(paired)),
        "difference": float(observed),
        "ci_low": float(np.nanquantile(draws, 0.025)),
        "ci_high": float(np.nanquantile(draws, 0.975)),
    }


def analyze_event_set(
    event_set: str, dates: pd.DatetimeIndex
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int | str]]]:
    frames: dict[str, pd.DataFrame] = {}
    table: list[dict[str, float | int | str]] = []
    for symbol in ETFS:
        event, other = event_frame(symbol, dates)
        frames[symbol] = event
        table.append(
            {
                "event_set": event_set,
                "ETF": symbol,
                "n_events": int(len(event)),
                "mean_abs_day0_event": float(event.day0.abs().mean()),
                "mean_abs_day0_other": float(other.abs().mean()),
                "corr_raw": correlation(event, False),
                "corr_excess": correlation(event, True),
            }
        )
    intervals = [
        {
            "event_set": event_set,
            **bootstrap_difference(frames["XLK"], frames[symbol], symbol, excess=excess),
        }
        for excess in (False, True)
        for symbol in ("XLE", "XLI", "XLB")
    ]
    return table, intervals


def run() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fomc = scheduled_fomc_statements()
    bls = scheduled_bls_releases()
    events = {"fomc": fomc, "cpi": bls["cpi"], "jobs": bls["jobs"]}
    pooled = pooled_events(events)

    _write_dates("fomc-dates.csv", fomc)
    _write_dates("cpi-dates.csv", bls["cpi"])
    _write_dates("jobs-dates.csv", bls["jobs"])
    _write_dates("pooled-macro-dates.csv", pooled)

    all_tables: list[dict[str, float | int | str]] = []
    all_intervals: list[dict[str, float | int | str]] = []
    power_rows: list[dict[str, float | int | str]] = []
    analysis_dates = {
        **{name: frame.date for name, frame in events.items()},
        "pooled": pooled.date,
    }
    for event_set, values in analysis_dates.items():
        dates = pd.DatetimeIndex(pd.to_datetime(values))
        table, intervals = analyze_event_set(event_set, dates)
        all_tables.extend(table)
        all_intervals.extend(intervals)
        n_events = int(table[0]["n_events"])
        power_rows.append(
            {
                "event_set": event_set,
                "n_events": n_events,
                "mdd_corr_difference_80pct": minimum_detectable_difference(n_events),
            }
        )
    counts = pd.DataFrame(
        [
            {
                "fomc_calendar_dates": len(fomc),
                "cpi_calendar_dates": len(bls["cpi"]),
                "jobs_calendar_dates": len(bls["jobs"]),
                "pooled_unique_dates": len(pooled),
                "pooled_overlap_dates": int(pooled.overlap.sum()),
            }
        ]
    )
    return (
        pd.DataFrame(power_rows),
        pd.DataFrame(all_tables),
        pd.DataFrame(all_intervals),
        counts,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help="fetch official calendars and calculate the fixed exploration",
    )
    args = parser.parse_args()
    if not args.run:
        parser.error("pass --run to fetch official calendars and calculate the exploration")
    power, table, intervals, counts = run()
    pooled_mdd = float(
        power.loc[power.event_set == "pooled", "mdd_corr_difference_80pct"].iloc[0]
    )
    print(f"pooled_detects_gap_0.1={str(pooled_mdd <= 0.1).lower()}")
    print(power.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print()
    print(table.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print()
    print(intervals.to_string(index=False, float_format=lambda value: f"{value:.6f}"))
    print()
    print(counts.to_string(index=False))


if __name__ == "__main__":
    main()
