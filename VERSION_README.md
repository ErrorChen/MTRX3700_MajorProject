> 本文保留独立Member B及整机历史。2026-11-05当前源码、成功完整构建、实际设备及发布SOF均为E7070008。本版R6 PASS13项+CAUGHT、270.641086秒；编译1159.722秒及门检25.963秒PASS，setup/hold +1.021/+0.121ns，下载/版本读回成功。首次真实蓝1从已锁定起始，经一次主机START完成落地接近/末端对准/DOCKED，观察ARM至终态29.315066秒、J3329mm，零速保持3.18423秒；用户确认持续前进、偏转不明显，探头前端约33.5cm。其余五牌、无目标起始搜索、E8 POWER/红2及重复性仍待，末端约25秒微调仍慢；历史失败全部保留。操作见[README.md](README.md)，证据与限制见[修复验收记录](docs/REPAIR_RESULT.md)。

# Version history and validation / 版本与验证记录

This is the consolidated history of Member B and the later ECHO-7 B/C integration. Entries below run from the earlier
baseline to the latest work. Build identities, failed experiments and evidence
levels are kept separate. README.md and README_EN.md are the maintained Chinese
and English operation guides; OWNERS.md records individual-file responsibility and origin.

这是按开发先后整理的版本记录。MODEL、RTL_SIM、拟合、下载、相机实测和用户确认的
实体VGA分别记录；历史通过不能证明后续源码通过。课程要求、用户需求和设计选择也不混用。

**当前入口（2026-11-05）**：本页后半的“ECHO-7 整机修复与现场迭代”及末尾E5至E8记录本次
`dc1db23` 基线之后的工作。历史段落中的“最终”“不再下载”“静止 Member B 顶层”
以及当时的 R6 FAIL 只描述对应日期和源码，不能作为当前集成版本的结论。
当前`E7070008`正/负方向各433检查、88完整UART PASS；完整R6 PASS13项+CAUGHT、
270.641086秒、targetMet=true。Full Compilation1159.722秒及post-fit25.963秒PASS，
ALM29281/32070（91%）、setup/hold最差+1.021/+0.121ns；实际下载及E8读回通过。
已锁定蓝1起始的真实相机/J3/IR/UART落地接近、减速、末端对准与DOCKED完成一次，
首次观察ARM至DOCKED29.315066秒、J3329mm，DOCKED零速保持3.18423秒后正常收尾V1。
用户确认持续前进、偏转不明显；本次START来自主机一次命令，合成写入/心跳均0。
其余五牌、从无目标开始搜索停靠、E8 POWER/红2启动仍待，不把单次成功外推全部需求。
末端约25秒微调、重复性和左右位移差仍保留；E5/E7实测失败、E6时序失败未删除。

此前`E7070005`的方向控制回归在负生产参数及正泛型参数下各**269 PASS**，
固定25fps真实像素管线到UART回归12帧通过；正常长回波FAR分类、d页FAr和主机分类字段
已加入候选源码。首次完整R6 **FAIL，303.500928秒**：12项PASS，reader编译达到总期限，
mutant未运行；随后最终优化R6实际 **13 PASS + 1 CAUGHT，239.403059秒**，达到285秒目标。
Full Compilation **1173.143秒PASS**、post-fit **25.799秒PASS**，
ALM29507/32070、setup/hold最差+2.089/+0.116ns；E5下载及版本读回通过，当时设备
保持E5的VISION_ONLY/未ARM/零速；零速蓝1锁定及FAR分类已实测，三次物理满圈已确认并设13.6秒近似上限，误差与不稳定的起步单边前冲保留。新默认TURN_SIGN=-1只校正有效视觉转向，未证明具体接线根因。

此前已完成构建/下载的 `E7070004` 控制自检为 **254 PASS**，完整 R6 为 **12 PASS + CAUGHT，
219.556074 秒**；Full Compilation **1121.141秒PASS**、post-fit门检 **25.868秒PASS**，
22:31:50 AEDT新SOF下载及E7070004读回成功。真实红2重新选择、新锁定后ARM/ALIGN
板上链路已通过，用户确认实物启动，并最终澄清“蓝一脱离后就停车了”。
收口为VISION_ONLY/未ARM/左右逻辑零速，用户确认已停止；主机STOP的独立机械停车时刻未测，zeroSent只证明发送完成。
不借用E7070002/E7070003 的硬件动作结果。完整证据和待验收项目见
[修复验收记录](docs/REPAIR_RESULT.md)。操作入口为[中文README](README.md) /
[English README](README_EN.md)；一页数据表发布位置为
[docs/ECHO7_Integrated_Datasheet.pdf](docs/ECHO7_Integrated_Datasheet.pdf)，按当前指标文件生成；各版证据保留其实际版本范围。

## 2026-10-22 to 2026-10-23: same-group predecessor

The initial repository was paekinator/MTRX3700-Major-Project. The user confirmed
that Hajin and Jiaze Sun developed this preliminary code in the same group;
Hajin mainly handles Member A. Member B's confirmed SID is 540207680. The old
starter package was reference material, never a replacement for that repository.

Earlier AI-assisted work covered colour masks, display statistics, fixed-ROI
diagnostics and counterclockwise VGA presentation. The retained native camera
size is 320x240; display orientation is separate from recognition and B/C
coordinates. Earlier safety/chassis work belongs to the predecessor and is not
included in the current stationary Member B top. Early statements that the
formal Brief or Verilator were unavailable describe that time only.

## 2026-11-02: migrated repository and real-camera diagnosis

The migrated tree was reorganised around rtl/, quartus/, tests/, tools/ and
assets/. The layout commit was c67b34e; the subsequent user commit 63bc383 included
continuous-replay fixture work. Current work continues from actual HEAD
bfe9616139e88bc56c3f9798b21f49c044efc092 without reverting user changes. The inspected
remote is ErrorChen/MTRX3700_MajorProject_V2; no push or force-push was performed
by this continuation.

Real captures established these separate failure classes:

- Orange background entered the old red classifier. The production path moved
  to integer HSV comparisons rather than claiming that PDF RGB values were
  camera measurements. Hue/saturation gates remain fixed; calibration updates
  two brightness floors only.
- Aggregate per-colour boxes hid individual signs. Bounded connected components,
  per-object contours and typed labels replaced that coarse display.
- Oblique signs needed a measured quadrilateral and native anchor checks.
  White strokes and direction anchors now use different, explicitly versioned
  predicates. No digit is obtained from a sheet cell or candidate slot number.
- Several initial replay failures were test-data mistakes: shared expected.hex
  collisions and a positional vector index selecting a synthetic negative
  instead of a recorded frame. Named, source-checked fixtures replaced them.

The relocated 20-bench ModelSim suite eventually passed as one invocation
20261102T135055_875419Z_test. Earlier partial runs and failed aggregate invocations
were not relabelled PASS. Native preparation tests covered 131,072 division
inputs and 524,288 signed clipping boundaries. MODEL checks remained separate
from those executed HDL tests.

## 2026-11-03: compiler recovery before the external review

| Build or experiment | Actual result and consequence |
|---|---|
| 77744a75 | Fitter routing-congestion failure |
| d606e861 | MAP passed; full compile deliberately terminated; no fitted result |
| fd9950d9 | 3,600-second timeout; no completed fit/timing acceptance |
| 9c0e0297 | Post-map diagnosis found a 64.749 ns path and -45.030 ns slack; not a fitted result |
| e943678b | Pipelined preparation reduced that path to 11.526 ns; severe later routing congestion remained |
| Manual GUI run | Windows recorded Quartus20.1 quartus.exe/QtCore4.dll crash at01:45:43 Sydney; this did not establish a separate quartus_fit crash |
| ab41e932 | Isolated Quartus18.1 complete fit/timing passed; compile16m32s; worst setup+3.205 ns, hold+0.119 ns; programmed and read back schema2 |

The ab41e932 baseline used17,519 ALMs,347/397 M10K and29/87 DSP. Its new frame225
accepted red1/2 and blue1-5, rejected blue6, and had not yet calibrated. Later
real frame31285 did commit eight samples/config1 (red32/blue28), but candidate
overflow made that frame invalid. Therefore both "calibration never worked"
and "calibration completed, so recognition is stable" were incorrect claims.

Source-closure isolation, explicit tool paths, exact build/SOF hashes, full
warning retention and the post-fit clock/CDC gate were retained in the CLI.
Windows CRLF parsing initially made successful programming appear to fail;
the parser was fixed and a subsequent real program/readback passed. Old SOFs
were never promoted to products of failed builds.

## 2026-11-03: supplied review and its disposition

The supplied review checked HEAD bfe9616, source identity e1cd47da with41
dependencies. It executed Python3.12.14/NumPy2.3.5/Pillow12.3.0:99 tests with9
skips in266.328 seconds, not99 fully executed passes. Verilator was absent in
that review environment, so its R6 result was ENVIRONMENT_BLOCKED. It did not
run Quartus, ModelSim or the physical board. Its old-fit comparison found12
changed and2 added dependencies; old20-bench evidence had19 changed source/TB
hashes. The review's limitations were not treated as current local limitations.

The final Major Project Brief was supplied,7 pages, SHA256
`6c4311e60feb53cc1ec17c5d1f00c43baaf72788d73b166972d6b394eefa048c`.
It is retained at docs/Major_Project_Brief_2026.pdf. The three-person
proposal is a separate reference, not a rubric. The five lecture PDFs remain
under docs with their original filenames and unchanged bytes.

| Review finding | Implemented disposition |
|---|---|
| Busy JTAG calibration ACK could silently lose an arm pulse | Action-ready/BUSY rejection added; acceptance, start and terminal commit are distinct; real busy rejection subsequently tested |
| R6 oracle still selected colour1/reader3 | Production/model/vector/debug profiles unified; historical profiles remain explicit replay choices |
| Old calibration success followed by capacity overflow | Active and completed capacities measured independently; later shared16 design and real duplicate scene tested |
| Current fit/program did not match source | Each frozen source obtained its own build identity, SOF digest, readback and new acquisition |
| R6/R7/R8/R9 incomplete | Actual5.050 simulation/mutant detection, recorded-input RTL comparison, per-file SID provenance and physical algorithm comparison added |
| SW0/SW1 display evidence missing | RTL pixel/stream checks and user-reported four-mode physical confirmation obtained; not described as a monitor photograph |

The review's suggested SW2 and earlier SW9 comparison mapping were superseded
by the user: SW8 is the algorithm comparison; SW9 is complete processing/overlay
pause. Its request to show rejected SW0 slots was also superseded by recognised-
only compact panels. Microphone input remains explicitly deferred; no ordinary
UART or motion implementation was added.

## 2026-11-03: active-label and timing corrections, 5633257e

Build19b60d31/schema3 fitted and programmed. New frame343 recognised all eight
formal signs, but later90-frame observations included9 red active-capacity
overflows. A seven-sample calibration attempt failed without corrupting config1;
its busy-request rejection alone was not called successful calibration.

Real frame30507 needed nine temporary red labels although only two red and seven
blue outputs survived. The active12/output8 revision7eec0ba4 recovered this
geometry in MODEL/RTL but failed VGA setup at-0.291 ns. Exact reciprocal
arithmetic in b6e89ca6 removed the37-level constant-division path, but an artificial
Gray first-stage hold failure remained. A hold-only false-path experiment
discarded required skew checks and was rejected. The final constrained design
retained20 ns max/skew/net bounds, vendor-style asynchronous minimum delay and
explicit Meta-to-Sync checks.

The frozen5633257e source SHA256 was
`5633257ec6022612b9b023a46902db3fe74763cedffc4b331756c1c2e8c574d3`;
its SOF SHA256 was
`11b555f7b06d863a7c8172417cb72d32f951f29f2da663e13153901cbdebefca`.

| Layer | Executed result for5633257e |
|---|---|
| MODEL |136 host tests and11 counterfactual groups PASS |
| RTL_SIM |30 ModelSim benches PASS; clean Verilator5.050 R6 in62.375s, intended early-lock mutant CAUGHT |
| R7 | Recorded frame327 compared to model and normal/bbox RTL; both accepted8, so no perspective benefit demonstrated on that input |
| QUARTUS_FIT_TIMING |899.968s compile+20.437s gate;23,433 ALMs,347M10K,47DSP; setup/hold/recovery/removal minima+3.430/+0.118/+28.081/+0.412ns |
| CAMERA_HW calibration | Three8-sample commits; conservative board-time bounds557.651/622.279/554.597ms; busy arm explicitly rejected |
| CAMERA_HW first trials |90 current reports plus3 retained old-request drains;744/744 labels over93 observations; maximum43.183ms |
| VGA | Four SW0/SW1 combinations reported normal by user; no monitor photograph |

Later physical algorithm comparison on the same5633257e image found actual
failures: normal712/720 labels, bbox469/720; both strict runs FAIL. Normal
frame16493 exhausted active12. Three apparent old-request failures were host
assessment errors; their timestamp-based reassessment did not erase the real
overflow. The cancelled3fcf96d3 active15/output8 build was never programmed.
This old firmware used SW9 for the algorithm comparison, not pure-camera mode.

## 2026-11-03: shared16, automatic orientation and a9caa52f

User-added rotated duplicate blue1/2 created nine blue regions, exceeding the
old output8. An interim split16-per-colour buildaf566fa1 failed resource limits
(3,730LABs and36,364ALMs) and was not programmed. The final implementation has
one16-slot completed pool with explicit colour bits,15 temporary labels per
colour,335 invalid row cycles and a341-cycle core guard. Capacity exhaustion
invalidates a whole frame; it never silently drops a numbered sign.

Reader5 resolves the unique native direction anchor among four corner orders;
ID still comes from pixels. Public B/C v2 is unchanged; private schema7 has96
status words and16 shared marker records. SW0 panels are recognised-only,
blue#0-#7/red#A-#F plus uniquely owned BJ. SW8 is perspective versus bbox; SW9
pauses algorithms and removes all overlays while preserving camera/time/profile.

Frozen source SHA256:
`a9caa52ff9cb8ce06b69755ed3c398c1d9f23a7b7c727a82b13e5e9f0d90d44a`.
SOF SHA256:
`4be67b7f2c52e54a24bfbffed31e7ef9301f1605277bb74b136d8e2f5d8c679b`.
Build20261102T232355_017699Z_build and program20261102T234304_659966Z_program
used discovered DE-SoC[USB-1], FPGA chain index2, not an assumed HPS index.

| Layer | Executed result for a9caa52f |
|---|---|
| MODEL |222 tests, no skips,130.525s; clean727-file export222 tests131.311s |
| RTL_SIM |35-bench audited aggregate; original full run failed a missing negative-anchor fixture; exporter repaired,1,680 anchor ROIs plus all unchanged benches verified |
| R6 |Verilator5.050 production-core suite PASS81.344s; clean export PASS60.171s; intended mutant CAUGHT |
| QUARTUS_FIT_TIMING |17m36s compile+23s gate;72 timing/unconstrained checks PASS; setup/hold/recovery/removal+3.272/+0.119/+26.469/+0.409ns |
| Resources |Adjusted ALMs26,537/32,070; actual placement31,478/32,070(98%), all3,207LABs occupied;36,427 registers;347/397M10K;47/87DSP;1PLL |
| Warnings/CDC |114 warning occurrences reviewed; no unreviewed critical warning;63/63 synchroniser chains checked at four corners; numerical MTBF not assessed |

The initial new frame312 and30-frame trial recognised all eight blue signs but
missed red1's cropped top anchor:270/300 labels, overall FAIL, no calibration.
After the user adjusted the view, frame19645 recognised10/10 numbered signs
and paired BJ. Three real eight-sample calibrations committed config12/13/14;
busy requests were rejected in all three. Conservative attempt-to-commit bounds
were596.184/582.718/594.523ms, not precise internal red1-confirmation timestamps.

The user confirmed a9 SW0/SW1=00/10/01/11 as normal ("能正常显示"). This is
USER_REPORTED_PHYSICAL. RTL VGA previews are separately labelled, not photographs
of the physical monitor.

After a further small paper movement, frame30158 exposed a real limit: the
rotated blue2 anchor was only1x3 strong-white pixels. It was correctly rejected
by the current two-dimensional anchor rule. Its red1/reference pair had a3px
centre shift but a5px left-edge shift, exceeding the old fixed4px tolerance.
Raw sample purity itself passed (red252 samples, blue492); changing colour
thresholds would not fix that geometric condition.

