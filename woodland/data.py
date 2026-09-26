"""Data ingestion and integrity checks.

Rules (DESIGN.md §4-5):
  * Raw downloads are stored immutably; derived matrices are rebuilt, never edited.
  * The research return series must be TOTAL-return (dividend-adjusted). Price-only
    series silently understate bond/ETF returns (for TLT/IEF the yield is most of
    the return), so `adj_close` is the dividend+split adjusted series and the
    unadjusted `close` is kept alongside for realism checks.

SOURCES (DESIGN.md §5, amended 2026-09-01)
  * Primary: Yahoo via yfinance (`auto_adjust=False`), which supplies the
    unadjusted OHLCV and the adjusted close in one request, on one calendar.
  * Cross-check: Tiingo (free keyed API, 20+ yrs of adjusted EOD) on every
    ingest — see journal/2026-09-01-second-source-decision.md.
  * Stooq is retired: it now serves a JavaScript proof-of-work anti-bot
    interstitial on stooq.com and stooq.pl alike, and we do not defeat bot
    detection (journal/2026-09-01-data-source-stooq-blocked.md).

  The cross-check compares the two providers' ADJUSTED closes, day by day, in
  return space. That is deliberate: the adjusted series is the one research
  actually consumes, so checking it tests the number we use rather than a
  neighbouring one. Raw closes would be the weaker test — Yahoo's `close` is
  split-adjusted while Tiingo's is as-traded, so every split would register as
  a false disagreement.

  A single-source ingest is never reported as "ok"; it is reported as
  NO SECOND SOURCE.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
import requests

log = logging.getLogger(__name__)

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d"
PROVENANCE_FILE = "_provenance.json"

OHLCV = ["open", "high", "low", "close", "volume", "adj_close"]
APPROVED_CROSSCHECK_BACKFILLS = {pd.Timestamp("2026-08-28")}


# ---------------------------------------------------------------- fetchers

def fetch_yahoo(ticker: str, start: str) -> pd.DataFrame:
    """Unadjusted OHLCV plus the dividend+split adjusted close, from one request.

    Taking both series from a single download guarantees they share a calendar
    and an identical split treatment, which is what makes `check_adjustment`
    meaningful.
    """
    import yfinance as yf  # optional dependency (crosscheck extra)

    df = yf.download(ticker, start=start, auto_adjust=False, actions=False, progress=False)
    if df is None or df.empty:
        raise ValueError(f"yfinance returned no data for {ticker!r}")
    if isinstance(df.columns, pd.MultiIndex):  # (field, ticker) for single downloads
        df.columns = [c[0] for c in df.columns]
    missing = {"Open", "High", "Low", "Close", "Adj Close", "Volume"} - set(df.columns)
    if missing:
        raise ValueError(f"yfinance response for {ticker!r} missing columns: {sorted(missing)}")
    out = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Adj Close": "adj_close", "Volume": "volume",
    })[OHLCV]
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out.index.name = "Date"
    return pd.DataFrame(out.sort_index())


def fetch_stooq(ticker: str, timeout: int = 30) -> pd.DataFrame:
    """Daily OHLCV from Stooq (US listing). Returns a Date-indexed DataFrame.

    Currently blocked by an anti-bot JS challenge (see module docstring); kept
    wired so the cross-check resumes automatically if access is restored.
    Stooq's US closes are split-adjusted but NOT dividend-adjusted — raw
    close only, never a research return series.
    """
    url = STOOQ_URL.format(symbol=f"{ticker.lower()}.us")
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    if not resp.text.startswith("Date"):
        raise ValueError(f"Stooq returned no CSV for {ticker!r}: {resp.text[:80]!r}")
    df = pd.read_csv(io.StringIO(resp.text), parse_dates=["Date"], index_col="Date")
    df.columns = [c.lower() for c in df.columns]
    return df.sort_index()


TIINGO_URL = "https://api.tiingo.com/tiingo/daily/{ticker}/prices"


def fetch_tiingo(ticker: str, start: str, token: str | None = None,
                 timeout: int = 30) -> pd.DataFrame:
    """Daily OHLCV + adjusted close from Tiingo. The cross-check source.

    The API key travels in the Authorization HEADER, never as a URL query
    parameter: query strings end up in proxy logs, browser history and error
    messages, and a leaked key is a rotation event.
    """
    from woodland.config import get_secret

    token = token or get_secret("TIINGO_API_KEY")
    if not token:
        raise RuntimeError(
            "TIINGO_API_KEY not set. Put it in .env (gitignored) or the "
            "environment; see journal/2026-09-01-second-source-decision.md"
        )
    resp = requests.get(
        TIINGO_URL.format(ticker=ticker.lower()),
        params={"startDate": start, "format": "csv"},
        headers={"Authorization": f"Token {token}"},
        timeout=timeout,
    )
    if resp.status_code == 404:
        raise ValueError(f"Tiingo has no series for {ticker!r}")
    if resp.status_code == 429:
        raise RuntimeError(f"Tiingo rate limit hit on {ticker!r}; retry later")
    resp.raise_for_status()
    if not resp.text.lstrip().startswith("date"):
        raise ValueError(f"Tiingo returned no CSV for {ticker!r}: {resp.text[:80]!r}")

    df = pd.read_csv(io.StringIO(resp.text), parse_dates=["date"], index_col="date")
    missing = {"open", "high", "low", "close", "volume", "adjClose"} - set(df.columns)
    if missing:
        raise ValueError(f"Tiingo response for {ticker!r} missing {sorted(missing)}")
    out = df.rename(columns={"adjClose": "adj_close"})[OHLCV]
    out.index = pd.to_datetime(out.index).tz_localize(None)
    out.index.name = "Date"
    return out.sort_index()


SOURCES = {
    "yahoo": fetch_yahoo,
    "tiingo": fetch_tiingo,
    "stooq": lambda t, start: fetch_stooq(t),
}


# ---------------------------------------------------------------- checks

def check_adjustment(df: pd.DataFrame, tol: float = 1e-4) -> dict:
    """Validate the dividend adjustment WITHIN one source.

    adj_close/close is a cumulative dividend-discount factor: it must be
    non-decreasing through time (each payment lifts every earlier price by a
    smaller fraction) and must reach 1.0 on the most recent bar, where no
    future dividends remain to discount. Violations mean a mismatched,
    stale, or spliced adjustment series.

    This is NOT a substitute for a second source: it cannot detect a price
    both series get wrong together.
    """
    both = df[["close", "adj_close"]].dropna()
    if len(both) < 2:
        return {"n": len(both), "verdict": "insufficient data"}
    ratio = both["adj_close"] / both["close"]
    drops = ratio.diff().dropna()
    worst_drop = float(drops.min())
    terminal = float(ratio.iloc[-1])
    problems = []
    if worst_drop < -tol:
        problems.append(f"adjustment factor decreases (worst {worst_drop:.2e})")
    if abs(terminal - 1.0) > tol:
        problems.append(f"terminal factor {terminal:.6f} != 1.0")
    if (both["close"] <= 0).any() or (both["adj_close"] <= 0).any():
        problems.append("nonpositive prices")
    return {
        "n": len(both),
        "first_factor": float(ratio.iloc[0]),
        "terminal_factor": terminal,
        "worst_factor_drop": worst_drop,
        "verdict": "ok" if not problems else "INVESTIGATE: " + "; ".join(problems),
    }


# A single-day adjusted move at least this large, with the adjustment factor
# unchanged across it, is a candidate missed corporate action. Both numbers are
# declared here rather than tuned: see journal 2026-09-07 (SYMC).
MISSED_EVENT_MOVE = 0.25
MISSED_EVENT_FACTOR_TOL = 1e-3


def check_missed_events(
    df: pd.DataFrame,
    move_threshold: float = MISSED_EVENT_MOVE,
    factor_tolerance: float = MISSED_EVENT_FACTOR_TOL,
    adj_column: str = "adj_close",
) -> dict:
    """Screen for corporate actions the adjusted series did not apply.

    ``check_adjustment`` cannot see this defect. It tests the adjustment factor
    for DECREASING and for a terminal value away from 1.0, and a missed event
    leaves the factor perfectly FLAT: if ``adjusted_close`` simply follows
    ``close`` through a split, ``adj_close/close`` never moves. Run against
    Symantec's file it returns "ok" while the adjusted series records a
    two-for-one split as a 48.6% loss.

    So this looks for the opposite signature - a large single-day adjusted
    return with an unchanged factor across it.

    **This is a screen, not a detector, and it cannot be made into one from
    inside a single file.** A genuine 30% earnings crash has exactly the same
    signature as a missed split: a large move with no adjustment, because there
    was nothing to adjust. Volume does not separate them either, since EODHD
    split-adjusts historical volume (journal 2026-09-07). Separating the two
    needs a second source or a cited corporate-action calendar; every hit here
    is a CANDIDATE and nothing is corrected.
    """
    column = adj_column if adj_column in df.columns else "adj_close"
    both = df[["close", column]].dropna()
    both = both[(both["close"] > 0) & (both[column] > 0)]
    if len(both) < 2:
        return {"n": len(both), "n_candidates": 0, "verdict": "insufficient data"}

    factor = (both[column] / both["close"]).to_numpy(float)
    adjusted = both[column].to_numpy(float)
    raw = both["close"].to_numpy(float)
    index = both.index

    adj_return = adjusted[1:] / adjusted[:-1] - 1.0
    raw_return = raw[1:] / raw[:-1] - 1.0
    factor_change = np.abs(factor[1:] / factor[:-1] - 1.0)
    flagged = (np.abs(adj_return) >= move_threshold) & (factor_change <= factor_tolerance)

    labels = [
        str(label.date()) if isinstance(label, pd.Timestamp) else str(label)
        for label in index
    ]
    candidates = [
        {
            "date": labels[position + 1],
            "adj_return": round(float(adj_return[position]), 6),
            "raw_return": round(float(raw_return[position]), 6),
            "price_ratio": round(float(raw[position + 1] / raw[position]), 6),
            "factor_rel_change": float(factor_change[position]),
        }
        for position in np.flatnonzero(flagged).tolist()
    ]
    return {
        "n": len(both),
        "move_threshold": move_threshold,
        "factor_tolerance": factor_tolerance,
        "n_candidates": len(candidates),
        "candidates": candidates,
        "verdict": "ok" if not candidates else
                   f"CANDIDATE MISSED EVENT: {len(candidates)} day(s)",
    }


def crosscheck_sources(
    primary: pd.Series,
    secondary: pd.Series,
    fail_tolerance: float = 0.02,
    monitor_tolerance: float = 0.005,
) -> dict:
    """Compare two INDEPENDENT providers' ADJUSTED closes on overlapping days.

    Compares daily RETURNS, not levels: two providers can hold different
    adjustment epochs (Yahoo rebases so the latest bar is unadjusted; others
    normalise elsewhere), which shifts every level by a constant factor while
    leaving returns identical. Returns are also what the backtest consumes, so
    a disagreement here is a disagreement that would reach a result.

    Differences above ``monitor_tolerance`` are counted and reported. Only a
    difference above ``fail_tolerance`` changes the verdict. These thresholds
    are planning-owned and codified in config/universe.yaml.
    """
    both = pd.DataFrame({"a": primary, "b": secondary}).dropna()
    if len(both) < 250:
        return {"overlap_days": len(both), "verdict": "insufficient overlap"}
    r = both.pct_change().dropna()
    diff = (r["a"] - r["b"]).abs()
    monitored = diff[diff > monitor_tolerance]
    failed = diff[diff > fail_tolerance]

    return {
        "overlap_days": len(both),
        "median_abs_ret_diff": float(diff.median()),
        "max_abs_ret_diff": float(diff.max()),
        "monitor_tolerance": monitor_tolerance,
        "n_days_gt_monitor": int(len(monitored)),
        "frac_days_gt_monitor": float(len(monitored) / len(diff)),
        "fail_tolerance": fail_tolerance,
        "n_days_gt_fail": int(len(failed)),
        "frac_days_gt_fail": float(len(failed) / len(diff)),
        "worst_dates": [
            {"date": str(cast(pd.Timestamp, d).date()), "abs_ret_diff": round(float(v), 6)}
            for d, v in monitored.sort_values(ascending=False).head(5).items()
        ],
        "verdict": "ok" if len(failed) == 0 else "INVESTIGATE",
    }


NO_SECOND_SOURCE = {
    "verdict": "NO SECOND SOURCE",
    "detail": "see journal 2026-09-01 (Stooq blocked)",
}


def _rebase_secondary_adj_close(
    primary: pd.DataFrame,
    secondary: pd.DataFrame,
    date: pd.Timestamp,
) -> tuple[float, float]:
    """Return a secondary adjusted close expressed on the primary's level basis.

    Adjusted-price providers can represent the same return history at different
    level epochs. A sourced replacement therefore uses Tiingo's adjusted return
    path but is scaled to Yahoo's nearby overlapping levels.
    """
    common = primary.index.intersection(secondary.index)
    ratios = primary.loc[common, "adj_close"] / secondary.loc[common, "adj_close"]
    nearby = ratios.loc[date - pd.Timedelta(days=31):date + pd.Timedelta(days=31)].dropna()
    usable = nearby if len(nearby) else ratios.dropna()
    if usable.empty:
        raise ValueError(f"cannot rebase cross-check adjusted close for {date.date()}")
    scale = float(usable.median())
    secondary_adj_close = float(cast(float, secondary.at[date, "adj_close"]))
    return secondary_adj_close * scale, scale


# ---------------------------------------------------------------- ingest

@dataclass
class IngestResult:
    ticker: str
    frame: pd.DataFrame
    provenance: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return (
            self.provenance.get("adjustment", {}).get("verdict") == "ok"
            and self.provenance.get("crosscheck", {}).get("verdict")
            in {"ok", "NO SECOND SOURCE"}
        )


def ingest_ticker(ticker: str, start: str, store: Path,
                  crosscheck_source: str | None = None,
                  fail_tolerance: float = 0.02,
                  monitor_tolerance: float = 0.005) -> IngestResult:
    """Fetch one ticker from the primary source, check it, persist parquet.

    `crosscheck_source` names an INDEPENDENT provider in SOURCES; when it is
    None (the current state of the world) the cross-check is recorded as
    NO SECOND SOURCE rather than silently omitted.
    """
    from woodland.snapshot import refuse_pinned_write

    store = Path(store)
    refuse_pinned_write(store / f"{ticker}.parquet")
    store.mkdir(parents=True, exist_ok=True)

    primary = fetch_yahoo(ticker, start)
    primary = primary.loc[primary.index >= pd.Timestamp(start)]
    frame = primary.copy()
    backfilled_bars: list[dict[str, str]] = []

    if crosscheck_source is None:
        crosscheck = dict(NO_SECOND_SOURCE)
    else:
        try:
            second = SOURCES[crosscheck_source](ticker, start)
            crosscheck = crosscheck_sources(
                primary["adj_close"], second["adj_close"],
                fail_tolerance=fail_tolerance,
                monitor_tolerance=monitor_tolerance,
            )
            for date in sorted(APPROVED_CROSSCHECK_BACKFILLS):
                if date not in primary.index and date in second.index:
                    frame.loc[date, OHLCV] = second.loc[date, OHLCV]
                    rebased_adj_close, scale = _rebase_secondary_adj_close(primary, second, date)
                    frame.at[date, "adj_close"] = rebased_adj_close
                    backfilled_bars.append({
                        "date": str(date.date()),
                        "source": crosscheck_source,
                        "reason": "primary missing; planning-approved confirmed trading day",
                        "adj_close_scale_to_primary": f"{scale:.12g}",
                    })
            frame = frame.sort_index()
        except Exception as e:
            log.warning("cross-check source %s failed for %s: %s", crosscheck_source, ticker, e)
            crosscheck = {"verdict": "SOURCE UNAVAILABLE", "error": str(e)}

    prov = {
        "primary_source": "yahoo",
        "rows": int(len(frame)),
        "first": str(frame.index[0].date()) if len(frame) else None,
        "last": str(frame.index[-1].date()) if len(frame) else None,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "adjustment": check_adjustment(frame),
        "crosscheck_source": crosscheck_source,
        "crosscheck": crosscheck,
        "backfilled_bars": backfilled_bars,
    }

    frame.to_parquet(store / f"{ticker}.parquet")
    return IngestResult(ticker=ticker, frame=frame, provenance=prov)


def write_provenance(records: dict[str, dict], store: Path) -> Path:
    """Persist per-ticker provenance beside the parquet store."""
    path = Path(store) / PROVENANCE_FILE
    path.write_text(json.dumps(records, indent=2, sort_keys=True))
    return path


def read_provenance(store: Path) -> dict:
    path = Path(store) / PROVENANCE_FILE
    return json.loads(path.read_text()) if path.exists() else {}


def load_ticker(ticker: str, store: Path) -> pd.DataFrame:
    return pd.read_parquet(Path(store) / f"{ticker}.parquet")


def build_matrix(tickers: list[str], store: Path, field: str = "adj_close",
                 *, research: bool = True) -> pd.DataFrame:
    """Date x ticker matrix of one field from the per-ticker parquet files."""
    if research:
        from woodland.snapshot import verify_research_store

        verify_research_store(store)
    cols = {t: load_ticker(t, store)[field] for t in tickers}
    frame = pd.DataFrame(cols).sort_index()
    if research:
        from woodland.snapshot import bound_frame
        frame = bound_frame(frame)
    return frame


# ---------------------------------------------------------------- integrity

def _alive_mask(prices: pd.DataFrame) -> pd.DataFrame:
    """True where a ticker is between its first and last observed bar."""
    cols = {}
    for t in prices.columns:
        first, last = prices[t].first_valid_index(), prices[t].last_valid_index()
        cols[t] = (pd.Series(False, index=prices.index) if first is None
                   else (prices.index >= first) & (prices.index <= last))
    return pd.DataFrame(cols, index=prices.index)


def calendar_report(prices: pd.DataFrame, min_coverage: float = 0.8) -> pd.DataFrame:
    """Cross-sectional calendar check: find dates only SOME live tickers report.

    A universe of liquid US ETFs shares one exchange calendar, so on any real
    trading day essentially every ticker that exists yet must print a bar. A
    date where only a minority report is a hole in the feed, not a market
    event — and it is invisible to a per-ticker gap check, because one absent
    weekday inside a normal week produces a gap no longer than a holiday
    weekend.

    This is the strongest integrity check available WITHOUT a second source:
    the tickers cross-check each other's calendar. It still cannot detect a
    wrong price on a day everyone reports.

    Returns one row per suspect date (empty frame when the calendar is clean).
    """
    alive = _alive_mask(prices)
    n_alive = alive.sum(axis=1)
    n_present = (prices.notna() & alive).sum(axis=1)
    coverage = n_present / n_alive.where(n_alive > 0)
    suspect = coverage.notna() & (coverage < min_coverage)
    if not suspect.any():
        return pd.DataFrame(columns=["n_alive", "n_present", "coverage", "missing"])
    rows: list[dict[str, object]] = []
    for d in prices.index[suspect]:
        absent = [t for t in prices.columns if alive.at[d, t] and pd.isna(prices.at[d, t])]
        rows.append({
            "date": d.date(),
            "n_alive": int(n_alive[d]),
            "n_present": int(n_present[d]),
            "coverage": round(float(coverage[d]), 3),
            "missing": ",".join(absent),
        })
    return pd.DataFrame(rows).set_index("date")


def missing_bars(prices: pd.DataFrame, min_coverage: float = 0.8) -> pd.Series:
    """Per-ticker count of absent bars on days the rest of the universe traded."""
    alive = _alive_mask(prices)
    n_alive = alive.sum(axis=1)
    coverage = (prices.notna() & alive).sum(axis=1) / n_alive.where(n_alive > 0)
    consensus = (coverage >= min_coverage).to_numpy()
    return (alive & prices.isna()).loc[consensus].sum()


def drop_suspect_dates(prices: pd.DataFrame,
                       min_coverage: float = 0.8) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Drop dates the calendar check flags, returning (clean_prices, dropped).

    Excluding a bar the feed did not deliver is honest; forward-filling one is
    not — a fabricated price produces a fabricated return, and the backtest
    would trade on it. Dropping means the following day's return spans two
    sessions, which is a visible, bounded distortion rather than an invented
    observation.

    The parquet store is never modified: this operates on the derived matrix,
    per the raw-data-immutable rule (DESIGN.md §4).
    """
    suspect = calendar_report(prices, min_coverage=min_coverage)
    dropped = pd.DatetimeIndex([pd.Timestamp(d) for d in suspect.index])
    return prices.drop(index=dropped, errors="ignore"), dropped


