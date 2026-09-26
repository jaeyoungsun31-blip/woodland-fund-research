# 2026-09-02 — Cash realism: the uninvested sleeve now earns the T-bill rate

Append-only. Engineering correctness fix, not a new study: no ledger rows, no
pre-registration needed, nothing promoted. Prior entries are NOT retro-edited
(rule 3) — this entry records what changes and what does not.

## The inconsistency

The deep-history universe carries `CASH` as an explicit asset, so v4's
defensive budget earns the one-month T-bill rate. The ETF universe had no such
asset and `backtest.run` hardcoded `gross = h @ r  # cash portion earns 0`, so
the same portfolio was scored under two different rules depending on which
universe it ran in. That is a correctness bug, not a modelling choice, and
every future ETF-window study would have inherited it.

Over the OOS window the rate is not a rounding error: it averages **1.78%
annualized and compounds to 47.3%** across 21.8 years.

## The fix

`woodland/cash.py` reads the daily rate from the **same Fama-French factors
file the deep-history universe already uses**, so both universes now take
their cash return from one series. `backtest.run` gains an optional
`risk_free` argument; the uninvested remainder `1 - sum(w)` earns it.

**Default is still zero.** That is deliberate: every number in the journal was
computed on the old path, and leaving it as the default is what keeps that
record verifiable rather than merely asserted. `scripts/run_cash_realism.py`
reproduces all four journalled Sharpes exactly (v2 0.700, v3 0.709, 60/40
0.806, vol-target 60/40 0.853) before reporting anything. Studies opt in.

Calendar: the factors file is published with a lag and ends 2026-06-30, so
**44 of 5,499 OOS bars (0.8%) carry the last known rate forward**. Alignment
is exact everywhere else — zero missing dates inside coverage. Carrying a
slow-moving bill rate forward for two months is defensible; carrying it for
years is not, so the helper errors past a 70-bar limit rather than leaving it
to a footnote, and reports the count either way.

## Who was actually exposed

Only strategies that hold cash. Average uninvested weight over the OOS window:

| | avg cash weight |
|---|---:|
| v2 ensemble | 0.11% |
| 60/40 | 0.00% |
| SPY buy&hold | 0.00% |
| vol-target 60/40 | 7.16% |
| **v3 voltarget** | **22.14%** |

Planning's prediction was right: v3 is the exposed one, because volatility
targeting parks unused exposure in cash by construction.

## (a) The return-series change: cash earns rf instead of 0

Sharpe still measured against rf=0, so this isolates the series change alone.

| series | CAGR old | CAGR new | Sharpe old | Sharpe new | Δ |
|---|---:|---:|---:|---:|---:|
| v2 ensemble | 9.72% | 9.72% | 0.700 | 0.700 | **+0.000** |
| 60/40 | 8.33% | 8.33% | 0.806 | 0.806 | **+0.000** |
| SPY buy&hold | 11.24% | 11.24% | 0.660 | 0.660 | +0.000 |
| vol-target 60/40 | 7.46% | 7.54% | 0.853 | 0.862 | +0.009 |
| **v3 voltarget** | 7.37% | **7.72%** | 0.709 | **0.739** | **+0.030** |

The point worth pulling out: **v3 gained more than its own comparator**
(+0.030 vs +0.009), because it held 22% cash against vol-targeted 60/40's 7%.
The old rule was quietly biased *against* v3 in precisely the comparison v3
existed to make. v3's max drawdown also improves, −22.64% to −21.37%.

## (b) The metric change: Sharpe against the real rf

Computed on the new series. Levels move a lot; this is the honest measurement.

| | Sharpe vs rf=0 | Sharpe vs real rf | Δ |
|---|---:|---:|---:|
| v2 ensemble | 0.700 | 0.581 | −0.120 |
| v3 voltarget | 0.739 | 0.575 | −0.164 |
| 60/40 | 0.806 | 0.639 | −0.167 |
| vol-target 60/40 | 0.862 | 0.663 | −0.200 |
| SPY buy&hold | 0.660 | 0.566 | −0.094 |

Every headline Sharpe this project has published is **0.09 to 0.20 too high**
as a risk-adjusted number. rf=0 was always flagged in `metrics.sharpe` as
overstating; this quantifies it.

## What changes, and what does not

Paired differences, through the stats module (10,000 resamples, block 21):

| comparison | basis | Δ | 95% CI | p (boot) | p (HAC) |
|---|---|---:|---|---:|---:|
| v2 − 60/40 | OLD | −0.106 | [−0.371, +0.158] | 0.433 | 0.417 |
| v2 − 60/40 | NEW series, rf=0 | −0.106 | [−0.371, +0.158] | 0.435 | 0.418 |
| v2 − 60/40 | NEW series, real rf | −0.058 | [−0.316, +0.199] | 0.659 | 0.652 |
| v3 − vt 60/40 | OLD | −0.144 | [−0.385, +0.088] | 0.234 | 0.242 |
| v3 − vt 60/40 | NEW series, rf=0 | −0.123 | [−0.365, +0.109] | 0.309 | 0.317 |
| v3 − vt 60/40 | NEW series, real rf | −0.087 | [−0.324, +0.139] | 0.463 | 0.474 |

**No conclusion changes.** Planning expected levels to move and paired
differences to move much less, and that is what happened: levels shift by up
to 0.20, the v2 difference by 0.048 and the v3 difference by 0.057.

Specifically:

* **Unaffected:** every v1, v2, v4 and v5 conclusion. v2 and 60/40 hold no
  cash, so their series are bit-identical; v5's schemes are fully invested;
  v4's rows sum to exactly 1.0, its defensive budget already going to the
  `CASH` asset (measured residual from intra-month drift: 0.057%, immaterial).
* **Improved but not overturned:** v3. Its headline rises 0.709 → 0.739 and
  the gap to vol-targeted 60/40 narrows by 40% (−0.144 → −0.087). The v3
  entry's conclusion — *vol targeting is a portfolio technique that helps
  everything, not an edge, and the trend overlay still trails vol-targeted
  60/40* — **survives on both bases** (0.739 vs 0.862 at rf=0; 0.575 vs 0.663
  against the real rate).
* **Nothing becomes significant.** Every comparison was indistinguishable from
  zero before and remains so; for v3 the p-value moves *away* from
  significance (0.234 → 0.463) even as the point estimate improves, because a
  smaller gap is harder to distinguish from no gap. Worth stating plainly so
  the narrowing is not mistaken for a strengthening result.

## Consequence for future work

Studies on the ETF window should pass `risk_free`; the default zero exists for
reproducing the record, not for new work. Whether the journalled headline
numbers should be *restated* on the new basis is a reporting-standard decision
for planning — raised as Q8, not assumed here.

## Forward note for the multi-asset pre-registration

Recorded now so it is not rediscovered later: including DBC caps the usable
sample near 2006. By this project's own power arithmetic
(`journal/2026-09-01-inference-existing-studies.md`), ~20 years cannot resolve
a 0.10 Sharpe difference — the smallest detectable effect at 80% power is
around 0.35. A DBC-inclusive multi-asset study must therefore be
pre-registered as **exploratory**, or use longer-history sleeves.

## Caveats

44 of 5,499 OOS bars carry a stale rate (0.8%, all after 2026-07-01). The
source-verification caveat is unchanged. rf=0 figures are retained throughout
for continuity, never as the honest number.
