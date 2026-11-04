> 本文保留独立 Member B 历史说明。2026-11-04 当前修复源码为 E7070004：六位独热选择、同一SOF三模式、有界扫描、CCTL、红2重新选择并等待新目标锁定后启动，以及单帧候选溢出恢复。当前操作以 [README.md](README.md) 为准，本次构建、实测与剩余限制见 [修复验收记录](docs/REPAIR_RESULT.md)，不沿用下方旧版本通过结论。

# Version history and validation / 版本与验证记录

This is the consolidated history of Member B and the later ECHO-7 B/C integration. Entries below run from the earlier
baseline to the latest work. Build identities, failed experiments and evidence
levels are kept separate. README.md and README_EN.md are the maintained Chinese
and English operation guides; OWNERS.md records individual-file responsibility and origin.

这是按开发先后整理的版本记录。MODEL、RTL_SIM、拟合、下载、相机实测和用户确认的
实体VGA分别记录；历史通过不能证明后续源码通过。课程要求、用户需求和设计选择也不混用。

**当前入口（2026-11-04）**：本页末尾的“ECHO-7 整机修复与现场迭代”记录本次
`dc1db23` 基线之后的工作。历史段落中的“最终”“不再下载”“静止 Member B 顶层”
以及当时的 R6 FAIL 只描述对应日期和源码，不能作为当前集成版本的结论。
当前源码 `E7070004` 的控制自检为 **254 PASS**，完整 R6 为 **12 PASS + CAUGHT，
219.556074 秒**；Full Compilation **1121.141秒PASS**、post-fit门检 **25.868秒PASS**，
22:31:50 AEDT新SOF下载及E7070004读回成功。真实红2重新选择、新锁定后ARM/ALIGN
板上链路已通过，用户确认实物启动，并最终澄清“蓝一脱离后就停车了”。
收口为VISION_ONLY/未ARM/左右逻辑零速，用户确认已停止；主机STOP的独立机械停车时刻未测，zeroSent只证明发送完成。
不借用E7070002/E7070003 的硬件动作结果。完整证据和待验收项目见
[修复验收记录](docs/REPAIR_RESULT.md)。操作入口为[中文README](README.md) /
[English README](README_EN.md)；一页数据表发布位置为
[docs/ECHO7_Integrated_Datasheet.pdf](docs/ECHO7_Integrated_Datasheet.pdf)，采用004最终核验及用户澄清后的结论。

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

设计 build ID 与 CCTL 接口版本是两个不同标识：以下三版设计分别为 `E7070002`、
`E7070003`、`E7070004`，接口仍为 `E7070001`，不是读回旧设计。

| 设计版本 | 本轮主要变化 | 对应该版的自动验证 | 对应该版的真实板卡结论 |
|---|---|---|---|
| E7070002 | 集成 B/C、三模式、CCTL、完整安全链、红2重新选择、分页候选诊断 | Full Compilation 1203.431秒 PASS；R6 245.451876秒、12 PASS + CAUGHT | 21:23 AEDT 下载/读回成功；合成左中右、租约失效、预算结束、真实 IR 和轮向通过；真实蓝1可锁定，但后续候选溢出暴露健康资格永久阻断 |
| E7070003 | 将历史候选溢出诊断与当前健康资格分离；坏帧后建立新边界并等待三相邻新好帧 | 控制236检查 PASS；R6 221.258456秒、12 PASS + CAUGHT；Full Compilation 1154.491秒 PASS | 22:02 AEDT 下载/读回成功；保留历史flags=3仍恢复健康和锁定，无需复位；23个真实不同帧、22次锁定；真实红2暴露“启动早于第三帧锁定”问题 |
| E7070004（当前源码） | 未标定 INTEGRATED 红2必须等新请求目标完成三帧锁定后才启动；健康无目标不能提前消耗授权 | 控制254检查 PASS；R6 219.556074秒、12 PASS + CAUGHT；Full Compilation1121.141秒及门检25.868秒PASS | 22:31:50 AEDT下载/读回成功；真实红2新选择→新锁定→ARM/ALIGN通过；用户确认实物启动及蓝1脱离后停车，末VISION_ONLY/未ARM/左右0 |

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

保留的范围限制是：落地三次一圈标定、六车位闭环、350 mm停靠误差、SW8正常/旁路公平对照、
实物超声危险及无回波边界、不同光照/遮挡，以及历史frame30321蓝6碎裂拒识。
004观察窗口仍有短暂LOST/ACQUIRE，持续视觉稳定性也明确保留。
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
