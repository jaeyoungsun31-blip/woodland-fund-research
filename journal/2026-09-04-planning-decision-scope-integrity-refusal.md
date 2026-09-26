# 2026-09-04 — planning decision: scope the blocking integrity refusal to the traded universe

Append-only. Amends the refusal conditions implemented under
`2026-09-03-planning-direction-phase3-the-machine.md`. Requires sign-off;
until signed, the current store-wide blocking behaviour stands.

## What happened

The first live cycle (`journal/2026-09-04-phase3-cycle-140935.md`, 14:09:35)
refused and submitted nothing. The refusal was correct behaviour and the
fail-closed ordering worked: reconciliation, registry initialisation, ledger
writes and submission were all skipped, and no state was left behind.

The reason was eleven `crosscheck='INVESTIGATE'` verdicts: XLB, XLE, XLI,
XLK, XLP, XLU, XLV, XLY, QQQ, EFA, DBC. These are the 63 historical
observations exceeding the 2% Yahoo/Tiingo threshold recorded on 2026-09-01
and documented in `CLAUDE.md`. They are a known, static condition, not new.

**The declared incumbent is `balanced-60-40`: 60% SPY, 40% IEF. Neither
appears in that list.** Both carry crosscheck blocks in `_provenance.json`
with no INVESTIGATE verdict. The loop is therefore refusing to trade two
instruments whose integrity checks pass, because eleven instruments it does
not hold have stale cross-source disagreements.

As implemented this is not a transient halt. It will refuse every cycle
indefinitely, so the loop cannot operate at all.

## The tension, stated plainly

Narrowing a safety condition because it is preventing the system from running
is precisely how safety discipline erodes, and the motive here is exactly
that: planning wants the loop to work. That motive is named rather than
hidden, because a reader in six months should be able to judge the change
knowing why it was made.

The argument against narrowing is real. Eleven simultaneous cross-source
disagreements could indicate something systematically wrong with ingestion,
in which case SPY and IEF may not be genuinely clean — they may simply not
have crossed the 2% threshold. Store-wide failure as a canary for
instrument-specific trust is a defensible design.

The argument for narrowing is that a refusal which can never clear is not a
safety property. It is an outage. A condition that blocks every cycle forever
provides no information after its first firing, and a system permanently
halted is one nobody will keep running honestly — the realistic failure mode
is that the check gets disabled hastily under time pressure rather than
amended deliberately now.

## Decision

**The blocking integrity check is scoped to the tickers the cycle would
actually trade. The store-wide check is retained as a non-blocking warning
recorded on every cycle.**

Binding conditions on the change:

1. **Scope is derived, not declared.** The blocking set is computed from the
   symbols in the cycle's emitted target, not from a configured list. A
   strategy that later holds XLK is blocked by XLK's verdict automatically,
   with no further amendment.
2. **Any INVESTIGATE verdict on a traded ticker still refuses.** Unchanged
   and non-negotiable.
3. **The store-wide result is recorded every cycle**, in the cycle journal,
   naming each flagged ticker. It never silently disappears. A cycle that
   trades cleanly while eleven other tickers are flagged says so in writing.
4. **A rise is escalated.** If the count of store-wide INVESTIGATE tickers
   exceeds the count at the time of this decision — eleven — the cycle
   refuses regardless of scope, because a *growing* disagreement is evidence
   of an active ingestion problem rather than a known static one. The
   baseline count is stored, not hardcoded in a comment.
5. **This authorises no other narrowing.** Stale data, fold-count mismatch,
   calendar integrity and the sanity anchors remain store-wide and blocking.
   A future proposal to scope any of those requires its own dated decision
   and may not cite this one as precedent.

## What this does not do

It does not resolve the eleven verdicts. They remain an open data-quality
issue, the store remains "dual-source checked but not clean" exactly as
`CLAUDE.md` describes it, and no research result that depends on those eleven
tickers gains any credibility from this decision. Clearing them is separate
work and is not scheduled here.

## Status

Requires Jaeyoung's sign-off. Until signed, cycles continue to refuse.
