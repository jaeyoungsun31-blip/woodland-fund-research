# xsmom-v16 dual run — pre-registration

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung, authorization given verbally in the
planning chat and recorded by planning (he could not sign the file directly).
Countersigned into the record by: Claude (planning). See
`2026-09-08-planning-record-package-signature.md` for the authorization scope.
Governs: the execution of the v16 study on the constituent panel
Inherits, does not restate: `2026-09-07-xsmom-v16-panel-preregistration.md`
(C1/C2/C3, primary metric, promotion gate — those terms are unchanged and are
NOT reproduced here; read that entry)
Depends on: A2 Amendment 2 and the data acceptance standard, both 2026-09-08,
both signed

## Purpose

Answer, by measurement rather than inspection, whether the panel's known and
unknown defects change the study's conclusion.

## The arms — a 2x2, all four or none

Two independent uncertainties, crossed:

| | favourable A2 bound | adverse A2 bound |
|---|---|---|
| **cleared subset** | arm A | arm B |
| **full panel** | arm C | arm D |

- **Data-quality axis.** *Cleared subset* = the symbols passing `STATE.md` §13
  (passed the Tiingo comparison AND carrying no quality or volume flag; 220 as
  measured 2026-09-07). *Full panel* = all 942.
- **A2 axis.** Favourable and adverse bounds per Amendment 2.

**All four arms are run, or none is.** No arm may be run alone, first, or
selectively. Results are reported together in one artifact.

## Why 2x2 rather than 2

Crossing the axes separates the two uncertainties. If the arms agree across the
A2 axis but diverge across the quality axis, the problem is security identity
and data defects. If they agree across quality but diverge across A2, the
problem is delisting treatment and no amount of further cleaning helps. If they
diverge across both, the panel does not support a conclusion. Each outcome
points at a different next action; a single paired run cannot distinguish them.

## Declared before running

1. **Panel window: 1999-01-06 to 2026-06-30.** Declared here because it was
   never declared in the v16 pre-registration (a standing open item). It is not
   varied afterward.
2. The cleared subset is frozen at its 2026-09-07 membership and recorded by
   symbol list in the run artifact. It is not re-derived after seeing results.
3. The 3 symbol-years quarantined pending A2 Amendment 1 are excluded from all
   four arms and reported.
4. Per-symbol cost inputs are **not** used; A3's fallback rule is defective
   (`STATE.md` §7.3) and unamended. All four arms run the retained flat
   0/5/10 bps scenarios, reported alongside as the existing protocol requires.
   The measured-cost scenario is out of scope for this study.
5. The ETF baseline reads the frozen snapshot
   `data/snapshots/etf-4c6a36b8.../`. The ten outstanding anchor failures must
   be ruled on before this study runs; if the ruling is to accept under a
   declared tolerance, that tolerance is cited in the run artifact.

## Outcomes and what each means

- **All four arms pass the inherited gate, and agree** (sign + overlapping CIs,
  per the acceptance standard): the result is admissible. Defects are disclosed,
  not disqualifying.
- **All four fail:** a negative result on the constituent panel. This is a real
  finding and is reported as one. It is not a reason to clean further and rerun.
- **Arms disagree:** *that is the finding.* No promotion. The disagreeing axis
  names the next work item. Report it and stop.

No outcome licenses re-running a subset, adjusting the cleared-subset
definition, or amending the bounds after the fact.

## Termination

On completion of all four arms and evaluation of the gate, the data question
for v16 is CLOSED under the acceptance standard's stopping rule. Later
discoveries go to the defect register and the next study.