The fixed-scene normal trial20261103T013437_754019Z_test used config18 and
three30-frame runs:300/300 labels each,900/900 total, no wrong IDs/overflow/new
drops, maximum46.322ms. SELECT1/2 gave30 expected zero-measurement ambiguous
reports; SELECT3-6 gave48 locked plus12 expected acquiring reports. The user
attested unchanged paper/camera/focus/lighting for the following comparison.
SW8 up/config19 produced298/300,298/300,299/300 (895/900), five rejects and zero
wrong IDs, maximum45.477ms; its strict development gate remains FAIL. Both modes
meet the declared95% numerical accuracy threshold, so this shows only a small
fixed-scene coverage difference, not a general perspective advantage.

Separate fresh frame37621 immediately after normal trials exposed another limit:
RUN3 horizontal support split a rotated blue1 into two components. Raw HSV and
causal cleanup alone retained one component; RUN3 cut its narrow side connections.
The90 sampled passes do not establish that every intervening frame passed.
The1x3 anchor and RUN3 split are different unresolved pixel-resolution failure
modes. Thin-anchor relaxation was explored and rejected because it introduced
false accepts; no success was fabricated from a known digit/position.

SW9 was physically tested with SW0/SW1 both on. The user confirmed
"确认只剩相机图像". Fresh raw frames45271/45502 advanced normally, config20->21,
all three raw-mode flags1, no candidates/observations/readiness, reasonFRAME_BAD,
same target request and committed colour floors. Down again produced frame47787,
config22 and the same tag46/blue3 locked; the sparse snapshots do not prove the
first two reacquisition cycles, which are covered in RTL.

The comparison helper's old fixed720 denominator was repaired to use verified
region/sample counts. Ten signs now correctly mean900 opportunities. Four new
negative/population cases and68 related tests passed; differing denominators
are rejected. This host-only change did not change the programmed FPGA.

## 2026-11-03: scale-aware pairing and documentation consolidation

The user requested removal of evidence/, member_b_review_pack/ and duplicate
docs Markdown, with a detailed bilingual README for future developers. The
maintained documents are now README.md, VERSION_README.md and OWNERS.md.
Reference PDFs remain under docs; formal marker artwork remains under
assets/markers. Required camera regression inputs and host-only truth annotations
move to tests/fixtures with byte hashes/provenance. Reproducible generated logs,
images, simulations and build databases belong in ignored build/.

Historical raw evidence directories are deliberately removed after extracting
their relevant findings here. This file records what was executed; it does not
pretend all old uncommitted raw logs remain distributable after removal. Prior
committed history remains in Git. Current-run originals remain in ignored build/.

The new pairing change replaces fixed endpoint tolerance with scale-aware
centre displacement, minimum overlap and existing width/height/gap ratios.
Unique red1 ownership and raw-RGB purity/stability checks stay intact. This is
configured-orientation bbox pairing, not an unlimited-angle calibration claim.
Its source, tests, fitted result and new board measurements are recorded below
only when executed; a9caa52f results above do not certify that new source.

### Executed checkpoint127d80b2: scale-aware calibration pairing

This checkpoint was completed before the later RUN2/publicv3 edits. Its exact
sourceSHA is127d80b2962cd3b1eb203e9270e1d569a90277437b0d2d7f63709e7d1329e2ab;
SOFSHA7618efef5201a3ddc9dd70fdf073d13045293f3431d5a5fdd51d68ff8dbb807a.
Build20261103T014610_881799Z_build passed full Quartus18.1 flow and timing.
Adjusted ALMs26528/32070; actual placed31581/32070 (98%); registers36651,
M10K347, DSP47, memory2790208bits. Worst setup/hold/recovery/removal slack was
2.588/0.102/27.511/0.397ns. All72 timing/constraint checks passed, with63
synchroniser chains.104 warning occurrences had no new unexplained signature;
ten previously reviewed32-to15bit truncation warnings disappeared after explicit
widths. Physical placement margin remained small and required another actual
fit for subsequent additions.

ModelSim's complete35-bench frozen suite20261103T014940_657181Z_test passed;
the R6 Verilator5.050 Bash entry20261103T014758_481494Z_verilator_course passed
in89.781s and caught the intended premature-lock mutant. The two targeted
calibration benches20261103T014519_152810Z_test passed310checks. An earlier
targeted aggregate014319 remained FAIL because its source changed mid-run,
even though its individual benches passed; it was not promoted to a green run.

Program20261103T021011_039452Z_program succeeded on DE-SoC[USB-1], FPGAindex2,
ID0x02D120DD; board buildId127d80b2/schema7 was read back. Fresh capture
20261103T021040_629684Z_capture, frame689/config1, recognised all10 numbered
markers plus uniqueBJ. Three real calibration attempts021125/021131/021136
committed versions2/3/4, each with8valid sample frames. Conservative observed
attempt-to-commit bounds were600946,605891,531185µs. Each busy-request rejection
test also confirmed the original attempt completed. Camera trial
20261103T021159_884118Z_test passed300/300 in each of three runs (900/900),
maximum capture-to-completion46313/46310/46309µs. These results certify
colourAlgorithm2/RUN3,reader5,public2/schema7, not the later unbuilt edits.

### Consolidation checks and subsequent RUN2/publicv3 development

The authorised cleanup removed1705 files totalling92.7MiB after a SHA inventory
at build/member_b/document_cleanup_inventory.json. Required regression inputs
were reduced to15real PNGs and their profiles/truth/provenance,28files about865KB
under tests/fixtures/camera. Seven reference PDFs were retained byte-for-byte;
their final location is docs/ directly. Formal single-page marker artwork stays
in assets/markers. No Git history or user database was removed. Later Git HEAD
was observed at d1c29be (user commit,2026-11-03T13:46:29+11:00); source hashes,
not an assumption about an earlier HEAD, bind each test/build.

Post-migration MODEL run20261103T015637_094102Z_test passed239tests with no skips.
An earlier isolated export run retained three scratch-directory setup failures;
the fixed BCTL/submission follow-up015326 passed9tests. Portable repository
checks now work in an exported tree without.git, using a temporary isolated Git
directory and real ignore semantics; six new tests and an actual no-Git export
passed021140_repository_check. The explicit datasheet sidecar/source hash is
required before a generated PDF can enter a submission ZIP.

RUN2 was introduced specifically for the observed frame37621 split, retaining
the filter's two-token delay and flush schedule. ColourAlgorithm3 uses the same
HSV2 gate but keeps runs of at least2pixels; historical colour2 remains RUN3.
Across15real images/32profiles, model accepted counts were267(RUN3),269(RUN2),
271(no horizontal filter), with no existing accepted ID lost and no overflow.
RUN2 reconnected the measured two-pixel side bridges. Peak red/blue activity
increased from9/8 to13/9; synthetic sixteen width2noise bars can now overflow
and correctly invalidate a frame.410synthetic cases preserved295 accepts,
236 explicit negatives had zero false accepts, and334known expectations had
zero mismatch. The real1×3 anchor remains rejected; no direction was guessed.
The actual dual-RUN2/RUN3 RTL bench021935 passed2841rows,909120pixels and
243local patterns. Related91host tests passed with resultSHA
f7089e5913dc6625bb3abfed5351ac850bab98c98b03d4ba3cd30a185a3efa40.

The user's next interface request exposed that publicv2 SELECT could only track
blue bays and offered no public marker inventory/location query. Publicv3 adds
typed identities (blue bay, red function, uniqueBJ), LIST/GET alongside the same
CLEAR/SELECT request channel, and an independent query response stream. Query
snapshots use three small synchronous descriptor banks, not a second colour
frame buffer. All positions still derive from recognised pixels and retain
native frame/time/config metadata. GET returns all same-type/digit positions;
tracking refuses ambiguous duplicates. Private schema8 and QRP3 transport,
host commands/client, consumers and tests are upgraded together. The sole
normative protocol is README §7–8 and perception_pkg.sv.

During implementation, targeted run024944 passed CDC, collision, calibration
and pause benches individually but its aggregate remained FAIL because the
query-store source changed during execution. Final frozen-source evidence must
be recorded separately; no partial run certifies a later binary.

### Current-source completion record

Checkpointca5dc67d completed publicv3/private8 and colourAlgorithm3/RUN2,
reader5. SourceSHAca5dc67d6d53b412ddaf23254194d0c16e5bf16107c517609f8d7c4b91211de9;
SOFSHA93e52e763b1de1582aebf7a92e7d7e207c0f9dafd9b2ea47d4e0afbf218b2217.
MODEL20261103T030213_630482Z_test passed283tests plus counterfactual groups.
The frozen37-bench ModelSim suite030213_680753 passed in21min34s, with no
source drift. R6 clean Verilator5.050 passed six production/module benches and
caught the deliberate early-lock mutant in108.125s (025433_037716).
Query-store standalone validation passed1313checks/43queries/107packets;
the new core query test passed17checks/13packets using explicit reader-result
injection, not camera pixels. A VGA fixture that still sent schema7 while
expecting a schema8 BJ label failed025428, then was corrected to use current
package constants and passed; production VGA logic did not change.

Quartus build025754_918086 passed in18min08s plus23.703s extra timing audit.
The correct top/device fitted: adjustedALM27542/32070 (86%), physical placement
32070/32070, with5380ALMs estimated recoverable by dense packing; this is not
an out-of-capacity result. Registers37140,349M10K,47DSP,2793072memory bits.
Query descriptors mapped to exactly2M10Ks as48×49 simple dual-port synchronous
RAM (unused64-bit padding optimised away), not an array of reset registers.
Worst four-corner setup/hold/recovery/removal slack2.678/0.118/25.222/0.477ns;
all72timing/constraint checks and four-corner63/63synchroniser coverage passed.
Request CDC covers24bits; resultToCamera covers1601endpoints; display796 is
unchanged. Every changed endpoint is within intended protocol/debug fields.
Independent warning/resource review found no new unexplained warnings or
pending exceptions. Full compile reported100warnings, all retained/reviewed.
Numeric MTBF remains NOT_ASSESSED. The debug frozen-bank clear adds noticeable
logic; a read-masking optimisation was analysed but deliberately not applied
to this passing source.

Program031717_832062 passed on the same uniquely discovered DE-SoC[USB-1]
FPGAindex2 (0x02D120DD), with actual ca5dc67d/schema8/public3 readback.
Fresh frame270 in031731_104872_capture passed CRC/same-frame/model comparison,
but **did not pass full-sheet recognition**: actual SW8 was1 (bbox bypass),
SW9 was0, config1, red1 and a top blue sign were clipped. Only blue5 was
accepted in that frame; calibrated0/BJfalse. This image is different from the
earlier fixed-scene truth and must not be scored against frame30158's regions.
The user was asked to return SW8/SW9 down and bring the full signs into view.

Real query smoke031934_markers returned the actual blue5 observation. Subsequent
BLUE_BAY/5 SELECT, GETblue5 and GETBJ passed public transaction checks: tracking
tag2 stayed unchanged through query tags3/4, blue5 remained locked, and missing
BJ produced a sole zero-measurement QUERY_NOT_FOUND packet. Details are in
build/member_b/ca5dc67d_initial_query_smoke.json. This is partial-scene interface
evidence, not a ten-sign, red-function, calibration or arbitrary-lighting pass.
R7 recorded-frame270 normal and bypass RTL/model comparison032112_857697 passed.
Normal-model investigation separately exposed an adjacent-card anchor ownership
failure: blue2/3/4 can include the next sign's white anchor and reject ambiguity.
Its cause is separate from the clipped red1, actual SW8 setting and prior1×3
anchor limit; no physical normal-mode success was claimed for this new pose.

README §7.10 was expanded after the user requested clearer parameters: every
command, valid type/digit combinations, GET=3 versus REFERENCE=3 versus F=15,
transaction tags, target substitutions, return codes, coordinates and executable
Python imports are explained in both languages. Independent implementation
review corrected readiness semantics, report-reason priority, query preservation
of tracking and the absence of an implemented run-time default-restore command.

### 2026-11-03, reader6 and command explanation follow-up

The source now identifies readerAlgorithm6, while retaining publicv3/schema8
and colourAlgorithm3. A white anchor component must have its exact doubled
bbox centre within its original measured candidate bbox. Full containment
was rejected experimentally because it lost17 previously accepted real
observations and four synthetic ones. The centre rule kept every previous
accepted candidate's bbox/type/digit/quality/orientation in33recorded-image
profiles:272 to274 accepts, restoring only frame270's blue3/4. These are
replays of preserved camera images, not33new independent acquisitions.
Frame270's blue2 still rejects UNKNOWN_PATTERN/ABDG; its actual E stroke
exists, but the estimated quad puts most samples outside it. No digit or
orientation is guessed. The clipped red1 remains a separate physical-input
blocker. Evidence: build/member_b/reader6/real_matrix.json.

The native RTL latches the34-bit owner bbox with its quad and compares10-bit
X/9-bit Y doubled centres before rounding. Targeted RTL passed18independent
edge/half-pixel/ownership cases,42anchor ROIs,131072division checks and
524288clipping checks. Three reader vectors (real frame270 and two explicit
own/neighbour-anchor counterfactuals) passed8960sample-coordinate comparisons.
Frame270's reader-only latency was282418cycles/5.648ms; this is not capture
or end-to-end latency. Evidence: reader6_targeted/result.json.

Versioned exports use MODEL_8, PROJECTIVE_VECTORS_5 and NATIVE_ANCHOR_VECTORS_2
(24words, original bbox appended). Historical reader5 keeps its original
models/formats and full-reader RTL replay explicitly sets
ENFORCE_OWNER_BOUNDS=0; reader6 uses1. Current shared-pool RTL does not pretend
to reproduce earlier/split-pool architectures. Host decoding fails closed
for unsupported combinations.145related HOST tests passed, including reader6
CLI propagation, unchanged historical5 and interface-profile drift rejection
(reader6_host_validation/result.json).

The previously reviewed QRP3 resource optimisation is now implemented: eight
packet words are stored, and the unused tail is masked to zero at the32-bit
read port. It avoids clearing88stored words on every query response. Debug
tests explicitly read every tail word after each of16packets and verify that
a subsequent status freeze restores all96words. Both debug/link benches passed
034008_295970. This changes no public or private wire format.

Source9070d1ed (SHA9070d1ed03edaa301cb43f823e211fed01cbc865a463f2d5fcb9ec35ed9a5193)
is under final37-bench simulation and Quartus build034215_716773. Full MODEL
034125_979536 passed310tests in268.007s, plus counterfactual groups; R6 clean
Verilator5.050/Bash034126_392190 passed six benches and caught the intended
early-lock mutation in112.172s. These are not fitting or board claims.

README7.10 now explains every command, all four request fields, valid selectors,
GET versus SELECT, JSON return interpretation and parameter substitutions.
Independent review checked seven real CLI help invocations and Python/RTL
signatures (reader6_host_validation/readme_7_10_review.json); all passed.

The completed checkpoint is recorded below. Microphone input remains deferred
by the user. Human ownership/sign-off, numeric physical operating ranges,
remaining relevant AI conversation exports, new occlusion/lighting tests and
whole-team integration remain separate responsibilities.

### 2026-11-03, reader6 completed board and interface validation

Source9070d1ed completed all37 ModelSim benches with no source drift
(034125_931495). Build034215_716773 passed in1105.766s plus26.406s explicit
timing audit:27071/32070 adjusted ALMs,37253 registers,349/397 M10K,
47/87 DSP and2793072 memory bits. Worst accepted setup/hold/recovery/removal
slack was2.601/0.107/25.034/0.442ns. All72 timing checks and63/63 synchroniser
chains at each of four corners passed; quantitative MTBF is NOT_ASSESSED.
The100 normalised warnings matched the previous reviewed checkpoint; none
were newly unexplained. Query storage remained two M10K,48×49 useful bits.
The query-tail read mask reduced memberBDebug total ALUT2287 to1005.

SOF SHA256 is725882cfe7bf547acdb3da3c3a5e7a5066d19bf181fca0c904d022dc3042da6d.
Program040143_422680 selected the discovered DE-SoC USB-1 FPGA, verified the
same target identity and read back9070d1ed/public3/schema8. Capture040119
correctly failed before programming because the new build manifest and old
board differed; that failure was retained. Fresh capture040200_186255 produced
real frame364,config1,ten accepted printed digits and one uniquely paired BJ.
Its PNG, hash, origin, profile and independently reviewed host-only regions
are retained under tests/fixtures/camera/frame364. Paper edges touch the image;
this is not a claim that every physical sheet edge is visible. R7 replay
040546_827101 compared these actual pixels/profile with both RTL modes.

