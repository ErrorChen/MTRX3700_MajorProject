# ECHO-7 version and validation record

This file records executed results and limits. [README.md](README.md) explains the current implementation, operation, requirements and student walkthrough. The only active command entry point is `python tools/echo7.py`; the only current Quartus revision is `quartus/PartBDebug.qpf`.

## Current status: 3 November 2026 (Australia/Sydney)

The source has been reorganised into `rtl`, `quartus`, `tests`, `tools`, `assets`, `docs`, `evidence` and ignored `build`. Obsolete demonstrations and generated files are removed from the active project under the user's cleanup instruction. Git retains the earlier source history. Historical evidence keeps its original contents/hashes; [relocation_index.json](evidence/relocation_index.json) explains former paths.

The deletion audit and preserved differences are in [repository_cleanup.json](evidence/repository_cleanup.json) and [cleanup_reviewed_changes.patch](evidence/cleanup_reviewed_changes.patch). The active layout was committed as `c67b34e`; the user's subsequent commit `63bc383` includes the continuous-replay fixture update. UTF-8/LF rules, exact Python requirements and `tools/check_repository.py` now support repeatable operation. Layout checks remain STRUCTURAL evidence, separate from HDL and hardware checks.

| Layer | Executed result | Boundary |
|---|---|---|
| STRUCTURAL, current layout | PASS: 37 project dependencies and 20 declared RTL benches | `tools/check_repository.py`; dependency checks do not execute those benches |
| MODEL, current reader algorithm 2 | PASS: 64 unittest cases plus 11 vision scenario groups | `build/member_b/20261102T135442_888047Z_test/result.json`; includes fixture-binding and warning-retention tests; camera fixtures are known regression data |
| MODEL, named fixture correction | PASS: nine projective Python tests; 528 existing vector files unchanged | Named aliases verify input source and distinguish original/swapped scenes; separate from full RTL acceptance |
| MODEL_TOOLING, warning retention | PASS: 15 tooling tests | Actual map log now retains all 87 warnings, including two unnumbered PLL-reset warnings; the warnings remain engineering findings |
| ASSET_RECOVERY, current layout | PASS: formal PDF parsed and rendered; six templates regenerated | Same formal PDF hash and geometry; not camera acceptance |
| RTL_SIM, HSV reader before relocation | PASS: 63 vectors, 153,600 exact sample coordinates, all decision/quality/reason fields | Four actual camera images replayed offline, each with eight accepted formal signs; relocated full RTL regression is a separate run |
| RTL_SIM, prior integration revision | PASS: 43 synthetic core frames, late snapshot and 6 continuous alternating frames | Source hashes in retained unified results; later source changes require regression |
| RTL_SIM, relocated short suite | PASS: 11 benches | `20261102T104803_176316Z_test`; includes colour/run filter, CDC, tracker, interaction and debug components |
| RTL_SIM, relocated five-bench attempt | FAIL overall: first three benches PASS, continuous fixture FAIL, collision NOT_RUN | `20261102T104921_481664Z_test`; retain the aggregate failure |
| RTL_SIM, continuous/collision rerun | PASS: both benches | `20261102T110912_418609Z_test`; corrected continuous fixture and explicit newer-drop/older-completion collision |
| RTL_SIM, merged fixes | PASS: all five affected benches | `20261102T112953_869299Z_test`: flattened candidate labels, recorded replay, continuous input, collision and frame profile |
| RTL_SIM, native synchroniser attributes | PASS: CDC transport regression | `20261102T112807_025408Z_test`; this does not replace fitted synchroniser/timing inspection |
| RTL_SIM, VGA mapping | PASS: 307,200 pixels and 165,691 stall cycles | Preserved old/new equivalence and an independent production raster oracle |
| RTL_SIM, native anchor | PASS: 188 ROIs; 166 valid, one ambiguous, one overflow | Portable production bench; maximum 3,697 cycles; this is one module, not the complete current system |
| RTL_SIM, reader algorithm 2 isolated integration | PASS: 71+3 vectors, 239,360 exact grid addresses | Maximum 216,856 cycles; current unified 75-vector/full-core run remains separate |
| RTL_SIM, pipelined native-anchor preparation | PASS: both focused benches; 188 ROIs and 75 reader vectors | 131,072 exact division inputs, 524,288 signed clipping checks and 240,640 exact grid coordinates; maximum reader workload 4.34064 ms |
| RTL_SIM, unified 20-bench attempt | FAIL: shared `expected.hex` fixture collision stopped the first bench | `20261102T125848_299841Z_test`; this failed aggregate remains recorded |
| RTL_SIM, fixture-collision correction | PASS: CCL and VGA contour benches together | `20261102T130527_555927Z_test`; this targeted pass does not replace the full suite |
| RTL_SIM, later full-suite attempt | FAIL: first 11 benches passed, then recorded replay used the wrong positional fixture | `20261102T133108_837984Z_test`; old index 61 was a synthetic rejected-red-digit case, not a camera capture |
| RTL_SIM, corrected full-suite rerun | PASS: all 20 benches, exit 0, suite source hashes unchanged | `20261102T135055_875419Z_test`, 13:50:55–14:03:58 UTC; named source-checked fixtures replace positional indices |
| QUARTUS_FIT_TIMING | FAIL for projective build `0x77744a75`: routing congestion | New shared arithmetic/sequential pairing/HSV source requires a successful complete build; no current timing pass inferred |
| QUARTUS_MAP, later build `0xd606e861` | PASS: 17 DSP blocks, 23,671 registers | Full compile was actively terminated; not a Fitter failure or completed timing result; source line-ending changes prevent current-source attribution |
| POST_MAP diagnostic | Negative timing paths identified in an isolated mapped clone | VGA 71.080 ns / −31.361 ns slack and candidate path 44.603 ns / −24.884 ns slack; not final fitted timing |
| Full build `0xfd9950d9` | TIMEOUT: exit 124 after 3,600 seconds | No completed fit or timing result; residual fitter process was cleaned up after approval review |
| Prior source `0x9c0e0297` | MAP execution PASS; post-map timing diagnostic FAIL: 64.749 ns path, −45.030 ns slack | Retained diagnosis before native-anchor preparation was pipelined; this audit did not start a Fitter run |
| New source `0xe943678b` | MAP execution PASS; preparation path 11.526 ns, remaining worst unrouted setup slack −0.723 ns | Full build `20261102T133904_630682Z_build` is running; no fit/timing acceptance yet |
| PROGRAMMED | Board still runs the earlier stationary camera acquisition baseline | No current B build was fitted/programmed; new B build ID/bitstream must be checked after download |
| CAMERA_HW_PIXELS_ONLY | Seven independent fresh CRC-checked camera inputs retained: 13139, 13511, 13675, 25046, 47630, 2462 and 43817 | Frame-ID wrap is legal; these prove baseline acquisition, while algorithm-2 recognition remains offline MODEL/RTL_SIM |
| MIC_HW | DEFERRED_BY_USER | Direct target numbers exercise the C interface and are not speech recognition |

