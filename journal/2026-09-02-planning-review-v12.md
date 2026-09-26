# 2026-09-02 — Planning review of trend-v12-execution

Append-only. Interpretation and decisions on the factual results in
`journal/2026-09-02-trend-v12-execution-results.md`. Accepts that entry as
reported; adds nothing to its numbers.

## What v12 established

**1. Buffering works, and it is the first execution improvement this project
has landed.** At 10 bps, 48 of 216 cells met all four pre-registered economic
criteria: turnover cut 46-68% (median 51.7%) while the Sharpe difference ran
+0.018 to +0.092 (median +0.065), with drawdowns improved 3.6-6.7pp and the
5th-percentile day improved 5-9 bps. Roughly half the trading, slightly better
outcomes.

**2. It is non-inferiority, not superiority.** No paired 95% interval excluded
zero in either direction. The correct claim is "we can trade half as much
without losing anything measurable", never "buffering improves the strategy".

**3. The mechanism is partial adjustment, and only at half speed.** Success
counts by adjustment were 1.00/0.50/0.33 = 0/48/0. Moving halfway toward the
target each rebalance is what works; moving all the way or only a third does
not. This is the Garleanu-Pedersen aim-portfolio result appearing in our own
data, and it is the strongest reason to treat the finding as mechanism rather
than coincidence.

**4. Tranching contributed nothing.** Tranches 1/4 = 48/0. Calendar-luck
diversification, which planning proposed twice and pushed for as a "free"
improvement, produced zero passing cells. Recorded as a planning idea that
failed on contact with data.

**5. The result is regime-dependent, and this is the limiting caveat.**
Leave-one-decade-out: removing the 2000s leaves 72 cells (median +0.087);
removing the 2020s leaves 57 (median +0.074); **removing the 2010s leaves ZERO
cells and a median of −0.090.** The full-window finding materially depends on
one decade. It is not a stable law.

## Decision: adopt partial adjustment at 0.50 as the default implementation

Adopted for all future v6-family work, effective now.

**Selected on mechanism, not on performance.** 48 cells passed; choosing the
best of them would be a selection from a surface pre-registered as carrying
none. Instead the choice is the single parameter the surface shows to be
load-bearing — adjustment = 0.50 — with band, delay and miss rate left at
their neutral settings. Any future claim that quotes a specific passing cell's
numbers must carry the full 216-config breadth in its trial count.

Rationale for adopting despite non-inferiority: halving turnover at no
measurable cost is worth having on its own terms, and it reduces the project's
exposure to the cost assumptions that v12 showed to be its weakest link. This
is an efficiency decision, not an edge claim.

## What v12 does NOT change

The frontier stands: v6 trails the vol-targeted 60/40 benchmark even at zero
hypothetical turnover. **Buffering makes the strategy cheaper to run; it does
not give it an edge it lacks.** Halving the turnover of a strategy with no
gross advantage does not create one.

The strategic direction set before v12 therefore stands unchanged:
cross-sectional equity momentum (`xsmom-v13-confirm`) is the project's primary
line of research, and the trend family is in maintenance.

## Standing requirement, reaffirmed

Any future proposal to increase trading frequency must first demonstrate a
gross edge at zero cost against the vol-targeted benchmark. v12 confirms none
currently exists in the trend family.
