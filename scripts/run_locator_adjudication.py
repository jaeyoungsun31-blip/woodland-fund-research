"""Re-scoped duplicate-locator census, and per-pair adjudication of survivors.

Two corrections to the first census, both from planning:

1. The 5% gate threshold is withdrawn. Nothing here gates on a fraction; the
   count is reported and the decision belongs to planning.
2. A contender counts only if it is **date-eligible for the same membership
   window** — its bounds contain that window — and the two imply different
   returns **within that window**. The first census measured divergence over
   the full overlap, which conflates two different things: a genuine contention
   inside the window a constituent was actually held, and a lineage succession
   whose two files describe different eras of the same entity.

The adjusted-ratio-range metric is unchanged and stays: exact agreement on the
adjusted *level* is degenerate, since each file's factor reaches 1.0 at its own
last bar.

Candidate generation is NOT redone. It is unchanged from
`run_duplicate_locator_census.py` — exact (date, close) token co-occurrence,
qualified on >=90% loose close agreement — and this script re-scopes the 93
pairs that survived it. The lower-bound caveat therefore carries over: a
contender whose prices are uniformly rescaled shares no exact token and is
invisible to the search that produced these pairs.

For each surviving contention the script then asks which of the two files is
wrong, because identical raw prices cannot imply incompatible returns unless
one adjusted series is defective. Evidence, in order of strength:

* `check_adjustment`'s monotonicity condition (`woodland/data.py`) — adj/close
  is a cumulative dividend factor and must be non-decreasing through time. A
  file that violates it is defective on the store's own stated rule.
* Tiingo, the project's independent keyed cross-check, compared on aligned
  daily adjusted RETURNS, never on rebased levels.

Read-only. Builds no panel, changes no price, applies nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Membership rows are one per constituent-year. Consecutive years are one
# window; a real absence from the index is a genuine gap and is kept as one.
MEMBERSHIP_JOIN_DAYS = 10

# Date-eligibility is a hard boundary, so it is tested at the boundary: a
# contender short of the window by no more than this is measured anyway and
# reported separately, because excluding a large contention on a one-day
# technicality would be an artefact of the rule rather than a finding.
NEAR_MISS_DAYS = 5

# Planning widened the eligibility boundary after CTX/CTX1 was excluded by a
# single day and measured +56.48pp. The tolerance is in TRADING days, counted
# on the resolved file's own bar index, because a calendar-day tolerance means
# a different number of observations over a holiday than over a mid-week gap.
DEFAULT_TOLERANCE_BARS = 0

# adjusted_close is stored to four decimals, so the ratio adj_a/adj_b carries a
# quantisation floor that is LARGER for low-priced series. WINMQ bottoms at
# 0.0420, where half a tick is 1.2e-3 relative - above the 1.001 tolerance the
# first census used. Every ratio range is therefore reported against its own
# rounding floor rather than against one global constant.
ADJUSTED_QUANTUM = 1e-4
RATIO_RANGE_TOLERANCE = 1.001

# check_adjustment's own tolerance, applied unchanged.
MONOTONICITY_ABS_TOL = 1e-4

# A ratio step this far beyond the day's rounding bound is a discrete event in
# one file and not jitter in both.
STEP_SIGMA = 5.0
MIN_STEP_REL = 5e-4

TIINGO_RETURN_TOL = 2e-4     # daily return agreement, absolute
TIINGO_MIN_BARS = 60
SAME_ENTITY_CLOSE_RTOL = 1e-3   # as in the census, reused to qualify the third source
TIINGO_MIN_ENTITY_MATCH = 0.90  # below this, the ticker resolves to a different company
TIINGO_DECISIVE_MARGIN = 0.02   # separation required to adjudicate on Tiingo
TIINGO_CORROBORATION = 0.95     # a file this close to Tiingo corroborates against its pair


def membership_intervals(rows: list[dict[str, Any]]) -> dict[str, list[tuple[str, str]]]:
    """Merge per-year membership rows into contiguous windows per locator."""
    by_locator: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in rows:
        by_locator[row["price_symbol"]].append((row["start"], row["end"]))
    out: dict[str, list[tuple[str, str]]] = {}
    for locator, spans in by_locator.items():
        ordered = sorted(spans)
        merged = [list(ordered[0])]
        for start, end in ordered[1:]:
            previous = date.fromisoformat(merged[-1][1])
            if date.fromisoformat(start) - previous <= timedelta(days=MEMBERSHIP_JOIN_DAYS):
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        out[locator] = [(s, e) for s, e in merged]
    return out


def tolerant_bounds(
    frame: pd.DataFrame, start: str, end: str, bars: int
) -> tuple[str, str]:
    """Shrink a membership window by `bars` trading days at each end.

    Counted on the resolved file's own dates, so "five trading days" means five
    observations the panel would actually have used, not five calendar days
    that might span a holiday weekend.
    """
    if bars <= 0:
        return start, end
    dates = pd.DatetimeIndex(frame["date"])
    inside = dates[(dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))]
    if len(inside) <= 2 * bars:
        return start, end
    return str(inside[bars].date()), str(inside[-1 - bars].date())


def load_frame(store: Path, symbol: str) -> pd.DataFrame:
    frame = pd.read_parquet(
        store / f"{symbol}.US.parquet",
        columns=["date", "close", "adjusted_close"],
    )
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.sort_values("date")


def window_mask(dates: pd.Series, intervals: list[tuple[str, str]]) -> np.ndarray:
    mask = np.zeros(len(dates), bool)
    for start, end in intervals:
        mask |= ((dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))).to_numpy()
    return mask


def measure_in_window(
    store: Path, left: str, right: str, intervals: list[tuple[str, str]]
) -> dict[str, Any]:
    """Agreement and return divergence restricted to the membership window."""
    merged = load_frame(store, left).merge(
        load_frame(store, right), on="date", suffixes=("_a", "_b")
    ).sort_values("date")
    merged = merged[window_mask(merged["date"], intervals)]
    out: dict[str, Any] = {"window_bars": int(len(merged))}
    if len(merged) < 3:
        return out
    close_a = merged["close_a"].to_numpy(float)
    close_b = merged["close_b"].to_numpy(float)
    adj_a = merged["adjusted_close_a"].to_numpy(float)
    adj_b = merged["adjusted_close_b"].to_numpy(float)
    good = np.isfinite(adj_a) & np.isfinite(adj_b) & (adj_a > 0) & (adj_b > 0)
    if good.sum() < 3:
        return out
    valid_close = np.isfinite(close_a) & np.isfinite(close_b)
    out["window_close_agreement"] = float(
        np.isclose(close_a[valid_close], close_b[valid_close], rtol=1e-6, atol=0).mean()
    )
    dates = merged["date"].to_numpy()[good]
    ratio = adj_a[good] / adj_b[good]
    out["window_ratio_range"] = float(ratio.max() / ratio.min())

    # Quantisation floor: half a tick on each series, at its in-window minimum.
    half = ADJUSTED_QUANTUM / 2.0
    epsilon = half / adj_a[good].min() + half / adj_b[good].min()
    out["rounding_floor"] = float((1 + epsilon) / (1 - epsilon)) if epsilon < 1 else None
    out["exceeds_rounding_floor"] = bool(
        out["rounding_floor"] is not None
        and out["window_ratio_range"] > out["rounding_floor"]
    )

    out["window_total_return_a"] = float(adj_a[good][-1] / adj_a[good][0] - 1.0)
    out["window_total_return_b"] = float(adj_b[good][-1] / adj_b[good][0] - 1.0)
    out["window_total_return_gap"] = float(
        out["window_total_return_a"] - out["window_total_return_b"])

    returns_a = np.diff(adj_a[good]) / adj_a[good][:-1]
    returns_b = np.diff(adj_b[good]) / adj_b[good][:-1]
    fine = np.isfinite(returns_a) & np.isfinite(returns_b)
    out["window_return_correlation"] = (
        float(np.corrcoef(returns_a[fine], returns_b[fine])[0, 1])
        if fine.sum() > 2 and returns_a[fine].std() > 0 and returns_b[fine].std() > 0
        else None
    )

    # Discrete steps in the ratio: where one file applied an event the other did
    # not. Compared against each day's own rounding bound, not a fixed constant.
    step = ratio[1:] / ratio[:-1]
    bound = half / np.minimum(adj_a[good][1:], adj_a[good][:-1]) + \
        half / np.minimum(adj_b[good][1:], adj_b[good][:-1])
    excess = np.abs(step - 1.0) - STEP_SIGMA * bound
    material = (excess > 0) & (np.abs(step - 1.0) > MIN_STEP_REL)
    out["ratio_steps"] = int(material.sum())
    if material.any():
        order = np.argsort(-np.abs(step - 1.0))
        top = [i for i in order if material[i]][:3]
        out["largest_step_date"] = str(pd.Timestamp(dates[top[0] + 1]).date())
        out["largest_step_factor"] = float(step[top[0]])
        out["step_dates"] = ";".join(str(pd.Timestamp(dates[i + 1]).date()) for i in top)
    return out


def factor_diagnostics(
    store: Path, symbol: str, intervals: list[tuple[str, str]]
) -> dict[str, Any]:
    """check_adjustment's monotonicity condition, whole-file and in-window.

    `woodland.data.check_adjustment` flags an ABSOLUTE drop below -1e-4 in
    adj_close/close. That threshold is absolute on a quantity that spans 0.05
    to 1.0, so a proportionally large violation early in a long file can pass.
    The relative counterpart is reported beside it; only the absolute one is
    the store's stated rule.
    """
    frame = load_frame(store, symbol).dropna(subset=["close", "adjusted_close"])
    frame = frame[(frame["close"] > 0) & (frame["adjusted_close"] > 0)]
    factor = (frame["adjusted_close"] / frame["close"]).to_numpy(float)
    dates = frame["date"].to_numpy()
    out: dict[str, Any] = {"bars": int(len(frame))}
    if len(factor) < 2:
        return out
    absolute = np.diff(factor)
    relative = absolute / factor[:-1]
    out["worst_factor_drop"] = float(absolute.min())
    out["worst_factor_drop_relative"] = float(relative.min())
    out["terminal_factor"] = float(factor[-1])
    out["monotonicity_violation"] = bool(absolute.min() < -MONOTONICITY_ABS_TOL)
    if out["monotonicity_violation"]:
        out["worst_drop_date"] = str(pd.Timestamp(dates[int(absolute.argmin()) + 1]).date())
    inside = window_mask(frame["date"], intervals)[1:]
    if inside.any():
        out["worst_factor_drop_in_window"] = float(absolute[inside].min())
        out["monotonicity_violation_in_window"] = bool(
            absolute[inside].min() < -MONOTONICITY_ABS_TOL
        )
        worst = int(np.argmin(np.where(inside, absolute, np.inf)))
        if out["monotonicity_violation_in_window"]:
            out["worst_drop_date_in_window"] = str(
                pd.Timestamp(dates[worst + 1]).date()
            )
    return out


# Only a definite "this ticker does not exist" may be cached as an absence.
# Everything else is transient and must never become a finding.
#
# This is deliberately inverted. The first version listed throttle phrases and
# treated anything else as a missing ticker, which failed twice: the vendor
# signals a cap in prose ("You have run over your hourly request allocation")
# AND as JSON ('{"detail": "You have run over your 50 ..."}'), and the second
# form matched no phrase in the list, so 470 throttled symbols were cached as
# "no Tiingo series" - among them BK, EQR, GPS, ULTA and AAL, which the vendor
# plainly carries. Enumerating the ways a vendor can say "no" is a losing game;
# enumerating the one way it says "this ticker is not real" is not.
ABSENCE_MARKERS = ("not found", "has no series for")


class TiingoThrottled(RuntimeError):
    """The vendor rate-limited us. Not evidence about any file."""


def tiingo_ticker_candidates(locator: str, contender: str) -> list[str]:
    """Tickers to try for one entity, most specific first.

    Store symbols carry local suffixes - `CCE_old` is our name for a second
    file, `IGT1` for a duplicate - that no vendor knows. The base ticker is
    tried after the literal one. Both files of a pair describe one entity, so
    one Tiingo series is the right reference for both.
    """
    out: list[str] = []
    for symbol in (locator, contender):
        for form in (symbol, re.sub(r"(_old\d*|\d+)$", "", symbol)):
            if form and form not in out:
                out.append(form)
    return out


def tiingo_series(symbol: str, start: str, cache: Path) -> pd.DataFrame | None:
    """Adjusted daily returns AND raw close from Tiingo, cached.

    Close is carried because a ticker is not an identity. Tickers are recycled:
    Tiingo's `WIN` is a company first listed 2023-12-01 trading near $16.50,
    not the Windstream that was delisted in 2020, and `NVLS` likewise resolves
    to something other than the Novellus acquired in 2012. Comparing our files
    against a recycled ticker would be the same error as accepting a token
    collision as a duplicate, so the entity is verified on price before any
    Tiingo number is used as evidence.

    Returns, never levels, for the comparison itself: the two vendors normalise
    the adjusted series to different terminal bars.
    """
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"tiingo-{symbol}-{start}.csv"
    if path.exists():
        if path.stat().st_size == 0:
            return None
        frame = pd.read_csv(path, parse_dates=["date"])
    else:
        from woodland.data import fetch_tiingo
        try:
            raw = fetch_tiingo(symbol, start)
        except Exception as exc:  # noqa: BLE001 - reachability is the measurement
            message = str(exc)
            print(f"    tiingo {symbol}: {type(exc).__name__}: {message[:70]}")
            if not any(mark in message.lower() for mark in ABSENCE_MARKERS):
                raise TiingoThrottled(symbol) from exc
            path.write_text("")
            return None
        finally:
            time.sleep(0.4)
        frame = raw.reset_index()[["Date", "close", "adj_close"]].rename(
            columns={"Date": "date"})
        frame.to_csv(path, index=False)
    frame = frame.dropna().sort_values("date")
    if len(frame) < TIINGO_MIN_BARS:
        return None
    out = pd.DataFrame(
        {"close": frame["close"].to_numpy(float),
         "adj_close": frame["adj_close"].to_numpy(float),
         "ret": pd.Series(frame["adj_close"].to_numpy(float)).pct_change().to_numpy()},
        index=pd.DatetimeIndex(frame["date"]),
    )
    return out.iloc[1:]


def tiingo_is_same_entity(
    store: Path, symbol: str, intervals: list[tuple[str, str]], reference: pd.DataFrame
) -> float | None:
    """Fraction of in-window days where Tiingo's raw close matches the file's."""
    frame = load_frame(store, symbol).dropna(subset=["close"])
    frame = frame[frame["close"] > 0]
    ours = pd.Series(frame["close"].to_numpy(float), index=pd.DatetimeIndex(frame["date"]))
    ours = ours[window_mask(pd.Series(ours.index), intervals)]
    joined = ours.to_frame("ours").join(reference["close"].rename("them"), how="inner")
    joined = joined.dropna()
    if len(joined) < TIINGO_MIN_BARS:
        return None
    return float(np.isclose(joined["ours"], joined["them"],
                            rtol=SAME_ENTITY_CLOSE_RTOL, atol=0).mean())


def tiingo_agreement(
    store: Path, symbol: str, intervals: list[tuple[str, str]], reference: pd.Series
) -> dict[str, Any] | None:  # reference is the 'ret' column
    """Fraction of in-window days where a file's adjusted return matches Tiingo."""
    frame = load_frame(store, symbol).dropna(subset=["adjusted_close"])
    frame = frame[frame["adjusted_close"] > 0]
    series = pd.Series(frame["adjusted_close"].to_numpy(float), index=frame["date"])
    ours = series.pct_change().dropna()
    inside = ours[window_mask(pd.Series(ours.index), intervals)]
    joined = inside.to_frame("ours").join(reference.rename("them"), how="inner").dropna()
    if len(joined) < TIINGO_MIN_BARS:
        return None
    close = np.isclose(joined["ours"], joined["them"], rtol=0, atol=TIINGO_RETURN_TOL)
    return {
        "bars": int(len(joined)),
        "agreement": float(close.mean()),
        "worst_abs_difference": float((joined["ours"] - joined["them"]).abs().max()),
    }


