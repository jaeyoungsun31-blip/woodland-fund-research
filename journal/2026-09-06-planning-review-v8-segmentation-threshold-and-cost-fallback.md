# Planning review — v8, two further defects and a latent cost-model defect

Date: 2026-09-06
Status: review (defects 3 and 4 block adjudication; defect 5 blocks training)
Artifact: `reports/security-resolver/2026-09-06-v8-resolver/`
Extends, does not supersede: `2026-09-06-planning-review-v8-two-defects.md`.
Defects 1 and 2 in that entry stand as written. Nothing here contradicts it.

## Independent confirmation of the MOB/RAL reversals

Verified by opening the parquet files, not by reading the packet.

```
MOB_old   483 bars   1997-12-31 -> 1999-11-30 (terminal): close +44.6%, volume 2.5x
RAL_old  4022 bars   2001-12-07 -> 2001-12-12 (terminal, segment 1): close +1.3%, volume 4.9x;
                     terminal close 0.06% below the $33.50 offer
                     2010-02-22 (segment 2, first bar): close ~818x segment 1's terminal
[price levels and volumes redacted in the public export]
```

Exxon closed Mobil 1999-11-30; Nestlé's Ralston Purina offer was $33.50.
Both reversals are correct and both rest on price evidence alone.

## Defect 3 — the 200-day segmentation threshold misses a real seam in `LB_old1`

`LB_old1` was split once, at the 7,566-day 1982→2003 gap. It contains a second
seam that the threshold does not reach:

```
2011-06-28 -> 2011-12-19: close +83.7%, volume 19.9x   [levels redacted]
gap 174 days | log price jump 0.61 | 60-bar volume median ratio 28.5x
```

The bar on the left of that seam is the terminal bar of `LB_old` — same date,
same close, same volume. `LB_old` is therefore a subset of what v8 calls
`LB_old1::segment2`, and `segment2` is two securities, not one.

The consequence is specific. `segment2` is presented as covering 2003-09-10 to
2021-08-02 and is `date_eligible` for LB's 2004–2021 membership windows. Its
right-hand half is L Brands (its 2015 high, 2019 low and terminal close are L
Brands'; levels redacted in the public export). Its left-hand half is a sub-$20 name with a five-figure daily
volume. A reviewer who accepts `segment2` on the strength of its right half
splices a microcap onto L Brands for 2003–2011. It is currently `unknown/low`,
so nothing is broken yet; it is a trap laid for the hand adjudication.

Measured blast radius. Scanning all 297 distinct candidate price files in the
packet for gaps of 45–200 days accompanied by a log price jump above 0.25 or a
60-bar volume median ratio outside [0.2, 5]:

```
DYN_old   2012-07-05 -> 2012-10-03   90d  close +3171%   (DYN unknown)
IGT_old   2008-07-18 -> 2008-10-20   94d  close -30.3%   (IGT reject/unknown)
IGT_old   2010-12-23 -> 2011-03-18   85d  close +40.3%   (IGT reject/unknown)
LB_old1   2011-06-28 -> 2011-12-19  174d  close +83.6%   (LB reject/unknown)
SGP_old2  2010-11-22 -> 2011-05-31  190d  close +50.0%   (SGP reject)
TOS_old1  2010-12-16 -> 2011-04-26  131d  close +214.8%  (TOS reject)
[price levels redacted in the public export]
```

Six seams in five files. **None of them sits under a current `accept`**, so v8
has produced no wrong acceptance from this defect. `SGP_old2` and `TOS_old1`
are already-spliced files carrying a second, undetected seam.

Recommended fix, and the reason it is a flag and not a split: auto-splitting
these six changes `date_eligible` for IGT, whose two 2008/2009 records already
moved to unique-live matches because of the first split. Segmentation changes
resolution counts and must therefore carry the same human sign-off as
acceptance. Add the joint predicate above as a **report-only seam flag** on the
packet row, and refuse `accept` on any candidate carrying an unadjudicated flag.

## Defect 4 — the volume field is not stable within a single file

`LB_old1`, prices continuous, no gap, no split:

```
2007-11-01  close (base)    volume (base)
2007-11-15  close -14.1%    volume 1.63x
2008-01-30  close -31.7%    volume 0.002x
2008-02-15  close -26.6%    volume 0.004x
[levels redacted in the public export]
```

A 100x collapse in daily volume across a continuous price path. This is a
vendor or venue change in the volume field, not a liquidity event.

This matters because `last_bar_volume_ratio` — terminal bar over the median of
the 60 preceding bars — is the primary discriminator behind all 78
`accept/medium` suggestions, and a 60-bar window can sit entirely on one side
of a shift like this. The ratio is not a reliable statistic on its own.

MOB and RAL survive because their price-level and terminal-price evidence is
independently decisive: a 1997 price history excludes a 2022 ADS, and a
terminal close 0.06% below a $33.50 offer excludes everything else. A medium accept resting only on the
volume ratio does not carry that. Finding 2 of the standing findings should be
read as **price level and terminal price are load-bearing; volume magnitude is
corroborating only.**

Related, and separate: `RAL_old::segment2` prints at roughly 800x segment 1's scale and then
rises about 5x (levels redacted in the public export). That is not
a US-dollar equity. A foreign-currency series is sitting inside a `.US` file.
Price level is admissible evidence only after a currency-plausibility screen,
and any accepted segment must be checked for a mid-file currency change.

## Defect 5 — A3's fallback rule collapses the per-symbol cost engine to a scalar

A3 states: *unmeasured symbols take the highest measured per-symbol value.*
Measured rates come from the Alpaca drift monitor, whose coverage is the 22
live ETFs. The constituent panel contains ~500 names per date, essentially none
of them measured. Under A3 as written, every constituent takes `c_max`, and

    sum_i( c_i * |dw_i| )  with  c_i == c_max  ==  c_max * sum_i |dw_i|

which is the scalar model the engine change exists to replace. The engine would
be rewritten, the measured/fallback split would be reported honestly as
~0/500, and nothing would change numerically.

The bias is not neutral. `c_max` across measured ETFs is on the order of 0.5
bps (SPY 0.130, IEF 0.542). A 1999 mid-cap's round-trip cost is one to two
orders of magnitude above that. A3's fallback, written for a 22-ETF universe,
prices a survivorship-free constituent panel at ETF spreads, which flatters
turnover-heavy strategies exactly where the new breadth would let them trade.
A3 needs an amendment before the engine is built, not after.

## A2 sizing — the default cannot be a single value

EODHD's `/api/eod` carries no terminal corporate-action value, so "absent a
documented provider value" is the universal case here, not the exception. A2's
stated conservative default — total loss on the final position — applied
universally would mark MOB at −100% on a terminal bar that printed into a
completed merger, and RAL at −100% against a $33.50 cash offer.

Terminal signature across the 149 archived candidate rows carrying a volume
ratio:

```
spike >= 5x with terminal close >= $1   (cash-exit signature)   44
terminal close < $1                     (failure signature)      6
neither                                 (ambiguous)             99
```

The ambiguous class is the majority. A single default value is wrong for two
thirds of the population in one direction or the other.

## Truncation population is small and bounded

Symbols in the packet whose only date failure is `dates_last` — the membership
window outlasts the price history, with no `dates_first` failure anywhere:

```
ABI  BSC  COV  FB  HET  PEAK  RTN   (7 symbols)
```

Seven names, all acquisitions or ticker changes. This is small enough to
adjudicate by hand once A2 declares the treatment.
