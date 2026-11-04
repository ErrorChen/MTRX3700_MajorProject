# ECHO-7 / MTRX3700: vision-guided bay search and docking

[中文](README.md) | [English](README_EN.md)

The production project is `quartus/PartBDebug.qpf`, with top level `echo7IntegratedTop`, targeting the DE1-SoC Cyclone V `5CSEMA5F31C6`. One SOF supports real-camera vision debugging, chassis debugging with synthetic vision, and integrated operation. Only physical SW0–SW5 select the target. JTAG cannot directly set wheel speeds or inject a fake ultrasonic distance.

Build, programming and board-test results are recorded in the [repair acceptance record](docs/REPAIR_RESULT.md). Earlier fit, simulation and camera records retain their historical scope; they do not certify current code on the vehicle. Sources and member attribution are in [OWNERS.md](OWNERS.md). Microphone and speech recognition have been removed. Red1 retains automatic colour calibration. Following the user's additional requirement, a newly presented red2 reselects the physical switch target, reacquires it and requests a start when no task is active.

## Current version and acceptance scope

The current production source identifier is **E7070004**. The CCTL interface identifier remains **E7070001**; these identifiers serve different purposes. See the [version history](VERSION_README.md) and the [repair record](docs/REPAIR_RESULT.md) for commands, elapsed times and hardware evidence.

| Version | Main change in that version | Evidence obtained |
|---|---|---|
| E7070002 | Three modes, physical one-hot selection, red2 events, the complete safety chain and paged vision diagnostics | Full Compilation and R6 passed; board injection, wheel direction, IR and real blue1 tracking passed. A later single-frame overflow exposed a permanent C inhibit caused by historical fault state. |
| E7070003 | Separate recoverable bad frames from historical fault bits; establish a recovery fence at reception time | 236 control checks, R6 and Full Compilation passed. The board recovered healthy tracking with faultFlags=3 retained; 22 locks across 23 distinct real frames. A red2 start occurring before a new lock was then found. |
| E7070004 | Without scan calibration, a pending red2 start waits for the new request's three-frame target lock | **254 targeted checks PASS; formal R6 completed in 219.556074 seconds with all 12 items and CAUGHT passing; Full Compilation and actual programming PASS; the user physically confirmed red2 starting and stopping when blue1 left the view.** The host's two-second STOP was not independently timed at the wheels. Final state: VISION_ONLY, disarmed, logical zero speed, and the user confirmed standstill. |

Real hardware corrections have been demonstrated. This does not mean all six bays have completed floor-level closed-loop trials or that a ground-level 360° scan has been calibrated. Most hardware work described here used a raised chassis. This README distinguishes implementation, version-specific observations and procedures still to perform. A reproduction procedure is not an execution claim.

## Environment and hardware prerequisites

| Item | Environment used / requirement |
|---|---|
| FPGA / project | DE1-SoC, Cyclone V 5CSEMA5F31C6; `quartus/PartBDebug.qpf` |
| Synthesis and programming | Quartus Prime Lite **18.1.0 Build 625**, Quartus STP and the USB-Blaster driver |
| Host scripts | **Python 3.13**; install project dependencies from `requirements.txt` |
| Formal R6 simulation | **Verilator 5.050**, Bash, GNU Make and a compatible C++ compiler; this machine used Git Bash, the MSYS2 MinGW compiler and `--jobs 4` |
| Targeted RTL simulation | ModelSim Altera Starter Edition **10.5b (2016.10)**; a ModelSim pass does not replace formal R6 |
| Vision input | The real OV7670 camera, existing project camera wiring and official marker cards; VGA for live video and diagnostics |
| Motion and protection | UGV02 chassis UART, real IR receiver, J3 RCWL-1601 ranging, 3.3 V interfaces and common ground |

The working directory on this machine is `C:\Quartus_Projects\ECHO72.0\github_publish\MTRX3700_MajorProject`. Adjust commands to the actual clone directory on another machine. Check camera wiring, power, ground, crossed UART connections and valid J3 echoes before use. Verify wheel direction with the chassis raised before floor tests. VISION_ONLY can debug vision without J3 connected; both motion-capable modes require real valid ranging and IR safety conditions. No J4 sensor has been added, and JTAG does not replace real ranging with fabricated values.

`status --watch` and injection each hold a JTAG session. Close one session before opening another; a busy link is not evidence of a board fault. Pin assignments are listed at the end of this document.

## Switches, buttons and displays

| Control | Current function |
|---|---|
| SW0 / SW1 / SW2 / SW3 / SW4 / SW5 | Select blue bay1 / 2 / 3 / 4 / 5 / 6 respectively; exactly one bit must be high |
| SW6 | Candidate boxes and local RGB/HSV, colour, digit and rejection diagnostics; two automatic pages of eight slots cover all 16 candidates |
| SW7 | Centre sampling box and the candidate covering the centre |
| SW8 | Bounding-box / perspective bypass; the same controller and safety chain apply, with observations reconfirmed after the configuration changes |
| SW9 | Raw camera display; immediately revokes motion authorization; leaving raw mode still requires a new START/POWER |
| IR POWER `0x12` | Start a qualified new task when no emergency stop is latched; does not reset an active task's scan budget |
| IR A `0x0F` | Latch emergency stop and immediately revoke motion permission |
| Red1 card with paired blue reference strip | Establish a real colour sampling window and calibrate; the reference strip is not a numbered blue bay |
| Red2 card | After consecutive confirmation, reselect the current valid switch target; without scan calibration, wait for the new target's three-frame lock before starting; VISION_ONLY only reacquires |
| POWER after emergency stop | The first new press only clears the IR latch and leaves the chassis stopped; release and press again to start |
| KEY0 | Global reset: INTEGRATED, DISARMED and zero speed; selection, colour calibration and scan calibration state are reinitialized |
| KEY1 | Cycle HEX distance / upper NEC16 / lower NEC16 pages; retain camera snapshot operation |

