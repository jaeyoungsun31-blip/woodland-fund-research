# 2026-09-03 — planning decision: v15 stale-cohort approximation

Append-only resolution of Q11 in `CLAUDE.md`, recorded before
`xsmom-v15-holding` is pre-registered or run.

The instruction to continue after the identification gap was surfaced is
treated as approval of Q11 option 2: use the existing Gaussian latent-rank
model to construct a wholly model-implied stale-cohort approximation. No
constituent data is added and the mechanically available alternative of merely
changing weights among daily-refreshed French decile indices remains rejected
as a mislabeled holding-period test.

At a scheduled formation close, the latent cohort is the upper 30% of ranks.
Its first following return uses equal probability mass in the three current
top deciles. On subsequent days until the next formation, propagate that
cohort's mass across all ten current deciles under the v13 Gaussian AR(1) rank
model with daily `rho = 229/230`, and apply those weights to the same day's
observed French decile returns. At the next formation close, refresh to the
current upper 30% for the following return. Turnover at refresh is twice the
model-implied fraction of the old cohort outside the current upper 30%.

This is not an observed stock portfolio. Both the slower-holding gross return
path and internal turnover are conditional on the Gaussian transition and
exchangeability assumptions. The monthly approximation will not reproduce
v13's daily-reconstituted top-three return path and must not be compared as if
the only difference were cost. Its value is a fixed sensitivity analysis of
the specific holding-period question, not evidence of exact tradeability.

