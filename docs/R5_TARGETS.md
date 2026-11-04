# ECHO-7 formal R5 target specification

The formal deliverable is [ECHO7_R5_Datasheet.pdf](ECHO7_R5_Datasheet.pdf), exactly one A4 page. [ECHO7_Integrated_Datasheet.pdf](ECHO7_Integrated_Datasheet.pdf) contains the retained product operating guide followed by the same R5 page. The two-page combined document is supplementary; it does not replace the course's standalone one-page sheet.

Source revision: **E7070014**. Specification date: **5 November 2026**. Current three-trial acceptance scores and claimed grade level are **PENDING**. Formal field completeness is not a claim that the robot has met the targets, passed R5 acceptance, or earned a grade.

## Course requirements and target provenance

The primary requirement is [Major_Project_Brief_2026.pdf](Major_Project_Brief_2026.pdf):

| Reference | Requirement used here |
|---|---|
| Page 3, R5 and section 2.3 | Define 3-5 measurable targets, including timing and accuracy/repeatability; give quantity/unit, condition ranges, a three-trial test, threshold and goal. |
| Page 4, section 2.3 | The tutor chooses within the ranges. State how three trials are scored, never select the best. Present predicted and measured values on the one-page datasheet; design a test that can be witnessed in about 90 seconds. The listed numerical examples are not prescribed specifications. |
| Pages 4 and 6, sections 2.4 and 4 | Name the claimed level and the modules supporting it. Actual closed-loop operation, measurements and the applicable bypass evidence determine achievement; a numerical threshold alone does not grant Credit or Distinction. |
| Page 7, section 7 | Include the one-page PDF in the code submission. |

The four targets and their numeric values are project choices:

| Target | Threshold | Goal | Origin and scope |
|---|---|---|---|
| T1, correct blue-marker identities | Minimum of three trial rates >=95%, zero wrong accepted IDs, all six bays represented in each trial | 100% in all three trials | Retains the project values in `tools/render_member_b_datasheet.py`. The formal denominator and worst-trial rule are made explicit here. |
| T2, sampled capture-to-result latency | Largest of three sample maxima <=150 ms, no new drop/overflow | <=100 ms | Retains the old renderer's project values. This is **not** the course's example camera-to-wheel latency quantity. |
| T3, confirmed calibration to profile commit | All three independent attempts complete within 2000 ms, with eight qualified samples each | All three within 1000 ms | Retains the old renderer's project values. A calibration ACK or completed-state snapshot is not a convergence measurement. |
| T4, physical gap error about 350 mm | Three autonomous docks; worst absolute ruler error <=50 mm | Worst error <=20 mm | New explicit project choice. The 350 mm reference follows the controller's desired stop gap; 50/20 mm are project acceptance values, not mandated course values or grade bands. |

No claimed level is invented for the group. The PDF explicitly says **PENDING - no level asserted**. This field must be updated only when the group chooses its claim and the supporting evidence can be stated honestly. Existing failed full-search tasks do not establish repeated complete operation.

## Exact scoring protocol

The authoritative editable fields are [tools/data/echo7_r5_targets.json](../tools/data/echo7_r5_targets.json). Each target includes all eight requested fields, a threshold source, contribution, current-trial list and separately scoped historical context.

- **T1:** At each of three tutor-chosen static poses, keep all six official blue signs fully visible. Before sampling, photograph and label their regions independently of the FPGA outputs. Score the first ten distinct current reports: six expected labels per report, 60 labels per trial. Bad, missing or ambiguous labels count as incorrect; do not wait for a good lock and discard failures. Report all three rates and use the lowest. Any wrong accepted identity fails the additional zero-wrong-ID condition. Merely seeing the set `{1,2,3,4,5,6}` is not a spatial truth score.
- **T2:** Reuse those three sets if their timing records and counters are complete. Compute the unsigned FPGA `completionUs - captureStartUs`; do not use USB/JTAG transfer time. Include failed completed reports. Use each trial's maximum and then the largest of the three maxima. A new drop/overflow or missing requested report fails the trial. Repeated snapshots of the same frame are not independent samples. The result bounds only these sampled completions, not all intervening frames or wheel response.
- **T3:** In VISION_ONLY, independently rearm colour calibration three times with red1 and its paired reference fully visible. Retain each board-time trace from a confirmed attempt through the eight valid samples and new-configuration commit. Report each conservative observed upper bound, then the longest. Missing start/commit evidence is INCOMPLETE; a rejected attempt or timeout is a failure, not an omitted trial. The pre-confirmation recognition interval is outside this quantity.
- **T4:** Use an already-visible and locked blue1-4 target, not an out-of-view search. Keep a fixed declared runtime profile, supply/load and plastic floor; reset to the same start marks for each run. Stop observing a run at 25 seconds if autonomous DOCKED has not occurred. After each completed dock, measure the target-plane gap from the **front of the J3 probe** with a ruler. Score `max(|gap_i - 350 mm|)` across three runs. Any timeout, manual stop or missing DOCKED fails the acceptance condition. A J3 number or camera-to-paper distance does not substitute for this ruler origin.

