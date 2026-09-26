# 2026-09-02 — trend-v8-blend: results

Study id: `trend-v8-blend`.

This is the factual execution record for
`journal/2026-09-02-trend-v8-blend-preregistration.md` and its append-only
cross-arm amendment. Nothing in this entry selects a mix, weight, prior, or
result, and nothing is promoted.

The complete stdout is retained locally at
`reports/trend-v8-blend-stdout.txt`. Its SHA-256 is
`9bdce8b932a6024b7c3ceb37a08f26c06abc4361a0c50b36e68413b6cace0fdb`.
That file contains every printed performance, inference, posterior,
matched-volatility, sub-period, and DSR row. The tables below capture the
pre-registered headline cells in the append-only journal.

## Execution and reconstruction checks

The deep-history phase ran first. It rebuilt the v7 deep single arms, formed
and froze the exact deep priors, and only then loaded and evaluated the ETF
arms. The ETF phase rebuilt every v7 single-arm comparator. All reconstructed
5 bps Sharpe values matched their v7 anchors exactly:

| universe | arm | w=0.1 | w=0.2 | w=0.3 |
|---|---:|---:|---:|---:|
| deep | trend | 0.867823 | 0.879940 | 0.887542 |
| deep | defensive | 0.861663 | 0.873578 | 0.886349 |
| ETF | trend | 0.851378 | 0.891745 | 0.922157 |
| ETF | gold | 0.888777 | 0.946354 | 0.964911 |
| ETF | defensive | 0.815806 | 0.827332 | 0.839194 |

The ETF window was 2004-10-22 through 2026-09-01, 5,499 stitched OOS bars
and 22 folds. The deep window was 1932-03-15 through 2026-06-30, 24,579
stitched OOS bars and 95 folds. The bootstrap used 10,000 stationary-block
resamples, expected block length 21, and seed 0. HAC is the pre-registered
Ledoit-Wolf counterpart. All inference below is at 5 bps unless stated.

## Deep-history prior arm

The deep-history base (60% MKT / 40% CASH) had 5 bps rf=0 Sharpe 0.841883,
real-RF Sharpe 0.531262, CAGR 8.1207%, volatility 9.8526%, maximum drawdown
-35.9426%, and annualized turnover 0.206128. This is frictionless academic
data and is not a duration-matched 60/40 portfolio.

| arm | w | SR0 at 0/5/10 bps | real-RF SR, 5 bps | CAGR, 5 bps | max DD | turnover |
|---|---:|---:|---:|---:|---:|---:|
| trend+defensive | .1 | .867796 / .865488 / .863180 | .552078 | 8.2996% | -34.9002% | .452397 |
| trend+defensive | .2 | .883003 / .879294 / .875583 | .563808 | 8.3912% | -33.8601% | .722731 |
| trend+defensive | .3 | .897135 / .891986 / .886834 | .574846 | 8.4810% | -32.8199% | .998125 |

| arm | w | delta SR0 vs base | bootstrap 95% CI | boot p | correlation | HAC 95% CI | HAC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| trend+defensive | .1 | .023605 | [.008578, .044585] | .015598 | .998367 | [.009263, .037948] | .001256 |
| trend+defensive | .2 | .037411 | [.014839, .063866] | .003600 | .996353 | [.017327, .057496] | .000261 |
| trend+defensive | .3 | .050103 | [.019646, .083536] | .001900 | .992944 | [.023070, .077138] | .000281 |

The neutral-prior deep posteriors frozen for the exact ETF comparisons were:

| arm | w | deep delta | bootstrap mean | likelihood SD | frozen mean | frozen SD |
|---|---:|---:|---:|---:|---:|---:|
| trend | .1 | .025940 | .025805 | .012317 | .025877 | .012302 |
| trend | .2 | .038056 | .037828 | .019403 | .037829 | .019345 |
| trend | .3 | .045659 | .045387 | .026543 | .045150 | .026395 |
| defensive | .1 | .019780 | .019820 | .007770 | .019760 | .007767 |
| defensive | .2 | .031695 | .031749 | .007842 | .031663 | .007838 |
| defensive | .3 | .044466 | .044535 | .007976 | .044421 | .007972 |
| trend+defensive | .1 | .023605 | .023546 | .009393 | .023572 | .009387 |
| trend+defensive | .2 | .037411 | .037282 | .012536 | .037317 | .012520 |
| trend+defensive | .3 | .050103 | .049920 | .016347 | .049890 | .016312 |