The complete six-switch value must remain stable for approximately 20 ms before selection is established. All zero means `NO_SELECTION`; multiple high bits mean `SELECTION_CONFLICT`. Both clear old tracking and prohibit motion. A valid target is tracked even while disarmed. Red2 can establish a new request boundary for the same physical selection. A synchronized switch change during motion stops and cancels the old task; the new selection requires a new start.

HEX4 shows the mode: `0` INTEGRATED, `1` VISION_ONLY or `2` CHASSIS_INJECT. HEX5 shows `n` for no selection, `C` for conflict, otherwise distance page `d` or NEC page `H/L`. HEX3–0 show distance in millimetres or the selected NEC data; invalid distance is blank. Use `status` for full state names, target number and failure reasons.

Read distance from only the rightmost four digits, HEX3–HEX0, on page `d`: these are **decimal millimetres**. For example, `d2 0520` means 520 mm (52.0 cm); the left `d2` means “distance page plus CHASSIS_INJECT mode” and is not part of the distance. KEY1 cycles `d → H → L`. On H/L, the right four digits are hexadecimal NEC remote-control data, not range. Invalid distance blanks all four right-hand digits; a blank display does not mean 0 mm.

The display, controller and JTAG status use the same ultrasonic `distance_mm`, with a new sensor measurement approximately every 100 ms. A separately timed JTAG snapshot may differ from the visible display by an update. Millimetres are the code's defined unit; absolute ruler accuracy has not been established. Adjusting the reflector setup changed an observed reading from 379 mm to 520/521 mm, while the actual reflecting surface and ruler origin were not established. This is not a basis for changing the conversion factor or claiming distance calibration.

LEDR0 is motion permission; 1 is IR emergency stop; 2 is valid distance; 3 is docked; 4 is ultrasonic HOLD; 5 is UART busy; 6/7 indicate complete/repeat NEC frames; 8 is a confirmed target; 9 is disarmed with valid distance. `LEDR0=0`, completion of a zero-speed JSON message and physical standstill are separate facts. NEC repeat frames and repeated complete POWER frames cannot turn one held press into both release and restart. A new key event requires approximately 180 ms of silence.

## Red1 calibration and vision diagnostics

Red1 calibration requires a uniquely recognized real red1 and its geometrically paired blue reference strip. Three consecutive healthy frames from the current configuration confirm the pair. Eight independent qualified frames are sampled, and colour thresholds/configuration are committed atomically at a subsequent SOF. Motion is inhibited during calibration, and red2 cannot preempt it. A successful calibration does not restart simply because red1 remains visible. Initial calibration can retry automatically; an explicit rearm is available through `calibrate --arm` below.

Default segmentation minima are red 48 and blue 20. Calibration derives colour minima from real samples; it does not automatically tune every recognition parameter. The white-stroke minimum of 84, strict white-anchor threshold, geometry gates and digit checks remain fixed algorithm parameters. Current BCTL has no arbitrary red/blue threshold-write command. A calibration ACK only confirms acceptance of the rearm request. Check `calibrated`, `calibrationSampleFrames=8`, configuration version and the terminal event to establish completion.

Keep the complete card inside the frame with a background margin, avoiding glare, substantial blur and fragmented red clutter. Candidate extraction supports up to 15 active labels per colour and 16 shared completed candidates. Capacity overflow rejects the whole frame. SW6 exposes rejected candidates, UNKNOWN and reason codes; SW7 shows local centre RGB/HSV. A local sample is not independent centre OCR. Digits still come from real pixels and each card's anchor/strokes, not from a fixed scene location or candidate index.

## Three operating modes

| Mode | Perception source | Motion |
|---|---|---|
| INTEGRATED, power-up default | Real camera and B vision processing | Allowed after an explicit start and real safety qualification |
| VISION_ONLY | Real camera and B vision processing | Always zero speed; selection, tracking and calibration work without J3 connected |
| CHASSIS_INJECT | Synthetic vision reports generated in the FPGA at 25 Hz | The same real C controller, IR/J3 protection and UART; additionally requires a valid host lease |

A mode change never starts a task. It revokes the previous authorization and creates new request/report boundaries. Real-camera faults and colour calibration are retained. Injection only isolates conditions belonging to that inactive source; switching back immediately reapplies them. IR and J3 remain active in both motion-capable modes.

A red2 already in view at power-up, KEY0 or a mode change cannot start the chassis. First remove it for three consecutive healthy frames, then present it uniquely for three consecutive confirmation frames. This produces one new request. STOP, emergency stop, selection changes, raw camera mode and applicable safety holds revoke the previous presentation; after recovery, remove and present it again. Red2 does not reset selection, task state or scan budget during an active task.

An inactive task waits at most one second after red2 reselects. If scan calibration is absent, the new request must acquire a three-frame target lock before starting. With scan calibration, healthy NOT_FOUND frames can qualify a search. Keep red2 and the selected blue card fully visible together; showing only red2 without the selected bay times out and leaves the vehicle stopped. STOP, IR, switch changes, mode changes, SW9, fatal faults or ultrasonic hazards cancel a pending start. Unsafe distance rejects a red2 start; recovery requires removal and a new presentation and cannot cause a delayed automatic start.

A legal START also needs a healthy current source, valid distance and a released ultrasonic HOLD. The controller does not save an unsafe START for later execution. A JTAG START ACK only means that the transaction was parsed; the CLI subsequently checks actual controller arming.

Red2 is a START request, not a command to run for exactly two seconds and stop. A normal task progresses according to the visual target, safety conditions, scan budget and docking state. With the chassis raised, wheel rotation cannot actually change body heading or distance to the target, so this setup cannot establish floor-level DOCKED operation. Stopping after target removal and a timed host STOP must also be observed separately.

