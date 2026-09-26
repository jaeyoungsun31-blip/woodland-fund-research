# 2026-09-01 — Promotion gate pre-registration (BINDING)

Signed off by Jaeyoung on 2026-09-01. Per DESIGN.md §8, amending these
thresholds requires a NEW dated journal entry BEFORE the retrain cycle in
which the amendment applies. This file is append-only history — never edit.

## The gate

A challenger replaces the incumbent only if, on the stitched walk-forward
out-of-sample history:

1. Net-of-cost Sharpe exceeds the incumbent's by >= 0.10
2. Max drawdown <= 1.25x the incumbent's
3. Condition 1 still holds at 10 bps one-way costs
4. Annualized turnover <= 1.5x the incumbent's

Ties or marginal wins keep the incumbent. Inertia is the correct prior;
churn is a cost.

## Execution-timing note (v0)

DESIGN.md §6 specified close-signal → next-OPEN fill. Engine v0 executes at
next CLOSE instead: adjusted open series are not yet validated, and
next-close is the more conservative timing (a full extra bar of delay).
Revisit when adjusted opens are cross-checked; any change is a journal entry.

## Trials ledger

Ledger starts at zero as of this date. Every configuration evaluated by the
harness — including abandoned ones — increments it. Deflated Sharpe is
computed against the ledger count, not against the trials we felt like
remembering.
