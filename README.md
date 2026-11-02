# ECHO-7 Member B

This repository contains the stationary MTRX3700 Member B perception demonstration: camera-based red/blue sign recognition, automatic colour-floor calibration, target selection and tracking, VGA feedback, and reproducible JTAG evidence. Member C owns movement, steering, chassis communication, stopping and navigation. `perceptionDemoTop` does not instantiate a motor controller or drive chassis signals.

The maintained entry point is `python tools/echo7.py`. [VERSION_README.md](VERSION_README.md) records actual checks, failed builds, hardware evidence and remaining limits. These are the two maintained README files. The single B/C contract is [docs/MEMBER_C_INTERFACE.md](docs/MEMBER_C_INTERFACE.md).

The verified board checkpoint is `0xab41e932`: isolated Quartus 18.1 compilation, four-corner timing, the extra CDC checks and actual FPGA download all passed. [The compiler recovery record](evidence/compiler_recovery/index.json) retains the routing fix, final resources and bitstream identity. The preceding RTL checkpoint passed all [20 self-checking benches](evidence/validation_e943678b_rtl20/index.json); its production RTL was unchanged by the constraint and host-tool recovery.

[Fresh camera frame 225](evidence/board_ab41e932_frame225/index.json) passed CRC, build/schema and same-frame pixel-model comparison for ten candidates. The FPGA accepted red 1/2 and blue 1–5, but rejected blue 6; calibration remained incomplete. The full-sheet hardware test therefore failed after its first sampled status frame. Compilation and download are recovered; complete recognition, calibration and the 30-frame target cycle remain unfinished. Voice input is deferred by the user.

## Start here

Use a verified Python installation with NumPy and Pillow. The inspected Windows machine uses the following executable; the initial PATH Python entries were Windows Store aliases.

Exact Python dependency versions are recorded in [requirements.txt](requirements.txt). `.editorconfig` and `.gitattributes` define UTF-8/LF source conventions. `python tools/check_repository.py` checks the single-project layout, explicit dependency closure and ignore rules; it does not simulate or build the FPGA.

```powershell
$python = 'C:/Users/15402/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $python tools/echo7.py doctor
& $python tools/echo7.py test --replay
& $python tools/echo7.py test --rtl
& $python tools/echo7.py --quartus-bin 'C:/intelFPGA_lite/18.1/quartus/bin64' --timeout 3600 build
& $python tools/echo7.py program
& $python tools/echo7.py capture --fresh
& $python tools/echo7.py status
```

`doctor` discovers executable paths, versions, the actual JTAG chain and project inputs. The inspected tools are Quartus Prime 18.1 Lite and ModelSim Altera Starter Edition 10.5b; another installation must be discovered and validated. External commands use argument arrays, including paths with spaces. CLI results are JSON: exit 0 means an executed pass, 1 means failure, and 2 means an external block or explicitly deferred function. A Python model pass is not an RTL simulation pass.

```powershell
& $python tools/echo7.py select --bay 3
& $python tools/echo7.py orientation --profile 0
& $python tools/echo7.py calibrate --arm
& $python tools/echo7.py test --hardware
& $python tools/echo7.py autodebug
```

Selection is a request to the non-motion C simulator; recognition still reads pixels. Voice-input testing is deferred at the user's request. A selected number, key press or debug command must not be labelled speech recognition. Calibration arming permits another real red-1 interaction and does not inject a successful calibration.

`build` targets only [quartus/PartBDebug.qpf](quartus/PartBDebug.qpf), top `perceptionDemoTop`, device 5CSEMA5F31C6. Programming requires a successful current build, a fresh bitstream hash and an unambiguous discovered FPGA target. Program and capture use the same selected cable/device; the chain index is not hard-coded. The actual OV7670 MVFP value is passed explicitly as 0x07. Configuration, download, camera acquisition and recognition are separate acceptance steps.