## Executable commands

Run commands from the repository root with Python 3.13. The example selects the executable actually used on this machine, avoiding the system Python 3.8 or an unavailable launcher. Change the path on another machine. Tools locate Quartus automatically; if necessary, put `--quartus-bin C:\intelFPGA_lite\18.1\quartus\bin64` before the subcommand. Supply both `--cable` and `--device` when selecting a target explicitly.

```powershell
Set-Location 'C:\Quartus_Projects\ECHO72.0\github_publish\MTRX3700_MajorProject'
$pythonExe = 'C:\Users\user\AppData\Local\Programs\Python\Python313\python.exe'
& $pythonExe tools/chassis_debug.py mode vision
& $pythonExe tools/chassis_debug.py status --watch

& $pythonExe tools/chassis_debug.py mode chassis
& $pythonExe tools/chassis_debug.py inject --x 80 --visible 1 --hold 3 --arm
& $pythonExe tools/chassis_debug.py scenario left-centre-right-loss --arm
& $pythonExe tools/chassis_debug.py scenario no-target-search --arm
& $pythonExe tools/chassis_debug.py scenario stale-frames --arm
& $pythonExe tools/chassis_debug.py stop

& $pythonExe tools/chassis_debug.py mode integrated
```

`status --watch` runs continuously. Press Ctrl+C to end the observation session before continuing with mode/injection commands. Use `--help` for supported subcommands and options. There is no standalone `chassis_debug.py start` subcommand: real integrated operation normally starts through IR POWER or a new red2 presentation; injection uses `--arm`.

With no other JTAG session open, real vision status, calibration and capture are available through:

```powershell
& $pythonExe tools/echo7.py doctor
& $pythonExe tools/echo7.py status
& $pythonExe tools/echo7.py calibrate --arm
& $pythonExe tools/echo7.py capture --fresh
```

`echo7.py status` reads BCTL colour/candidate/report state. `chassis_debug.py status` reads CCTL selection/safety/task state. Capture retains real RGB565, result words and CRC/version checks; use the output location reported by that invocation. In the integrated production top, C exclusively owns SELECT/CLEAR. Older B debugging `select/track/locate` commands are not substitutes for physical switch selection; speech commands are unsupported.

Use `observe` to save a bounded sequence. Physical SW0–SW5 still select the target. The command only reads CCTL then BCTL within one persistent session; it does not select a bay, change mode, ARM, renew a lease or STOP. Ending observation does not cancel a running INTEGRATED task. Set the mode and physical switches before running:

```powershell
& $pythonExe tools/chassis_debug.py observe --samples 30 --out build/observations/bay1-normal1.json --label bay1-normal-trial1
# Alternatively sample for a duration; choose either --seconds or --samples.
& $pythonExe tools/chassis_debug.py observe --seconds 8 --out build/observations/bay1-window.json --label bay1-window
```

`--samples` counts poll pairs, not necessarily new frames. `--interval` pauses after each pair and defaults to 0.1 seconds. JSON retains bad, unlocked and repeated samples, counts distinct C/B frames separately, and includes physical selection, mode, versions, thresholds, request tags and each read's start/end time. CCTL and BCTL freeze independently: **a pair is not a same-frame snapshot**. `COMPLETE` means collection completed, not recognition or motion acceptance. Ctrl+C or a transport error preserves records already read, including a partial CCTL sample if BCTL fails. Output must be a new file; existing evidence is never overwritten.

Static SW8 vision comparisons can start in VISION_ONLY. Keep the same blue card, physical selection, camera position/focus, card placement and illumination, with SW9 off. Collect three normal runs with SW8=0 and three bypass runs with SW8=1, using the same `--samples` count each time. Give each run a new filename and label, such as `normal1.json` through `normal3.json` and `bypass1.json` through `bypass3.json`. After changing SW8, let the current request/configuration stabilize; do not change selection, calibrate or switch mode during a run. Then compare offline:

```powershell
& $pythonExe tools/compare_observations.py --normal build/observations/normal1.json build/observations/normal2.json build/observations/normal3.json --bypass build/observations/bypass1.json build/observations/bypass2.json build/observations/bypass3.json --out build/observations/comparison.json
```

Without `--conditions-confirmed`, the result is `UNCONFIRMED_CONDITIONS`, exit 2. Only after the operator actually checks unchanged camera/card/lighting conditions for these six runs, add `--conditions-confirmed 'describe the actual confirmation'`. The comparator checks build, algorithm/colour profile, physical target, operating mode and poll count across all six runs, plus stable request/configuration and the expected SW8 value within each run. Raw SW9 display, reused runs and invalid time order are rejected. `COMPARISON_VALID` only means the inputs match; bad frames, lost locks and stale data remain visible for each mode. Both all-poll and distinct-frame summaries are reported. FPGA capture-to-completion time is not image-change-to-UART or mechanical response latency. Three static pairs for one selected bay do not establish six-bay floor-level acceptance.

The old `echo7.py test --hardware [--trials N]` and `autodebug` depend on automatic BCTL SELECT/CLEAR, which conflicts with the production top's sole request owner. They now return `BLOCKED`, exit 2, and point to `observe`. `autodebug` stops before building, programming or accessing the board. Historical B trial parsing/scoring remains available for old evidence; the old commands cannot certify that all six bays were automatically tested on the current top.

U is the rotated image coordinate `0..239`; V is `0..319`. U80/U120/U160 mean left/centre/right. `--hold` is in seconds and defaults to 3. Without `--arm`, a session updates templates but does not start a task. Mode changes, heartbeats and read-only status commands do not start tasks either.

Continuous injection updates the template, renews the lease and starts within one persistent Quartus STP session. Normal exit or Ctrl+C attempts STOP. An abnormal host exit causes the FPGA lease to expire after approximately 500 ms, directly revoking injection permission. Renewing the lease does not restart motion. Stopping frames while retaining heartbeats is still caught by the approximately 150 ms report freshness guard. INTEGRATED does not depend on JTAG heartbeats.

