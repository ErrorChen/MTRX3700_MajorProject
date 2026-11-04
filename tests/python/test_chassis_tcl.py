"""Execute production CCTL Tcl with a transport double, never a live FPGA."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import echo7


class ChassisTclTests(unittest.TestCase):
    def invoke(self, build_id=0xe7070011):
        tool = echo7.discover("quartus_sh")
        echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=echo7.WORK, prefix="cctl_tuning_tcl_") as folder:
            folder = Path(folder)
            response = folder / "responses.txt"
            driver = folder / "driver.tcl"
            fixture = r'''
rename load_package real_load_package
proc load_package {args} {}
proc get_insystem_source_probe_instance_info {args} {return {{0 64 128 CCTL}}}
proc start_insystem_source_probe {args} {}
proc end_insystem_source_probe {} {}
set ::source 0
set ::ack 0
set ::writes {}
proc read_source_data {args} {return [bits $::source 64]}
proc write_source_data {args} {
    set binary [lindex $args [expr {[lsearch $args -value]+1}]]
    set ::source [number $binary]
    set toggle [expr {($::source >> 63) & 1}]
    if {$toggle != $::ack} {
        set ::ack $toggle
        lappend ::writes [expr {($::source >> 56) & 15}]
    }
}
proc read_probe_data {args} {
    set meta [expr {(1 << 24) | (16 << 16) | ($::ack << 15)}]
    return "[bits 0x4343544c 32][bits BUILD_ID 32][bits $meta 32][bits 0 32]"
}
set argv [list fixtureCable fixtureDevice RESPONSE]
source SCRIPT
set trace [open TRACE w]
puts $trace $::writes
close $trace
'''
            fixture = fixture.replace("BUILD_ID", str(build_id))
            for key, path in (("RESPONSE", response), ("TRACE", folder / "writes.txt"),
                              ("SCRIPT", echo7.ROOT / "tools/tcl/chassis_session.tcl")):
                fixture = fixture.replace(key, "{" + path.as_posix() + "}")
            driver.write_text(fixture, encoding="utf-8")
            run = subprocess.run([tool, "-t", str(driver)], input="1\tTX\t11\t1979716\n2\tTX\t12\t0\n3\tQUIT\n",
                                 text=True, capture_output=True, timeout=20)
            replies = response.read_text(encoding="utf-8") if response.exists() else ""
            trace = (folder / "writes.txt").read_text() if (folder / "writes.txt").exists() else ""
            return run.returncode, replies, trace, run.stdout + run.stderr

    def test_actual_build_id_and_new_tune_opcode_round_trip(self):
        code, replies, trace, log = self.invoke()
        self.assertEqual(code, 0, log)
        self.assertIn("CCTL_OK\t1\t0", replies)
        self.assertIn("CCTL_ERROR\t2\tinvalid TX arguments", replies)
        self.assertIn("CCTL_OK\t3\tBYE", replies)
        self.assertEqual(trace.strip(), "11")

    def test_unknown_build_family_rejected_before_any_write(self):
        code, replies, trace, log = self.invoke(0x12340011)
        self.assertEqual(code, 0, log)
        self.assertIn("CCTL_ERROR\t1\tunsupported CCTL", replies)
        self.assertEqual(trace.strip(), "")


if __name__ == "__main__": unittest.main()