Three real recalibrations040344_444187,040348_656946 and040353_069673 passed
eight-sample commits and busy-request rejection, advancing config2/3/4.
Board-time poll upper bounds were580208,604969 and532525us; these are
conservative command-to-observed-completion bounds, not exact red1 onset
latencies. Last hardware sampling recorded252 red/504 blue pixels; a later
same-image model measurement of288/492 uses a different ROI/time and is
explicitly separate. Raw RGB validation does not imply AWB/AEC lock.

The real publicv3 interface test040433_321702 passed LIST, typed GET,
red1/red2/BJ SELECT, blue1/2 duplicate ambiguity, CLEAR and unaffected tracking
requests during queries. It held a query under backpressure while camera
frames continued and a genuine calibration committed config4 to5: held
payload/time/config remained unchanged, then a new query returned the new
configuration. All issued requests, responses and profile identities are
recorded by tools/validate_member_c_interface.py.

Normal hardware trials040656_032083 scored900/900, then SW8 bypass trials
041414_952228 also scored900/900, both three trials of30 distinct fresh frames
with ten signs. The first comparison was INVALID_COMPARISON because the host
runner changed. Normal trials were therefore repeated using the identical
frozen-checkpoint wrapper:041845_157073 scored900/900, zero wrong IDs/misses/
outside-region results. reader6_sw8_comparison_repeated.json is valid; both
modes pass. This scene demonstrates the physical bypass mechanism but does
not demonstrate an accuracy advantage or necessity for the normal algorithm.
These are sampled frames, not a claim about every intervening frame.

The user confirmed all four SW0/SW1 combinations and BJ, then confirmed that
SW0=SW1=SW9=1 shows only the camera. The later actual readback already had
SW9 down, and blue3 requestTag75 was locked again at frame44819/config9.
reader6_raw_user_confirmation.json distinguishes USER_REPORTED_PHYSICAL raw
display from the hardware-confirmed restoration; no raw-up status snapshot
was captured in this transition. No physical switch was simulated by the PC.

### 2026-11-03, reader7 main-colour ownership and overload investigation

Source7408a02d1009327f790bf246331e7f718f4671ba9f3998233ce07374ffb51ef9
keeps public3/schema8/colour3 and identifies reader7. Frame270's blue2 contained
a real three-pixel E stroke, but raw pixels belonging to the neighbouring blue4
pulled its estimated lower corner from[244,61] to[244,72]. Taking supports from
the unique largest four-connected raw-colour component restores seven of
seven E samples instead of one of seven. The component bbox must match all
four original candidate edges; ties, mixed bounds or active-label overflow
reject. Area is never used to assign a number. SW8 skips this additional scan.

mainColourSupportReader uses eight active labels,320×4 synchronous line RAM
and128×28 synchronous support RAM. Targeted RTL passed565 cases/13689 checks,
including512 small topologies,27 external vectors, merge/retirement/ties,
overflow, held inputs and reset. A union-support-loss mutant was caught by
the intended support assertion; ModelSim's raw exit0 was correctly converted
to failure by the wrapper. Full-reader integration passed normal/bypass and
historical reader6; maximum measured reader-only processing on these vectors
was1319652 cycles/26.393ms, excluding acquisition. Historical algorithms remain
explicit and are not silently reinterpreted.

MODEL042234_461679 passed341 tests plus counterfactual groups. Separately,
410 synthetic cases preserved295 prior accepts and had zero false accepts
among236 negatives. Across33 recorded-image profiles accepts rose274 to275,
with no lost IDs/orientations/bboxes. The strict all-field equality comparison
remains FAIL because an existing blue3 quality increased192 to255; the separate
non-regression assessment explicitly permits that improvement. These are
recorded-camera replays, not new board captures.

R6 run042119_525858 failed on the old continuous-frame test at frame3. An
independent ModelSim trace confirmed that its17.1609ms source period, which
omitted skipped sensor-row time, delivered frame3 at34.323470ms while the two
banks were READING and READY. The core correctly rejected the entire incoming
frame; at51.483070ms it published frame3 as bad/resourceDrop with zero matches.
The previous assertion incorrectly required every such frame to be observed.
The in-progress larger simulation042108_403104 was explicitly INTERRUPTED,
not reported as passing. Verification now separates a free-running40ms source
representing the measured camera from the original17.1609ms overload, retaining
drop/ownership/backpressure checks and requiring fresh three-frame relock after
recovery. No ready feedback is added to the simulated camera.

Build042031_633519 passed full compilation and the explicit four-corner timing
gate at04:40:52UTC. Source7408a02d binds SOF SHA256
0ebb6a4849cd1f5e9499cca80929ee198682cc3f287e72ea1defc11663c23a39.
Fitting used27810 adjusted ALM,38002 registers,351 M10K and47 DSP. The new
supportMemory128×28 and lineLabels320×4 each occupy one physical M10K, rather
than a register array. Full compile took1190s; fitter itself10min36s, with
placement and routing successful. This was active computation, not the earlier
memory-starved stalled build. All100 warnings match the previous reviewed
normalised set; full timing details remain in the source-bound result.

The detailed placement table displays32071/32070 ALMs while the root entity
table reports32069.9. Both values are retained in main_colour_resource_review;
local Quartus18.1 help documents proportional attribution of shared ALMs across
entities but does not establish the exact integer summary rounding formula.
FIT succeeded without an overuse error. This accounting difference must not
be presented as one extra physical ALM or hidden as spare placement headroom.

The revised cadence tests passed four independent ModelSim modes: continuous
40ms,17.1609ms overload followed directly by40ms recovery, truncated-frame
recovery, and protocol collision injection. The overload produced exactly two
whole-frame input drops and two stale-result rejections; the next request's
three new frames locked only on the third. Dropped frames wrote zero pixels;
admitted frames wrote exactly76800 sequential addresses. Stalled reports did
not change. Evidence:core_cadence_validation/summary.json. The production RTL
did not require a scheduling change.

Course R6 rerun043842_301612 passed all eight module/system benches and caught
the deliberately early-lock tracker mutation in228.031s, below the300s rule.
It includes both normal and overload system tests. Nine host runner tests
separately passed and guard against silently dropping either scenario. The
39-bench ModelSim development regression043535_957637 is still running;
programming and fresh reader7 camera evidence remain pending at this entry.

### 2026-11-03, reader7 completed checkpoint and two photographed poses

The previously pending development regression043535_957637 completed at
05:10:31UTC with39/39 ModelSim benches passing. Together with R6
043842_301612 (eight system/module benches plus the rejected early-lock
mutation), this completes the recorded simulation checkpoint for source
7408a02d1009327f790bf246331e7f718f4671ba9f3998233ce07374ffb51ef9.
Build042031_633519 passed fitting and the explicit final four-corner timing
gate; its SOF SHA256 is
0ebb6a4849cd1f5e9499cca80929ee198682cc3f287e72ea1defc11663c23a39.
Program044313_012680 succeeded on the discovered DE-SoC USB-1 Cyclone V
target and verified build7408a02d/public3/schema8. This is reader7 board
evidence; later reader8 model defaults do not relabel it.

Fresh capture044324_762472 produced frame241. Its two extra blue1/2 signs
had moved approximately30 pixels relative to frame364, so the earlier frozen
frame364 predictions are retained with an explicit scene-condition mismatch.
They are not retrospectively claimed as predictions of this changed pose.
Three recalibrations044349_203668,044421_302088 and044426_305022 passed;
the observed board-time completion bounds were592011,580674 and600539us.
The publicv3 interface test044436_346297 passed41 checks. R7
044627_573160 passed both RTL modes on the exact frame241 capture.

The corrected, independently labelled frame241 truth regions were used by
normal run044951_489860:900/900 printed digits, zero wrong IDs,90 current
reports and99 distinct observations including request transitions. Its maximum
board capture-to-completion latency was65.417ms. The preceding truth-v1
run044701_227993 remains retained; the v2 correction removed an overlapping
score-region edge and did not retrospectively replace that run's inputs.
The matched SW8 bypass run045104_494342 also scored900/900, with91 total
observations and45.580ms maximum latency. reader7_sw8_comparison.json is
COMPARISON_VALID under the user's unchanged-scene attestation. All four
SW0/SW1 combinations were confirmed physically by the user. Neither these
scores nor that confirmation proves an accuracy benefit from perspective
recovery or substitutes for a reader7 SW9-up hardware snapshot.

The subsequent physically rotated pose is a separate eight-sign scene,
retained as frame15078. Normal run045611_428051 scored717/720, with three
missing printed observations and no wrong IDs. Its strict hardware result is
FAIL: four of95 retained observations failed, including one unreliable or
unlocked target report. Maximum latency was58.494ms. Matched bypass
045949_085041 scored720/720 and passed, with44.143ms maximum latency.
reader7_rotated_sw8_comparison.json is a valid comparison containing that
normal-mode failure; it is not converted into a pass because aggregate
recognition exceeds95%. These results do not demonstrate an R9 digit benefit
for the normal algorithm. A later bounded search saved30 distinct fresh
images, frames32136..38058, all with blue6 accepted and no frame/overflow
failure. rotated_failure_capture/result.json correctly records
NO_FAILURE_CAPTURED_IN_BOUNDED_RUN. It neither erases the earlier failures nor
supplies a captured blue6 failure image for a claimed repair.

### 2026-11-03, reader8 projective calibration development, not yet board evidence

The rotated frame15078 exposed a separate calibration limitation. Red1's
bbox[117,1,176,87] and its blue reference bbox[115,81,170,105] have native
axis gap-7 pixels even though the strip is correctly below the slanted card.
The old axis-aligned blue inset also includes white/background pixels:
495 raw samples have B minimum57 and other-channel maximum174, so purity
fails independently of the pairing decision. Merely loosening the gap test
cannot provide valid calibration. The stored diagnosis remains under
rotated_calibration_15078; it is recorded-pixel analysis, not a new commit.

Reader8 preserves reader7 digit, anchor, ownership, white and colour3 rules.
It adds same-frame measured quads for calibration, allowing a blue strip with
a four-pixel bbox minimum to publish geometry while retaining the numbered
card's24-pixel edge and400-pixel area gates. SW8 bypass publishes no such
quads. Default host MODEL/export metadata now names reader8; explicit
readers1..7 retain their historical behaviour and version IDs. Nine exported
frame15078 digit/map/mask/candidate files were byte-identical between7 and8.
The thin-blue synthetic test remains UNKNOWN and never becomes a bay.

The new maintained geometry oracle uses forward homographies, canonical
scale320 and exact floor-Q4 coordinates, including negatives. It compares the
formal strip projection with the actual component under a scale-based corner
budget, edge ratios and forward half-plane bounds, requires unique cyclic
matching, and samples each object's own inset polygon. Blue sampling order
follows the winning cyclic correspondence. No inverse matrix or new RGB frame
buffer is required by this design. The initial nearest-Q4 experiment remains
separate from the new floor-Q4 results.

The floor model preserved30/30 old valid real profiles, produced31 raw-pure
pairs, rejected all215 neighbouring bays even when their accepted flags were
removed, and rejected six wrong-reference geometries. Of540 controlled
rotation/perspective/scale geometries,536 passed; four small projected-gap
collapse cases remain conservative rejections. Five raw-colour contamination
cases and the15-sample negative were rejected. Model sampling of frame15078
suggests blue floor28 instead of33. In the RGB565 input representation there
is no blue-channel level between24 and33, so this floor change alone changes
no pixel classification; it is not a digit-recovery claim.

Targeted host/model validation passed46 tests, and14 focused historical
tests passed after making the current8 and historical7 defaults explicit.
The817-record geometry vectors retain valid, invalid, rounded-degenerate,
extrapolation and cyclic-order cases. RTL integration, complete current-source
regression, fitting/timing, programming and new calibration-camera validation
are still separate gates at this entry. Reader7's fitted/programmed evidence
must not be presented as reader8 completion. Microphone input remains deferred.

### 3 November 2026, 05:49–06:08 UTC — configuration fix, full-core replay and fit failure

The complete MODEL run `20261103T054332_443689Z_test` passed355 tests and the
counterfactual entry. Its preceding failures concerned stale default-version
assertions and a missing datasheet description; those failures remain recorded.

An independent RTL probe found that the eighth old-version calibration sample
could coincide with a mode/configuration change and later request a commit.
`reader8_geometry_port_validation/config_boundary_result.json` retains the FAIL.
The repair binds a complete attempt to `attemptCfgVersion`, rejects changed
versions through WAIT/COLLECT/VALIDATE/COMMIT and immediately gates collection
and commit. An acknowledged commit is final. Pending SW8/orientation changes
also take priority over an old-profile commit at the core SOF boundary.
Updated interaction tests and the original counterexample passed ModelSim;
core calibration passed318 checks, including3px versus49-Q4 movement,
unchanged old thresholds and no false acknowledgement on mode switches.
See `reader8_geometry_port_validation/receipt.json` for source/log hashes.

`perception_calibration/perceptionCalibration_tb_verilator/result.json` passed
52 frames derived from the single actual frame15078:116 checks,18 raw-RGB
sampling frames, three terminal events, one SOP commit and SELECT1–6 each
locking only on its third new simulated observation. Permission revocation
and configuration changes retained the old48/20 profile; a fresh eight-frame
window committed37/28. Each sample contained177 red/272 blue pixels using
the reset/default-derived geometry. Earlier177/274 model samples used a
different profile. CSV files preserve samples, events and reports. This is
RTL_SIM of repeated recorded pixels, not52 independent camera acquisitions.

Source645102d6 SHA256 is
`645102d67d5e166d4298fb8ca5d79464a5a0ddc82524fcad05c13b905b6d7a9e`.
Actual R6 passed eight benches plus the caught early-lock mutant in255.766s
(`20261103T060008_784610Z_verilator_course`). An earlier loaded-machine run
exceeded300s and remains FAIL. The runner now reuses an identically compiled
core only within the current clean run, with binary/source/tool hashes and
separate continuous/overload simulation logs;13 HOST tests cover this change.
It never loads a previous run's binary or relaxes the300s gate.

Full build `20261103T055358_022378Z_build` FAILED placement preparation:
Error170012 requires3374 LABs, but the5CSEMA5 has3207. The incomplete-fit
estimate is33142 ALMs (103%),39589 registers and57 DSPs. These are not
completed timing/placement results. MAP correctly inferred16×88 geometry
storage as M10K. No SOF from this attempt was programmed. The earlier
e6a60680 build was interrupted for the proved configuration bug. Interrupted
full ModelSim runs retain partial results and interruption records, never a
full-suite PASS. VGA storage/control resource reduction is in progress; the
board still runs the successful7408a02d checkpoint.

Fresh frame45625 (`20261103T055719_167964Z_capture`) passed CRC, same-frame
and glyph checks with no candidate overflow, but rejected blue6 with reason4.
Its strict-white anchor is a closed1×3 component with three pixels; only the
two-column requirement fails. Adjacent unsaturated edge pixels fall below the
strong-white threshold. This differs from the earlier unrecorded uncertain
stroke/split refusals. Exact PNG/profile: `tests/fixtures/camera/frame45625/`.
A conservative strong-seed/weak-support model restores this example, but is
not yet a production RTL or camera fix. No global white threshold was lowered.

中文记录：真实图回放已验证许可撤销、版本切换拒旧、八帧采样、原子提交和
蓝1–6三帧锁定；R6实际入口通过，但拟合因LAB超限失败，尚未下载。
新实拍已保存蓝6锚点只剩一列的拒识反例。资源优化与锚点修复分别验证，
MODEL、RTL_SIM、失败拟合和真实相机证据不能相互替代。

### 3 November 2026, 06:09–06:33 UTC — generic anchor recovery and resource reuse

Fresh recorded frame63647 (`20261103T060920_641543Z_capture`) retains another
reader7 anchor refusal. Its full blue6 box remains[264,176,296,236]; an extra
inner blue island is not the earlier unrecorded split-card failure. Both
frame45625 and63647 are preserved with original pixels/profile in the small
camera fixtures. No historical result has been relabelled as reader9.

Reader9 adds one general rule, shared by every red/blue digit and rotation.
All four strict-anchor hypotheses run first. Zero strict matches, no hazard
and exactly one closed thin strong seed permit one additional scan through
the existing native component engine. Its complete weak support must retain
every seed pixel, contain no foreign strong pixels and pass the original
closure, size, area and ownership conditions. True strong count is retained;
fallback quality is capped at192. SW8 and historical reader profiles keep
strict behaviour. There is no blue6, slot or scene-position branch.

