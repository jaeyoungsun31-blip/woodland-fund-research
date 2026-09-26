# 2026-09-05 — Free equity data acquisition audit

Append-only engineering/data-quality record. User requested investigation of
free sources, with implementation conditional on quality. No strategy was
evaluated, no signal fitted, no gate amended, no incumbent changed, and no
trial-ledger records were required. This does not reopen a research family.

## Decision

**No source is approved for the stock-level momentum harness in this audit.**
WIKI and Dolt are accessible but have unresolved coverage/identity/terminal-
return gaps. The GitHub membership file is useful reference material, not a
complete security master. Engo's actual data could not be inspected without a
free-account key. Therefore no production adapter or source switch was made.
This is not a finding that free data is unusable; it is a finding that the
examined sources do not yet meet the requested use.

Intended grain: one identified security per trading date, with historical
eligibility, total returns, and auditable treatment of corporate actions and
terminal holdings. Prices for some delisted tickers alone do not establish a
survivorship-complete universe.

## Baseline verification

`.venv/bin/python -m pytest -q`: 404 passed, 1 failed, 1 skipped, 85.07s.
Existing failure: `test_real_universes_realise_their_journalled_shape[etf]`,
5,502 bars / 22 folds versus frozen 5,499 / 22. No baseline was changed or
test weakened. Audit was limited to data coverage and source access, with no
strategy performance calculations. No executable project files changed.

## Direct observations

### Quandl WIKI, Kaggle mirror — not approved

Source: https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites

An unauthenticated download returned HTTP 200 and a real ZIP. Downloaded and
profiled the complete archive, not just its description: 463,184,323 compressed
bytes; `WIKI_PRICES.csv`; 15,389,314 rows; 3,199 ticker strings; dates
1962-01-02 through 2018-03-27. Those dates describe the entire archive, not
continuous history for all names. One row has a missing key or adjusted close;
zero nonpositive non-null adjusted closes. This is not a full price audit.

Archive SHA-256:
`adfd226694c6f3ec2c56b585d973764180a39a3ec516601721e90096dc1de94f`.

No ticker records for ENE, ENRNQ, LEH, LEHMQ, or MTLQQ. GM starts
2010-11-18 and cannot be substituted for the pre-bankruptcy issuer. SIVB
history ends in 2018, before the bank's failure; TWTR history also ends in
2018, before its acquisition. Their presence therefore does not validate
terminal-event accounting. The mirror's metadata labels its license Unknown.
Nasdaq's original unauthenticated sample endpoint returned 403, QEPx04,
requiring a valid API key.

Exact-ticker joins to the downloaded membership reference:

| As-of | Members | Absent ticker labels | Present label, date outside history |
|---|---:|---:|---:|
| 2000-01-03 | 491 | 176 | 21 |
| 2008-09-15 | 498 | 62 | 10 |
| 2013-02-28 | 497 | 13 | 10 |
| 2017-12-29 | 505 | 6 | 3 |

These are **unresolved joins**, not proven missing-security counts. Alias,
punctuation, and vendor symbol conventions explain some. Neither dropping
them nor mapping them to today's same-named security is acceptable.
High severity for the intended use; high confidence in observed counts,
unresolved attribution between alias problems and genuinely missing history.

### fja05680/sp500 — reference only

Source: https://github.com/fja05680/sp500

Pinned commit `c31ac3cc56f28cf9a02b4e694eff7ceab596a0ff`, file
`S&P 500 Historical Components & Changes (Updated).csv`.
SHA-256 `39a9202c9ef69a74c0ff07e2113ad41fb6da7c8c5b6cd9541f0185fb4391e717`.

2,718 rows; columns date/tickers; 1996-01-02 through 2026-06-30;
1,206 distinct ticker strings; 487–507 members per row. No null cells,
invalid dates, duplicate dates, or within-row duplicate tickers; dates sorted.
Rows are snapshots, not a complete daily price calendar. Structural checks
pass, but independent membership completeness and announcement timing have
not been established. The maintainer warns of early-history omissions.

The 2000 snapshot uses ENRNQ, LEHMQ and MTLQQ labels. The 2022-06-01
as-of snapshot uses FB, and 2022-06-10 uses META. Thus labels require a
vendor-aware identity crosswalk; they are not universally usable historical
exchange tickers. An as-of membership loader alone would not close this gap.

### DoltHub post-no-preference/stocks — not approved

Source: https://www.dolthub.com/repositories/post-no-preference/stocks

Public SQL API returned HTTP 200, without credentials. Tables: ohlcv,
symbol, dividend, split. Direct boundary queries: 2011-01-03 through
2026-09-04; 24,107 symbol-table rows. A 2008-09-15 price count is zero.

Retains TWTR's 2022-10-27 bar and SIVB's 2023-03-09 bar. This is useful
pre-delisting evidence, not proof of final acquisition payouts or post-failure
recoveries. Symbol canaries found neither ENE/ENRNQ, LEH/LEHMQ nor MTLQQ.
Current FB metadata identifies a ProShares ETF, while the GitHub history
uses FB for Facebook. This proves a naive ticker join would mislabel history;
it does not prove Dolt's OHLCV itself splices those issuers.

Schema keys are `(date, act_symbol)` for prices and `act_symbol` for metadata.
No dated security-identity crosswalk or explicit terminal-return field was
exposed in inspected schemas. The OHLCV table has no adjusted-close column;
its adjustment basis needs verification before computing total returns.

Queries ran on master. Latest observed commit was
`unao90dumct6975p9871nv0l0furtr4m`; attempting that hash as API ref returned
400. The responses are retained, but the successful queries are not claimed
to be an immutable snapshot. Broad aggregate/range requests also timed out;
small indexed-date queries succeeded.

### Engo — access blocked, quality unverified

Source and specification: https://engo.capital/wiki

Both `/api/v1/lake/coverage` and the ENRNQ history endpoint returned 401,
requesting authentication. No ENGO_API_KEY was present in the process
environment; `.env` was not read. Asked user whether they have a free account;
no account was created and no key was requested in chat.

Provider disclosures remain unverified: historical archive frozen at
2026-08-04, separate listed-only forward feed, incomplete action coverage,
raw OHLC alongside adjusted close, and limited reliable membership history.
These disclosures prevent approving it on marketing claims alone.

## Evidence and next step

Local temporary audit bundle: `/tmp/woodland-free-data-audit/` contains the
downloaded WIKI ZIP, membership CSV, hashes, profiles, exact SQL response
JSONs, and `audit.ipynb` / `compare.py`. These are temporary audit artifacts,
not production inputs. No market data is added to git.

Next useful step: authenticate Engo with a user-owned free account and audit
actual security identities, price histories and terminal events. If that
fails, repairing the public-source identity/coverage gaps is a separate data
engineering project, not a safe automatic import. No thresholds or frozen
research windows should be loosened to make a source pass.
