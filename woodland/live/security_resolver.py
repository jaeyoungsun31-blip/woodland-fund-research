"""Fail-closed security identity resolution, independent of prices and models.

Dates are inclusive identity-validation bounds, NOT membership construction rules.
No suffix stripping, ticker-only acceptance, series concatenation, or fuzzy acceptance.
An audit may collect failures; production callers use resolve_all(), which raises.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

RESOLVER_VERSION = "1.4.0"
INTERIOR_GAP_DAYS = 200
FUZZY_REVIEW_FLOOR = 0.80  # Candidate reporting only; never an acceptance threshold.


def archived_symbol(symbol: str) -> bool:
    """User-directed exclusion, including numbered provider archive variants."""
    return re.search(r"_old\d*$", symbol.split("::segment")[0], re.IGNORECASE) is not None


def normalized_name(value: str) -> str:
    """Normalize typography only; preserve legal names and share-class distinctions."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold().replace("&", " and ")))


def instrument_exclusion(kind: str, name: str) -> str | None:
    """Whitelist the provider class, with a veto for contradictory security names."""
    if normalized_name(kind) != "common stock":
        return "instrument_type_not_common_stock"
    # Catalog Name is an unreliable slot label, never an instrument veto.
    return None


@dataclass(frozen=True)
class Constituent:
    record_id: str
    symbol: str
    start: date
    end: date
    name: str = ""
    exchange: str = ""
    identifiers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.record_id or not self.symbol or self.end < self.start:
            raise ValueError("Constituent requires an id, symbol, and ordered date bounds")


@dataclass(frozen=True)
class Security:
    security_id: str
    price_symbol: str
    name: str
    exchange: str
    instrument_type: str
    first: date | None
    last: date | None
    available: bool
    catalog_identifiers: Mapping[str, str] = field(default_factory=dict)
    # Only populated if identity is actually returned/bound by the price source.
    # A symbol-list ISIN alone MUST NOT be copied into this field.
    price_identifiers: Mapping[str, str] = field(default_factory=dict)
    quarantine: str = ""
    response_state: str = "unknown"
    storage_symbol: str = ""
    segment_index: int = 0
    price_evidence: Mapping[str, Any] = field(default_factory=dict)
    trading_gaps: tuple[tuple[date, date], ...] = ()


@dataclass(frozen=True)
class ManualRule:
    symbol: str
    price_symbol: str
    start: date
    end: date
    evidence: str
    names: tuple[str, ...] = ()
    exchanges: tuple[str, ...] = ()
    expected_identifiers: Mapping[str, str] = field(default_factory=dict)
    require_constituent_name: bool = False

    def __post_init__(self) -> None:
        if not self.evidence or self.end < self.start:
            raise ValueError("Manual rules require dated bounds and supporting evidence")


@dataclass(frozen=True)
class Resolution:
    record_id: str
    constituent_symbol: str
    start: str
    end: str
    status: str
    resolved_security: str | None
    price_symbol: str | None
    match_basis: str | None
    reason: str
    candidates: tuple[str, ...] = ()
    fuzzy_matches: tuple[dict[str, Any], ...] = ()
    evidence: str = ""
    candidate_diagnostics: tuple[dict[str, Any], ...] = ()
    failures: Mapping[str, list[str]] = field(default_factory=dict)
    resolver_version: str = RESOLVER_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UnresolvedConstituents(ValueError):
    def __init__(self, rows: Iterable[Resolution]):
        self.rows = tuple(rows)
        self.failures = tuple(r for r in self.rows if r.status != "resolved"
                              or not r.resolved_security or not r.price_symbol)
        super().__init__(f"Refusing use: {len(self.failures)} unresolved constituents")


def require_resolved(rows: Iterable[Resolution]) -> tuple[Resolution, ...]:
    """Mandatory boundary for any future panel consumer; no skip/filter mode."""
    result = tuple(rows)
    if not result:
        raise ValueError("Refusing an empty resolution table")
    if any(r.status != "resolved" or not r.resolved_security or not r.price_symbol for r in result):
        raise UnresolvedConstituents(result)
    return result


