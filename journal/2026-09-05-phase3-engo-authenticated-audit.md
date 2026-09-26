# Engo authenticated data audit — 2026-09-05

Follow-up to the free-equity-data audit. User authorized read-only testing
with an Engo key. Authentication succeeded (account endpoint HTTP 200).
No credential is recorded here. No study, fit, promotion, or order occurred.

## Decision

Do not integrate Engo as the constituent research source yet. Authentication
is resolved; completeness, identity mapping, and terminal-return treatment
are not. This is a data-quality decision, not a strategy performance result.

## Observed responses

Evidence: `/tmp/woodland-free-data-audit/engo-20260905T234901981470Z/`,
including request manifest, sanitized responses, and `local-profile.json`.
Read-only collector: `/tmp/woodland-free-data-audit/audit_engo.py`.
These are temporary local artifacts, not committed market data.

* Coverage reports EODHD-derived adjusted closes, 101,394,171 us_eod rows,
  2000-01-03 through 2026-08-04. Separate native datasets advertise later
  dates; their compatibility with us_eod has not been validated.
* Membership audit reports 188 members in June 2000 and 266 in June 2008.
  Strict 2008 membership returned HTTP 422 for incomplete history. The
  earliest sampled date passing the provider's 450-member floor is
  2018-06-30 (452). Passing that count is not proof of correct membership.
* ENRNQ supplies 1,226 bars through 2004-11-17; TWTR supplies 2,259 through
  2022-10-27. Their corporate-action endpoints returned 404. Final trading
  prices do not establish terminal proceeds or cancellation treatment.
* SIVB stops 2023-03-09; SIVBQ extends through 2024-11-07, and includes
  overlapping earlier history. They cannot simply be concatenated or
  counted as independent securities. Provider quality flags a large
  March 2023 change in SIVBQ; classification requires event verification.
* META includes history from 2012; FB starts 2025. Historical ticker joins
  therefore require an identity crosswalk, not literal current labels.
* LEHMQ and MTLQQ exact labels returned no prices. Alternate labels and
  company identities remain unresolved; this is not proof that all history
  for those companies is absent. GM starts at the 2010 IPO.
* IEF begins 2010-01-04 in this dataset, so it cannot replace the existing
  ETF store over the full frozen window.
* Nine returned price series contain no duplicate dates or null/nonpositive
  closes. This limited check does not validate calendar completeness,
  adjustment accuracy, delisting returns, or the whole universe.
* Provider quality explicitly identifies raw OHLC alongside adjusted close.
  An adapter would need to preserve that distinction. Close outside the
  raw daily range alone does not establish bad adjusted returns.

## Remaining conditions before integration

Resolve stable security identities and ticker reuse; validate historical
membership against an independent source; establish terminal proceeds and
corporate-action treatment; cross-check aligned adjusted returns under the
existing frozen tolerances. Do not silently merge native and historical
datasets or fill missing securities with surviving names.

No executable repository changes were made. The previously observed test
baseline remains a known issue: ETF realized-shape test reports 5,502 bars
versus frozen 5,499 (22 folds in each), with 404 passed and 1 skipped. No
threshold or test was changed, and no research performance was inspected.
