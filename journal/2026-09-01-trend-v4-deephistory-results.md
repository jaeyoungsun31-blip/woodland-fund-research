# 2026-09-01 — trend-v4-deephistory: results

Append-only. Pre-registered in
`journal/2026-09-01-trend-v4-deephistory-preregistration.md`; nothing below
deviates from it. Ledger: `trend-v4-deephistory-selection` (7 configs, 665
rows) and `trend-v4-deephistory-ensemble` (1 config, 95 rows).

**These are frictionless academic series, not tradeable securities.** No index
fund existed for most of this window, industry portfolios are not purchasable,
and real 1930s costs dwarf 10 bps. Read everything below as evidence about the
*signal*, never as a claim that the *strategy* was harvestable.

Harness output. Nothing is promoted; §8 is Phase 3.

Window: OOS 1932-03-15 .. 2026-06-30, 24,579 bars (**97.5 years**), 95 folds.

## 1. v1's question, answered: the instability is intrinsic

v1 raised it — 22 ETF folds selected 6 of 7 lookbacks with 10 switches — and
asked whether 5x the data would settle the parameter down.

**It does not.** On 95 folds the selection uses **all seven** lookbacks, with
**44 switches across 94 transitions (46.8%)**. The v1 reference rate was
**47.6%**. Four and a half times the data moved the switch rate by less than
one percentage point.

Selection counts: `{4: 29, 5: 16, 6: 8, 7: 3, 8: 5, 9: 7, 10: 27}` — bimodal at
the ends of the grid, which is what a coin-flip between "fast" and "slow"
looks like, not a parameter with an optimum the training window can find.

This retires the small-sample explanation. A five-year train window cannot
identify a trend lookback, and no plausible amount of history fixes that.

## 2. The ensemble beats selection — and now the sample can prove it

| | Sharpe @5bps | 95% CI |
|---|---:|---|
| v4 ensemble | **0.861** | [0.640, 1.104] |
| v4 selection | 0.799 | [0.575, 1.043] |

Difference **+0.063**, 95% CI [+0.009, +0.117], **p = 0.023** (bootstrap) /
0.025 (HAC). Statistically significant.

On the ETF window this comparison could never have been resolved. Here it is,
and it independently confirms the v2 hypothesis on a different universe over
4.5x the span: **averaging the lookbacks beats choosing one.** Not choosing is
the better decision, which follows directly from finding 1.

## 3. Full comparison, identical window

| Portfolio | CAGR | Ann. vol | Sharpe | Max DD | Turnover |
|---|---:|---:|---:|---:|---:|
| v4 ensemble @0bps | 11.66% | 13.54% | 0.882 | −40.68% | 5.67 |
| **v4 ensemble @5bps** | **11.34%** | **13.54%** | **0.861** | **−41.95%** | **5.67** |
| v4 ensemble @10bps | 11.02% | 13.54% | 0.840 | −43.19% | 5.67 |
| v4 selection @5bps | 10.64% | 13.88% | 0.799 | −51.36% | 7.06 |
| MKT buy&hold | 10.94% | 16.57% | 0.710 | −54.57% | 0.00 |
| 60% MKT / 40% CASH @5bps | 8.12% | 9.86% | 0.841 | −36.09% | 0.21 |

## 4. The first statistically significant edge this project has produced

| comparison | ΔSharpe | 95% CI | p (boot) | p (HAC) |
|---|---:|---|---:|---:|
| ensemble − MKT | **+0.152** | [+0.032, +0.277] | **0.014** | **0.009** |
| ensemble − 60% MKT/40% CASH | +0.020 | [−0.100, +0.147] | 0.747 | 0.732 |
| ensemble − selection | +0.063 | [+0.009, +0.117] | 0.023 | 0.025 |

**Against equities the trend ensemble wins, significantly**, and with a much
smaller drawdown (−41.9% vs −54.6%). This is the first result in the project
that survives a real significance test.

**Against the balanced portfolio it is a dead heat** — and this time the null
is informative. HAC SE is 0.058, so the interval rules out any difference
larger than about ±0.13 in either direction. On the ETF window the same
comparison had SE 0.125 and could rule out almost nothing. Here we can say
something substantive: over 97.5 years, a monthly trend rule across twelve
industries earns about what a static 60/40-style mix earns, at 28x the
turnover.

The predicted SE from the pre-registration (~0.06 on 97.5y, down from 0.125 on
21.8y) came out at 0.058. The power arithmetic in
`journal/2026-09-01-inference-existing-studies.md` holds.

## 5. By decade, and an honest look at decay

| decade | CAGR | Sharpe | max DD |
|---|---:|---:|---:|
| 1930s | 12.29% | 0.649 | −38.1% |
| 1940s | 6.75% | 0.652 | −36.3% |
| 1950s | 18.46% | **1.912** | −15.1% |
| 1960s | 12.96% | 1.446 | −18.4% |
| 1970s | 7.65% | 0.743 | −30.2% |
| 1980s | 16.75% | 1.137 | −33.0% |
| 1990s | 15.31% | 1.227 | −20.4% |
| 2000s | 4.32% | **0.363** | −31.5% |
| 2010s | 9.61% | 0.769 | −21.2% |
| 2020s | 10.36% | 0.641 | −33.6% |

Splitting the OOS record in half and re-running the same test:

| comparison | 1932-1979 (51.0y) | 1980-2026 (46.5y) |
|---|---|---|
| ensemble − MKT | **+0.235**, CI [+0.067, +0.421], p = 0.013 | +0.071, CI [−0.100, +0.239], p = 0.406 |
| ensemble − 60/40 analogue | +0.126, CI [−0.043, +0.312], p = 0.162 | −0.084, CI [−0.257, +0.088], p = 0.336 |

The point estimates roughly halve, and the edge over equities loses
significance in the modern era. **That is suggestive of decay and it does not
establish it.** The two eras' confidence intervals overlap heavily
([+0.067, +0.421] against [−0.100, +0.239]), so the difference between the two
differences is not itself distinguishable from zero. Splitting a sample in half
and observing that one half is significant while the other is not is a
well-known way to manufacture a decay story; I am not making that claim. What
can be said: the modern half alone does **not** show a significant edge over
equities, and the whole-sample significance is carried substantially by the
pre-1980 era.

## 6. Deflated Sharpe

Ensemble @5bps: Sharpe 0.86, one distinct config, SR0 = 0.00, DSR = 1.000.
Selection @5bps: Sharpe 0.80, 7 configs, train-Sharpe spread 0.087, SR0 = 0.04,
DSR = 1.000. Per the Q2 decision the effective-breadth note is attached: these
searches are narrow, so the DSR hurdle is weak and the number should not be
read as strong evidence on its own. The bootstrap and HAC tests in §4 are the
load-bearing statistics here, not the DSR.

## 7. Caveats

Frictionless academic series, as stated at the top — the single largest
qualifier on everything here. Turnover of 5.67 annually against 0.21 for the
static mix would have been ruinous at historical commission levels; the cost
scenarios (0/5/10 bps) are anachronistic for the early decades by a wide and
unquantified margin. `60% MKT / 40% CASH` is a declared deviation from binding
rule 5 and is a weaker baseline than a real 60/40, because T-bills are not
ten-year Treasuries (Q6). Sharpes use rf = 0, which flatters every level on a
window whose average T-bill rate was 3.06%; differences are much less affected.
Skew is −0.77 and excess kurtosis 20.7, so normal-theory intuition understates
tail risk throughout.
