# Security resolver only — 2026-09-06

Read first: `2026-09-06-planning-decision-revive-v16-on-constituent-data.md`
and `2026-09-03-xsmom-v16-costaware-preregistration.md`. This implements the
user's resolver-only instruction, not execution of the revived study. No
panel, fit, strategy result, terminal-return calculation, or promotion was
produced. No ingest code was changed or run; both project `data/` and the
download folder were opened read-only. No trial was evaluated or ledger row
written. Planning still owns the index/window and membership effective-date
conventions before any future study.

## Implementation

`woodland/live/security_resolver.py` (version 1.0.1),
`woodland/live/resolver_conventions.json` (version 2026-09-06.2), and
`woodland/live/resolver_audit.py` implement the resolver, reviewed mappings,
and a read-only store audit. Usage and limits are documented in
`woodland/live/SECURITY_RESOLVER.md`.

Strict `resolve`/`resolve_all` and `require_resolved` raise on unresolved
inputs. There is no skip/default route. The diagnostic CLI records every
failure before exiting with code 2. A future panel builder must consume the
strict interface; no panel builder was created or modified here.

Each table row represents a dated historical symbol occurrence. A ticker is
not a unique global key. Fuzzy suggestions include similarity scores and are
also emitted separately; none is accepted automatically. A stable-ID match
requires the identifier on the constituent AND price-side identity record.
The current EODHD daily files have date/OHLC/adjusted_close/volume only, so
symbol-list ISINs are not fabricated into a price-side ID. Catalog IDs can
veto a contradiction, and reviewed local IDs distinguish known entities.
Fallback acceptance requires exact normalized name, exchange, and date
coverage, or an explicitly sourced manual rule. Multiple acceptable files
remain ambiguous; no automatic concatenation is performed.

## Instrument classification

The symbol-list endpoint exposes `Type` and `Isin`. Both downloaded lists
were requested with `type=common_stock`: 17,954 active and 32,910 delisted
records, all labelled `Common Stock`. That label alone is insufficient.
For example, the live search endpoint returns BBBYW as Common Stock with
the name "Neighborhood Intelligence, Inc. Warrants", and BBBY-WT as Common
Stock with the name "BBBY-WS".

The resolver requires the Common Stock label and vetoes contradictory
warrant/right/unit/preferred/note/debenture descriptions. It flags **1,492
catalog records** under this conservative rule. This count is a classification
flag count, not independent verification that every flagged instrument is a
derivative. Unknown types are excluded. Cryptic mislabeled instruments can
still require investigation; no ticker-only acceptance is permitted.
Excluded catalog rows are reported; an input constituent with only excluded
candidates fails rather than disappearing.

## Supersession findings

The three BBBY-family records demonstrate why neither suffixes nor catalog
ISIN alone can be trusted:

| Provider code | Catalog ISIN | Observed price range |
| --- | --- | --- |
| BBBY | US6903701018 | 2002-05-30–2026-09-04 |
| BBBYQ | US0758961009 | 1992-06-05–2023-09-29 |
| BBBY_old | US0758961009 | 2002-05-30–2025-08-29 |

BBBY_old has **5,762 identical raw closes across 5,851 overlapping dates**
with BBBY, but only **2 identical closes across 5,371 overlapping dates**
with BBBYQ. It appears to serve the newer entity's history while its catalog
identifies the bankrupt company. This is an identity contradiction, not an
approved provider link. BBBY_old is **quarantined**, not merged into either
entity and not repaired. Separate evidence records the comparison and file
hashes. General fundamentals metadata could not be checked: HTTP 403.

