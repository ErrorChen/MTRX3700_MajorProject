#!/usr/bin/env python3
"""ECHO-7 Member B evidence runner. All external commands use argument arrays.

Exit 0 is a completed check, 1 is a failed check, and 2 is an external block or
an explicitly deferred function. MODEL, RTL_SIM and hardware are never merged.
Large logs live in build/member_b, not in the source directories.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent / "lib"
sys.path.insert(0, str(HERE))
WORK = ROOT / "build/member_b"
STATE = WORK / "device.json"


class Blocked(RuntimeError):
    pass


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def toolDirs():
    """Prefer the project's recorded 18.1 toolchain; discover roots from the host."""
    roots = []
    for var in ("QUARTUS_ROOTDIR", "QUARTUS_ROOTDIR_OVERRIDE"):
        value = os.environ.get(var)
        if value:
            root = Path(value)
            roots.append(root)
            installation = root.parent.parent
            if installation.is_dir():
                roots.extend(p / "quartus" for p in sorted(installation.iterdir()) if p.is_dir())
    roots = sorted(set(roots), key=lambda p: ("18.1" not in str(p), str(p)))
    return roots


def discover(name, override=None):
    if override:
        path = Path(override) / (name + (".exe" if os.name == "nt" else ""))
        if path.is_file():
            return str(path.resolve())
        raise Blocked(f"requested tool does not exist: {path}")
    suffix = ".exe" if os.name == "nt" else ""
    for root in toolDirs():
        subdirs = [root / "bin64", root / "bin"]
        if name in ("vsim", "vlog", "vlib"):
            subdirs = [root.parent / "modelsim_ase/win32aloem", root.parent / "modelsim_ase/linuxaloem"]
        for folder in subdirs:
            path = folder / (name + suffix)
            if path.is_file():
                return str(path.resolve())
    found = shutil.which(name)
    if found and "WindowsApps" not in found:
        return found
    raise Blocked(f"{name} was not found; use --quartus-bin or --modelsim-bin")


def sourceIdentity():
    """Hash the B project's explicit source/constraint closure, excluding its ID.

    Quartus databases and .qws UI state must not change the build identity.
    Vendor IP versions are recorded by the build tool.
    """
    project = ROOT / "quartus"
    qsf = project / "PartBDebug.qsf"
    files = {qsf, project / "PartBDebug.qpf"}
    searchPaths = [project]
    text = qsf.read_text(encoding="utf-8")
    for name in re.findall(r"^set_global_assignment\s+-name SEARCH_PATH\s+(.+?)\s*$", text, re.M):
        searchPaths.append((project / name.strip().strip('"{}')).resolve())
    for kind, name in re.findall(r"^set_global_assignment\s+-name (\w+_FILE)\s+(.+?)\s*$", text, re.M):
        files.add((project / name.strip().strip('"{}')).resolve())
    pending = list(files)
    seen = set()
    while pending:
        path = pending.pop()
        if path in seen or path.name == "memberBBuildId.svh":
            continue
        seen.add(path)
        if not path.is_file():
            raise RuntimeError(f"B project dependency is missing: {path}")
        if path.suffix.lower() in (".sv", ".svh", ".v", ".vh", ".sdc", ".qip"):
            source = path.read_text(encoding="utf-8", errors="replace")
            includes = re.findall(r'`include\s+"([^"]+)"', source)
            includes += re.findall(r'^\s*source\s+["{]?([^"}\s]+)', source, re.M)
            for include in includes:
                if Path(include).name == "memberBBuildId.svh":
                    continue
                candidates = [path.parent / include, *(folder / include for folder in searchPaths)]
                found = next((p.resolve() for p in candidates if p.is_file()), None)
                if found is None:
                    raise RuntimeError(f"unresolved source include {include} in {path}")
                files.add(found); pending.append(found)
    files = {p for p in files if p.name != "memberBBuildId.svh"}
    hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in sorted(files)}
    identity = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"sha256": identity, "buildId": int(identity[:8], 16), "files": hashes}


