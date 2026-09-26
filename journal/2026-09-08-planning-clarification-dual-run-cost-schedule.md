# Clarification — dual-run cost schedule must cover the inherited criteria

Date: 2026-09-08
Status: SIGNED 2026-09-08 by Jaeyoung ("yes", planning chat), recorded by
planning; he could not sign the file directly. Binding correction to clause 4 of
the dual-run pre-registration: **cost schedule 0/5/10/25 bps**
Corrects: an internal contradiction in
`2026-09-08-xsmom-v16-dual-run-preregistration.md` (clause 4)
Raised by: `[CODEX-A] 2026-09-08 — dual-run cost schedule cannot produce
inherited C2` in `AGENTS.md`. Codex A filed and stopped rather than
substituting a schedule. That was correct.

## The contradiction

The dual-run pre-registration declares in its header that it **inherits
C1/C2/C3 unchanged** and does not restate them. Clause 4 then enumerates the
cost scenarios as "the retained flat 0/5/10 bps scenarios."

The inherited criteria specify cost levels:

- **C1** — selected lambda>0 beats lambda=0 on stitched OOS Sharpe at **10 bps**
- **C2** — selected strategy beats hand 12-2 momentum at **25 bps**

C2 cannot be evaluated at all under a 0/5/10 schedule. The document therefore
requires two things that cannot both hold.

## Resolution

**The inherited criteria govern.** The document's own header declares C1/C2/C3
unchanged; clause 4's purpose was to exclude *per-symbol* costs (A3's fallback
is defective and unamended), not to redefine the cost levels at which the
inherited criteria are evaluated. The enumeration was defective.

Clause 4 reads, corrected:

> All four arms run flat cost scenarios only — no per-symbol cost inputs. The
> schedule is **0/5/10/25 bps**, which is the retained flat set together with
> every level the inherited C1/C2/C3 require. Per-symbol costs remain out of
> scope for this study.

## Why this is a correction and not an amendment

1. It changes nothing about what is tested. The inherited criteria already
   fixed 10 and 25 bps before clause 4 was written; the enumeration simply
   failed to cover them.
2. It resolves the contradiction in the direction the document itself declares
   authoritative.
3. **No arm has been run.** Nothing has been observed, so nothing can be
   contaminated by this repair. Correcting an unsatisfiable pre-registration
   before any result exists is legitimate; the same correction after a result
   would not be.

Point 3 is the load-bearing one. If any arm had run, the correct action would
be to void the run, not to fix the document.

## Planning's error

Clause 4's enumeration was copied from the A3 cost decision's language without
checking it against the inherited criteria. The pre-registration was drafted by
planning and signed on Jaeyoung's word; he had no practical opportunity to
catch it. The defect is planning's.
