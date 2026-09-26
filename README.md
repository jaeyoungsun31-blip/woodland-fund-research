# The Woodland Fund: a student's pre-registered search for a market edge

> **About this copy.** This is a cleaned, single-commit export of a private
> working repository. Journal entries and reports in this copy were redacted
> for local file paths and vendor-data excerpts: EODHD price levels became
> percentage changes, and per-ticker Tiingo tables became counts. References
> to a withheld working paper and a withheld pre-release audit were also
> replaced with short notes, in this README and in two journal entries
> (journal/2026-09-26-planning-correction-survivorship-claim-strength.md and
> journal/2026-09-26-planning-correction-survivorship-citations.md). A few
> files are excluded (see below). The pre-registration commit order cited
> throughout the journal can be verified in the private repository on
> request.

The Woodland Fund is one student's research programme. It asked a single
practical question:

> With free or low-cost daily data, no leverage and retail trading costs,
> can a systematic strategy beat a boring 60/40 portfolio out of sample,
> after costs?

For everything tested, the answer was **no**. The repository is the full
record of how that answer was reached:
- pre-registrations committed before results
- sealed holdouts enforced in code
- an append-only research journal
- a ledger of every configuration tried
- the code that produced each number

Nothing here is investment advice. No strategy was promoted, and no
live-money strategy has traded.

## Start here

- The accompanying working paper is being rewritten by the author and will be added later.
- **[`journal/FINDINGS-INDEX.md`](journal/FINDINGS-INDEX.md).** Every closed
  question, its one-line answer, and the journal entry that holds the
  evidence.
- **[`writeup/research-report.md`](writeup/research-report.md).** The longer
  account of the trend and momentum programme: seventeen studies, the
  inference methods, and the turnover budget.

## Headline findings

Each is stated at the strength of its source. Follow the link for intervals
and caveats.

| Question | Answer | Evidence |
|---|---|---|
| Cross-sectional momentum after 1980 | **Not established.** Three independent readings. On a delisting-inclusive, survivorship-controlled S&P 500 panel, a penalized model was significantly *worse* than naive momentum: −0.212 Sharpe, 95% CI [−0.413, −0.026] | [termination](journal/2026-09-10-planning-decision-termination-signed.md), [survivorship correction](journal/2026-09-26-planning-correction-survivorship-claim-strength.md) |
| Insider-purchase clusters | Null above $300k daily volume. Below it, **unresolved**, not positive. Closed without pre-registration; holdout never opened | [closure](journal/2026-09-25-planning-decision-insider-clusters-closed.md) |
| S&P 500 deletion rebound | **Untested probe.** One defective price file flips the sign of the answer | [probe](explore/deletions/README.md) |
| Kalshi MLB favourites, 2025 | **Closed by pre-registered kill rule:** −4.3¢ per contract, 95% CI [−6.5¢, −2.2¢] at 60 minutes | [closure](journal/2026-09-25-kalshi-mlb-favourite-closed.md) |
| Kalshi underdogs | Too little power to confirm. Abandoned unsigned | [closure](journal/2026-09-26-planning-decision-kalshi-closed.md) |
| 212 published anomalies (OSAP) | Value-weighted post-publication composite, 2015–2024: +0.103% per month, t = 1.34, gross of costs. What survives is concentrated in equal-weighted small-stock portfolios | [composite](explore/osap/composite_report.md), [triage](explore/osap/triage_report.md) |

The research phase is closed
([decision](journal/2026-09-26-planning-decision-research-phase-closed.md)).

## How to navigate

| Path | What is there |
|---|---|
| `DESIGN.md` | The programme's design contract |
| `journal/` | Append-only, dated decision and results entries. Corrections are new entries, never edits |
| `journal/trials.db.gz` | SQLite ledger of every configuration evaluated, including failures. Shipped gzipped to keep files under 5 MB: run `gunzip -k journal/trials.db.gz` before using scripts that read `journal/trials.db` |
| `woodland/` | Library: data checks, backtest engine, metrics, walk-forward harness, block-bootstrap and HAC inference, signals |
| `scripts/` | Study runners, ingestion, and `reproduce_all.py`, which rebuilds journalled headline numbers and fails on any mismatch |
| `tests/` | The suite that must pass before any result is looked at, including no-lookahead perturbation tests |
| `explore/` | Exploratory lines (insiders, deletions, Kalshi, OSAP), each with its own pre-registration or README and holdout guard |
| `reports/` | Selected derived outputs from the momentum runs: portfolio-level returns and metrics |
| `writeup/` | The research report. The accompanying working paper is being rewritten by the author and will be added later. |

