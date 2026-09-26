# 2026-09-02 — xsmom-v10-industry: results

Append-only. Pre-registered in `journal/2026-09-02-xsmom-v10-preregistration.md`
(including the embargo amendment to 252 bars); nothing below deviates from it.
Executed by the planning session. Script: `scripts/run_xsmom_study.py`; raw
output: `reports/xsmom-v10-stdout.txt`.

OOS 1932-05-04 .. 2026-06-30, 24,537 bars (94.1y), **95 folds**, 252-bar
embargo, 5 bps.

## Result: momentum beats the market, and does NOT beat equal-weighting

| portfolio @5bps | CAGR | vol | Sharpe | max DD | DD days | turnover |
|---|---:|---:|---:|---:|---:|---:|
| xsmom top-3 | 13.64% | 17.27% | **0.827** | −57.5% | 2,484 | **5.23** |
| equal-weight 12 industries | 12.12% | 15.89% | 0.800 | −54.2% | 1,828 | **0.27** |
| MKT buy&hold | 11.35% | 16.53% | 0.733 | −54.6% | 1,895 | 0.00 |
| 60% MKT / 40% CASH | 8.35% | 9.83% | **0.865** | −36.1% | 1,825 | 0.20 |

| comparison | ΔSharpe | 95% CI | p (boot) | p (HAC) | corr |
|---|---:|---|---:|---:|---:|
| xsmom − **equal-weight 12** | **+0.028** | [−0.059, +0.114] | **0.517** | 0.526 | 0.916 |
| xsmom − MKT | **+0.094** | [+0.008, +0.181] | **0.033** | 0.033 | 0.916 |
| xsmom − 60/40 | −0.038 | [−0.126, +0.050] | 0.394 | 0.390 | 0.914 |

## The decomposition the load-bearing control was built to expose

Momentum's advantage over the market is real and significant (+0.094,
p = 0.033). But split it:

* **MKT → equal-weight 12 industries: +0.067** — pure de-concentration, no
  signal, no ranking, 0.27 turnover.
* **equal-weight → momentum ranking: +0.028** — the actual signal, **not
  significant** (p = 0.52).

**Roughly 70% of the apparent momentum edge is equal-weighting, not momentum.**
Rank the industries or don't; on this cross-section the data cannot tell the
difference — and the ranking costs **20x the turnover** (5.23 vs 0.27) plus a
deeper drawdown (−57.5% vs −54.2%) and 656 more days underwater.

This is the mirror image of v7. There the trend sleeve beat its static control
decisively, and timing earned its keep. Here the ranking does not clear its
own control, and the honest verdict is that it does not.

## Decade breakdown @5bps

| decade | CAGR | Sharpe | max DD |
|---|---:|---:|---:|
| 1930s | 14.00% | 0.618 | −49.8% |
| 1940s | 8.79% | 0.698 | −42.1% |
| 1950s | 20.16% | **1.597** | −21.9% |
| 1960s | 13.73% | 1.166 | −28.3% |
| 1970s | 5.70% | 0.487 | −46.7% |
| 1980s | 20.30% | 1.201 | −35.2% |
| 1990s | 21.80% | 1.411 | −18.6% |
| 2000s | 3.28% | **0.259** | −44.8% |
| 2010s | 14.10% | 0.891 | −25.2% |
| 2020s | 18.47% | 0.821 | −38.0% |

Enormously regime-dependent. The 2000s are the documented momentum-crash era
and the strategy earned 3.3% a year through it with a −44.8% drawdown.

## Decay check — and a contrast worth recording

v4 found the time-series trend edge concentrated before 1980. Cross-sectional
momentum shows the **opposite** pattern:

| era | vs equal-weight | vs MKT |
|---|---|---|
| 1932-1979 (50.9y) | −0.008, p = 0.884 | +0.075, p = 0.221 |
| 1980-2026 (46.5y) | +0.064, p = 0.339 | +0.113, p = 0.083 |

If anything it is stronger in the modern era, not weaker. Neither era resolves
against equal-weight. Recorded because the two strategy families evidently do
not share a decay profile, which is itself informative about whether "the edge
is being arbitraged away" is a general claim or a family-specific one.

## Trial accounting

One configuration, no selection, no fitting, k fixed at 3. Deflation vacuous;
the paired tests are load-bearing. Embargo amendment to 252 bars declared in
advance and applied only to this study.

## What this cannot conclude

Twelve industries is a **coarse** cross-section — the finding may be about
granularity rather than about momentum. Stock-level decile portfolios sorted
directly on momentum are the proper test and are unavailable here only because
neither sandbox can reach the Ken French server; that download runs from the
user's own terminal. Until then, the conclusion is specifically: **momentum
ranking across 12 industries does not beat equally weighting those same 12
industries.**

Industry portfolios are frictionless academic constructs, not instruments.
Nothing is promoted; §8 is Phase 3.