The current full build, timing, programming and fresh B board acceptance remain open until their own source-linked result JSON records completion. No historical SOF or previous test is silently substituted. `python tools/lib/collect_evidence.py` produces a current file/run index without rewriting the historical records.

[Reader-algorithm-2 validation](evidence/reader_algorithm2_inputs/validation.json) preserves the earlier 60-test MODEL checkpoint, native-anchor RTL result, raw measurements and byte-compatibility checks. Its then-running suite state is historical; [the later checkpoint](evidence/validation_checkpoint_131340.json) records the 61-test MODEL pass, aggregate fixture failure and current map boundary. Explicit reader-1 regeneration reproduces all 63 historical HSV fixtures: 441 binary vector files match byte for byte. The current exporter emits 75 reader fixtures and 188 native-anchor ROIs. Its first 74 cases match the isolated 71+3 set across 518 binary files; the added case tests retirement of more than eight sequential components.

[The completed 20-bench regression](evidence/validation_e943678b_rtl20/index.json) retains the full result JSON, all 20 original simulation logs, exact PASS lines and hashes for 45 source/test files. Those hashes also match the current files at the evidence checkpoint. The same record retains the latest 64-test MODEL result and its 11 vision groups. The recorded-image integration bench passed 33 simulated frames using the source-checked `recorded_frame13675` alias: one actual acquisition replayed repeatedly, not 33 fresh camera captures. Historical failed aggregates remain unchanged.

[validation_checkpoint_63bc383.json](evidence/validation_checkpoint_63bc383.json) links the exact short-suite, failed five-bench attempt, successful collision rerun, stopped build, source-byte comparison and isolated frame-profile proposal.

That retained checkpoint predates the latest merged fixes. The subsequent run paths above are the newer evidence; historical indices are not rewritten to imply they tested later source. The final current-build index will be refreshed when build evidence is available.