Final native source SHA256 is
`943f3330ac0550168c76ad30b8d5a90abcc8f27cdae4768ffdd4a0eae7f8348c`.
Actual component RTL passed73 cases/1193 checks, including27 supports,
14 refusals, two overflows and one ambiguity. Strict old/new cycle comparison
passed1868 ROIs and7,288,257 cycles, including overflow/ambiguity. A deliberate
foreign-strong mutant failed as required; the checked runner propagated a
nonzero result despite ModelSim's raw `$fatal` exit behaviour. Independent MAP
estimated1434→1589 ALMs,2228→2492 ALUTs,1196→1390 registers, with1280 RAM bits
and10 DSPs unchanged. These are isolated synthesis estimates, not full fitting.
Receipt: `build/member_b/native_anchor9/review.json`.

MODEL preserved all old decisions across33 recorded profiles/330 ROIs and
410 synthetic cases/577 ROIs: zero lost/changed IDs, changed qualities or
negative false accepts. Eleven added host tests cover32 formal type/digit/
quarter-turn combinations and explicit counterexamples. The current-source
targeted actual ModelSim run `20261103T062653_461164Z_test` passed11 normal and
11 bypass cases, including both real failures, strict-priority/multiple-seed/
foreign-bridge negatives, four type/rotation examples and unknown/deleted
anchors. Normal mode recovered the two real blue6 anchors; this is RTL_SIM
using recorded pixels, not new CAMERA_HW. Full43-bench regression is separate.

VGA diagnostic work/published records now use a three-bank synchronous M10K
store; displayed records remain stable during serial loading and SOP
preemption. Actual old/new pixel and handshake equivalence passed3,944,178
pixels. The enhanced bench exercised2214 writes,46 load preemptions and17
cycles with all three banks owned. Independent same-settings MAP estimated
9908→7332 ALMs,9747→6189 ALUTs,6517→4016 registers; it inferred96×77bits of
M10K, with20 DSPs unchanged. Pipeline/SW9/arithmetic tests passed in
`20261103T061918_135877Z_test`. No display function was removed to save logic.

Current full build `20261103T062826_889919Z_build` uses source
`c63c9edbbd669744c7dee86f060352bf48ff9557bb0989f8084091860e4691d2`.
At this entry it is RUNNING, with the old7408a02d still programmed. A successful
isolated MAP or pixel replay is not evidence of final fit, timing or VGA
hardware. The complete flow, new SOF identity and fresh camera tests remain
required. The maintained inventory now covers230 files and43 RTL benches;
structural validation passed and human R8 sign-off remains pending.

中文记录：按用户要求采用通用判断规则，分时复用原扫描硬件；蓝6实拍只是
反例输入，不是专用识别分支。旧严格路径逐周期等价通过，薄锚点补查及拒识
反例实跑通过。VGA面板改用同步RAM，新旧逐像素一致，独立综合减少逻辑。
完整新工程仍在构建，不能将这些结果称为已经下载或相机验收通过。

### 3 November 2026 — final scope freeze and remaining blue6 failure

The user requested that blue6 instability be deferred and that work close
after one final programme. Production source remainsc63c9edb; no threshold
or recognition changes were made in response to the following new frame.
Fresh frame30321 (`20261103T063047_128847Z_capture`) still came from7408a02d.
Its blue6 raw HSV region is already fragmented:26 components, largest410px
ending aty210; cleanup leaves331px ending aty207. Of1459 hue/saturation-blue
pixels,881 fail the current value33 gate;501 lower-half pixels have expanded
blue24. A28 floor produces the same quantised mask. Diagnostic20/24 models
recover the sign, but these are not calibration or hardware acceptance.
Lighting/AGC/AWB/pose causes remain unisolated. The image is retained as
`tests/fixtures/camera/frame30321/`; its PNG SHA256 is
`4516b99ec2508b5ae170526397e9a7dff1836633b0ac8401395cb1b0558abb93`.
This upstream failure is separate from the two recovered thin-anchor inputs.

Final MODEL `20261103T063253_699527Z_test` passed370 tests in273.388s plus the
independent counterfactual command. It used an explicit900s host-run timeout;
the first default300s timeout remains FAIL. The course R6 budget was not
changed: run062658 passed its first seven benches but hit300s during the
last compilation, so its final bench/mutant did not execute and the aggregate
remains FAIL. Historical source645102d6's255.766s R6 PASS is not a current
source PASS. The broad current43-bench ModelSim run062727 was intentionally
interrupted after eight completed benches to honour the close-out scope;
its partial results/interruption record are retained. Current targeted
normal/bypass/component/equivalence proofs remain individually valid. The
existing52-frame changed-core test is being completed using Verilator,
separately from the course300s claim.

The pre-programme prediction was frozen at06:34:11UTC in
`reader9_predictions/predictions.json`, SHA256
`a5ed8fd0bbb688e2e4b2c6ce2d920347c2bfa3f9ebeb233ccc157fe09062ba24`.
It records design expectations, not measurements. The separate condition
assessment flags frame30321's slight pose/photometric change. No final90-frame
trial, SW8 advantage or new physical VGA confirmation is implied by a single
close-out capture. Those checks are deferred rather than silently passed.

中文记录：用户要求蓝6问题暂缓、最后一次下载后收口，源码冻结。
370项MODEL通过；R6本轮因300秒总限时失败，不能引用旧版本成功代替。
完整43项ModelSim按收口范围中止并保留已完成八项，针对性仿真单独计证。
本次仅完成最终构建、下载和新帧必要核验，不再安排三轮/开关对照实验。

The current-source52-frame Verilator integration subsequently PASSED:
19.219s compile,258.016s simulation,116 checks,18 accepted raw-sample frames,
three expected events and one atomic commit. All SELECT1–6 lock sequences
were0,0,1 on their three new simulated observations. Source hashes matched
thec63c9edb build throughout. Exact result SHA256 is
`b34358caeb4d45dc1e2cf49bba5d992455fabe15648f21a12e6efe1a61c92209`,
at `reader9_calibration/perceptionCalibration_tb_verilator/result.json`.
CSV samples/events/reports and evidence.json preserve each transition.
This repeats recorded frame15078 with report-paced input; it is neither
52 independent camera acquisitions nor a course R6 aggregate-budget PASS.

### 3 November 2026, 06:50 UTC — final programme and close-out

**Final source:**
`c63c9edbbd669744c7dee86f060352bf48ff9557bb0989f8084091860e4691d2`.
**Final SOF SHA256:**
`3e4f572055f63c02436608623a7994fbf5d840cccc13ba7b8e5c11bca2524d1d`.
Build `20261103T062826_889919Z_build` PASSED the complete Quartus18.1 flow
in1267.797s, followed by27.453s explicit timing/CDC checks. Fitter finished
at17:47:18 Sydney time:29133 adjusted ALMs,40579 registers,356/397 M10Ks,
57/87 DSPs and2806736 block-memory bits. The placement column is32069.1
ALMs: the adjusted91% figure is not spare placement capacity promised to C.
The integrated core hierarchy uses20009.5 adjusted ALMs,49 M10Ks and33 DSPs;
this is not a separately fitted C-integration budget. VGA diagnostics now
use3945.2 adjusted ALMs and two M10Ks. Geometry and display stores inferred
real synchronous RAM.

All72 timing checks across four corners passed; worst setup/hold/recovery/
removal slack is+2.139/+0.118/+27.361/+0.393ns. Illegal/unconstrained clocks
and input/output paths are zero. All63 expected synchroniser chains appear
at each corner; MTBF acceptance remains NOT_ASSESSED.100 compiler warnings
were retained and reviewed: after source-path/line normalisation, there are
no new warning descriptions relative to7408a02d. The unchanged bounded
index/truncation/shift and signed-minimum sentinel warnings are explained
in `reader9_closeout/warnings_review.json`; no warning suppression or new
false path was added.

Programme `20261103T065044_691029Z_program` successfully downloaded the new
SOF **once**, to the discovered `DE-SoC [USB-1]` FPGAindex2,
`5CSE(BA5|MA5)/5CSTFD5D5/..`, ID0x02D120DD. Exit0 and board readback both
confirmed buildc63c9edb/public3/schema8. No persistent flash or Git remote
write was performed.

Fresh capture `20261103T065056_662337Z_capture` PASSED new-transaction,
CRC/schema, same-frame and all nine candidate pixel/model agreement checks.
Frame251 uses reader9/colour3, SW8=0 and SW9=0. All eight formal digits
(red1/2, blue1–6) were accepted; the uniquely paired BJ strip is valid with
quality255. Eight raw-RGB sampling frames completed automatic calibration:
cfg1, red33/blue28,204 red samples and324 blue samples; the last sampling
frame20 passed sampler/frame/pairing/geometry/window checks. Success event1
was issued at785857us. The capture spans9942193→10001632us, giving59.439ms
on the same board timebase. The event time is not an arm-to-commit interval.
Interaction is idle/armed, busy0, audioReady0. Current frameGood1 and
candidateOverflow0 coexist with the retained transport fault bit and two
startup drops; no zero-drop continuous-run claim is made.

The genuine image and acquisition identity are preserved as
`tests/fixtures/camera/frame251/`, PNG SHA256
`1d92356cf81fe7ac2e166b03ccc4d10fd45761f28ab14f33735b25425d574089`.
The final pose differs from earlier reference frames; no historical truth
regions or multi-trial scores were reused. One successful frame does not
resolve blue6 instability. By explicit user direction, this is the last
programme and development stops here: no new SW0/SW1/SW8/SW9 physical
confirmation, final90-frame trials, current41-check C bench or microphone
test was claimed. Historical tests remain available with their real sources.

Close-out materials are `reader9_closeout/receipt.json`, the source-bound
one-page `member_b_datasheet.pdf` (three-trial measurements explicitly
PENDING), and `member_b_ai_statement_draft.pdf` (student review unsigned).
The visible-message AI transcript is a read-only export of the identified
session; it excludes private reasoning/system/tool content and does not
claim to cover every project conversation. These local files are not a
Canvas submission. The final source/SOF hand-off archive is
`build/member_b/member_b_c63c9edb_closeout.zip`; its generated manifest records
relative file hashes and the exact SOF/source binding. No compiler database
or personal toolchain is included.

最终中文交接：c63c9edb已通过完整构建与四角时序并最后下载一次，板上身份
已核对。新frame251识别红1/2、蓝1–6及BJ，自动八帧校色提交cfg1/R33/B28，
单帧处理延迟59.439毫秒。蓝6稳定性按用户要求暂缓；当前R6总限时失败、
完整43项仿真中止及最终物理开关/三轮验收未执行均已明确记录，不能称全部
课程验收完成。README、OWNERS和本版本记录为维护入口，麦克风继续暂缓。

Read another fresh image without rebuilding/downloading / 继续读新图、不再下载：

```powershell
& 'C:/Users/15402/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/echo7.py --quartus-bin 'C:/intelFPGA_lite/18.1/quartus/bin64' --timeout 120 capture --fresh
```

## 2026-11-04：ECHO-7 整机修复与现场迭代

本次从 `github_publish/MTRX3700_MajorProject` 的 `dc1db23` 继续开发；外层旧工程及其
未提交 QSF 修改未覆盖。用户要求“主要功能一定实现、需要实机纠正、可以保留部分缺陷、
不过度跑”。因此先恢复同一生产顶层的真实视觉—控制—UART 链，再用有限的定向仿真、
完整 R6、Quartus 构建和架空实机逐层核验。后续用户明确追加红2启动、R6 285秒目标、
详细中英 README 与推送仓库要求；这些追加要求覆盖此前对应的收口安排。

### 版本与证据总览

设计build ID与CCTL接口版本是两个不同标识：以下设计为`E7070002`至`E7070008`，
接口仍为`E7070001`，不能把固定接口版本当设计版本。005已完成本版构建、R6及实际下载/读回，运动与整圈覆盖按末节实际记录分别判断。

| 设计版本 | 本轮主要变化 | 对应该版的自动验证 | 对应该版的真实板卡结论 |
|---|---|---|---|
| E7070002 | 集成 B/C、三模式、CCTL、完整安全链、红2重新选择、分页候选诊断 | Full Compilation 1203.431秒 PASS；R6 245.451876秒、12 PASS + CAUGHT | 21:23 AEDT 下载/读回成功；合成左中右、租约失效、预算结束、真实 IR 和轮向通过；真实蓝1可锁定，但后续候选溢出暴露健康资格永久阻断 |
| E7070003 | 将历史候选溢出诊断与当前健康资格分离；坏帧后建立新边界并等待三相邻新好帧 | 控制236检查 PASS；R6 221.258456秒、12 PASS + CAUGHT；Full Compilation 1154.491秒 PASS | 22:02 AEDT 下载/读回成功；保留历史flags=3仍恢复健康和锁定，无需复位；23个真实不同帧、22次锁定；真实红2暴露“启动早于第三帧锁定”问题 |
| E7070004（此前实板版本） | 未标定 INTEGRATED 红2必须等新请求目标完成三帧锁定后才启动；健康无目标不能提前消耗授权 | 控制254检查 PASS；R6 219.556074秒、12 PASS + CAUGHT；Full Compilation1121.141秒及门检25.868秒PASS | 22:31:50 AEDT下载/读回成功；真实红2新选择→新锁定→ARM/ALIGN通过；用户确认实物启动及蓝1脱离后停车，末VISION_ONLY/未ARM/左右0；后续地面首轮约75°后无效测距HOLD，未完成一圈 |
| E7070005（历史实板版本） | 真实左右证据确定旧转向反向，生产TURN_SIGN=-1；用户新要求下正常完整长回波为FAR、异常仍保护；d页FAr及主机分类 | 方向两参数各269检查、12帧pixel-to-UART、完整sonar46检查PASS；首次R6超时FAIL303.500928秒保留，最终13 PASS + 1 CAUGHT/239.403059秒；Full Compilation1173.143秒及门检25.799秒PASS | 01:11:16 AEDT下载/读回E5；蓝1零速8/8锁定、FAR6/6有效无HOLD，d页用户确认；三次满圈13.561176/11.075500/11.436358秒实测，实际设置13.6秒；首轮逆时针，约超10°/5°/45°，前两次起步前冲保留 |
| E7070006（时序验收失败） | ALIGN误差分档3/4cm/s，方向/速度/20–100ms脉宽锁存，转中/跨侧先停车；zeroSent后1.5s及新fence三帧确认 | 正/负各338检查/53UART PASS，5.2128905秒；14帧pixel PASS78.99106秒；完整R6 PASS266.840318秒、13 PASS+CAUGHT；compile工具exit0/1183.703秒，但整体验收因setup −0.265/−0.203ns FAIL | 失败产物未下载；3cm/s起转及1.5s机械停稳未证，不借用E5实物结论 |
| E7070007（历史实板版本） | 只将默认脉宽32位乘法链改为8位误差、10..50截限及17位移位减法；实际速度误差和非默认公式保留 | 256种U输入0差异；正/负各338检查/53UART PASS，5.113292秒；首次词法COMPILE FAIL保留；R6 PASS265.276162秒、13 PASS+CAUGHT；编译1147.755秒/门检26.087秒PASS，setup/hold +0.864/+0.117ns | 下载/读回成功；01/03窗口未ARM、02缠线/HOLD、04/05微动/过冲均未DOCKED；连续合成居中直行基本走直，促成E8 |
| E7070008（当前实板/发布版本） | APPROACH内U75–165连续正向差速，远5/3、近4/3；范围外或350mm偏心先零速/驻留/三新帧，再原ALIGN | 正/负各433检查/88UART PASS；R6 13 PASS+CAUGHT、270.641086秒；编译1159.722秒/门检25.963秒PASS；setup/hold +1.021/+0.121ns | 03:28:58 AEDT下载/读回；首轮已锁定蓝1主机START实相机落地DOCKED，29.315066秒/J3329mm，零速保持3.18423秒及用户前进/位置确认；其余五牌/搜索/POWER/红2待 |

### 第一阶段：补齐控制契约和实际接口

实体 SW0–SW5 改为六位独热选择，20 ms 整组稳定后才接受；无拨码为 NO_SELECTION，
多拨码为 CONFLICT。未 ARM 时仍可 SELECT 和真实追踪。请求通过 ready/valid 握手，
当前正在等待接收的请求不能被新拨码覆盖；选择、配置、源切换和重新锁定均建立 tag/时间边界。
健康新帧、看见目标与三帧锁定分别记录，健康 NOT_FOUND 不再等同于视觉源坏掉。

