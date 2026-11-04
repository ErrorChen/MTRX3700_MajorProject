#!/usr/bin/env python3
"""CCTL chassis debugging through one persistent Quartus STP session.

Physical SW0-SW5 always select the bay. This tool never overrides wheel outputs
or sonar values. `tune` changes bounded controller parameters only while stopped
in VISION_ONLY; settings reset on KEY0/power loss/reprogramming. Changing search
speed invalidates the floor scan calibration. `stop` is standalone only when the JTAG link is idle; use Ctrl+C
in an active injection session. A lost process is stopped by the FPGA lease.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time

import echo7

MODES = {"integrated": 0, "vision": 1, "chassis": 2}
TUNING_DEFAULTS = {"search": 4, "turn": 4, "approach": 5, "fine": 3, "tolerance": 30}
TUNING_FIELDS = {"search": (0, 15, 3, 5), "turn": (4, 15, 3, 5),
                 "approach": (8, 15, 4, 8), "fine": (12, 15, 3, 4),
                 "tolerance": (16, 63, 10, 40)}


def tuning_word(**values):
    """Encode one atomic controller configuration; speeds are cm/s, tolerance pixels."""
    if set(values) != set(TUNING_FIELDS):
        raise ValueError("tuning needs search, turn, approach, fine and tolerance")
    word = 0
    for name, (shift, _, low, high) in TUNING_FIELDS.items():
        value = values[name]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{name} must be an integer in {low}..{high}")
        word |= value << shift
    if values["approach"] <= values["fine"]:
        raise ValueError("approach speed must exceed fine speed")
    return word


def tune(session, *, defaults=False, **changes):
    """Read parameters or commit one bounded word, with no mode/ARM/lease commands."""
    if set(changes) - set(TUNING_FIELDS):
        raise ValueError("unknown tuning parameter")
    changes = {name: value for name, value in changes.items() if value is not None}
    if defaults and changes:
        raise ValueError("--defaults cannot be combined with parameter changes")
    before = session.status(maintain_lease=False)
    if not defaults and not changes:
        return before
    if not before.get("tuningSupported"):
        raise RuntimeError("this firmware does not support runtime tuning; no write sent")
    if (before["mode"] != "VISION_ONLY" or before["taskArmed"] or before["motionPermit"] or
            before["leftCmS"] != 0 or before["rightCmS"] != 0 or not before["zeroSent"]):
        raise RuntimeError("tuning requires VISION_ONLY, disarmed, zero wheel commands and zeroSent; no write sent")
    desired = dict(TUNING_DEFAULTS if defaults else before["tuning"])
    desired.update(changes)
    payload = tuning_word(**desired)
    session.tx(11, payload)
    after = session.status(maintain_lease=False)
    if not after.get("tuningSupported") or after["tuning"] != desired:
        raise RuntimeError("tuning readback mismatch; write delivery or retention is unconfirmed")
    if (after["mode"] != "VISION_ONLY" or after["taskArmed"] or after["motionPermit"] or
            after["leftCmS"] != 0 or after["rightCmS"] != 0 or not after["zeroSent"]):
        raise RuntimeError("stationary boundary changed after tuning; no start was sent")
    if desired["search"] != before["tuning"]["search"] and after["scanCalibrated"]:
        raise RuntimeError("search speed changed but scan calibration was not invalidated")
    return after


def observation_words(x=120, y=160, visible=True, quality=255, width=40, height=50,
                      ambiguous=False, frame_good=True, frames_enabled=True):
    if not (0 <= x < 240 and 0 <= y < 320 and 0 <= quality <= 255 and
            0 < width <= 240 and 0 < height <= 320):
        raise ValueError("observation must use upright U=0..239, V=0..319 and positive bounded size")
    return (x | (y << 8) | (bool(visible) << 17) | (bool(ambiguous) << 18) |
            (bool(frame_good) << 19) | (bool(frames_enabled) << 20) | (quality << 24),
            width | (height << 8))


def decode_status(words):
    if len(words) != 16 or any(not 0 <= word <= 0xffffffff for word in words):
        raise ValueError("CCTL status must contain exactly sixteen unsigned words")
    mode = words[15] & 3
    signed7 = lambda value: (value & 127) - (128 if value & 64 else 0)
    state = (words[0] >> 21) & 15
    selection = "VALID" if words[0] & (1 << 14) else "SELECTION_CONFLICT" if words[0] & (1 << 15) else "NO_SELECTION"
    distance = words[8] & 4095
    distance_valid = bool(words[8] & (1 << 12))
    # E7070005 reserves valid+4000 for a completed out-of-range echo pulse.
    # Older invalid+4000 records remain INVALID, not evidence of clear space.
    distance_far = distance_valid and distance == 4000
    tuning_supported = words[13] & 0xffc00000 == 0xa1000000
    return {"mode": {0: "INTEGRATED", 1: "VISION_ONLY", 2: "CHASSIS_INJECT"}.get(mode, "INVALID"),
            "inputSource": "SYNTHETIC" if mode == 2 else "REAL_CAMERA",
            "switchMask": (words[0] >> 2) & 63, "stableMask": (words[0] >> 8) & 63,
            "selection": selection, "digit": (words[0] >> 16) & 15,
            "taskArmed": bool(words[0] & (1 << 20)),
            "state": {0: "IDLE", 1: "SEARCH", 2: "ALIGN", 3: "APPROACH", 4: "DOCKED",
                      5: "LOST", 6: "ACQUIRE", 7: "HOLD", 8: "NOT_FOUND"}.get(state, "INVALID"),
            "sourceHealthyFresh": bool(words[0] & (1 << 25)),
            "targetObserved": bool(words[0] & (1 << 26)),
            "targetLockedFresh": bool(words[0] & (1 << 27)),
            "motionPermit": bool(words[0] & (1 << 28)), "irEstop": bool(words[0] & (1 << 29)),
            "sonarHold": bool(words[0] & (1 << 30)), "selectionMatches": bool(words[0] & (1 << 31)),
            "requestTag": words[1] & 65535, "frameId": words[1] >> 16,
            "configVersion": words[2] & 65535, "faultFlags": words[2] >> 16,
            "inputAgeUs": words[3], "scanElapsedUs": words[4], "scanRemainingUs": words[5],
            "scanBudgetUs": words[6], "scanBasis": "CALIBRATED_TIME" if words[15] & (1 << 29) else "SCAN_UNCALIBRATED",
            "leftCmS": signed7(words[7]), "rightCmS": signed7(words[7] >> 8),
            "rawCameraMode": bool(words[7] & (1 << 17)),
            "failure": {0: "NONE", 1: "SCAN_BUDGET", 2: "TASK_TIMEOUT", 3: "SCAN_UNCALIBRATED"}.get((words[7] >> 20) & 15, "UNKNOWN"),
            "stopReason": (words[7] >> 24) & 7, "distanceMm": distance,
            "distanceValid": distance_valid, "distanceFar": distance_far,
            "distanceKind": "FAR" if distance_far else "MEASURED" if distance_valid else "INVALID",
            "uartBusy": bool(words[8] & (1 << 14)),
            "zeroSent": bool(words[8] & (1 << 15)), "timeUs": words[9],
            "fatal": bool(words[10] & (1 << 5)), "perceptionReady": bool(words[11] & 2),
            "pendingVisualStart": bool(words[10] & (1 << 6)),
            "colourCalibrated": bool(words[11] & 4), "interactionBusy": bool(words[11] & 8),
            "chassisRxCount": words[12] & 65535, "chassisRxLastByte": (words[12] >> 16) & 255,
            "chassisRxFramingError": bool(words[12] & (1 << 24)),
            "leaseAgeUs": words[14], "leaseValid": bool(words[15] & (1 << 31)),
            "templateValid": bool(words[15] & (1 << 30)),
            "scanCalibrated": bool(words[15] & (1 << 29)),
            "framesEnabled": bool(words[15] & (1 << 28)),
            "tuningSupported": tuning_supported,
            "tuning": {name: (words[13] >> shift) & mask
                       for name, (shift, mask, _, _) in TUNING_FIELDS.items()} if tuning_supported else None,
            "words": [f"0x{word:08x}" for word in words]}


class Session:
    def __init__(self, args):
        self.args = args
        self.process = None
        self.lock = None
        self.lines = queue.Queue()
        self.serial = 0
        self.ready = False
        self.responseThread = None
        self.nativeLog = None
        self.nativeLogPath = None

    def __enter__(self):
        echo7.WORK.mkdir(parents=True, exist_ok=True)
        self.lock = (echo7.WORK / "chassis-session.lock").open("a+b")
        self.lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                if not self.lock.read(1):
                    self.lock.write(b"0"); self.lock.flush()
                self.lock.seek(0)
                msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.lock.close(); self.lock = None
            raise RuntimeError("another chassis session owns JTAG; use its Ctrl+C/STOP, no command was sent") from error
        try:
            stp = echo7.discover("quartus_stp", self.args.quartus_bin)
            sessionDir = Path(tempfile.mkdtemp(prefix="cctl_session_", dir=echo7.WORK))
            responsePath = sessionDir / "responses.txt"
            responsePath.touch()
            self.nativeLogPath = sessionDir / "quartus.log"
            self.nativeLog = self.nativeLogPath.open("w", encoding="utf-8")
            command = [stp, "-t", str(echo7.ROOT / "tools/tcl/chassis_session.tcl"),
                       self.args.cable or "AUTO", self.args.device or "AUTO", str(responsePath)]
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=self.nativeLog,
                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1,
                env=echo7.quartusEnvironment(Path(stp).parent))
            process = self.process
            def read_lines():
                # Explicit file-channel replies are flushed by Tcl. Ordinary
                # Quartus stdout is only a diagnostic log, never our protocol.
                pending = ""
                with responsePath.open("r", encoding="utf-8", errors="replace") as responses:
                    while True:
                        chunk = responses.read()
                        if chunk:
                            pending += chunk
                            while "\n" in pending:
                                line, pending = pending.split("\n", 1)
                                self.lines.put(line.rstrip("\r"))
                        elif process.poll() is not None:
                            self.lines.put(None)
                            break
                        else:
                            time.sleep(0.005)
            self.responseThread = threading.Thread(target=read_lines, daemon=True)
            self.responseThread.start()
            deadline = time.monotonic() + self.args.timeout
            while True:
                line = self._line(deadline)
                if line.startswith("CCTL_READY\t"):
                    self.ready = True
                    print(line, flush=True)
                    return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _line(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("JTAG response timeout; command delivery is unconfirmed")
        try:
            line = self.lines.get(timeout=remaining)
        except queue.Empty as error:
            raise TimeoutError("JTAG response timeout; command delivery is unconfirmed") from error
        if line is None:
            raise RuntimeError(f"Quartus STP ended; command delivery is unconfirmed; see {self.nativeLogPath}")
        if not line.startswith("CCTL_"):
            print(line, file=sys.stderr, flush=True)
        return line

    def call(self, operation, *values):
        self.serial += 1
        self.process.stdin.write("\t".join(map(str, (self.serial, operation, *values))) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + self.args.timeout
        while True:
            line = self._line(deadline)
            fields = line.split("\t", 2)
            if len(fields) == 3 and fields[0] in ("CCTL_OK", "CCTL_ERROR"):
                if fields[1] != str(self.serial):
                    raise RuntimeError("CCTL response sequence mismatch")
                if fields[0] == "CCTL_ERROR":
                    raise RuntimeError(fields[2])
                return fields[2]

    def tx(self, opcode, payload=0):
        return self.call("TX", opcode, payload)

    def status(self, maintain_lease=False):
        operation = "STATUS_LEASE" if maintain_lease else "STATUS"
        return decode_status([int(value) for value in self.call(operation).split(",")])

    def bstatus(self, maintain_lease=False):
        from debug_decode import decodeWords
        values = [int(value) for value in self.call("BSTATUS_LEASE" if maintain_lease else "BSTATUS").split(",")]
        if len(values) != 97:
            raise RuntimeError("incomplete BCTL frozen status")
        decoded = decodeWords(values[1:])
        if decoded["buildId"] != values[0]:
            raise RuntimeError("BCTL header/frozen build identifier mismatch")
        return decoded

    def observation(self, **values):
        first, second = observation_words(**values)
        self.tx(5, first)
        self.tx(8)
        self.tx(6, second)
        self.tx(8)
        self.tx(7)

    def __exit__(self, *_):
        if self.process is not None:
            if self.process.poll() is None:
                try:
                    if self.ready:
                        self.call("QUIT")
                    else:
                        self.process.terminate()
                    self.process.wait(timeout=3)
                except (OSError, RuntimeError, TimeoutError, subprocess.TimeoutExpired):
                    self.process.terminate()
                    self.process.wait(timeout=3)
            if self.responseThread is not None:
                self.responseThread.join(timeout=1)
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.process = None
        if self.nativeLog is not None:
            self.nativeLog.close()
            self.nativeLog = None
        if self.lock is not None:
            self.lock.close()
            self.lock = None


def observation_summary(rows):
    """Describe all samples; collection completion is not functional acceptance."""
    cstates = [row["cctl"]["state"] for row in rows if "state" in row.get("cctl", {})]
    bstates = [row["bctl"]["state"] for row in rows if "state" in row.get("bctl", {})]
    return {
        "samples": len(rows), "completePairs": sum(bool(row.get("complete")) for row in rows),
        "cctlDistinctFrames": len({(s.get("requestTag"), s.get("configVersion"), s.get("frameId")) for s in cstates}),
        "bctlDistinctFrames": len({(s.get("buildId"), s.get("configVersion"), s.get("frameId"), s.get("captureStartUs")) for s in bstates}),
        "cctlHealthySamples": sum(bool(s.get("sourceHealthyFresh")) for s in cstates),
        "cctlLockedSamples": sum(bool(s.get("targetLockedFresh")) for s in cstates),
        "bctlBadFrameSamples": sum(not s.get("frameGood", False) for s in bstates),
        "cctlModes": sorted({s["mode"] for s in cstates}),
        "selectedDigits": sorted({s["digit"] for s in cstates}),
        "bctlBuildIds": sorted({s["buildId"] for s in bstates}),
        "bypassValues": sorted({s["bypassPerspective"] for s in bstates}),
        "meaning": "All polls retained, including held, bad and unlocked samples. CCTL and BCTL are separately frozen; no same-frame claim."}


def observe(session, out, label, *, samples=None, seconds=None, interval=0.1):
    """Read STATUS then BSTATUS only. Never select, ARM, renew a lease or STOP."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    rows = []
    status, failure = "COMPLETE", None
    metadata = {"schema": "echo7-observation-v1", "label": label,
                "startedAtUtc": datetime.now(timezone.utc).isoformat(),
                "inputSource": "LIVE_FPGA_JTAG_READONLY", "transport": "ONE_PERSISTENT_JTAG_SESSION",
                "requestedSamples": samples, "requestedSeconds": seconds, "intervalSeconds": interval,
                "operations": ["STATUS", "BSTATUS"], "samples": []}
    # Stream each complete or partial pair immediately; the finally block also
    # closes a valid JSON record after Ctrl+C or a transport error.
    with out.open("x", encoding="utf-8") as output:
        header = dict(metadata); del header["samples"]
        output.write(json.dumps(header, ensure_ascii=False)[:-1] + ', "samples": [\n')
        output.flush()
        try:
            while ((samples is not None and len(rows) < samples) or
                   (seconds is not None and time.monotonic() - started < seconds)):
                row = {"index": len(rows), "complete": False}
                rows.append(row)
                try:
                    for key, read in (("cctl", session.status), ("bctl", session.bstatus)):
                        row[key] = {"readStartSeconds": time.monotonic() - started}
                        row[key]["state"] = read()
                        row[key]["readEndSeconds"] = time.monotonic() - started
                    row["complete"] = True
                finally:
                    if len(rows) > 1: output.write(',\n')
                    output.write(json.dumps(row, ensure_ascii=False))
                    output.flush()
                c, b = row["cctl"]["state"], row["bctl"]["state"]
                print(json.dumps({"sample": row["index"], "mode": c["mode"], "digit": c["digit"],
                                  "cFrame": c["frameId"], "cLocked": c["targetLockedFresh"],
                                  "bFrame": b["frameId"], "bFrameGood": b["frameGood"],
                                  "bypass": b["bypassPerspective"]}), flush=True)
                if samples is not None and len(rows) >= samples: break
                time.sleep(interval)
        except BaseException as error:
            status = "INTERRUPTED" if isinstance(error, KeyboardInterrupt) else "FAIL"
            failure = str(error) or type(error).__name__
            raise
        finally:
            summary = observation_summary(rows)
            tail = {"status": status, "error": failure, "elapsedSeconds": time.monotonic() - started,
                    "summary": summary}
            output.write('\n], ' + json.dumps(tail, ensure_ascii=False)[1:])
            output.flush()
    print(json.dumps({"status": status, "path": str(out), "summary": summary}), flush=True)
    return {**metadata, "samples": rows, **tail}