Each build copies the exact hashed source closure into its own `build/member_b/<run>/source/` tree. Quartus databases, generated IP, reports and the SOF belong to that private copy. The original project and any GUI database are not reused. The selected Quartus installation also supplies the child-process Quartus/Qsys environment and companion tools; global environment variables are unchanged. RUNNING provenance records the source, project directory and actual tool version before compilation starts. Failed compiles retain their warnings and nonzero exit code. The successful manifest supplies the private SOF path to `program`.

A fresh capture must pass frame, packet schema and CRC checks, and its on-board build ID must agree with the programmed source. A held snapshot is an old observation and cannot count towards another tracking frame. JTAG file transfer duration is not FPGA processing latency. Large temporary outputs belong in ignored `build/`; small retained examples and indices belong in `evidence/`.

## Current layout and history

| Directory | Purpose |
|---|---|
| `rtl/` | Current capture, vision, interaction, tracking, debug and top modules |
| `quartus/` | The single current Quartus project, constraints and editable VGA Qsys source |
| `tests/rtl/` | Executed self-checking HDL benches and their manifest |
| `tests/python/` | Reference, counterfactual, protocol and tooling tests |
| `tools/` | CLI, capture/Tcl tools and implementation helpers in `lib/` |
| `assets/markers/` | Formal one-page artwork, recovered geometry, templates and labelled synthetic replay |
| `docs/` | Current B/C contract; original supplied documents under `inputs/` |
| `evidence/` | Small immutable historical results and current evidence indices |
| `build/` | Ignored compiler databases, bitstreams, vectors, recordings and detailed run logs |

The source baseline is commit `1a46e9a49e8ec676cf14e998c04888c4705729bf`. The user-authorised cleanup removed obsolete demonstration trees and generated clutter after Git-content and dependency checks; [repository_cleanup.json](evidence/repository_cleanup.json) and [the reviewed changes](evidence/cleanup_reviewed_changes.patch) preserve that decision. Commit `c67b34e` records the active Member B layout, followed by the user's `63bc383` cleanup/fixture commit. Git retains earlier history. The project is derived from the repository identified in the supplied source notes, not from a replacement starter archive. An initial 274-file byte comparison established correspondence with the supplied source snapshot; it did not establish authenticated remote ancestry. [metadata.json](evidence/metadata.json) preserves that historical audit.

Historical JSON/log contents and their original source hashes remain unchanged. [relocation_index.json](evidence/relocation_index.json) maps former paths to their current locations. `python tools/lib/collect_evidence.py` writes a current index without rewriting historical evidence or requiring removed demonstration directories.

## Printed sheet and coordinates

Print [ECHO7_All_Markers_A4_v2.pdf](assets/markers/ECHO7_All_Markers_A4_v2.pdf) in colour at 100% actual size. It is one landscape A4 page, 297 × 210 mm, with fold x=148.5 mm. The left half has red 1 with its own blue reference strip and red 2; the right half has blue 1–6 in two columns and three rows. The formal main rectangle is 54 × 60.75 mm. Colours are #C00000, #0057B8 and white. Printed colour values are not camera RGB thresholds.

[marker_spec.json](assets/markers/marker_spec.json) and [scene_manifest.json](assets/markers/scene_manifest.json) were recovered from exact paths in the supplied PDF because the original taskpack JSON was absent. They are explicitly labelled `RECOVERED_FROM_SUPPLIED_PDF` and DESIGN recovery. The manifest supplies test expectations only. No runtime identity comes from a sheet slot, candidate order or expected answer.

The digit ROI is fixed relative to the coloured main rectangle; digit 1 is not recentered around its narrow strokes. The independent top-left white anchor establishes orientation. The PDF, SVG, PNG and six templates remain together. `python assets/markers/recover_from_pdf.py` reproduces them using pypdf, Pillow and Poppler. The synthetic `sheet_320x240.png` and RGB565 `.hex` are logical pixel replay, not a complete sensor bus stream or a real camera capture.

The default scene keeps the whole page unfolded and fixed. Folding is an optional physical test performed by a person. Native camera coordinates remain 320 × 240; the external B/C frame remains 240 × 320. Transform bbox endpoints before rounding the centre:

```text
uMin = yMin                 uMax = yMax
vMin = 319 - xMax           vMax = 319 - xMin
centreU = floor((uMin + uMax)/2)
centreV = floor((vMin + vMax)/2)
```

The current real samples show upright native digits, so `orientationProfile=0`. Internal glyph rotation, external B/C coordinates and VGA presentation are separate transforms. Oblique camera placement is supported through projective sampling; finite pixel detail still limits useful angles and distances.

## Processing and timing

| Modules | Responsibility and invariant |
|---|---|
| `capture/ov7670_*`, `cameraStreamBridge`, `common/asyncPixelFifo` | Reuse the actual camera configuration/receiver; preserve frame metadata and coherent pixel transfer |
| `vision/hsvColourGate`, `horizontalRunFilter`, `causalMaskCleanup`, `boundedCandidates` | Classify colour, retain supported horizontal runs, suppress isolated pixels and form bounded main-region candidates |
| `vision/glyphBanks` | Two 320 × 240 banks, each with white and raw-colour foreground bits; 37.5 KiB logical capacity |
| `vision/projectiveMarkerReader` | Recover foreground corners, normalise perspective and classify pixel-derived strokes/anchor/holes |
| `vision/nativeAnchorReader` | Check an isolated native white component in a small corner neighbourhood; reject boundary paper, ambiguity and active-label overflow |
| `interaction/colourSampler`, `fixedSheetInteraction` | Pair red 1 with its own reference, sample raw RGB, validate and atomically commit a complete colour profile |
| `tracking/targetTracker`, `debug/memberCSimulator` | Accept public requests, report only current observations and enforce acquisition/loss/age rules |
| `debug/memberBDebug`, `frame_snap` | Acknowledged debug controls and same-frame snapshots |
| `debug/memberBVgaContour`, `memberBVgaLabels`, `memberBVgaOverlay` | Raw HSV region contours and separate accepted pixel-derived digit labels, with coherent frame metadata and stalled-stream handling |
| `top/perceptionCore`, `perceptionDemoTop` | Integratable CLOCK_50 core and isolated board wrapper |

Current colour algorithm 1 uses red signed hue −24° through 0°, blue hue 200° through 250°, saturation at least 0.5, and initial value floors red=48/blue=32. Signed integer cross-products implement HSV without division. This measured narrow red interval rejects most of the observed orange background; it is not a general lighting-invariance claim. Algorithm 0 remains explicit in historical host replay only.

Before candidate extraction, both colours retain complete horizontal runs of at least three pixels, then use the inherited causal left-or-above support rule. The raw colour bit stored for corner extraction is not eroded by these filters. Candidate capacity remains eight per colour. Noise, active labels and completed candidates are measured independently; overflow invalidates the frame. The row-reclaimed extractor requires its real row-maintenance gap and must not be validated with a fictitious zero-gap input stream.

Reader algorithm 2 finds four actual foreground corners using normalised diagonal extrema, checks convexity and geometry, and maps a 32 × 40 canonical grid through an integer homography into the same-frame white bank. Shared sequential arithmetic controls resource cost. Exact seven-stroke projections and two empty-hole checks use that grid. The independent direction anchor is checked in native pixels, where its small separation from surrounding paper is still present. Blue accepts 1–6; red accepts functions 1/2. The blank blue calibration strip is not a bay. Geometry requires edges of at least 24 pixels; any edge below 40 pixels caps quality at 192.

`nativeAnchorReader` scans a corner neighbourhood derived from the oriented colour quad. A qualifying four-connected white component must be closed inside that neighbourhood, contain at least three native pixels spanning two rows and two columns, and satisfy bounded size/area checks. Exactly one may qualify. Boundary-connected paper, multiple qualifying blocks and active-label overflow reject. Completed components retire; more than eight sequential small components do not alone cause overflow. This uses the existing white bank and a bounded row-label table, not another RGB frame.

