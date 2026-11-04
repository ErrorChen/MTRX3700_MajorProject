#!/usr/bin/env python3
"""ECHO-7 integrated build, camera diagnostics and regression runner.

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
import locale
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
    if os.name == "nt":
        for base in (Path("C:/intelFPGA_lite"), Path("C:/altera")):
            if base.is_dir():
                roots.extend(p / "quartus" for p in base.iterdir() if p.is_dir())
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
    """Discover the explicit source closure and simple build identifier.

    File names and the latest source modification time reject an obviously
    stale build without maintaining per-file hash manifests. Clean staging
    and a new output directory prevent reusing an earlier SOF as this build.
    """
    project = ROOT / "quartus"
    qsf = project / "PartBDebug.qsf"
    files = {qsf, project / "PartBDebug.qpf", ROOT / "rtl/common/memberBBuildId.svh"}
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
        if path in seen:
            continue
        seen.add(path)
        if not path.is_file():
            raise RuntimeError(f"project dependency is missing: {path}")
        if path.suffix.lower() in (".sv", ".svh", ".v", ".vh", ".sdc", ".qip"):
            source = path.read_text(encoding="utf-8", errors="replace")
            includes = re.findall(r'`include\s+"([^"]+)"', source)
            includes += re.findall(r'^\s*source\s+["{]?([^"}\s]+)', source, re.M)
            for include in includes:
                candidates = [path.parent / include, *(folder / include for folder in searchPaths)]
                found = next((p.resolve() for p in candidates if p.is_file()), None)
                if found is None:
                    raise RuntimeError(f"unresolved source include {include} in {path}")
                files.add(found); pending.append(found)
    header = (ROOT / "rtl/common/memberBBuildId.svh").read_text(encoding="utf-8")
    buildId = re.search(r"MEMBER_B_BUILD_ID\s+32'h([0-9a-fA-F]+)", header)
    if not buildId:
        raise RuntimeError("missing simple build identifier in memberBBuildId.svh")
    return {"buildId": int(buildId.group(1), 16), "top": "echo7IntegratedTop",
            "latestModifiedNs": max(p.stat().st_mtime_ns for p in files),
            "files": [p.relative_to(ROOT).as_posix() for p in sorted(files)]}


def stageBuildSources(identity, destination):
    """Copy the explicit dependencies into a new tree with no old SOF/database."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    for relative in identity["files"]:
        source = (ROOT / relative).resolve()
        target = (destination / relative).resolve()
        if not source.is_relative_to(ROOT.resolve()) or not target.is_relative_to(destination):
            raise RuntimeError(f"build dependency escapes its source tree: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        if source.read_bytes() != target.read_bytes():
            raise RuntimeError(f"source changed while staging build: {relative}")
    return destination / "quartus"


def verifiedBuild(sofPath=None):
    """Return this project's successful fresh build; reject another SOF path."""
    record = WORK / "last_build.json"
    if not record.is_file():
        raise Blocked("no current successful build record; run build first")
    build = json.loads(record.read_text(encoding="utf-8"))
    current = sourceIdentity()
    sof = Path(build["sof"]["path"]).resolve()
    if sofPath is not None and Path(sofPath).resolve() != sof:
        raise RuntimeError("--sof must identify the SOF produced by the recorded current build")
    if build.get("status") != "PASS" or build.get("source") != current:
        raise RuntimeError("sources differ from the current successful integrated build; rebuild first")
    if not sof.is_file() or sof.stat().st_size != build["sof"].get("bytes") or \
            sof.stat().st_mtime_ns != build["sof"].get("modifiedNs"):
        raise RuntimeError("the current build SOF is missing or changed")
    return build, sof


def quartusEnvironment(quartusBin, inherited=None):
    """Pin a child process and its Qsys descendants to one installed release.

    The user's global environment is never changed. In particular, selecting
    an 18.1 executable must not leave QUARTUS_ROOTDIR pointing at 20.1 or let a
    descendant find the other release through PATH.
    """
    environment = dict(os.environ if inherited is None else inherited)
    quartusBin = Path(quartusBin).resolve()
    quartusRoot = quartusBin.parent
    pinned = {"QUARTUS_ROOTDIR": str(quartusRoot),
              "QUARTUS_ROOTDIR_OVERRIDE": str(quartusRoot),
              "QSYS_ROOTDIR": str(quartusRoot / "sopc_builder/bin"),
              "SOPC_KIT_NIOS2": str(quartusRoot.parent / "nios2eds")}
    oldPath = next((value for key, value in environment.items() if key.upper() == "PATH"), "")
    for key in list(environment):
        if key.upper() in {*pinned, "PATH"}:
            del environment[key]
    preferred = [quartusBin, quartusRoot / "bin", quartusRoot / "sopc_builder/bin"]
    retained = []
    for item in oldPath.split(os.pathsep):
        parts = item.replace("\\", "/").lower().strip('"').split("/")
        if item and "quartus" not in parts and "nios2eds" not in parts:
            retained.append(item)
    environment.update(pinned)
    environment["PATH"] = os.pathsep.join([*(str(path) for path in preferred), *retained])
    return environment


def collectQuartusWarnings(output):
    """Keep both numbered compiler warnings and unnumbered vendor IP warnings.

    Quartus 18.1 PLL elaboration emits ``Warning: RST port ...`` without a
    message number. These still require review and must survive in the JSON.
    """
    return [line.strip() for line in output.splitlines()
            if re.match(r"\s*(?:Critical\s+)?Warning\s*(?:\(\d+\)|:)", line)]


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


def checkSynchroniserReports(folder, timing):
    """Bind explicit two-stage chain coverage to each analysed fitted corner.

    A reported MTBF headline is deliberately not an acceptance criterion.
    Source/SOF identity and setup/hold checks are separate build gates.
    """
    from synchronisers import validateSynchronisers
    if timing.get("analysisStage") != "POST_FIT":
        raise RuntimeError("synchroniser build coverage requires post-fit reports")
    corners = sorted({row["corner"] for row in timing.get("checks", [])})
    if not corners:
        raise RuntimeError("no fitted corners supplied for synchroniser coverage")
    records = []
    for corner in corners:
        reportPath = Path(folder) / f"synchronisers_{corner}.txt"
        coverage = validateSynchronisers(reportPath.read_text(encoding="utf-8", errors="replace"))
        records.append({"corner": corner, "report": str(reportPath),
                        "expectedChainCount": coverage["expectedChainCount"],
                        "reportedChainCount": coverage["reportedChainCount"],
                        "coverageStatus": coverage["coverageStatus"], "mtbfAcceptance": "NOT_ASSESSED"})
        (Path(folder) / f"synchronisers_{corner}.json").write_text(
            json.dumps(coverage, indent=2) + "\n", encoding="utf-8", newline="\n")
        if coverage["coverageStatus"] != "PASS":
            raise RuntimeError(f"fitted synchroniser coverage failed for {corner}: {coverage['errors']}")
    return records


class Runner:
    def __init__(self, args):
        self.args = args
        base = WORK / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + args.command)
        self.out = base
        collision = 0
        # Windows wall-clock resolution may give consecutive calls the same
        # timestamp. Atomic creation prevents mixing two evidence directories.
        while True:
            try:
                self.out.mkdir(parents=True)
                break
            except FileExistsError:
                collision += 1
                self.out = base.with_name(base.name + f"_{collision:03d}")
        self.result = {"schema": "echo7-cli-v1", "command": args.command, "status": "RUNNING",
                       "startedUtc": datetime.now(timezone.utc).isoformat(), "inputSource": "NONE",
                       "outputDirectory": str(self.out), "python": sys.executable,
                       "steps": []}
        self.selectedTarget = None
        self.logCounts = {}
        self.quartusBin = None

    def run(self, label, args, cwd=ROOT, timeout=None, checked=True, env=None):
        command = [str(a) for a in args]
        if env is None and (Path(command[0]).stem.startswith("quartus_") or
                            Path(command[0]).stem == "jtagconfig"):
            env = quartusEnvironment(Path(command[0]).resolve().parent)
        occurrence = self.logCounts.get(label, 0)
        self.logCounts[label] = occurrence + 1
        logName = label if occurrence == 0 else f"{label}_{occurrence:04d}"
        logPath = self.out / (logName + ".log")
        started = time.monotonic()
        # External programs write directly to a persistent regular file. A
        # descendant may inherit stdout after its parent exits; using a pipe
        # would make communicate()/close() depend on that descendant's lifetime
        # and could lose all pre-timeout Quartus output. Closing our file handle
        # never waits for a child to close its independent inherited handle.
        logEncoding = locale.getpreferredencoding(False)
        timedOut = False
        treeStopped = None
        parentRunning = False
        with logPath.open("wb", buffering=0) as log:
            def note(message):
                log.write((message + "\n").encode(logEncoding, errors="replace"))
            note("COMMAND " + json.dumps(command))
            note("LOG_ENCODING " + logEncoding)
            outputOffset = log.tell()
            process = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                       shell=False, start_new_session=(os.name == "posix"), env=env)
            try:
                code = process.wait(timeout=timeout if timeout is not None else self.args.timeout)
            except subprocess.TimeoutExpired as exc:
                timedOut = True
                note("TIMEOUT " + str(exc))
                # Stop only this command's PID/tree. If OS permissions prevent
                # tree cleanup, report uncertainty rather than claiming that no
                # compiler remains. Both cleanup attempts have bounded waits.
                treeStopped = False
                if os.name == "nt":
                    try:
                        terminated = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                                    stdout=log, stderr=subprocess.STDOUT, timeout=5)
                        treeStopped = terminated.returncode == 0
                    except (OSError, subprocess.SubprocessError) as cleanupError:
                        note("TREE_CLEANUP " + str(cleanupError))
                else:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                        treeStopped = True
                    except OSError as cleanupError:
                        note("TREE_CLEANUP " + str(cleanupError))
                if not treeStopped:
                    warning = "owned process tree cleanup was not confirmed; descendants may remain"
                    self.result.setdefault("terminationWarnings", []).append(warning)
                    note("TERMINATION_WARNING " + warning)
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=2)
                except (OSError, subprocess.TimeoutExpired) as cleanupError:
                    warning = "owned parent termination was not confirmed: " + str(cleanupError)
                    self.result.setdefault("terminationWarnings", []).append(warning)
                    note("TERMINATION_WARNING " + warning)
                parentRunning = process.poll() is None
                code = 124
        # The log remains authoritative if a surviving descendant writes later.
        # This return value is explicitly a snapshot taken when the call ends.
        output = logPath.read_bytes()[outputOffset:].decode(logEncoding, errors="replace")
        # Match text-mode subprocess semantics for consumers of line-oriented
        # Quartus protocols. Windows tools emit CRLF even though this runner
        # deliberately retains their exact bytes in the authoritative log.
        # Without normalisation, a multiline regex ending in '$' sees the
        # residual CR and rejects a correctly returned BCTL header/word.
        output = output.replace("\r\n", "\n").replace("\r", "\n")
        self.result["steps"].append({"name": label, "command": command, "returncode": code,
                                     "level": self.result.get("level", "TOOLS"),
                                     "logEncoding": logEncoding, "timedOut": timedOut,
                                     "treeTerminationConfirmed": treeStopped,
                                     "ownedParentMayRemain": parentRunning,
                                     "elapsedSeconds": round(time.monotonic() - started, 3), "log": str(logPath)})
        if checked and code:
            raise RuntimeError(f"{label} exited {code}; see {logPath}")
        return code, output

    def qt(self, name):
        # Discover once. A missing companion tool is an error rather than a
        # reason to silently switch to a different installed Quartus release.
        if self.quartusBin is None:
            self.quartusBin = Path(discover("quartus_sh", getattr(self.args, "quartus_bin", None))).parent
        return discover(name, self.quartusBin)

    def doctor(self):
        self.result["level"] = "DISCOVERY"
        self.result["tools"] = {}
        for name in ("quartus_sh", "quartus_sta", "quartus_pgm", "quartus_stp", "jtagconfig", "vsim", "vlog", "vlib"):
            try:
                path = (discover(name, self.args.modelsim_bin) if name in ("vsim", "vlog", "vlib") else self.qt(name))
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
            "README.md", "VERSION_README.md", "OWNERS.md", "docs/Major_Project_Brief_2026.pdf",
            "tests/fixtures/camera/manifest.json",
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
        captureArgs=[]
        caseArgs=[]
        if getattr(self.args,"vector_case",None):
            if getattr(self.args,"capture_result",None):
                raise RuntimeError("--vector-case and --capture-result select different evidence sources; choose one")
            if any(test["name"] not in {"projectiveMarkerReader_tb","projectiveBypass_tb"} for test in config["tests"]):
                raise RuntimeError("--vector-case requires --only projectiveMarkerReader_tb projectiveBypass_tb (or a subset)")
            caseArgs=[part for name in self.args.vector_case for part in ("--case",name)]
            self.result["selectedVectorCases"]=self.args.vector_case
        if getattr(self.args,"capture_result",None):
            if any(test["name"] not in {"projectiveMarkerReader_tb","projectiveBypass_tb"} for test in config["tests"]):
                raise RuntimeError("--capture-result requires --only projectiveMarkerReader_tb projectiveBypass_tb (or a subset)")
            captureArgs=["--capture-result",self.args.capture_result.resolve()]
            self.result["recordedCaptureInput"] = {"path": str(self.args.capture_result.resolve()),
                                                    "sha256": digest(self.args.capture_result)}
        self.result["rtlTests"] = []
        # Attribute the complete suite to one source snapshot. Per-test checks
        # alone miss an early bench's source changing while later benches run.
        suiteHashes = {path: digest(ROOT / path) for test in config["tests"] for path in test["sources"]}
        self.result["rtlSuiteSourceCount"] = len(suiteHashes)
        vectors = self.out / "vectors"
        self.run("candidate_vectors", [sys.executable, ROOT / "tools/lib/candidates_reclaimed_model.py",
                                    "--write-vectors", vectors])
        if any(test["name"] in ("boundedCandidatesActive_tb", "boundedCandidatesCapacity15_tb") for test in config["tests"]):
            self.run("capacity_vectors", [sys.executable, HERE / "export_capacity_vectors.py", "--out", vectors])
        if any(test["name"] == "boundedCandidatesCompleted16_tb" for test in config["tests"]):
            self.run("completed16_vectors", [sys.executable, HERE / "export_completed16_vectors.py", "--output-dir", vectors])
        if any(test["name"] == "mainColourSupportReader_tb" for test in config["tests"]):
            self.run("main_colour_vectors", [sys.executable, HERE / "export_main_colour_vectors.py", "--out", vectors])
        for name, exporter in (("calibrationPointMapper_tb", "export_calibration_mapper_vectors.py"),
                               ("calibrationGeometry_tb", "export_calibration_geometry_vectors.py"),
                               ("nativeAnchorSupport_tb", "export_native_anchor_support_vectors.py"),
                               ("perceptionCalibration_tb", "export_calibration_scene.py")):
            if any(test["name"] == name for test in config["tests"]):
                self.run(name + "_vectors", [sys.executable, HERE / exporter, "--out", vectors])
        if (HERE / "export_vision_vectors.py").exists():
            self.run("vision_vectors", [sys.executable, HERE / "export_vision_vectors.py", "--out", vectors])
        if any("memberBVgaContour.sv" in path for test in config["tests"] for path in test["sources"]):
            self.run("contour_vectors", [sys.executable, HERE / "export_contour_vectors.py", "--out", vectors])
        if any(Path(path).name in ("projectiveMarkerReader.sv", "nativeAnchorReader.sv", "mainColourSupportReader.sv")
               for test in config["tests"] for path in test["sources"]):
            self.run("projective_vectors", [sys.executable, HERE / "export_projective_vectors.py", "--out", vectors,*captureArgs,*caseArgs])
            if any(test['name']=='projectiveBypass_tb' for test in config['tests']):
                self.run("bypass_vectors", [sys.executable, HERE / "export_projective_vectors.py", "--out", vectors / "bypass", "--bypass-perspective",*captureArgs,*caseArgs])
            self.result["inputSource"] = ("RECORDED_CAMERA_RTL_REPLAY" if captureArgs else
                                          "MIXED_SYNTHETIC_AND_RECORDED_CAMERA_RTL_REPLAY")
        # The current reader can reproduce reader5 by disabling only the new
        # owner-centre predicate. Bind that choice to the exported source
        # profile, rather than silently running historical pixels as reader6.
        # Earlier readers changed more than this predicate and need their
        # corresponding historical RTL; do not claim equivalence here.
        projectiveParameters = {}
        projectiveManifest = vectors / "projective_manifest.json"
        if projectiveManifest.exists():
            vectorProfile = json.loads(projectiveManifest.read_text(encoding="utf-8"))
            readerAlgorithm = vectorProfile["readerAlgorithm"]
            if readerAlgorithm not in (5, 6, 7, 8, 9) or vectorProfile["candidatePoolMode"] != "SHARED":
                raise RuntimeError("current reader RTL replay supports shared-pool reader5/6/7/8/9 only; use matching historical RTL for older captures")
            projectiveParameters = {"ENFORCE_OWNER_BOUNDS": int(readerAlgorithm >= 6),
                                    "ENFORCE_MAIN_COMPONENT": int(readerAlgorithm >= 7),
                                    "EMIT_CALIBRATION_QUADS": int(readerAlgorithm >= 8),
                                    "ENABLE_THIN_ANCHOR_SUPPORT": int(readerAlgorithm >= 9)}
            self.result["projectiveReplayProfile"] = {
                "readerAlgorithm": readerAlgorithm,
                "colourAlgorithm": vectorProfile["colourAlgorithm"],
                "vectorManifest": str(projectiveManifest),
                "simulationParameters": projectiveParameters}
        for test in config["tests"]:
            name = test["name"]
            folder = self.out / name
            folder.mkdir()
            library = folder / "simlib"
            self.run(name + "_vlib", [binDir / ("vlib" + suffix), library], cwd=folder)
            sources = [ROOT / p for p in test["sources"]]
            sourceHashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
            testResult = {"name": name, "status": "RUNNING",
                          "inputSource": ("RECORDED_CAMERA_RTL_REPLAY" if captureArgs else
                                          test.get("inputSource", "SYNTHETIC_RTL_VECTORS")),
                          "simulationModelDefines": test.get("defines", [])}
            self.result["rtlTests"].append(testResult)
            # The course FrameGrab names its portable RAM/probe behavioural
            # branch VERILATOR; use that existing branch under ModelSim too.
            # This is RTL simulation of the wrapper, not Intel IP/JTAG validation.
            defines = ["+define+" + d for d in test.get("defines", [])]
            self.run(name + "_compile", [binDir / ("vlog" + suffix), "-sv", *defines, "-work", library, *sources], cwd=folder)
            plusargs = [value.replace("{vectors}", vectors.as_posix()).replace("{root}", ROOT.as_posix())
                        for value in test.get("plusargs", [])]
            simulationParameters = (projectiveParameters if
                test.get("top", name) == "projectiveMarkerReader_tb" else {})
            testResult["simulationParameters"] = simulationParameters
            parameterArgs = [f"-g{key}={value}" for key, value in simulationParameters.items()]
            command = [vsim, "-c", "-onfinish", "exit", "-lib", library, test.get("top", name),
                       *parameterArgs, "+VECTORS=" + vectors.as_posix(), "+VECTOR_DIR=" + vectors.as_posix(), *plusargs, "-do",
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
        if not re.search(r"TOP_LEVEL_ENTITY\s+echo7IntegratedTop\b", text) or "5CSEMA5F31C6" not in text:
            raise RuntimeError("PartBDebug must use echo7IntegratedTop and 5CSEMA5F31C6")
        identity = sourceIdentity()
        self.result["source"] = identity
        project = stageBuildSources(identity, self.out / "source")
        self.result["buildProject"] = str(project)
        toolPaths = {name: self.qt(name) for name in ("quartus_sh", "quartus_map", "quartus_fit", "quartus_asm", "quartus_sta")}
        _, version = self.run("quartus_version", [toolPaths["quartus_sh"], "--version"])
        environment = quartusEnvironment(self.quartusBin)
        self.result["toolchain"] = {"tools": toolPaths, "versionOutput": version.strip(),
            "environment": {name: environment[name] for name in
                ("QUARTUS_ROOTDIR", "QUARTUS_ROOTDIR_OVERRIDE", "QSYS_ROOTDIR", "SOPC_KIT_NIOS2")}}
        # Persist RUNNING provenance before a potentially long compile, so a
        # killed runner still leaves the exact private project and tool release.
        (self.out / "result.json").write_text(json.dumps(self.result, indent=2) + "\n", encoding="utf-8")
        sof = project / "output_files/PartBDebug.sof"
        compileCode, compileOutput = self.run("compile", [toolPaths["quartus_sh"], "--flow", "compile", "PartBDebug"],
            project, timeout=max(self.args.timeout, 3600), checked=False, env=environment)
        self.result["warnings"] = collectQuartusWarnings(compileOutput)
        if compileCode:
            raise RuntimeError(f"compile exited {compileCode}; see {self.out / 'compile.log'}")
        if any("Critical Warning" in line for line in self.result["warnings"]):
            raise RuntimeError("critical Quartus warnings require correction/review before this build can be programmed")
        if sourceIdentity() != identity:
            raise RuntimeError("sources changed during compilation; rebuild the current source")
        if not sof.exists():
            raise RuntimeError("compile did not produce a fresh PartBDebug.sof")
        self.run("timing_gate", [self.qt("quartus_sta"), "-t", ROOT / "tools/tcl/timing_check.tcl", "PartBDebug", self.out / "timing.json"], project)
        timing = json.loads((self.out / "timing.json").read_text())
        if timing.get("analysisStage") != "POST_FIT":
            raise RuntimeError("build timing acceptance requires post-fit analysis, not a post-map constraint audit")
        timing["reportGate"] = checkTimingReports(
            (project / "output_files/PartBDebug.sta.summary").read_text(),
            (project / "output_files/PartBDebug.sta.rpt").read_text())
        self.result["timing"] = timing
        if timing.get("status") != "PASS":
            raise RuntimeError("timing checks did not pass")
        self.result["synchroniserCoverage"] = checkSynchroniserReports(self.out, timing)
        self.result["sof"] = {"path": str(sof.resolve()), "bytes": sof.stat().st_size,
                              "modifiedNs": sof.stat().st_mtime_ns}
        self.result["fitterSummary"] = (project / "output_files/PartBDebug.fit.summary").read_text()
        self.result["status"] = "PASS"
        (WORK / "last_build.json").write_text(json.dumps(self.result, indent=2))

    def control(self, command=0, operation="control"):
        from debug_decode import schemaLayout
        # Reading the loaded design or sending an interface stimulus verifies
        # board communication. Camera recognition is a separate capture/test.
        self.result.setdefault("level", "PROGRAMMED")
        target = self.target()
        code, output = self.run("bctl", [self.qt("quartus_stp"), "-t", ROOT / "tools/tcl/jtag_control.tcl", operation,
                                      target["cable"], target["device"], str(command)], checked=False)
        if operation == "calibration-check":
            trace = re.findall(r"^ECHO7_CAL_TRACE\t(\d+)\t(\d+)\t(\d+)\t(\d+)\t(\d+)$", output, re.M)
            self.result["calibrationTrace"] = [dict(zip(("boardTimeUs", "frameId", "configVersion", "statusUpper", "sampleWord"), map(int, row))) for row in trace]
            busyMatch = re.search(r"^ECHO7_BUSY_ACTION\t([01]{32})$", output, re.M)
            self.result["busyActionMeta"] = int(busyMatch.group(1), 2) if busyMatch else None
        actionMatch = re.search(r"^ECHO7_ACTION\t(\d+)\t([01]{32})$", output, re.M)
        if command and actionMatch:
            actionMeta = int(actionMatch.group(2), 2)
            reasonCode = (actionMeta >> 12) & 3
            actionLayout = schemaLayout(actionMeta >> 24)
            if int(actionMatch.group(1)) != (command >> 24) or \
                    ((actionMeta >> 16) & 255) != actionLayout["contractVersion"] or (actionMeta & 255) != actionLayout["wordCount"]:
                raise RuntimeError("BCTL action acknowledgement does not match the requested opcode/schema")
            if (actionMeta >> 24) >= 3 and bool(actionMeta & (1 << 14)) != (reasonCode != 0):
                raise RuntimeError("BCTL action error flag and rejection reason disagree")
            self.result["commandAcceptance"] = {
                "opcode": int(actionMatch.group(1)), "transportAcknowledged": True,
                "accepted": not bool(actionMeta & (1 << 14)),
                "reason": {0: "ACCEPTED", 1: "INVALID_COMMAND", 2: "BUSY_OR_DISABLED"}.get(reasonCode, "RESERVED"),
                "completed": False,
                "meaning": "Action acceptance only; interaction completion requires its terminal event and configuration version."}
        if code and (code != 3 or not actionMatch):
            raise RuntimeError(f"BCTL transport failed with exit {code}; see bctl log")
        match = re.search(r"^ECHO7_HEADER\t([01]{96})$", output, re.M)
        if not match:
            raise RuntimeError("BCTL did not return its versioned status header")
        bits = match.group(1)
        magic, buildId, meta = (int(bits[i:i+32], 2) for i in (0, 32, 64))
        debugSchema = meta >> 24
        layout = schemaLayout(debugSchema)
        if magic != 0x42444247 or (meta >> 16) & 255 != layout["contractVersion"] or meta & 255 != layout["wordCount"]:
            raise RuntimeError(f"unsupported BCTL header magic={magic:08x}, meta={meta:08x}")
        words = re.findall(r"^ECHO7_WORD\t(\d+)\t([01]{32})$", output, re.M)
        if [int(n) for n, _ in words] != list(range(schemaLayout(debugSchema)["wordCount"])):
            raise RuntimeError("BCTL frozen word sequence is incomplete or reordered")
        status = {"magic": hex(magic), "schema": debugSchema, "contract": layout["contractVersion"], "buildId": buildId,
                  "words": [int(word, 2) for _, word in words]}
        from debug_decode import decodeWords
        status["decoded"] = decodeWords(status["words"])
        if status["decoded"]["debugSchemaVersion"] != debugSchema:
            raise RuntimeError("BCTL header and frozen status have different schema versions")
        if status["decoded"]["buildId"] != buildId:
            raise RuntimeError("BCTL header and frozen status have different build IDs")
        self.result["boardStatus"] = status
        self.result["inputSource"] = "JTAG_INTERFACE_STIMULUS" if command else "LIVE_JTAG_STATUS"
        if code == 3 or (command and actionMatch and not self.result["commandAcceptance"]["accepted"]):
            raise RuntimeError("BCTL action rejected: " + self.result["commandAcceptance"]["reason"])
        if command and debugSchema >= 3 and not actionMatch:
            raise RuntimeError("schema3 command has no action-level acceptance record")
        if operation == "calibration-check":
            from calibration_measurement import evaluateCalibration
            self.result["level"] = "CAMERA_HW"
            self.result["inputSource"] = "LIVE_CAMERA_RAW_RGB_WITH_JTAG_REARM"
            assessment = evaluateCalibration(self.result["calibrationTrace"], status["decoded"], self.result["busyActionMeta"])
            self.result["calibrationAssessment"] = assessment
            self.result["commandAcceptance"]["completed"] = bool(
                assessment["configurationCommitted"] and assessment["validSampleFrames"] == 8)
            if assessment["status"] != "PASS":
                raise RuntimeError("real calibration acceptance failed: " + assessment["reason"])
        return status

    def query(self, opcode, selector=None):
        """Run one real BCTL session, including recovery of abandoned replies."""
        from query_transport import parseQueryStream
        self.result.update(level="PROGRAMMED", inputSource="LIVE_FPGA_QUERY_RESULT",
                           transport="ONE_BOUNDED_JTAG_QUERY_SESSION")
        target = self.target()
        command = opcode << 24
        if selector is not None:
            command |= (selector[0] << 4) | selector[1]
        code, output = self.run("bctl_query", [self.qt("quartus_stp"), "-t", ROOT / "tools/tcl/jtag_control.tcl",
            "query-stream", target["cable"], target["device"], str(command),
            str(min(900, max(1, int(self.args.timeout))))], checked=False)
        self.result["queryTransportExitCode"] = code
        if code:
            self.result["queryRecoveryCommand"] = "python tools/echo7.py markers --drain"
            raise RuntimeError(f"query transport failed with exit {code}; retained packets are in bctl_query.log; use markers --drain")
        transaction = parseQueryStream(output, opcode, selector)
        self.result["queryTransaction"] = transaction
        self.result["operationMeaning"] = ("Drained abandoned FPGA query replies; tracking request unchanged."
            if opcode == 0 else "Complete FPGA LIST/GET reply; tracking request unchanged. Original capture timestamps must be rechecked before use.")
        return transaction

    def program(self):
        self.result["level"] = "PROGRAMMED"
        buildPath = WORK / "last_build.json"
        build, sof = verifiedBuild(getattr(self.args, "sof", None))
        target = self.target(programming=True)
        self.run("program", [self.qt("quartus_pgm"), "-c", target["cable"], "-m", "JTAG", "-o", f"p;{sof}@{target['index']}"])
        self.result["build"] = buildPath.as_posix()
        STATE.write_text(json.dumps({"programmedTarget": target, "source": build["source"], "sof": build["sof"],
                                     "programmedAtUtc": datetime.now(timezone.utc).isoformat()}, indent=2))
        status = self.control()
        if status["buildId"] != build["source"]["buildId"]:
            raise RuntimeError("programmed device buildId differs from the current build")
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
        from capture_transaction import validateSnapshotTransaction, validateFrameProgress
        metadataPath = self.out / "capture/snapshot_metadata.json"
        metadata = json.loads(metadataPath.read_text(encoding="utf-8"))
        transaction = validateSnapshotTransaction(metadata, target, held, dump.stat().st_size)
        self.result["snapshotTransaction"] = metadata
        self.result["snapshotTransactionValidation"] = transaction
        try:
            decoded = module.decode(dump.read_bytes())
        except module.DumpError as exc:
            # Keep the independent decoder failure inside the CLI's structured
            # nonzero-result path, even if the transport process returned zero.
            raise RuntimeError("GRAB decode/CRC failed: " + str(exc)) from exc
        if decoded["offset"] != 0 or decoded["bytes"] != dump.stat().st_size:
            raise RuntimeError("snapshot has prefix/trailing bytes; exact GRAB framing is required")
        self.result["snapshot"] = {k: decoded[k] for k in ("width", "height", "n_results", "crc", "results")}
        self.result["dumpSha256"] = digest(dump)
        from debug_decode import checkGrabSchema, decodeGrabWords
        checkGrabSchema(decoded["results"])
        buildPath = WORK / "last_build.json"
        if not buildPath.exists():
            raise Blocked("B GRAB needs a successful build manifest to verify its source buildId")
        expectedBuildId = json.loads(buildPath.read_text())["source"]["buildId"]
        self.result["packetType"] = "MEMBER_B"
        self.result["recognition"] = decodeGrabWords(decoded["results"], expectedBuildId)
        self.result["frameId"] = self.result["recognition"]["frameId"]
        self.result["fresh"] = transaction["fresh"]
        self.assessCapturedPixels()
        contextPath = STATE
        context = json.loads(contextPath.read_text()) if contextPath.exists() else {}
        self.result["programmingContext"] = str(contextPath) if context else None
        epoch = context.get("startedUtc", context.get("programmedAtUtc", "UNRECORDED"))
        if not held:
            historyPath = WORK / "last_capture.json"
            previous = json.loads(historyPath.read_text()) if historyPath.exists() else None
            self.result["nativeFrameComparison"] = validateFrameProgress(
                self.result["frameId"], previous, target, epoch, transaction["hostObservedMs"])
            historyPath.write_text(json.dumps({"target": target, "frameId": self.result["frameId"],
                                               "programmingEpoch": epoch, "dumpSha256": digest(dump),
                                               "hostObservedMs": transaction["hostObservedMs"],
                                               "snapshotCount": transaction["snapshotCount"]}))

    def assessCapturedPixels(self):
        """Classify only processed captures after the packet/frame/CRC gates.

        Raw mode still exports and validates the actual RGB capture. An empty
        marker list must never yield a vacuous glyph-agreement PASS or be called
        recognition success. Live request/display bits can differ from this
        frame-bound mode during transitions, so only rawCameraMode decides here.
        """
        recognition = self.result["recognition"]
        if recognition.get("rawCameraMode", False):
            assessment = {"status": "NOT_APPLICABLE_RAW_CAMERA_MODE",
                          "level": "CAMERA_HW_CAPTURE_ONLY", "comparedCandidateCount": 0,
                          "frameId": recognition["frameId"],
                          "reason": "Algorithms were disabled for this captured frame; RGB/CRC/schema/build/frame checks remain applicable."}
            self.result["glyphAgreement"] = assessment
            self.result["recognitionAssessment"] = dict(assessment)
            self.result["captureMeaning"] = "Verified raw RGB camera snapshot only; not recognition or target acceptance."
            return
        from debug_decode import compareMarkerPixels
        comparison = compareMarkerPixels(self.out / "capture/frame.png", recognition, self.out / "glyph_check")
        self.result["glyphAgreement"] = comparison
        script = "projective_reference.py" if recognition["readerAlgorithm"] in (1, 2, 3, 4, 5, 6, 7, 8, 9) else "vision_reference.py"
        profileArgs = (["--white-min", str(recognition["whiteMinimum"]), "--max-spread", str(recognition["whiteMaxSpread"]),
                        "--colour-algorithm", str(recognition["colourAlgorithm"]),
                        "--reader-algorithm", str(recognition["readerAlgorithm"]),
                        "--active-capacity", str(recognition["activeCandidateCapacity"]),
                        "--output-capacity", str(recognition["outputCandidateCapacity"])]
                       if recognition["readerAlgorithm"] in (1, 2, 3, 4, 5, 6, 7, 8, 9) else ["--cleanup"])
        if recognition["readerAlgorithm"] >= 5:
            profileArgs.append("--shared-pool" if recognition.get("sharedCandidatePool", False) else "--split-pool")
        if recognition.get('bypassPerspective',False):profileArgs.append('--bypass-perspective')
        self.run("pixel_reference", [sys.executable, HERE / script, self.out / "capture/frame.png",
                 "--orientation", str(recognition["orientationProfile"]),
                 "--red-min", str(recognition["redMinimum"]),
                 "--blue-min", str(recognition["blueMinimum"]), *profileArgs,
                 "--source", "RECORDED_CAMERA", "--out", self.out / "pixel_reference"])
        if comparison["status"] != "PASS":
            raise RuntimeError("captured glyph pixels disagree with the FPGA same-frame marker decisions")

    def hardware(self):
        # Default/autodebug acceptance uses the same finite, loss-preserving
        # assessor as formal multi-trial runs. Do not wait for success-only
        # frames or silently omit failed observations from the denominator.
        from trial_stream import measureLiveTrials
        measureLiveTrials(self, getattr(self.args, "trials", 0) or 1, sourceIdentity()["buildId"])

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
            self.control((1 << 24) | (1 << 4) | self.args.bay)
            self.result["operationMeaning"] = "C simulator SELECT transaction; not microphone or digit-recognition evidence"
        elif c in ("track", "locate"):
            from query_transport import markerSelector
            selector = markerSelector(self.args.type, self.args.digit)
            if c == "locate":
                self.query(9, selector)
            else:
                self.control((1 << 24) | (selector[0] << 4) | selector[1])
                self.result["operationMeaning"] = "Typed C simulator SELECT; locking still requires three unique real frame observations."
        elif c == "markers":
            self.query(0 if self.args.drain else 8)
        elif c == "clear": self.control(2 << 24)
        elif c == "calibrate":
            self.control(3 << 24, operation="calibration-check" if getattr(self.args, "verify_busy", False) else "control")
            self.result["operationMeaning"] = (
                "Real-red1 calibration completion assessed from eight valid samples and one configuration increment; see calibrationAssessment for the separately measured timing target."
                if getattr(self.args, "verify_busy", False) else
                "real-red1 workflow rearm accepted; not yet started or completed. Read interactionId, terminal userEvent and configVersion via status.")
        elif c == "orientation":
            state = self.control((6 << 24) | self.args.profile)
            deadline = time.monotonic() + self.args.timeout
            while state["decoded"]["orientationProfile"] != self.args.profile:
                if time.monotonic() >= deadline:
                    raise RuntimeError("orientation command acknowledged but no frame boundary applied the requested profile")
                state = self.control()
            self.result["operationMeaning"] = "explicit debug orientation applied at a frame boundary; B/C coordinates remain upright240x320"
        elif c == "speech":
            raise Blocked("speech is unsupported; select a bay with physical SW0-SW5")
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
    for name in ("doctor", "build", "status", "clear"):
        commands.add_parser(name)
    commands.add_parser("program").add_argument("--sof", type=Path,
        help="explicit SOF from this project's latest successful build (defaults to its recorded path)")
    autodebug = commands.add_parser("autodebug")
    test = commands.add_parser("test")
    # Both entry points use the same loss-preserving assessor. A truth file
    # changes host scoring only; it never enters the build or FPGA commands.
    for command in (test, autodebug):
        command.add_argument("--trials", type=int, choices=(1, 2, 3), default=0,
                             help="hardware only: retain all observations in 30-sample trials, including failures (default: one trial)")
        command.add_argument("--truth-regions", type=Path,
                             help="Test-only printed-digit regions for a fixed photographed scene; never supplied to FPGA; requires --trials")
    test.add_argument("--only", nargs="+", help="run the named RTL benches when narrowing a regression")
    test.add_argument("--capture-result",type=Path,help="R7: replay one verified camera result/profile through reader/anchor RTL")
    test.add_argument("--vector-case",action="append",help="named current-algorithm reader regression; repeat for multiple cases (historical capture profile uses --capture-result)")
    group = test.add_mutually_exclusive_group(required=True)
    for name in ("rtl", "replay", "hardware"):
        group.add_argument("--" + name, action="store_true")
    capture = commands.add_parser("capture")
    group = capture.add_mutually_exclusive_group()
    group.add_argument("--fresh", action="store_true")
    group.add_argument("--held", action="store_true")
    select = commands.add_parser("select")
    select.add_argument("--bay", type=int, choices=range(1, 7), required=True)
    commands.add_parser("markers").add_argument("--drain", action="store_true",
        help="Recover abandoned query replies only, without issuing another LIST")
    for name in ("locate", "track"):
        typed = commands.add_parser(name)
        typed.add_argument("--type", choices=("bay", "function", "reference"), required=True)
        typed.add_argument("--digit", type=int,
            help="bay1..6 or function1/2; omit for the paired calibration reference BJ")
    calibration = commands.add_parser("calibrate")
    calibration.add_argument("--arm", action="store_true", required=True)
    calibration.add_argument("--verify-busy", action="store_true", help="trace real sampling and verify a second arm is rejected while busy")
    commands.add_parser("orientation").add_argument("--profile", type=int, choices=range(4), required=True)
    speech = commands.add_parser("speech")
    group = speech.add_mutually_exclusive_group(required=True)
    group.add_argument("--arm", action="store_true")
    group.add_argument("--record", action="store_true")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    hardwareCommand = args.command == "autodebug" or (args.command == "test" and args.hardware)
    if getattr(args, "trials", 0) and not hardwareCommand:
        parser.error("--trials requires test --hardware or autodebug")
    if getattr(args, "capture_result", None) and not args.rtl:
        parser.error("--capture-result requires test --rtl")
    if getattr(args, "vector_case", None) and not args.rtl:
        parser.error("--vector-case requires test --rtl")
    if getattr(args,"truth_regions",None) and (not hardwareCommand or not args.trials):
        parser.error("--truth-regions requires test --hardware --trials 1..3 or autodebug --trials 1..3")
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
