**Kill rule: CLOSED.** The primary 95% interval lies entirely below zero at both cutoffs (60 min: [−0.0646, −0.0220]; 10 min: [−0.0609, −0.0188]), so the Kalshi favourite line is closed.

# Kalshi MLB favourite test — 2025 season results

Run 2026-09-25 exactly as pre-committed in [precommit_mlb.md](precommit_mlb.md)
(`46fd223`), after the holdout seal in [HOLDOUT.md](HOLDOUT.md) (`5c8a205`).
The pre-run suite ended `619 passed, 1 skipped in 84.01s (0:01:24)`, and the
holdout guard test ended `7 passed`. Code: [mlb_favourite.py](mlb_favourite.py).
Every game passed `require_exploration_game` before its candles were
requested, and again before P&L. No 2026 game was priced. Public
unauthenticated GETs only. Raw responses are in the gitignored `mlb2025_raw/`,
`mlb2025_observations.jsonl`, `mlb2025_gate.json` and
`mlb2025_results.json`. This is an exploration, not a harness result, and
makes no performance claim.

## Sample gate

| | Count |
|---|---:|
| 2025 KXMLBGAME events | 2,214 |
| Not clean YES/NO settled | 4 |
| No schedule match | 24 |
| More than one schedule game for the date and team pair | 35 |
| **Eligible games** | **2,151** |
| **Usable quote at 60 min** | **2,008** |
| **Usable quote at 10 min** | **2,080** |
| Pull time (schedules, teams, cutoff, 2,151 candle requests) | 537.5 s |

Both cutoffs cleared the 500-game gate. All 2,151 markets settled before the
historical cutoff (`market_settled_ts` 2026-07-27), so every candle came from
the historical endpoint.

**How the exclusions fell.** The statsapi schedule files a postponed game's
row under its make-up `officialDate`. As a result:

- Every postponed or doubleheader game failed one of the two earlier checks,
  for one of two reasons:
  - the ticker's original date had no row left (the 24 no-match events)
  - the date and team pair returned two or three rows (the 35
    multiple-match events)
- A diagnostic, which read schedule rows only and no outcomes, confirmed the
  split:
  - all 24 no-match events have a `Postponed` row for the same pair within a
    day
  - 31 of the 35 multiple-match events include a `Postponed` row, and the
    other 4 are same-date pairs
- So the dedicated doubleheader and postponed/rescheduled checks were never
  reached, and they excluded 0. The games the precommit meant to exclude were
  excluded. They are counted under the earlier labels.

## Primary: mean net P&L per contract, favourite at the ask, held to settlement

| Cutoff | Games | Mean net P&L | 95% bootstrap interval | Win rate | Mean ask | Mean fee |
|---|---:|---:|---|---:|---:|---:|
| 60 min | 1,996 | **−0.0432** | [−0.0646, −0.0220] | 55.2% | 0.5869 | 0.0084 |
| 10 min | 2,069 | **−0.0395** | [−0.0609, −0.0188] | 55.6% | 0.5874 | 0.0084 |

- **Why fewer games than usable quotes.** A usable quote with equal YES and
  NO asks has no favourite. That applied to 12 games at 60 minutes and 11 at
  10 minutes.
- **The bootstrap** is iid over games, 10,000 resamples, seed 0.
- **Fee:** `round up(0.5 × 0.07 × 100 × P × (1 − P))` to the cent, divided
  by 100, using KXMLBGAME's pre-live multiplier of 0.5. Applying 2026 fees to
  2025 prices is a counterfactual.
- **The loss is mostly price, not fee.** Favourites won 3.1 to 3.5 points less
  often than their ask implied. The fee adds about 0.8¢.

**Fee sensitivity (declared, descriptive).** On one-contract orders the fee is
$0.01 on every trade. That gives −0.0448 [−0.0662, −0.0235] at 60 minutes
and −0.0411 [−0.0625, −0.0204] at 10 minutes.

## Secondary (descriptive only; cannot rescue the primary)

**By favourite ask band**

| Band | 60 min: n | mean | 95% interval | 10 min: n | mean | 95% interval |
|---|---:|---:|---|---:|---:|---|
| (0.50, 0.60) | 1,240 | −0.0481 | [−0.0762, −0.0203] | 1,281 | −0.0334 | [−0.0601, −0.0059] |
| [0.60, 0.70) | 622 | −0.0482 | [−0.0875, −0.0097] | 644 | −0.0670 | [−0.1045, −0.0287] |
| [0.70, 1.00] | 134 | +0.0258 | [−0.0476, +0.0961] | 144 | +0.0298 | [−0.0408, +0.0976] |

The [0.70, 1.00] band's point estimate is positive, but its interval spans
zero on about 140 games. It was pre-declared as descriptive and does not
reopen the line.

**Calibration: realized favourite win rate against ask**

| Ask band | 60 min: n | mean ask | win rate | Wilson 95% | 10 min: n | mean ask | win rate | Wilson 95% |
|---|---:|---:|---:|---|---:|---:|---:|---|
| 0.50–0.55 | 583 | 0.525 | 48.9% | [44.8, 52.9] | 593 | 0.525 | 51.4% | [47.4, 55.4] |
| 0.55–0.60 | 750 | 0.572 | 53.2% | [49.6, 56.7] | 790 | 0.573 | 52.9% | [49.4, 56.4] |
| 0.60–0.65 | 429 | 0.618 | 55.7% | [51.0, 60.3] | 435 | 0.617 | 54.0% | [49.3, 58.7] |
| 0.65–0.70 | 224 | 0.672 | 68.3% | [61.9, 74.0] | 238 | 0.671 | 66.0% | [59.7, 71.7] |
| 0.70–0.75 | 102 | 0.715 | 73.5% | [64.2, 81.1] | 111 | 0.716 | 75.7% | [66.9, 82.7] |
| 0.75–0.80 | 31 | 0.764 | 83.9% | [67.4, 92.9] | 32 | 0.763 | 78.1% | [61.2, 89.0] |
| 0.80–0.85 | — | — | — | — | 1 | 0.800 | 100% | [20.7, 100] |
| 0.95–1.00 | 1 | 1.000 | 100% | [20.7, 100] | — | — | — | — |

Below an ask of 0.65, favourites won less often than the ask implied in every
band at both cutoffs.

The single 60-minute observation at ask 1.00 (`KXMLBGAME-25APR19SFLAA`) is an
empty-book artefact. Its candle has YES bid 0.00, so the NO ask is 1.00. It
was kept as pre-registered, and its net P&L is 0.00.

## Other required figures

| | 60 min | 10 min |
|---|---|---|
| Worst single-game loss | −0.7861 (`KXMLBGAME-25APR20MIAPHI`, YES at 0.78) | −0.7762 (`KXMLBGAME-25AUG26COLHOU`, YES at 0.77) |
| Share of observations with favourite ask ≥ 0.70 | 6.7% (134/1,996) | 7.0% (144/2,069) |

**Quote quality (descriptive).** The median quote age was 0 seconds at both
cutoffs, meaning the candle ended on the cutoff minute in 72.8% and 81.5% of
usable games. The median YES spread was 1¢ and the mean 1.16¢. The loss is
therefore not a wide-spread artefact.

## Limits

- A one-minute candle's closing ask is not a guaranteed fill, and book depth
  is not observed.
- The home-team book was fixed in advance. The away book was never read.
- The fees are 2026 fees applied to 2025 prices.
- One season was tested. The 2026 holdout remains sealed, but it is not
  pristine: see the disclosure in [HOLDOUT.md](HOLDOUT.md).
