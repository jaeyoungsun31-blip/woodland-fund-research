# Date-match admissibility applied — batch01 re-adjudicated, and a raw-close scale defect

Date: 2026-09-07
Status: completed measurement and adjudication; all identity outcomes remain proposals
Implements: `2026-09-06-planning-decision-date-match-admissibility.md` (SIGNED),
`2026-09-06-planning-decision-A2-delisting-and-membership-end-convention.md` (SIGNED)
Declaration: `2026-09-06-phase3-date-admissibility-implementation.md`
Artifacts: `reports/security-resolver/2026-09-07-date-admissibility/`
Code: `woodland/live/resolver_multiplicity.py`, `woodland/live/resolver_numeric.py`,
`scripts/run_date_admissibility.py`

The signed rule had never been applied to any run. It is now applied. This report
explicitly supersedes the identity suggestions in
`reports/security-resolver/2026-09-06-evidence-batch01/`; that packet is retained
unedited and no entry in it was rewritten. Where the two disagree, batch01
accepted on evidence this rule finds insufficient.

## Multiplicity

Computed from separate first-bar and last-bar counters over the 50,864 readable
files in the v9 manifest (`listed_parquet_files` 50,864; all readable), never
over expanded segments. The signed decision's measurement reproduces: unique last
bar 2.91%, unique first bar 3.06%, last bar shared by more than 100 files 37.04%,
first bar 13.23%. `1997-12-31` is the first bar of 3,760 files and the last bar of
none; `1999-01-04` is the first bar of 1,546 and the last bar of 3. Distinct first
dates 8,600; distinct last dates 5,927. The largest single last-bar cohort is
2026-09-04 at 17,448 files, which is the store's own extraction date, not an event.

Both boundary counts are recorded on all 40 packet rows, including the 24 that
were never accepts. Eleven of the 40 touch a vendor floor on at least one
boundary; none relies on one, because in every case the pivot the citation
predicts is the other boundary. The flag is carried regardless.

Two refusals are implemented in the counter rather than left to the caller.
A pivot absent from the manifest is recorded as unknown multiplicity and never as
unique, so it does not satisfy the multiplicity-1 branch and falls through to the
numeric requirement. A segment boundary is never counted: `LB_old1::segment2`
begins 2003-09-10, which is a splice this codebase introduced, while the file
begins 1982-04-01; its first-bar multiplicity is unknown and its last bar, a
genuine file boundary, counts normally. `LB_old1::segment1` is the mirror case —
first bar counted at 2, last bar unknown.

## Adjudication — 5 of 16 accepts survive

Observed pivot multiplicities: DOW_old 5, CF 10, DG 8, KMI 7,
LB_old1::segment2 8, AGN 11, RTN 4, APC_old 10, BBT_old 10, STI_old 10, TMK 10,
CA_old 7, HCA 5, PX_old 7, CEG_old 3, HLT 6.

This matches the shape the declaration stated in advance: CEG_old at multiplicity
3 is the only date-only accept the 2–3 rule still permits, and 14 others require
numbers. Of those 14, three carried a usable number in their own citation.

Surviving: DOW_old (cited close 66.65, residual $0.0000, $0.02 band); CA_old
(cash 44.50 against 44.44, −0.1348%, 5% band); AGN (120.30 + 0.866 × cited ABBV
close 83.96 = 193.00936 against 193.02, +0.0055%, 1% band); HCA (IPO offering
30.00 against first close 31.02, +3.40%, ±30% band, medium confidence); CEG_old
(date alone, medium confidence).

Returned to unknown, in three distinct classes. **Retrieved number with no
applicable observed counterpart:** APC_old (59 + 0.2934 × OXY acquisition-date
*average* 46.31 = 72.587354 against 72.77 — an average valuation price is not a
closing-price prediction, and the 0.25% proximity is not scored); PX_old (a
one-for-one ratio predicts no closing price); STI_old (1.295 × BBT_old close
54.24 = 70.2408 against 70.13, inside 1%, but the acquirer close is read from
this store rather than independently cited, and BBT_old's own identity is itself
unverified — corroborating one unverified file with another is one channel
presented as two). **No number retrieved:** CF, DG, HLT (listing dates, no
offering price); LB_old1::segment2 (separation date, no consideration); TMK (a
rename carries no consideration); BBT_old (BB&T was the acquirer, so no
consideration on its own shares); RTN (2.3348 RTX cited, no RTX same-event close
retrieved). **Number that misses:** KMI alone.

Returning to unknown is not a rejection. For CF, DG, HLT and RTN the missing
figure is published in a 424B or a merger agreement and the outstanding work is
retrieval, not research. STI_old becomes a pass on arithmetic already performed
if an independently cited BB&T close for 2019-12-06 is retrieved.

Bands were applied as declared and none was widened: $0.02 absolute on a cited
exact close, 5% on fixed cash, 1% on stock consideration from a cited same-event
acquirer close, ±30% on an IPO offering price. All numerical checks used raw
close; no adjusted close and no assumed rescaling entered any comparison.

## KMI — a scale error in the price file

The tenfold discrepancy the declaration flagged and refused to accommodate is a
defect in the stored data, not a split adjustment and not a wrong security. The
raw OHLC columns of `KMI.US.parquet` (sha256
`cad44aa87183b26a9fe4e8bf0bf081470a0e018a3d7f20e467fcea5a9763eab6`) are inflated
by a factor of ten for 989 bars, from the file's first bar 2011-02-11 through
2015-01-16 inclusive.

