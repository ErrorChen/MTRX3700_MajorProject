# Version history and validation / 版本与验证记录

This is the consolidated history of Member B. Entries below run from the earlier
baseline to the latest work. Build identities, failed experiments and evidence
levels are kept separate. README.md is the maintained bilingual development and
B/C interface guide; OWNERS.md records individual-file responsibility and origin.

这是按开发先后整理的版本记录。MODEL、RTL_SIM、拟合、下载、相机实测和用户确认的
实体VGA分别记录；历史通过不能证明后续源码通过。课程要求、用户需求和设计选择也不混用。

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
It is retained at docs/reference/Major_Project_Brief_2026.pdf. The three-person
proposal is a separate reference, not a rubric. The five lecture PDFs remain
under docs/reference with their original filenames and unchanged bytes.

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
Reference PDFs remain under docs/reference; formal marker artwork remains under
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

### Current-source completion record

IN_PROGRESS: append final source/SOF identity, executed tests, fit/program and
new-camera results here before delivery. Microphone input remains deferred by
the user. Human ownership/sign-off, new physical occlusion/lighting-range tests
and whole-team integration remain separate responsibilities.