The tutor may choose within the stated 0.40-0.70 m camera ranges for T1-T3 and 0.60-0.70 m starting gap for T4. Other stated conditions, including complete borders, stable indoor lighting and no glare, are part of the specification. T1/T2 can share captures. The intended live procedure allows about 90 seconds per target including setup/reset; T4's three 25-second caps leave approximately 15 seconds for reset and recording. This is a proposed demo procedure, not an executed timing claim. Demonstrate IR safety before a driving trial.

## Predictions are separate from measurements

- T1's 100% is the intended decoder result on the declared static sheet, not an inferred probability of real-world recognition.
- T2's provisional 100 ms allocation is 40 ms nominal frame acquisition plus a 60 ms processing/commit allowance. It is not a proven worst-case bound and is not derived retrospectively from the 57.066 ms historical maximum.
- T3's ideal 360 ms frame-count estimate uses eight qualified sampling frames plus one commit boundary at nominal 25 fps. It excludes pre-confirmation recognition and rejected frames; it is not a measured convergence interval or unconditional guarantee.
- T4 has no defensible numerical braking/ranging model yet, so its prediction remains PENDING. The logical 350 mm comparison cannot predict physical stopping error by itself.

These predictions were declared for this specification. They must not be described as predictions made before the old E4/E12 experiments.

## Historical evidence retained without upgrading it

The JSON stores these contextual summaries and their original local log paths. They are **not** populated into `currentTrials` and cannot earn a current target score.

| Evidence | Observed fact | Why it is not current R5 acceptance |
|---|---|---|
| E7070004, `sw8_pairs/normal1.json`, `sw8_pairs_resume1/normal2.json`, `normal3.json` | Each file has 12 distinct snapshots with the complete accepted blue-ID set 1-6: 12/12, 12/12, 12/12. | Different build and a set-presence check, without the formal per-label spatial truth denominator. |
| E7070012, `integrated_blue4_e12_flowoff_search_to_dock.jsonl` | 90 B snapshots; `processingLatencyUs` spans 38818-57066 us. | One dynamic task, not three static scoring sets. B/C snapshots freeze independently; this is not scene-to-UART or mechanical latency. |
| E7070012, `e12_blue4_calibration_preflight.json` | `calibrated=true`, `calibrationSampleFrames=8`, configuration 1. | Completed-state evidence, without three independently timed start/commit intervals. |
| Same E12 real-camera task | INCOMPLETE after 60.0067485 seconds, no DOCKED; host observation cleanup stopped the task. | No scored final docking gap. Final J3 407 mm is not a ruler-based T4 result. |

The source logs are under `build/remaining_20261104/` in the development workspace. Build logs are not implicitly bundled by the submission exporter. The published specification retains their concise contextual values and limitations; it does not pretend that raw logs are present in the ZIP.

Earlier successful visible-target stopping, later interrupted approaches and separate post-stop reads must not be concatenated into one successful full search-to-dock run. The observed complete out-of-view task remains unpassed. T4's narrower visible-target protocol does not replace the course's complete-run demonstration.

## Contribution and bypass boundary

T1/T2 concern the self-designed projective/anchor reader, colour/shape processing and report pipeline. T3 concerns real-pixel reference calibration. T4 concerns qualified target use and motion/stop decisions. For the applicable R9 comparison, repeat T1 with SW8=1 at matched poses, lighting, ranges and fixed source. Keep IR/J3 and the rest of the robot active. If bypass still meets threshold, this target does not show that the bypassed stage was necessary. Current static bypass observations do not establish a Credit/Distinction claim or a ground-loop improvement.

## Generate and package

Run `python tools/render_integrated_datasheet.py` with `reportlab` and `pypdf` installed. It checks that the target-specification build ID matches `rtl/common/memberBBuildId.svh`, requires 3-5 targets and all eight fields, and refuses to label missing current trials as measured. It generates:

1. `docs/ECHO7_R5_Datasheet.pdf`: standalone **one-page** formal sheet for the course.
2. `docs/ECHO7_Integrated_Datasheet.pdf`: **two-page** product guide plus that formal sheet.

Render and visually inspect both pages after edits. For the final export, pass `--datasheet docs/ECHO7_R5_Datasheet.pdf`; `export_submission.py` intentionally requires its explicitly selected course datasheet to be one page. The source tree automatically includes both PDFs, this Markdown explanation, the renderer and `tools/data/echo7_r5_targets.json`, so it can be regenerated after extraction. The exporter also places the selected formal sheet at top-level `echo7_datasheet.pdf`.

Use the actual final E14 SOF only after the root's build/programming checks. Document generation and ZIP integrity add no hardware acceptance. Do not insert a future E14 result, a grade or a trial count before its evidence exists.