生产 SOF 内包含 INTEGRATED、VISION_ONLY、CHASSIS_INJECT 三模式。第三种模式只替换
感知报告，沿用真实实体拨码、IR、J3、控制状态机及 UART；主机不能直接写轮速或伪造距离。
CCTL 提供状态快照、模式、START/STOP、注入和扫描参数；注入/调试会话有500 ms租约，
失约取消任务并发零速，恢复心跳不自动恢复旧任务。

运动流程包含有界 SEARCH、停车等待、ACQUIRE 驻留、ALIGN、APPROACH 及终态。
首次发现目标须先确认完整零速 JSON 已发送，再驻留200 ms、建立新采集边界、积累三帧新观测。
APPROACH 远距5 cm/s，500 mm以内3 cm/s，350 mm停靠；250 mm及以下危险/无效测距
进入安全 HOLD，连续三个真实新样本达到300 mm才恢复安全资格。IR A立即锁存停止；
第一次新的 POWER 仅解除 IR，第二次独立新按压才可启动，NEC repeat/持续按住不能算第二次。
这些行为经控制 TB、真实管脚时序模型及后续部分实机验证，证据层级保持分开。

### 第二阶段：用户追加红2、资源超限与有限范围优化

原附件中的红2 NO_ACTION 被用户明确追加需求替换为“重新取当前拨码、重新锁定并开始”。
实现范围为未启动/终态接收红2，活动任务不因反复呈卡重置累计扫描预算。
VISION_ONLY 只重新选择不 ARM；INTEGRATED 在安全条件满足后等待新报告；
CHASSIS_INJECT 不接入真实红2。红2须先移开三健康帧，再呈现三帧，上电已有卡不触发。
STOP、模式、IR、实体选择或安全边界清除旧授权；重新选择不清除已完成的红1校色。

首次构建 `20261104T094653_234340Z_build` 在追加需求后停止，其子流程仍留下
**32238/32070 ALM，无法 fit** 的报告。这不是通过构建，也没有下载该产物。
VGA 候选诊断随后从18组同时存储改为10组：每页8个候选，加中心与参考，
两页覆盖全部16个候选（含拒绝候选），默认每120个 VGA SOP切页，60 Hz下约2秒。
这次只做必要的分页资源调整，保留显示内容、中心关联和单HSV转换器。

主机工具方面，持久 STP 的 stdout 缓冲导致交互响应不可靠，改为显式 flush 的文件响应通道；
同一会话 STATUS/BSTATUS/STATUS 实测43/262/38 ms。Windows Verilator 环境按实际
编译器/DLL路径修正，未以模型或假结果替代 RTL 仿真。

R6 的失败与提速顺序保留如下，输入、断言和故意坏模块检测未删减：

1. 首次串行套件到300秒总限时后清理，实耗303.055秒，9项已通过、其余未完成，结果 **FAIL**。
2. 连续帧与过载两个独立系统场景在同次新编译之后并行运行，290.761秒，完整12项 PASS 和 CAUGHT；
   满足课程300秒，尚未满足用户新增285秒目标。
3. 编译并发 jobs=4 后，E7070002完整干净副本套件245.451876秒 PASS。
4. 每次后续生产 RTL 修正均重新运行完整套件：E7070003为221.258456秒，E7070004为219.556074秒。

这里复用的是**同一次调用**中生成的公共仿真二进制，由独立进程运行不同场景；没有拿上次构建的
二进制冒充当前源码。故意将三帧锁定改成两帧的私有 mutant 被原断言捕获为 CAUGHT，生产源码不变。

### 第三阶段：E7070002 构建、实机与第一个现场缺陷

E7070002 Full Compilation PASS，ALM29417/32070、M10K357/397、DSP51/87，
最差 setup/hold 为 +1.164/+0.078 ns，未约束路径0。21:23 AEDT下载本次新 SOF并读回
E7070002。用户确认底盘架空、SW0单独上拨、红1/蓝1在镜头前。

合成 U=80/120/160 实测逻辑轮速分别为(-4,+4)、(+3,+3)、(+4,-4) cm/s；
真实 J3约365–370 mm。失约后撤销授权并零速，续租不重启；1秒累计搜索预算耗尽后
NOT_FOUND并零速。用户确认观察到转向、同向转动和最终停止，另确认(+3,+3)时两侧实物均向前。
真实 IR A、第一次POWER只释放、第二次POWER启动也通过，测试后 STOP/VISION_ONLY。

首次真实画面中 A4 标牌贴边裁切，红色活动标签18超过15容量。保留原始 GRAB及模型复现，
用户将同张纸移远，再复位后24个不同帧中23次锁定蓝1（q255，U178/V181），红1完成8帧校色。
此后约20秒又发生单帧候选溢出；B历史 fault sticky 位导致 C 永久失去健康资格，
INTEGRATED 安全拒绝 ARM。这是现场发现的功能阻断，不能把之前的短时锁定写成持续成功。

### 第四阶段：E7070003 坏帧恢复与第二个现场缺陷

最小修正在感知适配器完成：历史 FAULT_CANDIDATE_OVERFLOW 仍保留诊断，但不永久禁止健康。
第一次 sticky 上升和每个匹配当前tag/config、时间新鲜、序号新的坏报告/RESOURCE_DROP
立即撤销旧健康、观测和锁定，建立**接收时刻**的新边界；旧管线好帧、重复帧、旧tag不能充数。
只有边界后三个相邻新健康帧恢复健康（允许 NOT_FOUND），目标锁定仍另需三帧有效观测。
FIFO、fatal、双bank硬故障仍阻断，没有通过忽略所有故障实现“恢复”。

该版控制236检查、完整R6、Full Compilation均通过。ALM29373/32070，
最差setup/hold +0.967/+0.117 ns，未约束0；22:02 AEDT新SOF下载并读回E7070003。
真实运行中frame338保留faultFlags=3，但健康和锁定已恢复，无复位；随后23个不同帧、
22次蓝1锁定，q255，U115/V186，处理延迟59.478 ms。这是本次已完成的真实故障纠正。

随后用户呈现真实红2，tag5→6证明重新SELECT生效。但第一健康报告尚未完成目标三帧锁定，
旧pending逻辑即发START；未标定扫描条件因此进入 SCAN_UNCALIBRATED/NOT_FOUND。
后续目标锁定也不会自动重启，用户看到“识别后无动作”。这个取消语义本身正确，问题是启动过早。
完整失败序列另存 `hardware_red2_e7070003_early_start.jsonl`，没有覆盖为后续成功。

### 第五阶段：E7070004 红2时序修正、板上通过与保留项

最小修正仅改变红2pending的启动资格：INTEGRATED未标定时必须等**本次重新选择后的当前目标锁定**，
前两帧ACQUIRING只能等待；已标定仍可凭健康新帧启动有界搜索。1秒授权窗口、STOP/IR/选择/
模式/安全取消、旧tag和旧帧隔离全部保留；健康无目标不启动，超时后的晚锁也不复活旧授权。

ModelSim控制自检254检查 PASS，实际解码15条UART，1.968秒；新增断言直接覆盖
前两帧不启动、第三帧锁定后APPROACH、无目标不启动、授权过期后不复活。
最终完整R6 219.556074秒，12 PASS + CAUGHT，满足用户285秒目标。
构建目录为 `build/member_b/20261104T111202_124373Z_build/`。

004 Fitter于22:28:38 AEDT成功：ALM29576/32070（92%）、寄存器41000、M10K357/397、
DSP51/87、memory bits2802640、PLL2。随后Full Compilation1121.141秒PASS、post-fit门检
25.868秒PASS，0 error/92 warnings；最差setup/hold +1.633/+0.118 ns、未约束0，
88项时序检查及每角63条同步链覆盖PASS，MTBF数值NOT_ASSESSED，没有放宽约束。
新SOF6706154字节于22:31:50 AEDT实际下载成功，BCTL读回E7070004匹配；
记录`build/repair/program_e7070004_console.log`。

随后真实红2板上链路通过：REAL_CAMERA/INTEGRATED、实体SW0选蓝1，tag3→4；
frame2900新锁定后ARM/ALIGN，逻辑L+4/R-4 cm/s、真实J3=468 mm、failure=NONE。
颜色已校准cfg1，但scanCalibrated=false，历史flags3仍保留；无需临时伪造扫描标定。
触发后2秒不发心跳，13个采样均ARM且leaseValid=false；7次ALIGN、4次LOST、2次ACQUIRE，
短暂丢失时零速重新确认，不能写成连续稳定转动2秒。触发和观察合计8个运动样本。
finally STOP确认未ARM、L0/R0、zeroSent=true，仍为INTEGRATED。

最终BCTL frame2959确认E7070004、蓝1q255、U182/V130、101×117框、frameGood=true，
处理延迟47.652 ms；红2事件7/id2、issuedAtUs115678441。
证据为`build/repair/hardware_red2.jsonl`和`red2_console.log`，003失败另存未覆盖。
用户确认004红2后实物会启动，最初反馈“不会自动停车”；随即收口到VISION_ONLY、未ARM和逻辑零速。
随后用户先确认“现在已停止”，再明确澄清“事实上是蓝一脱离后就停车了”。最终结论是004实物启动及
蓝1脱离后的实际停车已确认，撤去泛化的停车故障待查结论；不能把实际停止归因于切换模式。
主机两秒观察后STOP/zeroSent只说明板上撤销授权和零速JSON发送完成，其独立机械停车时刻未测，
不能写成两秒实物定时停车。红2开始正常任务并非两秒动作，架空也不能完成真实车体对准/停靠。
002的轮子/IR历史实测保留独立版本边界；按用户要求不再扩展硬件测试，继续文档和仓库发布。

该次发布时保留的范围限制是：落地三次一圈标定、六车位闭环、350 mm停靠误差、SW8正常/旁路公平对照、
实物超声危险及无回波边界、不同光照/遮挡，以及历史frame30321蓝6碎裂拒识。
004观察窗口仍有短暂LOST/ACQUIRE，持续视觉稳定性也明确保留。
后续架空J3/HOLD/STOP和SW8静态三对补验另列于下文；此处保留当时范围，不重复当作当前全未测。
架空转轮不等于地面360°标定，发完零速JSON不等于测量到车体物理静止。
当前无标定正式模式禁止无目标扫描，默认10秒只用于明确启动的合成调试；已锁定真实目标可接近。

迭代所引用的完整日志索引、命令、设计身份和验收边界统一保存在
[docs/REPAIR_RESULT.md](docs/REPAIR_RESULT.md)。本段记录的是开发与实际验证，不是课程完整验收、
Canvas提交或所有历史缺陷修复声明。用户要求的仓库推送由本轮最终交接另行记录。

最终发布SOF的仓库位置为`firmware/E7070004/PartBDebug.sof`，PDF位置为
`docs/ECHO7_Integrated_Datasheet.pdf`。PDF通过`tools/render_integrated_datasheet.py`
读取`docs/integrated_datasheet_metrics.json`复现（依赖reportlab/pypdf），旧`build/repair/`
过程文件不冒充最新发布物。发布SOF副本使用Quartus Programmer加载；`echo7.py program`
仍只接受本机成功构建记录中的原始SOF，不因整理文档而放宽产物身份核对。

发布前结构与打包检查另行执行：README白名单明确为`README.md`、`README_EN.md`、
`VERSION_README.md`三件；对应结构测试6项PASS（1.613秒），实际仓库检查48个bench、60个
工程依赖PASS。submission已有14项测试PASS（0.226秒），导出包含英文README和最终PDF指标JSON；
OWNERS覆盖277个源文件，新增工具/测试按B+C与未知SID如实归属。这些是主机/结构验证，
不增加RTL测试数量，也不替代硬件证据。

### 2026-11-04，继续原任务：实体拨码观测与交接工具修复

用户随后要求继续原prompt剩余验收，覆盖前一阶段暂停扩展硬件测试的范围决定。
此轮工具/文档修改没有改变生产RTL、板上版本或SOF：仍为E7070004；最终完整R6仍是
219.556074秒、12项PASS与CAUGHT。本轮没有为工具修改重复R6或Full Compilation。

只读审查发现旧`echo7.py test --hardware --trials`的trial-stream仍会自动发送BCTL
SELECT/CLEAR，而正式顶层已由C独占目标请求。旧命令不能代表当前六档实体开关验收。
现将`test --hardware`及`autodebug`明确返回BLOCKED/退出2，指向新观测入口；
`autodebug`在replay、构建、下载与板卡访问前就停止。历史评分和重复牌检查保留，
没有修改旧观测或用自动选牌绕开实体开关。

`tools/chassis_debug.py observe`在一个持久STP会话里依次冻结读取CCTL和BCTL，支持
`--samples N`或`--seconds S`、`--out`与`--label`，正常退出只QUIT，不发送MODE、
SELECT、CLEAR、ARM、心跳或STOP。每个端点的内容和主机读取区间独立保存；不把两次冻结
称为同帧。所有bad、unlocked和held轮询保留，另计不同帧数；Ctrl+C/传输失败也保存
已读部分。COMPLETE表示采集完成，不是功能PASS，输出文件不可覆盖已有记录。

`tools/compare_observations.py`离线比较正常/旁路各三次观测，要求同一构建、配置值、
实体目标、运行模式和poll数，单次内部请求/config稳定，SW8分别0/1且SW9关闭。
它拒绝重复使用一次run和错误时间顺序，分别统计全部轮询与不同帧；坏帧、丢锁、陈旧和
延迟值不会被删掉。没有操作者真实条件确认则UNCONFIRMED_CONDITIONS/退出2。
COMPARISON_VALID仅表明可比较，不能升级为六车位落地闭环、停靠或图像到UART延迟验收。
当前摘要中的延迟只来自FPGA capture/completion时间戳。

合成`scenario no-target-search --arm`改为读取当前scanBudgetUs，保持模板“预算＋3秒”，
覆盖最终零速、200ms停稳、900ms确认及轮询余量。同一会话持续记录状态并分页续租，
不再到默认10秒就抢先STOP；退出仍尝试STOP。HOLD期间不累计搜索转动时间，因此不能
仅根据会话时长宣布预算耗尽，也没有设置或伪造地面扫描标定。

导出器此前只把SOF放在`verified/PartBDebug.sof`，导致包内README的`firmware/E7070004/`
链接断开。现在只归档一份已核对当前构建的SOF，路径按构建ID生成
`firmware/<BUILD_ID>/PartBDebug.sof`；简短build_record记录包内路径和原始本机产物位置。
实际smoke ZIP验证了唯一SOF、当前README固件路径、PDF、CRC及与本次构建SOF字节相同。
这次smoke不代表随后所有新增实机记录与文档都已打入最终交接包。

针对检查实际完成：chassis/旧入口保护/submission共27项PASS（0.408秒），
新观测比较器及保留的历史评分/重复牌回归共32项PASS（0.505秒）。这些共59项均为
主机测试，部分使用明确的合成fixture，不增加任何实机或RTL通过数量。
OWNERS新增观测比较工具及其测试，当前279个文件；自动生成器同步保留B+C归属与
A/C SID pending，未杜撰成员身份或人工签核。中英文README补齐对应命令和边界。
后续六牌、六档实体选择及SW8实测结论以根代理核对后的独立原始记录为准，未在此预填成功。

### E7070004续测：完整六牌、六档实体选择和非法组合

根代理随后完成真实相机只读采集，vision根据全量记录生成
`build/continuation_20261104/vision_findings.json`与`six_switches_analysis.json`；
完整表见`docs/REPAIR_RESULT.md`末尾。本段只追加已核对的零运动视觉证据，不改变004源码、
219.556074秒R6或已发布SOF的身份。

用户将六张蓝牌完整置于画面，并用绿色胶带遮住红2。GRAB frame26844像素/结果同帧，
CRC0x80b8核对通过，E7070004、cfg1、红57/蓝37、正常透视、非raw；六张蓝牌均接受且q255，
处理52.889ms，无候选溢出。另12个不同B帧中六张蓝牌分别12/12接受，所选蓝1为
C健康/锁定12/12；全程VISION_ONLY、未ARM、零速。遮住的红2残余和参考条没有被伪造为数字。

实体SW0–SW5及非法选择续测运行150.054秒，保留441对完整只读采样，B为441个不同帧、
C为405个不同缓存帧。六个one-hot都实际锁定对应蓝牌；主要区间的N/C健康/C锁定/B锁定为：
蓝1=200/200/197/197，蓝2=23/23/22/22，蓝3=28/27/24/24，蓝4=22/19/16/15，
蓝5=29/28/23/23，蓝6=30/30/26/26。另有蓝2短过渡1次未锁，冲突后返回蓝1为
64/63/62/62，首对仍保留旧tag25 CLEAR而C已请求tag26；C没有接受旧报告为新锁。