MAX_STEPS_TESTED = 5
STEP_MATCH_ATOL = 2e-3


def adjusted_returns(store: Path, symbol: str) -> pd.Series:
    frame = load_frame(store, symbol).dropna(subset=["adjusted_close"])
    frame = frame[frame["adjusted_close"] > 0]
    series = pd.Series(frame["adjusted_close"].to_numpy(float), index=frame["date"])
    return series.pct_change().dropna()


SPLIT_SIZED = 0.15
NEGATIVE_DISTRIBUTION = 1e-3   # a security cannot pay a negative dividend


def classify_disagreement(store: Path, pair: dict[str, Any]) -> dict[str, Any]:
    """Separate an adjustment defect from a raw-price discrepancy.

    The brief's premise - identical prices cannot imply incompatible returns
    unless one adjusted series is wrong - holds only where the raw prices are
    in fact identical on the disagreeing day. They often are not: two files can
    agree on 99.9% of closes and still record a different close on the handful
    of days that produce the divergence, and then each file's adjusted return
    faithfully tracks its own raw return. That is a price defect, not an
    adjustment defect, and it needs a different fix.

    A day where the raw move is split-sized and one file's adjusted return
    simply follows it is decided here, with no third source: a two-for-one
    split is not a 48.6% loss.
    """
    dates = [d for d in str(pair.get("step_dates") or "").split(";") if d]
    if not dates:
        return {}
    frames = {}
    for symbol in (pair["locator"], pair["contender"]):
        frame = load_frame(store, symbol).set_index("date")
        frames[symbol] = frame
    adjustment, price, notes = 0, 0, []
    missed_event_by, impossible = "", ""
    implied_a: list[float] = []
    implied_b: list[float] = []
    for text in dates:
        stamp = pd.Timestamp(text)
        moves = {}
        for symbol, frame in frames.items():
            if stamp not in frame.index:
                break
            located = frame.index.get_loc(stamp)
            if not isinstance(located, int) or located == 0:
                break
            position = located
            moves[symbol] = (
                float(frame["close"].iloc[position] / frame["close"].iloc[position - 1] - 1),
                float(frame["adjusted_close"].iloc[position]
                      / frame["adjusted_close"].iloc[position - 1] - 1),
            )
        if len(moves) != 2:
            continue
        (raw_a, adj_a), (raw_b, adj_b) = moves[pair["locator"]], moves[pair["contender"]]
        if abs(adj_a - adj_b) < STEP_MATCH_ATOL:
            continue
        if abs(raw_a - raw_b) <= 1e-6 * max(1.0, abs(raw_a)):
            adjustment += 1
            # On a day both files record the same raw prices, the difference
            # between a file's adjusted and raw return is the cash distribution
            # it applied, as a fraction of the prior close. A NEGATIVE value is
            # not a distribution any security can pay, so it decides the pair
            # with no external source. The magnitude of a positive one is
            # evidence a reader can weigh, but identifying it against an actual
            # declared dividend needs a cited dividend history, which the store
            # does not carry.
            implied_a.append(adj_a - raw_a)
            implied_b.append(adj_b - raw_b)
            if adj_a - raw_a < -NEGATIVE_DISTRIBUTION and adj_b - raw_b >= 0:
                impossible = pair["locator"]
            elif adj_b - raw_b < -NEGATIVE_DISTRIBUTION and adj_a - raw_a >= 0:
                impossible = pair["contender"]
            if abs(raw_a) > SPLIT_SIZED:
                tracks = [name for name, (raw, adj) in
                          ((pair["locator"], (raw_a, adj_a)),
                           (pair["contender"], (raw_b, adj_b)))
                          if abs(adj - raw) < 1e-3]
                if len(tracks) == 1:
                    missed_event_by = tracks[0]
                    notes.append(f"{text}: raw {raw_a:+.4f} in both; {tracks[0]} carries it "
                                 f"into its adjusted series unchanged - a corporate action "
                                 f"of that size was not applied")
        else:
            price += 1
            notes.append(f"{text}: raw returns themselves differ "
                         f"({raw_a:+.4f} vs {raw_b:+.4f}) - a price discrepancy, "
                         f"not an adjustment one")
    out: dict[str, Any] = {
        "implied_distribution_locator": ";".join(f"{v:+.4f}" for v in implied_a),
        "implied_distribution_contender": ";".join(f"{v:+.4f}" for v in implied_b),
        "days_adjustment_only": adjustment,
        "days_raw_price_differs": price,
        "defect_class": ("adjustment" if adjustment and not price else
                         "raw_price" if price and not adjustment else
                         "mixed" if price and adjustment else "undetermined"),
        "classification_notes": " | ".join(notes[:4]),
    }
    if missed_event_by:
        out["missed_corporate_action_by"] = missed_event_by
    if impossible:
        out["negative_distribution_by"] = impossible
    return out


