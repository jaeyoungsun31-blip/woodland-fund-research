# Re-scoped duplicate locators: 22 contentions, and the resolver picks the bad file

Date: 2026-09-07
Status: completed measurement and adjudication; no gate, no panel, nothing applied
Supersedes the counting in `2026-09-07-phase3-duplicate-locator-census.md`; that
entry stands unedited, as does its report.
Artifacts: `reports/security-resolver/2026-09-07-locator-adjudication/`
Code: `scripts/run_locator_adjudication.py`, `tests/test_locator_adjudication.py`

Two corrections from planning govern this entry. The 5% gate threshold is withdrawn
and nothing is scored against a fraction. A contender counts only if its bounds
contain the membership window and the two files imply different returns inside that
window. The adjusted-ratio-range metric is retained; exact agreement on the adjusted
level stays rejected as degenerate.

**The census's 73 diverging locators become 22.** 61 of the 93 qualified pairs are
Case 4 ticker successions covering different eras of one lineage, 9 more agree inside
the window, and 23 pairs across 22 locators genuinely contend. Of those, 10 move a
constituent's cumulative in-window return by more than one percentage point and one
accounts for 90.9 of them.

## The reference case dissolves, and three named cases land differently

`FISV`/`FI` ranges 1.402 over the full overlap and **1.000000** inside Fiserv's
membership window, against a quantisation floor of 1.000003. It is one series under
two normalisations. The whole disagreement was outside the window.

`MYL`/`VTRS`, `ANTM`/`ELV` and `GEN`/`SYMC` were expected to fail date eligibility as
different eras of one lineage. They do not, and the reason is worth recording because
it generalises: **the successor's file is backfilled with the entire pre-succession
history.** `VTRS` begins 1980-03-17, the same day `MYL` does. `ELV` begins 1993-01-28,
before Anthem's window opens. Their bounds contain the window, so eligibility is
satisfied and the second limb does the separating - `MYL`/`VTRS` diverges by 1.0025
in-window and 0.00 pp cumulatively, while `SYMC`/`GEN` is the largest contention in
the store. `TPR`/`COH` is a succession as expected, as are both warrant cases that
topped the census's worst-divergence table.

## A correction to the premise, and it changes the remedy

The brief held that identical prices cannot imply incompatible returns unless one
adjusted series is wrong. That is true where the raw prices really are identical on
the disagreeing day, and on 9 of the 23 pairs they are not. Two files agree on 99.9%
of closes and differ on the handful of days that produce the divergence, each file's
adjusted return faithfully tracking its own raw return. That is a price defect, not an
adjustment defect.

`CTL`/`LUMN`, the pair the brief led with, is **one bar**: 2020-03-09, `CTL` 11.07
against `LUMN` 10.26, identical again on 2020-03-10 and 2020-03-11. `ADS`/`BFH` fails
on the same date with the same shape. In `IGT`/`IGT1` and `NLOK`/`GEN` the offending
bar is a repeat of the previous close.

Cumulatively these are near-nil - `CTL`/`LUMN` is -0.21 pp over 21 years. That is not
the same as harmless: the bad bar gives `CTL` a -7.5% day followed by +0.9% where
`LUMN` has -14.3% followed by +8.9%, a fabricated two-day round trip on one of the
most consequential days in the sample. Cumulative gap and daily distortion are
different questions and both are reported.

## SYMC: a missed split, in the column the panel reads

`SYMC`, `GEN` and `NLOK` carry identical raw closes across 2004-12-01, where the close
falls 48.61%. `GEN` and `NLOK` record an adjusted return of +2.77%. `SYMC`
records **-48.61%** - its adjusted column follows the raw column straight through what
the price series itself shows to be a two-for-one split. A two-for-one split is not a
48.6% loss, so no third source is needed, and where three files exist for one entity
two agree and one does not.

Over the membership window 2004-01-07 to 2019-10-18, 3,974 bars: `GEN` +79.06%,
`NLOK` +79.05%, `SYMC` **-11.86%**. **90.9 percentage points on one constituent, and
`SYMC` is the file v9 resolved.**

This is the mirror image of KMI. There the raw column was inflated tenfold and
`adjusted_close` was continuous, so the panel was never exposed. Here the raw column
is right and `adjusted_close` is wrong, which is the column returns are computed from.
The pair of findings together says the store's defects are not confined to one column.

