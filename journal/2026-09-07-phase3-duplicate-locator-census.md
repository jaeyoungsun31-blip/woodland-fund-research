# Duplicate-locator census — the gate fails; the panel was not built

Date: 2026-09-07
Status: completed measurement; gate condition NOT met; no panel constructed
Gate: fewer than 5% of the 947 automatically resolved symbols may have a
contending locator whose adjusted series disagrees. Measured: **7.71%**.
Artifacts: `reports/security-resolver/2026-09-07-duplicate-locators/`
Code: `scripts/run_duplicate_locator_census.py`

**73 of the 947 automatically resolved symbols have a contending locator in the
store that implies a materially different return series.** That is 7.71% against
a 5% threshold, 7.50% under the most conservative exclusion, and it is a lower
bound. The automatic path is contaminated. The panel was not built and Task 3's
conditional work was not begun.

## Method — candidates from prices, never from tickers

The reference case `FISV`/`FI` shares no ticker string, and linking the two
through the catalog would mean trusting the field the resolver exists not to
trust. Candidates are therefore generated from exact `(date, close)`
co-occurrence on a fixed probe calendar, then measured over the full overlap.
The reference figures reproduce exactly: 9,858 overlapping bars, 80.0% close
agreement, 20.9% adjusted-close agreement at `rtol=1e-6`. Volume agreement
measures 28.3% against the 24.5% quoted in the brief; the difference is recorded,
not reconciled.

Two corrections were required before the census meant anything. Both changed the
answer and both are recorded because the first version of each was wrong.

**Token co-occurrence is far too weak a filter on its own.** With 50,806 indexed
files and prices quantised to six significant figures, five coincidental
`(date, close)` collisions are common rather than rare. The first run reported
212 locators with contenders, among them `AEP` against `ES`, `CMS`, `NVRI` and
`CWT` — different utilities agreeing on 0.5% of their closes. The stated
reasoning, that five exact collisions are not a realistic coincidence, was simply
wrong at this scale. Qualification is now evidence that two files record the same
traded prices: close agreement of at least 90% at `rtol=1e-3`, against
`FISV`/`FI`'s 99.0%. That rejected **1,685 token collisions** and reduced the
population from 212 to 83.

**Exact agreement on the adjusted level is a degenerate contamination test.**
Each file's adjustment factor reaches 1.0 at its own final bar, so two files
ending on different dates disagree on every adjusted level by construction.
`AGN`/`WPI` score 0.0% on levels while their returns correlate 0.99994. Applied
literally, the gate's own metric would condemn every legitimate pair and the
result would carry no information.

The test used instead is the one that reaches the panel: the range of
`adjusted_a / adjusted_b` across the overlap. Two files that are one series under
two normalisations give a constant ratio and a range of 1.000. `FISV`/`FI` range
**1.402**, so they are not one series viewed twice — they are two different return
histories. The threshold is 1.001.

## Result

947 automatically resolved locators (`unique_live_candidate`, 12,961 rows).
1,685 token collisions rejected as different entities. 83 locators retain a
qualified contender across 93 pairs. **73 diverge** — 7.71%. Excluding the two
cases driven solely by a warrant ticker, 71 — 7.50%. In **26** cases the
preferred-locator rule selects a different file from the one v9 resolved: ADS,
ANTM, BHGE, COG, CTL, DF, DISCA, EQR, FBHS, FI, FLT, FRC, HFC, HRS, IAC, KORS,
KRFT, MMC, MYL, NLOK, NVLS, PKI, SW, SYMC, TMK, TUP.

Worst divergences by adjusted-ratio range: `C`/`C-WS-A` 3,010,472;
`WFC`/`WFC-WS` 878.5; `MYL`/`VTRS` 211.7; `TPR`/`COH` 56.5; `WIN`/`WINMQ` 56.4;
`DF`/`DFODQ` 26.1; `CTRA`/`COG` 13.1; `GEN`/`SYMC` 7.03; `ANTM`/`ELV` 2.02;
`CTL`/`LUMN` 1.91; `FISV`/`FI` 1.40; `FISV`/`FISV_old` 1.28.

These are not exotic instruments. `MYL`/`VTRS`, `TPR`/`COH`, `CTRA`/`COG`,
`GEN`/`SYMC`, `ANTM`/`ELV`, `CTL`/`LUMN` and `FISV`/`FI` are ordinary ticker
successions across large, long-lived constituents — the names a constituent panel
is mostly made of. `TPR`/`COH` returns correlate **−0.104** over 4,294 shared
bars.

