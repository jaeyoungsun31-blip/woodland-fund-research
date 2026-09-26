# A4 coverage-boundary amendment and constituent diagnostic — 2026-09-06

User-directed amendment, recorded before any panel or fit. This supplements
the revival decision's A4 membership leakage test; it does not remove that
test or alter either frozen perturbation requirement.

## Declared rule

The panel start date is set after the last vintage cliff that materially
affects the constituent universe, determined by measurement rather than by
the vendor's overall distribution. Every result reports, per year, the count
of constituents whose history is truncated by a vendor coverage boundary
rather than by their actual listing date. A year in which that count exceeds
a declared threshold is reported as coverage-limited and excluded from the
primary comparison.

The user has not yet specified the materiality cutoff or annual exclusion
threshold. Both remain UNSET, and no final panel start or year exclusions
have been selected. A clarification was requested. No return or performance
results may be used to choose them. The earlier 1998 minimum is not evidence
that 1998 provides adequate constituent coverage.

The annual counting definition (membership overlap, needed feature-history
window, unique security count and denominator if a percentage is used) must
also be fixed before application. An early historical truncation does not
automatically imply missing required history in every later membership year.
Unresolved identities or unknown listing dates are unknown, not zero missing
coverage. The resolver's no-drop refusal remains binding.

## Available evidence and scope

No EODHD point-in-time index membership export is present. The available
GitHub S&P 500 symbol-only diagnostic has 1,206 unique historical symbols
and 16,180 symbol-year records: 50 resolved, 578 no_candidates, and 15,552
candidates_unmatched. Only four distinct price symbols have an accepted
resolution for at least one record. Thus a valid complete ever-constituent
security distribution cannot yet be calculated. No symbol-only match was
silently accepted to manufacture that universe.

For diagnosis only, collected the union of existing candidate price symbols
and accepted resolutions from the completed-download resolver output:
1,117 common-stock histories, including 408 in the delisted catalog. These
are potential matches, not 1,117 verified index constituents. Symbol reuse
and omitted renamed candidates can bias this diagnostic in both directions.

| Candidate start date | All candidates | Delisted candidates | Catalog exchanges (all candidates) |
| --- | ---: | ---: | --- |
| 1997-12-31 | 156 | 156 | NYSE 112; NASDAQ 33; OTCMKTS 7; OTCBB 3; NYSE MKT 1 |
| 1999-01-04 | 16 | 16 | NYSE 9; NASDAQ 7 |
| 2003-09-10 | 9 | 9 | NYSE 6; NASDAQ 3 |
| 2016-01-04 | 4 | 4 | NYSE 2; NASDAQ 1; PINK 1 |
| 1980-03-17 | 100 | 13 | NYSE 78; NASDAQ 21; NYSE MKT 1 |
| 1984-11-05 | 38 | 12 | NYSE 33; NASDAQ 3; NYSE MKT 1; OTCQB 1 |
| 1973-02-21 | 30 | 1 | See full distribution for the delisted count verification |

Start-date pile-ups indicate suspected coverage cliffs, not confirmed
truncation of each record. Independent listing or pre-boundary trading
evidence is needed to distinguish IPO starts. Exchange labels are current
or terminal catalog metadata, not reconstructed exchange at the cliff.
The strictly resolved subset contains ENRNQ and WAMUQ at 1997-12-31,
BBBYQ at 1992-06-05 and WM at 1988-06-22; it is too incomplete to choose a
coverage boundary or estimate universe shares.

Full exact-date distributions and exchange counts for all candidates,
delisted candidates, and the incomplete resolved subset are saved under
`reports/security-resolver/2026-09-06-constituent-cliffs-provisional/`.
`annual-coverage-status.csv` preserves every source year with resolution
counts and marks confirmed truncation and coverage status unknown, rather
than fabricating annual values. `candidate-history-bounds.csv`,
`summary.json`, and `reproduce.py` preserve the diagnostic method. Source is
the version-3 completed-download resolver manifest and resolution table.
Data and ingest remain untouched; no panel, model, study or exclusions ran.