class SecurityResolver:
    def __init__(self, securities: Iterable[Security], rules: Iterable[ManualRule] = ()):
        self.securities = tuple(securities)
        self.rules = tuple(rules)
        self.by_symbol: dict[str, list[Security]] = defaultdict(list)
        self.by_name: dict[str, list[Security]] = defaultdict(list)
        self.by_id: dict[tuple[str, str], list[Security]] = defaultdict(list)
        self.by_word: dict[str, set[str]] = defaultdict(set)
        for s in self.securities:
            if self.by_symbol.get(s.price_symbol):
                raise ValueError("Duplicate price locator; split/review its identities first")
            self.by_symbol[s.price_symbol].append(s)
            name = ""  # Catalog names are display-only.
            if name:
                self.by_name[name].append(s)
                for word in name.split():
                    self.by_word[word].add(name)
            for key, value in {**s.catalog_identifiers, **s.price_identifiers}.items():
                if value:
                    self.by_id[key, value].append(s)
        self.archives: dict[str, list[Security]] = defaultdict(list)
        for security in self.securities:
            source = security.storage_symbol or security.price_symbol
            if source != security.price_symbol:
                self.by_symbol[source].append(security)
            if archived_symbol(source):
                base = re.sub(r"_old\d*$", "", source, flags=re.IGNORECASE)
                self.archives[base].append(security)
        self.by_rule: dict[str, list[ManualRule]] = defaultdict(list)
        for rule in self.rules:
            self.by_rule[rule.symbol].append(rule)

    @staticmethod
    def _dates(c: Constituent, s: Security) -> bool:
        return s.first is not None and s.last is not None and s.first <= c.start <= c.end <= s.last

    @staticmethod
    def _interior_gap(c: Constituent, s: Security) -> bool:
        return any((right - left).days > INTERIOR_GAP_DAYS
                   and left < c.end and right > c.start
                   for left, right in s.trading_gaps)

    @staticmethod
    def _id_conflict(c: Constituent, s: Security) -> bool:
        return any(
            value and key in s.catalog_identifiers and s.catalog_identifiers[key] != value
            for key, value in c.identifiers.items()
        ) or any(
            value and key in s.price_identifiers and s.price_identifiers[key] != value
            for key, value in c.identifiers.items()
        )

    def audit_one(self, c: Constituent) -> Resolution:
        """Return one diagnostic row, including every failure and fuzzy suggestion."""
        candidates: dict[str, Security] = {}

        def add(items: Iterable[Security]) -> None:
            for item in items:
                # Price symbols are storage locators, not inferred security identities.
                candidates[item.price_symbol] = item

        spellings = {c.symbol, c.symbol.replace(".", "-")}
        symbol_candidates: list[Security] = []
        for spelling in sorted(spellings):
            symbol_candidates.extend(self.by_symbol.get(spelling, []))
            symbol_candidates.extend(self.archives.get(spelling, []))
        add(symbol_candidates)
        name = normalized_name(c.name)
        add(self.by_name.get(name, []))
        for key, value in c.identifiers.items():
            if value:
                add(self.by_id.get((key, value), []))
        rules = self.by_rule.get(c.symbol, [])
        for rule in rules:
            add(self.by_symbol.get(rule.price_symbol, []))
        fuzzy: list[dict[str, Any]] = []
        # No catalog-name matching; fuzzy review queue remains empty.
        diagnostics: dict[str, dict[str, Any]] = {}
        for symbol, candidate in sorted(candidates.items()):
            predicates = {
                "archived": archived_symbol(candidate.price_symbol),
                "quarantine": bool(candidate.quarantine),
                "instrument_exclusion": instrument_exclusion(
                    candidate.instrument_type, candidate.name) is not None,
                "dates_first": candidate.first is None or candidate.first > c.start,
                "dates_last": candidate.last is None or candidate.last < c.end,
                "id_conflict": self._id_conflict(c, candidate),
                "interior_gap": self._interior_gap(c, candidate),
            }
            diagnostics[symbol] = {
                "price_symbol": symbol, "available": candidate.available,
                "response_state": candidate.response_state,
                "rejected_predicates": [k for k, rejected in predicates.items() if rejected],
                "no_acceptance_basis": False,
            }
        existing = [s for s in candidates.values() if s.available]
        base: dict[str, Any] = dict(record_id=c.record_id, constituent_symbol=c.symbol,
                    start=c.start.isoformat(), end=c.end.isoformat(),
                    candidates=tuple(sorted(candidates)),
                    candidate_diagnostics=tuple(diagnostics.values()),
                    failures={k: v["rejected_predicates"] for k, v in diagnostics.items()},
                    fuzzy_matches=tuple(sorted(fuzzy, key=lambda x: (-x["similarity_score"],
                                                                    x["price_symbol"]))))
        if not existing:
            return Resolution(**base, status=("empty_response" if candidates and all(
                                  s.response_state == "empty_response"
                                  for s in candidates.values()) else "no_candidates"),
                              resolved_security=None,
                              price_symbol=None, match_basis=None,
                              reason="No plausible readable price file in the captured store")
        eligible = [s for s in existing if not s.quarantine
                    and instrument_exclusion(s.instrument_type, s.name) is None
                    and self._dates(c, s) and not self._id_conflict(c, s)]
        live = [s for s in eligible if not archived_symbol(s.price_symbol)
                and s.price_symbol in spellings]
        archived_block = any(archived_symbol(s.price_symbol) and self._dates(c, s)
                             for s in symbol_candidates)
        accepted: list[tuple[Security, str, str]] = []
        for s in eligible:
            stable = any(value and s.price_identifiers.get(key) == value
                         for key, value in c.identifiers.items())
            matching_rules = [r for r in rules if r.price_symbol == s.price_symbol
                              and r.start <= c.start <= c.end <= r.end
                              and (not r.require_constituent_name or bool(c.name))
                              and all(s.catalog_identifiers.get(k) == v
                                      for k, v in r.expected_identifiers.items())
                              and (not c.name or not r.names or name in
                                   {normalized_name(n) for n in r.names})
                              and (not c.exchange or not r.exchanges or
                                   c.exchange in r.exchanges)]
            # Reviewed ticker reuse bounds must also constrain stable/name matches.
            if rules and not matching_rules:
                continue
            if archived_symbol(s.price_symbol) and not matching_rules:
                continue
            if stable:
                accepted.append((s, "stable_id", "Identifier present on constituent and price"))
            elif matching_rules:
                accepted.append((s, "manual", matching_rules[0].evidence))
        if (not accepted and not rules and len(live) == 1 and not archived_block
                and not self._interior_gap(c, live[0])):
            chosen = live[0]
            normalized = chosen.price_symbol != c.symbol
            basis = "normalized_symbol" if normalized else "unique_live_candidate"
            evidence = (f"Constituent {c.symbol}; lookup {chosen.price_symbol}; "
                        f"full catalog candidates "
                        f"{sorted(s.price_symbol for s in symbol_candidates)}; "
                        "uniqueness tested over full catalog including archived and quarantined "
                        "records; one eligible non-archived record and no date-eligible archive; "
                        "no gap over 200 calendar days intersects the membership window")
            accepted.append((chosen, basis, evidence))
        accepted_symbols = {item[0].price_symbol for item in accepted}
        for candidate in eligible:
            diagnostics[candidate.price_symbol]["no_acceptance_basis"] = (
                candidate.price_symbol not in accepted_symbols
                and not archived_symbol(candidate.price_symbol))
            if diagnostics[candidate.price_symbol]["no_acceptance_basis"]:
                diagnostics[candidate.price_symbol]["rejected_predicates"].append(
                    "no_acceptance_basis")
            if candidate.price_symbol in accepted_symbols:
                diagnostics[candidate.price_symbol]["rejected_predicates"][:] = []
        stable_matches = [item for item in accepted if item[1] == "stable_id"]
        if stable_matches:
            accepted = stable_matches
        if len(accepted) == 1:
            s, basis, evidence = accepted[0]
            return Resolution(**base, status="resolved", resolved_security=s.security_id,
                              price_symbol=s.price_symbol, match_basis=basis,
                              reason="Unique verified match", evidence=evidence)
        reason = (
            "Multiple acceptable price records; canonical selection requires review" if accepted
            else str(base["failures"])
        )
        return Resolution(**base, status="candidates_unmatched", resolved_security=None,
                          price_symbol=None, match_basis=None, reason=reason)

    def resolve(self, c: Constituent) -> Resolution:
        return require_resolved([self.audit_one(c)])[0]

    def resolve_all(self, constituents: Iterable[Constituent]) -> tuple[Resolution, ...]:
        return require_resolved(self.audit_one(c) for c in constituents)
