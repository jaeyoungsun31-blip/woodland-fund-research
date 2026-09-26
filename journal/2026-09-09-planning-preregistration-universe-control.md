# Pre-registration — xsmom-v16 universe control

Status: **SIGNED**, 2026-09-09.

## 1. Question under test

Does xsmom-v16 clear a positive gate on a universe that is both
survivorship-free and free of identified price defects?

This condition has never been run. It is not a re-run of v16 and it does not
reopen v16's closed data question.

## 2. Why this study exists

`journal/2026-09-09-planning-ruling-v16-dual-run-closed.md` closed v16. That
closure stands. `journal/2026-09-09-planning-correction-cleared-subset-is-survivorship-biased.md`
corrects the conclusion drawn from it: neither arm pair tested the hypothesis.

- Arms A/B: no cells above 100% daily, but the cleared subset excludes 469
  symbols for `no_tiingo_series` — second-vendor coverage, not EODHD quality.
  65.7% of those left the index before 2026 against 20.0% of the cleared 220.
  Median 149 names ranked per day.
- Arms C/D: correct universe width (median 439) but 348 cells above 100% daily
  across 27 symbols. A series printing +23,678% is always the top-ranked
  momentum name, so the ranking mechanism itself is corrupted, not merely the
  returns.

## 3. Universe — frozen, not re-derived

`reports/defect-excluded-universe-2026-09-09/universe.csv`: the 942
favourable-panel columns minus the 27 defect symbols enumerated in
`journal/defect-register.md`. 915 included.

Verified by planning against the panel before signing:

- panel columns matched: 915
- cells with `abs(return) > 1.0`: **0**; max +0.987, min -0.995
- daily `membership_names` min / median / max: 327 / 425 / 501
- last priced bar before 2026-01-01: 403 / 915 = 44.04%

Codex reports 328 / 425 / 499 and 405 / 915 = 44.26% using last membership date
rather than last priced bar. Both measures are recorded; neither is corrected to
the other. The runner must verify the manifest's sha256 on read and refuse on
mismatch, as the cleared subset does.

## 4. Design — one arm

Single arm. The A2 axis is **not** repeated: the dual run measured it at -0.071
(cleared) and -0.032 (full) with no verdict change in any arm. The favourable
bound is used. Dropping the axis also removes the agreement criterion and with
it the null-sign-concordance defect registered on 2026-09-09.

- Study ID: `xsmom-v16-universe-control-20260909`
- Panel: the 915-symbol favourable panel above
- Membership mask and short-gap fill: as signed 2026-09-08, unchanged
- Cost schedule: 0, 5, 10, 25 bps — reporting dimension, not a search dimension
- Walk-forward splits: unchanged from v16
- Configuration grid: the existing 16. **The grid is closed.** Adding a
  configuration voids this pre-registration and requires a new one.

## 5. Gate — positive and achievable

**G1.** Deflated Sharpe > 0.95, with `n_trials = 80` declared here, before the
run. 80 = 16 configurations x 5 distinct data conditions examined across the
whole v16 program (A, B, C, D, and this one). Cross-universe selection is
penalized rather than ignored.

**G2.** The penalized model beats the naive momentum baseline with the **lower
bound of the 95% bootstrap CI strictly above zero.** A point-estimate sign is
not sufficient and is not evidence.

**G3 is deleted.** v16's C3 required an independent era. The panel begins
1999-01-06; no independent era exists inside it. C3 could not pass under any
outcome and v16 was therefore at most two-for-three before it started. No
criterion enters this study without a stated feasibility check.

## 6. Trial accounting defect carried forward

Every v16 arm recorded `n_trials: 352` in its DSR. That is 22 folds x 16
configurations — fold-level evaluations counted as trials. DSR's N is the number
of candidate configurations searched, not the number of fold evaluations.

This made v16's gate harder, not easier: at n=64 arm A's threshold falls from
0.857 to approximately 0.72, still far above its achieved 0.407. **Correcting it
does not rescue v16.** Recorded so the correction cannot later be mistaken for a
reason to reopen a closed study.

## 7. Pre-declared interpretation

Declared before the run, binding on both outcomes.

**If the gate fails:** xsmom-v16 is dead on a genuinely survivorship-free,
defect-free universe. The next hypothesis inherits this as its baseline. No
further universe variation is run for v16.

**If the gate passes:** the finding is that the cleared-subset screening
methodology suppressed the result, not that the strategy was rescued by better
data. The second-vendor-availability screen is retired and the finding is
reported as a methodology result.

**This is the only universe re-test xsmom-v16 receives.** Either outcome closes
the question permanently. A third universe requires a new hypothesis, not a new
panel.

## 8. Disclosure carried forward

213 refused constituents / 1,574 refused symbol-years; A2 coverage 452 exits
(8 treated, 441 unclassified, 3 quarantined); independent cross-check 430/942,
delisted-skewed; 45 filled short-gap cells; 27 defect symbols excluded by
construction and enumerated in the register; prior v16 trials as recorded in
`journal/trials.db` under 13 study namespaces, 16 distinct config hashes.

## 9. Signature

Planning recommends. Execution requires Jaeyoung's signature below.

- Signed by: Jaeyoung
- Date: 2026-09-09