`scenario no-target-search --arm` reads the FPGA's current `scanBudgetUs` and holds the synthetic no-target template for the budget in seconds plus 3 seconds. This covers the final zero-speed message, 200 ms settling, 900 ms confirmation and polling margin; the default 10-second budget gives a 13-second session. The same session continuously prints CCTL state and renews the lease between pages, exposing SEARCH, final ACQUIRE, NOT_FOUND or real HOLD. HOLD does not add search rotation time, so elapsed session duration alone cannot prove budget completion; inspect the retained states. Exit still attempts STOP. This command does not set scan calibration or equate raised-wheel rotation with a ground revolution.

**Stop active injection using Ctrl+C in its owning process.** Use a separate `stop` command only when the JTAG link is idle. The tool rejects contention with another chassis session; inability to open the link does not mean STOP was delivered. Do not run another BCTL/GRAB process alongside an active injection session.

Play a sequence with `play <JSON-file> --arm`. The file is a nonempty JSON array of objects, for example:

```json
[
  {"x": 80, "visible": true, "hold": 3},
  {"x": 120, "visible": true, "hold": 3},
  {"x": 160, "visible": true, "hold": 3},
  {"visible": false, "hold": 4}
]
```

Each row can also specify `y`, `quality` or `frames_enabled`. Users do not maintain internal tags, frame IDs or capture timestamps. Templates are staged and committed atomically; incomplete transactions cannot become partially updated observations. CCTL uses stable 64-bit transactions, toggle/ACK and error codes. STATUS freezes a 16-word snapshot containing mode, switches, task state, request/frame/configuration, age, search budget, logical speeds, real J3, IR and UART zero-completion state.

Observe `mode`, `inputSource`, `selection`, `digit`, `requestTag`, `frameId`, `sourceHealthyFresh`, `targetObserved`, `targetLockedFresh`, `taskArmed`, `motionPermit`, `distanceValid`, `sonarHold`, `irEstop`, `failure` and `zeroSent` together. Command acknowledgement, a new frame, target lock, task authorization and physical movement are distinct facts. One field alone cannot establish that the complete chain passed.

## Search, alignment, docking and recovery

The main path is `IDLE → SEARCH → ACQUIRE → ALIGN → APPROACH → DOCKED`, with `LOST`, `HOLD` and `NOT_FOUND` states. Disarmed operation only tracks. SEARCH rotates with logical left/right speeds of `-4/+4 cm/s` only while frames are fresh and healthy, real safety conditions pass, and budget remains. Healthy NOT_FOUND reports can sustain search; a target lock is not required for search activity.

One unambiguous target observation with correct identity, time and configuration stops search. ACQUIRE first waits for a complete zero-speed UART message, then waits a conservative default 200 ms, and finally establishes a new capture fence. Alignment/approach require three independent new frames after that fence plus a locked result. The confirmation window defaults to 900 ms. These waiting parameters are not measured mechanical settling times.

ALIGN uses opposite wheel speeds of 4 cm/s; U110–130 is centred. APPROACH uses 5 cm/s beyond 500 mm and 3 cm/s between 350 and 500 mm. A reliable aligned target reaching 350 mm produces DOCKED. Target loss immediately stops translation, first attempts stationary reacquisition, then searches within the remaining budget. DOCKED and NOT_FOUND revoke task authorization: a new image or recovered distance cannot restart them. A new task can be explicitly started without a global reset.

Scanning currently uses **accumulated authorized search-turn command time**, not verified heading feedback. Only permitted SEARCH rotation consumes this budget; ACQUIRE/HOLD waits do not. A separate 120-second task wall-clock limit applies. The direction-query receive path is retained, but real feedback has not been validated for angle-based closed-loop scanning.

The default 10-second value is an uncalibrated bounded chassis-debug budget, reported as `SCAN_UNCALIBRATED`. INTEGRATED prohibits formal no-target scanning without calibration, while a reliably visible target can still be aligned with and approached. For an approximately 360° calibrated scan, first make three actual floor trials at the same fixed wheel speed in a clear area, measure a full revolution using direction marks, and record repeatability before setting the measured duration:

```powershell
# This is an example, not a measured calibration value. Replace 30 with the measured result.
& $pythonExe tools/chassis_debug.py scan --seconds 30 --calibrated
```

Changing `scan` stops the task. `--calibrated` is the operator's confirmation of real measurement. Calibration lasts for the current FPGA session and is lost at KEY0 or reconfiguration. Simulation duration, raised-wheel rotation or an arbitrary number of seconds cannot establish a ground-level 360° result. After scanning ends, a final stationary confirmation is performed; an absent target produces NOT_FOUND.

Invalid, missing, stale or ≤250 mm real J3 distance immediately prohibits motion and enters HOLD. Recovery requires three **new** valid measurements, each ≥300 mm. Re-reading one sample does not count; recovery does not clear IR/fatal latches or replenish search budget. Normal 350 mm docking and 250 mm protective stopping are reported separately. Ranging occurs approximately every 100 ms, accepts 20–3999 mm, and has a 30 ms measurement timeout plus a 1-second stale guard.

Camera abandon, a bad frame for the current request or candidate overflow revokes qualification and establishes a new boundary. Three adjacent fresh healthy frames from the current configuration restore search qualification; these may be NOT_FOUND. Alignment/approach still require renewed three-frame target confirmation. Historical candidate-overflow diagnostics remain visible, but recovering the image no longer requires global reset from E7070003 onward. FIFO fatal and double-bank exhaustion remain inhibiting faults across mode changes or good frames. If the current image keeps overflowing, put the full marker in view and simplify the background; reset cannot repair an invalid image.

