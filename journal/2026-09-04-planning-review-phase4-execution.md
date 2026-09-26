# 2026-09-04 — planning review: Phase 4 paper execution

Append-only review of commits `184201f` and `9b541a5`. Nothing was run and no
order was submitted. Verdict: **the safety architecture is accepted; the
measurement path has one blocking defect and one material labelling defect,
and must be fixed before the first submission.**

## Accepted without reservation

`assert_paper_base_url` requires scheme `https` and hostname exactly
`paper-api.alpaca.markets`, and is re-checked immediately before every GET and
POST rather than only at construction. `woodland/live/alpaca.py` is read-only
by construction — it defines no POST, PUT or DELETE path at all. Secrets are
read through `get_secret`, travel in headers, and are never logged or written
to a record. `validate_submission` accumulates **every** refusal reason and
raises before the first order request, so a batch cannot be partly submitted.
Guards cover the Phase 3 refusal, market-closed, per-symbol weight bounds,
gross exposure over 100%, and a per-order notional cap. Drift records are
JSONL, append-only, and outside the trials ledger, and carry a standing
`cost_label` naming the paper simulator's omissions.

This is the correct shape for something that can place orders.

## F1 — BLOCKING: fills are never observed

`submit_rebalance` reads `filled_avg_price`, `filled_at` and `filled_qty`
directly from the POST `/orders` response. A market order returns immediately
in an `accepted` or `new` state; those three fields are null at that instant.
Nothing anywhere polls `GET /orders/{id}` — the only `sleep` in the package is
the SQLite lock retry at `cycle.py:385`.

Consequence: `fill_price`, `fill_timestamp`, `fill_quantity` and
`signed_implementation_shortfall_bps` will be null on essentially every
record. **The drift monitor, which is the entire reason Phase 4 exists, will
record no fills.**

Required fix: reconcile after submission. Preferred design is a separate
reconciliation pass that reads open and recently-filled orders at the start of
the next cycle and completes the earlier record, because it survives a crash
or a shutdown between submit and fill. A bounded in-process poll of
`GET /orders/{id}` with an explicit timeout is acceptable as well, provided a
timeout writes the record with fills still null and a reason, rather than
silently dropping the observation.

## F2 — MATERIAL: the quote feed is IEX, and is labelled NBBO

Both modules request `feed: "iex"`, but every field and message calls the
result NBBO: `nbbo_bid`, `nbbo_ask`, `nbbo_spread`, `quoted_half_spread_bps`'s
error text, and "no NBBO quote for {symbol}".

IEX is a single venue carrying a low single-digit percentage of consolidated
US volume. Its quote is not the NBBO and is typically **wider**. The measured
half-spread is therefore biased **upward** — it overstates cost. Alpaca's free
market-data tier is IEX-only; the consolidated SIP feed is a paid
subscription, so using IEX is a legitimate constraint rather than a mistake.
Mislabelling it is not.

Required fix: rename every `nbbo_*` field and message to `iex_*`, record the
feed identifier on each drift record, and state the upward bias wherever a
cost figure is reported.

Note for whoever later cites these numbers: the IEX feed biases the measured
spread **up**, and the paper simulator biases the realised cost **down**
(`2026-09-04-planning-note-what-paper-trading-can-measure.md`). Two biases of
unknown magnitude in opposite directions do not produce an unbiased estimate.
Report both directions; never present the net as if it were the truth.

## F3 — DESIGN: the decision price makes shortfall nearly tautological

`plan_rebalance` sets `decision_price` to the current quote midpoint. When a
market order is submitted immediately against that same quote, the signed
shortfall is approximately the half-spread by construction, so
`signed_implementation_shortfall_bps` is close to a restatement of
`quoted_half_spread_bps` rather than an independent measurement.

The informative quantity is measured against **the close the target was
actually computed from**, which is what the Phase 4 specification asked for.
That captures delay cost between decision and execution, which is a real
component of implementation shortfall and the only one this setup can observe
that the half-spread does not already give.

Required fix: carry the decision close and its timestamp from the cycle into
`PlannedOrder`, and record shortfall against it. Keep the mid-quote figure as
a separate labelled field if useful; do not conflate the two.

## F4 — MINOR

No journal entry was written for the Phase 4 implementation. Every prior piece
of work in this repository has one, and the engineering record should not
start being optional now.

Also minor: `plan_rebalance` fetches quotes before `market_open()` is
consulted, so a closed-market cycle fetches stale quotes and then refuses.
Harmless, but check the clock first.

## Standing instruction

No order is submitted until F1 and F2 are fixed. F1 because the run would
produce no measurement; F2 because it would produce a mislabelled one, and a
mislabelled number in an append-only record is worse than no number.
