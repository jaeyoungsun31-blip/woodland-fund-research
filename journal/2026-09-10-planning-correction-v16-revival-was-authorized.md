# 2026-09-10 — correction: v16's revival was authorized, not irregular

Corrects: `journal/2026-09-10-planning-decision-termination-signed.md`.
That entry is not edited.

The termination entry states that during the suspension "`xsmom-v16` —
withdrawn before execution on 2026-09-03 — was revived and run twice." The
sentence is factually true and its implication is not. It was written before
planning had read `2026-09-06-planning-decision-revive-v16-on-constituent-data`.

That entry reverses the withdrawal explicitly, satisfies T2 on its face by
naming two quantities external to the hypothesis — the identification gap
closed by constituent-level delisting-inclusive data, and cost measured per
symbol rather than assumed — and holds the pre-registration fixed: the six
features, the estimator, the 16-cell grid, and C1/C2/C3 all unchanged, with
the explicit warning that altering any of them "would convert a
pre-registered study into a search dressed in a pre-registration's clothes."

It also carried planning's prediction forward unchanged: `[Likely]` C2 fails,
`[Likely]` C3 fails, and "better data does not make momentum work; it makes
the answer trustworthy." Both predictions held.

The revival was correct. What was irregular is narrower and remains true: the
suspension opened on 2026-09-03 was never resolved, so the project ran for
seven days under a termination criterion whose triggering condition the rf=0
correction had already invalidated.

## Separately — two amendments from that entry were never implemented

Recorded here because the same reading found them; see
`journal/FINDINGS-INDEX.md` §3 for detail.

- **A4, the membership leakage test, does not exist.** The amendment called
  the perturbation tests "preconditions of execution, not deliverables of it."
  `tests/test_no_lookahead.py` covers the return side only.
- **A3, per-symbol costs, is not wired.** Both runs used the flat schedule.

Neither undermines the negative findings: lookahead and understated costs both
bias results upward, and cannot cause a working strategy to fail. Both bear on
any positive figure from these runs, including the naive-momentum baseline's
0.4545 Sharpe, which is already withdrawn from citation on other grounds.
