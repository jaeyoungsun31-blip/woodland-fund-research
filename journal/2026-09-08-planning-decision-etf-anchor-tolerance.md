# ETF anchor ruling — accept under a declared tolerance of 1e-3

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("yes", planning chat), recorded by
planning; he could not sign the file directly. Planning recommended and did NOT
self-authorize — see "Conflict" below. Declared reproduction tolerance on Sharpe
anchors: **1e-3**.
Evidence: `journal/2026-09-07-phase3-etf-current-store-anchor-drift.md`,
`reports/anchor-measurement-2026-09-07/`
Required by: clause 5 of `2026-09-08-xsmom-v16-dual-run-preregistration.md`

## The question

Yahoo restated adjusted close backward on 2026-09-07, changing the ETF snapshot
hash. Measured against the replacement anchors, 43 of 53 pass and 10 fail. The
frozen snapshot `data/snapshots/etf-4c6a36b8.../` is the configured research
store. Either the ten failures are accepted under a declared tolerance, or the
anchors are regenerated.

## The evidence

```
anchors checked                  53
pass                             43
fail                             10   (every one a Sharpe)
largest absolute delta     0.000585110099   (v6 multi-asset; v14 raw-v6)
smallest absolute delta    0.000078379085   (v14 S2 min-variance)
9 of 10 fail only at 6-decimal precision (tolerance 5e-7)
1 of 10 fails at 3-decimal precision (tolerance 5e-4, delta 5.85e-4)
```

Relative magnitude: 5.85e-4 against anchors near 0.79 is a change of roughly
0.07%. This project's own inference work measured Sharpe confidence intervals of
about +/-0.4 over 21.8 years. The drift is therefore about **three orders of
magnitude below the precision at which this project can distinguish anything.**

No study conclusion changes. These are precision-tolerance failures, not result
changes.

## Recommendation

**Accept, with a declared reproduction tolerance of 1e-3 on Sharpe anchors.**

1e-3 covers all ten failures with roughly 1.7x headroom over the largest delta,
and remains far tighter than any effect this project could claim. The tolerance
is declared here, cited in every run artifact that relies on it, and is not
adjusted after any result is seen.

This ruling accepts a **reproduction tolerance**. It does not ratify the
restated snapshot as correct, does not re-pin, and does not resolve whether
`config/etf-anchors-2026-09-07.json` already constituted an acceptance. Those
remain open.

## Why not re-anchor

Re-anchoring rewrites the reference values to match the current store, which
makes reproduction trivially pass and destroys the ability to detect the next
restatement. The guard is worth more than the ten failures cost. A declared
tolerance keeps the guard live and bounds what it will forgive.

## Conflict, stated plainly

Planning drafted the acceptance package that this ruling unblocks, and planning
benefits from it clearing. That is a reason for planning to recommend and not to
authorize. The mechanical refusal Codex A built into the harness — no arm runs
without a recorded ruling — is deliberately not satisfiable by planning alone.

Jaeyoung's authorization, recorded as with the 2026-09-08 package, converts this
to SIGNED.
