#!/usr/bin/env python3
"""Course R6: clean Verilator 5.050 module/system tests and a caught mutant.

This is a bounded course demonstration suite, not a replacement for echo7.py's
full ModelSim regression. Its system bench runs the production perceptionCore
on six alternating RGB565 frames with real row gaps and report backpressure.
Synthetic pixels do not constitute live CAMERA_HW or vehicle integration.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_VERSION = "5.050"
SUITE_NAMES = (
    "perceptionCoreContinuous_tb", "hsvColourGate_tb", "targetTracker_tb",
    "fixedSheetInteraction_tb", "colourSampler_tb",
)
ERROR_PATTERN = re.compile(r"%Error:|Assertion failed|\bFAIL(?:ED)?\b|\*\*\s+(?:Error|Fatal)")
MUTATION_BEFORE = "newReport.locked = nextCount == 3;"
MUTATION_AFTER = "newReport.locked = nextCount == 2;"


class EnvironmentBlocked(RuntimeError):
    """Required external tool or dependency is unavailable."""


def fileHash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selectTests(manifest):
    byName = {test["name"]: test for test in manifest["tests"]}
    return [byName[name] for name in SUITE_NAMES]


def exactVersion(output):
    return bool(re.match(r"\s*Verilator\s+5\.050\b", output))


def simulationPassed(record, output, passMarker):
    return not record["timedOut"] and record["returnCode"] == 0 and \
        passMarker in output and ERROR_PATTERN.search(output) is None


def mutantCaught(record, output):
    # A missing executable, compilation failure, generic crash or timeout is
    # never CAUGHT. Require the intended assertion from the existing good TB.
    return not record["timedOut"] and record["returnCode"] != 0 and \
        "three-frame lock" in output and ERROR_PATTERN.search(output) is not None


def makeMutant(sourcePath, destination):
    source = Path(sourcePath).read_text(encoding="utf-8")
    if source.count(MUTATION_BEFORE) != 1:
        raise RuntimeError("tracker mutation anchor changed; review the deliberate fault")
    Path(destination).write_text(source.replace(MUTATION_BEFORE, MUTATION_AFTER), encoding="utf-8")


def runProcess(arguments, cwd, logPath, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("the complete clean suite exceeded 300 seconds")
    started = time.monotonic()
    command = [str(value) for value in arguments]
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace",
                               start_new_session=os.name != "nt")
    timedOut = False
    try:
        output, _ = process.communicate(timeout=remaining)
    except subprocess.TimeoutExpired:
        timedOut = True
        # Stop only this runner's compiler/simulator process tree. In POSIX a
        # separate session prevents signalling another user's build process.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=5, check=False)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        output, _ = process.communicate(timeout=5)
    Path(logPath).write_text(output, encoding="utf-8")
    return {"arguments": command, "returnCode": process.returncode, "timedOut": timedOut,
            "elapsedSeconds": round(time.monotonic() - started, 6), "log": str(logPath)}, output


def prepareVectors(outputDir):
    """Generate only the existing system bench's two independent pixel oracles.

    Reuse the full suite's image generator, CCL model and projective classifier.
    No marker ID is assigned from a sheet cell or from candidate order.
    """
    from export_vision_vectors import cases, packCandidate
    from projective_reference import classifyProjective
    from vision_reference import pixelsOf, quantise565, recognise

    outputDir = Path(outputDir)
    outputDir.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (name, original, orientation) in enumerate(itertools.islice(cases(), 2)):
        image = quantise565(original)
        base = recognise(image, cleanup=True, redMin=48, blueMin=20, colourAlgorithm=2,
                         pruneUnusable=True, activeCapacity=15, capacity=16, sharedCapacity=16)
        if base["overflow"]:
            raise RuntimeError(f"system fixture candidate overflow: {name}")
        candidateWords, expectedWords, candidateColours = [0] * 16, [0x000f0001] * 16, [0] * 16
        blueOne = []
        for slot, candidate in enumerate(base["markers"]):
            fields = {key: candidate[key] for key in ("colour", "bbox", "area")}
            colour = fields["colour"]
            if slot >= 16:
                raise RuntimeError("system fixture exceeds shared total capacity16")
            candidateWords[slot] = packCandidate(fields)
            candidateColours[slot] = int(colour == "blue")
            marker = classifyProjective(image, fields, orientation=orientation, redMin=48, blueMin=20,
                                        colourAlgorithm=2, readerAlgorithm=5)
            digit = marker["digit"] if marker["accepted"] else 15
            expectedWords[slot] = (int(marker["accepted"]) << 24) | (digit << 16) | \
                                 (marker["quality"] << 8) | marker["reasonCode"]
            if colour == "blue" and marker["accepted"] and digit == 1:
                blueOne.append(fields["bbox"])
        if len(blueOne) != 1:
            raise RuntimeError("system oracle must independently recognise one blue 1")
        data = {
            "rgb565": "".join(f"{((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3):04x}\n"
                              for r, g, b in pixelsOf(image)),
            "candidates": "".join(f"{word:018x}\n" for word in candidateWords),
            "candidate_colours": "".join(f"{colour:x}\n" for colour in candidateColours),
            "expected": "".join(f"{word:08x}\n" for word in expectedWords),
        }
        paths = {}
        for suffix, text in data.items():
            path = outputDir / f"continuous_{index}_{suffix}.hex"
            path.write_text(text, encoding="ascii", newline="\n")
            paths[suffix] = {"file": path.name, "sha256": fileHash(path)}
        records.append({"name": name, "inputSource": "SYNTHETIC_PIXEL_COUNTERFACTUAL",
                        "blueOneBbox": blueOne[0], "poolLayout": "SHARED_TOTAL",
                        "candidateOrder": "MODEL_CANONICAL_GEOMETRY_NOT_RTL_RETIREMENT_ORDER", "files": paths})
    if len(records) != 2 or records[0]["blueOneBbox"] == records[1]["blueOneBbox"]:
        raise RuntimeError("system fixtures do not exercise pixel-dependent target movement")
    (outputDir / "fixtures.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verilator", default="verilator", help="Verilator 5.050 executable; no installation is attempted")
    parser.add_argument("--jobs", type=int, default=2, choices=range(1, 17))
    parser.add_argument("--out", type=Path, help="new result directory; existing directories are never reused/deleted")
    parser.add_argument("--prepare-vectors", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if os.name == "nt" and os.environ.get("VERILATOR_ROOT"):
        # The native makefile is evaluated by Git's POSIX shell. Backslashes
        # in the inherited Windows path otherwise become shell escapes.
        os.environ["VERILATOR_ROOT"] = Path(os.environ["VERILATOR_ROOT"]).as_posix()
    if args.prepare_vectors:
        prepareVectors(args.prepare_vectors)
        return 0
    started = time.monotonic()
    deadline = started + 300.0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    outputDir = (args.out or ROOT / "build/member_b" / (stamp + "_verilator_course")).resolve()
    outputDir.mkdir(parents=True, exist_ok=False)
    result = {"schema": "echo7-verilator-course-v1", "status": "RUNNING", "level": "RTL_SIM",
              "requiredVersion": REQUIRED_VERSION, "maximumSeconds": 300, "cleanBuild": True,
              "scope": "Member B modules and perceptionCore pixel-to-report system; no chassis", "tests": [], "commands": []}
    exitCode = 1
    try:
        verilator = shutil.which(args.verilator)
        missing = [name for name in ("make",) if not shutil.which(name)]
        compiler = shutil.which(os.environ.get("CXX", "g++")) or shutil.which("clang++")
        if not verilator or not compiler or missing:
            raise EnvironmentBlocked("require Verilator 5.050, make and a C++ compiler in this shell; "
                                     f"verilator={verilator}, compiler={compiler}, missing={missing}")
        record, version = runProcess([verilator, "--version"], ROOT, outputDir / "version.log", deadline)
        result["commands"].append(record)
        result["toolchain"] = {"verilator": verilator, "version": version.strip(), "compiler": compiler}
        if record["returnCode"] or not exactVersion(version):
            raise EnvironmentBlocked("course R6 requires exactly Verilator 5.050; found " + version.strip())
        record, compilerVersion = runProcess([compiler, "--version"], ROOT, outputDir / "compiler_version.log", deadline)
        result["commands"].append(record)
        if record["returnCode"]:
            raise EnvironmentBlocked("C++ compiler cannot report its version")
        result["toolchain"]["compilerVersion"] = compilerVersion.strip()
        try:
            import numpy
            import PIL
        except ImportError as error:
            raise EnvironmentBlocked("Python model dependencies missing: NumPy and Pillow") from error
        result["toolchain"].update(numpy=numpy.__version__, pillow=PIL.__version__)
        manifest = json.loads((ROOT / "tests/rtl/manifest.json").read_text(encoding="utf-8"))
        tests = selectTests(manifest)
        sourcePaths = {path for test in tests for path in test["sources"]}
        sourcePaths.update(("tests/rtl/manifest.json", "tools/lib/verilator_suite.py", "run_all_tests.sh",
                            "tools/run_r6_windows.py",
                            "tools/lib/export_vision_vectors.py", "tools/lib/vision_reference.py",
                            "tools/lib/projective_reference.py", "tools/lib/candidates_reclaimed_model.py",
                            "tools/lib/candidates_model.py", "tests/python/test_vision.py",
                            "assets/markers/marker_spec.json", "assets/markers/sheet_320x240.png"))
        result["sourceSha256"] = {path: fileHash(ROOT / path) for path in sorted(sourcePaths)}
        vectors = outputDir / "vectors"
        record, _ = runProcess([sys.executable, __file__, "--prepare-vectors", vectors], ROOT,
                               outputDir / "vectors.log", deadline)
        result["commands"].append(record)
        if record["returnCode"] or record["timedOut"]:
            raise RuntimeError("system pixel/model vector generation failed or timed out")
        result["fixtures"] = json.loads((vectors / "fixtures.json").read_text(encoding="utf-8"))
        # Run the production system before smaller modules, never substituting
        # a protocol-only bench to meet the deadline. All object dirs are new.
        for test in [*tests, {**next(t for t in tests if t["name"] == "targetTracker_tb"), "mutant": True}]:
            mutant = test.get("mutant", False)
            name = "targetTracker_broken_lock" if mutant else test["name"]
            folder = outputDir / name
            folder.mkdir()
            top = test.get("top", test["name"])
            sources = [ROOT / path for path in test["sources"]]
            if mutant:
                mutantPath = folder / "targetTracker.sv"
                makeMutant(ROOT / "rtl/tracking/targetTracker.sv", mutantPath)
                sources = [mutantPath if path == ROOT / "rtl/tracking/targetTracker.sv" else path for path in sources]
                result["mutation"] = {"source": "rtl/tracking/targetTracker.sv", "privateSha256": fileHash(mutantPath),
                                      "before": MUTATION_BEFORE, "after": MUTATION_AFTER}
            defines = ["-D" + define for define in test.get("defines", []) if define != "VERILATOR"]
            command = [verilator, "--binary", "--timing", "--assert", "-Wno-fatal", "--top-module", top,
                       "--Mdir", folder / "obj", "-j", str(args.jobs), *defines, *sources]
            if os.name == "nt":
                # Git Bash and native MinGW may carry different C++/pthread
                # DLLs. Bind the generated simulator to its compiler's static
                # runtime; this changes no HDL semantics or assertion flags.
                command[1:1] = ["-LDFLAGS", "-static", "-MAKEFLAGS", "PYTHON3=" + Path(sys.executable).as_posix()]
            record, _ = runProcess(command, folder, folder / "compile.log", deadline)
            result["commands"].append(record)
            if record["returnCode"] or record["timedOut"]:
                raise RuntimeError(f"{name} compilation failed or exceeded the complete-suite deadline")
            binary = folder / "obj" / ("V" + top + (".exe" if os.name == "nt" else ""))
            plusargs = [value.replace("{vectors}", vectors.as_posix()) for value in test.get("plusargs", [])]
            record, output = runProcess([binary, "+VECTOR_DIR=" + vectors.as_posix(), *plusargs], folder,
                                        folder / "simulation.log", deadline)
            result["commands"].append(record)
            passed = mutantCaught(record, output) if mutant else simulationPassed(record, output, test["passMarker"])
            status = "CAUGHT" if mutant and passed else "PASS" if passed else "FAIL"
            result["tests"].append({"name": name, "status": status,
                                    "inputSource": test.get("inputSource", "SYNTHETIC_MODULE_STIMULUS")})
            print(status + " " + name, flush=True)
            if not passed:
                raise RuntimeError(f"{name}: missing expected assertion/PASS, failed simulation or timeout")
        changed = [path for path, digest in result["sourceSha256"].items() if fileHash(ROOT / path) != digest]
        if changed:
            raise RuntimeError("sources changed during clean suite: " + ", ".join(changed))
        if time.monotonic() > deadline:
            raise TimeoutError("complete clean suite exceeded 300 seconds")
        result["status"] = "PASS"
        exitCode = 0
    except EnvironmentBlocked as error:
        result.update(status="ENVIRONMENT_BLOCKED", error=str(error))
        print("FAIL ENVIRONMENT_BLOCKED: " + str(error), flush=True)
        exitCode = 2
    except (OSError, RuntimeError, TimeoutError, KeyError, ValueError) as error:
        result.update(status="FAIL", error=str(error))
        print("FAIL " + str(error), flush=True)
    finally:
        result["elapsedSeconds"] = round(time.monotonic() - started, 6)
        result["exitCode"] = exitCode
        (outputDir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"{result['status']} course R6; result={outputDir / 'result.json'}", flush=True)
    return exitCode


if __name__ == "__main__":
    raise SystemExit(main())