Four measurements across 2015-01-20, the single step in the file. Raw close steps
×0.100698. `adjusted_close` steps ×1.006983, an ordinary session. Share volume
steps ×1.0029 bar-to-bar and ×0.7529 on 20-day medians, where a genuine
ten-for-one split would lift volume by approximately ten. The
`close/adjusted_close` factor steps 17.9687 → 1.79687, retaining the identical
mantissa, which is arithmetic applied to a stored number rather than a corporate
action. There is exactly one such step in the file.

Volume is the discriminator. A split and a scale error are indistinguishable on
the price columns alone; they separate on whether share count moved. The
conclusion rests on the file's internal evidence and not on an external claim
about Kinder Morgan's corporate history: a ten-for-one share split is ruled out
by the volume series, and a change of security by the continuity of
`adjusted_close`. Confirmation against a cited split history would strengthen the
finding and is not required to reach it.

This accounts for the observation completely. Against the cited $30 offering
price, the first close as stored is +935.0%; with the tenfold removed it is
+3.5%, inside the ±30% band. KMI's event vintage is therefore probably correct
and its data is not. It remains `unknown`, correctly: the rule requires a number
the data corroborates, and this data cannot corroborate anything at that date.
No price was modified. Correcting the file is a separate, cited, reviewable
action and was not taken.

## The scale defect is not confined to KMI

A read-only scan of all 50,864 files searched for steps in
`close/adjusted_close` that are near-exact powers of ten
(|log10(step) − round(log10(step))| < 0.002), then classified each by whether
`adjusted_close` and share volume are continuous across it (adjusted flat 0.7–1.4,
volume flat 0.33–3.0, volume tracking the split factor within 3×, 20-bar medians).

3,800 files carry at least one power-of-ten step, 4,992 steps in total, of which
4,970 are classifiable; the remaining 22 fall on a file's first or last bar, where
the volume test has no side to compare. Classification of the 4,970: 1,106 steps
are raw-column scale errors, 282 are consistent with genuine splits, 1,280 show
`adjusted_close` stepping as well, and 2,302 are indeterminate on the volume
test. **1,037 files — 2.04% of the store — carry at least one raw-column scale
error of KMI's signature.**

This is a lower bound and not a census. The indeterminate and
`adjusted_also_steps` groups are not cleared; they are undecided by this test.
KMI is the only affected file among the 39 measured by batch01, so the other
fifteen accepts are unaffected.

The consequence for this workstream is direct and unwelcome. The signed rule
answers weak date evidence by requiring numerical evidence drawn from the price
files, and roughly one file in fifty has a raw price column wrong by a power of
ten. The requirement remains correct — it caught KMI, which a date match alone
would have admitted — but a fingerprint miss now carries two candidate
explanations, wrong identity and wrong data, and only the volume-continuity test
separates them. Any future numeric fingerprint should be evaluated against a
locator that has passed that test.

## Scope not covered

`prompts/2026-09-07-claudecode-resolver-v150-amendment1.md` specifies six tasks;
this session was directed to a narrower scope and the following were not
attempted: the shared append-only evidence store, A2 Amendment 1 Cases 5 and 6,
reclassification of the 59 A2 symbols under the amended 1-5-4-2-3 ordering, the
re-census, and the duplicate-locator census across the 947 automatically resolved
symbols. That last item is identified in its own brief as the measurement most
likely to outrank the rest: FISV and FI overlap on 9,858 bars with 80.0%
agreement on unadjusted close but 20.9% on adjusted close, and adjusted close is
what returns are computed from. It remains unmeasured.

State on arrival: the resolver modules implemented segmentation, raw-bar price
evidence, A2 case signatures in the signed 1-4-2-3 order, coverage measurement
and the human review packet, but contained no multiplicity computation, no
vendor-floor rule, no band table and no adjudication of batch01. Those are what
this entry adds.

## Verification and prohibitions

New focused tests: 26 passed, covering separate first/last counters, unreadable
files excluded, absent pivots yielding unknown rather than unique, segment
boundaries never counted, the 1/2–3/4+ thresholds, vendor floors inadmissible at
every multiplicity including the CEG multiplicity-3 case, the four band values,
and KMI's tenfold miss remaining a miss. Full suite: 514 passed, 1 skipped, 1
failure — the pre-existing ETF bar-count failure (5,502 versus 5,499 journalled,
22 folds), unchanged, not fixed and not suppressed, as instructed. Ruff and mypy
clean on all new modules.

No panel was built. No price data was changed. No backtest was run. No synthetic
bar was created. No approval was applied and no A2 treatment was applied; A2
classifications remain proposals under the signed convention. Catalog names
remain display-only. Coverage remains separate from identity and remains unknown
wherever identity is unknown. A matching event vintage does not approve the
complete file, the membership mapping, or any stitch.

Two commits were made on explicit instruction, superseding the standing
no-commit rule in the v150 brief: `96003de` records the pre-existing working tree
as a save point, including 38 journal entries and the resolver modules;
`825758a` records this work. Neither contains an approval or an applied A2
treatment. `reports/` and `data/` are gitignored, so no report artifact and no
price data entered history; the artifacts regenerate from
`scripts/run_date_admissibility.py`.

## Note on repository location

The configured working directory for this session was `Documents/Woodland Fund/`,
which is empty apart from a `.claude-flow` directory. The repository is
`Documents/Trading Algorithim/`. No data was lost, but an automated run pointed at
the configured path would find nothing and could report an empty state as a
finding.