def step_evidence(
    store: Path, pair: dict[str, Any], reference: pd.Series | None
) -> dict[str, Any]:
    """Test the days the two files disagree, not the days they agree.

    Overall agreement rates cannot separate these files: the disagreements are
    a handful of discrete events among thousands of quiet days, so both files
    score ~0.98 against any third source. The step dates are where the question
    actually lives - on 2004-12-01 either Symantec split two-for-one or it did
    not, and Tiingo says which.
    """
    out: dict[str, Any] = {}
    dates = [d for d in str(pair.get("step_dates") or "").split(";") if d]
    if not dates or reference is None:
        return out
    left = adjusted_returns(store, pair["locator"])
    right = adjusted_returns(store, pair["contender"])
    lines, left_hits, right_hits, tested = [], 0, 0, 0
    for text in dates[:MAX_STEPS_TESTED]:
        stamp = pd.Timestamp(text)
        if stamp not in left.index or stamp not in right.index or stamp not in reference.index:
            continue
        a, b, t = float(left[stamp]), float(right[stamp]), float(reference[stamp])
        if abs(a - b) < STEP_MATCH_ATOL:
            continue
        tested += 1
        a_ok = abs(a - t) <= STEP_MATCH_ATOL
        b_ok = abs(b - t) <= STEP_MATCH_ATOL
        left_hits += int(a_ok and not b_ok)
        right_hits += int(b_ok and not a_ok)
        mark = "locator" if (a_ok and not b_ok) else (
            "contender" if (b_ok and not a_ok) else "neither")
        lines.append(f"{text}: {pair['locator']} {a:+.4f} / "
                     f"{pair['contender']} {b:+.4f} / tiingo {t:+.4f} -> {mark}")
    out["steps_present"] = len(dates)
    out["steps_tested"] = tested
    out["steps_matching_locator"] = left_hits
    out["steps_matching_contender"] = right_hits
    out["step_detail"] = " | ".join(lines)
    return out