## ETF performance

The unmodified 60/40 base at 5 bps had CAGR 8.3467%, volatility 10.6091%,
rf=0 Sharpe 0.808795, real-RF Sharpe 0.641320, maximum drawdown -32.1852%,
worst day -5.4217%, daily fifth percentile -0.9926%, and annualized turnover
0.234389. SPY buy-and-hold had CAGR 11.2431%, volatility 18.8421%, rf=0
Sharpe 0.659864, real-RF Sharpe 0.565574, and maximum drawdown -55.1894%.

| blend | w | SR0 at 0/5/10 bps | real-RF SR, 5 bps | CAGR, 5 bps | vol | max DD | worst day | p05 day | turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| trend+gold | .1 | .875245 / .873176 / .871106 | .694402 | 8.5262% | 9.9374% | -28.6836% | -5.1117% | -.9375% | .410921 |
| trend+defensive | .1 | .836661 / .834566 / .832470 | .659010 | 8.2562% | 10.1208% | -30.0694% | -5.0913% | -.9617% | .423586 |
| gold+defensive | .1 | .856718 / .855234 / .853749 | .678146 | 8.4105% | 10.0322% | -29.5408% | -5.2456% | -.9324% | .296149 |
| three-way | .1 | .856920 / .855110 / .853299 | .677804 | 8.3993% | 10.0202% | -29.4303% | -5.1495% | -.9372% | .361890 |
| trend+gold | .2 | .936514 / .933356 / .930196 | .745429 | 8.7345% | 9.4518% | -25.4545% | -4.8075% | -.9095% | .599194 |
| trend+defensive | .2 | .867244 / .864064 / .860882 | .680376 | 8.2082% | 9.6725% | -27.9101% | -4.7647% | -.9238% | .616366 |
| gold+defensive | .2 | .904044 / .902411 / .900778 | .716620 | 8.5127% | 9.5611% | -27.1578% | -5.0717% | -.8902% | .310759 |
| three-way | .2 | .906255 / .903795 / .901334 | .717184 | 8.4907% | 9.5196% | -26.6670% | -4.8812% | -.9055% | .468797 |
| trend+gold | .3 | .982104 / .977684 / .973260 | .784121 | 8.9236% | 9.1747% | -22.9927% | -4.5090% | -.8895% | .816909 |
| trend+defensive | .3 | .896914 / .892425 / .887933 | .700684 | 8.1543% | 9.2661% | -25.7152% | -4.4417% | -.9042% | .835461 |
| gold+defensive | .3 | .944350 / .942587 / .940823 | .749689 | 8.6038% | 9.2073% | -24.9826% | -4.9000% | -.8658% | .323555 |
| three-way | .3 | .951025 / .947746 / .944465 | .752917 | 8.5713% | 9.1169% | -24.2271% | -4.6167% | -.8823% | .600193 |

## Paired ETF differences against the unmodified base