## Source and input audit

The initial local baseline was clean on `main` at `1a46e9a49e8ec676cf14e998c04888c4705729bf`. Its configured remote was the user's V2 repository. The requested historical Part A anchor was not present in the local object database, so its ancestry was not invented or forced into the checkout. A 274-file SHA256 comparison found exact source/tool/project/document correspondence with the supplied snapshot. That provenance remains in [metadata.json](evidence/metadata.json); current operation does not depend on an archive or duplicate project tree.

Supplied text inputs were read and retained under [docs/inputs](docs/inputs). The five required original lecture PDFs and formal Major Project Brief were absent. Course page references are therefore mapped from the supplied requirements text, not claimed as independently read primary PDFs. No rubric, required recognition rate, report length or exact deadline was fabricated.

The supplied one-page formal marker PDF was parsed and visually rendered. Its SHA256 is `0162b5a7ada3c7d03dcf96baf5a8a5ce077ff8d165aaad8cc228947ff70436a0`. The original marker JSON/templates were missing; exact vector paths were recovered into the explicitly labelled DESIGN specification. The page remains landscape A4 with one fold, red 1/red 2, six blue digits, white ink and 54 × 60.75 mm main regions. No formal source was replaced with a guessed font or alternative layout.

## Actual image findings and corrections

The retained images came from the actual OV7670 chain, with fresh requests, frame IDs, PNG/dump hashes and CRC checks. [real_inputs/index.json](evidence/real_inputs/index.json) covers the first three complete-page captures; frame 25046 is retained under [hsv_audit](evidence/hsv_audit). All displayed numbers are upright in native coordinates, so the current orientation profile is 0. The external B/C 240 × 320 convention remains unchanged.

The oblique paper produces blue main regions approximately 32–41 pixels wide and 62–71 pixels high. The thinnest measured stroke is about 2 pixels, with others about 3 pixels. The original axis-ratio gate rejected genuine cards; projective normalisation now uses measured colour corners. A direction anchor and exact pixel stroke pattern still determine the answer. Quality is based on measured edges, not an arbitrary cap on every blue sign.

Independent unfiltered white-reference measurements contradicted the earlier floor of 160:

| Raw reference | Samples | Retained at 160 | Retained at 112 |
|---|---:|---:|---:|
| Printed white anchors | 36 | 11.1% | 97.2% |
| Printed white strokes | 316 | 48.7% | 94.9% |
| Blank coloured backgrounds | 281 | 0% | 0% |

The same maximum channel-spread condition of 64 applies. [white_sample_measurements.json](evidence/white_sample_measurements.json), [the selected ROIs](evidence/white_sample_rois.png) and [rectified crops](evidence/projective_contact_sheet.png) preserve the evidence. That correction established reader algorithm 1's minimum-channel floor of 112. It remains reproducible; the later algorithm-2 change below has different, explicitly versioned brightness semantics. Automatic calibration still changes only red/blue value floors.

Two subsequently acquired frames, 47630 and 2462, exposed new failures: algorithm 1 accepted only five and four signs respectively. Real anchor pixels were present, but colour-mask corner shrinkage and normalised sampling missed them. Blue-6 vertical strokes were also only about two native pixels wide and mixed with blue ink. In frame 47630, an unfiltered 18-pixel C-stroke patch had minimum channel 99–107, so the old white predicate erased all 18 pixels. Frame 2462 supplied a separate, dimmer example with continuous stroke brightness around 98–104. [The original failed capture](evidence/camera_counterexample_47630/capture.json) remains unchanged.

Algorithm 2 preserves the original quad, homography and stroke/hole tests. Its fixed white predicate is `R+2*G+B >=384` with channel spread at most 64. It evaluates the anchor as one closed four-connected native white component in a small geometrically derived neighbourhood. Boundary paper and multiple qualifying components reject; active-label overflow rejects; retired noise components do not consume permanent slots. Blind quad expansion was rejected after it falsely accepted missing-anchor and wrong-orientation signs using surrounding paper.

The six independent recorded images each yield red 1/red 2 and blue 1–6 under algorithm 2 in MODEL. [The input index](evidence/reader_algorithm2_inputs/index.json), [raw measurements](evidence/reader_algorithm2_inputs/frame2462_raw_samples.json) and [model comparison](evidence/reader_algorithm2_inputs/algorithm2_model_comparison.png) show the input provenance and effect. All six are now tuning/regression inputs, not an unseen test set. No white auto-calibration or current B board recognition is implied. Native-anchor tests include ambiguity, boundary paper, a harmless isolated speck, ten simultaneous labels and more than eight sequential retired components.

