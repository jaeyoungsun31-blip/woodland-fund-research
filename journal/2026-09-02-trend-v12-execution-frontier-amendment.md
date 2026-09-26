# 2026-09-02 — trend-v12-execution: maximum-viable-turnover amendment (BINDING)

Append-only planning amendment. Written before the turnover frontier is
computed. It adds one diagnostic output to the already pre-registered v12
study and does not alter the signal, execution surface, success criteria, or
trial accounting.

## Rationale

Planning needs to know whether a higher-frequency strategy is economically
viable at all before designing one. Short-horizon signals can survive in gross
returns and disappear after implementation costs. The cost frontier is
therefore a prerequisite for a later frequency decision, not an after-the-fact
adjustment to a tested strategy.

## Fixed comparison

Use the same stitched v6 multi-asset ensemble, OOS window, real-cash return,
and suspect-date treatment as the main v12 run. Start from v6 returns at zero
transaction cost. The comparator is the standing vol-targeted 60/40: monthly
60% SPY / 40% IEF targets passed through the fixed 63-trading-day, 10% annual
volatility target with scale capped at 1.0 and no leverage. Rebuild the
comparator on the identical OOS calendar and charge its observed turnover at
each cost level.

For hypothetical annual cost-engine turnover `T` and one-way cost `c` bps,
define the v6 net series by subtracting a constant daily implementation drag:

`r_net(T, c) = r_v6_gross - T * c / 10,000 / 252`.

This is a transparent linear-capacity diagnostic. It holds the gross signal
distribution fixed, assumes no nonlinear market impact, and does not claim
that changing signal frequency would leave gross returns unchanged.

At each `c in {5, 10, 25, 50}` bps, solve analytically for the turnover where
v6 rf=0 net Sharpe equals the net rf=0 Sharpe of the vol-targeted 60/40 at that
same cost. If v6 already trails at `T=0`, report maximum viable turnover as
**none (zero turnover already fails)** rather than presenting a negative
turnover. If the equality is positive, report it in annual cost-engine
turnover units and verify it by direct substitution.

## Frontier and holding-period interpretation

Print the four break-even points and save a Matplotlib frontier plot under
`reports/`, with annual turnover on the horizontal axis, cost per trade on the
vertical axis, net-Sharpe advantage as the field, and the zero-advantage
contour drawn wherever it exists. Mark the four required cost levels and the
observed v6 turnover of 5.153x/year.

Translate positive turnover capacity into an equivalent holding interval.
Because this project's cost engine uses `sum(abs(delta weight))`, a complete
rotation from one fully invested asset to another is 2.0 turnover units. A
full portfolio rotation every month, week, or day therefore corresponds to
approximately 24x, 104x, or 504x annual cost-engine turnover. Also report the
one-leg cash-transition bound (`252/T` trading days) so the convention is not
hidden. State plainly whether the frontier funds monthly, weekly, or shorter
full rotations at realistic retail costs. Decision frequency is not itself
turnover, so this statement is an affordability bound, not evidence that an
untested higher-frequency signal has gross edge.

The turnover grid used to draw the fixed analytic surface is presentation,
not a parameter search. No execution cell is selected, no new strategy is
evaluated, and no additional ledger configuration is created. The frontier is
journaled with the rest of v12, then the study stops.