| blend | w | delta SR0 | bootstrap 95% CI | boot p | correlation | HAC 95% CI | HAC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| trend+gold | .1 | .064381 | [.011802, .112180] | .010999 | .991801 | [.012153, .116621] | .015693 |
| trend+defensive | .1 | .025771 | [.000161, .048010] | .035096 | .998183 | [.001786, .049760] | .035217 |
| gold+defensive | .1 | .046439 | [.007083, .084714] | .019898 | .995238 | [.006061, .086825] | .024186 |
| three-way | .1 | .046315 | [.010076, .079534] | .008899 | .996069 | [.010061, .082577] | .012286 |
| trend+gold | .2 | .124561 | [.012248, .224771] | .020798 | .964308 | [.016178, .232966] | .024291 |
| trend+defensive | .2 | .055268 | [.004825, .100172] | .020098 | .992922 | [.008645, .101902] | .020161 |
| gold+defensive | .2 | .093616 | [.012401, .171725] | .021698 | .979805 | [.010486, .176763] | .027302 |
| three-way | .2 | .095000 | [.019378, .163800] | .008699 | .983414 | [.021068, .168949] | .011788 |
| trend+gold | .3 | .168889 | [-.009607, .326966] | .047095 | .913278 | [.000576, .337232] | .049221 |
| trend+defensive | .3 | .083630 | [.005167, .154379] | .026197 | .983024 | [.011723, .155552] | .022640 |
| gold+defensive | .3 | .133792 | [.006282, .255172] | .035096 | .950794 | [.004602, .263006] | .042380 |
| three-way | .3 | .138951 | [.018828, .246582] | .014699 | .959350 | [.023632, .254295] | .018198 |

These are paired comparisons with correlations from 0.913278 to 0.998183.
The high correlations supply the power anticipated in the pre-registration.
They establish that the blends differ from the base under the stated tests;
they do not establish that combining sleeves improves on the constituent
single sleeves.

## Cross-arm result: combining versus single sleeves

All 36 blend-versus-single and all 18 blend-versus-blend pairs were run at
the same weight. The complete 54-row classical table and 108-row
prior-matched Bayesian table are in the saved stdout. Every comparison uses
identical series and reports its correlation; observed correlations ranged
from 0.825221 to 0.999496 versus base and from 0.860280 to 0.999433 across
arms.

No blend had a 95% paired-bootstrap interval wholly above zero against either
trend or gold. Against gold, the point estimates and intervals were:

| blend minus gold | w | delta SR0 | bootstrap 95% CI | boot p | corr | HAC 95% CI | HAC p |
|---|---:|---:|---:|---:|---:|---:|---:|
| trend+gold | .1 | -.015601 | [-.049991, .017354] | .366563 | .996532 | [-.050245, .019040] | .377371 |
| trend+gold | .2 | -.012998 | [-.083341, .055260] | .711029 | .985166 | [-.084438, .058440] | .721362 |
| trend+gold | .3 | .012772 | [-.089547, .113358] | .800420 | .967605 | [-.092785, .118332] | .812522 |
| trend+defensive | .1 | -.054212 | [-.120867, .011696] | .109189 | .986008 | [-.124007, .015574] | .127861 |
| trend+defensive | .2 | -.082290 | [-.219213, .056494] | .245075 | .939001 | [-.227485, .062890] | .266576 |
| trend+defensive | .3 | -.072487 | [-.278031, .138866] | .494651 | .860280 | [-.291987, .147000] | .517421 |
| gold+defensive | .1 | -.033543 | [-.069339, .003413] | .070493 | .995687 | [-.072034, .004942] | .087582 |
| gold+defensive | .2 | -.043943 | [-.117329, .036935] | .266773 | .981163 | [-.124041, .036148] | .282195 |
| gold+defensive | .3 | -.022324 | [-.133466, .100749] | .709729 | .958281 | [-.141344, .096691] | .713122 |
| three-way | .1 | -.033667 | [-.078391, .010710] | .137886 | .993686 | [-.080516, .013175] | .158911 |
| three-way | .2 | -.042559 | [-.133994, .051014] | .373263 | .972535 | [-.139876, .054751] | .391311 |
| three-way | .3 | -.017165 | [-.153037, .124147] | .809819 | .938602 | [-.162515, .128181] | .816936 |

Trend+gold had positive point differences from trend at every weight
(.021798, .041611, .055527), but its 95% intervals all crossed zero. The
trend+defensive blend had negative point differences from trend at every
weight (-.016812, -.027681, -.029732), also with intervals crossing zero.
Gold+defensive and the three-way blend had small positive point differences
from trend in several cells, but none had an interval wholly above zero.