Original BBBY constituents resolve to BBBYQ over the reviewed pre-suspension
range. BBBYQ remains the original entity's archived label. New BBBY is
accepted under that historical ticker only from **2025-08-29**, even though
its backfilled series begins in 2002. Reviewed rules check both target names
and expected ISINs. A later contradictory catalog change causes refusal.
Issuer evidence:
[2023 Nasdaq suspension](https://www.sec.gov/Archives/edgar/data/886158/000119312523115523/d89202dex991.htm),
[2025 reassignment](https://investors.beyond.com/news-events/press-releases/news-details/2025/Beyond-Inc--Changes-Name-to-Bed-Bath--Beyond-Inc--and-Reclaims-Ticker-Symbol-BBBY/default.aspx).

LEH is archived as LEH (1997-12-31–2008-09-17 in the captured file), and
Enron is ENRNQ (1997-12-31–2004-11-17). ENE→ENRNQ and WM→WAMUQ are explicit
reviewed identities, not suffix transformations. Enron identity evidence:
[GAO report](https://www.gao.gov/pdf/product/new-items-d03138).
Waste Management's WM reassignment was **2009-08-05**, per its
[issuer announcement](https://investors.wm.com/news-releases/news-release-details/waste-management-announces-ticker-change-wm/).
Washington Mutual's WAMUQ cancellation is documented in its
[2012 filing](https://www.sec.gov/Archives/edgar/data/933136/000090951812000125/mm03-2312_8ke995.htm).
WM and WAMUQ files were not yet in the captured store; their resolver cases
pass on constructed fixtures, not a claim of completed real-file coverage.

The provider's symbol-change endpoint returned **403**. Its
[documentation](https://eodhd.com/financial-apis/us-stock-symbol-rename-history-api)
limits access to Extended/All-in-One and history to 2022-07-22 onward. It
cannot supply the old Enron/Washington Mutual transitions even with an
upgrade. No entitlement was changed or bypassed.

## Provisional snapshot and reports

Input folder: `<home>/Downloads/Woodland-EODHD`.
The captured file inventory has **27,916 readable parquet files**; 22,948
catalog symbols have no file in that snapshot. Later additions do not alter
these counts. The code reads completed-file footers and records file
size/mtime/date bounds. It does not hash every price value or certify price
integrity. Catalog hashes and membership input hash are recorded.

**No EODHD historical constituent export exists in that folder.** Its JSON
files are the active and delisted symbol catalogs, not dated index membership.
The historical membership API probe also returned 403. Therefore actual
EODHD unresolved-constituent counts are **unavailable, not zero**.

For a clearly labelled diagnostic only, the earlier GitHub fja05680/sp500
symbol-only CSV was checked. It contains no constituent names or IDs, so
the resolver correctly refuses ticker-only matching. Annual symbol
observation envelopes are used to keep the output small; these are not
continuous membership intervals or a substitute for EODHD membership.

Across **16,180 symbol-year diagnostic rows** (1996–2026):

* **23 resolved**, through reviewed rules.
* **7,237 no_candidates**: no plausible readable file in the snapshot;
  incomplete downloading is one possible cause.
* **8,920 candidates_unmatched**: files exist but do not satisfy the rule,
  including missing name/exchange evidence in the symbol-only input. These
  are diagnosable failures, not a count of missing companies at EODHD.

All counts are **provisional until ingest completes**. No unresolved input
was dropped. Annual per-symbol counts can exceed 500 because they include
all names observed during a year, not one date's membership.

Final local outputs (ignored, not committed market data):

* `reports/security-resolver/2026-09-06-v2-github-provisional/resolution.jsonl`
* `reports/security-resolver/2026-09-06-v2-github-provisional/annual-unresolved.csv`
* The same directory includes the manifest, summary, excluded instruments,
  fuzzy review queue, BBBY conflict evidence and metadata access results.
* `eodhd-membership-status.json` explicitly records unavailable EODHD counts.

Version 2 replays the same captured price-file snapshot with hardened manual
rules; version 1 is retained, not overwritten. Final snapshot hash:
`c7eb530cb3b8e58c332b86bcb28632001815da41b49c54223582c697b3265da9`.

## Validation and remaining boundary

**53 resolver tests pass**, covering the BBBY family and quarantine, WM reuse,
LEH/Enron aliases, instrument exclusion, both failure categories, identifier
conflicts, fuzzy nonacceptance, ambiguity, read-only incomplete-store handling,
and append-only output versions. Ruff and mypy pass for the new modules.

Full pytest before changes: 404 passed, 1 failed, 1 skipped. Final full run:
**459 passed, 1 failed, 1 skipped**. The same existing ETF realized-shape
failure remains: 5,502 bars versus frozen 5,499, with 22 folds in both.
The workspace changed concurrently; the new resolver's isolated count is
53. No existing test or frozen expectation was weakened. No commit was made
with a failing baseline. Unrelated changes, including a concurrently added
downloader script, were left alone.

Actual EODHD constituent resolution awaits a dated membership export with
identity evidence. The download need not finish for diagnostic use, but
neither these provisional counts nor fixture successes authorize a panel.