Anchor preparation captures the quad at request acceptance, registers vertex arithmetic and extrema, performs exact division by 40 over 17 steps, then registers the clipped ROI. Exhaustive arithmetic and input-mutation tests preserve the original geometry. This adds 22 cycles per candidate; the largest tested complete reader workload takes 217,032 CLOCK_50 cycles, or 4.34064 ms, excluding capture, candidate extraction and transport.

Timing-oriented changes preserve the observable results: the candidate extractor maintains flattened label aliases, and the VGA paths use an exact bounded unsigned multiply/shift for the two-thirds coordinate mapping instead of wide signed division. The label invariants, all 512 relevant arithmetic inputs and complete stalled VGA frames were tested. These equivalence checks do not establish final FPGA timing.

Algorithm 2's fixed white predicate is `R + 2*G + B >= 384` and `max(R,G,B)-min(R,G,B) <= 64`: weighted brightness at least 96, with bounded channel spread. Independent raw samples from two new camera counterexamples showed that the earlier minimum-channel rule erased thin blue-6 strokes. This is a fixed empirical white profile. Automatic calibration changes only red/blue value floors; white auto-calibration is not implemented.

Historical reader algorithm 1 remains explicit in host replay as `--reader-algorithm 1`, with its original `min(R,G,B) >=112` default. The current model defaults to algorithm 2. Debug reader IDs and white-profile modes prevent old captures from silently acquiring the new meaning.

VGA contours follow raw red/blue HSV transitions, including separate regions of the same colour and the blank blue reference strip. Contours indicate colour segmentation only. Digit labels require accepted pixel-derived markers; a blue outline does not grant a bay ID. A 640 × 2-bit synchronous row memory supports contours without another full-colour frame. This logic is included in the fitted and programmed `0xab41e932` checkpoint. The appearance of that new output on the physical monitor still needs visual confirmation; a JTAG camera image is not a VGA screenshot. Upstream display-buffer tearing remains a separate limitation.

Bank ownership separates FREE, WRITING, READY and READING. Candidate frame ID, original capture time, configuration version and bank identity remain bound to the pixels. A busy bank causes an explicit full-frame drop, never a read of overwritten data. Multi-bit descriptors and configurations use a handshake or FIFO; independently synchronising each bit is not atomic transfer. Final BRAM/resource mapping and all relevant timing checks require a successful current Fitter run.

The held-payload crossings `resultToCamera` and `cameraBridge|requestCdc` retain their 20 ns maximum-delay bound and an explicit 20 ns physical net-delay bound. Only their artificial same-edge inter-clock hold check is excluded: the handshake keeps data stable until acknowledgement returns through the source synchroniser. Synchroniser stage-to-stage checks and the Gray-bus maximum-delay, minimum-delay and skew constraints remain active. The recovery timing gate checks this exact coverage; the exception is not a blanket clock-domain cut or a fitted timing pass.

## Interaction and Member C

[docs/MEMBER_C_INTERFACE.md](docs/MEMBER_C_INTERFACE.md) and [perception_pkg.sv](rtl/common/perception_pkg.sv) are the single behavioural/type contract. Version 2 uses targetRequest=22 bits, targetReport=139 bits, userEvent=104 bits and perceptionStatus=76 bits. All public channels are in CLOCK_50 with shared synchronous reset and `timeUs`.

SELECT and CLEAR are distinct operations. `activeBayMask=10'h07E` permits only IDs 1–6. Three valid/ready channels hold valid and complete payload through backpressure; valid does not wait for ready. A presented report cannot be overwritten, a replaceable pending report counts its replacement, and events cannot disappear silently. Camera capture continues independently of C readiness.

A unique observed target locks only after three consecutive distinct good frames. A new request, configuration change, missing/bad frame or same-ID ambiguity immediately clears acquisition history. When observed is false, public centre, dimensions and quality are zero. C checks current tag, configuration and age from original `captureStartUs`, including while no new report arrives. The initial 150 ms age budget is not a measured latency guarantee; wraparound is legal.