Several blends did clear defensive alone in individual cells. These are
expected constituent-versus-weaker-constituent comparisons, not evidence that
averaging beat the strongest component. Within the blend family,
trend+gold minus the three-way blend at w=.1 was .018066 with bootstrap CI
[.001207, .033302], p=.028397, correlation .999147; at w=.2 and .3 its
intervals crossed zero. No family member is selected from these curves.

## Bayesian allocation and sensitivity

The block-bootstrap distribution was treated as a normal likelihood, as
pre-registered. The table below reports each new ETF arm against the base.
`EL A/N` is posterior expected loss for allocate / do-not-allocate. Every new
blend had lower expected loss for allocation under both priors.

| arm | w | prior | posterior mean | 90% CrI | P(delta>0) | P(delta>.05) | EL A/N | action |
|---|---:|---|---:|---:|---:|---:|---:|---|
| trend+gold | .1 | skeptical | .051130 | [.013820,.088441] | .987905 | .519872 | .010095/.051225 | allocate |
| trend+gold | .1 | neutral | .063720 | [.022069,.105372] | .994071 | .706030 | .010048/.063769 | allocate |
| trend+defensive | .1 | skeptical | .024320 | [.004811,.043830] | .979841 | .015191 | .010088/.024408 | allocate |
| trend+defensive | .1 | neutral | .025709 | [.005651,.045768] | .982494 | .023191 | .010077/.025786 | allocate |
| gold+defensive | .1 | skeptical | .040065 | [.009597,.070534] | .984728 | .295867 | .010101/.040166 | allocate |
| gold+defensive | .1 | neutral | .046145 | [.013447,.078844] | .989864 | .423127 | .010068/.046214 | allocate |
| three-way | .1 | skeptical | .041137 | [.013638,.068635] | .993066 | .298002 | .010038/.041175 | allocate |
| three-way | .1 | neutral | .046083 | [.016978,.075187] | .995398 | .412395 | .010026/.046108 | allocate |
| trend+gold | .2 | skeptical | .058009 | [-.002107,.118124] | .943768 | .586728 | .010875/.058884 | allocate |
| trend+gold | .2 | neutral | .119095 | [.032959,.205232] | .988524 | .906489 | .010207/.119302 | allocate |
| trend+defensive | .2 | skeptical | .044667 | [.008646,.080687] | .979308 | .403790 | .010167/.044834 | allocate |
| trend+defensive | .2 | neutral | .054749 | [.014869,.094628] | .988032 | .577641 | .010100/.054849 | allocate |
| gold+defensive | .2 | skeptical | .056085 | [.004011,.108158] | .961765 | .576205 | .010485/.056570 | allocate |
| gold+defensive | .2 | neutral | .091175 | [.024780,.157571] | .988051 | .846152 | .010167/.091342 | allocate |
| three-way | .2 | skeptical | .061923 | [.013394,.110452] | .982085 | .656940 | .010191/.062114 | allocate |
| three-way | .2 | neutral | .093013 | [.033536,.152489] | .994949 | .882887 | .010058/.093070 | allocate |
| trend+gold | .3 | skeptical | .043834 | [-.026936,.114604] | .845852 | .443022 | .013458/.047292 | allocate |
| trend+gold | .3 | neutral | .151590 | [.019984,.283196] | .970928 | .897904 | .010897/.152487 | allocate |
| trend+defensive | .3 | skeptical | .052918 | [.003079,.102757] | .959634 | .538357 | .010494/.053412 | allocate |
| trend+defensive | .3 | neutral | .081732 | [.019793,.143672] | .985014 | .800296 | .010200/.081932 | allocate |
| gold+defensive | .3 | skeptical | .050900 | [-.013835,.115635] | .902049 | .509120 | .011817/.052717 | allocate |
| gold+defensive | .3 | neutral | .125610 | [.023916,.227303] | .978908 | .889327 | .010482/.126092 | allocate |
| three-way | .3 | skeptical | .059706 | [-.002402,.121815] | .943088 | .601433 | .010917/.060623 | allocate |
| three-way | .3 | neutral | .131946 | [.039617,.224275] | .990629 | .927838 | .010177/.132123 | allocate |

