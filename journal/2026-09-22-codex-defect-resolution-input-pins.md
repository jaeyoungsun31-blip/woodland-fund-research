# 2026-09-22 — resolution supplement: anchor failures and ignored-input pins

Authorized defect audit only. No study was rerun or result recomputed. This entry supplements `2026-09-22-codex-defect-red-suite-since-snapshot-freeze.md`; that earlier entry is unchanged.

## Four additional failures at `20ff814`

All four tests were red at `20ff814` because `scripts.reproduce_all` lacked `load_anchor_set_split` and/or `freeze_time_anchor_records`. Commit `a97287a0435a071242c96e1742f50f3d0a17212c` introduced the missing functions and made each pass. The final v16 dual-run result was recorded in intervening commit `f420350`, so a study result **was inspected while each of these tests was failing**. The universe-control result at `7308092` came after the fix.

| Test ID (`tests/test_anchor_set_split.py::`) | Fix commit | Result inspected while failing? |
|---|---|---|
| `test_signed_anchor_set_split_is_30_reproduced_and_23_replaced` | `a97287a` | Yes: v16 dual run (`f420350`); universe control: no. |
| `test_reproduced_gate_refuses_delta_above_its_own_published_tolerance` | `a97287a` | Yes: v16 dual run (`f420350`); universe control: no. |
| `test_reproduced_gate_uses_each_anchor_precision_not_a_flat_floor` | `a97287a` | Yes: v16 dual run (`f420350`); universe control: no. |
| `test_replaced_anchors_have_no_pass_field` | `a97287a` | Yes: v16 dual run (`f420350`); universe control: no. |

## Ignored input inventory and hashes

The table enumerates gitignored files read by the initial v16 panel, the four-arm v16 dual run, or universe-control scoring and disclosure. The two factors copies share the same bytes. “Previously pinned” means the **raw file SHA-256** was in config or a committed input manifest before this supplement. The ETF snapshot had an aggregate adjusted-close frame hash, which did not pin raw parquet bytes. The favourable panel hash appears in committed trial outputs, but those outputs are results rather than a committed input manifest and no reader enforced the hash.

