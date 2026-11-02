import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""Tool-level regressions; mocked JTAG is NEVER CAMERA_HW evidence."""
import json
import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from datetime import datetime, timezone

import echo7


class TimingGateTests(unittest.TestCase):
    def testVendorWarningsWithoutMessageNumbersAreRetained(self):
        output = ("Info: 0 errors, 87 warnings\n"
                  "Warning (10230): truncated value with size 32\n"
                  "  Warning: RST port on the PLL is tied to GND\n"
                  "Critical Warning (332148): Timing requirements not met\n"
                  "Info: quoted Warning (12345) is not a diagnostic\n")
        self.assertEqual(echo7.collectQuartusWarnings(output), [
            "Warning (10230): truncated value with size 32",
            "Warning: RST port on the PLL is tied to GND",
            "Critical Warning (332148): Timing requirements not met"])

    def testPostMapCannotQualifyFittedSynchroniserCoverage(self):
        with self.assertRaisesRegex(RuntimeError, "post-fit"):
            echo7.checkSynchroniserReports(Path("unused"), {"analysisStage": "POST_MAP_CONSTRAINT_AUDIT"})
        with self.assertRaisesRegex(RuntimeError, "no fitted corners"):
            echo7.checkSynchroniserReports(Path("unused"), {"analysisStage": "POST_FIT", "checks": []})

    def testRejectNegativeAndMissingTiming(self):
        with self.assertRaises(RuntimeError):
            echo7.checkTimingReports("", "")
        with self.assertRaises(RuntimeError):
            echo7.checkTimingReports("Type : Setup\nSlack : -0.1\nType : Hold\nSlack : 1\nType : Minimum Pulse Width\nSlack : 1", "")

    def testRejectUnconstrained(self):
        summary = "\n".join("Type : " + name + "\nSlack : 0.1" for name in ("Setup", "Hold", "Minimum Pulse Width"))
        names = ["Illegal Clocks", "Unconstrained Clocks", "Unconstrained Input Ports", "Unconstrained Input Port Paths",
                 "Unconstrained Output Ports", "Unconstrained Output Port Paths"]
        report = "\n".join("; " + n + " ; 0 ; 0 ;" for n in names)
        self.assertEqual(echo7.checkTimingReports(summary, report)["analysedChecks"], 3)
        with self.assertRaises(RuntimeError):
            echo7.checkTimingReports(summary, report.replace("Clocks ; 0", "Clocks ; 1"))


class ProcessTimeoutTests(unittest.TestCase):
    def testEqualWindowsTimestampsKeepEvidenceSeparate(self):
        args = argparse.Namespace(command="directory_selftest", timeout=1)
        with tempfile.TemporaryDirectory(prefix="runner_names_", dir=echo7.WORK) as folder:
            with patch.object(echo7, "WORK", Path(folder)), patch.object(echo7, "datetime") as clock:
                clock.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
                first = echo7.Runner(args)
                sentinel = first.out / "must_not_be_overwritten.txt"
                sentinel.write_text("original evidence")
                second = echo7.Runner(args)
                self.assertNotEqual(first.out, second.out)
                self.assertEqual(sentinel.read_text(), "original evidence")
                self.assertTrue(second.out.name.endswith("_001"))

    def testOwnedProcessTimeoutIsNonzeroAndRecorded(self):
        args = argparse.Namespace(command="timeout_selftest", timeout=1)
        runner = echo7.Runner(args)
        code, output = runner.run("sleeping_child", [sys.executable, "-c", "import time; print('started',flush=True); time.sleep(10)"], checked=False)
        self.assertEqual(code, 124)
        self.assertEqual(runner.result["steps"][0]["returncode"], 124)
        self.assertLess(runner.result["steps"][0]["elapsedSeconds"], 8)
        self.assertIn("timed out", output)
        self.assertIn("started", output)
        step = runner.result["steps"][0]
        persisted = Path(step["log"]).read_bytes().decode(step["logEncoding"])
        self.assertIn("started", persisted)
        self.assertIn("TIMEOUT", persisted)
        self.assertTrue(step["timedOut"])
        self.assertFalse(step["ownedParentMayRemain"])

    @unittest.skipUnless(sys.platform == "win32", "Windows inherited stdout regression")
    def testSurvivingShortDescendantCannotHoldRunnerStdoutPipe(self):
        args = argparse.Namespace(command="descendant_selftest", timeout=0.3)
        runner = echo7.Runner(args)
        childCode = "import time; print('descendant started',flush=True); time.sleep(3); print('descendant ended',flush=True)"
        parentCode = ("import subprocess,sys,time; print('parent started',flush=True); "
                      f"subprocess.Popen([sys.executable,'-c',{childCode!r}]); time.sleep(10)")
        # Simulate the exact OS failure observed during Quartus timeout: tree
        # enumeration is denied but the directly-owned process can be killed.
        # Only our short-lived test descendant survives; it exits by itself.
        realRun = subprocess.run
        def noTreeTermination(command, **kwargs):
            if command[0] == "taskkill":
                return subprocess.CompletedProcess(command, 1)
            return realRun(command, **kwargs)
        started = time.monotonic()
        with patch.object(echo7.subprocess, "run", side_effect=noTreeTermination):
            code, output = runner.run("parent_with_descendant", [sys.executable, "-c", parentCode], checked=False)
        elapsed = time.monotonic() - started
        self.assertEqual(code, 124)
        self.assertLess(elapsed, 2.5, "Runner waited for inherited descendant stdout")
        self.assertIn("parent started", output)
        self.assertIn("descendant started", output)
        self.assertFalse(runner.result["steps"][0]["treeTerminationConfirmed"])
        self.assertTrue(any("descendants may remain" in warning for warning in runner.result["terminationWarnings"]))
        time.sleep(max(0, 3.4 - elapsed))
        step = runner.result["steps"][0]
        persisted = Path(step["log"]).read_bytes().decode(step["logEncoding"])
        self.assertIn("descendant ended", persisted)

    def testNonzeroProcessKeepsCompleteOutputAndDoesNotShareLog(self):
        runner = echo7.Runner(argparse.Namespace(command="log_selftest", timeout=2))
        code, output = runner.run("same_label", [sys.executable, "-c", "print('first output'); raise SystemExit(7)"], checked=False)
        self.assertEqual(code, 7)
        self.assertIn("first output", output)
        firstLog = Path(runner.result["steps"][0]["log"])
        runner.run("same_label", [sys.executable, "-c", "print('second output')"])
        self.assertNotEqual(firstLog, Path(runner.result["steps"][1]["log"]))
        self.assertIn("first output", firstLog.read_text())
        self.assertNotIn("second output", firstLog.read_text())


class VectorNamespaceTests(unittest.TestCase):
    def testContourWriterCannotReplaceConnectedComponentVectors(self):
        from export_contour_vectors import writeVectors
        with tempfile.TemporaryDirectory(prefix="vector_namespace_") as folder:
            output = Path(folder)
            candidateFiles = {"masks.hex": "00\n", "expected.hex": "00000001\n", "metadata.json": "{}\n"}
            for name, text in candidateFiles.items():
                (output / name).write_text(text)
            writeVectors(output, [0x80000000, 0x40000000], [0x80000000, 0x40000000], [0x3020, 0x3020], [])
            for name, text in candidateFiles.items():
                self.assertEqual((output / name).read_text(), text)
            newFiles = {path.name for path in output.iterdir()} - set(candidateFiles)
            self.assertEqual(newFiles, {"contour_input.hex", "contour_expected.hex", "contour_profile.hex",
                                       "contour_vector_count.hex", "contour_vectors.json"})
            self.assertEqual((output / "contour_vector_count.hex").read_text(), "00000002\n")


class DeferredAudioControlTests(unittest.TestCase):
    def testArmIsOnlyVisualOpcodeAndNeverANumberProposal(self):
        # Test the command dispatcher without connecting to a board. This is a
        # tool protocol check, not evidence that red 2 or speech was recognised.
        runner = echo7.Runner(argparse.Namespace(command="speech", arm=True, record=False, timeout=1))
        commands = []
        def control(command):
            commands.append(command)
            return {"decoded": {"status": {"audioReady": 0}}}
        runner.control = control
        runner.execute()
        self.assertEqual(commands, [4 << 24])
        self.assertEqual(commands[0] & 0xffffff, 0)
        self.assertFalse(runner.result["audioReady"])
        self.assertEqual(runner.result["audioInputStatus"], "DEFERRED_USER")
        self.assertIn("no digit proposal", runner.result["operationMeaning"])
        self.assertNotIn("userEvent", runner.result)

    def testRecordIsExplicitlyDeferred(self):
        output = io.StringIO()
        with redirect_stdout(output):
            code = echo7.main(["speech", "--record"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result["exitCode"], 2)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["audioInputStatus"], "DEFERRED_USER")


class HardwareDiagnosticGateTests(unittest.TestCase):
    def testDiscardBeforeCurrentTargetReportStillFails(self):
        # Only the status transport is stubbed. This verifies the host refuses
        # a new drop before it can qualify a target, not camera recognition.
        runner = echo7.Runner(argparse.Namespace(command="test", timeout=1))
        initial = {"bufferDropCount": 0, "completionDiscardCount": 17, "status": {"faultFlags": 0}}
        responses = iter([initial, initial, {"completionDiscardCount": 18}])
        runner.control = lambda command=0: {"decoded": next(responses)}
        with self.assertRaisesRegex(RuntimeError, "completionDiscardCount changed"):
            runner.hardware()
        self.assertEqual(runner.result["initialDiagnostics"]["completionDiscardCount"], 17)
        self.assertEqual(runner.result["hardwareFrames"], [])

    def testSaturatedDiscardCounterCannotProveNoNewDrops(self):
        runner = echo7.Runner(argparse.Namespace(command="test", timeout=1))
        runner.control = lambda command=0: {"decoded": {"bufferDropCount": 0,
            "completionDiscardCount": 0xffff, "status": {"faultFlags": 0}}}
        with self.assertRaisesRegex(RuntimeError, "saturated"):
            runner.hardware()


class TclFailurePropagationTests(unittest.TestCase):
    """Execute the real Tcl script with a small deterministic API test double.

    These tests cover device selection and error propagation, not JTAG drivers,
    FPGA configuration, camera pixels or recognition.
    """
    def invoke(self, duplicate):
        try:
            tool = echo7.discover("quartus_sh")
        except echo7.Blocked:
            self.skipTest("Quartus Tcl interpreter unavailable")
        with tempfile.TemporaryDirectory(prefix="tcl_test_", dir=echo7.WORK) as folder:
            root = Path(folder)
            script = root / "driver.tcl"
            out = root / "out"
            fixture = """
