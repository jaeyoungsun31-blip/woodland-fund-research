# Phase 1: S&P 500 deletion rebound feasibility probe

The reproducible calculation is `phase1.py`. It reads the SHA-pinned constituent
membership mask and local EODHD adjusted closes, then writes only into this
directory. The complete event census, annual counts, price-coverage failures,
event-level abnormal returns, and clustered summary tables are in the adjacent
CSV files. `summary.json` records the input hash and counts.

The membership mask is **not a complete historical S&P 500 roster**: it holds
resolved symbols only (437 members at the 2012-04-04 EODHD floor), and its own
source README says 213 constituent symbols were refused. Accordingly, the 263
transitions found here are all exits *observable in that mask* since the floor,
not all real index deletions. There are 218 mechanically classified discretionary
exits (a positive EODHD adjusted close exists on or after the fifth trading
session after the last-member date), and 45 mechanically classified acquisitions
or delistings. This price-continuation test cannot establish the actual corporate
reason for deletion.

Of 218 discretionary exits, 155 have a positive adjusted close on every SPY/IWM
session from 60 sessions before through 60 sessions after the first day out.
The other 63 are named, with the first missing date, in `coverage.csv`.
Day 0 is the first day out of the index, the effective date in this analysis.
Announcement dates are unavailable, so the pre-exit window cannot be anchored
to announcements. For each session, abnormal return is the security's adjusted
close-to-close return minus the benchmark's adjusted close-to-close return; CAR
is the sum over the specified window. The pre-window includes returns dated
−20 through −1; the post windows include returns dated 0 through +5, +1
through +20, and +1 through +60. Costs subtract a fixed 10 or 25 basis points
round trip from the +1 through +20 CAR. Means, medians, and positive shares
weight deletions equally. The 95% percentile bootstrap resamples effective-date
clusters (10,000 draws, seed 20260923), keeping same-date deletions together.

**Data-quality block.** The constituent-panel README explicitly says its
adjusted-price panel should not be backtested because of contaminated source
prices. Seven of the 155 covered deletions are in its quality-flag list: GR,
CBE, RRD, X, GNW, ARNC, and JWN. CBE's local EODHD adjusted close falls
99.91% between 2012-11-30 and 2012-12-03; the mechanical continuation
rule still labels it discretionary, and its +1 to +20 SPY-relative CAR is
−99.13%. Excluding just CBE changes the all-period +1 to +20 SPY mean from
−0.30% to +0.34%; excluding all seven flagged names changes it to +0.16%.
These exclusions are diagnostics, **not** replacement estimates. The tables
describe the available files, not a validated trading result or evidence of an
edge. No significance claim is made.