`check_adjustment` returns `ok` for `SYMC`, worst factor drop -7.62e-06 against a
tolerance of 1e-4, and it cannot do otherwise: the factor is 0.705775 before the split
and 0.705773 after. A missed event leaves the ratio flat, which is exactly what the
check demands. So the store's integrity check is now on record as blind in both
directions - it misses KMI's tenfold factor increase because it only flags decreases,
and it misses a missing split because the factor never moves. Catching either needs a
cited corporate-action calendar the store does not carry.

## The finding that bears on the resolver

15 of the 23 pairs are decided, 3 of them with no third source at all. **In 13 of
those 15 - 12 distinct locators - the defective file is the one v9 resolved:** `ADS`,
`ANTM`, `CTL`, `FBHS`, `KRFT`, `MMC`, `NLOK`, `NVLS`, `PKI`, `SYMC`, `TUP`, `WIN`.
Only `SW`/`SMFTF` and `CCEP`/`CCE_old` went the other way.

That is not a coin flip. The automatic path resolves to the file named by the ticker
of the day, and the vendor's file under a superseded ticker is on this evidence the
less well maintained of the two - it misses the split, omits the dividends, and
carries the bad crash-day bar. The successor's backfilled file is better on every pair
where the two can be separated. Nothing has been applied; no resolver status or
locator preference was changed.

## Method notes worth keeping

**A ticker is not an identity, at the third source either.** Tiingo's `WIN` is a
company first listed 2023-12-01, not the Windstream delisted in 2020.
Every Tiingo series is now qualified on price against our own files - at least 90% of
in-window closes matching at rtol 1e-3, the same rule the census used to reject token
collisions - before any of its numbers count as evidence. A first pass without that
guard produced a verdict for `NVLS`/`NVLS1` off a recycled ticker and it was withdrawn.
The guard also shows why the check must be in-window: Tiingo's `NVLS` matches at
0.9817 across Novellus's window even though the ticker was later reused.

**Overall agreement rates cannot adjudicate these pairs.** The disagreements are a
handful of discrete events among thousands of quiet days, so both files score ~0.98
against any third source regardless of which is right. The adjudication is done on the
step dates, where the question actually lives.

**The implied distribution reaches where no vendor does.** On a day both files record
the same raw prices, the difference between a file's adjusted and raw return is the
cash distribution it applied. `SMFTF` implies a negative one on three days, which no
security pays, deciding that pair internally. `WINMQ` implies a stable distribution
about 3.8 times the one `WIN` implies; `KHC` implies distributions on three dates
where `KRFT` implies nothing at all. (Per-share amounts are redacted in the public
export.) That establishes which file applied something and which applied
nothing. Naming the actual declared dividend would be an external claim and this store
carries no cited dividend history to support one.

**A rate limit is not a finding.** The vendor signals throttling in prose - "You have
run over your hourly request allocation" - and an early version of the script matched
only the word "limit", read that as "no such ticker", cached it, and reported 19 pairs
as having no third source. Wrong in a way that would have looked like a result.
`tests/test_locator_adjudication.py` pins this and six other rules.

## Limits

Candidate generation was not redone and its lower bound carries over in full: a
contender whose prices are uniformly rescaled shares no exact `(date, close)` token
and was never proposed. 22 is a lower bound on the same search.

Membership is measured only where the record asserts it. Annual rows are joined across
breaks of ten days or less, so a longer turn of the year is excluded rather than
assumed - 1.17% of hull days across the contending pairs, 14.69% on `SW`. A defect
inside such a break is invisible here.

**The eligibility boundary is hard, and one case sits on it.** `CTX`/`CTX1` is
excluded because `CTX1` ends **one day** before Centex's window closes. Measured over
the window anyway it ranges 2.046 with a cumulative gap of **+56.48 pp** - it would be
the second-largest contention in the store. `ARNC`/`ARNC_old` misses by three days and
is immaterial. The count is 22 locators strictly, 23 with a one-day tolerance, and
which is intended is planning's call.

## Prohibitions

No panel was built. No price data was changed. No backtest was run. No synthetic bar
was created. No approval and no A2 treatment was applied. No resolver status or
locator preference was changed. The only network access was read-only cross-check
requests to Tiingo, with the key in the authorization header.