def inject(session, rows, arm):
    """Rows hold a template while the same host session renews its lease."""
    if session.status()["mode"] != "CHASSIS_INJECT":
        raise RuntimeError("first run mode chassis; mode changes never ARM")
    try:
        for index, row in enumerate(rows):
            session.tx(8)
            session.observation(x=row.get("x", 120), y=row.get("y", 160),
                visible=row.get("visible", True), quality=row.get("quality", 255),
                frames_enabled=row.get("frames_enabled", True))
            session.tx(8)
            if index == 0 and arm:
                deadline = time.monotonic() + 3
                while True:
                    state = session.status(maintain_lease=True)
                    if state["selection"] != "VALID":
                        raise RuntimeError("select exactly one physical SW0-SW5 before ARM")
                    if state["sourceHealthyFresh"] and state["distanceValid"] and not state["sonarHold"]:
                        break
                    if state["irEstop"] or state["fatal"] or time.monotonic() >= deadline:
                        raise RuntimeError("ARM refused: current real safety/source conditions are not ready: " + json.dumps(state))
                    time.sleep(0.05)
                session.tx(3)
                state = session.status(maintain_lease=True)
                if not state["taskArmed"] and state["state"] not in ("DOCKED", "NOT_FOUND"):
                    raise RuntimeError("START transaction acknowledged but controller did not arm: " + json.dumps(state))
            print(json.dumps({"input": "SYNTHETIC_VISION", "row": row, "armRequested": arm}), flush=True)
            until = time.monotonic() + row["hold"]
            while time.monotonic() < until:
                # One session both renews between status pages and records the
                # SEARCH -> final ACQUIRE -> NOT_FOUND sequence, including HOLD.
                state = session.status(maintain_lease=True)
                print(json.dumps({"input": "SYNTHETIC_VISION", "state": state}), flush=True)
                time.sleep(min(0.1, max(0, until - time.monotonic())))
    finally:
        # Also revoke an already-armed task when a non-arming session ends.
        try:
            session.tx(4)
            print("STOP acknowledged; physical standstill requires observation.", flush=True)
        except (OSError, RuntimeError, TimeoutError) as error:
            print(f"STOP not confirmed: {error}; FPGA injection lease must expire.", file=sys.stderr)