def adjudicate(pair: dict[str, Any]) -> tuple[str, str, str, str]:
    """Which file the panel should use, which is defective, status, evidence.

    Evidence, strongest first:

    * Tiingo on the days the two files actually disagree. Overall agreement
      rates cannot separate these files - the disagreements are a handful of
      discrete events among thousands of quiet days, so both score ~0.98
      against any third source. The step dates are where the question lives.
    * `check_adjustment`'s monotonicity condition, IN-WINDOW. A violation
      elsewhere in the file says it is damaged somewhere, not that it is the
      wrong series here, so that is carried as context and never adjudicates.

    When the two disagree the pair is `conflicted`, never quietly decided. When
    each file wins some step dates, both are defective in different places and
    the pair is `both_defective`.
    """
    locator, contender = pair["locator"], pair["contender"]
    evidence: list[str] = []
    monotonic_verdict = ""

    left_bad = pair.get("locator_monotonicity_violation_in_window")
    right_bad = pair.get("contender_monotonicity_violation_in_window")
    if left_bad and not right_bad:
        monotonic_verdict = contender
        evidence.append(
            f"{locator} violates check_adjustment monotonicity in-window "
            f"({pair['locator_worst_factor_drop_in_window']:.3e} at "
            f"{pair.get('locator_worst_drop_date_in_window')})")
    elif right_bad and not left_bad:
        monotonic_verdict = locator
        evidence.append(
            f"{contender} violates check_adjustment monotonicity in-window "
            f"({pair['contender_worst_factor_drop_in_window']:.3e} at "
            f"{pair.get('contender_worst_drop_date_in_window')})")
    elif left_bad and right_bad:
        evidence.append("both files violate check_adjustment monotonicity in-window")
    else:
        evidence.append("neither file violates check_adjustment monotonicity in-window")
    for side, symbol in (("locator", locator), ("contender", contender)):
        if pair.get(f"{side}_monotonicity_violation") and not pair.get(
            f"{side}_monotonicity_violation_in_window"
        ):
            evidence.append(f"{symbol} violates it elsewhere in the file "
                            f"({pair.get(f'{side}_worst_drop_date')}), outside this window")

    missed = pair.get("missed_corporate_action_by")
    if missed:
        correct = contender if missed == locator else locator
        evidence.append(
            f"{missed} carries a split-sized raw move into its adjusted series "
            f"unchanged, on a day both files record the same raw prices; no third "
            f"source is needed to call that wrong")
        evidence.append(f"disagreeing days: {pair.get('days_adjustment_only')} adjustment-only, "
                        f"{pair.get('days_raw_price_differs')} with differing raw prices")
        return correct, missed, "resolved_on_store_internal_evidence", "; ".join(evidence)

    impossible = pair.get("negative_distribution_by")
    if impossible:
        correct = contender if impossible == locator else locator
        side = "locator" if impossible == locator else "contender"
        amounts = pair.get(f"implied_distribution_{side}")
        evidence.append(
            f"{impossible} implies a NEGATIVE cash distribution ({amounts} of the prior "
            f"close) on days both files record the same raw prices; no security pays a "
            f"negative dividend")
        return correct, impossible, "resolved_on_store_internal_evidence", "; ".join(evidence)

    ticker = pair.get("tiingo_ticker")
    tested = pair.get("steps_tested") or 0
    left_hits = pair.get("steps_matching_locator") or 0
    right_hits = pair.get("steps_matching_contender") or 0
    step_verdict, status = "", ""
    if tested:
        evidence.append(f"tiingo({ticker}) on {tested} disagreeing step date(s): "
                        f"{locator} {left_hits}, {contender} {right_hits}")
        if left_hits and right_hits:
            status = "both_defective"
            evidence.append("each file matches the independent source on days the other "
                            "misses, so both carry adjustment defects in this window")
        elif left_hits:
            step_verdict = locator
        elif right_hits:
            step_verdict = contender
        else:
            status = "third_source_matches_neither"
            evidence.append("tiingo matches NEITHER file on the disagreeing days")
    elif ticker is None:
        status = "tiingo_unreachable"
        if pair.get("tiingo_throttled"):
            return "undetermined", "", "tiingo_deferred", "; ".join(
                [*evidence, "the vendor rate-limited this lookup; not evidence about "
                            "either file - rerun to complete"])
        rejected = pair.get("tiingo_tickers_rejected")
        evidence.append(
            "tiingo has no series for this entity under either ticker"
            + (f"; rejected as a different company under a recycled ticker: {rejected}"
               if rejected else ""))
    else:
        status = "below_third_source_resolution"
        evidence.append(f"tiingo({ticker}) reached, but every disagreeing day is smaller "
                        f"than the {STEP_MATCH_ATOL:.0e} return tolerance a third vendor "
                        f"can settle")

    evidence.append(f"disagreeing days: {pair.get('days_adjustment_only')} adjustment-only, "
                    f"{pair.get('days_raw_price_differs')} with differing raw prices "
                    f"(class: {pair.get('defect_class')})")
    left = pair.get("locator_tiingo_agreement")
    right = pair.get("contender_tiingo_agreement")
    if left is not None and right is not None:
        evidence.append(f"overall in-window tiingo agreement: {locator} {left:.3f}, "
                        f"{contender} {right:.3f}")

    if step_verdict and monotonic_verdict and step_verdict != monotonic_verdict:
        evidence.append("CONFLICT: the monotonicity condition and the step-date test "
                        "name different files")
        return "undetermined", "", "conflicted", "; ".join(evidence)
    verdict = step_verdict or monotonic_verdict
    if not verdict:
        return "undetermined", "", status or "undetermined", "; ".join(evidence)
    defective = contender if verdict == locator else locator
    if not status:
        status = "resolved" if tested else "resolved_on_monotonicity"
    return verdict, defective, status, "; ".join(evidence)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True,
                        help="duplicate-locators.csv from the first census")
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--no-tiingo", action="store_true")
    parser.add_argument("--tolerance-bars", type=int, default=DEFAULT_TOLERANCE_BARS,
                        help="trading days of slack on the date-eligibility bounds")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.resolution.read_text().splitlines()
            if line.strip()]
    automatic = [r for r in rows if r.get("status") == "resolved"
                 and r.get("match_basis") == "unique_live_candidate"]
    windows = membership_intervals(automatic)
    locators = sorted(windows)
    print(f"{len(locators)} automatically resolved locators ({len(automatic)} rows)")

    pairs = list(csv.DictReader(args.pairs.open()))
    print(f"{len(pairs)} qualified pairs from the first census (generation unchanged)")

    eligible: list[dict[str, Any]] = []
    successions: list[dict[str, Any]] = []
    for pair in pairs:
        locator = pair["locator"]
        intervals = windows[locator]
        start, end = pair["membership_start"], pair["membership_end"]
        tolerant_start, tolerant_end = tolerant_bounds(
            load_frame(args.store, locator), start, end, args.tolerance_bars)
        covers_start = pair["contender_first"] <= tolerant_start
        covers_end = pair["contender_last"] >= tolerant_end
        record = {
            "locator": locator, "contender": pair["contender"],
            "membership_start": start, "membership_end": end,
            "membership_intervals": len(intervals),
            "eligibility_start": tolerant_start,
            "eligibility_end": tolerant_end,
            "locator_first": pair["locator_first"], "locator_last": pair["locator_last"],
            "contender_first": pair["contender_first"],
            "contender_last": pair["contender_last"],
            "overlap_bars_full": int(pair["overlap_bars"]),
            "full_overlap_ratio_range": float(pair["adjusted_ratio_range"] or 0) or None,
        }
        if covers_start and covers_end:
            record.update(measure_in_window(args.store, locator, pair["contender"],
                                            intervals))
            eligible.append(record)
        else:
            record["reason"] = (
                "contender begins after the window opens" if not covers_start
                else "contender ends before the window closes"
            )
            shortfall = (
                (date.fromisoformat(pair["contender_first"]) - date.fromisoformat(start)).days
                if not covers_start
                else (date.fromisoformat(end) - date.fromisoformat(pair["contender_last"])).days
            )
            record["missing_days"] = shortfall
            if shortfall <= NEAR_MISS_DAYS:
                record.update(measure_in_window(args.store, locator, pair["contender"],
                                                intervals))
                record["near_miss"] = True
            successions.append(record)

    near_misses = [p for p in successions if p.get("near_miss")
                   and (p.get("window_ratio_range") or 0) > RATIO_RANGE_TOLERANCE]
    contending = [p for p in eligible
                  if p.get("window_ratio_range") is not None
                  and p["window_ratio_range"] > RATIO_RANGE_TOLERANCE]
    above_floor = [p for p in contending if p.get("exceeds_rounding_floor")]
    print(f"  date-eligible contenders : {len(eligible)}")
    print(f"  lineage successions      : {len(successions)} "
          f"({len(near_misses)} short of eligibility by <= {NEAR_MISS_DAYS}d "
          f"and diverging anyway)")
    print(f"  diverge inside window    : {len(contending)} "
          f"({len(above_floor)} above their own rounding floor)")

    print("adjudicating survivors ...")
    throttled = False
    for pair in above_floor:
        intervals = windows[pair["locator"]]
        for side, symbol in (("locator", pair["locator"]), ("contender", pair["contender"])):
            for key, value in factor_diagnostics(args.store, symbol, intervals).items():
                pair[f"{side}_{key}"] = value
        if not args.no_tiingo:
            start = pair["membership_start"]
            reference: pd.Series | None = None
            ticker, rejected = "", []
            for candidate in tiingo_ticker_candidates(pair["locator"], pair["contender"]):
                try:
                    frame = tiingo_series(candidate, start, args.cache)
                except TiingoThrottled:
                    throttled = True
                    break
                if frame is None:
                    continue
                match = max(
                    (m for m in (
                        tiingo_is_same_entity(args.store, pair["locator"], intervals, frame),
                        tiingo_is_same_entity(args.store, pair["contender"], intervals, frame),
                    ) if m is not None), default=None)
                if match is None or match < TIINGO_MIN_ENTITY_MATCH:
                    rejected.append(f"{candidate}"
                                    f"({'no overlap' if match is None else f'{match:.2f}'})")
                    continue
                reference = frame["ret"].dropna()
                ticker = candidate
                pair["tiingo_entity_match"] = match
                break
            if throttled:
                pair["tiingo_throttled"] = True
            if rejected:
                pair["tiingo_tickers_rejected"] = ";".join(rejected)
                print(f"    rejected as a different entity: {';'.join(rejected)}")
            if reference is not None:
                pair["tiingo_ticker"] = ticker
                for side, symbol in (("locator", pair["locator"]),
                                     ("contender", pair["contender"])):
                    measured = tiingo_agreement(args.store, symbol, intervals, reference)
                    if measured is None:
                        continue
                    pair[f"{side}_tiingo_agreement"] = measured["agreement"]
                    pair[f"{side}_tiingo_bars"] = measured["bars"]
                    pair[f"{side}_tiingo_worst_difference"] = measured[
                        "worst_abs_difference"]
                pair.update(step_evidence(args.store, pair, reference))
        pair.update(classify_disagreement(args.store, pair))
        verdict, defective, status, evidence = adjudicate(pair)
        pair["panel_should_use"] = verdict
        pair["defective_file"] = defective
        pair["status"] = status
        pair["evidence"] = evidence
        print(f"  {pair['locator']:>6s}/{pair['contender']:<8s} -> {verdict:<9s} "
              f"[{status}]")

    args.out.mkdir(parents=True, exist_ok=True)

    def dump(name: str, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        fields: list[str] = []
        for record in records:
            for key in record:
                if key not in fields:
                    fields.append(key)
        with (args.out / name).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

    dump("adjudication.csv", above_floor)
    dump("date-eligible.csv", eligible)
    dump("lineage-successions.csv", successions)

    summary = {
        "scope": {
            "correction_1": "the 5% gate threshold is withdrawn; no fraction is gated",
            "correction_2": "a contender counts only if its bounds contain the membership "
                            "window AND the two imply different returns inside that window",
            "metric_retained": "range of adjusted_a/adjusted_b; adjusted-level agreement is "
                               "degenerate and is not used",
            "candidate_generation": "unchanged from run_duplicate_locator_census.py and not "
                                    "redone; the lower-bound caveat carries over",
        },
        "automatic_locators": len(locators),
        "eligibility_tolerance_bars": args.tolerance_bars,
        "qualified_pairs": len(pairs),
        "date_eligible_pairs": len(eligible),
        "date_eligible_locators": len({p["locator"] for p in eligible}),
        "lineage_succession_pairs": len(successions),
        "lineage_succession_locators": len({p["locator"] for p in successions}),
        "near_miss_days": NEAR_MISS_DAYS,
        "near_miss_diverging": [
            {"locator": p["locator"], "contender": p["contender"],
             "missing_days": p["missing_days"],
             "window_ratio_range": p.get("window_ratio_range"),
             "window_total_return_gap": p.get("window_total_return_gap")}
            for p in near_misses],
        "contending_pairs": len(contending),
        "contending_locators": sorted({p["locator"] for p in contending}),
        "contending_above_rounding_floor": len(above_floor),
        "contending_locators_above_floor": sorted({p["locator"] for p in above_floor}),
        "adjudication": [
            {"locator": p["locator"], "contender": p["contender"],
             "window_ratio_range": p.get("window_ratio_range"),
             "window_close_agreement": p.get("window_close_agreement"),
             "window_bars": p.get("window_bars"),
             "window_total_return_gap": p.get("window_total_return_gap"),
             "panel_should_use": p.get("panel_should_use"),
             "status": p.get("status"),
             "defect_class": p.get("defect_class"),
             "implied_distribution_locator": p.get("implied_distribution_locator"),
             "implied_distribution_contender": p.get("implied_distribution_contender"),
             "defective_file": p.get("defective_file"),
             "evidence": p.get("evidence")}
            for p in sorted(above_floor, key=lambda p: -(p.get("window_ratio_range") or 0))
        ],
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
