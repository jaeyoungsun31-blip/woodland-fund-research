# 2026-09-02 — trend-v6-multiasset: results

Append-only. Pre-registered in
`journal/2026-09-02-trend-v6-multiasset-preregistration.md`; nothing below
deviates from it, including the expectation — recorded in advance — that the
Sharpe difference might be unresolvable while the diversification improved.
Ledger: `trend-v6-multiasset` and `trend-v6-multiasset-dbc`, 1 config x 22
folds each.

Harness output. Nothing is promoted; §8 is Phase 3.

OOS 2004-10-22 .. 2026-09-01, 5,499 bars (21.8y) — **identical window to v2**.
All series, v2 included, run through the cash-realistic engine so both sides
are scored under the same rules.

## 1. The diversification claim — decisive

This is what the window can support, and it is not a close call.

| universe | sleeves | avg pairwise corr | range | DR | **effective bets** |
|---|---:|---:|---|---:|---:|
| v2 9 US equity sectors | 9 | **0.650** | 0.479 … 0.858 | 1.202 | **1.44** |
| v6 multi-asset | 6 | **0.179** | −0.297 … 0.911 | 1.573 | **2.47** |
| v6 + DBC | 7 | 0.182 | −0.303 … 0.911 | 1.610 | 2.59 |

**Nine US equity sectors are worth about 1.4 independent bets.** Not nine —
1.4. The most correlated pair is XLB/XLI at 0.858, and even the *least*
correlated sector pair, XLE/XLP at 0.479, is more correlated than the
*average* multi-asset pair at 0.179. Diversifying across nine labels for one
bet is the thing this project has been doing for five studies.

Six asset classes give **2.47** effective bets — a 71% improvement, and
achieved with *fewer* holdings. Realized strategy weights give essentially the
same answer (2.35), so this is not an artefact of assuming equal weighting.

Worth stating in the other direction too: **six sleeves are not six bets**.
The most correlated multi-asset pair is TLT/IEF at 0.911 — two Treasury
maturities are one duration bet wearing two labels. The least correlated is
SPY/TLT at **−0.297**, the equity/duration hedge, which is where most of the
gain comes from.

## 2. Risk improved measurably; return did not

| Portfolio @5bps | CAGR | Ann. vol | Sharpe rf=0 | Sharpe vs rf | Max DD | Turnover |
|---|---:|---:|---:|---:|---:|---:|
| **v6 multi-asset** | 8.41% | **11.14%** | **0.781** | **0.621** | **−21.96%** | **5.15** |
| v6 + DBC | 8.03% | 11.33% | 0.738 | 0.581 | −26.91% | 5.25 |
| v2 9-sector | 9.72% | 14.82% | 0.700 | 0.581 | −37.62% | 5.78 |
| SPY buy&hold | 11.24% | 18.84% | 0.660 | 0.566 | −55.19% | 0.00 |
| 60/40 | 8.33% | 10.62% | 0.806 | 0.639 | −32.34% | 0.23 |
| vol-target 60/40 | 7.54% | 8.89% | **0.862** | **0.663** | −20.85% | 0.53 |

Against v2 the multi-asset version cuts volatility by a quarter, **cuts the
maximum drawdown nearly in half**, and trades less. Tails improve too:

| | skew | excess kurtosis | worst day | best day |
|---|---:|---:|---:|---:|
| v2 9-sector | −0.44 | 7.40 | **−8.74%** | +7.60% |
| v6 multi-asset | −0.21 | **3.39** | **−4.13%** | +3.91% |

The worst single day halves. Those are *estimable* quantities on 21.8 years;
the Sharpe difference is not, which is the next section.

It still does not beat the balanced baselines: 60/40 at 0.806 and
vol-targeted 60/40 at 0.862 remain ahead of 0.781 on Sharpe, though v6's
drawdown (−21.96%) now roughly matches vol-targeted 60/40's (−20.85%) with a
higher CAGR.

## 3. The headline Sharpe comparison — and a premise that did not hold

| comparison | corr | ΔSharpe | 95% CI | p (boot) | p (HAC) | SE |
|---|---:|---:|---|---:|---:|---:|
| v6 − v2 9-sector | 0.526 | +0.080 | [−0.291, +0.442] | 0.674 | 0.669 | 0.188 |
| v6 − SPY | 0.330 | +0.121 | [−0.313, +0.546] | 0.591 | 0.571 | 0.213 |
| v6 − 60/40 | 0.412 | −0.026 | [−0.452, +0.386] | 0.908 | 0.903 | 0.209 |
| v6 − vol-target 60/40 | 0.484 | −0.082 | [−0.492, +0.318] | 0.697 | 0.680 | 0.198 |
| +DBC − v6 | 0.926 | −0.043 | [−0.236, +0.134] | 0.647 | 0.628 | 0.088 |

**None is distinguishable from zero.** More usefully, the pre-registered
expectation about *why* was wrong in an instructive way.