A seventh independent capture, frame 43817, completed a fresh GCTL transaction from count 7 to 8 with matching acknowledgement, stable pre/post snapshot state and CRC `0x1c09`. [Its original pixels, metadata and offline result](evidence/camera_frame43817/index.json) are retained separately. Reader algorithm 2 accepts all eight formal signs and rejects the blank blue strip without candidate overflow in this MODEL run. It has not been added to the frozen production vectors. The FPGA was still running the earlier camera baseline, so this is `CAMERA_HW_PIXELS_ONLY` plus MODEL, not B recognition on the board.

Raw red-1 calibration ROIs contained 210/210/245 samples, with R=66–82; their own geometrically paired blue strip contained 396/396/432 samples, with B=57–66. Purity, range, count and previous-frame ROI stability checks passed in replay. The current formula `(minimum+maximum)>>2` predicts R37/B30. [calibration_profile_audit.json](evidence/calibration/calibration_profile_audit.json) is the historical RGB-mask diagnostic; it is not eight fresh hardware samples or a board commit.

## Orange background, HSV and capacity

The orange object satisfies the old RGB dominance rule. Manually selected raw ROIs from four real frames showed printed-red signed hue approximately −11.6° through 0°, while the orange patch was approximately −0.6° through +12°. Ideal print colour values cannot describe this camera's measured hue distribution.

Current colour algorithm 1 uses red −24° through 0°, blue 200° through 250°, saturation at least 0.5 and boot value floors R48/B32. It uses the [OpenCV RGB-to-HSV definition](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html), with hue in degrees and exact signed cross-products instead of a divider. An independent floating-point HSV comparison covers all 65,536 native RGB565 encodings. Hue zero remains valid for ideal red.

Hue restriction alone fragmented the background: R32/R40 overflowed CAP8 on one earlier frame. R48 with the old cleanup retained all eight signs in four frames, but reducing the floor during calibration could reintroduce that failure. AND-neighbour and 3-of-4 erosion alternatives lost true signs by shrinking corner/anchor evidence and were rejected.

The implemented horizontal filter retains every pixel of a same-colour run of at least three pixels, suppresses shorter runs, then applies the original causal OR support rule. Only candidate extraction sees this filtering; the corner reader uses raw HSV foreground. On all four real inputs, both R48/B32 and calibrated R37/B30 preserve eight formal signs without overflow. At R37 the measured red active peaks are 5/6/6/4; blue peaks are 4/4/5/5. See [horizontal_run_support.json](evidence/hsv_audit/horizontal_run_support.json) and [hsv_model_update.json](evidence/hsv_model_update.json). Runtime algorithm IDs distinguish historical RGB ratio from current HSV replay.

Lighting limits remain real. The historical reader-1 uniform RGB gain trial is labelled synthetic, not a physical lighting experiment: its recorded image retained eight signs at gains 1, 1.25, 1.5 and 2; gain 0.75 avoided overflow but yielded only one sign, and gain 0.5 exceeded blue active-label capacity. Those exact recognition counts have not been relabelled as algorithm-2 results. The new reader improves the measured thin-stroke and anchor failures; it still does not establish general lighting invariance.

## Executed simulation and build failures

Historical reader-1 vectors cover 1–6, red/blue types, unsupported 0/7/8/9, empty blocks, missing anchors, deleted strokes, swapped pixel identities, four orientations, independent perspective poses and four actual captured inputs. That 63-vector run passed 153,600 exact nearest-coordinate checks. Maximum reader time in that set is 198,484 CLOCK_50 cycles, 3,969.68 µs. The current reader-2 exporter has 75 cases, including six separate actual captures and native-anchor negative controls. Both its focused reader test and the complete 20-bench integration suite now pass. These reader-cycle counts exclude acquisition, candidate extraction, CDC, queueing and JTAG transfer.

The completed-frame/drop collision fix gives the newer invalid observation priority over an older completion on the same cycle. It releases the older reader bank but suppresses its report, snapshot publication and calibration advancement. Debug schema 2 word 94 bits 31:16 expose a saturating `completionDiscardCount`; low fault bits retain their previous meanings. This is a counted discard, not a successful observation or a silent report replacement.

