# v16 panel run refused before fitting: ETF snapshot changed

as_of: 2026-09-04 (ETF); 2026-06-30 (constituent panel).
Registered ETF SHA256: 7b64be101f62166ed9261a8d51a8894f61310238dfa8d75c2c8e4f3d45c233e6
Observed ETF SHA256: 4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901
Panel SHA256: 47d4eee2c5c90a37a731d985148efb85058fae40dc2202a5f4953d04884fcaf5

The input guard refused execution before either arm fitted a model. Twenty ETF
parquet files differ in size and/or modification time from the recorded inventory;
repeated fresh snapshot calculations give the observed hash above. The panel hash
is unchanged. The writer has not been established. No replacement hash or anchors
were silently accepted. The earlier 53/53 reproduction pass describes the original
registered snapshot, not the now-changed store. The full test suite passed 574 tests
with one skip before this discovery; this is not validation of the changed snapshot.
C1/C2/C3 are unavailable for both arms, not failed statistical gates.

Details: reports/xsmom-v16-panel/pinned-run/snapshot-refusal.json.
No study results were tuned, no synthetic bars were created, and nothing was
staged or committed. Price-store immutability cannot be confirmed: the ETF files
changed during this task, although no price write was intentionally performed.

Required panel reporting block: 213 constituents refused / 1,574 symbol-years;
excluded defects CTX, DF, IGT, COG; substitutions SYMC→GEN, NLOK→GEN, WIN→WINMQ,
KRFT→KHC, MMC→MRSH; FCPT has no usable bars. A2 is signed but its treatment remains
unapplied to this panel: no delisting terminal return is imputed and no Case 2
adverse bound is computed.
