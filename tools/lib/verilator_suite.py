#!/usr/bin/env python3
"""Course R6: clean Verilator 5.050 module/system tests and a caught mutant.

This is a bounded course demonstration suite, not a replacement for echo7.py's
full ModelSim regression. Its system bench runs the production perceptionCore
on six alternating RGB565 frames with real row gaps and report backpressure,
plus an independent source-overload and three-fresh-frame recovery scenario.
Synthetic pixels do not constitute live CAMERA_HW or vehicle integration.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
    "tb_pixel_uart_repair", "tb_sonar_guard", "tb_control_repair", "tb_chassis_debug", "red2Start_tb",
    "perceptionCoreContinuous_tb", "perceptionCoreOverload_tb", "hsvColourGate_tb", "targetTracker_tb",
    "fixedSheetInteraction_tb", "colourSampler_tb", "markerQueryStore_tb", "mainColourSupportReader_tb",
)
ERROR_PATTERN = re.compile(r"%Error:|Assertion failed|\bFAIL(?:ED)?\b|\*\*\s+(?:Error|Fatal)")
MUTATION_BEFORE = "newReport.locked = nextCount == 3;"
MUTATION_AFTER = "newReport.locked = nextCount == 2;"


class EnvironmentBlocked(RuntimeError):
    """Required external tool or dependency is unavailable."""


def fileHash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def compilationIdentity(command, sources, toolchain):
    """Describe exactly the ordered inputs of one generated simulator.

    Object-directory location is the only removed compiler argument. Runtime
    plusargs never enter this function: continuous and overload must still run
    as separate simulations. Absolute source paths, their current bytes, top,
    defines, timing/assertion flags and compiler settings all remain in the key.
    The present R6 source closure is explicit and contains no local includes.
    """
    arguments = [str(value) for value in command]
    if arguments.count("--Mdir") != 1:
        raise ValueError("expected one explicit compiler object directory")
    index = arguments.index("--Mdir")
    if index + 1 >= len(arguments):
        raise ValueError("missing compiler object directory")
    arguments[index + 1] = "<CURRENT_RUN_OBJECT_DIRECTORY>"
    environmentNames = ("CC", "CXX", "CFLAGS", "CPPFLAGS", "CXXFLAGS", "LDFLAGS",
                        "MAKE", "MAKEFLAGS", "AR", "VERILATOR_ROOT", "PATH")
    identity = {
        "arguments": arguments,
        "sources": [{"path": str(Path(path).resolve()), "sha256": fileHash(path)} for path in sources],
        "toolchain": toolchain,
        # Hash environment values so a changed search path/flag prevents reuse,
        # without copying the entire host PATH into every compilation record.
        "environmentSha256": {name: hashlib.sha256(os.environ.get(name, "").encode("utf-8")).hexdigest()
                              for name in environmentNames},
    }
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest(), identity


class CurrentRunCompilations:
    """In-memory reuse only; never discover or load an earlier run's binary.

    A successful compilation registers its exact output hash. Every later use
    checks that the resolved binary still belongs to this run and has identical
    bytes. Creating another instance starts empty even for the same directory.
    """
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.entries = {}

    def _ownedBinary(self, path):
        binary = Path(path).resolve()
        try:
            binary.relative_to(self.directory)
        except ValueError as error:
            raise RuntimeError("compiled binary is outside the current clean run") from error
        if not binary.is_file():
            raise RuntimeError("compiled simulator binary is missing")
        return binary

    def register(self, key, name, path):
        binary = self._ownedBinary(path)
        entry = {"path": str(binary), "sha256": fileHash(binary),
                 "inputSha256": key, "compiledFor": name}
        self.entries[key] = entry
        return {**entry, "reusedFrom": None}

    def lookup(self, key):
        if key not in self.entries:
            return None
        entry = self.entries[key]
        binary = self._ownedBinary(entry["path"])
        if fileHash(binary) != entry["sha256"]:
            raise RuntimeError("compiled simulator binary changed during the current run")
        return {**entry, "reusedFrom": entry["compiledFor"]}


def selectTests(manifest):
    byName = {test["name"]: test for test in manifest["tests"]}
    selected = [dict(byName[name]) for name in SUITE_NAMES]
    for test in selected:
        if test["name"] == "tb_sonar_guard":
            # Keep production clock frequencies and six complete 100 ms sensor
            # transactions: measured/near/FAR/no-rise/stuck-high/recovery. The
            # manifest default retains the full twelve-sample boundary run.
            test["plusargs"] = ["+R6_REPRESENTATIVE"]
            test["inputSource"] = "PIN_LEVEL_J3_REAL_TIMING_REPRESENTATIVE_NORMAL_FAR_NEAR_FAULT_RECOVERY"
        if test["name"] == "mainColourSupportReader_tb":
            # The bounded course run executes this bench's independent built-in
            # merge/retirement/tie/overflow cases. The full ModelSim run also
            # passes MAIN_VECTORS and exercises the recorded pixel matrix.
            test["plusargs"] = []
            test["inputSource"] = "SYNTHETIC_BUILTIN_COMPONENT_OWNERSHIP_AND_OVERFLOW"
    return selected


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
    startedUtc = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
            "startedUtc": startedUtc, "finishedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
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
        base = recognise(image, cleanup=True, redMin=48, blueMin=20, colourAlgorithm=3,
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
                                        colourAlgorithm=3, readerAlgorithm=9)
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
    parser.add_argument("--jobs", type=int, default=4, choices=range(1, 17))
    parser.add_argument("--out", type=Path, help="new result directory; existing directories are never reused/deleted")
    parser.add_argument("--prepare-vectors", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if os.name == "nt" and os.environ.get("ECHO7_R6_NATIVE_PATH"):
        os.environ["PATH"] = os.environ["ECHO7_R6_NATIVE_PATH"] + os.pathsep + os.environ.get("PATH", "")
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
              "targetSeconds": 285, "simulationConcurrency": 2, "compilerConcurrency": 1,
              "compileJobs": args.jobs,
              "scope": "B+C modules, scanning/safety/CCTL, real-timing sonar TRIG/ECHO and actual perceptionCore pixels through C and UART", "tests": [], "commands": [],
              "compilations": [], "compilationReuse": "EXACT_INPUTS_WITHIN_THIS_FRESH_RUN_ONLY"}
    exitCode = 1
    try:
        verilator = shutil.which(args.verilator)
        makeExecutable = shutil.which("make")
        missing = [] if makeExecutable else ["make"]
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
        result["toolchain"]["make"] = makeExecutable
        toolExecutables = {"verilator": verilator, "compiler": compiler, "make": makeExecutable}
        toolHashes = {name: fileHash(path) for name, path in toolExecutables.items()}
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
                            "assets/markers/marker_spec.json", "assets/markers/sheet_320x240.png",
                            "tests/vectors/sheet_320x240_rgb565.hex"))
        sourceHashes = {path: fileHash(ROOT / path) for path in sorted(sourcePaths)}
        result["sourceCount"] = len(sourceHashes)
        # Compile from a fresh source copy, with no prior objects or binaries.
        # Internal hashes only detect an edit racing this invocation; no
        # per-file hash manifest is exported or required from the user.
        sourceRoot = outputDir / "source"
        for relative in sorted(sourcePaths):
            copied = sourceRoot / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, copied)
            if fileHash(copied) != sourceHashes[relative]:
                raise RuntimeError("source changed while making the clean copy: " + relative)
        result["sourceCopy"] = str(sourceRoot)
        vectors = outputDir / "vectors"
        record, _ = runProcess([sys.executable, __file__, "--prepare-vectors", vectors], ROOT,
                               outputDir / "vectors.log", deadline)
        result["commands"].append(record)
        if record["returnCode"] or record["timedOut"]:
            raise RuntimeError("system pixel/model vector generation failed or timed out")
        result["fixtures"] = json.loads((vectors / "fixtures.json").read_text(encoding="utf-8"))
        # Run the production system before smaller modules, never substituting
        # a protocol-only bench to meet the deadline. Reuse is limited to an
        # already compiled exact-input binary from this fresh invocation; every
        # scenario still executes independently with its own log and verdict.
        compiled = CurrentRunCompilations(outputDir)
        result["parallelGroups"] = []
        result["compileSimulationOverlap"] = "SERIAL_PRECOMPILE_DURING_FIRST_SIMULATION_PAIR"
        result["prefetchedScenarios"] = []

        def prepareScenario(test):
            # Preparation stays on the main thread: at most one compiler
            # process (with args.jobs children), even while simulations run.
            # Both binaries in a simulation pair are compiled before launch.
            mutant = test.get("mutant", False)
            name = "targetTracker_broken_lock" if mutant else test["name"]
            folder = outputDir / name
            folder.mkdir()
            top = test.get("top", test["name"])
            sources = [sourceRoot / path for path in test["sources"]]
            if mutant:
                mutantPath = folder / "targetTracker.sv"
                makeMutant(sourceRoot / "rtl/tracking/targetTracker.sv", mutantPath)
                sources = [mutantPath if path == sourceRoot / "rtl/tracking/targetTracker.sv" else path for path in sources]
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
            for toolName, path in toolExecutables.items():
                if fileHash(path) != toolHashes[toolName]:
                    raise RuntimeError("tool executable changed during clean suite: " + toolName)
            # Detect a mid-run source edit before either compiling or reusing
            # it. The deliberate private mutant is recorded separately above.
            for path in test["sources"]:
                if fileHash(ROOT / path) != sourceHashes[path]:
                    raise RuntimeError("source changed during clean suite: " + path)
            compileKey, _ = compilationIdentity(command, sources, result["toolchain"])
            compiledBinary = compiled.lookup(compileKey)
            if compiledBinary is None:
                record, _ = runProcess(command, folder, folder / "compile.log", deadline)
                result["commands"].append(record)
                if record["returnCode"] or record["timedOut"]:
                    raise RuntimeError(f"{name} compilation failed or exceeded the complete-suite deadline")
                binary = folder / "obj" / ("V" + top + (".exe" if os.name == "nt" else ""))
                compiledBinary = compiled.register(compileKey, name, binary)
                result["compilations"].append({"cacheKey": compileKey,
                                               "compiledBinary": compiledBinary})
            else:
                binary = Path(compiledBinary["path"])
                (folder / "compile_reuse.json").write_text(json.dumps(compiledBinary, indent=2) + "\n", encoding="utf-8")
                (folder / "compile.log").write_text(
                    "No compiler process was run: exact-input binary reused from this fresh run.\n" +
                    json.dumps(compiledBinary, indent=2) + "\n", encoding="utf-8")
            return (test, name, folder, compiledBinary), command, compileKey, top

        completedPairs = set()
        scenarios = [*tests, {**next(t for t in tests if t["name"] == "targetTracker_tb"), "mutant": True}]
        prefetched = {}
        for test in scenarios:
            mutant = test.get("mutant", False)
            name = "targetTracker_broken_lock" if mutant else test["name"]
            if name in completedPairs:
                continue
            if name in prefetched:
                prepared, command, compileKey, top = prefetched.pop(name)
                # Precompilation may precede execution by many seconds. Recheck
                # the owned binary rather than trusting stale cached metadata.
                checkedBinary = compiled.lookup(compileKey)
                if checkedBinary is None or checkedBinary["path"] != prepared[3]["path"]:
                    raise RuntimeError("prepared simulator no longer matches its current-run compilation")
            else:
                prepared, command, compileKey, top = prepareScenario(test)
            group = [prepared]
            if name == "tb_pixel_uart_repair":
                # Independent production pixel/UART and real-clock sonar
                # benches have no shared writes. Compile their separate
                # binaries first, then overlap only the two simulations.
                paired = next(t for t in tests if t["name"] == "tb_sonar_guard")
                pairedPrepared, _, _, _ = prepareScenario(paired)
                group.append(pairedPrepared)
                completedPairs.add(paired["name"])
            if name == "perceptionCoreContinuous_tb":
                # These two independent processes only read their immutable
                # vectors. They share this invocation's exact-input binary,
                # with separate cwd/logs and independent assertions/verdicts.
                paired = next(t for t in tests if t["name"] == "perceptionCoreOverload_tb")
                pairedFolder = outputDir / paired["name"]
                pairedFolder.mkdir()
                pairedCommand = list(command)
                pairedCommand[pairedCommand.index("--Mdir")+1] = pairedFolder / "obj"
                pairedSources = [sourceRoot / path for path in paired["sources"]]
                pairedKey, _ = compilationIdentity(pairedCommand, pairedSources, result["toolchain"])
                if (pairedKey != compileKey or paired.get("top", paired["name"]) != top or
                        paired.get("defines", []) != test.get("defines", [])):
                    raise RuntimeError("continuous/overload no longer have identical compile inputs")
                pairedBinary = compiled.lookup(pairedKey)
                (pairedFolder / "compile_reuse.json").write_text(json.dumps(pairedBinary, indent=2)+"\n", encoding="utf-8")
                (pairedFolder / "compile.log").write_text(
                    "Exact-input binary from this fresh invocation; scenario runs concurrently in its own process.\n", encoding="utf-8")
                group.append((paired, paired["name"], pairedFolder, pairedBinary))
                completedPairs.add(paired["name"])
                result["parallelScenarios"] = [name, paired["name"]]

            def runScenario(item):
                scenario, scenarioName, scenarioFolder, scenarioBinary = item
                plusargs = [value.replace("{vectors}", vectors.as_posix()).replace("{root}", sourceRoot.as_posix())
                            for value in scenario.get("plusargs", [])]
                return runProcess([Path(scenarioBinary["path"]), "+VECTOR_DIR=" + vectors.as_posix(), *plusargs],
                                  scenarioFolder, scenarioFolder / "simulation.log", deadline)

            preparationError = None
            if len(group) == 2:
                result["parallelGroups"].append([item[1] for item in group])
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [pool.submit(runScenario, item) for item in group]
                    if name == "tb_pixel_uart_repair":
                        # Hide serial compilation behind the long, independent
                        # pixel/sonar simulations. No third simulator is started,
                        # no earlier-run binary is loaded, and the prepared
                        # scenarios still run in the original order below.
                        # The overload partner retains its explicit exact-input
                        # check/reuse path when the continuous pair is reached.
                        try:
                            for later in scenarios:
                                laterName = "targetTracker_broken_lock" if later.get("mutant", False) else later["name"]
                                if laterName in ("tb_pixel_uart_repair", "tb_sonar_guard", "perceptionCoreOverload_tb"):
                                    continue
                                # Stop starting compilers once an already
                                # completed first-pair simulation has failed.
                                if any(future.done() and not simulationPassed(*future.result(), item[0]["passMarker"])
                                       for item, future in zip(group, futures)):
                                    break
                                prefetched[laterName] = prepareScenario(later)
                                result["prefetchedScenarios"].append(laterName)
                        except (OSError, RuntimeError, TimeoutError, KeyError, ValueError) as error:
                            # Retain the independent simulation verdicts/logs
                            # before reporting a failed overlapped preparation.
                            preparationError = error
                    outcomes = [future.result() for future in futures]
            else:
                outcomes = [runScenario(group[0])]
            failed = []
            for (scenario, scenarioName, _, scenarioBinary), (record, output) in zip(group, outcomes):
                result["commands"].append(record)
                passed = mutantCaught(record, output) if mutant else simulationPassed(record, output, scenario["passMarker"])
                status = "CAUGHT" if mutant and passed else "PASS" if passed else "FAIL"
                result["tests"].append({"name": scenarioName, "status": status,
                                        "compiledBinary": scenarioBinary,
                                        "inputSource": scenario.get("inputSource", "SYNTHETIC_MODULE_STIMULUS")})
                print(status + " " + scenarioName, flush=True)
                if not passed:
                    failed.append(scenarioName)
            if failed:
                raise RuntimeError(f"{', '.join(failed)}: missing expected assertion/PASS, failed simulation or timeout")
            if preparationError is not None:
                raise preparationError
        changed = [path for path, digest in sourceHashes.items() if fileHash(ROOT / path) != digest]
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
        result["targetMet"] = result["status"] == "PASS" and result["elapsedSeconds"] <= result["targetSeconds"]
        result["exitCode"] = exitCode
        (outputDir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"{result['status']} course R6; result={outputDir / 'result.json'}", flush=True)
    return exitCode


if __name__ == "__main__":
    raise SystemExit(main())