rename load_package real_load_package
proc load_package {args} {}
proc get_hardware_names {} {return {mockCable}}
proc get_device_names {args} {return DEVICE_LIST}
proc get_insystem_source_probe_instance_info {args} {return {{0 1 21 GCTL}}}
proc get_editable_mem_instances {args} {return {{0 100 16 a b GRAB}}}
proc start_insystem_source_probe {args} {}
proc end_insystem_source_probe {} {}
proc read_probe_data {args} {return 000000000000000000100}
proc read_source_data {args} {return 0}
proc begin_memory_edit {args} {}
proc end_memory_edit {} {}
proc read_content_from_memory {args} {
    set start [lindex $args [expr {[lsearch $args -start_address] + 1}]]
    set count [lindex $args [expr {[lsearch $args -word_count] + 1}]]
    set words {4752 4142 0001 0001 0001 0001 0000 0000 0000}
    return [join [lreverse [lrange $words $start [expr {$start + $count - 1}]]] ""]
}
set argv [list OUT --held --python PYTHON --mvfp 0x07]
source SCRIPT
"""
            devices = "{{@2: 5CSEMA5 (0x02D120DD)} {@3: 5CSEMA5 (0x02D120DD)}}" if duplicate else "{{@2: 5CSEMA5 (0x02D120DD)}}"
            fixture = fixture.replace("DEVICE_LIST", devices).replace("OUT", "{" + out.as_posix() + "}")
            fixture = fixture.replace("PYTHON", "{" + Path(sys.executable).as_posix() + "}")
            fixture = fixture.replace("SCRIPT", "{" + (echo7.ROOT / "tools/tcl/grab_jtag.tcl").as_posix() + "}")
            script.write_text(fixture)
            result = subprocess.run([tool, "-t", str(script)], cwd=root, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout + result.stderr

    def testTwoTargetsAreRejected(self):
        code, output = self.invoke(True)
        self.assertNotEqual(code, 0, output)
        self.assertIn("expected one selected", output)

    def testDecoderBadCrcIsNonzero(self):
        code, output = self.invoke(False)
        self.assertNotEqual(code, 0, output)
        self.assertIn("CRC error", output)
        self.assertIn("grab.py failed", output)


if __name__ == "__main__":
    unittest.main()
