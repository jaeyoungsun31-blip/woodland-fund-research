# The second source finds what a single file cannot: MO, and 23 others

Date: 2026-09-07
Status: partial coverage (204 of 947 compared), run continuing; nothing corrected
Artifacts: `reports/security-resolver/2026-09-07-tiingo-crosscheck/`
Code: `scripts/run_tiingo_panel_crosscheck.py`, using `crosscheck_sources`
Related: `2026-09-07-phase3-symc-missed-split.md`

`crosscheck_sources` was written on 2026-09-01 as the design for exactly this
and had never been run on the constituent store. Running it changes what we know
about the panel.

## Why it had to be run

The duplicate-locator census finds a missed corporate action only where a
duplicate file happens to exist. `SYMC` was caught because EODHD also ships
`GEN` and `NLOK`; had it not, a two-for-one split recorded as a 48.6% loss would
have entered the panel with nothing to contradict it.

**`MO` is the proof that the luck runs out.** On 2008-03-31 the `MO` file's raw
close falls 69.93%, its adjusted close falls 69.93%, and `adjusted_close/close`
is flat at 0.320104 on both sides of the day. Tiingo puts the day at −1.56%.
That is the SYMC signature exactly — an event carried into the adjusted column
unapplied — in a name with **28 years of membership**, and the store holds no
second file for Altria, so no amount of duplicate-locator work would ever have
reached it.

## Coverage, and the refusal that makes it trustworthy

204 symbols compared of 220 attempted, ordered by membership-years. 10 candidate
tickers were rejected because they resolve to a different company, 6 have no
Tiingo series, and **0 symbols were recorded as agreeing because of a throttle**.

That last count is the point. The vendor caps at roughly 100 symbols an hour and
says so in prose — "You have run over your hourly request allocation" — which an
earlier version of the adjudication script read as "no such ticker" and cached.
A throttled symbol is recorded `not_attempted`; the run sleeps and retries. The
same guard rejects recycled tickers on price before their returns are used.

## Result

**140 of 204 compared symbols — 68.6% — carry at least one day where the two
vendors' adjusted returns differ by more than the 2% fail tolerance.**

Failing-day counts are a poor guide to damage, though. Most disagreements
reverse within days: 89 of the 140 move a constituent's cumulative in-window
contribution by a percentage point or less. 51 move it by more, 21 by more than
10 pp, and 5 by more than 50 pp. Failing days cluster on 1999–2003 — 263 of 521.

The five largest: `WMB` +318.57 pp, `MO` −77.07 pp, `MSI` +74.30 pp, `USB`
−68.27 pp, `F` +54.70 pp.

## A disagreement names no culprit; our own factor does

Both vendors are fallible and the comparison cannot say which is wrong. Our
adjustment factor can, on the days that matter. Flat across a large move means
our file applied nothing; stepping means it did. Over all 521 failing days:

| | days |
|---|---:|
| our factor flat across a >10% move — **we missed an event** | 37 |
| our factor steps — we applied one the other source did not | 51 |
| small move, flat factor — an ordinary price disagreement | 433 |

Direction genuinely runs both ways. `HPQ` on 2000-06-05 and `USB` on 1999-04-16
both show our factor stepping while Tiingo reports the raw move — there the
second source is the weaker one. `WMB` on 2002-10-30 is a third shape again: our
adjusted series rises 51.58% on a day the raw price fell 3.20%, a *spurious*
adjustment rather than a missing one.

**24 of the 204 compared symbols carry at least one day where our factor is flat
across a move above 10%**: A, AFL, BSX, CI, CMA, CMCSA, COF, EFX, FDX, FITB,
GLW, HES, HIG, IPG, KEY, MO, MU, NKE, PCG, RF, SCHW, SPG, VMC, WMB.

That is 11.8% of the covered set. It should **not** be extrapolated to the
remaining 743: coverage was ordered by membership-years, so these are the
longest-lived names and have the most opportunities to have had an event at all.

## The single-source screen is not a substitute, and the gap is measured

`check_missed_events`, added the same day, screens the same defect from inside
one file. Against the 21 symbols whose cumulative gap exceeds 10 pp it flags
**11**, and names the same day for **2**.

It cannot do better in principle. The screen needs a large adjusted move with a
flat factor, so it is blind wherever the disagreement is large but our own
adjusted return is small — `HPQ`'s worst day is a 24-point disagreement in which
our series moves +8.44%, under any usable threshold. **Roughly half the worst
defects are invisible from inside a single file.** A second source is not a
refinement of the screen; it is the only instrument that sees this class.

## What this does to the panel

The panel built the same day already carries a blocking finding — 67 symbols
whose broken raw series give the equal-weighted cross-sectional mean a 434%
annualised volatility. This is a second, independent one, and it does not
overlap: `MO`, `WMB` and the rest are not broken files, they are well-formed
series with a wrong adjustment on a handful of days.

Neither finding is corrected here. No price was changed, no bar synthesised, no
approval or A2 treatment applied, and no resolver status or locator preference
written. The only network access was read-only cross-check requests with the key
in the authorization header.

## Owed

Coverage of the remaining 743 symbols, at roughly 100 an hour. The run is
resumable — the response cache means a re-run covers only what is missing — and
the count of symbols whose factor is flat across a large move is the number that
should be carried forward, not the 68.6% disagreement rate.
