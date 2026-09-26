# Planning review — full Tiingo cross-check: a good measurement, a weak verdict

Date: 2026-09-07
Status: review (does not block; changes what the cross-check can be used for)
Artifact: `reports/security-resolver/2026-09-07-tiingo-crosscheck/`
(`summary.json` and `crosscheck.csv` written 23:06; no journal entry existed for
this run when this review was written — the 18:07 entry describes the earlier
100-name partial run.)

## Reported

```
automatic_locators 947 | attempted 947
compared              430
no_tiingo_series      473
different_entity       41
insufficient_overlap    3
verdicts: ok 222 | INVESTIGATE 208   (fail tol 0.02, monitor 0.005)
```

## The number that matters is 473, not 208

Only 45% of the panel could be compared at all. **Tiingo has no series for 473
of 947 resolved symbols**, and that population is disproportionately the
delisted names — the half the EODHD purchase exists to capture and the half
where identity is hardest to establish.

Consequence: **Tiingo cannot serve as the constituent panel's cross-check.** It
is structurally blind to the population at risk. It remains useful for the live
ETF store, where coverage is complete. Treating a Tiingo pass as evidence of
panel integrity would be a coverage claim the data does not support.

## It does not speak to the wrong-security finding

Every symbol flagged in `STATE.md` §7.2 on the volume screen was checked:

```
no_tiingo_series : CFC ACS BT FBF GLK SOV NVR GHC CIN GR UVN CSR SLR
different_entity : AYE
```

Thirteen unverifiable, one returned `different_entity`. The cross-check neither
corroborates nor refutes the finding. `AYE` is weak support; the other thirteen
are silence. The §7.2 adjudication still has to be done on price evidence.

## 208 INVESTIGATE is not 208 defects

`disagreement-direction.csv` classifies 521 failing days:

```
other                      433  (83%)
we_adjusted_they_did_not    51
ours_missed_event           37
```

Only 88 of 521 failing days are attributed to either provider. The remaining
433 are unexplained. And Tiingo produces its own obvious garbage — `KSU`
2013-05-24 theirs +36.36 (+3,636%), `TMUS` 2019-07-15 theirs +8.89 — so a
disagreement is not evidence about EODHD by default.

**Do not let "208 symbols fail the cross-check" enter the record as "208 EODHD
defects."** That inference is unsupported and is the failure mode of
`2026-09-06-planning-review-v7-packet-and-catalog-name-defect.md` in new dress.

## The real yield is the 37

The `ours_missed_event` days are small, concrete, and match a recognisable
class — unadjusted corporate actions producing fabricated near-±100% returns:

```
MO   2008-03-31  ours -0.6993  theirs -0.0156   (Philip Morris Intl spinoff)
RTN  2001-05-14  ours -0.9496  theirs +0.0078
JWN  1999-12-21  ours +1.2708  theirs +0.0599
```

This matters disproportionately because v16 is cross-sectional momentum and
**ranks on past returns**: a fabricated ±100% day is a top- or bottom-decile
signal, not noise. Adjudicating 37 days is cheap and removes a direct attack
surface on the signal.

## Recommendations

1. Adjudicate the 37 `ours_missed_event` days against corporate-action evidence.
   Small, high value, do it first.
2. Investigate why 433 of 521 failing days classify as `other`. A classifier
   that explains 17% of its own findings is not yet a diagnostic.
3. Do not spend more on extending Tiingo coverage of the panel. The 473 gap is
   a vendor-coverage fact, not a run parameter.
4. Record in the panel's reporting block that **45% of the panel is
   independently cross-checked and 55% is not**, with the delisted skew named.

## Process

`STATE.md` §12 assigns work item 14 to Qwen; Claude Code ran it. Lane collision
on the first day the lanes existed. Not harmful here — the work is additive and
report-only — but the convention needs to hold or §12 is decoration.
