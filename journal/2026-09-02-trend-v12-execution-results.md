# 2026-09-02 — trend-v12-execution: results

Append-only factual report. Pre-registered in
`2026-09-02-trend-v12-execution-preregistration.md`; the turnover frontier was
separately frozen before computation in
`2026-09-02-trend-v12-execution-frontier-amendment.md`. Nothing is promoted
and no execution cell is selected.

Canonical stdout:
`reports/trend-v12-execution-stdout.txt` (SHA-256
`b62db3864e8b7ee943017afc5da9d5f07f64d69b6a83f05f211e288619472b2d`).
Frontier table and plot:
`reports/trend-v12-execution-turnover-frontier.txt` and `.png` (SHA-256
`d1db24453b7439c737ca1254b59090298743353cb45e87e45f9eb9ce331bf3a9` and
`158902dd0d0ed0cab4fe21815cfc071ad5276c701f570ffa70f4a7e83c0edd0b`).

## Reconstruction and scope

OOS was 2004-10-22 through 2026-09-01: 5,499 bars and 22 folds. The v6
reconstruction passed before inference: 5 bps Sharpe 0.780673 versus 0.781
journaled, and annual turnover 5.153145 versus 5.15. The common missed masks
skipped 13/264 decisions at 5% and 27/264 at 10%.

The first completed raw run exposed a reporting-only floating-point defect in
the mathematically identical reference row (`p=0.770423` instead of the
defined `p=1`). Commit `2657969` fixed and tested it. The canonical reporting
rerun differed only in that p-value and signed zero; the first output is
preserved as `reports/trend-v12-execution-stdout-superseded-reference-p.txt`.
No non-reference estimate, success count, configuration, or real ledger row
changed.

## Unbuffered v6 and baselines

| portfolio / cost | CAGR | vol | Sharpe rf=0 | Sharpe real-RF | max DD | turnover |
|---|---:|---:|---:|---:|---:|---:|
| v6 / 0 bps | 8.6914% | 11.1446% | 0.803704 | 0.644365 | -21.7186% | 5.153145 |
| v6 / 5 bps | 8.4116% | 11.1430% | 0.780673 | 0.621309 | -21.9602% | 5.153145 |
| v6 / 10 bps | 8.1325% | 11.1421% | 0.757584 | 0.598205 | -22.2012% | 5.153145 |
| v6 / 25 bps | 7.2989% | 11.1440% | 0.688009 | 0.528654 | -22.9202% | 5.153145 |
| v6 / 50 bps | 5.9219% | 11.1626% | 0.571319 | 0.412220 | -24.1693% | 5.153145 |
| SPY / all costs | 11.2431% | 18.8421% | 0.659864 | 0.565574 | -55.1894% | 0.000000 |
| 60/40 / 0 bps | 8.3385% | 10.6212% | 0.807285 | 0.640002 | -32.3165% | 0.232231 |
| 60/40 / 5 bps | 8.3259% | 10.6212% | 0.806195 | 0.638911 | -32.3351% | 0.232231 |
| 60/40 / 10 bps | 8.3133% | 10.6211% | 0.805104 | 0.637819 | -32.3537% | 0.232231 |
| 60/40 / 25 bps | 8.2756% | 10.6210% | 0.801831 | 0.634545 | -32.4093% | 0.232231 |
| 60/40 / 50 bps | 8.2128% | 10.6209% | 0.796373 | 0.629085 | -32.5046% | 0.232231 |

## Fixed 216-cell surface

At 10 bps, 48/216 cells met all four pre-registered economic criteria. This
is a non-inferiority/turnover result, not evidence that any one cell is
superior: no paired 95% interval excluded zero in either direction.

Across those 48 cells, turnover reduction ranged 46.20%-68.01% (median
51.73%), Sharpe difference ranged +0.0183 to +0.0921 (median +0.0645), and the
bootstrap lower bound ranged -0.0999 to -0.0367. Tracking error ranged
3.27%-5.19% annualized. Their maximum drawdowns improved by 3.63-6.71
percentage points and fifth-percentile daily returns improved by 5.08-9.35
bps. Across the full surface, all 216 cells passed the fixed drawdown and tail
tolerances; 144 passed turnover reduction, 77 passed the inference bound, and
48 passed both plus the risk tests.

For completeness, success counts by each fixed setting were: adjustment
`1.00/0.50/0.33 = 0/48/0`; tranches `1/4 = 48/0`; delay `0/1/2 = 18/15/15`;
missed rate `0/.05/.10 = 9/18/21`; band `0/.025/.05/.10 = 12/12/12/12`.
These are surface descriptions. They do not select an adjustment, tranche,
delay, miss rate, band, or combination.

Cost crossovers versus unbuffered v6 were already positive at 0 bps for 127
cells, occurred above zero for 47 cells (0.260-49.742 bps, median 8.396), and
were not observed through 50 bps for 41 cells; one cell is the reference.
Again, no crossover or cell is selected.

Deflated Sharpe used the full effective breadth of 216 highly correlated
execution trials: SR0 0.078895, trial-Sharpe SD 0.028272, and DSR
0.998109-0.999823. This is descriptive and is not a selection license.

## Regime dependence

Leave-one-decade-out results were not stable. Removing the 2000s left 72
cells meeting the same combined criteria and a median Sharpe difference of
+0.0869. Removing the 2010s left **zero** such cells and a median difference
of -0.0902. Removing the 2020s left 57 cells and a median difference of
+0.0742. Thus the full-window non-inferiority result depends materially on the
decade composition; this is not assumed away.

Unbuffered v6 10 bps sub-period Sharpes were 1.3231 (2004-2007), 0.6986
(2008-2014), 0.1866 (2015-2019), 1.2063 (2020-2021), and 0.7517
(2022 through 2026-09-01).
The complete grouped surface and all 648 omission rows are in stdout.

## Maximum viable turnover frontier

| cost | v6 gross Sharpe at zero hypothetical turnover | vol-target 60/40 net Sharpe | advantage | maximum viable turnover |
|---:|---:|---:|---:|---|
| 5 bps | 0.803704 | 0.862283 | -0.058580 | none |
| 10 bps | 0.803704 | 0.859295 | -0.055591 | none |
| 25 bps | 0.803704 | 0.850315 | -0.046612 | none |
| 50 bps | 0.803704 | 0.835306 | -0.031602 | none |

There is no non-negative break-even contour: v6 trails the fixed 63-day/10%
vol-targeted 60/40 even before hypothetical v6 costs. On this relative-Sharpe
criterion, the data therefore do not fund monthly (24x), weekly (104x), or
daily (504x) full rotations at the tested costs. This is an affordability
bound, not a test of any faster signal; decision frequency is not itself
turnover.

## Exploratory v11 overlay

This does not confirm v11. Under assumed one-way annual turnover per leg of
1x/2x/4x, the simple 13.8-point gross spread retained 12.8/11.8/9.8 points at
50 bps; long-short Sharpe fell from 0.512 gross to 0.468/0.424/0.335. These
are assumed stresses, not observed decile turnover, and v11 remains
unregistered and exploratory.

## Trials and disposition

The immutable ledger audit is exact: `trend-v12-execution` has 216 distinct
configurations and 4,752 rows; `trend-v12-execution-v11-overlay` has 3 and
282. Total: 219 configurations and 5,034 rows. The frontier is a fixed
analytic diagnostic and adds no trial.

Nothing is promoted. No cell may be carried forward as a selected result from
this curve without counting that selection in a future trial budget. The
source store remains dual-source checked but not clean under the codified 2%
rule. The futures-data and higher-frequency-design decisions remain for
planning. Stop after v12.