When a newer capture-drop observation and an older processing completion arrive on the same cycle, the newer invalid observation takes priority. The older reader bank is still released, but its result cannot overwrite the newer loss or advance calibration. This is separately tested from ordinary report backpressure.

Fixed-sheet mode sequences resident red cards instead of declaring a permanent conflict: identify red 1 and its own blue reference; collect eight valid stable raw sampling frames; commit the entire shadow profile at SOP; then recognise red 2 under the new version and arm interaction. Red 1 staying visible does not repeatedly recalibrate. Sample failure preserves the old complete profile. Permit revocation cancels uncommitted work; a revocation already observed in the commit domain takes priority. Idle arming is separate from busy sampling/classification.

Microphone input and vocabulary acceptance are deferred. The earlier microphone sources were statically reviewed before cleanup and their hashes/findings remain in historical evidence. No activity gate, debug digit, synthetic PCM or selected target is presented as recognition of spoken numbers.

## Debug schema and frame identity

The public B/C contract remains version 2. The private BCTL/EBP1 debug schema is version 2, with a 96-word frozen status payload. BCTL uses whole-word stability followed by a held toggle/acknowledgement transaction. SELECT/CLEAR acknowledgement occurs only when the C simulator accepts the request; address changes can read another frozen word without issuing a new command.

| EBP1 word | Meaning |
|---|---|
| 0–1 | Magic `0x45425031`, debug schema 2 and contract 2 |
| 2–5 | Snapshot time, completed native frame ID, its original capture time and completion time |
| 6–7 | Configuration version, orientation and red/blue floors belonging to that completed frame's bank |
| 8–9 | Whole-frame buffer-drop count and red/blue candidate counts |
| 10–12 | Live public status, including current `activeCfgVersion` |
| 24–87 | Sixteen colour-typed candidate/marker slots, with pixel-derived digit, quality and native bbox |
| 91–93 | Completed-frame validity, source build ID and peak active label counts |
| 94 | Bits 31:16 saturating `completionDiscardCount`; bits 15:4 reserved zero; bits 3:0 transport/candidate fault diagnostics |
| 95 | `{colourAlgorithm[7:0], readerAlgorithm[7:0], whiteMinimum[7:0], whiteMaxSpread[7:0]}`; current values are 1/2/96/64, with weighted-luma semantics for reader 2 |

`completionDiscardCount` counts older processing completions discarded by newer-drop arbitration. It is distinct from dropped capture frames and overwritten pending reports. Word 94 low bits remain bit3 transport-fault history, bit2 candidate overflow, bit1 candidate error and bit0 candidate overrun. Schema 1 historical packets use the old word-95 interpretation and must not be silently interpreted as HSV.

A configuration may change while an earlier frame is still being processed. Debug words 6/7 therefore describe that frame's bank-held profile; live status can already report a newer version. A negative-control bench exposed the former use of live values. The correction is merged and its production RTL passed 15 profile checks across nine accepted completions, followed by the affected integration regression. Fresh board frame 225 verifies the binding at configuration 0; a successful real calibration/version transition remains unverified.

A full image GRAB appends native frame binding and build identity as words 96/97. The host checks those against the 96-word payload, target report, programmed source and packet CRC before comparing the captured pixels with the explicitly selected colour/reader algorithms.

The current QSF uses two parallel processors and `FITTER_EFFORT="AUTO FIT"`, as checked against the installed Quartus 18.1 help. Automatic effort may reduce additional optimisation once timing requirements are satisfied; it does not relax the SDC or make an incomplete fit acceptable. A prior 60-minute timeout under measured memory pressure is recorded separately from routing failure and timing failure.

Build `0xab41e932` completed in 16 minutes 32 seconds, using 17,519 ALMs, 347/397 M10K blocks and 29/87 DSP blocks. Its worst four-corner setup/hold slacks are +3.205/+0.119 ns. [The 96-warning review](evidence/compiler_recovery/warning_review_ab41e932.json) accounts for all messages rather than suppressing them. Inherited PLL loss-of-lock recovery and default drive/slew settings remain explicit limitations.

