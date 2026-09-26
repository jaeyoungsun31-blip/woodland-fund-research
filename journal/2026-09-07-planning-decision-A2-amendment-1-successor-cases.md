# A2 Amendment 1 — Case 4 was wrong; adding Case 5 and a duplicate-locator rule

Date: 2026-09-07
Status: PROPOSED — unsigned
Amends: `2026-09-06-planning-decision-A2-delisting-and-membership-end-convention.md`
(SIGNED 2026-09-06). That entry stands as written; this amends Case 4 and adds
Case 5 and Case 6. Cases 1, 2, 3, the integrity clause and the reporting
requirements are unchanged.

## What v9 reported

```
symbol-years by case:  1: 0   2: 58   3: 1   4: 0   unresolved: 1,515
symbol-years refused:  1,574 of 14,635  (10.8%)
seam days Case 4 would drop: 0
refused_case3_confirmed: 1     refused_case3_residual_unverified: 106
```

Case 4 fired zero times. Twenty-nine symbols fell to Case 3 — the residual,
which refuses.

## The cause is a defect in Case 4 as I wrote it, not in Codex's work

Codex retrieved the corporate actions correctly, with citations it actually
fetched:

```
DOW  -> DWDP  2017-09-01  investors.dupont.com press release
FISV -> FI    2023-06-07  investors.fiserv.com listing transfer
CEG  -> EXC   2012-03-12  SEC 8-K, accession 000119312512114696
FB   -> META  2022-06-09  investor.atmeta.com
COV  -> MDT   2015-01-26  SEC EX-99.1, accession 000119312515020681
```

The classification then failed on the signature I specified. Two errors, both
mine.

### Error 1 — the seam test assumes a newly created successor

A2 Case 4 requires "a successor file whose first bar falls within five trading
days of the predecessor's last bar." That holds only when the successor did not
previously exist. Where a constituent is acquired by an established company, the
successor file begins decades earlier:

```
COV      2007-06-14..2012-06-15   MDT   1973-05-02..2026-09-04
CEG_old  1997-12-31..2012-03-12   EXC   1973-05-02..2026-09-04
DOW_old  2003-09-10..2017-08-31   DWDP  1980-03-17..2019-06-28
```

The test can never pass. The correct test is continuity of **coverage**, not
proximity of first bars: the successor must have a bar on the next trading day
after the predecessor's last, and the predecessor must have none after it.

### Error 2 — stock acquisitions are not continuity

The pre-signature amendment routed stock and stock-plus-cash deals to "Case 4 as
a continuity event." That was wrong. When a constituent is acquired for stock,
its seat ends; the acquirer is a **separate constituent with its own membership
record**. Stitching the two fabricates a single security out of two, and would
carry the acquirer's returns into the target's history.

Measured confirmation — overlapping bars, agreement on unadjusted close:

```
DOW_old vs DWDP   3,520 overlapping bars    0.0% close agreement
CEG_old vs EXC    3,572 overlapping bars    0.0%
COV     vs MDT    1,263 overlapping bars    0.0%
ARNC    vs HWM    1,709 overlapping bars    0.0%
```

DWDP's pre-2017 history is DuPont's, not Dow's. MDT's pre-2015 history is
Medtronic's own. These are different securities that happen to share a calendar.

## Case 4 — RESTATED (pure rename only)

**Signature.** A cited corporate action changing the ticker with **continuity of
the legal entity** — a rename or listing transfer, not an acquisition. The
successor must have a bar on the first trading day after the predecessor's last
bar, and the predecessor must have no bars after that date.

**Treatment.** Treat predecessor and successor as one security with two
locators. Take the predecessor through its last bar and the successor from the
seam forward. **Any overlapping bars are the successor's own separate history
and must be excluded**, never averaged or preferred.

**Seam rule.** Unchanged: adjusted-close factors are per file, so the seam-day
return is dropped and counted.

Qualifying examples: FB→META, FISV→FI. Not qualifying: CEG→EXC, COV→MDT,
DOW→DWDP, ARNC→HWM.

## Case 5 — NEW: acquisition for stock, or stock plus cash

**Signature.** A cited completed acquisition in which consideration includes
equity in the acquirer, and the file terminates within five trading days of the
close.

**Treatment.** The membership window ends at the last bar. Exit at the last
close, which already reflects the exchange ratio against the acquirer's price.
**Do not stitch to the acquirer.** The acquirer holds its own seat and appears
in the panel under its own membership record; carrying the target into it would
double-count the acquirer and fabricate continuity.

**Ordering.** Case 5 is tested immediately after Case 1 and before Case 4, so a
stock acquisition is never mistaken for a rename.

## Case 6 — NEW: duplicate locator, same security

**Signature.** Two live files whose bars cover substantially the same span for
the same entity.

Measured instance:

```
FISV vs FI   9,858 overlapping bars 1986-09-25..2025-11-10
             unadjusted close agree  80.0%
             ADJUSTED close agree    20.9%
             volume agree            24.5%
```

The same company under two tickers, with **divergent adjustment factors**. This
is the defect class first seen in `BBBY_old`.

**Treatment.** Declare a single preferred locator per security by rule — the one
whose bounds span the membership window; where both do, the one with the greater
bar count — record the rejected locator, and report the adjusted-close
divergence over the overlap in every result. Never merge or average the two.

## Revised ordering

**1, 5, 4, 2, 3, with 6 applied first wherever two locators contend.**
Case 3 remains the residual.

## Consequence for the v9 census

The 29 Case 3 assignments are, on this evidence, mostly unretrieved rather than
unexplainable — Codex's own counts say so: one Case 3 confirmed against 106
symbol-years of "residual unverified". The 10.8% refusal is an artifact of a
defective Case 4 and a missing Case 5, not a measurement of the panel's health.
Reclassify before drawing any conclusion about panel viability.

## Separate defect — the evidence store is not shared between runs

`DOW_old` was cited and corroborated in `evidence-batch01` (SEC filing,
predicted last date 2017-08-31 and terminal close $66.65, both observed). The v9
classification pass recorded "no qualifying cited action explains the end" for
the same symbol. Retrieved evidence must persist to a single store that every
subsequent pass reads, or work is repeated and then contradicted.
