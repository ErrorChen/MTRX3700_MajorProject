"""Host/Tcl protocol tests with synthetic GCTL, never camera hardware evidence."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib")]
import echo7
from capture_transaction import validateSnapshotTransaction, validateFrameProgress

TARGET = {"cable": "mockCable", "device": "@2: 5CSEMA5 (0x02D120DD)", "index": 2}


def metadata(held=False, count=17):
    before = {"count": count, "ack": 0, "busy": 0, "ready": 1, "mode": 0, "source": 0}
    accepted = deepcopy(before)
    if not held:
        accepted.update(count=(count + 1) & 0xffff, ack=1, source=1)
    return {"schema": "echo7-snapshot-transaction-v1", "mode": "held" if held else "fresh",
            "verified": True, "target": {k: TARGET[k] for k in ("cable", "device")},
            "requestBefore": before, "requestedToggle": None if held else 1,
            "accepted": accepted, "readBefore": deepcopy(accepted), "readAfter": deepcopy(accepted),
            "startedHostMs": 1000, "acceptedHostMs": 1100, "readStartedHostMs": 1200,
            "readFinishedHostMs": 1300, "memoryWords": 8}


class SnapshotHostTests(unittest.TestCase):
    def testFreshAndCounterWrap(self):
        for count in (17, 65535):
            result = validateSnapshotTransaction(metadata(count=count), TARGET, False, 16)
            self.assertTrue(result["fresh"])
            self.assertEqual(result["countDelta"], 1)

    def testHeldCannotBecomeFreshEvidence(self):
        self.assertFalse(validateSnapshotTransaction(metadata(True), TARGET, True, 16)["fresh"])
        with self.assertRaisesRegex(RuntimeError, "mode mismatch"):
            validateSnapshotTransaction(metadata(True), TARGET, False, 16)

    def testWrongAckUnchangedCountAndReplacedSnapshot(self):
        cases = []
        bad = metadata()
        for name in ("accepted", "readBefore", "readAfter"):
            bad[name]["ack"] = 0
        cases.append(bad)
        bad = metadata()
        for name in ("accepted", "readBefore", "readAfter"):
            bad[name]["count"] = bad["requestBefore"]["count"]
        cases.append(bad)
        bad = metadata(); bad["readAfter"]["count"] += 1; cases.append(bad)
        bad = metadata(); bad["target"]["cable"] = "another FPGA"; cases.append(bad)
        bad = metadata(); bad["verified"] = False; cases.append(bad)
        for bad in cases:
            with self.subTest(metadata=bad), self.assertRaises(RuntimeError):
                validateSnapshotTransaction(bad, TARGET, False, 16)

    def testShortRepeatBackwardsAndNativeWrap(self):
        previous = {"target": TARGET, "programmingEpoch": "epoch", "hostObservedMs": 1000, "frameId": 65535}
        result = validateFrameProgress(0, previous, TARGET, "epoch", 1200)
        self.assertEqual(result["nativeFrameDelta"], 1)
        for frame in (65535, 65534):
            with self.assertRaisesRegex(RuntimeError, "short comparison interval"):
                validateFrameProgress(frame, previous, TARGET, "epoch", 1200)

    def testLongIdleHalfWrapIsIndeterminateNotStale(self):
        previous = {"target": TARGET, "programmingEpoch": "epoch", "hostObservedMs": 1000, "frameId": 100}
        for frame in (40000, 100):
            result = validateFrameProgress(frame, previous, TARGET, "epoch", 7_200_000)
            self.assertEqual(result["comparison"], "INTERVAL_OUTSIDE_MODULAR_COMPARISON_WINDOW")
        previous.pop("hostObservedMs")
        self.assertEqual(validateFrameProgress(100, previous, TARGET, "epoch", 1200)["comparison"],
                         "HISTORY_HAS_NO_HOST_INTERVAL")


class SnapshotTclTests(unittest.TestCase):
    """Run the real transport Tcl in Quartus with deterministic API replacements."""
    def invoke(self, scenario, held=False, count=17):
        try:
            tool = echo7.discover("quartus_sh")
        except echo7.Blocked:
            self.skipTest("Quartus Tcl interpreter unavailable")
        echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="snapshot_test_", dir=echo7.WORK) as folder:
            local = Path(folder)
            out = local / "out"
            fixture = r'''
rename load_package real_load_package
proc load_package {args} {}
rename clock realClock
set fakeMs 100000
proc clock {args} {
    if {[lindex $args 0] eq "milliseconds"} {incr ::fakeMs 100;return $::fakeMs}
    return [realClock {*}$args]
}
set scenario SCENARIO
set snapshotCount COUNT
set ack 0;set request 0
proc get_hardware_names {} {return {mockCable}}
proc get_device_names {args} {return {{@2: 5CSEMA5 (0x02D120DD)}}}
proc get_insystem_source_probe_instance_info {args} {return {{0 1 21 GCTL}}}
proc get_editable_mem_instances {args} {return {{0 100 16 a b GRAB}}}
proc start_insystem_source_probe {args} {}
proc end_insystem_source_probe {} {}
proc read_source_data {args} {return $::request}
proc read_probe_data {args} {
    set bits ""
    for {set i 15} {$i>=0} {incr i -1} {append bits [expr {($::snapshotCount>>$i)&1}]}
    return "${bits}${::ack}0100"
}
proc write_source_data {args} {
    set ::request [lindex $args [expr {[lsearch $args -value]+1}]]
    if {$::scenario ne "unchanged"} {set ::snapshotCount [expr {($::snapshotCount+1)&65535}]}
    if {$::scenario ne "bad_ack"} {set ::ack $::request}
}
proc begin_memory_edit {args} {}
proc end_memory_edit {} {}
proc read_content_from_memory {args} {
    set start [lindex $args [expr {[lsearch $args -start_address]+1}]]
    set count [lindex $args [expr {[lsearch $args -word_count]+1}]]
    set words {4752 4142 0001 0001 0001 0001 0000 0000 0000}
    if {$::scenario eq "replace"} {incr ::snapshotCount}
    return [join [lreverse [lrange $words $start [expr {$start+$count-1}]]] ""]
}
# Only transport bookkeeping is under test here; test_tools separately executes
# the actual decoder and proves bad CRC failure propagates out of this script.
rename exec realExec
proc exec {args} {return MOCK_DECODER}
set argv [list OUT --python PYTHON --mvfp 0x07 HELD]
source SCRIPT
'''
            fixture = fixture.replace("SCENARIO", "{" + scenario + "}").replace("COUNT", str(count))
            fixture = fixture.replace("OUT", "{" + out.as_posix() + "}").replace("HELD", "--held" if held else "")
            fixture = fixture.replace("PYTHON", "{" + Path(sys.executable).as_posix() + "}")
            fixture = fixture.replace("SCRIPT", "{" + (ROOT / "tools/tcl/grab_jtag.tcl").as_posix() + "}")
            driver = local / "driver.tcl";driver.write_text(fixture)
            run = subprocess.run([tool, "-t", str(driver)], cwd=local, capture_output=True, text=True, timeout=30)
            path = out / "snapshot_metadata.json"
            result = json.loads(path.read_text()) if path.exists() else None
            return run.returncode, run.stdout + run.stderr, result

    def testActualTclFreshHeldAndCountWrap(self):
        for held, count in ((False, 17), (True, 17), (False, 65535)):
            with self.subTest(held=held, count=count):
                code, output, result = self.invoke("ok", held, count)
                self.assertEqual(code, 0, output)
                self.assertIsNotNone(result, output)
                validated = validateSnapshotTransaction(result, TARGET, held, 18)
                self.assertEqual(validated["fresh"], not held)
                self.assertEqual(result["readBefore"], result["readAfter"])

    def testActualTclRejectsBadAckUnchangedCountAndReadReplacement(self):
        for scenario in ("bad_ack", "unchanged", "replace"):
            with self.subTest(scenario=scenario):
                code, output, result = self.invoke(scenario)
                self.assertNotEqual(code, 0, output)
                self.assertIsNotNone(result, output)
                self.assertFalse(result["verified"])
                self.assertIn("snapshot", result["reason"])


if __name__ == "__main__":
    unittest.main()
