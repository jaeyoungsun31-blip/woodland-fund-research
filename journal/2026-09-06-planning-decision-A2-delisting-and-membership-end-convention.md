# Decision A2 — delisting returns and membership windows that outlast their price history

Date: 2026-09-06
Status: SIGNED 2026-09-06
Amended: 2026-09-06, pre-signature — Case 1 restricted to all-cash consideration;
stock-and-cash deals routed to Case 4; the adverse bound extended from the
absent set to all of Case 2.
Supersedes: nothing. A2 was declared open on 2026-09-06 in
`2026-09-06-planning-decision-revive-v16-on-constituent-data.md` and has blocked
both panel construction and packet adjudication since.

## The problem this settles

A membership record can outlast its price file. In the v8 review packet, 36 rows
across 30 symbols end after their candidate's last bar; 31 of those shortfalls
exceed two years. Separately, 29 symbols holding 122 symbol-years (0.83% of the
14,635-symbol-year panel) have no price file at all.

Those two facts have four different causes with four different correct
treatments. Applying one rule to all of them produces bias, and the bias is not
random: the 29 absent symbols are **entirely** companies that entered bankruptcy
(RSHCQ, MTLQQ, LEHMQ, ABKFQ, AAMRQ, UAWGQ, WCOEQ …). Dropping them silently
reconstructs survivorship bias inside the instrument built to remove it.

## Integrity clause — binding on all four cases

Classification uses the **corporate action**, never the realized return. It is
forbidden to consult a name's performance, or the effect on any result, when
deciding which case applies. Every classification requires a retrievable
citation (URL or SEC accession number). A name whose case cannot be established
by citation remains `unresolved` and is refused for the affected window — an
unresolved constituent is a refusal, not an omission.

## Case 1 — Completed cash merger or acquisition

**Signature.** The file terminates; a cited corporate action completes on or
within five trading days of the last bar; the consideration is **all cash**; and
the terminal close is within 5% of the cited cash price.

Deals paying stock, or stock plus cash, do **not** qualify. The terminal close
of a stock deal tracks the acquirer's price and the exchange ratio, so no
meaningful band exists against a single cited figure, and the holder receives a
continuing position rather than cash. Route those to Case 4 as a continuity
event.

**Treatment.** Hold to the last bar and exit at the last close. Truncate the
membership window to the last bar. No synthetic return is inserted.

**Rationale.** The deal price is already in the last print. `RAL_old` terminates
0.06% below Nestlé's $33.50 offer; the residual is under 0.1%.

## Case 2 — Bankruptcy, liquidation, or performance-related delisting

**Signature.** A cited bankruptcy or delisting event, with either no price file
or a file that ends while the security was still trading toward its terminal
value.

**Treatment.** Carry whatever history exists. On the first date after the last
bar, apply a declared terminal return:

- the cited recovery to common holders where a figure is available;
- otherwise the Shumway fill: **−30%** for NYSE/AMEX, **−55%** for Nasdaq
  (Shumway 1997; Shumway & Warther 1999).

**Where no price file exists at all,** the name cannot be priced and cannot be
held. It is excluded from the tradeable universe on those dates.

**Mandatory paired sensitivity — all of Case 2, not only the absent set.** The
Shumway fills are estimated on 1962–1993 CRSP data and their calibration to
post-2000 bankruptcies is unestablished. Every result on this panel is therefore
computed twice:

- **base** — cited recoveries where available, Shumway fills otherwise, absent
  set excluded;
- **adverse bound** — every Case 2 name assigned −100% at its terminal date,
  and the absent set assigned −100% over its final membership year.

Any conclusion that does not survive both is not supported by this panel and
must be reported as such. This converts both an unfixable gap and an
unvalidated parameter into stated bounds rather than silent assumptions.

## Case 3 — Data truncation

**Signature.** The file ends, membership continues, and **no** cited corporate
action falls on or near the last bar. The security demonstrably kept trading.

**Treatment.** **Refuse** the name for the portion of the window after the last
bar. Do not exit at the last close.

**Rationale.** `BSC_old` ends 2008-03-14 at $30.00 on 187M shares — 27× its
60-day median — the day the Fed/JPMorgan financing was announced. Bear Stearns
went on to close at $10 on 2008-05-30. Exiting at the last close books $30 for a
$10 outcome, a threefold overstatement on exactly the kind of name this panel
exists to capture. Vendor incompleteness must never be recorded as a delisting.

Refused symbol-days are counted and reported, never dropped quietly.

## Case 4 — Ticker change or corporate successor

**Signature.** A cited corporate action changing the ticker with continuity of
the entity, and a successor file whose first bar falls within five trading days
of the predecessor's last bar.

**Treatment.** Stitch predecessor and successor into one security history.

**Seam rule.** Adjusted-close factors are computed per file, so a return
calculated across the join is an artifact. The seam-day return is **dropped**,
and each dropped seam day is counted and reported. Returns within each segment
are computed normally.

**Rationale.** FB→META, FISV→FI, COV→Medtronic and similar account for most of
the 31 shortfalls exceeding two years. Refusing them would delete Meta and Dell
from the panel for a locator change.

## Ordering

Cases are tested 1, 4, 2, 3, in that order; the first whose signature is
satisfied applies. Case 3 is the residual: it is what remains when no cited
corporate action explains the file's end. This ordering is deliberate — it
forces a positive, cited explanation before a name is treated as an event, and
sends everything unexplained to refusal rather than to a synthetic return.

## Reporting requirements

Every result computed on this panel must report, alongside it:

1. symbol-years by case (1/2/3/4);
2. symbol-years refused under case 3 and under the citation requirement;
3. symbol-years in Case 2, split into priced and absent, with base and
   adverse-bound results for each;
4. seam days dropped under case 4.

A result published without these is not a result from this panel.

## Signature

Proposed by: planning chat, 2026-09-06
Signed by: Jaeyoung — 2026-09-06

Provenance: approved verbally in the planning chat and recorded by the planning
chat on Jaeyoung's instruction; he was on mobile and could not edit the file
himself. The approval covers the four cases, the integrity clause, the ordering
1-4-2-3, the all-cash restriction on Case 1, the adverse bound across all of
Case 2, refuse-not-exit on Case 3, and the seam-day drop on Case 4.
