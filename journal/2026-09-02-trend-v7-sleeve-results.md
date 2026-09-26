# 2026-09-02 — trend-v7-sleeve: results

Append-only. Pre-registered in
`journal/2026-09-02-trend-v7-sleeve-preregistration.md`; nothing below deviates
from it. Source: `reports/trend-v7-sleeve-stdout.txt`. Ledger:
`trend-v7-sleeve-etf` (264 rows) and `trend-v7-sleeve-deep` (855 rows).

Harness output. Nothing is promoted; §8 is Phase 3.

Reconstruction check passed before anything else ran: v2 rebuilt to 0.7004
(journalled 0.700) and v6 to 0.7807 (journalled 0.781).

## Headline: the direction change worked, and the load-bearing test passed

**A trend sleeve does improve a balanced portfolio, and it does so for
reasons the static control cannot supply.**

Deep history, 94 years, 5 bps, paired vs unmodified 60% MKT / 40% CASH:

| sleeve | w | ΔSharpe | 95% CI (boot) | p (boot) | p (HAC) | corr |
|---|---:|---:|---|---:|---:|---:|
| **trend** | 0.1 | **+0.026** | [+0.004, +0.052] | **0.033** | **0.010** | 0.997 |
| **trend** | 0.2 | **+0.038** | [+0.001, +0.077] | **0.048** | **0.022** | 0.989 |
| trend | 0.3 | +0.046 | [−0.005, +0.100] | 0.087 | 0.049 | 0.979 |
| static equity | 0.1 | −0.002 | [−0.014, +0.016] | 0.783 | 0.722 | 0.999 |
| static equity | 0.3 | **−0.022** | [−0.042, +0.000] | **0.037** | **0.015** | 0.997 |

ETF window, 21.8 years, same construction:

| sleeve | w | ΔSharpe | p (boot) | p (HAC) | corr |
|---|---:|---:|---:|---:|---:|
| **trend** | 0.1 | **+0.043** | 0.051 | **0.046** | 0.994 |
| trend | 0.2 | +0.083 | 0.070 | 0.058 | 0.976 |
| static multi-asset | 0.1 | **+0.000** | **0.987** | 0.987 | 0.998 |
| static multi-asset | 0.3 | +0.002 | 0.958 | 0.960 | 0.986 |

The pairing did what it was chosen to do. Against SPY (r = 0.78) the SE was
0.125 and nothing resolved; here at r = 0.99+ the SE falls to 0.010 and a
0.026 difference resolves at p = 0.010. **Same data, same 94 years — the power
came from asking a paired question.**

## The static control: the pre-registered test, and it is decisive

The pre-registration named this as load-bearing, because v6 showed the gain
came from diversification (1.44 → 2.47 effective bets) and the open question
was whether trend *timing* adds anything beyond holding the basket.

It does. Adding a static equal-weight multi-asset basket to 60/40 contributes
**exactly nothing** over 21.8 years (+0.0002, p = 0.987), and on 94 years a
static equal-weight industry sleeve is significantly **harmful** at w = 0.3
(−0.022, p = 0.015). The trend sleeve beats it head-to-head in both universes
(ETF w=0.1: 0.851 vs 0.809; deep w=0.1: 0.868 vs 0.840).

So the answer to the question this study was built to ask is yes: the timing
is doing work, not just the diversification.

## The sting: trend loses to embarrassingly simple alternatives

This was not the load-bearing control and it is the most important caveat here.

**ETF window — a static gold sleeve beats trend at every weight.**

| w | trend Sharpe | gold Sharpe | more defensive | static multi-asset |
|---:|---:|---:|---:|---:|
| 0.1 | 0.851 | **0.889** | 0.816 | 0.809 |
| 0.2 | 0.892 | **0.946** | 0.827 | 0.811 |
| 0.3 | 0.922 | **0.965** | 0.839 | 0.811 |

Gold's own paired improvement at w = 0.1 is +0.080 (p = 0.034) — nearly double
trend's +0.043, from a sleeve requiring no signal, no harness, and no turnover.

**Deep history — simply holding more cash matches trend, with tighter
significance.** More-defensive delivers +0.020 (p = 0.0009 HAC) at w = 0.1 and
+0.044 (p < 0.0001) at w = 0.3, against trend's +0.026 and +0.046. Head to
head at w = 0.1 trend leads 0.868 to 0.862 — a lead far inside noise.

Seven studies of trend machinery produce an improvement that a static gold
allocation exceeds in one window and a lower equity weight matches in the
other. That has to be stated in exactly those terms.

## What defends the trend result, and what does not

Honest for it: trend's improvement **replicates across both universes and
94 years**, at three weights, in two independent test procedures. Gold's edge
rests on one asset in one 21.8-year window during an exceptional bull run for
that asset, with intervals that widen fast (gold at w = 0.3: p = 0.195). No
gold series exists for the deep window, so we cannot check whether it survives
— and that is a limitation of our data, not evidence in trend's favour.

Honest against it: "their result is era-specific and ours replicates" is the
argument every strategy makes about its rivals. The measured fact is that on
the tradeable window, gold won.

## Effect size, plainly

The best case is +0.026 to +0.043 Sharpe on a balanced portfolio at a 10%
sleeve. That is real, it is small, and it is bought with a sleeve running
~5x annual turnover inside a portfolio that otherwise runs 0.23x.

## Trial accounting

21 distinct configurations as pre-registered (ETF 3 × 4, deep 3 × 3), all
logged including controls. Blend weights are reported as a curve; **no weight
is selected and none is called best.** Nothing was fitted, so the deflated
Sharpe hurdle is vacuous and carries no evidential weight — the paired
bootstrap and HAC tests are load-bearing, as pre-registered.

## What this does not establish

Not that trend has alpha. Not that 10% is the right weight. Not that the
sleeve beats the best simple alternative — on the ETF window it did not. The
§8 gate has still never run and nothing is promoted.

## Open question this raises for planning

Gold beat the trend sleeve on the only window we can trade. Before any
promotion conversation, that comparison deserves its own study — a gold sleeve
is a serious rival, not a strawman, and it was only in v7 as a control.