**A note on commit hashes.** Journal entries cite commit hashes as evidence
of ordering, for example that a pre-registration was committed before any
data was fetched. This copy is a fresh single-commit export, so those
hashes refer to the private working repository, where the commit order can be
verified on request.

## What is excluded, and why

- **Market and vendor data.** No raw data is included:
  - EODHD end-of-day prices (paid subscription)
  - Tiingo responses (free tier)
  - Kalshi market data and candles
  - Open Source Asset Pricing files
  - Fama–French archives

  Vendor terms restrict redistribution, and every dataset is rebuildable
  from its source with your own access.
- **Per-symbol vendor-derived tables.** For example per-symbol volume
  screens and Tiingo split and coverage lists. Where a report depended on one,
  the aggregate result is kept and the per-symbol table is removed.
- **Credentials and local configuration.** `.env`, API keys, and machine-
  specific launch configuration. None was ever committed.
- **Internal agent-coordination files.** Working-state notes used to
  coordinate the coding agents.

Some journal entries quote individual prices as evidence of data defects,
for example a stock split recorded as a loss. They are kept as short
excerpts.

## Reproducing with your own data licences

1. **Environment.** Python 3.11+ and [uv](https://github.com/astral-sh/uv):
   `uv venv && uv pip install -e ".[crosscheck,dev]"`, then
   `.venv/bin/python -m pytest -q`.
2. **Credentials.** Put them in environment variables or an untracked `.env`:
   - `TIINGO_API_KEY` for the cross-check source
   - `ALPACA_API_KEY` and `ALPACA_API_SECRET`, only for the paper-trading
     loop

   The EODHD downloader (`scripts/woodland-download-eodhd.py`) reads its key
   from a local file outside the repository. Keys are never written to the
   repository.
3. **Data, by study:**
   - ETF studies: `scripts/ingest.py` (Yahoo, with a Tiingo cross-check) and
     `scripts/ingest_fama_french.py` (Ken French data library).
   - Constituent panel: an EODHD subscription that includes delisted
     securities. Historical membership comes from the public
     [`fja05680/sp500`](https://github.com/fja05680/sp500) list; see the
     survivorship correction for what that does and does not control.
   - Kalshi: public, unauthenticated endpoints only
     (`explore/kalshi/*.py`), plus the MLB Stats API.
   - OSAP: `explore/osap/fetch.py`. Google Drive may refuse anonymous
     downloads; a signed-in browser download works.
     `explore/osap/sources.json` pins the sha256 of each file analysed.
4. **Verification.** `scripts/reproduce_all.py` rebuilds the journalled
   headline numbers and exits non-zero on any mismatch.

Results depend on vendor data versions. Adjusted prices are revised as
corporate actions are reprocessed, so exact reproduction needs the same
snapshots. Where they matter, the journal records snapshot hashes.

## AI assistance

**Research design and decisions** were made by the author, Jaeyoung Sun, in
a planning role:
- the questions
- the pre-registrations
- the kill rules
- the acceptance or rejection of each result
- the termination criterion

**Implementation** was done by AI coding agents, OpenAI Codex and Anthropic
Claude Code, under that direction. They wrote code, ran analyses, and
drafted journal entries and reports.

**Verification** relied on mechanisms, not trust in any agent:
- an automated test suite that must pass before results are examined
- perturbation tests that detect lookahead
- an append-only journal in which errors are corrected by new dated entries

The record includes agent errors caught this way; see
`journal/defect-register.md`.

## Citing

If you use the OSAP-based results, cite Chen, A. Y., and Zimmermann, T.
(2022), "Open Source Cross-Sectional Asset Pricing", *Critical Finance
Review* 11(2), 207–264.

## Licence

Code is MIT; prose is CC BY 4.0. No licence is granted for third-party data.
See [`LICENSE`](LICENSE).
