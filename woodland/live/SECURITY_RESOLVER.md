# Security resolver

This module resolves identity only. It does not ingest, repair, concatenate
prices, construct a panel, compute returns, fit, or promote anything.

`SecurityResolver.resolve()` and `resolve_all()` raise
`UnresolvedConstituents` on any unresolved input. A future panel consumer must
call `resolve_all()` (or `require_resolved()` on the entire saved resolution
table) before using any row. Audit methods retain failures solely to produce
diagnostic reports; filtering their output to successful rows is prohibited.
There is no panel builder in this change, so no existing builder is patched.

## Rules

* Only `Common Stock` catalog entries can be selected. Contradictory warrant,
  right, unit, preferred, note, and debenture names veto the provider label.
  Excluded catalog rows remain in a separate report. A constituent whose only
  candidate is excluded remains an unresolved input; it never disappears.
  The provider label is not a certification: cryptic or otherwise mislabeled
  instruments still require review, and there is no ticker-only acceptance.
* A stable identifier can establish a match only when present on both the
  constituent and the price-side identity record. EODHD's downloaded daily
  price schema has no such field; catalog ISINs are evidence and conflict
  checks, not a fabricated price-side identifier. Resolver-created IDs are
  not represented as provider-issued IDs.
* Otherwise acceptance requires an exact normalized company name, exchange,
  and the full requested date range inside the captured price range. Name
  normalization removes punctuation/case only, preserving share classes.
  A broad exchange code such as US is not silently equated with NYSE/NASDAQ.
* Reviewed manual rules have explicit dates, names, sources, and expected
  catalog identifiers where available. Rules also constrain generic matches
  so a backfilled modern ticker cannot bypass a historical reuse boundary.
* Fuzzy candidates at similarity >= 0.80 are reported with their scores;
  this is a review threshold, never an acceptance threshold. Candidate search
  uses shared name tokens/prefix blocks. It is a heuristic search and does
  not prove an absent company's data is unavailable worldwide.
* No suffix pattern is used to infer a relationship. `BBBY_old` is
  quarantined because its catalog identity contradicts the observed prices.
  It is not merged into BBBYQ or BBBY. WM and BBBY reassignments produce
  different security IDs; an input spanning identities fails rather than
  concatenating two series.

`no_candidates` means no plausible **readable** price file was in the captured
store; missing, unfinished, and changing files may cause this. Known catalog
candidate symbols are retained even if their files are missing.
`candidates_unmatched` means plausible files existed but no unique candidate
satisfied the acceptance rules. Its reason can be missing identity evidence,
instrument exclusion, date coverage, conflict, quarantine, or ambiguity.
Neither label establishes that the company is missing from the vendor itself.

## Run a diagnostic

```bash
.venv/bin/python -m woodland.live.resolver_audit \
  --store '<home>/Downloads/Woodland-EODHD' \
  --constituents /absolute/path/to/constituents.csv \
  --source-label 'Exact source and index of supplied membership' \
  --output reports/security-resolver/NEW-UNIQUE-RUN
```

CSV columns: `record_id,symbol,start,end,name,exchange` and optionally
`ISIN,CUSIP,FIGI`. Each row is a historical occurrence, not a globally unique
ticker: the same symbol may identify different securities in different
periods. Date bounds are inclusive identity-validation bounds, not a decision
about whether an index's removal date is inclusive. The membership owner must
define effective dates before a panel is built. End dates must be explicit.

The parser also accepts EODHD `HistoricalTickerComponents` JSON with
`Code,Name,StartDate,EndDate` and optional exchange/identifiers. Missing names,
exchanges, or identifiers are not filled with today's catalog information.
Missing/open end dates must be supplied explicitly in a separate input copy.

The old GitHub `date,tickers` CSV can be used only for diagnostics. It is
reduced to annual symbol observation envelopes, with first/last observed
dates, and cannot certify continuous membership. No names/IDs are invented.
Its counts are NOT the requested EODHD membership counts.