## Requirements traceability

COURSE references below come from the supplied [requirements map](docs/inputs/COURSE_REQUIREMENTS.md). The five original lecture PDFs and formal Major Project Brief were not available; their page contents have not been independently verified here. No rubric, compulsory accuracy rate, report length or deadline has been invented.

| Class/source | Requirement | Concrete implementation/evidence |
|---|---|---|
| COURSE: L1 pp15,18 | Incremental work, division of ownership, progress, consistent style and recoverable baseline | Git history, this source map, version record and source-linked runs |
| COURSE: L1 p19 | Understand and verify AI output; retain an AI appendix | Review notes below, real self-checks, recorded failures and corrections |
| COURSE: Digital Programming pp42–43,46 | Distinguish simulation, synthesis, fit, timing and configuration; inspect hierarchy/resources | CLI evidence layers and Fitter resource/timing gates |
| COURSE: HDL pp15,18,49 | Explicit widths/signs/parameters and assignment discipline | Shared typed package, nonblocking sequential state, complete combinational assignments |
| COURSE: Modular/Testbench pp35–36 | Self-checking benches and assertions | Executed ModelSim benches; DESIGN adds nonzero automation failures and PASS-marker checks |
| COURSE: Modular/Testbench pp37–40,47–51 | Avoid latches; synchronous RAM and mapped BRAM | Explicit ownership/read latency; resource evidence retained per build |
| COURSE: FPGA Design pp28,46 | Synchronise asynchronous events; use board tools | FIFO/handshake CDC and ISSP/JTAG; multi-bit atomicity is an additional DESIGN rule |
| USER: active signs and fixed page | Only blue 1–6, red 1/2, one foldable landscape page | Formal artwork, pixel templates, unknown/type/counterfactual tests |
| USER: perspective and current observation | Read identity from pixels and tolerate oblique imaging | Real crops, projective warps, swapped/deleted strokes, quality/rejection and tracking tests |
| USER: evidence and scope | Fresh capture, overflow/configuration/report evidence; no motion and postponed speech | Current wrapper, C simulator and separately labelled acceptance layers |
| DESIGN: consistent capture | Same-frame bank/config/time association and complete-frame drops | CDC, reader, late-snapshot and continuous-frame benches |
| DESIGN: empirical HSV/support | Separate observed orange and control fragmented candidates without positional answers | Raw ROI statistics, full-frame CAP8 checks and exhaustive RGB565 HSV tests |

The course examples permit relevant `$display`, `$signed` and memory initialisation uses; no unrelated assignment-wide ban has been imported.

## Student walkthrough and AI appendix

Begin with the sheet: colour proposes a region; white pixels supply the number. Explain why the blue reference has no identity and why a slot cannot answer a digit test. Show a native oblique crop and its rectified white samples. Interpolation adds no optical detail; two-pixel strokes justify cautious quality and rejection.

Follow one frame through the FIFO, candidate extractor, owned bank and projective reader. Show its capture timestamp/configuration on the final report. Select a bay through the C simulator, observe three-frame acquisition, then demonstrate loss, ambiguity or a changed request using a self-checking replay. Inspect a stalled valid/ready transaction: the visible payload must stay unchanged.

Explain the one-shot red-1 calibration and red-2 arming sequence using its actual simulation/hardware layer. Show one source build ID and bitstream hash before displaying fresh camera evidence. A download proves configuration; it does not prove successful recognition. Report the current limitations from VERSION_README, including deferred microphone input and unexecuted physical tests.

OpenAI Codex assisted the implementation, tests, recovered assets, debugging and documentation. Student ownership and human review must be recorded separately; these files do not imply a human sign-off. Original supplied notices are retained in [docs/inputs/OWNERS.md](docs/inputs/OWNERS.md) and [AI_STATEMENT.md](docs/inputs/AI_STATEMENT.md). The version record preserves incorrect initial assumptions, real failed checks and the tests used to verify corrections.
