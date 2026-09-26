> **Public export:** `volume-screen.csv` and `cleared-subset.csv` (per-symbol, vendor-derived) are excluded from
> this copy. The counts quoted below are unchanged.

# Cleared subset — frozen 2026-09-07 membership

Produced by planning 2026-09-08 to satisfy clause 2 of
`journal/2026-09-08-xsmom-v16-dual-run-preregistration.md`, which requires the
cleared subset to be frozen and read from an artifact at run time rather than
re-derived.

**These files are the authority. Do not re-derive the subset.**

## Method (STATE.md §13)

A panel symbol is CLEARED when all three hold:

1. Tiingo cross-check verdict is `ok`
   (`reports/security-resolver/2026-09-07-tiingo-crosscheck/crosscheck.csv`)
2. it carries no panel quality flag
   (`reports/security-resolver/2026-09-07-constituent-panel/quality-flags.csv`)
3. it carries no volume flag — median in-window volume >= 100,000 shares
   (`volume-screen.csv`, this directory)

```
panel symbols     942
volume-flagged     25
quality-flagged    67
CLEARED           220
```

220 reproduces STATE.md §13 exactly.

## Files

- `volume-screen.csv` — all 942 symbols with `median_in_window_volume` and the
  flag. The **metric is recorded per symbol**, not only the flag, so the
  threshold's sensitivity can be tested without re-reading the price store.
- `cleared-subset.csv` — `symbol, cleared, exclusion_reasons`. Every excluded
  symbol names why, so the subset is auditable rather than asserted.

## Provenance and known limits

The volume screen was computed from `data/Woodland-EODHD/*.parquet` by planning.
Substitutions applied: SYMC→GEN, NLOK→GEN, WIN→WINMQ, KRFT→KHC, MMC→MRSH.

**The threshold is a heuristic, and it has known false positives.** NVR and GHC
are genuinely thin, legitimately low-volume S&P 500 members and are flagged
anyway. The screen is a conservative filter for defining a comparison subset —
it is NOT a claim that a flagged symbol is defective. The wrong-security
question (`STATE.md` §7.2) remains open and is not settled by this file.

## Why this file exists

STATE.md §13 stated a method and a result but persisted neither input nor
output; the 25-symbol volume-flag list existed only as prose. Codex A correctly
refused to construct the freeze from a prose table and from a lane it is
forbidden to read. That refusal was right and this artifact is the fix.
