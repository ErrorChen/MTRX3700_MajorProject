# ECHO-7 version and validation record

This file records executed results and limits. [README.md](README.md) explains the current implementation, operation, requirements and student walkthrough. The only active command entry point is `python tools/echo7.py`; the only current Quartus revision is `quartus/PartBDebug.qpf`.

## Current status: 2 November 2026

The source has been reorganised into `rtl`, `quartus`, `tests`, `tools`, `assets`, `docs`, `evidence` and ignored `build`. Obsolete demonstrations and generated files are removed from the active project under the user's cleanup instruction. Git retains the earlier source history. Historical evidence keeps its original contents/hashes; [relocation_index.json](evidence/relocation_index.json) explains former paths.

| Layer | Executed result | Boundary |
|---|---|---|
| MODEL, current layout | PASS: 37 unittest cases plus 11 vision scenario groups | `build/member_b/20261102T104001_122301Z_test/result.json`; synthetic and recorded inputs are labelled |
| ASSET_RECOVERY, current layout | PASS: formal PDF parsed and rendered; six templates regenerated | Same formal PDF hash and geometry; not camera acceptance |
| RTL_SIM, HSV reader before relocation | PASS: 63 vectors, 153,600 exact sample coordinates, all decision/quality/reason fields | Four actual camera images replayed offline, each with eight accepted formal signs; relocated full RTL regression is a separate run |
| RTL_SIM, prior integration revision | PASS: 43 synthetic core frames, late snapshot and 6 continuous alternating frames | Source hashes in retained unified results; later source changes require regression |
| QUARTUS_FIT_TIMING | FAIL for projective build `0x77744a75`: routing congestion | New shared arithmetic/sequential pairing/HSV source requires a successful complete build; no current timing pass inferred |
| PROGRAMMED | Earlier camera acquisition baseline was configured | The failed B build was not programmed; new B build ID/bitstream must be checked after download |
| CAMERA_HW | Fresh CRC-checked camera inputs retained, including frames 13139, 13511, 13675 and 25046 | These prove real acquisition; offline recognition is MODEL/RTL_SIM, not current B on-board recognition |
| MIC_HW | DEFERRED_BY_USER | Direct target numbers exercise the C interface and are not speech recognition |

The current full build, timing, programming and fresh B board acceptance remain open until their own source-linked result JSON records completion. No historical SOF or previous test is silently substituted. `python tools/lib/collect_evidence.py` produces a current file/run index without rewriting the historical records.

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

The same maximum channel-spread condition of 64 applies. [white_sample_measurements.json](evidence/white_sample_measurements.json), [the selected ROIs](evidence/white_sample_rois.png) and [rectified crops](evidence/projective_contact_sheet.png) preserve the evidence. The fixed floor is now 112. Automatic calibration still changes only red/blue value floors; white calibration has not been silently added.

Raw red-1 calibration ROIs contained 210/210/245 samples, with R=66–82; their own geometrically paired blue strip contained 396/396/432 samples, with B=57–66. Purity, range, count and previous-frame ROI stability checks passed in replay. The current formula `(minimum+maximum)>>2` predicts R37/B30. [calibration_profile_audit.json](evidence/calibration/calibration_profile_audit.json) is the historical RGB-mask diagnostic; it is not eight fresh hardware samples or a board commit.

## Orange background, HSV and capacity

The orange object satisfies the old RGB dominance rule. Manually selected raw ROIs from four real frames showed printed-red signed hue approximately −11.6° through 0°, while the orange patch was approximately −0.6° through +12°. Ideal print colour values cannot describe this camera's measured hue distribution.

Current colour algorithm 1 uses red −24° through 0°, blue 200° through 250°, saturation at least 0.5 and boot value floors R48/B32. It uses the [OpenCV RGB-to-HSV definition](https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html), with hue in degrees and exact signed cross-products instead of a divider. An independent floating-point HSV comparison covers all 65,536 native RGB565 encodings. Hue zero remains valid for ideal red.

Hue restriction alone fragmented the background: R32/R40 overflowed CAP8 on one earlier frame. R48 with the old cleanup retained all eight signs in four frames, but reducing the floor during calibration could reintroduce that failure. AND-neighbour and 3-of-4 erosion alternatives lost true signs by shrinking corner/anchor evidence and were rejected.