Prior integration checks include a 33-frame simulation that repeatedly supplied one actual recorded image through the capture interface. It exercised calibration, version commit, red-2 arming and target 1–6 acquisition. That is explicitly one recorded image repeated, not 33 fresh camera frames. A later frozen unified run passed 43 synthetic frames, loss/recovery, late snapshot and continuous capture/processing with backpressure. Earlier 37/43-frame axis-reader results remain historical and cannot validate the HSV implementation.

After merging flattened candidate aliases and frame-held configuration metadata, the five affected production RTL benches all passed. Candidate extraction checked 26 frames, 51,505 invariant observations, 39 nested merges and a maximum alias count of seven. Recorded replay passed 33 simulated frames using the same stored image; continuous replay passed six frames; collision replay passed two cases and 11 reports; frame-profile replay passed 15 checks and nine accepted completions. None of these counts represents new camera acquisition.

Build `0x77744a75`, source SHA256 `77744a756271bf8182e53b37f6ef9c566e0ca9e122f2c719df050b478a2860ee`, failed routing with Critical Warning 188026 and Warning 16618. It did not exceed declared resource capacity: the failed Fitter reported 25,463/32,070 ALMs, 22,133 registers, 345/397 M10K blocks and 77/87 DSP blocks. Each two-bit glyph bank mapped to 19 M10K blocks. [revision_77744a75](evidence/revision_77744a75) preserves the failure and bounded report excerpts. The implementation now shares arithmetic and sequences reference pairing to reduce parallel routing; estimates or model tests are not a successful Fitter result.

The same build exposed ineffective Gray-bus maximum-skew constraints. A [post-map CDC audit](evidence/cdc_constraint_audit.json) found that asynchronous clock-group cuts suppressed their timed paths and verified a replacement constraint approach in the installed analyser. This diagnostic does not substitute for the final fitted multi-corner setup/hold/recovery/removal review.

The later `0xd606e861` synthesis mapped to 17 DSP blocks instead of the earlier 77. Its full compile was actively stopped, and the raw CLI result records exit 1; this must not be relabelled as a completed Fitter failure. CRLF-to-LF changes altered the source identity while that attempt was outstanding, so its results are not acceptance of the current bytes. [map_warning_audit_d606e861.json](evidence/map_warning_audit_d606e861.json) remains a dated read-only map-stage audit.

An isolated clone of that mapped database identified two costly combinational paths at the slow 1100 mV, 0 °C corner: the VGA coordinate conversion's wide signed division contributes a 71.080 ns data path with −31.361 ns slack, and candidate-root/box logic has a 44.603 ns path with −24.884 ns slack. These are post-map diagnostic estimates, not final post-fit timing. Equivalent arithmetic and candidate-root changes have now been merged and functionally checked; a new full fit must establish timing.

[vga_timing_optimisation.json](evidence/vga_timing_optimisation.json) records exact `(n*683)>>10 == floor(2*n/3)` checks for all 512 bounded inputs, plus old/new equivalence and an independent production raster test over 307,200 pixels with 165,691 stall cycles. The existing 11,200-pixel overlay regression also passed. Native synchroniser attributes were merged and the CDC transport bench passed separately. These checks establish functional behaviour, not post-fit delay or metastability performance.

A separate negative-control bench exposed debug frame-profile mixing: completed frame 1 used config 0 and floors 48/32, while live config had advanced to 1 and floors 37/30; words 6/7 incorrectly exposed the live values. The merged correction stores the effective profile with each bank and publishes it alongside the accepted frame. Production RTL passed 15 profile checks and nine accepted completions; the uncorrected implementation failed the intended control. This is protocol/configuration injection evidence, not image-recognition or board evidence. Live public status keeps its separate `activeCfgVersion` semantics.

Other concrete fixes include explicit enum widths after an actual synthesis error, reserved-identifier corrections after an HDL compiler failure, robust vector filenames, and automation that checks PASS/fatal text as well as exit status. Tests fail nonzero and retain their source hashes. A testbench changed during one earlier aggregate run; that run remains FAIL, and its affected benches were rerun with frozen source instead of relabelling it.

The subsequent full build `0xfd9950d9` reached its 3,600-second timeout and returned 124. Available-memory observations were 495–838 MiB, with fitter private memory around 2,349 MiB. This demonstrates memory pressure but does not establish a sole cause or final timing outcome. The residual fitter process was terminated after approval review. [timeout_build_fd9950d9.json](evidence/timeout_build_fd9950d9.json) retains the source identity and surviving reports; there is no fitted result or downloaded bitstream from that attempt.

