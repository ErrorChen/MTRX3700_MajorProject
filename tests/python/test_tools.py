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
import unittest

import echo7


class TimingGateTests(unittest.TestCase):
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
    def testOwnedProcessTimeoutIsNonzeroAndRecorded(self):
        args = argparse.Namespace(command="timeout_selftest", timeout=1)
        runner = echo7.Runner(args)
        code, output = runner.run("sleeping_child", [sys.executable, "-c", "import time; print('started',flush=True); time.sleep(10)"], checked=False)
        self.assertEqual(code, 124)
        self.assertEqual(runner.result["steps"][0]["returncode"], 124)
        self.assertLess(runner.result["steps"][0]["elapsedSeconds"], 8)
        self.assertIn("timed out", output)


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
