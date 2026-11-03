"""Execute production BCTL Tcl against a transport double, not a real FPGA."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools"))
import echo7


class BctlTclTests(unittest.TestCase):
    def invoke(self,schema=3,brokenBusy=False):
        tool=echo7.discover("quartus_sh")
        # A fresh export has no generated build directory. This test owns its
        # scratch parent; it must not depend on an earlier CLI/test creating it.
        echo7.WORK.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=echo7.WORK,prefix="bctl_tcl_") as folder:
            script=Path(folder)/"driver.tcl"
            fixture=r'''
rename load_package real_load_package
proc load_package {args} {}
proc get_hardware_names {} {return {fixtureCable}}
proc get_device_names {args} {return {fixtureDevice}}
proc get_insystem_source_probe_instance_info {args} {return {{0 32 128 BCTL}}}
proc start_insystem_source_probe {args} {}
proc end_insystem_source_probe {} {}
proc bits {value width} {
    set result ""
    for {set i [expr {$width-1}]} {$i>=0} {incr i -1} {append result [expr {($value>>$i)&1}]}
    return $result
}
set ::source 0
set ::ack 0
set ::error 0
set ::reason 0
set ::freeze 0
set ::armCount 0
proc read_source_data {args} {return [bits $::source 32]}
proc write_source_data {args} {
    set binary [lindex $args [expr {[lsearch $args -value]+1}]]
    set value 0
    foreach bit [split $binary ""] {set value [expr {($value<<1)|$bit}]}
    set ::source $value
    set toggle [expr {($value>>31)&1}]
    if {$toggle!=$::ack} {
        set ::ack $toggle
        set ::error 0;set ::reason 0
        set opcode [expr {($value>>24)&15}]
        if {$opcode==5} {incr ::freeze}
        if {$opcode==3} {
            incr ::armCount
            if {$::armCount==2 && !BROKEN_BUSY} {set ::error 1;set ::reason 2}
        }
    }
}
proc read_probe_data {args} {
    set address [expr {($::source>>8)&255}]
    set word 0
    switch $address {
        0 {set word 0x45425031}
        1 {set word [expr {(SCHEMA<<16)|2}]}
        2 {set word [expr {$::freeze*40000}]}
        3 {set word $::freeze}
        6 {set word [expr {$::freeze>=3 ? 2 : 1}]}
        12 {set word [expr {$::freeze==2 ? 2640 : 304}]}
        89 {set word [expr {$::freeze>=3 ? 8 : 1}]}
        92 {set word 0x12345678}
    }
    set meta [expr {(SCHEMA<<24)|(2<<16)|($::ack<<15)|($::error<<14)|($::reason<<12)|96}]
    return "[bits 0x42444247 32][bits 0x12345678 32][bits $meta 32][bits $word 32]"
}
set argv [list calibration-check fixtureCable fixtureDevice [expr {3<<24}]]
source SCRIPT
'''
            fixture=fixture.replace('SCHEMA',str(schema)).replace('BROKEN_BUSY',str(int(brokenBusy)))
            fixture=fixture.replace('SCRIPT','{'+(echo7.ROOT/'tools/tcl/jtag_control.tcl').as_posix()+'}')
            script.write_text(fixture,encoding='utf-8')
            result=subprocess.run([tool,'-t',str(script)],capture_output=True,text=True,timeout=30)
            return result.returncode,result.stdout+result.stderr

    def testAcceptedThenBusyRejectedAndTraceCompletes(self):
        code,output=self.invoke()
        self.assertEqual(code,0,output)
        self.assertIn('ECHO7_BUSY_ACTION',output)
        self.assertEqual(output.count('ECHO7_CAL_TRACE\t'),3)
        self.assertEqual(output.count('ECHO7_WORD\t'),96)

    def testWrongBusyAcceptanceIsNonzero(self):
        code,output=self.invoke(brokenBusy=True)
        self.assertNotEqual(code,0,output)
        self.assertIn('busy arm did not return BUSY_OR_DISABLED',output)

    def testOldSchemaRejectedBeforeAnyArm(self):
        code,output=self.invoke(schema=2)
        self.assertNotEqual(code,0,output)
        self.assertIn('requires BCTL schema3 action acceptance',output)
        self.assertNotIn('ECHO7_ACTION\t',output)


if __name__=='__main__':unittest.main()
