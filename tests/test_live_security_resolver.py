"""Identity tests use synthetic prices/metadata, never the downloading store."""

from dataclasses import replace
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from woodland.live.resolver_audit import (
    annual_report,
    load_constituents,
    load_conventions,
    snapshot_store,
    write_report,
)
from woodland.live.security_resolver import (
    Constituent,
    Security,
    SecurityResolver,
    UnresolvedConstituents,
    instrument_exclusion,
    require_resolved,
)

CONVENTIONS = Path(__file__).parents[1] / "woodland/live/resolver_conventions.json"


def security(symbol: str, name: str, first: str = "1990-01-01",
             last: str = "2026-09-04", exchange: str = "NYSE", **kwargs: object) -> Security:
    return Security(security_id="test:" + symbol, price_symbol=symbol, name=name,
                    exchange=exchange, instrument_type="Common Stock",
                    first=date.fromisoformat(first), last=date.fromisoformat(last),
                    available=True, **kwargs)  # type: ignore[arg-type]


def constituent(symbol: str, when: str, name: str = "", exchange: str = "") -> Constituent:
    return Constituent(symbol + when, symbol, date.fromisoformat(when),
                       date.fromisoformat(when), name, exchange)


@pytest.fixture
def family() -> SecurityResolver:
    conventions, rules = load_conventions(CONVENTIONS)
    securities = [
        security("BBBYQ", "Bed Bath & Beyond Inc.", "1992-06-05", "2023-09-29", "PINK",
                 catalog_identifiers={"ISIN": "US0758961009"}),
        security("BBBY", "Bed Bath & Beyond, Inc.", "2002-05-30",
                 catalog_identifiers={"ISIN": "US6903701018"}),
        security("BBBY_old", "Bed Bath & Beyond Inc", "2002-05-30", "2025-08-29", "NASDAQ",
                 catalog_identifiers={"ISIN": "US0758961009"},
                 quarantine=conventions["quarantine"]["BBBY_old"]),
        security("LEH", "Lehman Brothers Holdings Inc", "1997-12-31", "2008-09-17"),
        security("ENRNQ", "Enron Corp", "1997-12-31", "2004-11-17"),
        security("WAMUQ", "Washington Mutual Inc", "1983-01-01", "2012-03-19", "OTCMKTS",
                 catalog_identifiers={"ISIN": "US9393221034"}),
        security("WM", "Waste Management Inc", "1990-01-01",
                 catalog_identifiers={"ISIN": "US94106L1098"}),
    ]
    return SecurityResolver(securities, rules)


@pytest.mark.parametrize("year", range(1993, 2023))
def test_old_bbby_always_selects_bankrupt_entity(family: SecurityResolver, year: int) -> None:
    row = family.resolve(constituent("BBBY", f"{year}-06-15"))
    assert row.price_symbol == "BBBYQ"
    assert row.match_basis == "manual"


def test_bbby_reassignment_boundary_and_gap(family: SecurityResolver) -> None:
    assert family.resolve(constituent("BBBY", "2025-08-29")).price_symbol == "BBBY"
    for day in ("2023-06-01", "2024-01-01", "2025-08-28"):
        with pytest.raises(UnresolvedConstituents):
            family.resolve(constituent("BBBY", day))
    assert family.resolve(constituent("BBBYQ", "2023-09-29")).price_symbol == "BBBYQ"


def test_bbby_old_contradictory_metadata_is_quarantined(family: SecurityResolver) -> None:
    with pytest.raises(UnresolvedConstituents):
        family.resolve(constituent("BBBY_old", "2020-01-02"))
    # Even the catalog's ISIN is insufficient to bless this price file.
    bad = next(s for s in family.securities if s.price_symbol == "BBBY_old")
    source = replace(constituent("BBBY_old", "2020-01-02", bad.name, bad.exchange),
                     identifiers={"ISIN": "US0758961009"})
    with pytest.raises(UnresolvedConstituents):
        SecurityResolver([bad]).resolve(source)


@pytest.mark.parametrize(("symbol", "target"), [("LEH", "LEH"), ("ENE", "ENRNQ"),
                                                ("WM", "WAMUQ")])
def test_confirmed_historical_aliases(family: SecurityResolver, symbol: str, target: str) -> None:
    assert family.resolve(constituent(symbol, "2000-01-03")).price_symbol == target


