# Planning review — v7 packet accepted; my `MOB`/`RAL` counterexamples were wrong

Date: 2026-09-06
Status: review + correction (mine)
Artifact: `reports/security-resolver/2026-09-06-v7-resolver/`

## The build is sound

- `unique_live_candidate` resolved 948 symbols against a predicted ~961. Lower,
  not higher: the archived-eligibility clause blocked 13 symbols that would
  otherwise have auto-resolved. The guard worked in the safe direction.
- `no_candidates_absent` = 29, matching prediction exactly. No web lookup of
  names occurred (hard rule 5 held).
- All 1,021 reuse rows across 136 symbols remain rejected. `_dates` intact.
- `RDS.A` normalized to `RDS-A` and then failed dates (prices begin 2005,
  membership 1999–2002). Correct: the Royal Dutch Shell ADR dates from the 2005
  unification; the 1999–2002 seat was held under a different security.

## Correction — four of the eleven suggested verdicts are wrong, and I caused it

The v7 prompt gave `MOB_old` (Mobilicom) and `RAL_old` (Ralliant) as worked
counterexamples for hard rule 4. I asserted both from the catalog `Name` without
checking the price series. Both assertions are false.

`MOB_old` — 483 bars, 1997-12-31..1999-11-30:

```
1997-12-31 -> 1999-11-30 (last bar): close +44.6%, volume 2.5x
[price levels and volumes redacted in the public export]
```

Median volume ~1.6M/day. Exxon completed its acquisition of Mobil Corp on
1999-11-30. The file is Mobil. Mobilicom Ltd is an Israeli micro-cap ADS listed
in 2022 and cannot hold 1997–1999 history.

`RAL_old` — 4,022 bars, 1997-12-31..2022-03-02, with an 8.2-year interior gap:

```
1997-12-31 -> 2001-12-12 (last bar before the gap): close -50.1%,
last-bar volume ~7x median   [levels redacted in the public export]
gap 2001-12-12 -> 2010-02-22 (2,994 days)
```

Nestlé acquired Ralston Purina at $33.50/share, completing December 2001. The
terminal close is 0.06% below the offer, on about 7x median volume. Segment 1 is Ralston Purina.
"Ralliant Corporation" describes only the post-2010 segment.

The suggested verdicts `reject/high` on MOB (2 rows) and RAL (2 rows) must be
reversed or re-examined. The remaining seven (BSC, APC, Q, SEG, SGP accepts;
LB rejects) stand.

## Root cause — the archived catalog `Name` is not the file's name

EODHD attaches the **current or last** name of a symbol slot to the archived
record, not the name of the security whose bars the file contains. It is
therefore unreliable in both directions: it wrongly rejects (MOB, RAL) and would
wrongly accept wherever a slot's last occupant happens to resemble its first.

Consequence for
`2026-09-06-planning-finding-archived-old-records-hold-the-missing-histories.md`:
the recommendation to pull a constituent name list and match on names is
downgraded. Matching a reliable constituent name against an unreliable catalog
name certifies nothing. A name list remains useful as the statement of *which
company held the seat*, but the verification must run against price evidence.

## Evidence channels that are reliable

1. **Date bounds** — first and last bar against the membership window.
2. **Interior trading gaps** — a gap over ~200 calendar days in a US daily
   series is a slot-reuse seam, not a halt. Segment the file at the seam; each
   segment becomes a candidate with its own bounds.
3. **Price level and volume** — order of magnitude discriminates a large-cap
   index constituent from a micro-cap successor.
4. **The terminal bar** — a completed cash merger prints at the deal price on
   elevated volume. `RAL_old`'s terminal close 0.06% below Nestlé's $33.50 offer is a fingerprint.

## Splice census

Of 141 archived files referenced in the review packet, **132 are single
securities** (no gap over 200 days) and **9 are spliced**:

```
DNB_old   2000-10-02 -> 2003-09-10  (1,073d)
IGT_old   2008-10-20 -> 2009-08-26    (310d)
LB_old1   1982-12-23 -> 2003-09-10  (7,566d)
LIFE_old1 three seams -> four segments
Q_old1    2011-03-31 -> 2013-05-09    (770d)
RAL_old   2001-12-12 -> 2010-02-22  (2,994d)
SGP_old2  2009-11-20 -> 2010-09-29    (313d)
TEK_old   2007-12-17 -> 2008-12-17    (366d)
TOS_old1  2008-12-16 -> 2010-05-07    (507d)
```

The archived pile is mostly trustworthy as data and untrustworthy as labels.

## On the packet's 316 `unknown` / `low` rows

Codex issued verdicts only for the symbols named in the prompt and journals, and
marked everything else `unknown/low` with the note "catalog identity only;
independent constituent identity not supplied." Given the name defect above,
that refusal was correct — it had no reliable evidence channel to reason from.
It now has four.

## Do not approve

No verdict in `review-packet.csv` should be ingested until the packet is rebuilt
with splice segmentation and the price-evidence columns.
