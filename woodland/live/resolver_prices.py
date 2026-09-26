"""Read-only raw-bar evidence and conservative archived splice boundaries."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from woodland.live.security_resolver import (
    INTERIOR_GAP_DAYS,
    Constituent,
    ManualRule,
    Security,
    SecurityResolver,
    archived_symbol,
)

ARCHIVED_SPLICE_GAP_DAYS = INTERIOR_GAP_DAYS
VOLUME_REFERENCE_BARS = 60
REVIEW_MIN_BARS = 61
REVIEW_MIN_MEDIAN_VOLUME = 100_000
REVIEW_MIN_CLOSE = 1
REVIEW_MAX_CLOSE = 10_000
REVIEW_MIN_TERMINAL_RATIO = 1
REVIEW_MAX_TERMINAL_RATIO = 100


def segment_bounds(dates: pd.Series) -> tuple[list[tuple[int, int]], list[dict[str, Any]]]:
    """Half-open positional slices on already ordered unique dates."""
    values = pd.to_datetime(dates).reset_index(drop=True)
    if values.isna().any() or not values.is_monotonic_increasing or values.duplicated().any():
        raise ValueError('Dates must be valid, strictly increasing and unique')
    cuts = [int(i) for i in np.flatnonzero(
        values.diff().dt.days.to_numpy() > ARCHIVED_SPLICE_GAP_DAYS)]
    seams = [{'previous': str(values.iloc[i - 1].date()),
              'next': str(values.iloc[i].date()),
              'gap_days': int((values.iloc[i] - values.iloc[i - 1]).days)} for i in cuts]
    edges = [0, *cuts, len(values)]
    return list(zip(edges, edges[1:], strict=False)), seams


def price_evidence(frame: pd.DataFrame) -> dict[str, Any]:
    def finite(value: Any) -> float | None:
        return float(value) if pd.notna(value) and np.isfinite(value) else None
    volume = pd.to_numeric(frame['volume'], errors='coerce')
    reference = volume.iloc[max(0, len(volume) - VOLUME_REFERENCE_BARS - 1):-1]
    median = finite(reference.median()) if len(reference) else None
    last = finite(volume.iloc[-1])
    return dict(first_close=finite(frame['close'].iloc[0]),
                last_close=finite(frame['close'].iloc[-1]),
                median_volume=finite(volume.median()), last_bar_volume=last,
                trailing_volume_median=median, trailing_volume_bar_count=int(reference.count()),
                last_bar_volume_ratio=last / median if last is not None and median
                and median > 0 else None, bar_count=len(frame))


def scan_price_evidence(
    store: Path, securities: list[Security], inputs: list[Constituent], rules: list[ManualRule],
) -> tuple[list[Security], dict[str, Any]]:
    lookup = SecurityResolver(securities, rules)
    needed: set[str] = set()
    for c in inputs:
        for spelling in {c.symbol, c.symbol.replace('.', '-')}:
            needed.update(s.price_symbol for s in lookup.by_symbol.get(spelling, []))
            needed.update(s.price_symbol for s in lookup.archives.get(spelling, []))
        for rule in lookup.by_rule.get(c.symbol, []):
            needed.add(rule.price_symbol)
    targets = [s for s in securities if s.available and
               (not archived_symbol(s.price_symbol) or s.price_symbol in needed)]

    def inspect(s: Security) -> tuple[list[Security], dict[str, Any]]:
        path = store / (s.price_symbol + '.US.parquet')
        before = path.stat()
        columns = ['date', 'close', 'volume'] if s.price_symbol in needed else ['date']
        frame = pd.read_parquet(path, columns=columns).sort_values('date').reset_index(drop=True)
        bounds, seams = segment_bounds(frame['date'])
        archive = archived_symbol(s.price_symbol)
        # Live gaps are observed only: keep the full original candidate intact.
        pieces = bounds if archive else [(0, len(frame))]
        result = []
        for index, (a, b) in enumerate(pieces, 1):
            part = frame.iloc[a:b]
            split = archive and len(bounds) > 1
            locator = f'{s.price_symbol}::segment{index}' if split else s.price_symbol
            result.append(replace(s, price_symbol=locator,
                security_id=f'{s.security_id}::segment{index}' if split else s.security_id,
                storage_symbol=s.price_symbol, segment_index=index,
                first=pd.Timestamp(part['date'].iloc[0]).date(),
                last=pd.Timestamp(part['date'].iloc[-1]).date(),
                price_evidence=price_evidence(part) if s.price_symbol in needed else {},
                trading_gaps=tuple((pd.Timestamp(g['previous']).date(),
                                    pd.Timestamp(g['next']).date())
                                   for g in seams) if not archive else ()))
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError(f'Price file changed during read: {s.price_symbol}')
        return result, dict(symbol=s.price_symbol, archived=archive, seams=seams,
                            applied=archive and bool(seams),
                            segments=[dict(candidate=x.price_symbol, first=str(x.first),
                                           last=str(x.last), segment_index=x.segment_index,
                                           **x.price_evidence) for x in result])

    replacements = {}
    changes = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for s, (parts, info) in zip(targets, executor.map(inspect, targets), strict=True):
            replacements[s.price_symbol] = parts
            if info['seams']:
                changes.append(info)
    updated = [part for s in securities for part in replacements.get(s.price_symbol, [s])]
    return updated, dict(gap_threshold_calendar_days=ARCHIVED_SPLICE_GAP_DAYS,
        reference_previous_bars=VOLUME_REFERENCE_BARS,
        archived_files_scanned=sum(archived_symbol(s.price_symbol) for s in targets),
        live_files_scanned=sum(not archived_symbol(s.price_symbol) for s in targets),
        archived_segmentations=[r for r in changes if r['archived']],
        live_gaps_report_only=[r for r in changes if not r['archived']])


def suggest_price_verdict(
    security: Security | None, occurrences: list[Any],
) -> tuple[str, str, str]:
    if security is None or not security.price_evidence:
        return 'unknown', 'low', 'Price evidence unavailable; no identity conclusion.'
    s, e = security, security.price_evidence
    notes = (f"last bar {s.last} close {e['last_close']} on {e['last_bar_volume']} shares "
             f"vs 60d median {e['trailing_volume_median']} "
             f"({e['trailing_volume_bar_count']} preceding bars; excludes terminal bar). ")
    contains = [s.first is not None and s.last is not None
                and s.first.isoformat() <= str(r.start) <= str(r.end) <= s.last.isoformat()
                for r in occurrences]
    overlaps = [s.first is not None and s.last is not None
                and s.first.isoformat() <= str(r.end) and str(r.start) <= s.last.isoformat()
                for r in occurrences]
    if occurrences and not any(overlaps):
        return 'reject', 'high', notes + 'No overlap with pending membership; wrong time window.'
    plausible = (e['bar_count'] >= REVIEW_MIN_BARS
                 and all(e[k] is not None and REVIEW_MIN_CLOSE <= e[k] <= REVIEW_MAX_CLOSE
                         for k in ['first_close', 'last_close'])
                 and e['median_volume'] is not None
                 and e['median_volume'] >= REVIEW_MIN_MEDIAN_VOLUME
                 and e['last_bar_volume'] is not None and e['last_bar_volume'] > 0
                 and e['last_bar_volume_ratio'] is not None
                 and REVIEW_MIN_TERMINAL_RATIO <= e['last_bar_volume_ratio']
                 <= REVIEW_MAX_TERMINAL_RATIO)
    if contains and all(contains) and plausible:
        return 'accept', 'medium', notes + ('Contains all pending windows; price level, liquidity '
            'and terminal activity compatible. Human suggestion only, not verified identity.')
    return 'unknown', 'low', notes + ('Partial containment or insufficient price/volume evidence. '
                                    'Price pattern alone does not decide identity.')
