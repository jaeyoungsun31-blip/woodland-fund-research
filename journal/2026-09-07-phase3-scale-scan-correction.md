# Correction — the scale-defect scan counted stock splits, not defects

Date: 2026-09-07
Status: correction to a measurement in a prior entry; the prior entry stands unedited
Corrects: `2026-09-07-phase3-date-admissibility-results.md`, section
"The scale defect is not confined to KMI"
Artifacts: `reports/security-resolver/2026-09-07-date-admissibility/scale-defect-scan.json`

The prior entry reported that 1,037 files, 2.04% of the store, carry a raw-column
scale error of KMI's signature. **That characterisation is wrong.** The count is
real but it is not a defect count: most of those files record genuine stock
splits, correctly stored. The classifier that separated "scale error" from
"split" does not work, and the reason it does not work invalidates the class, not
merely its calibration.

## The discriminator was void

The scan flagged steps in `close/adjusted_close` that are near-exact powers of
ten, then classified each by whether share volume stepped with the price. The
stated reasoning was that a genuine N:1 split multiplies share volume by about N,
while a scale error moves the price column alone.

That reasoning assumes the vendor stores unadjusted volume. **EODHD
split-adjusts historical volume.** Volume is therefore already expressed on the
post-split basis on both sides of the step and never steps at a split. Every
genuine split in the store looks, to this test, exactly like a scale error.

Seven cases, measured directly, 20-bar median volume either side:

| symbol | date | raw close step | adjusted step | volume 1-bar | volume 20d median | truth |
|---|---|---:|---:|---:|---:|---|
| NVDA | 2024-06-10 | ×0.1007 | ×1.0075 | 0.7618 | 0.6879 | genuine 10:1 split |
| AVGO | 2024-07-15 | ×0.1008 | ×1.0080 | 0.7552 | 0.5937 | genuine 10:1 split |
| NFLX | 2025-11-17 | ×0.0992 | ×0.9917 | 0.5479 | 1.0353 | genuine 10:1 split |
| SMCI | 2024-10-01 | ×0.0974 | ×0.9738 | 0.4474 | 0.5380 | genuine 10:1 split |
| MA | 2014-01-22 | ×0.1018 | ×1.0177 | 0.7147 | 1.0231 | genuine 10:1 split |
| C | 2011-05-09 | ×9.7699 | ×0.9770 | 9.5813 | 1.1781 | genuine 1:10 reverse split |
| KMI | 2015-01-20 | ×0.1007 | ×1.0070 | 1.0029 | 0.7529 | scale error |

Every 20-day volume ratio lies between 0.538 and 1.181. Not one approaches ten.
The test had no discriminating power and returned the same answer for all seven.
C's single-bar volume ratio of 9.58 is a spike on the reverse-split date itself
and does not survive the 20-day median, so it is not a counter-example.

Consistent with this, 836 of the 1,106 steps the scan called scale errors are
power +1 — the raw close falling by ten, the exact shape of a 10:1 split — and
the median volume ratio across all of them is 1.181, which is flatness, not
evidence.

## What the number actually is

`scale-defect-scan.json` reports **files containing a power-of-ten step in the
raw close column**: 3,800 files, 4,992 steps, of which 4,970 are testable. That
measurement stands. The subdivision into `scale_error_raw_column` (1,106 steps
across 1,037 files) and `consistent_with_split` (282) does not, and neither label
should be cited.

Separating the two classes requires an external, cited split calendar. The store
does not contain one, and no internal signal in these files distinguishes a
correctly recorded split from a ten-fold error in the raw column: both leave
`adjusted_close` continuous, both leave volume flat, and both step the adjustment
factor by the same power of ten. The prior entry's claim that "volume is the
discriminator" is withdrawn.

## KMI remains a true positive, on different evidence

The KMI finding survives, but not because of the volume test, and the prior
entry's reliance on that test was misplaced.

KMI is a defect because a retrieved citation gives an IPO offering price of $30
while the stored raw first close is $310.50 — a contradiction of exactly ten —
and because no split occurred on 2015-01-20 to explain the step. The security
never traded near $418. Neither fact comes from the volume series.

That is the correct form of the argument and it is worth stating plainly: the
defect was caught by a **cited external number contradicting the stored one**,
which is precisely the mechanism the signed date-admissibility rule installs. The
scan did not find it; the fingerprint did. The scan then generalised a single
true positive into a store-wide class on a test that could not support it.

The measurements of the KMI file itself are unaffected: 989 bars inflated
ten-fold from 2011-02-11 through 2015-01-16, one step, `adjusted_close`
continuous. Only the claim that 1,037 files share that condition is withdrawn.

## The panel is unaffected; the fingerprint method is not

`adjusted_close` is continuous across all seven steps above — the adjusted return
on the step day is +0.75%, +0.80%, −0.83%, −2.62%, +1.77%, −2.30% and +0.70%
respectively, every one under 3% in absolute value and none of them anomalous.

Returns are computed from `adjusted_close`. **The defect is confined to the raw
column, and the panel does not read the raw column.** No panel result is exposed
to this.

What is exposed is the numerical fingerprint method, which reads raw close by
signed instruction — correctly, since a cited consideration or offering price is
a raw, unadjusted figure. So the exposure is narrow and specific: a fingerprint
comparison against a raw close is only as good as that file's raw column, and at
least one file in the store has a raw column wrong by a factor of ten with no
internal signal that says so.

## The existing integrity check cannot catch this

`check_adjustment` in `woodland/data.py` computes `adj_close / close` and flags
three conditions: the factor decreasing, a terminal factor away from 1.0, and
nonpositive prices. KMI's defect raises that factor ten-fold at 2015-01-20 —
0.05565 to 0.55651 — and an **increase is not one of the flagged conditions**.
Run against the KMI file it returns `verdict: ok`, worst factor drop
−7.28e-06 against a tolerance of 1e-4, terminal factor exactly 1.0.

Two further facts complete the picture. The check expects a column named
`adj_close` while the EODHD store writes `adjusted_close`, so it cannot be
applied to this store without a rename. And `scripts/woodland-download-eodhd.py`
runs no adjustment validation of any kind — it verifies column presence and
prints that these are "raw vendor files awaiting data-quality validation." That
validation has not been performed.

A check that would have caught KMI is not the same as the one that exists: it
would need to flag the factor *rising* by a power of ten on a date with no cited
split, which reduces again to needing a split calendar.

## Effect on prior conclusions

The batch01 re-adjudication is unchanged: five accepts survive, eleven return to
unknown, KMI among them for the reason already recorded. No multiplicity count,
band, or verdict in
`reports/security-resolver/2026-09-07-date-admissibility/admissibility.csv`
depends on the scan.

The sentence in the prior entry beginning "roughly one file in fifty has a raw
price column wrong by a power of ten" is withdrawn. The supported statement is
that one file is known to be wrong, that the store contains no validated
adjustment check, and that the true rate is unmeasured.

The report README and `scale-defect-scan.json` are annotated in place with this
correction, since `reports/` is regenerable output and not append-only history.
The prior journal entry is left exactly as written.

## Prohibitions

No price data was changed. No panel was built, no backtest run, no synthetic bar
created, no approval or A2 treatment applied. The seven verification reads were
read-only.
