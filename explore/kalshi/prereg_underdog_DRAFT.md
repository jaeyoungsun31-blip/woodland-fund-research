# DRAFT — UNSIGNED — Kalshi underdog confirmation pre-registration

**Status: UNSIGNED DRAFT.** Nothing here is in force, and no data may be
fetched under it. Jaeyoung must choose the open items below and sign in a new
commit before any 2026, 2027 or NHL price is requested. Drafted 2026-09-25.

## Origin: post-hoc, and disclosed as such

This hypothesis was **formed after seeing results**. The pre-registered
favourite test (`46fd223`, results in `1ce0e53`, journal
`2026-09-25-kalshi-mlb-favourite-closed.md`) closed the favourite line, with
an interval below zero at both cutoffs. Afterwards, favourites were
**observed** to win 55.2% and 55.6% of games against an average ask of 0.587.
That is a reverse favourite-longshot pattern. The mirror strategy (buy the
underdog) was then computed on the **same 2025 data**. That number is
in-sample and **is not evidence**:

| Cutoff | 2025 games | Underdog mean ask | Mean net P&L (MLB fee) | Clustered t (in-sample) |
|---|---:|---:|---:|---:|
| 60 min | 1,996 | 0.425 | +0.0147 | 1.28 |
| 10 min | 2,069 | 0.424 | +0.0110 | 0.96 |

Even in-sample, where it is most flattering, this is not distinguishable
from zero. The 2025 season is used up and may **not** appear in any
confirmation sample.

## Outcome-data exposure

Explorations before any seal pulled **2026 KXMLBGAME settled results**,
volumes and official 2026 MLB schedules with final scores. The same census
pulled **KXNHLGAME settled results**, which include the 2025-26 season. See
`HOLDOUT.md` for the file list. **No price for either sample has been
fetched.** Neither sample is pristine: outcomes were on disk, although they
were never analysed against prices. Only a forward-collected 2027 MLB season
is untouched.

## Strategy (identical to `precommit_mlb.md` except the side bought)

- **Book and favourite:** events, the home-team book, the 60- and 10-minute
  cutoffs, the 300-second quote-age limit, and the favourite rule are all
  **exactly** as in `precommit_mlb.md`.
- **Underdog:** the side that is not the favourite. Buy one contract at its
  ask, which is `1 − favourite bid`:
  - favourite YES: buy NO at `1 − yes_bid`
  - favourite NO: buy YES at `yes_ask`
- **No favourite, no underdog:** a game with no favourite at a cutoff has no
  observation there.