The mechanism that makes this dangerous is that the contamination is nearly
invisible on the column a human inspects and decisive on the column returns are
computed from. `CTL` and `LUMN` agree on **100.0%** of raw closes and still imply
return series whose ratio moves by a factor of 1.9. A reviewer comparing prices
would see two identical files and pick either.

## Why 7.71% is a lower bound

Candidates are found by exact `(date, close)` matching. A contender whose prices
are uniformly rescaled — a KMI-style raw-column error, or a file stored on a
different split basis — shares no exact token with its counterpart and is
invisible to this search. Additionally, 58 of the 50,864 files produced no usable
token and were not indexed, and contenders overlapping fewer than 250 bars were
not measured. Whatever the true rate is, it is not below 7.71%.

## The warrant cases, and why they do not rescue the gate

`C`/`C-WS-A` and `WFC`/`WFC-WS` are warrants whose vendor files carry long
stretches of the common stock's prices — 63.1% and 44.0% of closes exactly equal
the common's — before diverging to warrant prices. That is a separate vendor
defect. It is reported rather than filtered out, and it drives only 2 of the 73;
removing both leaves 7.50%, still above the threshold. The gate outcome does not
depend on how warrants are treated.

## What was not done

Task 3's panel construction was conditional on the gate and the gate failed, so
no panel was built: no dimensions, no coverage measurement, no names-per-day
series, no thin-date report. The 211 review symbols were not declared refused
because there is nothing yet to declare them refused *from*. Nothing here changes
any resolver status, and no locator preference was applied — the 26 disagreements
are recorded as measurements, not corrections.

## Task 4 — what the panel would still need, cost engine specifically

Reported only; nothing was implemented.

**The per-symbol cost engine does not exist.** `woodland/backtest.py:106` sets a
single `cost_rate = cost_bps / 1e4`, and line 139 collapses the per-symbol deltas
to a scalar immediately — `turn = float(np.abs(w - h).sum())` — before charging
`turn * cost_rate`. The signed specification requires
`sum_i(cost_rate_i * |dw_i|)`.

The code change is small and well-posed: `np.abs(w - h)` is already the
per-symbol vector the specification needs, so the sum becomes a dot product
against a rate vector aligned to `prices.columns`, with a scalar `cost_bps`
retained and broadcast so every existing call site behaves identically. That is
the easy part and it is not the blocker.

Four things gate it, three of them data rather than code.

1. **The decision is unsigned.** `2026-09-05-planning-decision-per-symbol-cost-model.md`
   states "Requires sign-off" and carries no `Status: SIGNED` line, unlike A2 and
   the date-match rule. It is a proposal.
2. **No symbol qualifies for a measured rate.** The calibration protocol requires
   at least 40 reconciled orders per symbol across at least 20 distinct regular
   sessions. `data/live/paper-drift.jsonl` holds **9 records across 2 symbols**
   (SPY and IEF). Zero symbols qualify, so every rate in a constituent panel of
   several hundred names would come from the fallback.
3. **The fallback would swallow the universe.** Unmeasured symbols take the
   highest measured per-symbol value. With effectively nothing measured, the
   entire panel is priced from fallback, and the decision itself requires that a
   challenger whose universe is mostly fallback be reported as such and its cost
   result not treated as measured. The engine would run and the output would not
   be a measured-cost result.
4. **Reproducibility is a stated precondition.** `scripts/reproduce_all.py` must
   reproduce every journalled number at the flat scenarios to existing precision
   after the change; if any historical figure moves, the change is wrong and is
   reverted rather than re-baselined.

Beyond cost, the panel needs the locator question settled for at least the 73
diverging symbols and a decision on the 26 where the preferred rule disagrees
with the resolved choice, since both determine which return series a constituent
contributes.

Note for later: `K ~ 232` was derived under a single-rate assumption. Under
per-symbol costs the turnover budget becomes strategy-specific. That
generalisation is not made here and the turnover-budget note is not amended.

## Prohibitions

No panel was built. No price data was changed. No backtest was run. No synthetic
bar was created. No approval and no A2 treatment was applied. No resolver status
or locator preference was changed. The census is read-only throughout.
