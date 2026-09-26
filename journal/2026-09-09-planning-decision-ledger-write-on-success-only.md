# Decision — the trials ledger records on arm success only

Date: 2026-09-09
Status: SIGNED 2026-09-09 by Jaeyoung ("yes, and yes"), recorded by planning.
Scientific change: alters how the anti-p-hacking record behaves. Not mechanics.

## The defect

`woodland/harness/costaware_panel.py` writes the ledger batch after **fitting**
(~line 234). The OOS phase runs afterwards (~line 321). An arm that fits and
then refuses at OOS therefore leaves a full batch in the ledger, marked
`status='evaluated'`, for a run that produced no out-of-sample result.

Measured:

```
xsmom-v16-panel-dual-v4-A-20260909   352 rows   status='evaluated'
                                     written 2026-09-09T03:08:15..03:08:19Z
                                     arm then refused: {"phase":"OOS",
                                     "reason":"risk_free contains non-finite values"}
```

Three consequences:

1. **Phantom evaluations inflate the trial count**, and the trial count feeds
   the deflated-Sharpe gate. The record overstates how much was evaluated.
2. **Every failed attempt permanently burns a study ID**, forcing a version
   bump (v3 → v4 → v5), each failure adding 352 mislabelled rows. A treadmill
   with a ratchet.
3. The `status` value is false for those rows.

## Decision 1 — record on success only

The ledger write becomes **atomic with arm success**, at the same moment as the
staging-directory promotion. An arm that does not reach a valid OOS result
records `status='aborted'` and **does not consume its study ID**; the duplicate
guard at `costaware_panel.py:234` must test for a *completed* study, not for the
mere presence of rows.

This does not hide anything. Fits that produced no out-of-sample result cannot
have been selected on, so they are not trials in the sense the guard exists to
protect. Recording them as `evaluated` was the misleading version; recording
them honestly as `aborted`, or not at all, is the accurate one.

## Decision 2 — the existing 352 rows are left untouched

The mislabelled rows under `xsmom-v16-panel-dual-v4-A-20260909` are **not
edited**. `journal/trials.db` is append-only by convention — the code comment
states "prior study rows never changed" — and an append-only record that is
edited once is no longer append-only.

They are instead **disclosed as phantom** in the trial count of every report
that follows: 352 rows marked `evaluated` that produced no OOS result, from the
2026-09-09 03:08 arm-A attempt.

Note on authorization: Jaeyoung answered "yes" to a question posed as an
either/or. Planning has read that as endorsing the recommendation it made in
the same message — leave untouched and disclose — because doing nothing to the
record is the reversible choice and editing it is not. Recorded here so the
interpretation is visible rather than assumed.

## Also disclosed, unchanged

- `…dual-v3-{A,B,C,D}-20260907`, 352 evaluated rows each, 2026-09-08 22:34-22:37,
  **5 bps only** — a complete execution of the same 16 configurations at a
  single cost level. Untouched, unread, disclosed as a prior trial.
- `…dual-{A,B,C,D}-20260907`, 16 error rows each — the 02:56 refusal.

Distinct configurations across all of these remain **16 per arm**. No new search
breadth has been spent.
