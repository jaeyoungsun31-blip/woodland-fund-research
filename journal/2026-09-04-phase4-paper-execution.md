# 2026-09-04 — Phase 4 paper execution implementation

Append-only engineering record. Not a study, signal fit, challenger evaluation,
or promotion decision.

Phase 4 connects the declared `balanced-60-40` SPY/IEF incumbent to Alpaca
Paper only. The runner stays dry-run by default. Submission requires explicit
`--execute`, `--emit-targets`, and `--submit-paper` authority. The endpoint
guard accepts only the exact `paper-api.alpaca.markets` HTTPS hostname before
each order request; no live-money endpoint is available through this path.

Before an order, the cycle retains the decision close and timestamp used to
form the target. The broker checks the paper market clock before requesting
IEX quotes, validates all refusal conditions before its first POST, and logs a
pending JSONL drift record immediately after each accepted order response.

At the start of a later explicit paper cycle, pending order IDs are reconciled
through `GET /orders/{id}` and an append-only resolving record adds terminal
fill timestamp, price, and quantity. A non-terminal response becomes an
explicit reconciliation-timeout record with null fill fields and a reason; it
is never silently dropped. This permits recovery after a process stop between
submission and fill.

Implementation shortfall is signed against the stored decision close. The IEX
mid-quote comparison remains a separate labelled field. Every paper-derived
cost is a lower bound because the simulator omits impact, latency slippage,
queue position, price improvement, fees, and liquidity constraints. IEX is
not a consolidated quote: its observed spread is biased upward. These
opposing biases are reported separately and are not treated as an unbiased
cost estimate.

The incumbent remains fixed at 60% SPY / 40% IEF. No challenger was evaluated
or promoted; v17's failed C3 remains binding for this paper-execution path.