def test_wm_reuse_cannot_join_entities(family: SecurityResolver) -> None:
    old = family.resolve(constituent("WM", "2008-09-24"))
    new = family.resolve(constituent("WM", "2009-08-05"))
    assert old.resolved_security != new.resolved_security
    assert (old.price_symbol, new.price_symbol) == ("WAMUQ", "WM")
    with pytest.raises(UnresolvedConstituents):
        family.resolve(constituent("WM", "2009-08-04"))
    crossing = replace(constituent("WM", "2008-01-02"), end=date(2010, 1, 4))
    with pytest.raises(UnresolvedConstituents):
        family.resolve(crossing)
    # The newer company's backfilled history must not bypass the reviewed bounds.
    with pytest.raises(UnresolvedConstituents):
        family.resolve(constituent("WM", "2000-01-03", "Waste Management Inc", "NYSE"))


@pytest.mark.parametrize("name", ["Acme Warrants", "Acme Rights", "Acme Units",
                                  "Acme Preferred Stock", "Acme Senior Notes Due 2031", "BBBY-WS"])
def test_catalog_names_cannot_override_instrument_type(name: str) -> None:
    assert instrument_exclusion("Common Stock", name) is None
    s = security("ACME", name)
    r = SecurityResolver([s]).audit_one(constituent("ACME", "2000-01-03", name, "NYSE"))
    assert r.status == "resolved"


def test_type_whitelist_and_no_suffix_inference() -> None:
    assert instrument_exclusion("Warrant", "Acme")
    assert instrument_exclusion("Preferred Stock", "Acme")
    assert instrument_exclusion("", "Acme")
    assert instrument_exclusion("Common Stock", "Unit Corp") is None
    assert instrument_exclusion("Common Stock", "Enron Corp") is None
    s = security("ACME_old", "Acme")
    assert SecurityResolver([s]).audit_one(constituent("ACME", "2000-01-03")).status \
        == "candidates_unmatched"


def test_failure_modes_and_never_drop() -> None:
    s = security("ACME", "Acme")
    source = constituent("ACME", "1980-01-03", "Different Company", "NYSE")
    resolver = SecurityResolver([s])
    assert resolver.audit_one(source).status == "candidates_unmatched"
    assert SecurityResolver([replace(s, available=False)]).audit_one(source).status \
        == "no_candidates"
    valid = constituent("ACME", "2000-01-03", "Acme", "NYSE")
    with pytest.raises(UnresolvedConstituents) as error:
        resolver.resolve_all([valid, source, constituent("NONEXISTENT", "2000-01-03")])
    assert len(error.value.rows) == 3
    assert len(error.value.failures) == 2
    with pytest.raises(ValueError):
        require_resolved([])


def test_exact_catalog_name_is_not_identity_evidence() -> None:
    resolver = SecurityResolver([security("NEW", "Acme Incorporated")])
    c = constituent("OLD", "2000-01-03", "Acme Incorporated", "NYSE")
    with pytest.raises(UnresolvedConstituents):
        resolver.resolve(c)
    for wrong in (replace(c, exchange=""), replace(c, exchange="NASDAQ"),
                  replace(c, start=date(1980, 1, 1))):
        with pytest.raises(UnresolvedConstituents):
            resolver.resolve(wrong)


def test_fuzzy_never_accepted_even_at_high_similarity() -> None:
    resolver = SecurityResolver([security("NEW", "Acme Corporation")])
    c = constituent("OLD", "2000-01-03", "Acme Corporatio", "NYSE")
    row = resolver.audit_one(c)
    assert row.status == "no_candidates"
    assert row.match_basis is None
    assert row.fuzzy_matches == ()
    with pytest.raises(UnresolvedConstituents):
        resolver.resolve(c)


def test_stable_id_must_be_on_price_side_and_has_priority() -> None:
    s = security("NEW", "Renamed Company", catalog_identifiers={"ISIN": "id1"})
    c = replace(constituent("OLD", "2000-01-03"), identifiers={"ISIN": "id1"})
    with pytest.raises(UnresolvedConstituents):
        SecurityResolver([s]).resolve(c)
    bound = replace(s, price_identifiers={"ISIN": "id1"})
    competitor = security("OTHER", "Acme")
    c = replace(c, name="Acme", exchange="NYSE")
    result = SecurityResolver([bound, competitor]).resolve(c)
    assert result.price_symbol == "NEW" and result.match_basis == "stable_id"


def test_id_conflict_cannot_be_overridden_by_name_or_manual(family: SecurityResolver) -> None:
    c = replace(constituent("BBBY", "2020-01-02"), identifiers={"ISIN": "US6903701018"})
    with pytest.raises(UnresolvedConstituents):
        family.resolve(c)


