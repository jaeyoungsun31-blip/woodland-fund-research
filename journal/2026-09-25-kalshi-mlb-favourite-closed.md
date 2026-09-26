# Kalshi MLB favourite line: closed by its pre-registered kill rule

Date: 2026-09-25
Status: **CLOSED** under the kill rule in `explore/kalshi/precommit_mlb.md`
Scope: exploration under `explore/kalshi/`, not a harness study; no performance claim
Artifacts: `explore/kalshi/mlb_results.md`, `explore/kalshi/mlb_favourite.py`
(committed in `1ce0e53`); raw responses and per-game observations are
gitignored under `explore/kalshi/`
Related: `explore/kalshi/prereg_underdog_DRAFT.md` (UNSIGNED)

## Order of operations

1. **Holdout sealed first:** `5c8a205`
   (`explore/kalshi/HOLDOUT.md`, `holdout.py`, `test_holdout.py`). Every
   KXMLBGAME game with a scheduled start on or after 2026-01-01 UTC is
   sealed.
2. **Pre-registration second:** `46fd223` (`explore/kalshi/precommit_mlb.md`).
   Both commits came before any KXMLBGAME price, quote or candlestick was
   requested, for any season.
3. **The run:** 2025 season only. Every game passed
   `require_exploration_game` before its candles were requested. No 2026
   game was priced.

## Sample gate

| | Games |
|---|---:|
| 2025 KXMLBGAME events | 2,214 |
| Eligible after exclusions | 2,151 |
| Usable quote at 60 min | 2,008 |
| Usable quote at 10 min | 2,080 |

Both cutoffs cleared the 500-game gate. Pull time was 537.5 s, and every
candle came from the historical endpoint.

## Primary result

Buy the favourite at its ask, pay the KXMLBGAME taker fee, and hold to
settlement. The figure is mean net P&L per contract, with an iid bootstrap
over games (10,000 resamples, seed 0).

| Cutoff | Games | Mean net P&L | 95% interval |
|---|---:|---:|---|
| 60 min | 1,996 | −0.0432 | [−0.0646, −0.0220] |
| 10 min | 2,069 | −0.0395 | [−0.0609, −0.0188] |

The difference between usable quotes and games is 12 games at 60 minutes and
11 at 10 minutes. Those had equal YES and NO asks, and so no favourite.

**Verdict: CLOSED.** The interval lies entirely below zero at both cutoffs.
The price bands, calibration table and fee sensitivity were pre-declared as
descriptive, and none of them rescues it.

## Post-hoc observation — not a finding

Favourites won **55.2%** (60 min) and **55.6%** (10 min) of games against an
average ask of **0.587**. In the ask bands below 0.65, the win rate sat below
the ask in every band at both cutoffs. Favourites were overpriced relative to
realized frequency. That is the reverse of the usual favourite-longshot
pattern, in which longshots are overpriced.

This was **noticed after the results were seen**. It was not a pre-registered
hypothesis and is not a finding. It is recorded only because it motivates the
unsigned underdog draft, which is itself post-hoc in origin.

## Disclosures

- **Fee multiplier.**
  - [kalshi.com/fee-schedule](https://kalshi.com/fee-schedule), read
    2026-09-25, lists KXMLBGAME at a multiplier of 0.5 pre-game (1 live).
  - The base formula `round up(M × 0.07 × C × P × (1 − P))` was taken from the
    **search-indexed text** of *Fee Schedule for July 2026 – 7.7.26 Update*.
    Direct retrieval of the PDF was blocked by a bot challenge, so the PDF
    itself was not read.
  - The formula was checked against the page's published KXMLBGAME range of
    $0.04–$0.88 per 100 contracts.
- **Counterfactual fees.** 2026 fees were applied to 2025 prices. The fee in
  force in 2025 may have differed.
- **Exclusion labels.**
  - The MLB schedule files a postponed game's row under its make-up
    `officialDate`, so the dedicated doubleheader and
    postponed/rescheduled checks never fired (0 each).
  - Those games were excluded anyway, under earlier labels: 24 "no schedule
    match" and 35 "multiple schedule games".
  - A schedule-only diagnostic, which read no outcomes, confirmed the cause:
    all 24 no-match events have a `Postponed` row within a day, and 31 of
    the 35 multiple-match events include one.
- **The kept 1.00 ask.** One 60-minute observation, `KXMLBGAME-25APR19SFLAA`,
  had a YES bid of 0.00, making the NO ask 1.00. It is an empty-book artefact,
  kept as pre-registered, with net P&L 0.00.
- **2026 outcome exposure.** Explorations before the seal pulled 2026
  KXMLBGAME settled results, volumes and official schedules with final
  scores, though no prices. KXNHLGAME settled results were pulled in the same
  census. `HOLDOUT.md` lists the files. The 2026 MLB holdout is sealed but not
  pristine.
- **Other limits.**
  - A one-minute candle's closing ask is not a guaranteed fill, and depth
    was not observed.
  - Only the home-team order book was read.
  - One season.
