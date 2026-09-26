# Game-winner rules-time validation — exploration only

Pre-inspection suite: `619 passed, 1 skipped in 90.59s (0:01:30)`.

Scope was limited to `KXNBAGAME`, `KXMLBGAME`, `KXNFLGAME`, and `KXNHLGAME`. The [Kalshi historical-market schema](https://docs.kalshi.com/api-reference/historical/get-historical-markets) exposes `rules_primary`, the source of the scheduled-time text. The census used public settled-market endpoints and did not use volume for selection, weighting, or ranking. A clock time was accepted only when the rules stated a date, time, and EST/EDT suffix. `America/New_York` timezone rules supplied the UTC conversion, and the stated suffix had to agree with DST on that date. An unparseable string was never assigned a guessed time.

| League | Settled markets | Events | Non-YES/NO markets excluded | Clean events | Parsed clean events | Parse failures | Parse-failure rate | Eligible? |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| NBA | 2,898 | 1,449 | 6 | 1,446 | 0 | 1,446 | 100% | No; also unvalidated |
| MLB | 9,156 | 4,578 | 20 | 4,568 | 2,339 | 2,229 | 48.8% | No |
| NFL | 828 | 414 | 12 | 408 | 0 | 408 | 100% | No; also unvalidated |
| NHL | 3,132 | 1,566 | 2 | 1,565 | 0 | 1,565 | 100% | No |

Representative rules-text failures:

- NBA: “If San Antonio wins the Game 5: New York at San Antonio professional basketball game originally scheduled for Jun 13, 2026, then the market resolves to Yes.” It gives no clock time.
- MLB: “If Toronto wins the Los Angeles D vs Toronto (Game 6) professional baseball game originally scheduled for Oct 31, 2025, then the market resolves to Yes.” It gives no clock time. A separate clock-bearing MLB case, “If AL wins the AL vs NL professional baseball game originally scheduled for Jul 14, 2026 at 8:00 PM EDT, then the market resolves to Yes,” could not be matched to an MLB club-vs-club schedule entry without guessing a team mapping.
- NFL: “If Seattle wins the Los Angeles R at Seattle professional football divisional round game, then the market resolves to Yes.” It gives no clock time.
- NHL: “If VGK Golden Knights wins the Game 6: Carolina at Vegas professional hockey game scheduled for Jun 14, 2026, then the market resolves to Yes.” It gives no clock time.

The public [official MLB schedule API](https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-07-23) returned games with team identities, UTC `gameDate`, and status without a key. A deterministic random sample of 200 unique parsed MLB games (seed `20260923`) was matched by local date and both teams. **200/200 (100%)** matched within ±15 minutes; in fact all 200 differences were zero minutes and all official statuses were `Final`. Every comparison and the empty mismatch list are in `mlb_start_validation.json`. The parsed clean MLB events all occurred in 2026; this coverage cannot support the requested 2025-07-01 before/after split. The free [official NHL schedule API](https://api-web.nhle.com/v1/schedule/2026-06-14) responded without a key, but there were zero parsed NHL games to sample. NBA and NFL were deliberately marked unvalidated and excluded, as permitted by the request.

All four leagues fail the stated usability rule: at least 99% official-time agreement **and** under 2% parse failures. The 40 non-YES/NO market records were excluded. Actual postponed/rescheduled-game counts for the full censuses were not inferred from generic rules text; since no league passed the start-time gate, no market entered the strategy sample. No candlestick or final-hour trade pull was started, so there is no pull time for that stage, quote coverage, wash-trade share, favourite-strategy P&L, hit rate, event bootstrap interval, or last-trade sensitivity result. No significance claim is made.
