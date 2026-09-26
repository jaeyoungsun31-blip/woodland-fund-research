# 2026-09-04 — v6/v7/v8 risk-free Sharpe convention recomputation

Append-only factual correction. This is a metric recomputation, not a new
study: no configuration, sleeve, blend weight, cost level, selection rule, or
trials-ledger row was added. The original v6, v7, and v8 entries are unchanged.

The existing paired stationary-bootstrap/HAC correction path was applied with
10,000 joint stationary resamples, expected block length 21, and seed 0.
Every pair is shown under both conventions: the original `rf=0` calculation
and aligned real-risk-free excess-return calculation. The frozen 2026-09-01
archive was extracted into a temporary directory and read there; `data/` was
not changed. This matters: the current store has 5,502 ETF OOS bars, whereas
the frozen v7 source has the original 5,499 and exactly reproduces the v7
5-bps `trend:w=0.1` rf=0 Sharpe of 0.851378.

The complete machine-readable recomputation tables are retained locally under
`reports/trend-rf-frozen-*.csv`. They contain all 0/5/10-bps base comparisons
for v6, v7 ETF, v8 ETF, and the exact v8 deep-history analogue. The v7 sleeve
result is reported first because its cash-heavy 60/40 comparator has the same
structural convention asymmetry as v17.

## v7 trend sleeve in 60/40 — both historical horizons, in full

Each cell is `delta [95% bootstrap CI]; p_boot / p_HAC`. Positive deltas favour
the indicated trend sleeve over the unmodified balanced base.

### ETF, 2004-10-22 through 2026-09-01 (5,499 OOS bars)

| Weight | Cost | rf=0 | Excess return |
|---:|---:|---|---|
| 10% | 0 | +0.044529 [-0.000764, +0.083449]; .0946 / .0983 | +0.034883 [-0.008706, +0.072754]; .0946 / .0983 |
| 10% | 5 | +0.042583 [-0.003052, +0.081664]; .0510 / .0463 | +0.032934 [-0.010940, +0.071024]; .1156 / .1192 |
| 10% | 10 | +0.040636 [-0.005316, +0.079875]; .0572 / .0540 | +0.030983 [-0.013218, +0.069148]; .1414 / .1434 |
| 20% | 0 | +0.087388 [-0.006753, +0.169637]; .1100 / .1076 | +0.069450 [-0.020017, +0.148899]; .1100 / .1076 |
| 20% | 5 | +0.082949 [-0.011438, +0.165519]; .1365 / .1323 | +0.065003 [-0.024810, +0.144671]; .1365 / .1323 |
| 20% | 10 | +0.078506 [-0.016367, +0.161311]; .1658 / .1612 | +0.060552 [-0.029528, +0.140376]; .1658 / .1612 |
| 30% | 0 | +0.120599 [-0.025663, +0.250565]; .1582 / .1484 | +0.096512 [-0.042620, +0.222573]; .1582 / .1484 |
| 30% | 5 | +0.113362 [-0.033619, +0.243786]; .1925 / .1815 | +0.089259 [-0.050332, +0.216011]; .1925 / .1815 |
| 30% | 10 | +0.106115 [-0.041274, +0.236640]; .2340 / .2199 | +0.081998 [-0.058011, +0.208718]; .2340 / .2199 |

### FF12 deep history, 1932-03-15 through 2026-06-30 (24,579 OOS bars)

| Weight | Cost | rf=0 | Excess return |
|---:|---:|---|---|
| 10% | 0 | +0.028613 [+0.006371, +0.054838]; .0216 / .0046 | +0.034155 [+0.013388, +0.059103]; .0050 / .0005 |
| 10% | 5 | +0.026083 [+0.003901, +0.052205]; .0334 / .0096 | +0.031620 [+0.010928, +0.056537]; .0083 / .0012 |
| 10% | 10 | +0.023551 [+0.001405, +0.049594]; .0537 / .0190 | +0.029084 [+0.008421, +0.054016]; .0132 / .0027 |
| 20% | 0 | +0.043302 [+0.006643, +0.082778]; .0258 / .0093 | +0.055929 [+0.021820, +0.092749]; .0020 / .0005 |
| 20% | 5 | +0.038197 [+0.001577, +0.077647]; .0477 / .0215 | +0.050814 [+0.016744, +0.087632]; .0051 / .0016 |
| 20% | 10 | +0.033085 [-0.003602, +0.072589]; .0898 / .0460 | +0.045695 [+0.011707, +0.082517]; .0116 / .0044 |
| 30% | 0 | +0.053327 [+0.002855, +0.107206]; .0449 / .0218 | +0.073989 [+0.026805, +0.123550]; .0024 / .0011 |
| 30% | 5 | +0.045795 [-0.004710, +0.099808]; .0866 / .0484 | +0.066444 [+0.019361, +0.116021]; .0068 / .0032 |
| 30% | 10 | +0.038251 [-0.012335, +0.092255]; .1528 / .0987 | +0.058891 [+0.011663, +0.108388]; .0179 / .0089 |

