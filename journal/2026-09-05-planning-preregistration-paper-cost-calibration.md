# 2026-09-05 — pre-registration: paper cost-calibration protocol

Append-only planning protocol, written before qualifying additional paper-fill
observations are collected or used. This is not a study, does not alter a
cost scenario, and does not authorize a selective rerun or promotion. It
implements the signed-off per-symbol model in
`2026-09-05-planning-decision-per-symbol-cost-model.md`.

## Eligibility, fixed in advance

A symbol qualifies for a measured paper-cost rate only after **at least 40
reconciled orders for that symbol**, spanning **at least 20 distinct regular
market sessions**. A session is the America/New_York calendar date of the
order's submit timestamp. The threshold therefore applies separately to SPY,
IEF, and every later target symbol; 40 observations concentrated in one week
or in another symbol do not qualify a symbol.

An eligible observation is a durable drift-log record with event
`reconciled`, a positive decision close, positive fill price and quantity, a
valid buy or sell side, and a submit timestamp. Orphans, reconciliation
timeouts, records lacking a fill, and non-terminal records do not count. No
outlier is removed after inspection.

## Statistics, fixed in advance

For every target symbol, report separately:

1. the median signed implementation shortfall in basis points against the
   recorded decision close, where positive is adverse for both buys and sells;
2. the median IEX quoted half-spread in basis points at order submission.

The two figures are never combined or netted. The first statistic, clamped at
zero if its median is favourable, is the symbol's **paper-derived lower-bound
cost rate** for the measured scenario. The IEX half-spread is a separately
reported diagnostic, not an additive charge: it is already one component of a
fill relative to the decision close and adding it would double count it.

Every table, figure, and reported measured-cost number carries both standing
bias directions verbatim: **IEX quotes are biased upward relative to the
consolidated quote; paper fills are biased downward relative to real
implementation cost.** Consequently the measured rate is a lower bound, not
an estimate of live implementation cost.

## Rule after qualification

The flat `cost_bps_scenarios: [0, 5, 10]` in `config/universe.yaml` remain
unchanged for continuity. A separately named measured scenario is added as a
per-symbol map whose eligible symbols receive their paper-derived lower-bound
rate. A symbol that has not met the threshold receives the highest qualified
per-symbol measured rate, exactly as fixed in the per-symbol cost decision.
Every result reports both the flat scenarios and the measured scenario,
including the count of measured versus fallback-priced symbols.

Before the measured scenario is used, `scripts/reproduce_all.py` must first
reproduce every existing journalled flat-scenario anchor at its published
precision. It must then re-evaluate **every registered study** at the measured
per-symbol scenario. The result is either a complete, reproducible
all-studies recalculation or no recalculation at all: no family, sleeve,
strategy, cost level, era, or favourable subset may be rerun selectively.
The trials ledger is not rewritten; the measured-cost output is an append-only
recomputation record.

## Scope limits

This protocol calibrates only the paper-execution lower bound for instruments
that have qualifying observations. It does not measure impact, latency
slippage, queue position, price improvement, fees, or liquidity constraints,
and therefore cannot establish the affordability of historical
many-name momentum constructions. It cannot change the pre-registered gate,
incumbent, or promotion status.
