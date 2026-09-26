# Resolver 1.3.0 segmentation and evidence declaration — 2026-09-06

Read planning-review-v7-packet-and-catalog-name-defect before implementation.
The earlier MOB/RAL name counterexamples are withdrawn. Catalog Name is display
context only: remove name-based matching, manual catalog-name checks, fuzzy
catalog-name lookup and name-based instrument vetoes. Provider Type and existing
ID/date/quarantine checks remain. This means mislabeled Common Stock records
cannot be vetoed by their unreliable names; record this limitation explicitly.
No names or identifiers are copied into the constituent source.

ARCHIVED_SPLICE_GAP_DAYS = 200 calendar days, strict greater-than. Scan sorted
unique price dates. Split archived candidate files at every qualifying interior
gap; use independent 1-based segment candidates with their own bounds and bar
evidence. No concatenation or acceptance based on segmentation. Scan all live
catalog files with the same detector but do not change their candidacy. A long
gap is a segmentation safeguard, not independently proven corporate identity.

Price evidence uses raw close and volume. VOLUME_REFERENCE_BARS = 60: median
of up to 60 previous bars within the segment, excluding its terminal bar.
Record actual reference-bar count; missing/zero denominator yields null ratio.
All-file median volume is computed within each candidate segment only.

Suggestions only, never applied: reject/high if no unresolved membership
window has any overlap with the segment; otherwise unknown/low unless the
segment contains all pending source windows, has at least 61 bars, first/last
raw closes in [1, 10000], median volume at least 100000 shares, positive terminal
volume, and terminal/reference volume ratio in [1,100]. Those conditions produce
accept/medium (price pattern compatible, not verified identity). Constants are
review heuristics, not acceptance criteria or large-cap identity tests. Price
levels outside these ranges never prove wrong identity and stay unknown/low.
State actual terminal date/close/volume/reference median and missing evidence.

Archives still require an explicitly verified manual basis. Full containment
is unchanged, all unresolved constituents refuse use, 13 coverage inputs remain
unresolved, and live gaps are report-only. No panel, backtest, price changes,
web lookup, approval ingestion, git add or commit.
