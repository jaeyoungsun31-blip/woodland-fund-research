"""Shared study scaffolding: the constants and setup every runner repeats.

Before this module existed, `MAX_LOOKBACK_DAYS = 210` appeared in ten study
scripts, the nine-sector list in seven, and `stitch()` was defined eleven
times. That is not merely untidy — a study whose universe silently disagreed
with its predecessor's would still run, still print, and still be journalled,
and nothing would catch it. Centralising the constants makes divergence a
test failure instead of a discrepancy nobody notices.

Two rules this module follows:

**One source of truth, including across modules.** Where `woodland.pipeline`
already owns a constant, this module re-exports it rather than restating the
value. There is exactly one place each number lives.

**Names carry meaning, not just a value.** `VOL_TARGET_WINDOW` (63 bars, the
realised-volatility window for exposure scaling) and `RISK_COV_WINDOW` (126
bars, the covariance window for risk-based sizing) were both spelled
`VOL_WINDOW` in different scripts with different values. They are different
quantities and now have different names, so a future reader cannot conflate
them and a test can tell them apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from woodland import cash, data
from woodland.config import ROOT, all_tickers, load_config
from woodland.fama_french import INDUSTRIES
from woodland.harness import splits as sp
from woodland.pipeline import (
    DEFAULT_LOOKBACKS,
    REALIZED_VOL_WINDOW,
    SIZING_WINDOW,
    TARGET_ANN_VOL,
)

# --------------------------------------------------------------- universes

SECTORS: list[str] = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
MULTI_ASSET: list[str] = ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD"]
MULTI_ASSET_DBC: list[str] = [*MULTI_ASSET, "DBC"]
DEEP_INDUSTRIES: list[str] = list(INDUSTRIES)

ETF_RISK_OFF = "IEF"
DEEP_RISK_OFF = "CASH"
DEEP_MARKET = "MKT"

# --------------------------------------------------------------- signal

# Re-exported from woodland.pipeline so the value lives in exactly one place.
LOOKBACKS: list[int] = list(DEFAULT_LOOKBACKS)
VOL_TARGET_WINDOW: int = REALIZED_VOL_WINDOW      # 63 bars, exposure scaling
VOL_TARGET_ANN: float = TARGET_ANN_VOL            # 10% annualised target
RISK_COV_WINDOW: int = SIZING_WINDOW              # 126 bars, covariance sizing

# --------------------------------------------------------------- scheme

TRAIN_YEARS = 5
VALIDATE_YEARS = 1
STEP_YEARS = 1
MAX_LOOKBACK_DAYS = 210          # 10 months; equals the embargo by construction
XSMOM_EMBARGO_DAYS = 252         # amended for the momentum studies (v10 onward)

COSTS: tuple[float, ...] = (0.0, 5.0, 10.0)
PRIMARY_COST = 5.0

# Frozen realisations of the pre-registered scheme. A change here means the
# data or the scheme moved, and every journalled number is then suspect.
ETF_EXPECTED_BARS = 5_502  # snapshot amendment 2026-09-07; old 5499 superseded
ETF_EXPECTED_FOLDS = 22
DEEP_EXPECTED_BARS = 24_579
DEEP_EXPECTED_FOLDS = 95


# Names this module is the single source of truth for. A study script that
# assigns any of these its own value is redefining a shared decision locally,
# which is what let ten scripts drift apart; tests/test_no_constant_duplication
# turns that into a test failure. A script needing a genuine variant should
# give it a DIFFERENT name (see EXECUTION_COSTS in the v12 runner), so the
# divergence is visible rather than disguised as agreement.
OWNED_CONSTANTS: frozenset[str] = frozenset({
    "SECTORS", "MULTI_ASSET", "MULTI_ASSET_DBC", "DEEP_INDUSTRIES",
    "ETF_RISK_OFF", "DEEP_RISK_OFF", "DEEP_MARKET",
    "LOOKBACKS", "VOL_TARGET_WINDOW", "VOL_TARGET_ANN", "RISK_COV_WINDOW",
    "TRAIN_YEARS", "VALIDATE_YEARS", "STEP_YEARS",
    "MAX_LOOKBACK_DAYS", "XSMOM_EMBARGO_DAYS",
    "COSTS", "PRIMARY_COST",
    "ETF_EXPECTED_BARS", "ETF_EXPECTED_FOLDS",
    "DEEP_EXPECTED_BARS", "DEEP_EXPECTED_FOLDS",
})


@dataclass(frozen=True)
class StudyContext:
    """A universe, its frozen walk-forward folds, and its OOS window."""

    name: str
    prices: pd.DataFrame
    folds: list[sp.Split]
    lo: pd.Timestamp
    hi: pd.Timestamp
    risk_free: pd.Series | None
    n_bars: int

    @property
    def index(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.prices.index)


def oos_window(
    index: pd.DatetimeIndex, folds: list[sp.Split]
) -> tuple[pd.Timestamp, pd.Timestamp, int]:
    """First bar, last bar, and total bar count across all validate windows."""
    windows = [f.validate_index(index) for f in folds]
    live = [w for w in windows if len(w)]
    if not live:
        raise ValueError("no validate window contains any bar")
    return live[0][0], live[-1][-1], sum(len(w) for w in live)


def stitch(prices: pd.DataFrame, targets: pd.DataFrame, folds: list[sp.Split]) -> pd.DataFrame:
    """Keep only the target rows falling inside a validate window.

    This is the operation that makes an out-of-sample curve out of a
    full-history target stream, and it was previously copied into eleven
    scripts.
    """
    index = pd.DatetimeIndex(prices.index)
    stitched = pd.DataFrame(float("nan"), index=prices.index, columns=prices.columns)
    for split in folds:
        window = split.validate_index(index)
        if not len(window):
            continue
        rows = targets.loc[window[0]:window[-1]].dropna(how="all")
        stitched.loc[rows.index] = rows
    return stitched


def stitch_targets(targets: pd.DataFrame, folds: list[sp.Split]) -> pd.DataFrame:
    """`stitch` for callers whose targets already span the full price grid.

    Identical semantics; it simply takes the axes from the targets rather than
    from a separate price frame.
    """
    return stitch(targets, targets, folds)


def make_folds(index: pd.DatetimeIndex, embargo_days: int = MAX_LOOKBACK_DAYS) -> list[sp.Split]:
    """The frozen walk-forward scheme, with the embargo checked against itself."""
    folds = sp.make_splits(index, train_years=TRAIN_YEARS, validate_years=VALIDATE_YEARS,
                           step_years=STEP_YEARS, embargo_days=embargo_days)
    sp.check_embargo_covers_lookback(folds, index, MAX_LOOKBACK_DAYS)
    return folds


@lru_cache(maxsize=4)
def etf_context(embargo_days: int = MAX_LOOKBACK_DAYS, with_risk_free: bool = True) -> StudyContext:
    """The tradeable ETF universe on the frozen scheme."""
    cfg = load_config()
    store = ROOT / cfg["data"]["store"]
    prices, _ = data.drop_suspect_dates(data.build_matrix(all_tickers(cfg), store))
    index = pd.DatetimeIndex(prices.index)
    folds = make_folds(index, embargo_days)
    lo, hi, n_bars = oos_window(index, folds)
    rf = None
    if with_risk_free:
        rf, _ = cash.align_risk_free(cash.load_risk_free_daily(store), index)
    return StudyContext("etf", prices, folds, lo, hi, rf, n_bars)


@lru_cache(maxsize=4)
def deep_context(embargo_days: int = MAX_LOOKBACK_DAYS) -> StudyContext:
    """The 1926- Fama-French industry universe, with MKT and CASH joined."""
    store = ROOT / "data"
    industries = pd.read_parquet(store / "fama_french_12_industry_daily.parquet")
    factors = pd.read_parquet(store / "fama_french_factors_daily.parquet")
    if not industries.index.equals(factors.index):
        raise ValueError("industry and factor calendars differ; re-run the FF ingest")
    prices = industries.join(factors, how="inner")
    if prices.isna().any().any():
        raise ValueError("deep-history matrix has missing values")
    index = pd.DatetimeIndex(prices.index)
    folds = make_folds(index, embargo_days)
    lo, hi, n_bars = oos_window(index, folds)
    return StudyContext("deep", prices, folds, lo, hi, None, n_bars)


def check_realisation(context: StudyContext) -> None:
    """Fail loudly if the scheme no longer realises its journalled shape."""
    expected = {
        "etf": (ETF_EXPECTED_BARS, ETF_EXPECTED_FOLDS),
        "deep": (DEEP_EXPECTED_BARS, DEEP_EXPECTED_FOLDS),
    }.get(context.name)
    if expected is None:
        return
    bars, folds = expected
    if context.n_bars != bars or len(context.folds) != folds:
        raise ValueError(
            f"{context.name} universe realises {context.n_bars} bars / "
            f"{len(context.folds)} folds, journalled {bars} / {folds}. Every "
            "journalled number on this universe is suspect until this is explained."
        )


def data_store() -> Path:
    return Path(ROOT) / str(load_config()["data"]["store"])


# --------------------------------------------------------------- reporting


def summary_table(
    named: dict[str, pd.Series],
    rf_daily: pd.Series | None = None,
    turnovers: dict[str, pd.Series] | None = None,
) -> pd.DataFrame:
    """The standard side-by-side table every study prints.

    Binding rule 5 requires results beside their baselines rather than alone,
    so this takes a mapping and never a single series.
    """
    from woodland import metrics

    table = metrics.compare(named, rf_daily=rf_daily)
    if turnovers:
        table["ann_turnover"] = pd.Series(
            {k: metrics.ann_turnover(v) for k, v in turnovers.items()}
        )
    return table


def cost_labelled(prefix: str, by_cost: dict[float, pd.Series]) -> dict[str, pd.Series]:
    """Label a series at each cost the way the journal entries do."""
    return {f"{prefix} @{int(cost)}bps": series for cost, series in sorted(by_cost.items())}
