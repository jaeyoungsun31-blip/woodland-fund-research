# Planning finding — the ETF snapshot writer is the live cycle; do not re-pin

Date: 2026-09-07
Status: finding (supersedes one line; blocks the proposed remedy)
Supersedes: the sentence "The writer has not been established" in
`2026-09-07-xsmom-v16-panel-snapshot-refusal.md`. Every other statement in that
entry stands, and the refusal itself was correct.

## The writer

`scripts/run_cycle.py --execute --emit-targets --submit-paper --refresh-data`,
completed 15:00:21 EDT 2026-09-07. Its own log is `data/live/cycle-stdout.log`
and it journalled itself as `2026-09-07-phase3-cycle-150021.md`. The refresh arm
rewrote all 20 ETF parquets and `data/_provenance.json` in the same pass:

```
_provenance.json  fetched_at "2026-09-07T19:00:19+00:00"  primary_source yahoo
file mtimes       15:00:06 .. 15:00:19 EDT, sequential by symbol
```

Not a mystery process, not corruption, not an agent. The research snapshot and
the live trading loop share one mutable price store, and the loop refreshes it
on every weekday run.

## What changed, and what did not

No new bars. `rows` 6968 and `last` 2026-09-04 are unchanged, and 2026-09-07 was
a market holiday — the cycle's own log records `submission refused:
market_closed`. File sizes moved in **both** directions:

```
XLK  304372 -> 304389   (+17)
XLB  299056 -> 299067   (+11)
TLT  255987 -> 255916   (-71)
XLV  290830 -> 290769   (-61)
SPY  341006 -> 340972   (-34)
XLC  101080 -> 101078   ( -2)
```

Sizes falling rules out appended rows. This is Yahoo restating adjusted close
backward — routine vendor behaviour that recurs on every distribution revision.

## It is a data change, not an encoding change

Two independent proofs:

1. The registered hash is taken over `adj_close` as sorted date-index CSV at
   `%.17g`, not over file bytes. Parquet re-encoding alone cannot move it.
2. The cycle's own bounded target moved with no new bars, the same incumbent,
   and a closed market:

```
2026-09-04 run   {"SPY": 0.6022491277692078, "IEF": 0.3977508722307921}
2026-09-07 run   {"SPY": 0.6022423776268814, "IEF": 0.3977576223731186}
```

The restated history propagated into a live target. That is the measurement the
refusal was missing.

## Correction to a tempting reading

A restated adjustment series is **not** a lookahead surface. Adjusted-close
daily returns satisfy `r_t = adj_t/adj_{t-1} - 1`, which picks up only the
event at `t`; a fold trained as of 2010 does not inherit 2011–2026 dividends
through the price series. Recording this because the opposite claim is the
intuitive one and would have been wrong.

The real harm is narrower and still disqualifying for a pinned study: a past
day's return can change retroactively, so **reproduction is not guaranteed and
journalled Sharpes can move with no one touching the code.** The 53/53
reproduction pass described a series the vendor has since revised.

## Why re-pinning is the wrong remedy

Re-pinning registers a silently restated history as ground truth, destroys the
ability to state what the 53 anchors were computed against, and fixes nothing:
the next weekday cycle refreshes the store again. Under the current layout any
pinned research run has a shelf life of about one trading day.

## Open

The plist `ops/com.jaeyoung.woodland.cycle.plist` (mtime 2026-09-04 18:49) is
scheduled `Hour 15, Minute 45`. The run completed at 15:00:21. The schedule does
not explain the invocation. An unaccounted path that runs `--refresh-data` and
`--submit-paper` is its own problem and is not closed by this entry.

Unrelated and unnoticed since 2026-09-04: `data/live/cycle-stderr.log` ends in
`403 Client Error: Forbidden for url: https://paper-api.alpaca.markets/v2/orders`
at `woodland/live/broker.py:118`. Phase 4 has not been submitting.