def test_reviewed_mapping_refuses_changed_provider_identity(family: SecurityResolver) -> None:
    old = next(s for s in family.securities if s.price_symbol == "BBBYQ")
    for changed in (replace(old, catalog_identifiers={"ISIN": "different"}),):
        resolver = SecurityResolver([changed], family.rules)
        with pytest.raises(UnresolvedConstituents):
            resolver.resolve(constituent("BBBY", "2000-01-03"))

    renamed = SecurityResolver([replace(old, name="Unrelated Corporation")], family.rules)
    assert renamed.resolve(constituent("BBBY", "2000-01-03")).price_symbol == "BBBYQ"


def test_ambiguous_files_and_duplicate_locators_refused() -> None:
    a, b = [security(symbol, "Acme", price_identifiers={"ISIN": "same"})
            for symbol in ["A", "B"]]
    with pytest.raises(UnresolvedConstituents):
        SecurityResolver([a, b]).resolve(
            replace(constituent("A", "2000-01-03"), identifiers={"ISIN": "same"}))
    with pytest.raises(ValueError):
        SecurityResolver([a, a])


def test_versioned_report_preserves_failures_and_fuzzy(tmp_path: Path) -> None:
    resolver = SecurityResolver([security("A", "Acme Corporation")])
    rows = [resolver.audit_one(constituent("UNKNOWN", "1980-01-03")),
            resolver.audit_one(constituent("A", "1980-01-03", "Acme Corporatio", "NYSE"))]
    annual = annual_report(rows)
    assert annual[0]["no_candidates"] == 1
    assert annual[0]["candidates_unmatched"] == 1
    out = tmp_path / "v1"
    write_report(out, rows, {}, [], {"version": "test"}, "synthetic")
    assert len((out / "resolution.jsonl").read_text().splitlines()) == 2
    assert (out / "fuzzy-review.json").read_text() == "[]"
    assert '"resolver_version"' in (out / "manifest.json").read_text()
    with pytest.raises(FileExistsError):
        write_report(out, rows, {}, [], {"version": "test"}, "synthetic")


def test_snapshot_is_read_only_and_tolerates_incomplete_store(tmp_path: Path) -> None:
    import json

    rows = [{"Code": s, "Name": s, "Type": "Common Stock", "Exchange": "NYSE"}
            for s in ["A", "B", "C"]]
    (tmp_path / "active-symbols.json").write_text(json.dumps(rows))
    (tmp_path / "delisted-symbols.json").write_text("[]")
    pd.DataFrame({"date": ["2000-01-03", "2000-01-04"], "close": [1, 2]}).to_parquet(
        tmp_path / "A.US.parquet")
    (tmp_path / "B.US.parquet").write_bytes(b"unfinished")
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    securities, manifest, _ = snapshot_store(tmp_path, {})
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert [s.available for s in securities] == [True, False, False]
    assert manifest["files"]["B"]["state"] == "unreadable_or_changing"
    assert manifest["files"]["C"]["state"] == "not_in_snapshot"


def test_input_never_fills_names_from_current_catalog(tmp_path: Path) -> None:
    p = tmp_path / "membership.csv"
    p.write_text('date,tickers\n2000-01-03,"A,B"\n2000-02-01,"A,B"\n')
    rows = load_constituents(p)
    assert len(rows) == 2 and all(not r.name for r in rows)
    assert rows[0].start == date(2000, 1, 3) and rows[0].end == date(2000, 2, 1)


@pytest.mark.parametrize('symbol', ['ABC_old', 'ABC_old1', 'ABC_old2'])
def test_all_archived_locators_refuse_even_exact_identity(symbol: str) -> None:
    s = security(symbol, 'Example Inc')
    resolver = SecurityResolver([s])
    with pytest.raises(UnresolvedConstituents):
        resolver.resolve(constituent(symbol, '2000-01-03', 'Example Inc', 'NYSE'))


def test_empty_response_is_separate_and_refuses() -> None:
    s = replace(security('ABC', 'Example Inc'), available=False, first=None,
                last=None, response_state='empty_response')
    resolver = SecurityResolver([s])
    row = resolver.audit_one(constituent('ABC', '2000-01-03'))
    assert row.status == 'empty_response'
    assert annual_report([row])[0]['empty_response'] == 1
    with pytest.raises(UnresolvedConstituents):
        require_resolved([row])


def test_readable_match_takes_precedence_over_empty_alternative() -> None:
    empty = replace(security('ABC', 'Example Inc'), available=False,
                    response_state='empty_response', catalog_identifiers={'ISIN': 'same'})
    good = security('XYZ', 'Example Inc', price_identifiers={'ISIN': 'same'})
    row = SecurityResolver([empty, good]).resolve(
        replace(constituent('ABC', '2000-01-03'), identifiers={'ISIN': 'same'}))
    assert row.price_symbol == 'XYZ'