UART is 115200, 8N1, with complete `T:1` JSON and a normal 200 ms command heartbeat. A stop takes priority after the complete JSON currently in transmission. Both default wheel polarity constants are −1, so logical forward 5 cm/s sends `{"T":1,"L":-0.05,"R":-0.05}`. Verify actual rotation and forward direction with the chassis raised, then measure stopping error on the floor.

## Three-stage reproduction procedure

1. **VISION_ONLY:** select each of the six bays through SW0–SW5, and use SW6/7 to inspect local samples and rejection reasons. Check advancing frame IDs, observed/locked state, loss under occlusion and reacquisition. Reconfirm after a red1 calibration commit; default thresholds also permit image setup and tracking before calibration. SW6 changes page every 120 VGA frames, approximately 2 seconds at 60 Hz: #0–7 followed by #8–F. The page travels with the captured sample records. These labels are candidate indices; the recognized digit or UNKNOWN is shown separately. Centre RGB/HSV is local sampling, not independent OCR, and SW7 remains available on both pages. J3 need not be valid in this stage; commanded wheel speed remains zero.
2. **CHASSIS_INJECT:** obtain valid real J3 distance and raise the chassis to verify wheel direction and forward polarity for U80/U120/U160. Use a real reflector to test 500/350/250 mm behaviour. Check no-target search, brief target appearance, loss, Ctrl+C/lease expiry, IR A and two distinct POWER presses. Ground revolution calibration requires room for the entire vehicle to rotate, clear surroundings and real valid echoes; one forward J3 sensor does not establish clearance around the body. Record this stage as synthetic visual input.
3. **INTEGRATED:** stop the injection process, switch to integrated, select through physical switches, then use IR POWER or a new red2 presentation. Record real search→discovery→settling confirmation→alignment→approach→docking, with separate coverage of all six bays, loss, obstacles, missing echoes and emergency stop. The computer may be disconnected; normal tasks do not require host renewal. Compare SW8 normal/bypass in three trials each of the same scene, measuring task time, stopping error and image-change-to-UART latency.

At the current speeds, travelling from 1 m to 350 mm alone takes approximately 15 seconds ideally; scanning and confirmation add time. Final performance is based on measured results, not the old proposal's 12/18-second targets.

## Build and verification

Check the Python path and Quartus tools first. If Python dependencies are missing, run `& $pythonExe -m pip install -r requirements.txt`. Dependency installation is outside R6 timing.

```powershell
& $pythonExe tools/echo7.py build
& $pythonExe tools/echo7.py program
& $pythonExe tools/echo7.py test --rtl --only tb_control_repair tb_chassis_debug tb_pixel_uart_repair
```

Alternatively, open the QPF in Quartus and run Full Compilation; `quartus/output_files/PartBDebug.sof` is the direct-project default. `echo7.py build` uses an isolated directory for each build. The `program` command above uses the SOF recorded by the latest successful local build; `--sof` can explicitly supply that record's absolute path. Programming checks the build source and artifact; an older SOF cannot stand in for a new feature.

Published files use fixed paths: [E7070004 FPGA program](firmware/E7070004/PartBDebug.sof) and [integrated datasheet PDF](docs/ECHO7_Integrated_Datasheet.pdf). The 004 SOF is **6706154 bytes**, generated from the successfully compiled 004 source, not a renamed 003 artifact. To use the published SOF directly, select the actual USB-Blaster and FPGA at chain position 2 in Quartus Programmer, add the SOF and execute Program/Configure. BCTL should subsequently read `buildId=0xE7070004`. Position 2 was observed on this DE1-SoC; inspect the chain when changing boards.

A precompiled SOF does not carry a local `echo7.py` successful-build record, so use Quartus Programmer for that path. `echo7.py program` continues to require the artifact matching its local successful-build record; provenance protection is not relaxed. SOF configuration is volatile and must be restored after power loss. Permanent boot-image deployment is not claimed here.

The published datasheet can be regenerated from `docs/integrated_datasheet_metrics.json`. These are separate document-tool dependencies; the main vision environment's `requirements.txt` does not need to change:

```powershell
& $pythonExe -m pip install reportlab pypdf
& $pythonExe tools/render_integrated_datasheet.py
```

With a current successful local build record, export the integrated hand-off ZIP:

```powershell
& $pythonExe tools/export_submission.py --out build/echo7_submission.zip --datasheet docs/ECHO7_Integrated_Datasheet.pdf
```

Export verifies the current source/build, rejects a stale SOF and refuses to overwrite an existing ZIP. The archive contains exactly one SOF at `firmware/<BUILD_ID>/PartBDebug.sof`, currently `firmware/E7070004/PartBDebug.sof`, matching the README link; there is no second `verified/PartBDebug.sof` copy. It retains both READMEs, project/RTL/test/tool sources, real replay inputs and documentation, while excluding build databases, private toolchains and unrelated run caches. The one-page PDF needs no SHA sidecar, and the ZIP receives a CRC check. Dialogue enters the archive only through an explicitly selected, checked export manifest. A fresh clone without a local successful-build record must build before using the exporter. Archive integrity adds no hardware acceptance claim and performs no Git commit or upload.

| Version with an actual artifact | Isolated build artifact path | Build status |
|---|---|---|
| E7070002 | `build/member_b/20261104T100141_653795Z_build/source/quartus/output_files/PartBDebug.sof` | PASS and programmed, with version-specific board evidence; historical artifact, not the release file |
| E7070003 | `build/member_b/20261104T104155_505074Z_build/source/quartus/output_files/PartBDebug.sof` | PASS and programmed; live bad-frame recovery verified; historical artifact |
| E7070004 | `build/member_b/20261104T111202_124373Z_build/source/quartus/output_files/PartBDebug.sof`; release copy `firmware/E7070004/PartBDebug.sof` | Full Compilation **PASS**; programmed and BCTL version verified at 2026-11-04 22:31:50 AEDT, **PASS**; red2 reselect/new-lock/start observed, and the user confirmed physical stopping when blue1 left the view |