全零NO_SELECTION共17次，CONFLICT共27次，其中稳定mask3为26次，另一次是mask6过渡。
这些非法选择均无C健康/锁定且B未选择目标；全441对均VISION_ONLY、未ARM、无运动许可、
逻辑L/R=0。C总健康390/441、锁定370/441，B好帧434/441。7个坏B帧全部是candidateOverflow，
没有candidateError/overrun，每次坏样本后均观察到好B帧；仅部分在同一选择结束前观察到双锁恢复。
完整坏帧/过渡记录保留，不能写成441次无丢锁或无坏帧。

CCTL先读、BCTL后读，两端分别冻结，因此一对中C尚锁定而稍后B出现新坏帧，不证明C接受了
该坏帧继续运动。读数间0.306–0.699秒见到好B、部分读数间恢复双锁，都不是精确原生帧恢复
或物理拨动到锁定延迟。本轮建立六档真实视觉选择覆盖，仍未替代六车位落地闭环。
该阶段结束时SW6/7显示、SW8三对公平试验、J3危险/无回波/距离边界与地面扫描标定待验；
后续新增的显示、J3及STOP证据见下方续测记录，不追溯改写当时的验收范围。

### 数码管使用说明澄清（生产RTL不变）

核对`memberCBoard.sv`后明确：d页HEX3–HEX0为十进制毫米，左侧HEX5页标识及HEX4模式
不属于距离；例如`d2 0520`是CHASSIS_INJECT模式下520mm。KEY1循环d/H/L，H/L显示NEC
遥控码；距离无效时右四位全熄灭。显示、控制及JTAG取自同一distance_mm，测量约100ms更新，
JTAG快照和现场观看不是同一时刻采样。中英文README已同步。

现场反射板摆位调整前后曾读到379mm与520/521mm；尚未核定真实反射面、尺子起点和绝对误差。
没有根据这次摆位差异修改换算系数，也未据此宣称距离标定或所有物理边界验收通过。

### E7070004续测：J3停靠、HOLD复核及独立STOP

生产RTL、板上版本及发布SOF仍为E7070004，最终完整R6仍为219.556074秒；此次只修正
一次性主机验收脚本和记录，没有重新编译RTL或重复R6。以下运动试验全部为合成视觉、
真实IR/J3/UART、架空底盘；原始记录及分析位于`build/continuation_20261104/`，
可移植说明见`docs/REPAIR_RESULT.md`。所有失败、未确认项及清理记录保留。

| 试验 | 记录与结果 | 实物确认及限制 |
|---|---|---|
| SW6/7显示 | SW6颜色信息可见；SW7中心在白色空隙显示局部颜色和“无标牌” | 用户确认；SW6两页/16槽/UNKNOWN/拒识原因及SW7中心覆盖牌/歧义仍未确认 |
| 停靠01 | `dock_hardware_01.jsonl`、`dock_analysis.json`；434快照/78.931565秒；首次变化为517mm、逻辑+5/+5→446mm、+3/+3→347mm、DOCKED/撤权/零速 | 用户确认运动、减速、停车、退远不重启；534–615mm退远窗口12快照/2.194秒仍DOCKED/零速；不是落地停靠误差 |
| HOLD01 | `hold_hardware_01.jsonl`、`hold_analysis_01.json`；362快照/66.181秒，板上条件PASS | 用户未确认实物全过程并要求重做，不算物理恢复验收 |
| HOLD02 | `hold_hardware_02.jsonl`、`hold_analysis_02.json`；434快照/79.899秒，原FAIL保留 | 用户未见恢复；主机在滞回观察未满1秒时抢先STOP，截断已开始的ACQUIRE，不证明生产RTL恢复失败 |
| HOLD03 | `hold_hardware_03.jsonl`、`hold_analysis_03.json`；469快照/86.677721秒，6项条件PASS、notVerified为空、清理无错误 | 用户确认近停、滞回仍停、退远恢复、随后自动停；本轮未观察轮向，未测机械停车延迟 |

停靠01首次DOCKED后83快照/14.853秒保持撤权/零速，包含退远窗口；条件确认点
521/454/321mm来自随后不同快照，不与首次变化517/446/347mm混为精确距离边界。
全部数值为真实J3报告读数，未校准尺子起点、反射面或绝对距离误差。

HOLD02尾部为237mm HOLD→251/254/266/292/297mm（滞回区间记录跨度仅0.652370秒）
→305mm HOLD→313mm ACQUIRE。79.860570秒末样本仍ARM、sonarHold已解除、逻辑零速，
租约/来源/目标锁定有效；79.860697秒主机即请求STOP并随后切mode1，阻止恢复转动被观察。
脚本现将提前安全恢复且尚未满1秒的阶段记为NOT_VERIFIED并继续、总结果为PARTIAL，
避免把不完整试验误写成生产缺陷或PASS。硬件恢复规则仍为三个新的有效样本≥300mm，
并非固定等待1秒；HOLD03完整满足主机要求，无跳过或PARTIAL。

HOLD03危险确认窗口231–242mm：5快照/0.647892秒HOLD/零速；滞回254–292mm：
7快照/1.163541秒仍HOLD/零速；退远367–407mm：19快照/3.119478秒恢复ALIGN，
逻辑−4/+4。恢复观察满3秒后，80.491761秒显式TX4 STOP，继续原模板及心跳。
STOP ACK至末快照6.093588秒，34个不同帧的状态快照均未ARM、零速且zeroSent=true；
首末快照跨度5.919557秒，原生frameId推进147。J3始终有效且为367–376mm，租约、来源、
锁定持续有效，sonarHold/IR/fatal均否，模式、选择、tag及配置不变，之后才切mode1清理。
因此本次停止和不自启有独立于失约、目标丢失、危险距离及切模式的记录；用户也确认停车。
34次为状态轮询，不是独立测距次数；持续描述指全部已记录样本，不能排除采样间变化。
本次结果不补证早先真实红2试验中未隔离的主机2秒STOP物理时刻，也不测机械停车延迟。

本轮结束于VISION_ONLY、IDLE、未ARM、逻辑零速、zeroSent=true，用户确认已停。
该阶段结束时尚待：无回波实物测试、SW8正常/旁路三对公平试验、SW6翻页及拒识/UNKNOWN全槽确认、
SW7中心覆盖牌/歧义、地面扫描标定与六车位闭环、精确距离/停车误差，以及A/C成员SID。
后续静态SW8三对、自动翻页、中心蓝1和首次地面中断记录已追加于下文，不把此历史清单当最新状态。
HOLD03本轮轮向未观察，未因此再扩展硬件运行；早期其他版本的轮向证据仍按版本单独保留。

### 2026-11-05：断电恢复、SW8三对静态对照和VGA补验（E7070004不变）

用户改为底盘供电后FPGA曾断电，JTAG也一度不可见；恢复电源和编程连接后，重新下载
本次已完成Full Compilation的E7070004实际SOF，程序下载及板上build ID核验成功。
日志在`build/remaining_20261104/reprogram_e7070004.log`。此前未完成的GRAB和连接失败
记录保留，没有将旧图像当成重新上电后的当前图像。生产RTL、发布SOF、219.556074秒
的R6和原fit/timing结果均未改变，未为纯硬件观察重复编译。

重新上电后的首张同帧GRAB显示标牌过小、偏画面边缘，未形成有效候选；用户调整纸张
完整入镜并确认镜头到纸张约42厘米（纠正先前口述42毫米）后，默认红48/蓝20、未校色
配置下六张蓝牌各连续6/6接受，蓝1健康锁定，VISION_ONLY全程未ARM和零速。
这次记录与断电前的红57/蓝37校色结果分别保留，不假设校色参数跨断电保存。

实体SW8依次采normal1/bypass1、normal2/bypass2、normal3/bypass3，各12个C/B配对。
第一次会话在等待normal2拨码时达到180秒阶段期限，退出PARTIAL，总229.014756秒；
已完成的第一对及等待日志未覆盖。新会话只续采其余四段，用时80.414576秒，并保存
原始超时来源及各段实际路径；不是六段全部来自同一个会话。用户对保持相机、纸张位置、
光照不变的确认题回复“done”，比较工具输出COMPARISON_VALID。两次会话均只读STATUS/
BSTATUS，没有选择覆盖、START、注入、心跳或STOP命令。C/B分别冻结，不宣称同帧。

| 静态对照 | 正常透视，3轮合计 | 实体SW8旁路，3轮合计 |
|---|---|---|
| 配对数及不同C/B帧 | 36，各端均36个不同帧 | 36，各端均36个不同帧 |
| 六蓝牌各自接受次数 | 蓝1–6各36/36 | 蓝2为35/36，其余各36/36 |
| 选定蓝1的C/B健康锁定 | 36/36 | 36/36 |
| 当前坏帧、候选溢出/错误、重复帧 | 均0 | 均0；但有一次有效候选拒识 |
| FPGA采集至处理完成平均时间 | 53.240667毫秒 | 42.578861毫秒 |
| 未ARM、无许可、L/R零速、zeroSent | 36/36 | 36/36 |

旁路第二轮样本0/frame20748，蓝2位置的candidate#5被reader uncertain拒识，quality0，
reason3；下一采样frame20763同位置恢复蓝2/q255。该帧仍为好帧，不能把“无坏帧”写成
“所有候选全部识别成功”，也不能由一个抽样失败推断持续缺陷或透视算法的普遍优越性。
各段采样数和配置匹配，实际采集用时不完全相等；数据只覆盖这些静态轮询，不代表所有
相机原生帧、地面六车位任务、正常/旁路地面各三次闭环，或图像变化到实际UART响应延迟。
详细表和原始文件索引见`docs/REPAIR_RESULT.md`；本次未新增逐文件哈希报告。

完成对照后，用户明确目视确认SW6的PAGE:1/PAGE:2自动交替；当前六候选时第二页为空
符合预期。随后移动纸张使蓝1覆盖中心小框，用户确认SW7显示ID:B1，之后恢复仅SW0上拨。
这两项补齐翻页和中心有效标牌身份的实物观察；UNKNOWN/拒识原因、16个满槽及中心歧义
并未随之全部验收。显示补验后的只读预检为配置7、colourCalibrated=true、蓝1健康锁定、
J3为386毫米且有效、IR未锁存、VISION_ONLY/零速；不将对照期间的默认未校色配置延续到
纸张移动之后，也没有读取或猜测这次新校色的具体阈值。

用户已确认底盘落地、周围可容纳一整圈、编程线缆可安全安排；地面标定和真实视觉停靠
在下一阶段单独记录。本节没有落地运动通过结论。断电/重新配置后扫描仍默认10秒且
未标定，不能将这个缺省值写成实测360度或已保存的一圈标定。

### 2026-11-05：E4地面首轮失败、左右实图核对与E5候选修正

本轮先执行E4真实落地试验，再定位问题、接受用户新规则并修改候选源码。没有先假设
硬件转向符合RTL中的left/right命名，也没有把原先的直行/架空动作通过当作真实视觉
闭环已通过。下述原始记录在`build/remaining_20261104/`，旧E4日志及已发布SOF均保留。

**地面与首轮失败。** `ground_scan_01.jsonl`为78个CCTL快照、21.518290秒，
结果TRIAL_INVALID，cleanupErrors为空。用户最初口述环氧树脂，后明确纠正当前测试
地面是**塑胶地板**，实验室才是环氧树脂；原日志首行不改，`ground_operator_notes.json`
补记更正。输入为健康合成NOT_FOUND、真实J3/IR/UART、实际落地底盘，临时预算60秒，
scanCalibrated=false，不是相机找牌或停靠任务。

一次START后12个SEARCH快照均逻辑L/R=−4/+4，实际有效J3为434–1702mm；相邻移动
快照的FPGA timeUs与scanElapsedUs增量差全部为0。21.457927秒的记录已进入HOLD：
raw4000、distanceValid=false、sonarHold=true，ARM保留但permit=false、左右0、zeroSent=true；
source/lease仍健康，IR没有触发，累计SEARCH命令时间2,899,142us。主机随后才请求
STOP并切VISION_ONLY，因此无效测距保护先于主机清理。最终仍未ARM/零速，清理无错。

用户确认约转75°后停下；首次方向口述有自我更正，后按**俯视**再次询问，明确回答
**顺时针**。用户另说明停下朝向前方空旷、未放恢复回波的纸板。该场景说明、近似角度
及电气状态各自记录：没有测原始ECHO波形，不能只凭4000判定电气唯一原因。首轮
没有完整360°、没有IR终点，三次整圈接受数仍0/3；不把75°或2.899142秒比例外推成标定。

**左右静态证据。** 车体固定后，同一蓝1从前左移到前右。`body_left_01.json`有
6/6完整C/B配对，U80、V158–159、J3 442–450mm，耗时3.426745秒；
`body_right_01.json`有6/6配对，U174、V157、J3 436–440mm，耗时2.810337秒。
两次C/B各6个不同帧，目标健康锁定，无坏帧，E4/cfg7、正常透视、红24/蓝20，
全程VISION_ONLY/未ARM/零速。用户明确VGA左半蓝1就是车体实际前左，U向右增加而V
基本不变，排除把低U当右侧或错用垂直轴的解释；C原样使用centreU，不做隐藏镜像。

结合ground01逻辑−4/+4实际顺时针，旧低U ALIGN确实背离车体左目标。此次定位为
**有效视觉转向反向**；双轮同号直行不能排除真实左右通道互换，本轮不再扩大单轮追线，
不声称已经证明某条接线错误。候选E5只将生产顶层TURN_SIGN默认+1改为−1，经已有
参数链影响SEARCH及两侧ALIGN，原左右极性−1/−1、居中+5/+5与+3/+3保持。
低U/SEARCH新逻辑(+4,−4)，按既有UART编码输出L−0.04/R+0.04；高U相反。
没有交换U/V、改变像素样本、翻转合成坐标或更改前进符号。没有运行时方向CLI；
需要新构建/下载后验证实际朝向目标，新一圈标定必须用最终方向及当前地面。

**随后用户改变正常无回波规则。** 用户明确指示“超声波读不出数据时可认为前方障碍
无限远，此时不应该应急停机”，覆盖附件原先所有无回波均禁止运动的规则。E5候选
在range驱动约23.3ms到上限后等待该次真实ECHO回低；本次有实际TRIG/有效回波过程、
长脉冲完整结束且未到80ms事务期限，才发布4000/valid=true的FAR哨兵。没有触发/
上升、恒高不落、期限到达或过短异常仍invalid；近≤250mm和IR保护不变，恢复仍需
连续三个新的安全样本≥300mm。每100ms事务和陈旧检查保留。FAR不是实测4米，也不
证明车体四周空旷；旧E4的4000/valid=false记录不回改成FAR。

板上d页仅在valid+4000显示FAr，H/L遥控页不变，invalid仍空白；主机decode新增
distanceFar和distanceKind（FAR/MEASURED/INVALID）。正常量程外与异常信号的实物
分界、新方向接近停靠在本段修改时仍待E5下载后验证；后续本版下载及静止FAR实测
已完成，见末尾新记录。正常空旷FAR不等于异常信号边界或运动闭环全部验证。

**新增聚焦回归。** 当前`tb_control_repair`使用显式负生产参数，269项/20条完整UART
PASS；同bench正参数泛型对照也269项PASS，不累加成538项独立需求。覆盖SEARCH、
低/高U完整JSON左右字段、U109/110/130/131边界、两段直行与STOP完整零。编译及
两次ModelSim总3.367385秒，日志为`turn_e5/control_negative.log`、`control_positive.log`。
`tb_pixel_uart_repair`固定25fps、原12帧真实RGB565管线输入不改，显式TURN_SIGN=-1，
12帧/12报告PASS；SEARCH41、低U18、前进39、高U34、zero118条完整UART。
Verilator5.050编译12.529247秒、运行71.835396秒、总84.364643秒，日志`turn_e5/pixel/`。
这些是RTL_SIM和编码验证，不是新版本实物方向测量或完整R6。

独立`tb_sonar_guard`在完整生产时钟尺度的模拟引脚回波下46检查PASS，12输出样本、
11次TRIG，覆盖24/39/75ms完整长脉冲、80ms恒高/晚落沿、无上升/无触发异常、近距及
新事务恢复。新副本Verilator编译5.821181秒、运行83.748601秒、总89.572575秒；
结果为`sonar_guard_verilator_20261104T133057_380747Z/result.json`。前一次
`...T133013_823304Z`编译exit255/MSYS权限异常记录保留（0.233933秒，未进入RTL仿真），
没有被成功重试覆盖。这里是模拟ECHO波形的RTL_SIM，不是传感器实物或完整R6。

