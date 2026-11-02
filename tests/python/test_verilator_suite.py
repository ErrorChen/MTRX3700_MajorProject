"""HOST_RUNNER checks only; these are not Verilator or course R6 evidence."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("verilator_suite", ROOT / "tools/lib/verilator_suite.py")
suite = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suite)


class VerilatorRunnerTests(unittest.TestCase):
    def testExactVersionRequired(self):
        self.assertTrue(suite.exactVersion("Verilator 5.050 2026-04-01 rev example"))
        for text in ("Verilator 5.048", "Verilator 5.0501", "Other 5.050", ""):
            self.assertFalse(suite.exactVersion(text), text)

    def testSystemIsMandatoryAndFirst(self):
        manifest = json.loads((ROOT / "tests/rtl/manifest.json").read_text(encoding="utf-8"))
        selected = suite.selectTests(manifest)
        self.assertEqual(selected[0]["name"], "perceptionCoreContinuous_tb")
        self.assertIn("rtl/top/perceptionCore.sv", selected[0]["sources"])
        self.assertEqual(selected[0]["plusargs"], ["+CONTINUOUS"])
        self.assertGreaterEqual(len(selected), 4)
        with self.assertRaises(KeyError):
            suite.selectTests({"tests": [test for test in manifest["tests"]
                                         if test["name"] != "perceptionCoreContinuous_tb"]})

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


if __name__ == "__main__":
    unittest.main()