The formal course R6 entry remains `./run_all_tests.sh`: clean copy, Verilator **5.050**, module/system self-checks, and CAUGHT for an intentionally broken module. The user's target is ≤285 seconds; the course threshold is 300 seconds. This Windows wrapper invokes the same Bash entry with four compilation jobs. Within one invocation, completely identical compilation inputs share a newly compiled binary through an internal hash cache; all scenarios still run independent assertions, without binaries from an earlier invocation:

```powershell
& $pythonExe tools/run_r6_windows.py --compiler-bin 'C:\msys64\mingw64\bin' --bash 'C:\Program Files\Git\bin\bash.exe' --jobs 4
```

A ModelSim pass is not an R6 pass. Actual version-specific executions in the required environment are listed in the repair record. Run broader historical vision/Python regressions when changes justify them, rather than repeating every old test to increase counts.

The E7070004 formal R6 completed in a clean copy with Verilator 5.050: **219.556074 seconds, exit 0, all 12 items plus CAUGHT PASS, targetMet=true**. Its result is `build/member_b/20261104T110801_416299Z_verilator_course/result.json`. E7070002 took 245.451876 seconds and E7070003 took 221.258456 seconds. Acceleration comes from sharing identical new compilation within the invocation, parallel independent continuous/overload scenarios and four compilation jobs. The 25 fps source rate, assertions and real observation path remain intact; earlier-run binaries and forced observations are not used. The deliberate mutant must still be caught by actual assertions.

`tb_control_repair` covers one-hot selection, modes, search, settling, safety, negative cases and decoded UART JSON. `tb_board_repair_pins` uses actual NEC pulse timing, a J3 TRIG/ECHO model and 115200 UART without forcing controller inputs. The pixel system chain supplies real perceptionCore pixels; synthetic debug reports and recorded-camera replay are identified separately. Older integration benches used obsolete three-bit selection and fixed ultrasonic behaviour; historical passes cannot be transferred to current code.

## Version-specific hardware evidence

The paths below index original logs in this working directory. Full build databases and simulation caches under `build/` are not committed. The portable account is the [repair record](docs/REPAIR_RESULT.md); the release retains only the current SOF and datasheet. A local log absent from a fresh clone is not a new execution result.

| Version and input layer | Observed result | Evidence and scope |
|---|---|---|
| E7070002, synthetic vision→real chassis | U80/U120/U160 produced turning/forward/opposite turning; heartbeat loss revoked authorization and renewal did not restart; the user confirmed wheel movement and stopping | `build/repair/hardware_injection.jsonl`; `hardware_straight.jsonl` includes confirmation that both wheels moved forward; raised chassis |
| E7070002, real IR/J3/UART | A latched stop; first POWER only released it; second new POWER started; real J3 echoes were valid | `build/repair/hardware_ir.jsonl`; not proof of every physical distance boundary or floor stopping error |
| E7070002, physical scene correction | Cropped red1/blue1 caused overflow; moving the same A4 sheet farther away produced 23 locks across 24 distinct frames, blue1 quality 255, and eight-frame calibration 41/24 | `build/repair/live_capture/`, `hardware_vision_e7070002.jsonl`; VISION_ONLY remained at zero speed |
| E7070003, real bad-frame recovery | Historical faultFlags=3 remained; frame 338 regained `sourceHealthyFresh=true` and `targetLockedFresh=true` without reset or clearing the fault history | `build/repair/hardware_recovery.jsonl`; verifies correction of the E2 permanent inhibit |
| E7070003, continuous real vision | 22 locks across 23 distinct frames; frame 855 blue1 quality 255, U115/V186, 122×130 box, 59.478 ms processing | `build/repair/hardware_vision.jsonl`; zero-speed VISION_ONLY, not six-bay floor completion |
| E7070003, real red2 | Request tag 5→6 proved reselect; start preceded the new lock and entered SCAN_UNCALIBRATED/NOT_FOUND, with no automatic revival | `build/repair/hardware_red2_e7070003_early_start.jsonl`; recorded failure, not successful red2 acceptance |
| E7070004, real red2 and real camera | Tag 3→4; frame 2900 acquired the new lock before ARM/ALIGN, logical L+4/R−4 cm/s, real J3=468 mm; scan uncalibrated, failure=NONE and historical faultFlags=3 retained; the user confirmed red2 starting and clarified that it stopped when blue1 left the view | `build/repair/hardware_red2.jsonl`, `red2_console.log`; the host STOP record's DISARMED, L0/R0 and zeroSent=true establish board state/message completion, while its independent physical stopping time was not measured. Final state: VISION_ONLY, disarmed, logical zero speed, with standstill confirmed by the user. |
| E7070004, all six physical blue cards | Same-frame GRAB frame 26844 accepted blue1–6 at quality 255; across another 12 distinct B frames, each blue digit was accepted 12/12, while selected blue1 was C-healthy/locked 12/12; all samples commanded zero speed | `build/continuation_20261104/six_cards_initial/`, `blue1.json`, `vision_findings.json`; red57/blue37, configuration 1, normal perspective; green tape covered red2 and its residual was rejected rather than assigned a false digit |
| E7070004, six physical switch selections and invalid masks | 150.054 seconds, 441 read-only pairs; each one-hot selection produced its matching real blue-card lock; 17 no-selection and 27 conflict samples; all 441 were VISION_ONLY, disarmed, without motion permission and at logical zero speed | `build/continuation_20261104/six_switches.json` and `six_switches_analysis.json`; C healthy 390/441, locked 370/441, B good 434/441; all seven candidate-overflow bad frames and lost locks retained |
| E7070004, physical SW6/7 display | The user confirmed visible colour information with SW6; with SW7 centred on a white gap, local colour and “no marker” were visible | See the [repair record](docs/REPAIR_RESULT.md); SW6's two pages/all 16 slots/UNKNOWN/rejection reasons and SW7 over a marker or ambiguous scene remain unconfirmed |
| E7070004, synthetic vision plus real J3 docking | 434 status snapshots over 78.931565 seconds; logical +5/+5 at actual 517 mm, +3/+3 at 446 mm, then first DOCKED/disarmed/zero at 347 mm; after moving the reflector away to 534–615 mm, 12 snapshots over 2.194 seconds remained DOCKED/zero | `build/continuation_20261104/dock_hardware_01.jsonl` and `dock_analysis.json`; the user confirmed movement→slowing→stopping→no restart after moving the reflector away; raised chassis, no floor stopping-error claim |
| E7070004, real J3 protective stop/hysteresis/recovery and independent STOP | HOLD03 retained 469 status snapshots over 86.677721 seconds; all six criteria passed with no unverified items; the user confirmed near-stop, remaining stopped in hysteresis, recovery farther away and subsequent STOP | `build/continuation_20261104/hold_hardware_03.jsonl` and `hold_analysis_03.json`; synthetic vision, real IR/J3/UART, raised wheels; direction was not observed in this run and mechanical stopping latency was not measured |