def checkTimingReports(summaryText, reportText):
    """Require all four corner summaries and no unconstrained clock/path rows."""
    items = re.findall(r"Type\s*:\s*(.+)\nSlack\s*:\s*(-?\d+(?:\.\d+)?)", summaryText)
    if not items:
        raise RuntimeError("timing summary has no analysed slack values")
    for check in ("Setup", "Hold", "Minimum Pulse Width"):
        if not any(check in name for name, _ in items):
            raise RuntimeError(f"timing summary is missing {check} checks")
    negative = [{"check": name, "slackNs": float(value)} for name, value in items if float(value) < 0]
    if negative:
        raise RuntimeError("negative timing slack: " + json.dumps(negative))
    rows = re.findall(r";\s*(Illegal Clocks|Unconstrained [^;]+)\s*;\s*(\d+)\s*;\s*(\d+)\s*;", reportText)
    if len(rows) < 6:
        raise RuntimeError("unconstrained path summary is missing or incomplete")
    if any(int(a) or int(b) for _, a, b in rows):
        raise RuntimeError("unconstrained paths/clocks remain: " + repr(rows))
    return {"analysedChecks": len(items), "worstSlackNs": min(float(v) for _, v in items),
            "unconstrainedSummary": rows}


class Runner:
    def __init__(self, args):
        self.args = args
        self.out = WORK / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + args.command)
        self.out.mkdir(parents=True)
        self.result = {"schema": "echo7-cli-v1", "command": args.command, "status": "RUNNING",
                       "startedUtc": datetime.now(timezone.utc).isoformat(), "inputSource": "NONE",
                       "outputDirectory": str(self.out), "python": sys.executable,
                       "runnerSha256": digest(__file__), "steps": []}
        self.selectedTarget = None
        self.logCounts = {}

    def run(self, label, args, cwd=ROOT, timeout=None, checked=True):
        command = [str(a) for a in args]
        occurrence = self.logCounts.get(label, 0)
        self.logCounts[label] = occurrence + 1
        logName = label if occurrence == 0 else f"{label}_{occurrence:04d}"
        logPath = self.out / (logName + ".log")
        scriptHashes = {arg: digest(arg) for arg in command[1:]
                        if Path(arg).suffix.lower() in (".py", ".tcl") and Path(arg).is_file()}
        started = time.monotonic()
        process = None
        try:
            process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, errors="replace", shell=False, start_new_session=(os.name == "posix"))
            output, _ = process.communicate(timeout=timeout or self.args.timeout)
            code = process.returncode
        except subprocess.TimeoutExpired as exc:
            # Stop only this owned command and its descendants. A Quartus shell
            # timeout must not leave its compiler writing the build DB behind.
            if os.name == "nt":
                try:
                    terminated = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=5)
                    treeStopped = terminated.returncode == 0
                except (OSError, subprocess.SubprocessError):
                    treeStopped = False
                if not treeStopped:
                    self.result.setdefault("terminationWarnings", []).append(
                        "taskkill could not enumerate/terminate the owned tree; directly terminating the owned process handle")
                if process.poll() is None:
                    process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            try:
                trailing, _ = process.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                # An unkillable descendant can retain the stdout pipe even
                # after its parent has stopped. Preserve bounded failure and
                # explicitly record the remaining cleanup uncertainty.
                process.stdout.close()
                trailing = "owned command stopped; descendant stdout pipe did not close"
                self.result.setdefault("terminationWarnings", []).append(trailing)
            output = str(exc) + "\n" + trailing
            code = 124
        logPath.write_text("COMMAND " + json.dumps(command) + "\n" + output, encoding="utf-8")
        self.result["steps"].append({"name": label, "command": command, "returncode": code,
                                     "level": self.result.get("level", "TOOLS"),
                                     "scriptSha256": scriptHashes,
                                     "elapsedSeconds": round(time.monotonic() - started, 3), "log": str(logPath)})
        if checked and code:
            raise RuntimeError(f"{label} exited {code}; see {logPath}")
        return code, output

    def qt(self, name):
        return discover(name, self.args.quartus_bin)

    def doctor(self):
        self.result["level"] = "DISCOVERY"
        self.result["tools"] = {}
        for name in ("quartus_sh", "quartus_sta", "quartus_pgm", "quartus_stp", "jtagconfig", "vsim", "vlog", "vlib"):
            try:
                path = discover(name, self.args.modelsim_bin if name in ("vsim", "vlog", "vlib") else self.args.quartus_bin)
                self.result["tools"][name] = path
                if name == "quartus_sh":
                    self.run(name + "_version", [path, "--version"])
                if name == "vsim":
                    self.run(name + "_version", [path, "-version"])
            except Blocked as exc:
                self.result["tools"][name] = {"status": "BLOCKED", "reason": str(exc)}
        self.run("git_status", ["git", "status", "--short"], ROOT)
        self.run("git_head", ["git", "rev-parse", "HEAD"], ROOT)
        self.result["projects"] = {"PartBDebug": (ROOT / "quartus/PartBDebug.qpf").is_file()}
        self.result["pythonDependencies"] = {n: importlib.util.find_spec(n) is not None for n in ("numpy", "PIL")}
        self.result["pythonVersion"] = sys.version
        self.result["taskInputs"] = {name: (ROOT / name).is_file() for name in (
            "docs/inputs/COURSE_REQUIREMENTS.md", "docs/inputs/SOURCE_NOTES.md", "docs/inputs/ARCHITECTURE.md", "docs/MEMBER_C_INTERFACE.md",
            "assets/markers/marker_spec.json", "assets/markers/scene_manifest.json", "assets/markers/ECHO7_All_Markers_A4_v2.pdf")}
        if self.result["projects"]["PartBDebug"]:
            self.result["sourceDiscovery"] = sourceIdentity()
            self.result["sourceDiscoveryMeaning"] = "STATIC_FILE_CLOSURE_ONLY; no synthesis, timing, programming or recognition is implied"
        self.run("jtagconfig", [self.qt("jtagconfig")], checked=False)
        _, cables = self.run("programmer_list", [self.qt("quartus_pgm"), "-l"], checked=False)
        self.result["jtagAvailable"] = "No JTAG hardware available" not in cables
        targets = self.targets()
        self.result["targets"] = targets
        if not targets:
            raise Blocked("no 5CSEMA5 target detected: connect/power the DE1-SoC USB-Blaster and run doctor again")

    def targets(self):
        _, output = self.run("jtag_targets", [self.qt("quartus_stp"), "-t", ROOT / "tools/tcl/jtag_control.tcl", "list"])
        targets = []
        for line in output.splitlines():
            if line.startswith("ECHO7_TARGET\t"):
                _, cable, device, index = line.split("\t")
                targets.append({"cable": cable, "device": device, "index": int(index)})
        return targets

    def target(self, programming=False):
        # A multi-step run keeps one explicitly identified target. The Tcl I/O
        # commands still verify that exact cable/device is present on every use.
        if self.selectedTarget is not None:
            return self.selectedTarget
        targets = self.targets()
        if self.args.cable:
            targets = [x for x in targets if x["cable"] == self.args.cable]
        if self.args.device:
            targets = [x for x in targets if x["device"] == self.args.device or str(x["index"]) == self.args.device]
        if len(targets) != 1:
            raise Blocked(f"expected one selected 5CSEMA5 target, found {len(targets)}; use exact --cable and --device")
        target = targets[0]
        if STATE.exists():
            previous = json.loads(STATE.read_text())
            # Selection is explicit and recorded. Never silently capture a different board.
            if previous.get("programmedTarget") and previous["programmedTarget"] != target and not programming:
                raise Blocked("target differs from the last programmed device; program this target explicitly first")
        self.result["target"] = target
        self.selectedTarget = target
        return target

    def rtl(self):
        self.result["level"] = "RTL_SIM"
        self.result["inputSource"] = "SYNTHETIC_RTL_VECTORS"
        vsim = discover("vsim", self.args.modelsim_bin)
        binDir = Path(vsim).parent
        suffix = ".exe" if os.name == "nt" else ""
        self.run("simulator_version", [vsim, "-version"])
        config = json.loads((ROOT / "tests/rtl/manifest.json").read_text())
        if getattr(self.args, "only", None):
            requested = set(self.args.only)
            available = {test["name"] for test in config["tests"]}
            if requested - available:
                raise RuntimeError("unknown RTL test names: " + repr(sorted(requested - available)))
            config["tests"] = [test for test in config["tests"] if test["name"] in requested]
        self.result["rtlTests"] = []
        # Attribute the complete suite to one source snapshot. Per-test checks
        # alone miss an early bench's source changing while later benches run.
        suiteHashes = {path: digest(ROOT / path) for test in config["tests"] for path in test["sources"]}
        self.result["rtlSuiteSourceSha256"] = suiteHashes
        vectors = self.out / "vectors"
        self.run("candidate_vectors", [sys.executable, ROOT / "tools/lib/candidates_reclaimed_model.py",
                                    "--write-vectors", vectors])
        if (HERE / "export_vision_vectors.py").exists():
            self.run("vision_vectors", [sys.executable, HERE / "export_vision_vectors.py", "--out", vectors])
        if any("projectiveMarkerReader.sv" in path for test in config["tests"] for path in test["sources"]):
            self.run("projective_vectors", [sys.executable, HERE / "export_projective_vectors.py", "--out", vectors])
            self.result["inputSource"] = "MIXED_SYNTHETIC_AND_RECORDED_CAMERA_RTL_REPLAY"
        for test in config["tests"]:
            name = test["name"]
            folder = self.out / name
            folder.mkdir()
            library = folder / "simlib"
            self.run(name + "_vlib", [binDir / ("vlib" + suffix), library], cwd=folder)
            sources = [ROOT / p for p in test["sources"]]
            sourceHashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
            testResult = {"name": name, "status": "RUNNING", "sourceSha256": sourceHashes,
                          "inputSource": test.get("inputSource", "SYNTHETIC_RTL_VECTORS"),
                          "simulationModelDefines": test.get("defines", [])}
            self.result["rtlTests"].append(testResult)
            # The course FrameGrab names its portable RAM/probe behavioural
            # branch VERILATOR; use that existing branch under ModelSim too.
            # This is RTL simulation of the wrapper, not Intel IP/JTAG validation.
            defines = ["+define+" + d for d in test.get("defines", [])]
            self.run(name + "_compile", [binDir / ("vlog" + suffix), "-sv", *defines, "-work", library, *sources], cwd=folder)
            plusargs = [value.replace("{vectors}", vectors.as_posix()) for value in test.get("plusargs", [])]
            command = [vsim, "-c", "-onfinish", "exit", "-lib", library, test.get("top", name),
                       "+VECTORS=" + vectors.as_posix(), "+VECTOR_DIR=" + vectors.as_posix(), *plusargs, "-do",
                       "onerror {quit -code 1}; onbreak {quit -code 1}; run -all; quit -code 0"]
            _, output = self.run(name + "_simulation", command, cwd=folder,
                                 timeout=max(self.args.timeout, test.get("timeoutSeconds", 0)))
            if test["passMarker"] not in output or re.search(r"\bFAIL(?:ED)?\b|\*\*\s+(Error|Fatal)", output):
                testResult["status"] = "FAIL"
                raise RuntimeError(f"{name} has missing PASS marker or simulator assertion/error")
            if any(digest(ROOT / p) != value for p, value in sourceHashes.items()):
                testResult["status"] = "SOURCE_CHANGED_DURING_TEST"
                raise RuntimeError(f"{name} sources changed during simulation; rerun for an attributable result")
            testResult["status"] = "PASS"
        changed = [path for path, value in suiteHashes.items() if digest(ROOT / path) != value]
        if changed:
            self.result["sourceChangedDuringSuite"] = changed
            raise RuntimeError("RTL suite sources changed during the run; completed benches retain their individual source hashes")

    def replay(self):
        self.result["level"] = "MODEL"
        self.result["inputSource"] = "MIXED_SYNTHETIC_AND_RECORDED_CAMERA_REPLAY"

        self.run("member_b_models", [sys.executable, "-m", "unittest", "discover", "-s", ROOT / "tests/python", "-p", "test_*.py", "-v"])
        self.run("vision_counterfactuals", [sys.executable, ROOT / "tests/python/test_vision.py"])

    def build(self):
        self.result["level"] = "QUARTUS_FIT_TIMING"
        qsf = ROOT / "quartus/PartBDebug.qsf"
        if not qsf.exists():
            raise Blocked("PartBDebug.qsf is not available yet")
        text = qsf.read_text()
        if not re.search(r"TOP_LEVEL_ENTITY\s+perceptionDemoTop\b", text) or "5CSEMA5F31C6" not in text:
            raise RuntimeError("PartBDebug must use perceptionDemoTop and 5CSEMA5F31C6")
        identity = sourceIdentity()
        header = ROOT / "rtl/common/memberBBuildId.svh"
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text("// Generated by echo7.py build from sourceIdentity().\n`define MEMBER_B_BUILD_ID 32'h%08x\n" % identity["buildId"])
        self.result["source"] = identity
        self.run("quartus_version", [self.qt("quartus_sh"), "--version"])
        sof = ROOT / "quartus/output_files/PartBDebug.sof"
        oldTime = sof.stat().st_mtime_ns if sof.exists() else None
        _, compileOutput = self.run("compile", [self.qt("quartus_sh"), "--flow", "compile", "PartBDebug"], ROOT / "quartus", timeout=max(self.args.timeout, 3600))
        self.result["warnings"] = [line.strip() for line in compileOutput.splitlines() if "Warning (" in line]
        if any("Critical Warning" in line for line in self.result["warnings"]):
            raise RuntimeError("critical Quartus warnings require correction/review before this build can be programmed")
        if sourceIdentity()["sha256"] != identity["sha256"]:
            raise RuntimeError("sources changed during compilation; build cannot be attributed to its initial source hash")
        if not sof.exists() or sof.stat().st_mtime_ns == oldTime:
            raise RuntimeError("compile did not produce a fresh PartBDebug.sof")
        self.run("timing_gate", [self.qt("quartus_sta"), "-t", ROOT / "tools/tcl/timing_check.tcl", "PartBDebug", self.out / "timing.json"], ROOT / "quartus")
        timing = json.loads((self.out / "timing.json").read_text())
        if timing.get("analysisStage") != "POST_FIT":
            raise RuntimeError("build timing acceptance requires post-fit analysis, not a post-map constraint audit")
        timing["reportGate"] = checkTimingReports(
            (ROOT / "quartus/output_files/PartBDebug.sta.summary").read_text(),
            (ROOT / "quartus/output_files/PartBDebug.sta.rpt").read_text())
        self.result["timing"] = timing
        if timing.get("status") != "PASS":
            raise RuntimeError("timing checks did not pass")
        self.result["sof"] = {"path": str(sof), "sha256": digest(sof)}
        self.result["fitterSummary"] = (ROOT / "quartus/output_files/PartBDebug.fit.summary").read_text()
        self.result["status"] = "PASS"
        (WORK / "last_build.json").write_text(json.dumps(self.result, indent=2))

    def control(self, command=0):
        # Reading the loaded design or sending an interface stimulus verifies
        # board communication. Camera recognition is a separate capture/test.
        self.result.setdefault("level", "PROGRAMMED")
        target = self.target()
        _, output = self.run("bctl", [self.qt("quartus_stp"), "-t", ROOT / "tools/tcl/jtag_control.tcl", "control",
                                      target["cable"], target["device"], str(command)])
        match = re.search(r"^ECHO7_HEADER\t([01]{96})$", output, re.M)
        if not match:
            raise RuntimeError("BCTL did not return its versioned status header")
        bits = match.group(1)
        magic, buildId, meta = (int(bits[i:i+32], 2) for i in (0, 32, 64))
        debugSchema = meta >> 24
        if magic != 0x42444247 or debugSchema not in (1, 2) or (meta >> 16) & 255 != 2 or meta & 255 != 96:
            raise RuntimeError(f"unsupported BCTL header magic={magic:08x}, meta={meta:08x}")
        words = re.findall(r"^ECHO7_WORD\t(\d+)\t([01]{32})$", output, re.M)
        if [int(n) for n, _ in words] != list(range(96)):
            raise RuntimeError("BCTL frozen word sequence is incomplete or reordered")
        status = {"magic": hex(magic), "schema": debugSchema, "contract": 2, "buildId": buildId,
                  "words": [int(word, 2) for _, word in words]}
        from debug_decode import decodeWords
        status["decoded"] = decodeWords(status["words"])
        if status["decoded"]["debugSchemaVersion"] != debugSchema:
            raise RuntimeError("BCTL header and frozen status have different schema versions")
        if status["decoded"]["buildId"] != buildId:
            raise RuntimeError("BCTL header and frozen status have different build IDs")
        self.result["boardStatus"] = status
        self.result["inputSource"] = "JTAG_INTERFACE_STIMULUS" if command else "LIVE_JTAG_STATUS"
        return status

    def program(self):
        self.result["level"] = "PROGRAMMED"
        buildPath = WORK / "last_build.json"
        if not buildPath.exists():
            raise Blocked("no successful build manifest; run build first")
        build = json.loads(buildPath.read_text())
        sof = Path(build["sof"]["path"])
        if build.get("status") != "PASS" or digest(sof) != build["sof"]["sha256"]:
            raise RuntimeError("SOF no longer matches the successful build manifest")
        if sourceIdentity()["sha256"] != build["source"]["sha256"]:
            raise RuntimeError("RTL/project changed since the successful build; rebuild before programming")
        target = self.target(programming=True)
        self.run("program", [self.qt("quartus_pgm"), "-c", target["cable"], "-m", "JTAG", "-o", f"p;{sof}@{target['index']}"])
        self.result["build"] = buildPath.as_posix()
        STATE.write_text(json.dumps({"programmedTarget": target, "source": build["source"], "sof": build["sof"],
                                     "programmedAtUtc": datetime.now(timezone.utc).isoformat()}, indent=2))
        status = self.control()
        if status["buildId"] != build["source"]["buildId"]:
            raise RuntimeError("programmed device buildId differs from the successful source/SOF manifest")
        self.result["programmerSucceeded"] = True
        self.result["buildIdVerified"] = True

    def capture(self):
        held = getattr(self.args, "held", False)
        self.result["level"] = "CAMERA_HW"
        self.result["inputSource"] = "LIVE_CAMERA" if not held else "HELD_CAMERA_SNAPSHOT"
        target = self.target()
        args = [self.qt("quartus_stp"), "-t", ROOT / "tools/tcl/grab_jtag.tcl", self.out / "capture",
                "--cable", target["cable"], "--device", target["device"], "--python", sys.executable, "--mvfp", "0x07"]
        if held:
            args.append("--held")
        self.run("capture", args, timeout=max(self.args.timeout, 300))
        # quartus_stp's exit code is insufficient: decode and CRC are checked again independently.
        spec = importlib.util.spec_from_file_location("echo7Grab", ROOT / "tools/capture/grab.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        dump = self.out / "capture/dump.bin"
        decoded = module.decode(dump.read_bytes())
        if decoded["offset"] != 0 or decoded["bytes"] != dump.stat().st_size:
            raise RuntimeError("snapshot has prefix/trailing bytes; exact GRAB framing is required")
        self.result["snapshot"] = {k: decoded[k] for k in ("width", "height", "n_results", "crc", "results")}
        self.result["dumpSha256"] = digest(dump)
        from debug_decode import checkGrabSchema, decodeGrabWords, compareMarkerPixels
        checkGrabSchema(decoded["results"])
        buildPath = WORK / "last_build.json"
        if not buildPath.exists():
            raise Blocked("B GRAB needs a successful build manifest to verify its source buildId")
        expectedBuildId = json.loads(buildPath.read_text())["source"]["buildId"]
        self.result["packetType"] = "MEMBER_B"
        self.result["recognition"] = decodeGrabWords(decoded["results"], expectedBuildId)
        self.result["frameId"] = decoded["results"][96]
        self.result["fresh"] = not held
        comparison = compareMarkerPixels(self.out / "capture/frame.png", self.result["recognition"], self.out / "glyph_check")
        self.result["glyphAgreement"] = comparison
        recognition = self.result["recognition"]
        script = "projective_reference.py" if recognition["readerAlgorithm"] == 1 else "vision_reference.py"
        profileArgs = (["--white-min", str(recognition["whiteMinimum"]), "--max-spread", str(recognition["whiteMaxSpread"]),
                        "--colour-algorithm", str(recognition["colourAlgorithm"])]
                       if recognition["readerAlgorithm"] == 1 else ["--cleanup"])
        self.run("pixel_reference", [sys.executable, HERE / script, self.out / "capture/frame.png",
                 "--orientation", str(recognition["orientationProfile"]),
                 "--red-min", str(recognition["redMinimum"]),
                 "--blue-min", str(recognition["blueMinimum"]), *profileArgs,
                 "--source", "RECORDED_CAMERA", "--out", self.out / "pixel_reference"])
        if comparison["status"] != "PASS":
            raise RuntimeError("captured glyph pixels disagree with the FPGA same-frame marker decisions")
        contextPath = STATE
        context = json.loads(contextPath.read_text()) if contextPath.exists() else {}
        self.result["programmingContext"] = str(contextPath) if context else None
        epoch = context.get("startedUtc", context.get("programmedAtUtc", "UNRECORDED"))
        if not held:
            historyPath = WORK / "last_capture.json"
            if historyPath.exists():
                previous = json.loads(historyPath.read_text())
                if previous.get("target") == target and previous.get("programmingEpoch") == epoch:
                    delta = (self.result["frameId"] - previous["frameId"]) & 0xffff
                    if not 0 < delta < 0x8000:
                        raise RuntimeError("fresh capture did not advance native frameId; repeated held frames cannot confirm lock")
            historyPath.write_text(json.dumps({"target": target, "frameId": self.result["frameId"],
                                               "programmingEpoch": epoch, "dumpSha256": digest(dump)}))

    def hardware(self):
        self.result["level"] = "CAMERA_HW"
        self.result["inputSource"] = "LIVE_CAMERA_STATUS_WITH_JTAG_TARGET_REQUESTS"
        records = []
        self.result["hardwareFrames"] = records
        initial = self.control()["decoded"]
        initialDropCount = initial["bufferDropCount"]
        initialCompletionDiscardCount = initial["completionDiscardCount"]
        initialFaultFlags = initial["status"]["faultFlags"]
        self.result["initialDiagnostics"] = {"bufferDropCount": initialDropCount, "faultFlags": initialFaultFlags,
                                             "completionDiscardCount": initialCompletionDiscardCount}
        if initialCompletionDiscardCount == 0xffff:
            raise RuntimeError("completion discard counter is saturated; reset the loaded design before measuring new hardware stability")
        lastFrame = None
        deadline = time.monotonic() + self.args.timeout
        for bay in range(1, 7):
            self.control((1 << 24) | bay)
            collected = 0
            while collected < 5:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"hardware acceptance timed out: bay{bay} collected {collected}/5 distinct locked frames")
                state = self.control()["decoded"]
                # Check every live snapshot, including a bad frame or a report
                # still carrying the previous target request. Such a discarded
                # completion must not disappear while waiting for a lock.
                if state["completionDiscardCount"] != initialCompletionDiscardCount:
                    raise RuntimeError("completionDiscardCount changed during hardware acceptance; an older completed observation was discarded")
                frameId = state["frameId"]
                if lastFrame is not None:
                    delta = (frameId - lastFrame) & 0xffff
                    if delta == 0:
                        continue
                    if delta >= 0x8000:
                        raise RuntimeError("hardware frame sequence moved backwards; repeated/old frames cannot confirm lock")
                lastFrame = frameId
                records.append(state)
                (self.out / "hardware_frames.json").write_text(json.dumps(records, indent=2))
                report, request, status = state["targetReport"], state["activeRequest"], state["status"]
                if report["frameId"] != frameId or report["requestTag"] != request["requestTag"] or report["bayId"] != bay:
                    continue
                acceptedBlue = sorted(m["digit"] for m in state["markers"] if m["accepted"] and m["isBlue"])
                acceptedRed = sorted(m["digit"] for m in state["markers"] if m["accepted"] and not m["isBlue"])
                if acceptedBlue != [1, 2, 3, 4, 5, 6] or acceptedRed != [1, 2]:
                    raise RuntimeError("fixed full-sheet acceptance failed: actual accepted pixel IDs=" + repr((acceptedRed, acceptedBlue)))
                if (status["faultFlags"] & ~initialFaultFlags & 7) or state["bufferDropCount"] != initialDropCount:
                    raise RuntimeError("camera/candidate/buffer diagnostics indicate dropped or corrupted observations")
                if not all(report[name] for name in ("targetSelected", "frameGood", "observed", "locked")) or report["ambiguous"]:
                    continue
                if report["configVersion"] != status["activeCfgVersion"] or not state["freshAtSnapshot"]:
                    raise RuntimeError("hardware target report has stale configuration or capture age")
                if not status["perceptionReady"] or status["interactionBusy"] or not status["calibrated"]:
                    continue
                collected += 1
        self.result["lockedFramesPerBay"] = 5
        self.result["acceptanceScope"] = "30 distinct current fixed-sheet observations; initial project gate, not course rubric or general accuracy"

    def execute(self):
        c = self.args.command
        if c == "doctor": self.doctor()
        elif c == "test":
            if self.args.rtl: self.rtl()
            elif self.args.replay: self.replay()
            else: self.hardware()
        elif c == "build": self.build()
        elif c == "program": self.program()
        elif c == "capture": self.capture()
        elif c == "status": self.control()
        elif c == "select":
            self.control((1 << 24) | self.args.bay)
            self.result["operationMeaning"] = "C simulator SELECT transaction; not microphone or digit-recognition evidence"
        elif c == "clear": self.control(2 << 24)
        elif c == "calibrate":
            self.control(3 << 24)
            self.result["operationMeaning"] = "one real-pixel calibration attempt armed; completion is reported by status and userEvent"
        elif c == "orientation":
            state = self.control((6 << 24) | self.args.profile)
            deadline = time.monotonic() + self.args.timeout
            while state["decoded"]["orientationProfile"] != self.args.profile:
                if time.monotonic() >= deadline:
                    raise RuntimeError("orientation command acknowledged but no frame boundary applied the requested profile")
                state = self.control()
            self.result["operationMeaning"] = "explicit debug orientation applied at a frame boundary; B/C coordinates retain contract v2"
        elif c == "speech":
            if self.args.arm:
                state = self.control(4 << 24)
                self.result["audioInputStatus"] = "DEFERRED_USER"
                self.result["audioReady"] = bool(state["decoded"]["status"]["audioReady"])
                self.result["operationMeaning"] = (
                    "reopen visual red-2 arming only; a real recognised red 2 is still required. "
                    "Microphone input remains deferred, audioReady=0 in this build, and this command creates no digit proposal")
            else:
                self.result["audioInputStatus"] = "DEFERRED_USER"
                raise Blocked("microphone recording/input is deferred by the user's latest instruction; use select --bay 1..6")
        elif c == "autodebug":
            self.replay(); self.rtl(); self.build(); self.program(); self.capture(); self.hardware()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quartus-bin")
    parser.add_argument("--modelsim-bin")
    parser.add_argument("--cable")
    parser.add_argument("--device")
    parser.add_argument("--timeout", type=int, default=300)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("doctor", "build", "program", "status", "clear", "autodebug"):
        commands.add_parser(name)
    test = commands.add_parser("test")
    test.add_argument("--only", nargs="+", help="run the named RTL benches when narrowing a regression")
    group = test.add_mutually_exclusive_group(required=True)
    for name in ("rtl", "replay", "hardware"):
        group.add_argument("--" + name, action="store_true")
    capture = commands.add_parser("capture")
    group = capture.add_mutually_exclusive_group()
    group.add_argument("--fresh", action="store_true")
    group.add_argument("--held", action="store_true")
    select = commands.add_parser("select")
    select.add_argument("--bay", type=int, choices=range(1, 7), required=True)
    commands.add_parser("calibrate").add_argument("--arm", action="store_true", required=True)
    commands.add_parser("orientation").add_argument("--profile", type=int, choices=range(4), required=True)
    speech = commands.add_parser("speech")
    group = speech.add_mutually_exclusive_group(required=True)
    group.add_argument("--arm", action="store_true")
    group.add_argument("--record", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    runner = Runner(args)
    code = 0
    try:
        runner.execute()
        runner.result["status"] = "PASS"
    except Blocked as exc:
        runner.result.update(status="BLOCKED", reason=str(exc)); code = 2
    except (OSError, RuntimeError, ValueError, ImportError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        runner.result.update(status="FAIL", reason=str(exc)); code = 1
    for testResult in runner.result.get("rtlTests", []):
        if testResult["status"] == "RUNNING":
            testResult.update(status="FAIL", reason=runner.result.get("reason", "test did not complete"))
    runner.result["exitCode"] = code
    runner.result["finishedUtc"] = datetime.now(timezone.utc).isoformat()
    (runner.out / "result.json").write_text(json.dumps(runner.result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(runner.result, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
