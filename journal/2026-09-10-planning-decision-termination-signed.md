# 2026-09-10 — planning decision: the termination criterion is signed

Status: **SIGNED**, 2026-09-10, by Jaeyoung in planning.

Resolves the suspension opened by
`journal/2026-09-03-planning-finding-rf-zero-sharpe-bias.md`, which asked
planning to decide what the corrected evidence means for
`journal/2026-09-03-planning-decision-termination-and-v16-withdrawal.md`.
That question stood unanswered for seven days. Neither prior entry is edited.

## What the suspension was about

The 2026-09-03 termination decision took effect on T1: `sleeve-v17-overlay`
failed C1. The same day, a finding established that every v15 and v17 pass/fail
criterion had been evaluated on rf=0 Sharpe over a window whose mean annualized
real risk-free rate is 3.0761%, biasing every comparison toward the cash-heavy
incumbent by roughly twenty-one times the measured effect.

The recomputation in `journal/2026-09-03-v15-v17-rf-sharpe-recomputation.md`
found, on excess returns with the pre-registered bootstrap unchanged:

- v17 C1 changes from failed to **met**;
- v15's full-history comparison versus 60/40 flips negative to **positive** at
  10 bps;
- **post-1980 remains ambiguous**: zero of four holding frequencies had a
  positive excess-return bootstrap lower bound versus either 60/40 or MKT at
  0, 5, 10, 25 or 50 bps;
- 1932–1979: all four frequencies cleared both references at 0, 5 and 10 bps;
  two cleared both at 25 bps; one at 50 bps.

T1's triggering condition was therefore invalidated. The research phase has
been running since on a criterion whose basis no longer held, and during that
period `xsmom-v16` — withdrawn before execution on 2026-09-03 — was revived
and run twice.

## Decision

**The termination criterion is signed, on a corrected basis. T1 is not the
reason.**

The reason is the era result, now established three times on unrelated data by
different methods:

1. `xsmom-v15-holding`, Fama-French prior-12-2 deciles, 1932–2026, 24,434 OOS
   bars, rf=0 basis: no 1980–2026 interval versus equal-weight-ten excluded
   zero at any registered cost or frequency.
2. The same series recomputed on excess returns: no 1980–2026 interval
   excluded zero versus either 60/40 or MKT, at any registered cost.
3. `xsmom-v16-universe-control`, EODHD survivorship-free constituent panel,
   2005-01-07 to 2026-06-30, 5,234 OOS bars, 915 defect-excluded symbols:
   G1 false (DSR 0.0075 against a 0.95 threshold) and G2 false (penalized
   minus naive momentum -0.212, CI [-0.413, -0.026], p = 0.033).

The measured cross-sectional momentum edge is supported by the pre-1980 half
of the sample and is not established post-1980. The tradeable window is
post-1980. That is a sufficient and better-evidenced closure than "the last
study failed."

T2 continues to bind. Any future study must name the specific quantity it
expects to move that prior studies did not. Planning can name none.

## What is not claimed

- Not a claim that cross-sectional momentum is false. It is not established
  post-1980 in the examined evidence.
- Not a claim of causation for the era pattern.
- Not a promotion. Nothing is promoted. The 60/40 control's tail advantage in
  CVaR95, CVaR99, maximum drawdown and underwater duration is unchanged and
  does not depend on the Sharpe convention.
- The identification gap is now **closed**, not open: v15's model-implied
  holding paths were the reason to acquire constituent-level data, and
  `xsmom-v16-universe-control` supplies the observed counterpart. It did not
  reverse the era finding.

## Remaining work

`writeup/research-report.md`, then Phase 3, then Phase 4. DESIGN.md §11
applies: "The loop (Phase 3) is the point of the project."

The write-up must carry the era result as its finding, the survivorship
methodology result as its second finding, and the full disclosure block.
