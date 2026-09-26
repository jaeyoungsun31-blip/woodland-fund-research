# Archived `_old` symbol comparisons — 2026-09-06

Read-only audit of the completed local EODHD store. No ingest, resolver
mapping, panel, model, or existing journal was changed.

Examined all 1,632 catalog symbols containing `_old` (including numbered
variants). Candidate comparisons used equal nonempty ISIN, equal company
name after lowercasing/removing punctuation, or the unsuffixed symbol.
The last criterion generates a comparison only, never an identity mapping.
This is not an exhaustive all-pairs price search or proof that no other
counterpart exists. No fuzzy candidate search was performed.

There were 1,591 candidate pairs covering 1,250 archived symbols; 382 had
no candidate by those rules. In total 1,143 archived symbols had no candidate
with overlapping dates (including the 382 without candidates). Only eight
had a candidate reproducing every archived date's raw OHLCV to absolute
tolerance 1e-8, relative tolerance zero. This is duplication of stored bars,
not automatic proof of shared security identity; no merges were accepted.

BBBY_old contradicts the proposed equivalence to BBBYQ:

| History | Start | End | Bars |
| --- | --- | --- | ---: |
| BBBY_old | 2002-05-30 | 2025-08-29 | 5,851 |
| BBBYQ | 1992-06-05 | 2023-09-29 | 7,888 |
| BBBY | 2002-05-30 | 2026-09-04 | 6,107 |

BBBY_old and BBBYQ share catalog ISIN US0758961009, but only **2 of 5,371**
overlapping raw closes match; zero adjusted closes or complete OHLCV rows
match. BBBY_old versus BBBY (different ISIN US6903701018) matches **5,762 of
5,851** raw closes (98.48%), 1,972 adjusted closes, and 130 complete OHLCV
rows. Therefore BBBY_old is neither an interchangeable BBBYQ price series
nor an exact duplicate of BBBY. Its catalog identity conflicts with its
observed prices, and its existing resolver quarantine remains appropriate.

Artifacts under `reports/security-resolver/2026-09-06-old-comparison/`:
`comparisons.csv` records names, ISINs, date ranges and raw/adjusted match
counts for every candidate pair; `old-symbol-summary.csv` includes every
archived symbol, including those without candidates. `summary.json` and
`reproduce.py` preserve counts and the method. Run the script from the
project root with a fresh output directory. Counts describe provider
records, not deduplicated economic securities. Lack of price overlap is
inconclusive about identity, and neither suffix nor name alone proves it.