同一sonar bench另有显式`+R6_REPRESENTATIVE`六事务路径，独立新副本运行25检查/
6样本/6次TRIG PASS，编译5.834637秒、仿真38.076932秒、总43.912875秒。
`sonar_guard_representative_20261104T133440_446720Z/validated_result.json`核对实际
退出0及PASS行；原包装器因PASS行新增scope字段而误报的`result.json` FAIL保留，
没有重跑或改RTL。完整46项边界路径仍在，代表路径不替代完整边界覆盖或完整R6。

**E5首次正式完整R6失败。** `build/member_b/20261104T133634_057221Z_verilator_course/result.json`
记录FAIL、退出1、303.500928秒、targetMet=false。新源码副本、Verilator5.050、jobs4，
目标285秒、总期限300秒不变；新增sonar后共有13个正式bench及mutant检测。前12项
pixel、control、CCTL、red2Start、sonar代表、continuous、overload、HSV、tracker、
fixedSheet、colourSampler、markerQueryStore均PASS；`mainColourSupportReader_tb`
编译达到整套截止时间，故意坏模块尚未执行。清理耗时计入实际303.500928秒；不写
CAUGHT、不写全部功能断言通过，也不借用E4的R6通过结论。

随后仅优化独立pixel/sonar仿真的并行调度，保留原continuous/overload并行、全部13项、
输入、断言及285/300秒标准，不复用前一次调用的二进制。为避免资源竞争，等E5完整
编译结束后才启动优化R6；最终实际13 PASS + 1 CAUGHT、239.403059秒、targetMet=true，
61个新复制源文件、cleanBuild=true、jobs4，结果在
`build/member_b/20261104T140614_115616Z_verilator_course/result.json`；日志为
`build/remaining_20261104/r6_e5_parallel_console.log`。生产RTL、TB、runner、输入均冻结。

**E5 Full Compilation实际完成。** `build/member_b/20261104T134331_185490Z_build/result.json`
记录PASS、退出0，Quartus Prime Lite18.1.0 Build625，compile1173.143秒、post-fit门检
25.799秒、0 errors/92 warnings，结果完成2026-11-05 01:03:31 AEDT。ALM29507/32070
（92%）、regs40957、M10K357/397、DSP51/87、memory bits2802640、PLL2；新SOF
6706157bytes，位于该build的`source/quartus/output_files/PartBDebug.sof`；后续已使用
此原始产物实际下载并读回E5，不把文件复制当作下载证据。

已读取本版`timing.json`、报告门与同步链覆盖数据：四角setup/hold/recovery/removal
均非负，最差setup+2.089ns、hold+0.116ns；88项报告检查，Illegal Clocks及所有列出的
未约束clock/input/output port/path为0。每角Gray9/9/32位timed path和同步级setup/hold
完整；resultToCamera1589位/requestCdc22位setup覆盖，resultToDisplay979物理端点
覆盖完整；max-skew与net-delay最差裕量18.013ns/13.647ns。每角63条预期/实际同步链
coverage PASS，MTBF验收NOT_ASSESSED。这些是本次真实结果，不沿用E4数值。

**当前发布门状态。** E5首次R6超时FAIL保留，最终优化R6 PASS239.403059秒；完整构建、
post-fit、原始SOF下载和E5读回均PASS，零速蓝1/FAR实测通过；实际有效转向、
真实视觉闭环及固定预算自动停车角误差仍未完成；FAR期间SEARCH和三次满圈已有记录，13.6秒近似上限已实际设置。004的219.556074秒、1121.141秒、
ALM29576和时序成绩继续只归004。E5单圈脚本独立保留，先读回E5再准备新SEARCH，
允许valid FAR、每次新ARM一次、真实IR A终止；真实INTEGRATED观察脚本不发START/
注入/心跳，等实体POWER，DOCKED保持3秒与NOT_FOUND分开。脚本就绪不算已经运行。
实际结束状态为E5 VISION_ONLY/未ARM/零速；三次一圈、六车位落地闭环、SW8地面对照、
实际停止误差与端到端延迟继续保留待项。详细证据及后续真实结果在
[REPAIR_RESULT.md](docs/REPAIR_RESULT.md)追加，旧失败不被候选修正覆盖。

本轮生产变更集中于`echo7IntegratedTop.sv`默认方向、`memberBBuildId.svh`身份、
`sonar_guard.sv`有界FAR分类及`memberCBoard.sv`距离页；主机解码在`chassis_debug.py`。
控制、像素和超声专项bench分别保留对应边界，manifest/suite纳入sonar代表项。
完整文件索引及测试层级见验收报告末节；源码冻结不表示新SOF已构建或板卡已下载。

**E5实际下载与静止实测。** 在完整R6及构建通过后，使用本次成功build的原始SOF下载，
`build/remaining_20261104/program_e5_console.log`记录PASS、programmerSucceeded=true、
buildIdVerified=true，实际读回E7070005；UTC2026-11-04T14:11:16.707754完成，换算
AEDT为2026-11-05 01:11:16.707754。构建完成时间与下载时间分别保留。

随后`e5_zero_scene_01.json`在3.045175秒取得8/8完整C/B配对，各8个不同帧；蓝1
healthy/observed/locked全部通过，U170/V159–160，J3真实432mm有效，VISION_ONLY/IDLE、
未ARM、左右0、zeroSent=true，无HOLD。实际校色配置1、红24/蓝16，colourCalibrated=true，
scanCalibrated=false，历史faultFlags3保留。C/B分别冻结，配对不冒充同一时刻快照。

用户移开挡板后，`e5_far_01.json`在2.270134秒取得6/6完整配对，均valid4000、
distanceFar=true、distanceKind=FAR、无HOLD、zeroSent=true；用户确认实际d页显示far。
此时健康但无目标，observed/locked=false，全程VISION_ONLY未ARM/左右0。4000是FAR
哨兵，既不代表测得4米，也不记录原始ECHO波形；静止读回不能证明运动期间的FAR行为。
这两项是E5真实硬件观察，不沿用E4结果；本版有效转向、连续整圈及地面停靠尚未验证。
截至这两组静止观察时，新版圈数为0/3、首圈尚在准备，没有写入标定；随后首轮执行结果单列如下。

**E5第一轮地面IR计时。** `ground_e5_01.jsonl`记录总34.960365秒、197个C快照，
IR_TERMINATED_TIMING_CAPTURED，failure/cleanupErrors均空。塑胶地板、当前整车及
底盘供电，健康无目标合成视觉、真实J3/IR/UART，临时60秒未标定预算；不是实际视觉
搜牌/停靠任务。80个运动快照全部SEARCH、逻辑(+4,−4)、source/lease健康、ARM/permit，
无HOLD/invalid/fatal/身份变化。70次MEASURED快照377–3120mm，10次FAR4000，分为
2/1/7次三个窗口，最长采样首末1.072009秒；快照次数不当作独立超声采样次数。
相邻79对真正运动快照timeUs与scanElapsedUs增量差−1..+1μs，未观察到计时中断。

实际IR快照先读到锁存、未ARM、IDLE、左右0、zeroSent=true，累计SEARCH **13.561176秒**，
随后主机才STOP及切VISION_ONLY。最终V1/未ARM/左右0、IR仍锁、J3379mm有效。
用户确认“转满一圈多一点点，同时转完后相较于起始是往前了一些”，原话保存在
`ground_e5_operator_notes.json`。这是1次满圈且轻微超转/前移的观察；最初旋向及误差待补，后续补充见下段，
不把IR终点累计时间冒充精确360°时间，不据此永久标定。
随后用户补充“逆时针，多了大概10°，前移约3.5cm。第二圈就绪”，原话已保存：
首轮可计物理满圈**1/3**，旋向为俯视逆时针；约10°和3.5cm是用户估计，漂移误差保留。
首轮阶段尚未写入参数，未将13.561176秒按估计角度缩放成精确360°；后续三圈汇总与实际写入另列。

当前E5固件发布副本为`firmware/E7070005/PartBDebug.sof`，6706157bytes。使用原始成功
build实际下载及读回的记录独立保留；历史E4发布路径继续只描述当时归档。

**E5第二轮满圈及启动不对称。** `ground_e5_02.jsonl`记录27.025306秒、146个C快照，
IR_TERMINATED_TIMING_CAPTURED，无failure/cleanupErrors。66个不同帧运动快照全为
SEARCH逻辑(+4,−4)，source/lease/ARM/permit和J3有效，tag6/配置1/蓝1保持，无HOLD/
fatal/提前IR。53个MEASURED快照395–1686mm，13个FAR快照分2/5/6次三段，最长采样
首末0.751414秒；65对相邻运动计时增量差−1..+1μs。IR先读到未ARM/零速发送完成，
累计SEARCH **11.075500秒**，随后主机STOP/mode1；末VISION_ONLY零速、IR锁、404mm有效。
随后用户确认“满一圈，多5°，前移大概2cm。然后我发现主要是启动的时候左右轮动力
输出不均匀，都出现了单边前冲的情况”。第二圈实际满圈成立，累计物理确认**2/3**；
约5°及2cm是用户估计，不当作精确传感器测量。两轮启动单边前冲/动力不对称作为实际
缺陷现象保留，尚不能归咎UART、接线、电机、摩擦或电源中的具体根因。当前只读核对
命令链，第二轮结束时尚未写scanCalibrated；后续第三圈与参数写入另列，仍保留两次
实际时间与漂移，不用期望值替换日志。

**E5第三轮满圈及实际13.6秒设置。** `ground_e5_03.jsonl`为151快照/27.078186秒，
IR_TERMINATED_TIMING_CAPTURED、无failure/cleanupErrors、累计SEARCH **11.436358秒**。
70个不同帧SEARCH快照全(+4,−4)、ARM/permit/source/lease/J3valid，tag8/配置1/蓝1不变，
无HOLD/fatal/提前IR；55个MEASURED402–1689mm，15个FAR快照分2/5/8次三段，最长采样
首末1.175691秒。69对相邻运动计时增量差−1..+1μs。实际IR撤ARM/零速发送完成先于
主机清理；末VISION_ONLY零速、IR锁、432mm有效。随后用户确认“满圈，我按晚了，
多转45°，没有单侧前冲”：三次满圈确认**3/3**，第三轮超转约45°含明确按晚误差，
没有观察到单侧前冲，位移未提供不补猜。后两次旋向没有另行口述，命令与首轮相同。

三次板上时间13.561176/11.075500/11.436358秒，最大最小差2.485676秒，均值12.024345、
中值11.436358；二者分别比最大少1.536831/2.124818秒，可能不能覆盖最慢实测轮次。
三圈物理确认后，已将最大值向上取**13.6秒**作为覆盖本次记录的有界SEARCH上限，
比最大多38.824ms，不保证未来条件下精确360°，快轮可能多转。
不按用户约5°/10°反馈缩放原始时间，保留起步前冲、超转、前移和人为终点判断边界。

实际CLI输出`e5_scan_calibrated_13600ms.json`读回scanBudgetUs=13600000、
scanBasis=CALIBRATED_TIME、scanCalibrated=true；VISION_ONLY/IDLE未ARM、左右0、
zeroSent=true、IR仍锁，J3421mm有效，没有START。旧scanElapsed11436358是前一轮的
保留计数。该运行时参数跨普通模式切换保留，reset/重新下载会清回10秒未标定默认，
没有烧成永久参数。只适用于已记录的当前塑胶地板、整车及底盘供电；实验室环氧地面
未测。尚未验收固定13.6秒预算自动停止时的转角误差，随后真实蓝1任务已执行但NOT_FOUND，不能记停靠
通过；起步前冲前两次出现、第三未出现，根因仍未证明。

只读UART源码审查确认，生产启用独立左右请求，IDLE同一时钟沿生成并冻结含L/R的完整
JSON，SEND逐字节发送，不逐侧拼旧值。此结论不证明底盘对端解析、电机施力或机械起步
同步，不能消除用户看到的单边前冲；没有据此归咎或修改单一硬件部件。

### 2026-11-05：E5真实蓝1失败、短转过冲诊断与E6候选

**先记录真实失败，再修改控制。** `integrated_blue1_01.jsonl`原label为visible_left，
但用户在独立preflight后已把蓝1移出视野，实际POWER前是健康NOT_FOUND；原日志不改，
场景更正在`integrated_e5_operator_notes.json`保存。实体POWER启动，主机START/合成写入/
heartbeat均0。任务结果**NOT_FOUND / SCAN_BUDGET**，不是DOCKED：656快照、全程观察
73.006122秒，首次ARM至终态36.330141秒，搜索累计达到13.600000秒后零速且未ARM。
主机随后STOP/mode1，cleanupErrors为空。任务段335不同C帧、蓝1/tag10/配置1保持，
真实J3valid、无HOLD/IR/fatal、lease=false；状态SEARCH128/ACQUIRE49/ALIGN129/LOST23/
APPROACH5/NOT_FOUND1，未完成真实停靠。

首次ACQUIRE实际是观察ARM后约**1.200秒**，第一次确认失败后约+2.320秒回SEARCH；
约+12.637秒是后一次ACQUIRE，+12.970秒才首次ALIGN，不能写11秒后才首次发现。
之后8个LOST窗口、9个ALIGN窗口反复，APPROACH仅5个+5/+5快照、613–663mm；
SEARCH累计在纠偏期间保持11.205106秒，后继续搜索到13.6秒并最终确认失败。CCTL没有
逐帧U/B拒识原因，不能唯一断言丢锁根因。用户确认首扫未确认、后跟踪靠近一段又
逆时针转远，并描述“左右来回一段时间后，转远了”；原话完整保留，不改成整机成功。

**固定纸板短转诊断仍为INCOMPLETE。** `real_turn_probe_e5_01.jsonl`采用一次主机START、
真实蓝1/真实J3，无注入/heartbeat；pre三帧U57，START发送至STOP请求0.340987秒，
7个运动C快照均ALIGN逻辑(+4,−4)。这不是严格0.30秒机械脉冲，也不是实际UART波形捕获。
首先确认零速的FPGA timeUs=1542683620；之后实际新capture分别+245.133ms/U96锁定、
+525.021ms/U142未锁、+884.877ms/U169锁定，处理耗时约48–49ms。仅2/3符合锁定，
脚本输出INCOMPLETE、medianDeltaU=null、trend=UNAVAILABLE，未造三帧中值PASS。

后来`e5_turn_probe_settled.json`六帧U全173、健康锁定，但它们在首次零确认约90.489–
92.608秒后采集，不能证明1.5秒内停稳。用户确认纸板固定、最终车轮完全停止；对短促
启动后的尾转时长答复无法判断。固定目标U趋向并跨越中心支持方向正确且明显过冲；
200ms后新画面仍变化，机械停止时间/尾转原因未定，不能用zeroSent替代实物停稳。

**E6实现。** 在`motion_fsm.sv`、`member_c_control.sv`中，进入ALIGN时锁存方向/速度/
脉宽；误差abs(U−120)≤30且不在110–130死区时用3cm/s，>30用4cm/s，SEARCH仍4cm/s。
时长clamp(error×2000us,20000us,100000us)：U89为62ms/4、U90为60ms/3、U109/131为
22ms/3。更新U不延长同一脉冲；到期、跨侧、或转中后都先零速ACQUIRE，不直接反转/
平移。zeroSent后驻留1.5秒，再新fence及3个postfence新帧重新确认；900ms确认超时不变。
`memberCBoard.sv`生产默认同步1.5秒，build ID为E7070006；入ALIGN本来已居中且本次
未转动的路径才可APPROACH。LOST持续无目标仍按原300ms回SEARCH，不能说所有分支
均等待1.5秒；安全/IR/STOP/lease、累计搜索预算及120秒任务总限没有放宽或被短转重置。

1.5秒是保守设计配置，不是已证机械静止；3cm/s可靠起步尚未实测。更频繁的起步可能
放大前两圈已有单边前冲，不能只凭仿真宣布机械过冲/漂移已修好。源码正式冻结。

**E6聚焦结果与发布边界。** 正/负TURN_SIGN ModelSim各338检查、53完整UART PASS，
编译零错误零警告，编译加两次仿真5.2128905秒；日志`control_e6_20261104T144617Z/`。
覆盖短转到限、锁存不延期、3/4分档/完整±0.03左右字段、跨侧/转中先停、实际零包后
驻留与postfence三帧、SEARCH连续和原安全回归。测试驻留1500us是加速协议配置，
不当作生产1.5秒实测；正负各338不累加成676个独立需求。

