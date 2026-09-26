# 2026-09-26 — planning decision: the Kalshi exploration is closed

Status: **DECIDED** in planning on Jaeyoung's instruction. No prior entry is
edited.

Closes the Kalshi line under `explore/kalshi/`. The favourite test and its
evidence are recorded in `2026-09-25-kalshi-mlb-favourite-closed.md`,
committed with the unsigned underdog draft in `bf35f2e`. The power script
behind the figures below is `explore/kalshi/underdog_power.py` (`667a527`).

## Decision

**The underdog pre-registration (`explore/kalshi/prereg_underdog_DRAFT.md`)
stays UNSIGNED and is abandoned.** No 2026 MLB, 2027 MLB or NHL price will be
fetched under it. The 2026 KXMLBGAME holdout stays sealed and unused.

## Reasons

- **The in-sample edge was not distinguishable from zero.** The mirror
  underdog trade on the same 2025 data that motivated it earned:
  - +0.0147 per contract at 60 min (t = **1.28**)
  - +0.0110 per contract at 10 min (t = **0.96**)

  These t-statistics are date-clustered. The trade is post-hoc and
  in-sample, so these figures flatter it.
- **No available confirmation sample has the power.** The designs assumed the
  in-sample edge, which is optimistic. Even two MLB seasons (2026 plus a
  forward 2027) give an expected t of at most **1.90**. The minimum
  detectable edge at 80% power is about 2.2¢, against the in-sample 1.1–1.5¢.
  Adding the 2025-26 NHL season lowers the expected t, because KXNHLGAME's fee
  multiplier is 1 against MLB's 0.5 pre-live.
- **Taker costs take about half of the observed mispricing.**
  - Measured at the mid-price, favourites were overpriced by **2.9¢** at
    60 min and **2.5¢** at 10 min. The favourite mid was 0.581 against win
    rates of 55.2% and 55.6%.
  - A taker pays about **1.4¢** of that: a mean half-spread of 0.58¢ plus a
    mean underdog fee of 0.85¢.
  - What is left, 1.1–1.5¢, is the in-sample edge above. It is statistically
    indistinguishable from zero.
  - "Roughly consumed" in planning's framing is best read as *half consumed,
    and the remainder undetectable*.
  - The mid-price gap is itself a post-hoc observation, not a finding.
- **A maker strategy cannot be tested historically.** Resting at or inside
  the spread would avoid the half-spread and pay the lower maker fee. But a
  fill depends on queue position and on who trades against the order, and
  neither is in the candlestick data. Historical candles show quotes, not
  whether a resting order would have filled, or at what adverse selection.
  Any maker backtest would be an upper bound, like the KXCPI pilot's
  `pilot_maker_pnl.csv`, not a result.

## What remains on the record

- Favourite line: **closed** by its pre-registered kill rule.
- Underdog line: **abandoned unsigned**. It was never tested out of sample
  and makes no claim either way.
- The 2026 MLB and KXNHLGAME samples remain unpriced. As disclosed in
  `explore/kalshi/HOLDOUT.md`, their outcomes are already on disk, so any
  future use must say so.
