# Planning review — the resolver has no automatic acceptance path

Date: 2026-09-06
Status: finding (blocking)
Artifact reviewed: `reports/security-resolver/2026-09-06-v6-resolver/` (resolver 1.1.0, conventions 2026-09-06.3, snapshot 22e03b4a…)

## Reported result

| status | rows |
|---|---|
| resolved | 48 |
| no_candidates | 418 |
| candidates_unmatched | 14,169 |
| empty_response | 0 |
| (coverage rows, separate shape) | 13 |

## Finding

The 14,169 are not a residual to adjudicate and not a threshold to tune. The
matcher cannot accept anything from this constituent source.

Measured, not inferred:

1. **All 48 resolved rows have `match_basis = "manual"`.** Zero resolved via
   `stable_id`, zero via `exact_name`. The 48 are the mechanical product of the
   8 hand-written rules in `woodland/live/resolver_conventions.json`.

2. **14,167 of 14,169 unmatched rows have exactly one candidate** (2 have two;
   1,064 distinct symbols single-candidate, 1 multi). This is not ambiguity.

## Root cause

`SecurityResolver.audit_one` offers three acceptance bases. Against this
constituent source, two are structurally unreachable:

- `resolver_audit.py:155` builds the GitHub symbol-only constituents as
  `Constituent(f"{year}:{symbol}", symbol, min(dates), max(dates))` — no `name`,
  no `exchange`, no `identifiers`.
- `exact_name` requires `name and c.exchange and bool(c.exchange)`. Never true.
- `stable_id` requires `c.identifiers` non-empty. Never true.
- `manual` is therefore the only live path. 8 rules → 48 rows.

A second defect sits behind the first and would survive a fix to it:

- `resolver_audit.py:127` stores the EODHD catalog ISIN in
  `catalog_identifiers` and sets `price_identifiers={}`.
- The `stable` predicate reads `s.price_identifiers.get(key)` — always empty.
- `_id_conflict` reads `catalog_identifiers`.

So ISIN is currently wired to **reject** a candidate and never to **accept**
one. Supplying constituent ISINs alone would not raise the match rate; it would
only add rejections.

A third defect is latent and will bite the population this exercise exists to
capture:

- `_dates` requires full containment `s.first <= c.start <= c.end <= s.last`.
- An annual membership record for a name delisted mid-year has `c.end` beyond
  `s.last`, and is rejected. Delisted constituents fail preferentially.
- Truncating membership at the delisting date is a convention that must be
  declared, not a matcher parameter to loosen.

## Diagnostic defect

`reason` for every unmatched row is the static string "Existing candidates
failed identity, instrument, date, or quarantine rule". It does not record
*which* predicate failed, and it does not distinguish "candidate failed
eligibility" from "candidate was eligible but no acceptance basis exists". Had
it recorded the failing predicate, the 0.33% rate would have been legible on
first read. Per-predicate failure attribution is a required output of the next
run.

## What is NOT the fix

Accepting a bare ticker match reintroduces exactly the contamination the
resolver exists to prevent (BBBY/BBBYQ, WM/WAMUQ). Enriching the symbol-only
list with names looked up **by that same ticker** from the EODHD catalog is
circular: it adds no independent identity evidence and would launder a ticker
match into an apparent name match.

## Standing constraints unaffected

The resolver correctly refused panel use (`panel_ready: false`,
`identity_resolved: false`). No panel was built, no price data changed. The
rule "an unresolved constituent is a refusal, not an omission" held.

## Open, unsigned

- Constituent source with independent identity (names, dates, ideally ISIN).
- Whether `unique_catalog_candidate` becomes a declared fourth acceptance basis,
  with uniqueness tested over the **full** catalog including archived and
  quarantined records, and multi-candidate symbols routed to review.
- Delisting truncation convention for `_dates` (relates to A2).