For approximately two seconds after triggering, status was read without sending heartbeats: all 13 samples remained armed with `leaseValid=0`, comprising 7 ALIGN, 4 LOST and 2 ACQUIRE. Including the trigger sample, there were 8 motion-command samples. **This is not two seconds of uninterrupted stable turning**: brief vision loss made the FPGA enter zero-speed reconfirmation. That run's final BCTL snapshot was frame 2959, E7070004, a good frame, blue1 quality 255, U182/V130, a 101×117 box, 47.652 ms processing, and red2 event 7/id 2. The record establishes red2→new-request lock→start and heartbeat-independent INTEGRATED operation. The user physically confirmed starting and clarified that the chassis stopped when blue1 left the view. The host's two-second STOP independently establishes board revocation/zeroSent only; its physical stopping time was not separately measured. The user's observed stop cannot be attributed to host STOP or the later mode1 switch. Final VISION_ONLY readback is disarmed with logical zero speed, and the user confirmed standstill. Six-bay floor docking and mechanical stopping latency are not established by this run.

The later six-switch observation retained 441 distinct B frames and 405 distinct cached C frames. C/B freeze separately; paired frame IDs need not match. C lock counts in the main blue1–6 intervals were 197/200, 22/23, 24/28, 16/22, 23/29 and 26/30; one additional brief blue2 transition was unlocked, and return to blue1 after conflict was 62/64. Of 27 conflicts, 26 formed a sustained stable mask3 interval and one was a mask6 transition. Every no-selection/conflict sample had no C health/lock and no selected B target. The first return-to-blue1 sample retained an old CLEAR report, which C did not accept as a new lock. All seven bad B frames were candidate overflows, each followed by an observed good B frame. For some bad samples, selection changed before relocking was observed. This establishes six-position visual selection coverage, not 441 continuously locked samples or floor-level six-bay completion. See the full interval table and bad-frame indices in the [repair record](docs/REPAIR_RESULT.md). SW6/7 have only the partial display confirmations listed above; matched SW8 comparisons remain outstanding.

The J3 follow-up used synthetic vision, real ranging/IR/UART and raised wheels. The docking record's 517→446→347 mm readings identify first observed state changes, not ruler-calibrated boundaries; criterion confirmation points at 521/454/321 mm came from different, later snapshots. After first DOCKED, all 83 snapshots over 14.853 seconds remained disarmed/zero, including the 2.194-second confirmation after moving the reflector farther away. The user confirmed the physical sequence. Cleanup returned to VISION_ONLY, IDLE, disarmed and zero speed. No floor stopping-distance error was measured.

HOLD03's qualifying hazard window covered 231–242 mm, five snapshots over 0.647892 seconds. Its hysteresis window covered 254–292 mm, seven snapshots over 1.163541 seconds, all HOLD/zero. Moving farther away to 367–407 mm yielded 19 snapshots over 3.119478 seconds of ALIGN with logical −4/+4. At 80.491761 seconds, the host explicitly sent TX4 STOP while continuing the same template and heartbeats. From STOP ACK to the final sample was 6.093588 seconds: all 34 distinct-frame status snapshots were disarmed/zero with zeroSent=true. Their first-to-last sample span was 5.919557 seconds, with the native frameId advancing by 147. Real J3 stayed at 367–376 mm; lease, source and target lock remained valid; sonarHold/IR/fatal stayed false; mode, selection, tag and configuration did not change until the later VISION_ONLY cleanup. The user confirmed near-stop, hysteresis hold, recovery and the subsequent automatic stop, but did not observe wheel direction. These are 34 status polls, not 34 independent sonar measurements. Statements about maintained state describe every recorded sample; this does not measure mechanical stopping latency or establish the separately unobserved STOP timing in the earlier red2 run.

Both previous HOLD records remain. HOLD01 retained 362 snapshots over 66.181 seconds and passed board checks, but the user did not confirm the complete physical sequence and requested a repeat. HOLD02 retained 434 snapshots over 79.899 seconds and its original FAIL: the measured distance left the hysteresis interval before the host's requested one-second observation completed. The final state had reached 313 mm, ACQUIRE and still armed, but the host treated the incomplete stage as failure and immediately sent STOP, preventing observation of resumed motion. The user therefore did not see recovery; this does not establish a production RTL recovery defect. The one-off acceptance script now records NOT_VERIFIED and continues after early safe recovery, producing PARTIAL overall. HOLD03 completed every stage without skipping. Production recovery still requires three new valid readings ≥300 mm; one second is only this test's hysteresis observation requirement. The host correction did not change RTL/SOF, and HOLD03 cleanup completed normally.