def integrity_report(prices: pd.DataFrame, min_years: float = 3.0) -> pd.DataFrame:
    """Per-ticker data-quality report for an adj_close matrix. Flags, not fixes."""
    holes = missing_bars(prices)
    last_dates = prices.apply(lambda series: series.last_valid_index())
    observed_last_dates = last_dates.dropna()
    # The modal terminal bar is robust to one failed mid-ingest fetch leaving
    # its previous parquet in place.  If modes tie, report every tied date
    # rather than inventing a consensus that the store does not have.
    consensus_dates = observed_last_dates.mode().sort_values()
    consensus = ",".join(str(date.date()) for date in consensus_dates)
    rows: list[dict[str, object]] = []
    for t in prices.columns:
        s = prices[t].dropna()
        if s.empty:
            rows.append({
                "ticker": t,
                "last_bar_consensus": consensus,
                "freshness": "NO DATA",
                "flag": "NO DATA",
            })
            continue
        r = s.pct_change().dropna()
        gaps = s.index.to_series().diff().dt.days
        is_fresh = s.index[-1] in set(consensus_dates)
        rows.append({
            "ticker": t,
            "first": s.index[0].date(),
            "last": s.index[-1].date(),
            "last_bar_consensus": consensus,
            "freshness": "CURRENT" if is_fresh else "STALE VS CONSENSUS",
            "years": round((s.index[-1] - s.index[0]).days / 365.25, 1),
            "n_nonpositive": int((s <= 0).sum()),
            "max_gap_days": int(gaps.max()) if len(gaps) else 0,
            "n_moves_gt_20pct": int((r.abs() > 0.20).sum()),
            "n_missing_bars": int(holes.get(t, 0)),
            "flag": " | ".join(filter(None, [
                "SHORT HISTORY" if (s.index[-1] - s.index[0]).days / 365.25 < min_years else "",
                "MISSING BARS" if holes.get(t, 0) else "",
                "NONPOSITIVE PRICES" if (s <= 0).any() else "",
                "GAP>7D" if len(gaps) and gaps.max() > 7 else "",
                "JUMPS" if (r.abs() > 0.20).any() else "",
            ])) or "ok",
        })
    return pd.DataFrame(rows).set_index("ticker")