- **Holding and fees:** hold to settlement. The fee is
  `round up(M × 0.07 × 100 × P × (1 − P))` to the cent, divided by 100, with
  M read from [kalshi.com/fee-schedule](https://kalshi.com/fee-schedule) on
  the signing date. As of 2026-09-25:
  - **KXMLBGAME** has M = 0.5 pre-live.
  - **KXNHLGAME** has M = 1, so NHL fees are about twice MLB's.
- **Fee counterfactual:** where the fee in force at trade time differs from
  the signing-date fee, the signing-date fee is used, and this is disclosed
  as a counterfactual.

## Confirmation sample — OPEN DECISION 1 (Jaeyoung)

Choose exactly one:

- **(a)** The 2026 MLB season: regular season plus postseason, KXMLBGAME.
- **(c)** (a) plus the 2025-26 NHL regular season (KXNHLGAME).
- **(d)** (a) plus the 2027 MLB season, collected forward. Evaluation happens
  only once 2027 is complete.

## Cutoff handling — OPEN DECISION 2 (Jaeyoung)

The favourite test reported each cutoff separately. The same games appear at
both cutoffs, so the two are not independent tests. Choose one:

- **Both cutoffs must pass.** Recommended: it selects no cutoff while the
  in-sample figures are in view.
- **One cutoff declared primary** at signing. Warning: the 60-minute in-sample
  edge is higher, so choosing it now would be a data-driven choice.

## NHL start times (only if (c) is chosen)

- **Source:** scheduled start from
  [api-web.nhle.com/v1/schedule/{date}](https://api-web.nhle.com/v1/schedule/2026-01-15)
  (`startTimeUTC`), public and keyless, regular season only (`gameType` 2).
- **Validation, before any price fetch.** Use the same 200-game method as
  MLB (`validate_mlb_starts.py`): 200 KXNHLGAME events, seed `20260923`,
  matched by local date and both teams. Pass requires at least 99% matched
  to exactly one game, and under 2% unparseable events.
- **Known gap.** `sports_start_validation_report.md` found that Kalshi's NHL
  rules text gives **no clock time**. So the MLB-style comparison of Kalshi
  start against official start cannot be replicated. The NHL validation
  checks the matching, not an independent clock time. The official schedule
  is the only clock source.
- **NHL exclusions:** the MLB rules translated to the NHL schedule's
  postponed, rescheduled and cancelled states.
- **Guard:** a holdout-style guard admitting only the chosen sample must be
  committed before the first fetch.

## Primary metric

- **What:** pooled mean net P&L per contract across the chosen confirmation
  sample, pooled over leagues and seasons.
- **Interval:** a 95% bootstrap interval, **clustered by game date**. Resample
  calendar dates (America/New_York) with replacement, with all games on a date
  moving together across leagues, 10,000 resamples, seed 0, percentile
  interval.
- **Pass:** the interval is entirely above zero, per decision 2.
- **Fail:** anything else. No secondary can rescue a failed primary. That
  includes league splits, price bands, calibration, alternate fees or
  alternate cutoffs. No window, filter, threshold, market or fee assumption
  may be added after results are seen.

## Power — post-hoc, in-sample, not evidence

- **Source:** computed by `underdog_power.py` from the 2025 observations.
- **Payoff SD:** the per-game SD is 0.492 (60 min) and 0.493 (10 min).
- **Date clustering:** the design effect is 1.085 and 1.122 over 183 dates.
- **Game counts:**
  - MLB 2026: 2,430 regular-season games, scaled by the 2025 usable yield per
    Kalshi event (0.902 and 0.935).
  - NHL 2025-26: 1,312 regular-season games, counted from api-web.nhle.com,
    with the same yield assumed.
  - NHL uses the same payoff SD and date design effect, but its fee is M = 1.
- **The assumed edge is the in-sample 2025 edge.** That edge is biased
  upward by selection, so the expected t below is **optimistic**.
- **MDE:** the minimum detectable edge at 80% power, with a two-sided 5% test
  (interval above zero).

| Design | Cutoff | Games | Assumed edge | SE | Expected t | MDE (80%) |
|---|---|---:|---:|---:|---:|---:|
| (a) MLB 2026 | 60 | 2,191 | +0.0147 | 0.0110 | 1.34 | 0.0307 |
| (a) MLB 2026 | 10 | 2,271 | +0.0110 | 0.0110 | 1.01 | 0.0307 |
| (b) NHL 2025-26 | 60 | 1,183 | +0.0063 | 0.0149 | 0.42 | 0.0418 |
| (b) NHL 2025-26 | 10 | 1,226 | +0.0026 | 0.0149 | 0.18 | 0.0418 |
| (c) (a)+(b) | 60 | 3,374 | +0.0118 | 0.0088 | 1.33 | 0.0247 |
| (c) (a)+(b) | 10 | 3,497 | +0.0081 | 0.0088 | 0.91 | 0.0248 |
| (d) (a)+MLB 2027 | 60 | 4,381 | +0.0147 | 0.0077 | 1.90 | 0.0217 |
| (d) (a)+MLB 2027 | 10 | 4,542 | +0.0110 | 0.0078 | 1.42 | 0.0217 |

**Reading the table.**

- **No design reaches an expected t of 2**, even when it assumes the
  optimistic in-sample edge.
- **Every MDE (2.2–4.2¢) is at least 1.5 times the in-sample edge**
  (1.1–1.5¢), and up to 16 times for NHL at 10 minutes.
- **Adding NHL lowers the expected t.** At M = 1, NHL fees remove most of the
  assumed edge.
- **The most likely outcome of any design is FAIL**, even if a small real
  edge exists.
- **Signing is still reasonable in one case:** if the purpose is to close the
  underdog question on record, rather than to find a trade.

## Data handling

Public unauthenticated GETs only. `.env` is not opened. Raw responses go under
gitignored paths only. There is to be no fetch of any price in the chosen
sample before the signed version of this document and its guard are
committed.
