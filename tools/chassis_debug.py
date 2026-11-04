#!/usr/bin/env python3
"""CCTL chassis debugging through one persistent Quartus STP session.

Physical SW0-SW5 always select the bay. This tool never writes wheel speeds or
sonar values. `stop` is standalone only when the JTAG link is idle; use Ctrl+C
in an active injection session. A lost process is stopped by the FPGA lease.
"""
from __future__ import annotations

import argparse
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
            "stopReason": (words[7] >> 24) & 7, "distanceMm": words[8] & 4095,
            "distanceValid": bool(words[8] & (1 << 12)), "uartBusy": bool(words[8] & (1 << 14)),
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
                session.tx(8)
                time.sleep(min(0.1, max(0, until - time.monotonic())))
    finally:
        # Also revoke an already-armed task when a non-arming session ends.
        try:
            session.tx(4)
            print("STOP acknowledged; physical standstill requires observation.", flush=True)
        except (OSError, RuntimeError, TimeoutError) as error:
            print(f"STOP not confirmed: {error}; FPGA injection lease must expire.", file=sys.stderr)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quartus-bin")
    parser.add_argument("--cable")
    parser.add_argument("--device")
    parser.add_argument("--timeout", type=float, default=10)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("mode").add_argument("mode", choices=MODES)
    commands.add_parser("status").add_argument("--watch", action="store_true")
    commands.add_parser("stop", help="idle link only; an active session must use Ctrl+C")
    scan = commands.add_parser("scan", help="set bounded turn duration; calibrated requires three measured trials")
    scan.add_argument("--seconds", type=float, required=True)
    scan.add_argument("--calibrated", action="store_true", help="affirm actual three-trial floor calibration, not simulation")
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
        with Session(args) as session:
            if args.command == "mode":
                session.tx(1, MODES[args.mode]); print(json.dumps(session.status(), indent=2))
            elif args.command == "stop":
                session.tx(4); print("STOP acknowledged; no physical standstill measurement implied.")
            elif args.command == "scan":
                session.tx(9, round(args.seconds * 1_000_000))
                session.tx(10, int(args.calibrated)); print(json.dumps(session.status(), indent=2))
            elif args.command == "status":
                while True:
                    print(json.dumps(session.status()), flush=True)
                    if not args.watch: break
                    time.sleep(0.5)
            else:
                inject(session, rows, args.arm)
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, RuntimeError, TimeoutError, echo7.Blocked) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