The current QSF uses two parallel processors and `AUTO FIT` effort according to the installed Quartus 18.1 option help. Auto effort can reduce further effort after timing requirements are met; the SDC remains the acceptance boundary. The completed [0x9c0e0297 post-map diagnostic](evidence/post_map_9c0e0297.json) kept the same source identity before and after execution and did not start fitting. It exposed native-anchor ROI preparation at 64.749 ns with −45.030 ns setup slack at slow 1100 mV, 0 °C; an internal anchor path also had −0.024 ns slack.

[The preparation correction](evidence/native_anchor_preparation_fix.json) registers the accepted quad, vertex arithmetic, balanced extrema and clipped ROI, with exact four-lane 17-step division by 40. The two focused RTL benches passed 188 ROIs, 75 reader cases and 240,640 exact homography-coordinate checks. Exhaustive checks covered all 131,072 unsigned 17-bit divider inputs and 524,288 signed clipping cases, together with start-input mutation and reset cases. Geometry and algorithm semantics remain unchanged. Preparation adds 22 cycles per candidate; the worst tested complete reader workload rose to 217,032 cycles, or 4.34064 ms at 50 MHz.

[The subsequent 0xe943678b map diagnostic](evidence/post_map_e943678b.json) reduces the preparation path to 11.526 ns. The remaining overall unrouted setup slack is −0.723 ns on a candidate path, and an internal anchor path remains at −0.412 ns. These are diagnostic estimates, not fitted acceptance. The source-linked full build `20261102T133904_630682Z_build` is running at this checkpoint; its result is still pending.

The first unified 20-bench attempt stopped when the contour exporter overwrote the candidate bench's generic `expected.hex`. [The retained namespace regression](evidence/vector_namespace_regression.json) records the failure, separate contour filenames and the subsequent combined CCL/VGA RTL pass. A later attempt passed its first 11 benches but failed recorded replay: positional index 61 now referred to the synthetic `red_rejected_3_4_5_6` case. That attempt did not test the intended recorded camera input and remains FAIL.

[The named-fixture correction](evidence/named_fixture_regression.json) checks source labels and PNG hashes, selects recorded frames by name, and makes continuous replay alternate the original and swapped-pixel scenes with different blue-1 positions. Nine projective Python tests passed; all 526 original projective hex files and both anchor files stayed byte-identical. Production RTL was unchanged. The corrected full 20-bench run `20261102T135055_875419Z_test` subsequently completed with exit 0 and every bench PASS. It includes 43 synthetic core frames, 33 repeated recorded frames, six alternating continuous frames, collision/profile checks, VGA stalls and both native-anchor/reader benches.

[Host warning retention](evidence/host_warning_retention.json) passed 15 tooling tests. Re-reading the actual map log now preserves 87 warnings instead of 85, including two unnumbered warnings about the inherited VGA PLL reset connection. Retaining these messages is a tooling correction, not resolution of the hardware warnings or timing approval.

The new VGA path separates raw HSV contours from accepted digit labels. Separate same-colour regions retain their pixel boundaries; the blank calibration strip receives a contour but no ID. [vga_contour_validation.json](evidence/vga_contour_validation.json) records 931,600 contour pixels, 395,588 stalled cycles, input bubbles, combined-label checks and isolated synchronous row-RAM inference. A real consecutive-SOP metadata-overwrite failure was reproduced and fixed. These are simulation/isolated-map results, not current physical VGA or complete fitted timing acceptance.

## Remaining acceptance and continuation

The current source has completed its full RTL and MODEL regressions. Source `0xe943678b` still requires a successful complete Quartus fit/timing result, followed by a fresh .sof download, matching on-board build/schema and current B captures. Its full build is still running at this checkpoint. The fixed-sheet acceptance then needs at least 30 distinct new frames, configuration/overflow evidence and reports for targets 1–6. Thirty is an initial project debugging threshold, not a course rubric or generalised accuracy claim. Any further source correction requires the relevant regression before a new matching build.

Physical occlusion/folding, different real illumination conditions and microphone words remain unexecuted or deferred unless later evidence explicitly records them. A person performs physical page changes. No hidden historical frame or held snapshot substitutes for a new observation.

Continue from the repository root:

```powershell
& 'C:/Users/15402/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/echo7.py autodebug
```

Use that command's JSON to identify the next actual failing layer. New source changes require the relevant regression and a new matching build/program/capture cycle before claiming hardware completion.