Each output directory is new and refuses overwrite. It includes a versioned
JSONL resolution table, fuzzy review queue, excluded instruments, annual
unresolved counts, and an input snapshot manifest. The manifest records
catalog/content hashes and file size/mtime/footer information; it is not a
full hash of every price value. Symbol lists and completed file names are
captured once, so later downloads do not alter that run. Inputs are opened
read-only. Re-run into another directory after ingest completes.

Exit code 2 means unresolved constituents remain, even though reports were
written successfully. `panel_ready` is always false: identity checks alone
do not validate membership, prices, corporate actions, or delisting proceeds.
All reported counts remain provisional until ingest completes.

## Resolver 1.1.0 — declared window and coverage inputs

The audit CLI clips membership diagnostics to 1999-01-05 through 2026-06-30
(inclusive). Supply `--coverage-input` pointing to the versioned
`midwindow-coverage.json` containing all 13 unresolved audit inputs. They are
preserved as typed records in the new resolution table and separately in
`coverage-inputs.json`. They block success even if the membership rows resolve.
This version does not accept imported claims of verified coverage; identity
and effective membership evidence must be reviewed before promotion and
materiality recomputation. No proxy ratio is promoted to verified materiality.

All `_old` and numbered `_old` price locators are ineligible, including when
names or identifiers match. They remain visible in exclusion diagnostics;
constituents referencing them still require another verified candidate or
produce a refusal. No price files are deleted and no suffix alias is invented.

Annual unresolved columns are `no_candidates`, `candidates_unmatched`, and
`empty_response`. The last means all plausible candidates have confirmed
zero-row parquet responses. Missing, corrupt or changing files are not
claimed to be empty responses. A readable acceptable candidate takes priority
over an empty alternative. The annual table counts unique symbols per status,
so a symbol with multiple failing occurrences may appear in multiple columns.

WM's stored history is Waste Management; WAMUQ is a separate security. The
historical meaning of the constituent ticker WM still depends on its dates
and identity. Continuous prices do not establish which company a historical
symbol-only membership record meant. BBBY and BBBYQ remain separate.

## Resolver 1.2.0 (supersedes 1.1.0 archive policy)

Constituent dot spellings are normalized to dash for lookup only. Base `_old`
and numbered archives now participate in the full candidate search. They are
never accepted by unique_live_candidate or normalized_symbol. Reviewed manual
rules remain necessary for archived acceptance in this implementation.

The declared unique-live rule accepts one eligible non-archived literal or
normalized candidate only if no date-eligible archive exists anywhere in that
symbol's full catalog family, including quarantined records. It is a fallback
for symbol-only input, never overrides a supplied conflicting name, and does
not bypass existing manual ticker-reuse constraints. Full _dates containment
is unchanged. Normalized acceptance records normalized_symbol and both spellings.

Each resolution includes failures keyed by candidate locator, splitting
 dates_first and dates_last; archived means blocked from automatic acceptance.
The review packet retains candidates and per-occurrence failures. Its catalog
names and suggested verdicts are not constituent identity enrichment or approval.
See the versioned report README for the human approval import command. That
command must be invoked explicitly after review; this audit never invokes it.

## Resolver 1.3.0 (supersedes catalog-name criteria)

Catalog Name is display-only. It no longer supplies exact-name acceptance,
fuzzy candidate lookup, a manual catalog-name check, or an instrument-name
veto. Instrument Type remains authoritative to the extent of provider quality;
mislabeled common-stock records cannot be detected from their slot names.

Archived constituent-candidate files split at interior gaps strictly greater
than ARCHIVED_SPLICE_GAP_DAYS=200 calendar days. Only split files get distinct
`::segmentN` locators; every inspected candidate carries 1-based segment_index,
source storage symbol and its raw-bar evidence. A split is a conservative
boundary, not proof of corporate identity. Full date containment applies per
segment, and no ticker-based automatic acceptance of archives is permitted.
The same detector scans live records but does not split or reject them.

Median volume and closing-price evidence are segment-local. Terminal volume
is compared to the median of up to 60 preceding bars, excluding the terminal
bar; a missing/zero median gives no ratio. Price suggestions are reviewer hints
under the declared heuristics, never applied rules. Segment-specific human
approvals must cite that segment locator and stay within its bounds. No approval
import has been run. Past journals and report versions remain unchanged.
