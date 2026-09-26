# 2026-09-02 — trend-v8-blend pre-registration amendment 1 (BINDING)

Append-only. Written before any v8 market return is computed. This clarifies a
cross-arm reporting implication in planning's Q9 resolution; it changes no
portfolio construction, prior, loss function, configuration count, or ledger
row count in the main pre-registration.

The main entry explicitly says that both "blend versus blend" and "blend
versus single-sleeve" comparisons must be prior-matched, but its comparison
count enumerates only the latter. V8 will report both:

* 4 blends x 3 single sleeves x 3 weights = 36 blend-versus-single pairs;
* choose(4, 2) x 3 weights = 18 blend-versus-blend pairs; and
* 54 total ETF cross-arm comparisons.

Every pair uses the same 5 bps window, paired 10,000-resample stationary
bootstrap with block length 21, HAC counterpart, and correlation. Bayesian
cross-arm posteriors use skeptical and neutral priors only. No deep-informed
posterior enters any of these 54 comparisons.

These are inference comparisons among the already fixed 12 configurations,
not additional trading configurations. Trial accounting remains 15 distinct
v8 configurations and 549 fold rows. No comparison is used to rank or select
a mix or weight.
