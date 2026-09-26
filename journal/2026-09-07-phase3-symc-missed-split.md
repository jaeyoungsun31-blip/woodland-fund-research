# SYMC: a two-for-one split recorded as a 48.6% loss, in the column the panel reads

Date: 2026-09-07
Status: defect confirmed from the store's own data; no price changed, nothing corrected
Severity: the largest single-constituent data defect found in this project
Artifacts: `reports/security-resolver/2026-09-07-locator-adjudication/`,
`reports/security-resolver/2026-09-07-missed-event-screen/`
Related: `2026-09-07-phase3-locator-adjudication.md`,
`2026-09-07-phase3-scale-scan-correction.md` (KMI, the mirror image)

## The defect

`SYMC.US.parquet`, `GEN.US.parquet` and `NLOK.US.parquet` carry **identical raw
closes** across 2004-12-01, where Symantec's raw close falls 48.61%:

| file | raw close change, 2004-11-30 → 2004-12-01 | adjusted return |
|---|---:|---:|
| `GEN` | −48.61% | **+2.77%** |
| `NLOK` | −48.61% | **+2.77%** |
| `SYMC` | −48.61% | **-48.61%** |

`SYMC`'s `adjusted_close` follows its `close` straight through the event:
down 48.61%. A two-for-one split is not a 48.6% loss. Two of the three
files for the same entity agree and one does not, and the disagreement needs no
external source to adjudicate — the price series itself shows a split, and an
adjusted series exists precisely to remove it.

Over Symantec's membership window, 2004-01-07 to 2019-10-18, 3,974 bars:

| file | cumulative adjusted return |
|---|---:|
| `GEN` | **+79.06%** |
| `NLOK` | **+79.05%** |
| `SYMC` | **-11.86%** |

**90.9 percentage points on a single constituent, over sixteen years of
membership, and `SYMC` is the file the v9 resolver selected.**

The screen written for this defect finds a **second** one in the same file:
2003-11-20, adjusted return -50.22%, price ratio 0.4978. That one falls outside
the membership window and so never reaches a panel, but it means the file's
adjustment series is wrong at more than one point rather than at an isolated
bad bar.

## Why this is worse than KMI

KMI's defect, recorded on 2026-09-07, inflated the raw OHLC columns tenfold for
989 bars while `adjusted_close` stayed continuous. The panel reads
`adjusted_close`, so no panel result was ever exposed to it; the exposure was to
the numerical fingerprint method, which reads raw close by signed instruction.

`SYMC` is the mirror image. The raw column is right and **`adjusted_close` is
wrong** — and that is the column returns are computed from. This is the first
confirmed defect in this store that reaches a result directly.

Taken together the two say something that neither says alone: the store's
defects are not confined to one column, and a check that validates one column
does not validate the other.

## `check_adjustment` cannot see it, and the reason is structural

`woodland/data.py::check_adjustment` returns **`verdict: ok`** for this file:
worst factor drop -7.62e-06 against a tolerance of 1e-4, terminal factor 1.0.

It has to. The check tests `adj_close/close` for *decreasing* and for a terminal
value away from 1.0. Across 2004-12-01 that factor is 0.705775 before and
0.705773 after. Because the adjusted column tracked the raw column through the
event, the ratio never moved — which is exactly what the check demands.

So the store's integrity check is now on record as blind in **both**
directions:

* it missed KMI's tenfold factor *increase*, because it only flags decreases;
* it misses a missed split, because a missed event leaves the factor *flat*.

## The screen, and its honest limit

`check_missed_events` is added to `woodland/data.py` for the second signature: a
single-day adjusted return beyond a declared threshold with the adjustment
factor unchanged across it.

**It is a screen, not a detector, and it cannot be made into one from inside a
single file.** A genuine 30% earnings crash has exactly the same signature as a
missed split: a large move with no adjustment, because there was nothing to
adjust. Symantec's own file demonstrates both — 2004-12-01 is a missed split
and 2018-05-11 (-33.1%) is a real crash on an internal-audit disclosure, and
the screen cannot tell them apart. Volume cannot separate them either, since
EODHD split-adjusts historical volume.

Run over the 947 automatically resolved locators, in-window, at a 25% threshold
it flags **388 symbols and 1,820 candidate days**; 143 of those days sit within
3% of a simple split ratio. The threshold curve is in the report. Separating the
classes needs a cited corporate-action calendar, which this store does not
carry — the same missing artefact the scale-scan correction reached from the
other direction.

## What the screen found that was not looked for

Applying it exposed a defect class more damaging than a missed split: files
whose raw series are simply broken. `ACS` alternates 33.51, 3.20, 31.50, 3.10,
33.50 on consecutive days. `CBE` sits frozen at 14.6 with a one-day excursion to
143.2. `WFT` records **zero change on 100% of its 904 in-window bars**. `CFC`
carries a single +450,325% day.

In the constituent panel built on 2026-09-07 this is not a rounding matter. The
equal-weighted cross-sectional mean of the 942-symbol panel has an annualised
volatility of **434%**; dropping the 67 quality-flagged symbols takes it to
**20.5%**, and the cumulative return from 5.3e25% to 1,336%. The panel is
unusable until that class is ruled on.

## Prohibitions

No price data was changed. `SYMC.US.parquet` is exactly as the vendor shipped
it. No bar was synthesised, no backtest was run, no approval or A2 treatment was
applied, and no resolver status or locator preference was written. The panel
built the same day reads `GEN` in place of `SYMC` as a declared, recorded
panel-construction substitution, not as a resolver change.