The implemented horizontal filter retains every pixel of a same-colour run of at least three pixels, suppresses shorter runs, then applies the original causal OR support rule. Only candidate extraction sees this filtering; the corner reader uses raw HSV foreground. On all four real inputs, both R48/B32 and calibrated R37/B30 preserve eight formal signs without overflow. At R37 the measured red active peaks are 5/6/6/4; blue peaks are 4/4/5/5. See [horizontal_run_support.json](evidence/hsv_audit/horizontal_run_support.json) and [hsv_model_update.json](evidence/hsv_model_update.json). Runtime algorithm IDs distinguish historical RGB ratio from current HSV replay.

Lighting limits remain real. Uniform RGB gain is labelled synthetic, not a physical lighting experiment. The latest recorded image retains eight signs at gains 1, 1.25, 1.5 and 2. At gain 0.75, horizontal support prevents overflow but only one sign passes; most others fail white-anchor evidence and one blue region is truncated. Gain 0.5 still exceeds the blue active-label capacity. This implementation improves observed orange separation and noise handling; it does not establish general lighting invariance.

## Executed simulation and build failures

Current reader vectors cover 1–6, red/blue types, unsupported 0/7/8/9, empty blocks, missing anchors, deleted strokes, swapped pixel identities, four orientations, independent perspective poses and four actual captured inputs. The optimised reader's 63-vector run passed 153,600 exact nearest-coordinate checks. Maximum reader time in that set is 198,484 CLOCK_50 cycles, 3,969.68 µs. This excludes acquisition, candidate extraction, CDC, queueing and JTAG transfer.

Prior integration checks include a 33-frame simulation that repeatedly supplied one actual recorded image through the capture interface. It exercised calibration, version commit, red-2 arming and target 1–6 acquisition. That is explicitly one recorded image repeated, not 33 fresh camera frames. A later frozen unified run passed 43 synthetic frames, loss/recovery, late snapshot and continuous capture/processing with backpressure. Earlier 37/43-frame axis-reader results remain historical and cannot validate the HSV implementation.

Build `0x77744a75`, source SHA256 `77744a756271bf8182e53b37f6ef9c566e0ca9e122f2c719df050b478a2860ee`, failed routing with Critical Warning 188026 and Warning 16618. It did not exceed declared resource capacity: the failed Fitter reported 25,463/32,070 ALMs, 22,133 registers, 345/397 M10K blocks and 77/87 DSP blocks. Each two-bit glyph bank mapped to 19 M10K blocks. [revision_77744a75](evidence/revision_77744a75) preserves the failure and bounded report excerpts. The implementation now shares arithmetic and sequences reference pairing to reduce parallel routing; estimates or model tests are not a successful Fitter result.

The same build exposed ineffective Gray-bus maximum-skew constraints. A [post-map CDC audit](evidence/cdc_constraint_audit.json) found that asynchronous clock-group cuts suppressed their timed paths and verified a replacement constraint approach in the installed analyser. This diagnostic does not substitute for the final fitted multi-corner setup/hold/recovery/removal review.

Other concrete fixes include explicit enum widths after an actual synthesis error, reserved-identifier corrections after an HDL compiler failure, robust vector filenames, and automation that checks PASS/fatal text as well as exit status. Tests fail nonzero and retain their source hashes. A testbench changed during one earlier aggregate run; that run remains FAIL, and its affected benches were rerun with frozen source instead of relabelling it.

## Remaining acceptance and continuation

The current relocated source still requires its final full RTL regression and successful complete Quartus fit/timing result, followed by a fresh .sof download, matching on-board build/schema and current B captures. The fixed-sheet acceptance then needs at least 30 distinct new frames, configuration/overflow evidence and reports for targets 1–6. Thirty is an initial project debugging threshold, not a course rubric or generalised accuracy claim.

Physical occlusion/folding, different real illumination conditions and microphone words remain unexecuted or deferred unless later evidence explicitly records them. A person performs physical page changes. No hidden historical frame or held snapshot substitutes for a new observation.

Continue from the repository root:

```powershell
& 'C:/Users/15402/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/echo7.py autodebug
```

Use that command's JSON to identify the next actual failing layer. New source changes require the relevant regression and a new matching build/program/capture cycle before claiming hardware completion.
