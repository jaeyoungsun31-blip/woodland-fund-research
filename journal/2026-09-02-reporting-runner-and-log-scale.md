# 2026-09-02 — Reporting: the missing runner, and a log-scale fix

Append-only. Engineering only: no study, no ledger rows, no methodology change.
Done from the planning chat because it is a renderer gap, not a research
decision.

## The gap

`woodland/tearsheet.py` (built 2026-09-01, commit 0538a53) is a renderer that
must be handed a completed `BacktestResult`, and `scripts/tear_sheet.py` is a
thin `write()` wrapper around it. Neither runs a strategy — deliberately, so
reporting cannot alter a backtest's inputs. The consequence nobody noticed:
**no script ever called it**, so `reports/` had been empty since the renderer
was written, and every result in this project had been read as tables of
numbers only.

## The fix

New `scripts/generate_reports.py`. It rebuilds each study's series from its
frozen pre-registered configuration, checks every one against the Sharpe
recorded in the journal, and refuses to write anything on a mismatch — the
same discipline `scripts/run_inference.py` uses, for the same reason: a
picture of a portfolio that is not the journalled portfolio is worse than no
picture. Then it writes one tear sheet per series plus `reports/summary.json`
(metrics and month-end equity curves) for downstream viewers.

**All eight series reconstructed exactly**, to three decimals:

| series | rebuilt | journalled |
|---|---:|---:|
| v2_ensemble | 0.700 | 0.700 |
| v3_voltarget | 0.709 | 0.709 |
| spy | 0.660 | 0.660 |
| mix_60_40 | 0.806 | 0.806 |
| vt_60_40 | 0.853 | 0.853 |
| v4_ensemble | 0.861 | 0.861 |
| mkt | 0.710 | 0.710 |
| mkt_cash_60_40 | 0.841 | 0.841 |

That is worth recording as a result in its own right: three sessions of
journalled numbers, rebuilt from scratch by a script written independently of
the ones that produced them, reproduce exactly. `reports/` stays gitignored —
these are regenerable artifacts, not records.

Run: `python scripts/generate_reports.py [--skip-deep]` (~35s for all eight).

## Log-scale equity curves

The first deep-history tear sheet exposed a real defect in the renderer. On the
1932-2026 window a linear y-axis compresses everything before ~1990 into a flat
line at zero: the last doubling occupies half the panel and the first fifty
years are invisible. `save_tear_sheet` now switches the equity panel to a log
axis when the curve spans more than two orders of magnitude, where equal
vertical distance is equal percentage change and every decade is legible. Short
windows are unaffected. Renderer-only; no number changes.

## Note for the coding chat

`generate_reports.py` was executed in the planning session's container
(Python 3.11) rather than on the Mac. The device-side Linux VM ships Python
3.10 and `woodland/data.py` imports `datetime.UTC`, which is 3.11+. Nothing to
fix — the repo's own venv is 3.12 — but it is why the PNGs in `reports/` should
be regenerated locally rather than trusted from elsewhere.
