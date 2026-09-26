# Resolver 1.1.0 windowed audit — 2026-09-06

Implemented the user's latest resolver instructions without building a panel,
changing prices, rerunning ingest, fitting, or excluding constituents.

All 1,632 `_old`/numbered `_old` price locators are ineligible, even for exact
name or stable-identifier matches. Files remain untouched and exclusions are
reported; an affected constituent still needs a verified alternative or fails.
This is a user-directed exclusion policy, not a blanket assertion that all
archived OHLCV series were proven identical. The BBBY price/metadata conflict
remains documented in the earlier audit; no automatic suffix alias is created.

WM's stored 1988–2026 history is Waste Management per user verification, while
WAMUQ is Washington Mutual. This does not erase historical constituent-symbol
ambiguity: a symbol-only WM observation before its documented ticker change
cannot be assigned to Waste Management solely because today's WM file has
backfilled prices. Existing date-sensitive identity tests remain unchanged.
BBBY and BBBYQ remain distinct; no series is concatenated.

Window: **1999-01-05 through 2026-06-30 inclusive**. The CLI requires all 13
mid-window coverage inputs, preserves them in the new table and a separate
input artifact, and blocks use while they remain unresolved. It does not
accept an imported clean classification as verification. Real materiality
remains unknown pending identity and effective membership evidence; the prior
symbol-day proxy is not promoted. The include-from-data-start decision applies
once a security and its membership are verified, never by dropping a name.

Completed read-only run:
`reports/security-resolver/2026-09-06-v6-resolver/`

* 14,635 windowed membership observation records.
* 48 resolved; 418 no_candidates; 14,169 candidates_unmatched; 0 empty_response.
* 14,587 unresolved membership records cause CLI exit 2.
* All 13 additional coverage identity inputs remain unresolved and independently
  block success. They are not counted as 13 additional unique constituents.

Annual report: annual-unresolved.csv, split by the three failure modes.
Empty response specifically means confirmed zero-row parquet for all plausible
candidates; missing/corrupt/changing files are not invented empty API responses.
No network call was made. Historical membership remains the GitHub symbol-only
proxy, not an EODHD security-linked export, so counts remain provisional as
identity evidence. Download completion does not settle those identities.

Validation: 58 resolver tests pass; Ruff and mypy pass for changed resolver
modules. Existing tests were preserved. The baseline full suite fails the
pre-existing ETF realization assertion (5502 bars versus frozen 5499); no
attempt was made to weaken it or modify that unrelated measurement path.
No commit made while the full suite is not green.