def no_target_search_rows(state):
    """Current FPGA budget plus final zero/dwell/acquisition and polling margin."""
    budget = state["scanBudgetUs"] / 1_000_000
    if not 1 <= budget <= 120:
        raise ValueError("FPGA scanBudgetUs is outside 1..120 seconds")
    # Production final acquire: zero UART + 1.5s settle + 900ms confirmation.
    # Three seconds includes polling margin; HOLD may still consume wall time,
    # so retained state records, not this duration, decide observed completion.
    return [{"visible": False, "hold": budget + 3.0}]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quartus-bin")
    parser.add_argument("--cable")
    parser.add_argument("--device")
    parser.add_argument("--timeout", type=float, default=10)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("mode").add_argument("mode", choices=MODES)
    commands.add_parser("status").add_argument("--watch", action="store_true")
    observation = commands.add_parser("observe", help="read-only CCTL/BCTL samples; physical SW selects, no ARM/lease/STOP")
    duration = observation.add_mutually_exclusive_group(required=True)
    duration.add_argument("--samples", type=int, help="number of polls; duplicates/bad/unlocked frames are retained")
    duration.add_argument("--seconds", type=float, help="bounded sampling duration, excluding session startup")
    observation.add_argument("--out", type=Path, required=True, help="new JSON path, never overwritten")
    observation.add_argument("--label", required=True, help="scene/bay/trial label; does not change hardware")
    observation.add_argument("--interval", type=float, default=0.1, help="pause after each C/B pair (seconds)")
    commands.add_parser("stop", help="idle link only; an active session must use Ctrl+C")
    scan = commands.add_parser("scan", help="set bounded turn duration; calibrated requires three measured trials")
    scan.add_argument("--seconds", type=float, required=True)
    scan.add_argument("--calibrated", action="store_true", help="affirm actual three-trial floor calibration, not simulation")
    tuning = commands.add_parser("tune", help="read parameters; writes require stopped VISION_ONLY, no auto-start")
    for name, (_, _, low, high) in TUNING_FIELDS.items():
        tuning.add_argument("--" + name, type=int, metavar=f"{low}..{high}",
                            help="pixels from U120" if name == "tolerance" else "logical cm/s")
    tuning.add_argument("--defaults", action="store_true", help="restore 4/4/5/3 cm/s and +/-30 pixels; cannot mix with changes")
    shot = commands.add_parser("inject")
    shot.add_argument("--x", type=int, default=120)
    shot.add_argument("--y", type=int, default=160)
    shot.add_argument("--visible", type=int, choices=(0, 1), default=1)
    shot.add_argument("--quality", type=int, default=255)
    shot.add_argument("--hold", type=float, default=3)
    shot.add_argument("--arm", action="store_true")
    scenario = commands.add_parser("scenario")
    scenario.add_argument("name", choices=("left-centre-right-loss", "no-target-search", "stale-frames"))
    scenario.add_argument("--arm", action="store_true")
    play = commands.add_parser("play", help="JSON list of x/y/visible/quality/hold rows")
    play.add_argument("path", type=Path)
    play.add_argument("--arm", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0 or bool(args.cable) != bool(args.device):
        parser.error("positive timeout and both --cable/--device are required when specifying a target")
    try:
        if args.command == "observe":
            if (args.samples is not None and not 1 <= args.samples <= 10000 or
                    args.seconds is not None and not 0 < args.seconds <= 3600 or
                    not 0 <= args.interval <= 10 or not args.label.strip()):
                raise ValueError("observe requires samples 1..10000 or seconds >0..3600, interval 0..10 and a label")
            if args.out.exists():
                raise FileExistsError("refusing to overwrite observation output")
        rows = None
        if args.command == "inject":
            observation_words(args.x, args.y, args.visible, args.quality)
            rows = [{"x": args.x, "y": args.y, "visible": args.visible, "quality": args.quality, "hold": args.hold}]
        elif args.command == "scenario":
            rows = ({"left-centre-right-loss": [{"x": x, "hold": 3, "visible": visible} for x, visible in
                      ((80, 1), (120, 1), (160, 1), (120, 0))],
                     "no-target-search": [{"visible": False, "hold": 10}],
                     "stale-frames": [{"hold": 3}, {"frames_enabled": False, "hold": 2}]}[args.name])
        elif args.command == "play":
            rows = json.loads(args.path.read_text(encoding="utf-8"))
        if rows is not None:
            if not isinstance(rows, list) or not rows:
                raise ValueError("play needs a nonempty row list")
            for row in rows:
                if not isinstance(row, dict) or not 0 < row.get("hold", 0) <= 120:
                    raise ValueError("each row needs hold > 0 and <= 120 seconds")
                if set(row) - {"x", "y", "visible", "quality", "hold", "frames_enabled"}:
                    raise ValueError("unknown scenario field")
                observation_words(x=row.get("x", 120), y=row.get("y", 160), quality=row.get("quality", 255))
        if args.command == "scan" and not 1 <= args.seconds <= 120:
            raise ValueError("scan duration must be 1..120 seconds")
        if args.command == "tune":
            changes = {name: getattr(args, name) for name in TUNING_FIELDS if getattr(args, name) is not None}
            if args.defaults and changes:
                raise ValueError("--defaults cannot be combined with parameter changes")
            for name, value in changes.items():
                low, high = TUNING_FIELDS[name][2:]
                if not low <= value <= high:
                    raise ValueError(f"{name} must be in {low}..{high}")
        with Session(args) as session:
            if args.command == "mode":
                session.tx(1, MODES[args.mode]); print(json.dumps(session.status(), indent=2))
            elif args.command == "stop":
                session.tx(4); print("STOP acknowledged; no physical standstill measurement implied.")
            elif args.command == "scan":
                session.tx(9, round(args.seconds * 1_000_000))
                session.tx(10, int(args.calibrated)); print(json.dumps(session.status(), indent=2))
            elif args.command == "tune":
                print(json.dumps(tune(session, defaults=args.defaults, **changes), indent=2))
            elif args.command == "status":
                while True:
                    print(json.dumps(session.status()), flush=True)
                    if not args.watch: break
                    time.sleep(0.5)
            elif args.command == "observe":
                observe(session, args.out, args.label, samples=args.samples,
                        seconds=args.seconds, interval=args.interval)
            else:
                if args.command == "scenario" and args.name == "no-target-search":
                    rows = no_target_search_rows(session.status())
                inject(session, rows, args.arm)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, TimeoutError, echo7.Blocked) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