def test_candidate_diagnostics_record_all_rejections() -> None:
    s = replace(security('ABC_old', 'Example Preferred', first='2010-01-01'),
                quarantine='review', catalog_identifiers={'ISIN': 'wrong'},
                instrument_type='Preferred Stock')
    c = replace(constituent('ABC_old', '2000-01-03'), identifiers={'ISIN': 'right'})
    row = SecurityResolver([s]).audit_one(c)
    assert set(row.candidate_diagnostics[0]['rejected_predicates']) == {
        'archived', 'quarantine', 'instrument_exclusion', 'dates_first', 'id_conflict'}
    assert not row.candidate_diagnostics[0]['no_acceptance_basis']
    assert row.status == 'candidates_unmatched'


def test_candidate_diagnostics_missing_basis_and_accepted() -> None:
    resolver = SecurityResolver([security('ABC', 'Example Inc'),
                                 security('ABC_old', 'Other slot name')])
    c = constituent('ABC', '2000-01-03', 'Unverified different name')
    rejected = resolver.audit_one(c)
    assert rejected.candidate_diagnostics[0]['rejected_predicates'] == ['no_acceptance_basis']
    assert rejected.candidate_diagnostics[0]['no_acceptance_basis']
    accepted = SecurityResolver([security('ABC', 'Any slot name')]).resolve(c)
    assert not accepted.candidate_diagnostics[0]['no_acceptance_basis']


def test_normalized_symbol_unique_live_accepts() -> None:
    row = SecurityResolver([security('BRK-B', 'Berkshire Hathaway')]).resolve(
        constituent('BRK.B', '2000-01-03'))
    assert row.price_symbol == 'BRK-B'
    assert row.match_basis == 'normalized_symbol'
    assert 'BRK.B' in row.evidence and 'BRK-B' in row.evidence


@pytest.mark.parametrize('symbol,name', [('MOB', 'Mobilicom Limited ADS'),
                                        ('RAL', 'Ralliant Corporation')])
def test_archive_dates_never_prove_identity(symbol: str, name: str) -> None:
    row = SecurityResolver([security(symbol + '_old', name)]).audit_one(
        constituent(symbol, '1999-06-01'))
    assert row.status == 'candidates_unmatched'
    assert row.failures[symbol + '_old'] == ['archived']


def test_date_eligible_quarantined_archive_blocks_live_uniqueness() -> None:
    live = security('APC', 'Live Company')
    archive = replace(security('APC_old', 'Anadarko Petroleum'), quarantine='review')
    row = SecurityResolver([live, archive]).audit_one(constituent('APC', '2000-01-03'))
    assert row.status == 'candidates_unmatched'
    assert set(row.candidates) == {'APC', 'APC_old'}
    assert 'no_acceptance_basis' in row.failures['APC']


def test_live_start_after_membership_is_still_refused() -> None:
    row = SecurityResolver([security('APC', 'Live Company', first='2026-02-12')]).audit_one(
        constituent('APC', '2000-01-03'))
    assert row.status == 'candidates_unmatched'
    assert row.failures['APC'] == ['dates_first']


def test_recorded_reuse_population_retains_date_rejection() -> None:
    """Integration check when local versioned audit evidence is available."""
    import json
    root = Path(__file__).parents[1] / 'reports/security-resolver'
    old_path = root / '2026-09-06-v6-resolver/resolution.jsonl'
    new_path = root / '2026-09-06-v7-resolver/resolution.jsonl'
    if not old_path.exists() or not new_path.exists():
        pytest.skip('Local market-data audit evidence is not committed')
    old = [json.loads(line) for line in old_path.read_text().splitlines()]
    new = {r['record_id']: r for r in
           (json.loads(line) for line in new_path.read_text().splitlines()) if 'record_id' in r}
    manifest = json.loads((old_path.parent / 'manifest.json').read_text())
    reuse = [r for r in old if r.get('status') == 'candidates_unmatched'
             and len(r['candidates']) == 1
             and manifest['files'][r['candidates'][0]].get('first', '') > r['start']]
    assert len(reuse) == 1021
    assert len({r['constituent_symbol'] for r in reuse}) == 136
    for row in reuse:
        result = new[row['record_id']]
        assert 'dates_first' in result['failures'][row['candidates'][0]]
        assert result['status'] == 'candidates_unmatched'
