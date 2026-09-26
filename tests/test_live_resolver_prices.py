"""Segmentation and price-only review invariants; no external market data."""
from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from woodland.live.resolver_prices import (
    ARCHIVED_SPLICE_GAP_DAYS,
    price_evidence,
    scan_price_evidence,
    segment_bounds,
    suggest_price_verdict,
)
from woodland.live.security_resolver import Constituent, Security, SecurityResolver


def test_gap_is_strictly_greater_than_200() -> None:
    first = pd.Timestamp('2000-01-01')
    dates = pd.Series([first, first + pd.Timedelta(days=200), first + pd.Timedelta(days=401)])
    bounds, seams = segment_bounds(dates)
    assert ARCHIVED_SPLICE_GAP_DAYS == 200
    assert bounds == [(0, 2), (2, 3)]
    assert seams[0]['gap_days'] == 201


def test_invalid_duplicate_dates_refuse() -> None:
    with pytest.raises(ValueError):
        segment_bounds(pd.Series(['2000-01-01', '2000-01-01']))


def test_volume_reference_excludes_terminal_bar() -> None:
    frame = pd.DataFrame({'close': [33.48] * 61, 'volume': [900_000] * 60 + [7_134_000]})
    evidence = price_evidence(frame)
    assert evidence['trailing_volume_median'] == 900_000
    assert evidence['last_bar_volume_ratio'] == pytest.approx(7_134_000 / 900_000)
    zero = price_evidence(pd.DataFrame({'close': [1, 2], 'volume': [0, 10]}))
    assert zero['last_bar_volume_ratio'] is None


def test_archives_segment_and_live_gaps_report_only(tmp_path: Path) -> None:
    dates = ['2000-01-03', '2000-01-04', '2010-01-04', '2010-01-05']
    frame = pd.DataFrame({'date': dates, 'close': [10, 11, 1, 2], 'volume': [1000] * 4})
    securities = []
    for symbol in ['ABC_old', 'ABC']:
        frame.to_parquet(tmp_path / f'{symbol}.US.parquet')
        securities.append(Security(symbol, symbol, 'Display', 'NYSE', 'Common Stock',
                                   date(2000, 1, 3), date(2010, 1, 5), True))
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    c = Constituent('test', 'ABC', date(2000, 1, 3), date(2010, 1, 5))
    updated, scan = scan_price_evidence(tmp_path, securities, [c], [])
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert [s.price_symbol for s in updated] == ['ABC_old::segment1', 'ABC_old::segment2', 'ABC']
    assert len(scan['archived_segmentations']) == len(scan['live_gaps_report_only']) == 1
    assert not scan['live_gaps_report_only'][0]['applied']
    resolver = SecurityResolver(updated)
    row = resolver.audit_one(c)
    assert 'dates_last' in row.failures['ABC_old::segment1']
    assert 'dates_first' in row.failures['ABC_old::segment2']
    # The live locator stays full-span, but v1.4 refuses automatic gap crossing.
    assert row.price_symbol is None
    assert row.status == 'candidates_unmatched'
    assert 'interior_gap' in row.failures['ABC']
    narrow = resolver.audit_one(replace(c, end=date(2000, 1, 4)))
    assert narrow.status == 'candidates_unmatched'
    assert narrow.failures['ABC_old::segment1'] == ['archived']


def test_names_never_change_price_suggestions() -> None:
    e = price_evidence(pd.DataFrame({'close': [33.48] * 61,
                                    'volume': [900_000] * 60 + [7_134_000]}))
    s = Security('id', 'RAL_old', 'Ralliant', 'NYSE', 'Common Stock',
                 date(1997, 12, 31), date(2001, 12, 12), True, price_evidence=e)
    c = Constituent('test', 'RAL', date(1999, 1, 5), date(2001, 12, 11))
    verdict = suggest_price_verdict(s, [c])
    assert verdict[:2] == ('accept', 'medium')
    assert verdict == suggest_price_verdict(replace(s, name='Unrelated Company'), [c])
    assert 'Ralliant' not in verdict[2]
    assert suggest_price_verdict(s, [replace(c, start=date(2005, 1, 1),
                                            end=date(2006, 1, 1))])[:2] == ('reject', 'high')


def test_catalog_name_difference_alone_does_not_quarantine(tmp_path: Path) -> None:
    import json

    from woodland.live.resolver_audit import snapshot_store
    base = {'Code': 'ABC', 'Type': 'Common Stock', 'Exchange': 'NYSE'}
    (tmp_path / 'active-symbols.json').write_text(json.dumps([{**base, 'Name': 'Current'}]))
    (tmp_path / 'delisted-symbols.json').write_text(json.dumps([{**base, 'Name': 'Former'}]))
    securities, manifest, _ = snapshot_store(tmp_path, {})
    assert not securities[0].quarantine
    assert manifest['catalog_conflicts'] == []