Resources/timing remain version-specific: E2 used 29417/32070 ALMs, with worst setup 1.164 ns and hold 0.078 ns; E3 used 29373/32070 ALMs, with worst setup 0.967 ns and hold 0.117 ns. Both used 357/397 M10Ks and 51/87 DSPs, with no unconstrained items and passing four-corner/CDC checks.

**E4 Full Compilation PASS:** 1121.141 seconds, post-fit gate 25.868 seconds, 0 errors and 92 warnings; 29576/32070 ALMs (92%), 41000 registers, 357/397 M10Ks, 51/87 DSPs, 2802640 memory bits and 2 PLLs. Worst four-corner setup is **+1.633 ns**, hold **+0.118 ns**, with no unconstrained items. All 88 checks and coverage of 63 synchronization chains per corner passed; MTBF is NOT_ASSESSED. Programming is recorded in `build/repair/program_e7070004_console.log`, with E7070004 verified through BCTL. Red2 hardware testing is recorded separately: compilation/programming success does not establish motion acceptance.

## Known limitations and outstanding measurements

- Six-bay floor-level closed-loop operation, three ground revolution calibration trials, actual 350 mm stopping error, complete task time and image-change-to-UART latency remain unmeasured. Accumulated command time is not verified heading feedback, and raised-wheel rotation is not a ground-level 360° test.
- Physical J3 protective stop, hysteresis, recovery and docking states now have the raised-wheel evidence above. A physical no-echo test, ruler-checked 250/300/350 mm boundaries and absolute ranging accuracy remain outstanding; reported readings are not calibrated geometric distances.
- SW6's two pages, all 16 slots, UNKNOWN and rejection reasons, and SW7 over a marker or ambiguous centre still need physical confirmation. Current confirmations cover SW6 colour information and SW7 colour/“no marker” over a white gap only.
- Three comparable SW8 normal/bypass trials, sustained movement, occlusion and varied lighting still need wider measurement. This repair used bounded validation instead of repeated long simulation in place of hardware work.
- Fragmented red backgrounds can still exceed active-label capacity. Current bad frames revoke permission; recovery is possible from E3 onward, but persistently invalid images do not become valid automatically. Cropping, glare, blur and duplicate targets can be rejected.
- The historical frame251 model accepts all eight official markers. Frame30321 still rejects fragmented blue6 under its original red41/blue33 profile. One offline comparison kept the original pixels and only lowered blue to 20, restoring all eight accepts; the current real six-card scene also accepted all six at red57/blue37. Stability across lighting/threshold conditions still needs verification; historical inputs and digit6 answers were not fabricated.
- The user confirmed physical E4 red2 starting and stopping when blue1 left the view. LOST/ACQUIRE intermittency remains, so sustained target visibility needs improvement. That run's independent physical timing of the host's two-second STOP remains unmeasured. Later HOLD03 independently verified explicit STOP and no restart with continuing input/lease, with physical stopping confirmed; mechanical stopping latency and wheel direction in that run were not measured. Final state is VISION_ONLY, disarmed and logical zero speed, with standstill confirmed; this does not establish floor docking acceptance.
- A/C member SIDs must still be supplied by the members. Course/IP notices and AI-assisted-change attribution remain; human sign-off is not invented.

## Pins, files and ownership

| Interface | FPGA signal | Pin |
|---|---|---|
| IR receiver | IRDA_RXD | PIN_AA30 |
| J3 TRIG / ECHO | GPIO_1[27] / GPIO_1[29] | PIN_AJ22 / PIN_AG22 |
| UGV02 UART TX / RX | GPIO_1[31] / GPIO_1[33] | PIN_AF23 / PIN_AD21 |

J3 uses the RCWL-1601, 3.3 V and common ground. Connect FPGA TX to chassis RX and FPGA RX to chassis TX. No J4 sensor has been added. Camera/VGA pins are defined by the QSF. The 24-bit B/C request, 141-bit report, 76-bit status and shared microsecond clock all reside in CLOCK_50. Real IR/J3 remain outside the synthetic vision source.

| Path | Purpose |
|---|---|
| `rtl/top/echo7IntegratedTop.sv` | Production three-mode top, source switching and board wiring |
| `rtl/capture/`, `rtl/vision/`, `rtl/tracking/` | Camera transport, colour/candidates/projective recognition and target reports |
| `rtl/interaction/` | Red1 calibration, fresh red2 presentation and event handshakes |
| `rtl/member_c/` | Selection adapter, task FSM, IR/J3 protection and UART chassis commands |
| `rtl/debug/` | BCTL/CCTL, synthetic vision and VGA sample diagnostics |
| `tests/`, `run_all_tests.sh` | Module/system self-checks, real-input fixtures and the formal R6 entry |
| `tools/chassis_debug.py`, `tools/echo7.py` | Persistent JTAG, injection, build, programming, calibration and real capture |
| `tools/compare_observations.py`, `tools/export_submission.py` | Offline paired SW8 summaries from physical-selection observations and integrated single-SOF ZIP export |
| `firmware/E7070004/PartBDebug.sof` | Current release SOF, published only after the final build succeeds |
| `docs/ECHO7_Integrated_Datasheet.pdf` | Current integrated datasheet |
| `docs/REPAIR_RESULT.md`, `VERSION_README.md`, `OWNERS.md` | Version-specific results, iteration history and source/member attribution |

Retain project sources, RTL/testbenches, runners, real camera inputs/models/replay, the final SOF and measurements needed for reporting. Build databases and simulation caches are not source. No new per-file SHA inventory or duplicate evidence package is introduced. Original course/IP notices remain, A/C SIDs remain pending, and member attribution or human sign-off is not fabricated.