像素链仅把center hold2帧延至4帧，总14帧、固定25fps，保留全部原12帧/顺序/像素输入/
断言，为新增停车边界提供真正三新帧，未降低资格。新副本单次PASS14帧/14报告、
sourceUnchanged=true，UART search41/left18/forward19/right34/zero178；编译9.217031秒、
仿真69.766992秒、包装器总78.991060秒，`pixel_uart_e6_20261104T144702_631205Z/result.json`。
上述简写均以`build/remaining_20261104/`为前缀，属于独立聚焦RTL_SIM。

正式E6 R6已完成一次**PASS：266.840318秒、13 PASS + 1 CAUGHT、targetMet=true、退出0**。
结果为`build/member_b/20261104T144856_668139Z_verilator_course/result.json`，61个新复制
源文件、cleanBuild=true、Verilator5.050、jobs4，满足285秒目标和300秒门槛；13个正式
bench（含14帧pixel、338项control、sonar代表）及原mutant检测保留，未借用旧二进制。
随后E6 Full Compilation的**编译工具退出0、1183.703秒，但整体验收FAIL、退出1**，
`build/member_b/20261104T144730_277631Z_build/result.json`记录critical timing warnings。
实际CLOCK_50 slow85 setup **−0.265ns/TNS −1.786ns**、slow0 **−0.203ns**，最差hold
+0.120ns。拟合为ALM29462/32070、寄存器41136、M10K357/397、DSP53/87、存储2802640bits、
PLL2。该构建在critical warnings门停止，没有独立timing_gate步骤或timing.json，不能记四角
门检PASS；器件装得下及功能仿真PASS均不能代替时序。E6失败产物**未下载、不得下载**，
当时设备仍E5 VISION_ONLY/未ARM/零速。没有随机换seed、放宽约束或忽略警告来接受产物。

### 2026-11-05：E6实际STA定位与E7等价运算修正

**先读取失败数据库的真实关键路径。** 对E6既有拟合数据库运行只读Quartus STA，目录
`build/remaining_20261104/e6_sta_diagnosis_20261104T150928_837210Z/`；耗时13.098885秒、
命令退出0，但结果明确`timingPass=false`，这是诊断完成，不是时序通过。两个slow角各20条
最差路径全部从mode[0]出发，到alignPulseUs低位寄存器：模式报告capture时间选择→adapter
afterFence减法/比较→centreU即时旁路→32位abs误差→串联两级DSP乘法→clamp→寄存器装载。
85°C最差路径15级逻辑、data delay19.971ns，两段DSP延迟3.159及2.047ns；完整报告为
`setup_6_slow_1100mv_85c_worst20.txt`、对应0°C文件及`path_endpoints.tsv`。
这才授权针对运算宽度修正，不绕开adapter的即时安全撤权或fence。

**E7只作等价算术优化。** `motion_fsm.sv`对五个默认参数（110/130死区、2000us/像素、
20000us最小、100000us最大）增加窄位路径：8位abs误差最大135，脉宽专用输入截到10..50，
用6位值扩成17位后计算`(x<<11)−(x<<5)−(x<<4)`，等于2000x。最大中间项102400在17位
范围内，减法非负；死区仍输出0，3/4速度分档使用未截限实际误差。非默认参数仍使用
原通用公式。build ID为E7070007；1.5秒、速度、TURN_SIGN、SEARCH、任务预算、IR/J3/
STOP等安全行为及SDC/QSF均未变。这不是新的机械调参，不能先声称已消除负setup。

**保留首次词法失败。** `control_e7_20261104T151306Z/`为COMPILE FAIL，ModelSim把
带基数十进制数字紧接三元`?`解析为不合法数字，5 errors/1 warning，仿真没有启动。
补必要空格后未改算术；原compile.log/result.json保留，没有用成功目录覆盖失败。
随后新目录`control_e7_20261104T151338Z/`编译0 error/0 warning，正/负TURN_SIGN各
338检查、53完整UART PASS（spin32/drive4/zero17，粗low24/high1、细low6/high1），
编译加两次仿真5.113292秒，result关联原失败目录。默认U0..255共256种输入与原公式
0处差异，`arithmetic_equivalence.json`保留每个U的原值/新值；枚举不是机械时间或STA证据。
上述简写控制目录均以`build/remaining_20261104/`为前缀。

**E7独立正式R6、构建、时序及实际下载均通过。** 本次R6结果为
`build/member_b/20261104T151442_166532Z_verilator_course/result.json`：**265.276162秒、
13 PASS + 1 CAUGHT、targetMet=true、退出0**；61个新复制源文件、cleanBuild=true、
Verilator5.050、jobs4，满足285秒目标及300秒门槛。含未改的14帧pixel、338项control及
真实时钟sonar代表；不另重复独立pixel，不沿用E6二进制或266.840318秒/R6 PASS。
Full Compilation目录`build/member_b/20261104T151422_461823Z_build/`的本版独立结果为
**PASS：编译1147.755秒、post-fit门检26.087秒，0 errors/92 warnings**。ALM29320/32070
（91%）、寄存器41015、M10K357/397、存储2802640bits、DSP51/87、PLL2；原始SOF位于该目录
`source/quartus/output_files/PartBDebug.sof`，6706155bytes。最差setup **+0.864ns（slow0）**、
hold **+0.117ns**；88项报告检查，Illegal Clocks及全部unconstrained均0。四角所需同步链
63/63、coverage PASS，MTBF验收NOT_ASSESSED；Gray9/9/32、相机/请求payload1590/22及
显示979物理端点覆盖完整。max-skew约束最差slack +18.437ns、net-delay约束slack +13.942ns，
是约束裕量，不是实际skew/延迟值。E7实际DSP回到51且setup为正，不借用E5/E6结果。

随后真实program成功，`build/remaining_20261104/program_e7_console.log`记录
programmerSucceeded=true、buildIdVerified=true、exit0，结束UTC2026-11-04 15:34:42.428181，
即2026-11-05 **02:34:42.428181 AEDT**；实际设计读回E7070007。下载后保持VISION_ONLY、
未ARM、左右0、zeroSent=true；用户蓝1仍在画外，塑胶地板及供电不变。

重新下载会清除运行时标定，因此随后明确恢复13.6秒经验扫描上限，而不是假定它跨下载保存。
`e7_scan_calibrated_13600ms.json`读回scanBudgetUs/remaining=13600000、CALIBRATED_TIME、
scanCalibrated=true、scanElapsed=0；REAL_CAMERA/蓝1稳定独热、sourceHealthyFresh=true、
targetObserved/Locked=false、VISION_ONLY/IDLE未ARM、左右0、zeroSent=true，IR=false、
sonarHold=false、真实J3694mm/valid MEASURED。没有START，不将参数恢复称为新一圈测试或
精确360°；该参数恢复阶段尚未开始真实搜索，后续observer01/02另列，分档短转的机械效果仍待验证。
E5真实任务失败及INCOMPLETE、三圈的超转/漂移/前冲，E6负setup和E7词法FAIL均继续保留；
3cm/s可靠起转、1.5秒机械停稳与真实视觉地面停靠仍未证实。

### E7首次真实观察未启动，保留INCOMPLETE

`build/remaining_20261104/integrated_blue1_e7_01.jsonl`在45秒实体POWER等待窗口内未观察到
ARM，含收尾147个CCTL快照全部IDLE/零速；结果**INCOMPLETE**，原因启动窗口到期并取消
迟到授权。首次ARM、首次任务终态和任务观察时长均null，完整窗口及收尾45.112171秒。
主机START/合成写入/heartbeat均0；到期STOP及切VISION_ONLY后仍未ARM、左右0、
zeroSent=true，cleanupErrors为空。此轮是**没有启动任务**，不是运动控制失败，更不是
搜索/停靠通过，也不据窗口内零速否认窗口外运动。用户随后明确报告反复按POWER无反应，
再按KEY0两次、每次短暂运动；此反馈与147个窗口内快照分别保留，触发因果未被完整捕获，
不推断是KEY0、迟到IR、视觉事件或其他某一因素已被证明。源码、构建及已下载E7不变。

随后主机设置并读回VISION_ONLY未ARM零速；`e7_after_key0_pairs.json`六组C/B分别冻结样本
确认B仍E7，5/6 C源健康，一次candidateOverflow/frameGood=false后恢复。J3依次92mm/HOLD、
792mm仍HOLD、788mm解除，之后789–792mm；此处本来零速，不能算运动急停验收。
KEY0把运行时扫描参数清为10秒/SCAN_UNCALIBRATED，符合复位设计。整理手部、线缆与红2后，
`e7_scan_restored_after_key0.json`明确恢复13.6秒/CALIBRATED_TIME、V1零速及J3737mm有效，
不是参数跨复位保存，也没有重新编译或下载。

### E7第二次真实任务：缠线/近距HOLD，观察到限后INCOMPLETE

`build/remaining_20261104/integrated_blue1_e7_02.jsonl`包含261个CCTL及258个BCTL快照。
首次ARM记录在主机20.0387466秒，任务观察60.0152787秒，含收尾80.0976572秒；结果
**INCOMPLETE**，原因为60秒任务观察限，firstTerminalSnapshot=null，不是DOCKED/NOT_FOUND。
主机START/合成写入/heartbeat均0，REAL_CAMERA/真实J3、13.6秒预算，首次SEARCH逻辑(+4,−4)。

轮询记录约20.039秒SEARCH（738mm）→21.331秒ACQUIRE（748mm）→23.701秒确认未成回SEARCH
（805mm）→26.068秒HOLD（215mm）→28.728秒解除HOLD回SEARCH（319mm）→29.598秒再次HOLD
（33mm）。累计SEARCH止于4.512126秒，未见ALIGN/APPROACH/DOCKED；最后收尾VISION_ONLY、
未ARM、左右0、zeroSent=true，J3251mm有效但HOLD仍在，cleanupErrors为空。轮询时刻不能
当作精确传感采样/状态转换或机械停车延迟，60秒是主机观察限而非生产120秒任务总限。

用户原话：“**扫过了蓝1，继续转的时候，遇到了线缆缠绕，然后超声波判定到距离过近中止**”。
保留线缆及近距保护对本次试验的影响，不将它归为纯控制逻辑失败或主任务成功；因未进入ALIGN，
本轮也不能证明新分档短转的实物效果。下一步等待用户把蓝1置于居中位置，做避免整圈缠线的
接近停靠验证；真实落地DOCKED和机械改善仍PENDING。源码与已通过的构建保持冻结。


## 2026-11-05: E7地面试验04/05、连续直行隔离与E8修复

E7构建/R6结果保持不变。窗口03再次45秒未ARM并正常收尾；用户报告多次POWER无反应，但无精确IR时刻，不能断言遥控器故障。随后经用户确认就绪，改用单次主机START，保留真实相机/J3/IR/UART、操作员A急停及限时STOP→VISION_ONLY，零合成视觉写入、零续租；这不作为POWER因果验证。

真实任务04从U112/J3约699mm开始，初始+5/+5后反复短转/驻留，60.1635664秒、206 C/201 B，未DOCKED；用户观察向前蠕动、左右累计约1/3.5cm。真实任务05从U197开始，15.048011秒、56 C/51 B，4cm/s短转把U带到123，随后APPROACH又使其到约56；用户观察主要左轮动作、右轮基本不动。两轮均INCOMPLETE并正常零速收尾，未以瞬间居中算停靠。

为了区分视觉切换与持续直行，两秒合成居中坐标经过真实C/超声/IR/串口和注入租约：+5/+5至J3<500mm后+3/+3，J3由618mm降至循环末454mm、零速后430mm，用户确认基本直着向前。此项仅证明该条件下连续前进可推进，不是实相机停靠，不能证明轮端同步或PID根因。

E7070008保留原110–130对准/停靠死区与全部安全资格，仅在已经进入APPROACH后允许U75–165内连续正向差速修正（远距5/3，近距4/3，方向随误差/原TURN_SIGN）；居中仍5/5或3/3。范围外或到350mm偏心时先ACQUIRE，完成零速、1.5秒保守驻留及新fence后三帧，再进行原短脉冲对准，避免前进后直接反转。SEARCH、累计预算、初始ALIGN、轮速极性、底盘固件及协议不改。E8独立仿真、构建、下载及首轮蓝1地面结果分别列于下文，未沿用E7 PASS。

Detailed raw paths, physical quotes and evidence boundaries are recorded in [REPAIR_RESULT](docs/REPAIR_RESULT.md). E8 now has one real-camera blue-1 approach/docking result from an initially locked target. Search from no target, five other bays and E8 POWER/red-2 starts remain pending. The earlier two-second centred injection remains synthetic vision through real hardware and is kept separate from the new camera result.


E8定向控制回归已实跑PASS：`build/remaining_20261104/control_e8_20261104T160731Z/`，两种TURN_SIGN各433检查/88条完整UART，compile+两sim共6.7496263秒、编译零错误零警告。新增真实编码5/3、4/3两方向，APPROACH范围/距离边界与立即撤权、退出后的零速/驻留/新fence三帧均覆盖。E8正式R6独立PASS：`20261104T160829_370108Z_verilator_course`，270.641086秒、13 PASS + CAUGHT、targetMet=true；14帧真实像素处理链至UART的右向纠偏实际为34条3/5前进差速、rightSpin0，保留帧数、识别和安全断言。

### E8完整构建、实际下载及蓝1真实落地DOCKED

本版`build/member_b/20261104T160829_127927Z_build/result.json`为PASS：compile1159.722秒、
post-fit25.963秒、0 errors/92 warnings；ALM29281/32070（91%）、寄存器41081、M10K357/397、
存储2802640bits、DSP51/87、PLL2，setup/hold最差+1.021/+0.121ns。88项报告检查、Illegal/
unconstrained全0；四角同步链63/63 coverage PASS，MTBF NOT_ASSESSED，不沿用E7结果。
原始`source/quartus/output_files/PartBDebug.sof`为6706156bytes。实际program于UTC
2026-11-04 16:28:58.446132（AEDT2026-11-05 **03:28:58.446132**）成功，E7070008读回匹配，
`program_e8_console.log`保留证据。发布[firmware/E7070008/PartBDebug.sof](firmware/E7070008/PartBDebug.sof)
与原产物逐字节一致；旧E7发布副本移除，原build/失败日志保留。下载后在V1零速明确恢复
13.6秒运行时参数，见`e8_scan_calibrated_13600ms.json`，不声称跨下载保存。

首次真实蓝1日志`build/remaining_20261104/integrated_blue1_e8_01.jsonl`输出
**DOCKED_OBSERVED**：116个C快照、110个不同B帧，B全部good且locked。真实相机/J3/IR/UART、
INTEGRATED，一次主机START，合成写入/heartbeat均0；起始蓝1已锁定，因此这次不覆盖SEARCH。
首次ARM主机2.169262秒，APPROACH(+5,+5)、J3690mm；随后462mm时(+3,+3)、365mm时采到
(+4,+3)差速，约6.076秒在350mm偏心处先ACQUIRE。之后约25.4秒末端微调，轮询采到3个
ALIGN(+3,−3)快照并多次静止重确认；采样数不是完整短脉冲次数，不能认定1.5秒机械停稳。

首次DOCKED主机31.484328秒，观察ARM到终态**29.315066秒**；未ARM、左右0、zeroSent=true、
J3 **329mm**，邻近独立B快照U110。12个DOCKED快照保持零速/未ARM，首末跨度**3.18423秒**，
随后finally STOP/VISION_ONLY，cleanupErrors为空；完整记录34.741535秒。C/B分别冻结，
不称同帧绑定；上述时间是主机观察时间，非精确物理停车或像素到UART延迟。
本轮未见SEARCH/LOST/HOLD/IR。用户原话：“**持续向前，不明显偏转，左轮大概多走了1cm？
探头前端距离大概33.5cm**”。这提供实际前进/停止位置观察；约1cm/33.5cm为估计，不能
把它与J3329mm的差值写成传感器校准或精密停车误差。

本轮实现了**已锁定蓝1起始的落地接近—减速—末端对准—DOCKED主功能**。约25秒末端微调
仍慢，重复性、左右位移差保留；其余蓝2–6、无目标起始搜索停靠、E8实体POWER/红2启动
仍PENDING，下一蓝2摆位正在等待用户回复。生产源码保持冻结；E5/E7实测失败、E6时序失败
及此前不完整窗口均保留，不因单次蓝1完成而泛化全部需求通过。