The handoff reasoned that because the two strategies would be correlated, the
paired CI would be tight enough to resolve a real difference. Pairing does
work that way — v5's inverse-vol scheme correlated **0.9957** with v2 and gave
an SE of **0.020**. But v6 correlates with v2 only **0.526**, and the paired SE
comes out at **0.188** — *wider* than the ~0.125 typical of same-universe
comparisons on this window.

**The diversification that makes the multi-asset portfolio attractive is
exactly what makes it hard to compare.** Two strategies sharing most of their
risk have a well-determined difference; two strategies sharing half their risk
do not. The tighter the relationship, the sharper the comparison — and this
study deliberately broke the relationship. That tension is worth carrying into
any future gate design: the challengers most worth promoting will tend to be
the ones the statistics can say least about.

The one comparison this sample *does* constrain is the nested one: +DBC vs
primary correlates 0.926, giving SE 0.088 and an interval that rules out
commodities adding more than **+0.13** Sharpe. The point estimate is negative
(−0.043). DBC did not help.

## 4. Sub-periods @5bps

| Period | v6 multi-asset | v2 9-sector | v6 max DD | v2 max DD |
|---|---:|---:|---:|---:|
| 2004-10-22..2008-01-01 | **1.340** | 1.022 | −17.5% | −11.2% |
| 2008-01-01..2015-01-01 | **0.719** | 0.626 | **−17.4%** | −36.0% |
| 2015-01-01..2020-01-01 | **0.221** | 0.691 | −22.0% | −15.6% |
| 2020-01-01..2022-01-01 | **1.224** | 0.979 | −10.5% | −23.4% |
| 2022-01-01..2026-09-01 | **0.776** | 0.527 | −15.1% | −18.1% |

Better in four of five, and the GFC period is the standout — a −17.4% drawdown
against v2's −36.0%. The exception is **2015-2020: Sharpe 0.221, CAGR 1.6%,
654 days in drawdown**, a stretch when bonds and gold went nowhere while
equities trended steadily up, so a diversified trend portfolio held its
defensive sleeves and lagged a concentrated equity one. That is the honest
cost of diversification, not a bug, and it is the sub-period a reader should
look at hardest.

## 5. Deflated Sharpe

Multi-asset 0.78, +DBC 0.74; one distinct config each, SR0 = 0.00, DSR 1.000.
Per the Q2 decision the effective-breadth note is attached: a single-config
study has no search breadth, so the DSR hurdle is vacuous and carries no
evidential weight here. The paired tests in §3 are the load-bearing
statistics — and they are null.

## 6. External validation against AQR's published TSMOM factor

Retrieved successfully: `Time-Series-Momentum-Factors-Monthly.xlsx`, 497
monthly observations 1985-01-31 .. 2026-05-29, stored with a source hash
(`data/aqr_tsmom_monthly_provenance.json`). 185 overlapping months.

| series | corr | beta | R² |
|---|---:|---:|---:|
| **v6 multi-asset** | **0.151** | 0.113 | 0.023 |
| **v6 + DBC** | **0.207** | 0.158 | 0.043 |
| v2 9-sector | **−0.003** | −0.003 | 0.000 |
| SPY buy&hold | −0.143 | −0.169 | 0.020 |

The ordering is the informative part. Our multi-asset implementation has a
positive correlation with the published factor, **adding commodities moves it
closer** (0.151 → 0.207, as it should — AQR's factor is heavily commodity- and
FX-weighted), and **the nine-sector version has literally zero relationship
with it** (−0.003). Five studies of "trend following" on US equity sectors
produced something with no measurable connection to the documented time-series
momentum effect; one study across asset classes produced something with a
detectable, if modest, connection.

The correlation is low in absolute terms, and that is expected rather than
disappointing: AQR's factor is long/short, volatility-targeted, across ~60
futures markets, while ours is long-only and unlevered on six ETFs. A
long-only portfolio's returns are dominated by asset-class beta, not by the
timing signal, so most of our variance cannot resemble a market-neutral
factor. **The regression intercept must not be read as alpha** — for a
long-only series regressed on a single long/short factor it is mostly
uncaptured market beta, which is why it is largest for SPY (10.4%/yr), a
portfolio with no timing signal at all.

## 7. Reading

The multi-asset universe is a genuine improvement in everything this sample
can measure — correlation structure, effective bets, volatility, drawdown,
tails, turnover — and an unresolvable one in the thing it cannot, the Sharpe
ratio. Given that the project's own power arithmetic says a 0.10 Sharpe
difference needs ~269 years, that combination is close to the best honest
outcome available from 21.8 years of data.

It also puts the previous five studies in perspective: they were run on a
universe worth 1.4 independent bets, and none of them could have discovered
that from a Sharpe ratio.

## 8. Caveats

Source-verification caveat stands (63 historical observations over the 2%
cross-check threshold). GLD is absent for the first ~4 months of the window
and DBC for the first ~19; the secondary study is reported separately for
exactly that reason. rf=0 columns are retained for continuity with the
journalled record, never as the honest number. ETF sleeves carry real tracking
and cost characteristics the FF deep-history series do not, so this is not
comparable to v4's 97.5-year result. Nothing here is promoted.