### FF12 deep-history eras, 5 bps

| Era | Weight | rf=0 | Excess return |
|---|---:|---|---|
| 1932–1979 | 10% | +0.046522 [+0.011054, +0.092403]; .0262 / .0106 | +0.050726 [+0.016932, +0.094569]; .0145 / .0042 |
| 1932–1979 | 20% | +0.070037 [+0.015364, +0.131418]; .0194 / .0080 | +0.079844 [+0.028063, +0.138753]; .0071 / .0019 |
| 1932–1979 | 30% | +0.088754 [+0.014758, +0.169445]; .0244 / .0118 | +0.104839 [+0.034413, +0.181104]; .0067 / .0024 |
| 1980–2026 | 10% | +0.005863 [-0.019396, +0.030973]; .6510 / .5975 | +0.012792 [-0.009604, +0.034667]; .2557 / .2341 |
| 1980–2026 | 20% | +0.006692 [-0.041840, +0.055452]; .7914 / .7566 | +0.022164 [-0.021252, +0.065002]; .3137 / .2903 |
| 1980–2026 | 30% | +0.003280 [-0.066614, +0.073726]; .9312 / .9167 | +0.028553 [-0.034274, +0.090740]; .3720 / .3500 |

The ETF trend-sleeve intervals remain ambiguous at every registered cost under
both conventions. The deep-history trend-sleeve result is positive under
excess-return inference at all nine registered cells; its rf=0 lower bounds
cross zero at 20%/10 bps and 30%/5–10 bps. The deep result is confined to
1932–1979: all three post-1980 excess-return intervals cross zero. Thus the
correction strengthens the early deep result but does not establish ETF or
post-1980 robustness, or select a sleeve weight. Nothing is promoted.

## v6 multi-asset

At the registered 5-bps comparison cost, changing convention does not reverse
or resolve any v6 conclusion. The excess-return deltas (95% bootstrap CI;
bootstrap/HAC p) are: versus v2, +0.040797 [-0.323784, +0.398190]; .8326 /
.8272; versus SPY, +0.055735 [-0.369995, +0.474646]; .8071 /.7924; versus
60/40, -0.017602 [-0.433296, +0.380600]; .9334 /.9323; versus vol-targeted
60/40, -0.041232 [-0.440425, +0.345109]; .8381 /.8332; and DBC minus v6,
-0.039997 [-0.228615, +0.134382]; .6633 /.6470. The equivalent rf=0 deltas
are respectively +0.080255, +0.120810, -0.025521, -0.081610, and -0.042651;
all of their intervals also cross zero. The full 0/5/10-bps tables are in the
local audit artifact. The diversification and distribution findings do not
depend on the Sharpe convention.

## v8 blends

All registered blend-versus-unmodified-base rows were recomputed at 0/5/10
bps. On the ETF window, excess-return inference is materially less favourable
than rf=0 for cash-light blends, but it leaves only these positive
bootstrap-lower-bound cells: `trend_gold:w=0.1` at all three costs
(5 bps: +0.053082 [+0.001563, +0.100328], p=.0377/.0453);
`trend_gold_defensive:w=0.1` at 0 and 5 bps (5 bps: +0.036484
[+0.001059, +0.069313], p=.0380/.0475); and
`trend_gold_defensive:w=0.2` at all three costs (5 bps: +0.075864
[+0.001879, +0.143339], p=.0358/.0431). Every other ETF blend/base
excess-return interval crosses zero.

For the exact deep-history `trend_defensive` analogue, all nine
excess-return intervals remain positive. At 5 bps they are +0.020963
[+0.006699, +0.041320] at 10%, +0.032695 [+0.011546, +0.058005] at 20%, and
+0.043733 [+0.015269, +0.075036] at 30% (bootstrap/HAC p=.0216/.0033,
.0071/.0010, and .0052/.0010). The equivalent rf=0 deep results are also
positive at every registered cell. This does not change v8's fixed-curve,
no-selection disposition or its cross-arm result against gold.

## Scope and disposition

Subtracting the same daily risk-free series from both portfolios changes the
paired Sharpe difference whenever portfolios carry different cash exposure;
the direction need not be the same in every family. It removes the mechanical
cash convention rather than awarding a strategy a benefit. This correction
does not modify drawdown, tail, turnover, diversification, Bayesian-prior, or
cross-arm evidence, and it authorizes neither a new study nor promotion.
