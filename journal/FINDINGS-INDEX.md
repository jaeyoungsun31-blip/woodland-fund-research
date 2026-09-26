# Findings index

Not append-only. This file is maintained and rewritten; the journal entries it
indexes are the record. Built 2026-09-10 from all 154 entries.

**Purpose: read this before writing any pre-registration.** The project's
recurring failure is that entries are written and never read back. On
2026-09-10 planning re-derived a finding already on the record from 2026-09-03,
and discovered a binding decision that had been suspended for seven days.

---

## 1. Closed questions — do not re-ask

| Question | Answer | Source |
|---|---|---|
| Does trend-following work on the ETF window? | No. Family closed. | `2026-09-02-planning-decision-close-trend-family` |
| Is there a gross edge at zero cost vs the vol-targeted benchmark? | No, in the trend family. Standing requirement for any successor. | `2026-09-02-trend-v12-frontier-INTERIM` |
| Does leverage help the strategy? | It helps the **benchmark** more: 60/40 +0.118 Sharpe, the largest free improvement in any study. | `2026-09-02-trend-v9-leverage-results` |
| Does cross-sectional momentum work post-1980? | **Not established, three times.** FF deciles on rf=0; the same on excess returns; the EODHD survivorship-free panel. | `2026-09-03-xsmom-v15-holding-results`, `2026-09-03-v15-v17-rf-sharpe-recomputation`, `2026-09-10-planning-decision-termination-signed` |
| Pre-1980? | Yes — all four holding frequencies cleared both references at 0/5/10 bps. | `2026-09-03-v15-v17-rf-sharpe-recomputation` |
| Does holding frequency matter? | No. 10bps Sharpe 0.789/0.786/0.794/0.788, spread 0.008. Nothing selected. | `2026-09-03-xsmom-v15-holding-results` |
| Does the ML/penalised layer beat naive momentum? | **No — significantly worse.** -0.212, CI [-0.413,-0.026], p=0.033 on the clean 915 universe. | `2026-09-09-planning-ruling-v16-dual-run-closed`, `reports/xsmom-v16-universe-control/summary.json` |
| Does the A2 delisting convention change any verdict? | No. -0.071 cleared, -0.032 full; no arm's verdict moves. | `2026-09-09-planning-ruling-v16-dual-run-closed` |
| Does a sleeve overlay on 60/40 help? | No, and monotonically adverse gross as well as net. | `2026-09-03-sleeve-v17-overlay-results` |
| Is the research phase over? | **Yes, signed 2026-09-10** on the era result, not on T1. | `2026-09-10-planning-decision-termination-signed` |
| Do insider-purchase clusters carry an edge? | **Closed without pre-registration; holdout never opened.** Null above $2M (−0.040%/mo, t −0.12) and $300k–$2M (+0.187%, t +0.81); below $300k unresolved (+3.327%, t +2.36, but median −0.507%, t −3.12, residual SD 14.3%, known defects). 24 looks. | `2026-09-25-planning-decision-insider-clusters-closed` |
| Does buying the Kalshi MLB favourite at the ask pay after fees? | **No — closed by pre-registered kill rule.** 2025 season: −0.0432 [−0.0646, −0.0220] at 60 min, −0.0395 [−0.0609, −0.0188] at 10 min. Underdog follow-up is a post-hoc, unsigned draft. | `2026-09-25-kalshi-mlb-favourite-closed` |
| Is the Kalshi underdog (mirror) trade worth confirming? | **No — abandoned unsigned; Kalshi line closed.** In-sample t 1.28 / 0.96; best confirmation design expected t 1.90; taker costs take ~1.4¢ of a 2.5–2.9¢ mid mispricing; maker fills untestable. | `2026-09-26-planning-decision-kalshi-closed` |
| Do published cross-sectional signals still pay, value-weighted, after 2015? | **Not detectably, gross.** OSAP composite of all 212, post-publication, VW 2015–2024: +0.103%/mo, t 1.34 (2000–2024: t 3.00; EW original spec: +0.292%, t 3.61). 14/208 VW predictors t > 2 vs ~5 by chance; 13.4 effective signals. **Active research phase closed**; live cycle disabled; no capital committed. | `2026-09-26-planning-decision-research-phase-closed` |
| Was the EODHD constituent panel survivorship-free? | **No — survivorship-controlled.** Delisting-inclusive prices (213 symbols / 1,574 symbol-years refused); delisting returns bracketed 0% / −100%; membership 1999–2026 from the symbol-matched `fja05680/sp500` list, not a vendor point-in-time record (EODHD's 2012+ endpoint returned 403). No verdict changes. | `2026-09-26-planning-correction-survivorship-claim-strength` |

## 2. Standing filters — apply before proposing anything

- **T2 (binding):** a study must name the specific quantity it expects to move
  that prior studies did not. No name, no study.
  `2026-09-03-planning-decision-termination-and-v16-withdrawal`
- **The four axes:** if a proposal is axis 4, it is very likely the wrong
  study. `2026-09-03-planning-note-four-axes`
- **Turnover budget K ~ 232:** a proposal must be tested *against* this note,
  not around it. `2026-09-03-planning-note-turnover-budget`
- **Incumbent:** 60/40 has outperformed in every study to date, and its tail
  advantage (CVaR95, CVaR99, max drawdown, underwater duration) does not
  depend on the Sharpe convention.
- **Sharpe convention:** excess returns, never rf=0. rf=0 biased every v15/v17
  comparison toward the cash-heavy incumbent by ~21x the measured effect.
  `2026-09-03-planning-finding-rf-zero-sharpe-bias`

## 3. UNFULFILLED PRECONDITIONS — the serious gap

`2026-09-06-planning-decision-revive-v16-on-constituent-data` declared four
amendments. Two were never implemented, and both dual-run and universe-control
executed anyway.

**A4 — membership leakage test. NOT IMPLEMENTED.** The amendment required that
"altering the constituent list after a cutoff must leave every panel row at or
before that cutoff bit-identical," and called the perturbation tests
"preconditions of execution, not deliverables of it."
`tests/test_no_lookahead.py` contains a *return-side* panel perturbation test
(`test_panel_perturbation_features_coefficients_and_targets_bit_identical`)
and no membership-side test. The revival entry's own standing caution applies:
"A survivorship-clean panel with a lookahead-contaminated membership list will
produce beautiful, entirely false results, and nothing in the output will
indicate the problem."

*Scope of the damage:* lookahead inflates results. The **negative** findings
are therefore robust — contamination cannot make a working strategy fail. Any
**positive** number from these runs is not, including naive momentum's 0.4545
Sharpe. This is a second, independent reason not to publish that figure.

**A3 — per-symbol costs. NOT WIRED.** The amendment required per-symbol costs
with flat scenarios retained alongside. Neither `costaware_panel` nor
`universe_control` references per-symbol costs; both runs used flat
0/5/10/25 only. SPY and IEF measured 0.130 and 0.542 bps against the flat
25 bps applied, so the flat schedule is likely conservative for large caps and
unknown for small ones.

## 4. Open decisions awaiting signature

- `2026-09-04-planning-decision-Q5-statistical-gate` — until signed, the four
  original 2026-09-01 gate conditions remain in force.
- `2026-09-04-planning-decision-scope-integrity-refusal` — until signed,
  cycles continue to refuse.

## 5. Known defects and open items

- `journal/defect-register.md` holds six deferred items.
- Full-suite ETF bar-count failure (5,502 vs 5,499), unchanged since
  2026-09-06 and deliberately not worked around.
- EODHD constituent history floor: the pre-2012 half may need an external
  source (CRSP/WRDS or SEC reconstruction). Unresolved.
  `2026-09-06-planning-finding-eodhd-constituent-history-floor`
- Alpaca 403 from 2026-09-04 is resolved as of 2026-09-09; when or how was
  never recorded.
- The 15:00 cycle LaunchAgent is disabled and preserved under
  `ops/disabled-launchagents/`.
- 32 smoke-test ledger rows under `smoke-universe-control-DELETEME`, retained
  and disclosed rather than deleted.

## 6. Deliverable

`writeup/research-report.md`, then Phase 3, then Phase 4. The report predates
the rf=0 correction, the survivorship finding and the universe-control result;
parts of it are now wrong rather than merely incomplete.
