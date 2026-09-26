# 2026-09-04 — planning note: what paper trading can and cannot measure

Append-only. Not a study. Written BEFORE Phase 4 is built, because planning has
repeatedly justified Phase 4 on a claim that is only partly true, and the
limitation must be on the record before any number produced by the drift
monitor is cited.

## The claim planning made, and the correction

Planning has said, more than once, that Phase 4's drift monitor "measures our
actual implementation cost" and thereby turns the 25-50 bps assumption behind
`K ~ 232` into an observed number. **That is an overstatement.**

Alpaca paper fills are simulated. Per Alpaca's own documentation, the
simulation matches orders against the real-time NBBO, but explicitly does NOT
model market impact, latency slippage, order queue position, price
improvement, information leakage, or regulatory fees; and order size is not
checked against available NBBO quantity, so a fill can exceed real liquidity.
Partial fills are injected at random on roughly 10% of eligible orders.

## What that leaves, stated precisely

**Measured with real data:** the quoted spread being crossed at the moment of
submission, since fills occur at the prevailing NBBO. Also the decision-to-
submission delay, the schedule's reliability, and whether the pipeline
produces the intended orders at all.

**Not measured:** impact, latency slippage, queue position, fees, and the
true fill quality that only real capital reveals.

Therefore a paper-derived cost figure is a **lower bound** on true one-way
cost, not an estimate of it. It must be reported that way, always.

## Why the bound is still useful — and where it is not

For the declared incumbent (60/40 in SPY and IEF, monthly, at a five-figure
account size) the omitted components are genuinely small: a retail-sized order
in the two most liquid instruments in the US market has essentially no impact,
and commissions are zero. For that portfolio the quoted spread is most of the
true cost, so the bound should be close.

For the strategies that actually failed on cost, it is not close at all. The
v13 and v15 momentum constructions imply holding hundreds of small- and
mid-cap names. There, impact and liquidity are a large fraction of true cost,
and paper trading — which will happily fill an order larger than the entire
displayed size — is exactly the wrong instrument.

**The consequence, stated so it cannot be mis-cited later: Phase 4 will
produce a defensible cost figure for the incumbent and will NOT resolve
whether the momentum sleeve is affordable.** The post-1980 question is not
answered by paper trading. Any future study proposing to reopen it on the
basis of a Phase 4 cost number is refused under T2.

## What Phase 4 is genuinely for

1. Operational proof: the loop runs unattended, on schedule, and refuses when
   it should — validated against a broker rather than a test fixture.
2. Order-path correctness: targets become the intended orders, and the round
   trip reconciles.
3. A real, if optimistic, spread-cost measurement for the incumbent.
4. A drift record accumulating from day one, so that if real capital is ever
   committed the comparison is available.

Those are worth the build. The cost claim is not the reason, and planning
should stop citing it as one.

`[Certain]` on Alpaca's documented fill behaviour. `[Likely]` that the paper
bound is within a few bps of truth for SPY/IEF at this account size.
`[Speculative]` and not to be relied on for anything else.
