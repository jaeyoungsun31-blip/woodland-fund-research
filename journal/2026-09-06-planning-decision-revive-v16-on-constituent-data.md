# 2026-09-06 — planning decision: revive xsmom-v16 on constituent-level data

Append-only. Reverses the withdrawal in
`2026-09-03-planning-decision-termination-and-v16-withdrawal.md` and amends
`2026-09-03-xsmom-v16-costaware-preregistration.md`. Requires sign-off.

## Why this is not a re-opened tactic

T2 requires a proposal to name the quantity it moves that prior studies did
not. This names two, and both are external to the hypothesis:

1. **The identification gap is closed.** Every prior stock-level result —
   v11, v13, v15 — rested on Ken French decile portfolios: frictionless
   academic constructs with no constituents, no delistings, and no tradeable
   analogue. Jaeyoung has purchased EODHD coverage including delisted
   companies, verified present. v15's and v17's standing limitation, that
   every path and turnover figure is model-implied rather than observed, is
   removable for the first time.
2. **Cost is measured, not assumed, and now per-symbol**
   (`2026-09-05-planning-decision-per-symbol-cost-model.md`). The 25-50 bps
   figure that killed v13 was never observed; SPY and IEF measured 0.130 and
   0.542 bps.

The withdrawal stands as history and is not edited. It was correct when
written: planning predicted failure and had no constituent data. The second
condition has changed.

## What does NOT change

**The six features stay exactly as pre-registered**, with the same
definitions, the same cross-sectional z-scoring and +/-3 winsorisation. The
estimator stays the closed-form smoothness-penalised ridge. The 16-cell grid
stays as declared and is not widened. The controls stay: the `lambda = 0`
twin and hand-specified 12-2 momentum, with beating the *rule* as the bar
rather than beating equal-weight. C1, C2 and C3 stay as written, C3 primary.

Changing any of these while adding better data would convert a
pre-registered study into a search dressed in a pre-registration's clothes.

## Amendments

**A1 — universe.** The 49 French industry portfolios are replaced by
**point-in-time index membership** from EODHD. The panel at date `t` contains
exactly the constituents as of `t`: a name enters when it entered the index
and leaves when it left, including by delisting. The index and the history
window are declared in the amended pre-registration before the first fit and
are not varied afterwards.

**A2 — delisting return convention, declared before any study.** Prices that
simply stop are not sufficient. A company acquired at a premium and one that
went to zero produce identical truncated price series, and treating both as
"series ends" biases results **upward** while appearing rigorous — a dataset
that keeps good exits and drops bankruptcies is worse than one that drops
both. The convention must state the terminal return applied at delisting, its
source, and what is done when the provider supplies none. Absent a documented
provider value, the conservative default is a total loss on the final
position, and the count of names using each treatment is reported in every
result.

**A3 — costs.** Per-symbol under the 2026-09-05 decision, with the flat
0/5/10 scenarios retained and reported alongside. Unmeasured symbols take the
highest measured per-symbol value, and the measured/fallback split is
reported. Large and small caps differ by an order of magnitude in spread, and
this study is the first in the project able to express that.

**A4 — a second leakage test.** The existing panel perturbation test covers
the return side. Membership is a new leakage surface and gets its own:
**altering the constituent list after a cutoff must leave every panel row at
or before that cutoff bit-identical.** A membership list timestamped by
announcement rather than effective date is lookahead, and it is invisible in
results.

## Standing caution

Better data raises the stakes of every prior discipline rather than relaxing
any of it. A survivorship-clean panel with a lookahead-contaminated
membership list will produce beautiful, entirely false results, and nothing
in the output will indicate the problem. The two perturbation tests are
preconditions of execution, not deliverables of it.

Planning's prediction from the original pre-registration is unchanged and
remains on the record: `[Likely]` C2 fails and `[Likely]` C3 fails. Better
data does not make momentum work; it makes the answer trustworthy.
