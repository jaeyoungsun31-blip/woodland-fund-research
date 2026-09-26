# Correction: the Tiingo cross-check covered 430 of 947, not 947

Date: 2026-09-07
Status: correction to coverage reported in an entry written the same day; that
entry stands unedited
Corrects: `2026-09-07-phase3-tiingo-panel-crosscheck.md`, which reported partial
coverage of 204 and is superseded on coverage only
Artifacts: `reports/security-resolver/2026-09-07-tiingo-crosscheck/`

The run completed over all 947 automatically resolved locators. **It compared
430 of them.** 473 were recorded as having no Tiingo series, and most of those
are not absences — they are throttle responses this script misclassified.

## The defect

The vendor caps requests in two message forms. One is prose:

    Error: You have run over your hourly request allocation.

The other is JSON:

    {"detail": "You have run over your 50 ..."}

The script carried a list of throttle phrases — `allocation`, `rate limit`,
`too many requests`, `429`, `over your hourly`, `over your daily` — and matched
the first form. It matched nothing in the second. Once the run crossed into the
JSON form it began writing empty cache sentinels and recording symbols as having
no series. **470 sentinels were written.** Among the symbols so recorded are
`BK`, `EQR`, `GPS`, `ULTA`, `AAL` and `MMC`, all of which the vendor plainly
carries.

## Why the earlier fix did not hold

This is the second firing of the same class. The first was in the adjudication
script, where matching only the word "limit" turned a rate limit into 19
findings of "no third source". The fix then was to widen the phrase list, and
that was the wrong shape of fix: **enumerating the ways a vendor can say "slow
down" is an open-ended problem, and the list will always be one form behind.**

The classification is now inverted. Only an explicit `not found` or `has no
series for` may be cached as an absence. Every other response — recognised,
unrecognised, a timeout, a 500 — is transient, is never cached, and can never
become a finding. Failing safe does not require anticipating the vendor's
vocabulary.

`tests/test_locator_adjudication.py` pins both throttle forms, a timeout and a
500 against the new rule, and the two definite-absence forms.

## What survives

The 430 comparisons are real fetches against real data and are unaffected. On
them:

* **208 of 430 (48.4%)** disagree past the 2% fail tolerance; 131 of those move
  a constituent's cumulative contribution by a percentage point or less, 38 by
  more than 10 pp, 14 by more than 50 pp.
* **41 symbols carry at least one day where our own adjustment factor is flat
  across a move above 10%** — the subset that names us rather than the vendor.
  `SYMC` is among them, which is a genuine check: this test knows nothing about
  duplicate files and reaches the same file the duplicate-locator work did.
* `MO` on 2008-03-31 stands exactly as recorded: raw −69.93%, adjusted −69.93%,
  factor flat at 0.320104, Tiingo at −1.56%.

The direction analysis now covers 773 failing days: 63 where our factor is flat
across a large move, 73 where we adjusted and the vendor did not, 637 ordinary
price disagreements.

`KSU` at +3636.08% and `TMUS` at +889.10% on their worst days are the second
source's own defects. The comparison finds disagreement, not fault.

## What is owed

473 symbols are uncovered, not cleared. The sentinels are deleted so a re-run
re-attempts them; at the observed throughput of roughly 76 symbols an hour that
is about six hours of wall clock, almost all of it spent asleep. Until then the
correct statement is **430 of 947 covered**, and the 9.5% rate at which our
factor is flat across a large move must not be extrapolated to the rest: the
covered set was ordered by membership-years, so it is the longest-lived names,
with the most opportunities to have had a corporate action at all.

## Prohibitions

No price data was changed, no bar synthesised, no backtest run, no approval or
A2 treatment applied, no resolver status or locator preference written. Network
access was read-only cross-check requests with the key in the authorization
header.