The exact trend+defensive supplementary deep-informed posteriors had means
.024389, .041068, and .055118 at w=.1/.2/.3, with 90% intervals
[.012148,.036629], [.022752,.059384], and [.030453,.079783]. They also chose
allocation under the fixed loss. They were not used in any cross-arm result.

The only action sensitivity flip anywhere in the ETF arm-versus-base table
was the reconstructed `defensive:w=0.1` comparator: skeptical and neutral said
do not allocate, while its supplementary deep-informed posterior said
allocate. No new blend's allocation action flipped between the universally
available skeptical and neutral priors. Posterior magnitudes and
`P(delta>.05)` nevertheless moved materially with the prior, especially at
w=.2 and w=.3.

All cross-arm Bayesian comparisons were prior-matched. Skeptical and neutral
posteriors only were used. For the 12 blend-minus-gold comparisons,
`P(delta>0)` ranged from .035775 to .595437; none reached .60 under either
prior. Therefore the Bayesian cross-arm evidence also did not establish that
combining improved on gold. This is a statement about the fixed comparisons,
not a ranking or selection.

## Matched volatility and sub-periods

The complete 108-row matched-volatility table (36 pairs x 3 costs) records
which side was scaled in every row. Only CAGR, maximum drawdown, worst day,
and fifth-percentile day were scaled; Sharpe was excluded. Scaling always
reduced the more volatile side to the less volatile side with no leverage.

Against gold, the scaled side changed with the weight. For trend+gold versus
gold it was trend+gold at w=.1 (5 bps scale .997522), and gold at w=.2
(.983600) and w=.3 (.943281). At w=.3 the matched CAGR was 8.9236% for
trend+gold and 8.9056% for gold; maximum drawdowns were -22.9927% and
-23.4358%; worst days -4.5090% and -4.6800%; fifth-percentile days -.8895%
and -.8817%. This one distribution cell does not select w=.3 or overturn the
uncertain Sharpe difference.

The pre-registered ETF sub-period table was printed for 2004-07, 2008-14,
2015-19, 2020-21, and 2022-26. No blend dominated its constituent singles in
every period. For example, trend+gold w=.3 rf=0 Sharpe was 1.426290,
.772778, 1.066086, 1.298194, and .901824 across those periods; gold w=.3 was
1.448086, .677630, 1.182802, 1.185342, and 1.010206. The full deep decade
table and full ETF sub-period table are in the captured stdout.

## Evidence limits, trials, and disposition

The evidence base is uneven: trend has 94 years behind it; gold has 22.
Deep-informed priors are **UNAVAILABLE** for gold and every gold-containing
blend. No trend-sized posterior was substituted. Gold was pegged under
Bretton Woods until 1971, so even a future floating-price history would be
roughly 55 years rather than 94 and would begin at a structural break. Any
future gold ingest remains a separate data-layer decision and must pass the
dual-source cross-check before research use.

The ledger contains exactly 15 distinct v8 configurations and 549 fold rows:
12 ETF configurations x 22 folds = 264, and 3 FF12 configurations x 95 folds
= 285. Reconstructed v7 comparators were not relogged. Each reported curve
has effective breadth one; SR0=0 DSR values round to 1.000, making DSR
vacuous. The paired tests are load-bearing.

Result: blends improved on the unmodified base in these fixed ETF cells, but
the study did not show that combining sleeves improved on the strongest
single-sleeve comparator, static gold. The allocation loss preferred every
new blend to the base under both universally available priors, while the
size of the inferred benefit remained prior-sensitive. Nothing was selected,
promoted, or carried forward. Planning review is required before any v9 or
new study is designed.

## 2026-09-02 correction — interpretation discipline

This correction is appended; the original result text above is unchanged.

The blends beat the unmodified base, but none reliably beat static gold. That
is a **negative result for sleeve averaging as a source of edge**. In this
study, averaging's demonstrated value was variance reduction, not return.

No blend weight was selected from the `w in {0.1, 0.2, 0.3}` curve, and no
blend weight may be selected from it after the fact. Any future claim built on
one weight from this curve must explicitly treat that choice as selection and
carry the selection in its trials count.
