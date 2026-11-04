"""HOST_RUNNER checks only; these are not Verilator or course R6 evidence."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verilator_suite", ROOT / "tools/lib/verilator_suite.py")
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class VerilatorRunnerTests(unittest.TestCase):
    def runHostDouble(self, output, failedScenario=None):
        """Exercise the real runner orchestration, with no HDL tool execution.

        Only compiler/simulator processes are replaced. Real source hashes,
        private mutant creation, invocation-local binary registration and JSON
        reporting still execute. Generated executable files are inert text.
        """
        selected = suite.selectTests(json.loads((ROOT / "tests/rtl/manifest.json").read_text(encoding="utf-8")))
        markers = {test["name"]: test["passMarker"] for test in selected}
        calls = []
        pairedSimulationBarrier = threading.Barrier(2)

        def process(arguments, cwd, logPath, deadline):
            command = [str(value) for value in arguments]
            logPath = Path(logPath)
            calls.append({"arguments": command, "cwd": str(cwd), "log": str(logPath), "deadline": deadline,
                          "threadId": threading.get_ident()})
            code = 0
            if logPath.name == "version.log":
                text = "Verilator 5.050 HOST_RUNNER_DOUBLE_ONLY\n"
            elif logPath.name == "compiler_version.log":
                text = "Compiler HOST_RUNNER_DOUBLE_ONLY\n"
            elif "--prepare-vectors" in command:
                vectors = Path(command[command.index("--prepare-vectors") + 1])
                vectors.mkdir()
                (vectors / "fixtures.json").write_text("[]\n", encoding="utf-8")
                text = "HOST_RUNNER_DOUBLE_ONLY vectors\n"
            elif "--binary" in command:
                objects = Path(command[command.index("--Mdir") + 1])
                objects.mkdir()
                top = command[command.index("--top-module") + 1]
                binary = objects / ("V" + top + (".exe" if os.name == "nt" else ""))
                binary.write_bytes(b"INERT_HOST_TEST_FILE_NOT_A_SIMULATOR")
                text = "HOST_RUNNER_DOUBLE_ONLY compilation\n"
            else:
                name = Path(cwd).name
                if name in ("perceptionCoreContinuous_tb", "perceptionCoreOverload_tb"):
                    pairedSimulationBarrier.wait(timeout=2)
                if name == "targetTracker_broken_lock":
                    code, text = 1, "%Error: Assertion failed: three-frame lock HOST_RUNNER_DOUBLE_ONLY\n"
                elif name == failedScenario:
                    code, text = 1, "FAIL injected runner transport/simulation outcome\n"
                else:
                    text = markers[name] + " HOST_RUNNER_DOUBLE_ONLY\n"
            logPath.write_text(text, encoding="utf-8")
            return {"arguments": command, "returnCode": code, "timedOut": False,
                    "elapsedSeconds": 0.0, "log": str(logPath)}, text

        with patch.object(suite.shutil, "which", return_value=sys.executable), \
             patch.object(suite, "runProcess", side_effect=process), \
             contextlib.redirect_stdout(io.StringIO()):
            exitCode = suite.main(["--out", str(output)])
        return exitCode, json.loads((output / "result.json").read_text(encoding="utf-8")), calls

    def testExactVersionRequired(self):
        self.assertTrue(suite.exactVersion("Verilator 5.050 2026-04-01 rev example"))
        for text in ("Verilator 5.048", "Verilator 5.0501", "Other 5.050", ""):
            self.assertFalse(suite.exactVersion(text), text)

    def testSystemIsMandatoryAndFirst(self):
        manifest = json.loads((ROOT / "tests/rtl/manifest.json").read_text(encoding="utf-8"))
        selected = suite.selectTests(manifest)
        self.assertEqual(selected[0]["name"], "tb_pixel_uart_repair")
        self.assertIn("rtl/top/perceptionCore.sv", selected[0]["sources"])
        continuous = next(test for test in selected if test["name"] == "perceptionCoreContinuous_tb")
        self.assertEqual(continuous["plusargs"], ["+CONTINUOUS"])
        overload = next(test for test in selected if test["name"] == "perceptionCoreOverload_tb")
        self.assertIn("rtl/top/perceptionCore.sv", overload["sources"])
        self.assertIn("+OVERLOAD", overload["plusargs"])
        self.assertEqual(len(selected), 12)
        pixel = next(test for test in selected if test["name"] == "tb_pixel_uart_repair")
        self.assertIn("rtl/top/perceptionCore.sv", pixel["sources"])
        self.assertIn("rtl/member_c/member_c_control.sv", pixel["sources"])
        self.assertIn("rtl/member_c/chassis_command.sv", pixel["sources"])
        with self.assertRaises(KeyError):
            suite.selectTests({"tests": [test for test in manifest["tests"]
                                         if test["name"] != "perceptionCoreContinuous_tb"]})
        with self.assertRaises(KeyError):
            suite.selectTests({"tests": [test for test in manifest["tests"]
                                         if test["name"] != "perceptionCoreOverload_tb"]})

    def testPassRequiresMarkerExitAndNoErrors(self):
        record = {"returnCode": 0, "timedOut": False}
        self.assertTrue(suite.simulationPassed(record, "PASS tracker", "PASS tracker"))
        for output in ("", "PASS tracker\n%Error: assertion", "PASS tracker\nFAIL other"):
            self.assertFalse(suite.simulationPassed(record, output, "PASS tracker"))
        self.assertFalse(suite.simulationPassed({**record, "returnCode": 1}, "PASS tracker", "PASS tracker"))
        self.assertFalse(suite.simulationPassed({**record, "timedOut": True}, "PASS tracker", "PASS tracker"))

    def testCaughtRequiresIntendedAssertion(self):
        record = {"returnCode": -6, "timedOut": False}
        expected = "%Error: targetTracker_tb.sv: Assertion failed: three-frame lock bay=1 n=2"
        self.assertTrue(suite.mutantCaught(record, expected))
        for output in ("Segmentation fault", "%Error: syntax error", "PASS targetTracker_tb", ""):
            self.assertFalse(suite.mutantCaught(record, output))
        self.assertFalse(suite.mutantCaught({**record, "timedOut": True}, expected))
        self.assertFalse(suite.mutantCaught({**record, "returnCode": 0}, expected))

    def testMutationOnlyChangesPrivateCopy(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.sv"
            destination = Path(folder) / "broken.sv"
            source.write_text("begin\n" + suite.MUTATION_BEFORE + "\nend\n", encoding="utf-8")
            original = source.read_bytes()
            suite.makeMutant(source, destination)
            self.assertEqual(source.read_bytes(), original)
            self.assertIn(suite.MUTATION_AFTER, destination.read_text(encoding="utf-8"))
            source.write_text("anchor changed", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                suite.makeMutant(source, destination)

    def testExpiredDeadlineNeverLaunches(self):
        with patch.object(suite.subprocess, "Popen") as launch:
            with self.assertRaises(TimeoutError):
                suite.runProcess(["unused"], ROOT, ROOT / "unused.log", time.monotonic() - 1)
            launch.assert_not_called()

    def testSubprocessPreservesSpacesAndFailure(self):
        with tempfile.TemporaryDirectory(prefix="runner space ") as folder:
            value = "value with spaces; literal $()"
            record, output = suite.runProcess(
                [sys.executable, "-c", "import sys; print(sys.argv[1]); sys.exit(7)", value],
                folder, Path(folder) / "run log.txt", time.monotonic() + 10)
            self.assertEqual(record["returnCode"], 7)
            self.assertFalse(record["timedOut"])
            self.assertEqual(output.strip(), value)

    def testMissingToolWritesBlockedExitTwo(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "new run"
            with patch.object(suite.shutil, "which", return_value=None), contextlib.redirect_stdout(io.StringIO()):
                exitCode = suite.main(["--out", str(output)])
            result = json.loads((output / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(exitCode, 2)
            self.assertEqual(result["status"], "ENVIRONMENT_BLOCKED")
            self.assertEqual(result["tests"], [])
            self.assertEqual(result["commands"], [])

    def testWrongVersionIsBlockedBeforeBuild(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "wrong version"
            record = {"returnCode": 0, "timedOut": False}
            with patch.object(suite.shutil, "which", side_effect=lambda name: name), \
                 patch.object(suite, "runProcess", return_value=(record, "Verilator 5.048")) as run, \
                 contextlib.redirect_stdout(io.StringIO()):
                exitCode = suite.main(["--out", str(output)])
            self.assertEqual(exitCode, 2)
            self.assertEqual(run.call_count, 1)

    def testCompilationIdentityKeepsSourcesOrderTopDefinesFlagsAndTools(self):
        with tempfile.TemporaryDirectory() as folder:
            first, second = Path(folder) / "one.sv", Path(folder) / "two.sv"
            first.write_text("module one; endmodule\n", encoding="utf-8")
            second.write_text("module two; endmodule\n", encoding="utf-8")
            sources = [first, second]
            command = ["verilator", "--binary", "--timing", "--assert", "--top-module", "one",
                       "--Mdir", Path(folder) / "first objects", "-DTEST", *sources]
            tools = {"version": "Verilator 5.050", "compilerVersion": "example"}
            original, inputs = suite.compilationIdentity(command, sources, tools)
            changed = list(command); changed[changed.index("--Mdir") + 1] = Path(folder) / "other objects"
            self.assertEqual(original, suite.compilationIdentity(changed, sources, tools)[0])
            self.assertEqual([item["path"] for item in inputs["sources"]], [str(path.resolve()) for path in sources])
            for replacement in ("differentTop", "one"):
                changed = list(command)
                if replacement == "differentTop":
                    changed[changed.index("--top-module") + 1] = replacement
                else:
                    changed.remove("--assert")
                self.assertNotEqual(original, suite.compilationIdentity(changed, sources, tools)[0])
            self.assertNotEqual(original, suite.compilationIdentity([*command, "-DOTHER"], sources, tools)[0])
            self.assertNotEqual(original, suite.compilationIdentity(command, list(reversed(sources)), tools)[0])
            self.assertNotEqual(original, suite.compilationIdentity(command, sources, {**tools, "compilerVersion": "changed"})[0])
            with patch.dict(os.environ, {"CXXFLAGS": "-O1 HOST_TEST_ONLY"}):
                self.assertNotEqual(original, suite.compilationIdentity(command, sources, tools)[0])
            first.write_text("module one; initial $error; endmodule\n", encoding="utf-8")
            self.assertNotEqual(original, suite.compilationIdentity(command, sources, tools)[0])

    def testReuseNeverLoadsPreviousRunAndRejectsForeignOrChangedBinary(self):
        with tempfile.TemporaryDirectory() as folder:
            current = Path(folder) / "current"; current.mkdir()
            binary = current / "compiled"; binary.write_bytes(b"first bytes")
            cache = suite.CurrentRunCompilations(current)
            registered = cache.register("same inputs", "first scenario", binary)
            self.assertIsNone(registered["reusedFrom"])
            reused = cache.lookup("same inputs")
            self.assertEqual(reused["sha256"], suite.fileHash(binary))
            self.assertEqual(reused["reusedFrom"], "first scenario")
            self.assertIsNone(cache.lookup("different inputs"))
            self.assertIsNone(suite.CurrentRunCompilations(current).lookup("same inputs"))
            foreign = Path(folder) / "previous"; foreign.write_bytes(b"first bytes")
            with self.assertRaisesRegex(RuntimeError, "outside the current"):
                cache.register("foreign", "previous run", foreign)
            binary.write_bytes(b"tampered bytes")
            with self.assertRaisesRegex(RuntimeError, "changed during"):
                cache.lookup("same inputs")

    def testFreshRunCompilesCoreOnceButExecutesBothScenariosAndMutant(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "clean run"
            exitCode, result, calls = self.runHostDouble(output)
            self.assertEqual(exitCode, 0)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["cleanBuild"])
            self.assertEqual(result["maximumSeconds"], 300)
            self.assertEqual(len(result["tests"]), len(suite.SUITE_NAMES)+1)
            self.assertEqual([test["name"] for test in result["tests"][:-1]], list(suite.SUITE_NAMES))
            self.assertEqual(result["tests"][-1]["status"], "CAUGHT")
            compilations = [call for call in calls if "--binary" in call["arguments"]]
            simulations = [call for call in calls if Path(call["log"]).name == "simulation.log"]
            self.assertEqual((len(compilations), len(simulations)), (len(suite.SUITE_NAMES), len(suite.SUITE_NAMES)+1))
            first = next(test for test in result["tests"] if test["name"] == "perceptionCoreContinuous_tb")
            overload = next(test for test in result["tests"] if test["name"] == "perceptionCoreOverload_tb")
            self.assertEqual(overload["compiledBinary"]["reusedFrom"], first["name"])
            self.assertEqual(overload["compiledBinary"]["sha256"], first["compiledBinary"]["sha256"])
            continuousRun = next(call for call in simulations if Path(call["cwd"]).name == "perceptionCoreContinuous_tb")
            overloadRun = next(call for call in simulations if Path(call["cwd"]).name == "perceptionCoreOverload_tb")
            self.assertEqual(continuousRun["arguments"][0], overloadRun["arguments"][0])
            self.assertNotIn("+OVERLOAD", continuousRun["arguments"])
            self.assertIn("+OVERLOAD", overloadRun["arguments"])
            self.assertNotEqual(continuousRun["log"], overloadRun["log"])
            self.assertNotEqual(continuousRun["threadId"], overloadRun["threadId"])
            self.assertEqual(result["parallelScenarios"], ["perceptionCoreContinuous_tb", "perceptionCoreOverload_tb"])
            self.assertTrue((output / overload["name"] / "compile_reuse.json").is_file())
            self.assertEqual(len(set(call["deadline"] for call in calls)), 1)
            good = next(test for test in result["tests"] if test["name"] == "targetTracker_tb")
            mutant = result["tests"][-1]
            self.assertIsNone(mutant["compiledBinary"]["reusedFrom"])
            self.assertNotEqual(good["compiledBinary"]["inputSha256"], mutant["compiledBinary"]["inputSha256"])
            # A second fresh invocation compiles again even though identical
            # current-run binaries still exist in the first result directory.
            _, second, secondCalls = self.runHostDouble(Path(folder) / "another clean run")
            self.assertEqual(sum("--binary" in call["arguments"] for call in secondCalls), len(suite.SUITE_NAMES))
            self.assertIsNone(second["tests"][0]["compiledBinary"]["reusedFrom"])

    def testFailureOfReusedSimulatorStillFailsAndKeepsIndependentLog(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "failed overload"
            exitCode, result, calls = self.runHostDouble(output, "perceptionCoreOverload_tb")
            self.assertEqual(exitCode, 1)
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual([test["status"] for test in result["tests"]], ["PASS"]*5 + ["FAIL"])
            failed = result["tests"][-1]
            self.assertEqual(failed["compiledBinary"]["reusedFrom"], "perceptionCoreContinuous_tb")
            self.assertIn("FAIL injected", (output / failed["name"] / "simulation.log").read_text())
            self.assertEqual(sum("--binary" in call["arguments"] for call in calls), 5)


if __name__ == "__main__":
    unittest.main()