| Ignored input (repository-relative) | Current SHA-256 | Previously pinned in config or committed input manifest? |
|---|---|---|
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/DBC.parquet` | `e93ab84f491b3175ea5a6507484a804149e7d12109fe392a3e29eceee66e1c07` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/EEM.parquet` | `587bce086b8cf858241bcf0d13053bc7bc66cd6795ae3875329432c33956cbd0` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/EFA.parquet` | `0bd38feed58096c2da1963abe93463f92c52c56b086a1822c3fe33fff184bace` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/GLD.parquet` | `798ba66932a437654f3b7af310c0bd60351b7048a50b51d27fad423d5e1e01ae` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/IEF.parquet` | `6a8a1c1eecdbea91919999c2085b4dd81fc7b62dfa4afd4242b4cd883b29f316` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/IWM.parquet` | `8f693285b23ffbc936ae8ec1a948c38d4e04c54cd5c1955106d01c42a47fbc47` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/QQQ.parquet` | `fb0696e2daaa156162cd1c2c94213c799fb5d80b77383f17da31508c695e659f` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/SPY.parquet` | `9226ca17191f2457eca8cb0ec38c04c7fded8cd886ab185d2e03f8f483962888` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/TLT.parquet` | `f2e6c92e22d57b313799630b9a7afdce9d5550a44ec1cf84af5a8ced5e0ea252` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLB.parquet` | `985ce3470cf017b85c0045311523ad645117198cd235d908b41b04d4dcf248ab` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLC.parquet` | `64469139b69a7afd69ad74a42fd974bcf9ab9f4276f2fe7c7413bfc09ba1e04a` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLE.parquet` | `9958b6ff4ecc53033760001f511f9f3553ee29a6386391a11e230002fee1303d` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLF.parquet` | `89ff3e6b6341aab4147d0927161126ad85503f02451bb7116d9a87a5fd3cebab` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLI.parquet` | `60309a12bd51606378568586d768eb230ba5a1ac4de95f5b1ecab0dcf4adca61` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLK.parquet` | `9da721910915cea4417e985d185de2a4335aa2b974801a6fbcf054e41bed9cb5` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLP.parquet` | `4fe9919324646040f2bcbce117efe1b53c312db61278e6817a02dcc7b5b31fd3` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLRE.parquet` | `98115c019801513fbad186d1246bb0a28b1fc43655740040c795e3055a0fd45a` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLU.parquet` | `b9e6df858432a1e5d9ce777bbc3775518f76440436bb4ea279b53fc2394a38ea` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLV.parquet` | `8dd0a3951693c891134f169f45b639461a137330d62e15b69bfd6596d3d31e55` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/XLY.parquet` | `606f184f73d0998a570737f0663e4c2a86d8ff8bed7172b3b154b36a5b259a9b` | No raw-file pin; aggregate adjusted-close frame was pinned. Now raw hash pinned and enforced. |
| `data/SPY.parquet` | `c74e439995150b7c62497bde09b64e54353e6849fd3cb47f0a60898d1647164f` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-constituent-panel/membership-mask.parquet` | `decdd7dfd9123dca73f9aa6af148e889e53ea5afcd250f06ccc4b400af971400` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-constituent-panel/panel-returns.parquet` | `c4d9403771eb1f69ce86804602774ca39ca587791dfabc7c266720c2695ffde2` | No config/manifest pin; historical hash in committed preregistration. Config now pins historical hash; current file is refused. |
| `reports/security-resolver/2026-09-07-constituent-panel/panel-returns-a2-adverse.parquet` | `789fbd053d70ad95326f31c2bfd0ab85b19f1e9b6af833bb8e4175ff8e1a9cfb` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-constituent-panel/panel-returns-a2-favourable.parquet` | `575d1d08c16b4dcf68a9b5eaed304e20fdd82a80ca9430566ce81af81189aeba` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-constituent-panel/panel-summary.json` | `1d422bc86cb5bd15fe60863ed01094aabe13a2a388513351cc2aaae5a77a60ec` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-missed-event-screen/missed-event-candidates.csv` | `4c9a87a18cbd3ec28d3fbbcd59bc55f8a7eeec8e21637d0850c01c65ef1f57d4` | No; now pinned and enforced |
| `reports/security-resolver/2026-09-07-tiingo-crosscheck/crosscheck.csv` | `19b37a79592b5a2dda7a2c5d25459ba3a495ce038fe676524200a789e0010ba1` | No; now pinned and enforced |
| `reports/xsmom-v16-panel/pinned-run/inputs.json` | `10d324a444425bf7347b8aaba384637f6106f532a1c1becb45778c058bc43619` | No; now pinned and enforced |
| `data/fama_french_factors_daily.parquet` | `ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7` | `risk_free_sha256` added in preceding 2026-09-22 repair; now enforced for both working and frozen stores. |
| `data/snapshots/etf-4c6a36b8c1e52f2cc50dca437ff4d892dc21a87c96b18ff08de70eb85e84d901/fama_french_factors_daily.parquet` | `ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7` | `risk_free_sha256` added in preceding 2026-09-22 repair; now enforced for both working and frozen stores. |

The initial v16 `panel-returns.parquet` currently hashes to `c4d9403771eb1f69ce86804602774ca39ca587791dfabc7c266720c2695ffde2`, whereas the signed preregistration and snapshot-refusal journal record `47d4eee2c5c90a37a731d985148efb85058fae40dc2202a5f4953d04884fcaf5`. The config pins the recorded study hash; an attempt to read the current file now refuses. This does not establish what bytes were present at execution time for other inputs whose historical raw hashes were not recorded. The tracked cleared-subset and universe-control manifests are outside this ignored-file inventory; the latter already has a source-enforced SHA-256.

The new `pinned_input_sha256` map in `config/universe.yaml` records raw hashes. The panel, mask, cross-check, event-screen, working SPY calendar and ETF snapshot readers check these before parsing. The risk-free loader checks both stores. A tamper test changes an ignored membership mask and confirms refusal. No prior journal entry or trial row was edited.
