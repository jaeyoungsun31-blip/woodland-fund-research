# Amendment 1 — xsmom-v16 universe control

Amends: `journal/2026-09-09-planning-preregistration-universe-control.md`
(SIGNED 2026-09-09, committed f6a2cf2). That entry is not edited.

Status: **SIGNED**, 2026-09-09. Jaeyoung selected the G2 cost level in the
planning chat; planning drafted both corrections.

## Legitimacy of amending after signature

`journal/trials.db` holds **zero rows** under
`xsmom-v16-universe-control-20260909`. No fold, no fit, no result exists.
Neither correction below can have been chosen with knowledge of an outcome.
This window closes the moment the study runs; after that, both items would
require a new study rather than an amendment.

## Correction 1 — G2 declares no cost level

Raised by Codex A, which refused execution rather than infer one, and declined
to inherit the value from the former dual-run C2 convention. Both refusals were
correct.

The defect is planning's. §4 declares costs 0/5/10/25 bps as a **reporting**
dimension. §5 then states G2 without naming which of those four levels the gate
is evaluated at. As written, whoever executes the study chooses the cost level
after seeing four answers. That is the failure a pre-registration exists to
prevent, inside a signed pre-registration.

Inheriting the old convention would also have been wrong: `costaware_panel`
computes C2 symmetrically at 25/25, while `dual_panel`'s reporting block pairs
`penalized-10-returns.csv` against `momentum-25-returns.csv`. Two different C2
definitions exist in the codebase. Neither is adopted here by default.

**G2 is evaluated at 25 bps on both legs.** The lower bound of the 95%
bootstrap CI on `penalized@25 - momentum@25` must be strictly above zero.

0, 5 and 10 bps are reported and are **explicitly non-gating**. A pass at a
lower cost level with a failure at 25 is a failure. This is recorded now so
that outcome cannot be re-litigated later.

Rationale: 25 bps is the harshest declared level, so a pass cannot be
attributed to optimism and a failure cannot be re-argued at a friendlier
number. It matches the momentum leg the engine already used. Committing in
advance to the strictest available option is the form of this commitment that
cannot be called cherry-picking.

Acknowledged cost of the choice: a real but marginal effect will fail at 25 bps
and will not be distinguishable from no effect at all. Accepted.

## Correction 2 — §5's stated reason for deleting G3 is false

§5 states that v16's C3 required an independent era, that no independent era
exists in a panel beginning 1999-01-06, and that C3 could not pass under any
outcome.

That is wrong. `woodland/harness/costaware_panel.py:340` implements C3 as:

```
C3 = c1.ci_low > 0 and c2.ci_low > 0
```

C3 is a conjunction of the C1 and C2 confidence-interval bounds. It has nothing
to do with eras and it was achievable. It failed in the dual run because C1's
lower bound was -0.0222, not because it was impossible. The `C3_note` string
"Same OOS dates; entirely post1980, no independent era check" is boilerplate
that never described the implementation.

Planning read the note rather than the code. This is the project's founding
failure mode — asserting from a metadata field without opening the
implementation — committed inside the document written to prevent it.

**The deletion of G3 stands; its reason is replaced.** G3 is deleted because
C3 as implemented is redundant: it restates `C1 and C2` and adds no independent
criterion. §5's era-feasibility argument is withdrawn and must not be cited.

No claim about C3's feasibility may be made from `C3_note` in any future entry.

## Effect on the runner

`woodland/harness/universe_control.py` sets `G2_COST_BPS = None` and refuses.
That constant becomes `25.0` once this amendment is committed. Nothing else in
the signed design changes: universe, study ID, grid of 16, `G1_N_TRIALS = 80`,
the DSR threshold of 0.95, and §7's pre-declared interpretation all stand.

- Signed by: Jaeyoung
- Date: 2026-09-09
