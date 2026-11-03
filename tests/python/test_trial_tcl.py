"""Run the maintained single-session trial Tcl against a transport double.

This exercises the real Tcl parser/loops/header gates. It neither connects to
JTAG nor measures hardware speed. The double removes transport sleeps.
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
import echo7


class TrialTclTests(unittest.TestCase):
    def invoke(self, trials=1, corruptHeader=False, reverseFrame=False, typed=False):
        tool = echo7.discover('quartus_sh')
        with tempfile.TemporaryDirectory(dir=echo7.WORK, prefix='trial_tcl_') as folder:
            script = Path(folder) / 'driver.tcl'
            fixture = r'''
rename load_package real_load_package
proc load_package {args} {}
rename after real_after
proc after {args} {}
proc get_hardware_names {} {return {fixtureCable}}
proc get_device_names {args} {return {fixtureDevice}}
proc get_insystem_source_probe_instance_info {args} {return {{0 32 128 BCTL}}}
proc start_insystem_source_probe {args} {puts FIXTURE_SESSION_STARTED}
proc end_insystem_source_probe {} {puts FIXTURE_SESSION_ENDED}
proc bits {value width} {
    set result ""
    for {set i [expr {$width-1}]} {$i>=0} {incr i -1} {append result [expr {($value>>$i)&1}]}
    return $result
}
set ::source 0
set ::ack 0
set ::bay 0
set ::tag 0
set ::frame 65530
set ::freeze 0
set ::sinceSelect 0
set ::report 0
set ::typed TYPED
proc read_source_data {args} {return [bits $::source 32]}
proc write_source_data {args} {
    set binary [lindex $args [expr {[lsearch $args -value]+1}]]
    set value 0
    foreach bit [split $binary ""] {set value [expr {($value<<1)|$bit}]}
    set ::source $value
    set toggle [expr {($value>>31)&1}]
    if {$toggle!=$::ack} {
        set ::ack $toggle
        set opcode [expr {($value>>24)&15}]
        if {$opcode==1} {
            if {$::typed && (($value>>4)&3)!=1} {error "typed trial did not select BLUE_BAY"}
            set ::bay [expr {$value&15}];incr ::tag;set ::sinceSelect 0
        }
        if {$opcode==2} {set ::bay 0;incr ::tag;puts FIXTURE_CLEAR_ACCEPTED}
        if {$opcode==5} {
            incr ::freeze;incr ::sinceSelect
            # One duplicate status, one old-request transition, one bad frame,
            # and native frame wrap are deliberate independent stimuli.
            if {!($::bay==1 && $::sinceSelect==4)} {set ::frame [expr {($::frame+1)&65535}]}
            if {REVERSE_FRAME && $::bay==1 && $::sinceSelect==5} {set ::frame [expr {($::frame-2)&65535}]}
            set reportTag [expr {$::bay==1 && $::sinceSelect==2 ? $::tag-1 : $::tag}]
            set ::report [expr {$::typed ? (($reportTag<<125)|($::frame<<109)|(($::bay ? 1 : 0)<<59)|(($::bay ? $::bay : 15)<<55)) :
                (($reportTag<<123)|($::frame<<107)|($::bay<<55))}]
        }
    }
}
proc read_probe_data {args} {
    set address [expr {($::source>>8)&255}]
    set word 0
    switch $address {
        0 {set word 0x45425031}
        1 {set word [expr {$::typed ? 0x00080003 : 0x00040002}]}
        2 {set word [expr {$::freeze*40000}]}
        3 {set word $::frame}
        6 {set word 1}
        88 {set word [expr {$::typed ? (($::bay!=0 ? (1<<22) : 0)|($::tag<<6)|(($::bay ? 1 : 0)<<4)|($::bay ? $::bay : 15)) :
            (($::bay!=0 ? (1<<20) : 0)|($::tag<<4)|$::bay)}]}
        91 {set word [expr {!($::bay==1 && $::sinceSelect==3)}]}
        92 {set word 0x12345678}
        93 {set word [expr {$::typed ? 0x01100f00 : ((8<<16)|(12<<8))}]}
        95 {set word [expr {$::typed ? 0x03055440 : 0}]}
    }
    if {$address>=13 && $address<=17} {set word [expr {($::report>>(32*($address-13)))&0xffffffff}]}
    set magic 0x42444247
    if {CORRUPT_HEADER && $::bay==1 && $::sinceSelect==2 && $address==17} {incr magic}
    set meta [expr {($::typed ? 0x08030000 : 0x04020000)|($::ack<<15)|96}]
    return "[bits $magic 32][bits 0x12345678 32][bits $meta 32][bits $word 32]"
}
set argv [list trial-stream fixtureCable fixtureDevice TRIALS 30]
source SCRIPT
'''
            fixture = fixture.replace('TRIALS', str(trials)).replace('CORRUPT_HEADER', str(int(corruptHeader)))
            fixture = fixture.replace('REVERSE_FRAME', str(int(reverseFrame)))
            fixture = fixture.replace('TYPED', str(int(typed)))
            fixture = fixture.replace('SCRIPT', '{' + (echo7.ROOT / 'tools/tcl/jtag_control.tcl').as_posix() + '}')
            script.write_text(fixture, encoding='utf-8')
            result = subprocess.run([tool, '-t', str(script)], capture_output=True, text=True, timeout=40)
            return result.returncode, result.stdout + result.stderr

    def testRetainsBadOldDuplicateAndWrapInOneSession(self):
        code, output = self.invoke()
        self.assertEqual(code, 0, output)
        self.assertEqual(output.count('FIXTURE_SESSION_STARTED'), 1)
        self.assertEqual(output.count('FIXTURE_SESSION_ENDED'), 1)
        begins = re.findall(r'^ECHO7_TRIAL_BEGIN\t(\d+)\t(\w+)\t(\d+)\t(\d+)$', output, re.M)
        self.assertEqual([int(row[0]) for row in begins], list(range(40)))
        self.assertEqual(begins[0], ('0', 'INITIAL', '0', '0'))
        self.assertEqual(begins[-1], ('39', 'CLEAR', '0', '0'))
        self.assertEqual(sum(row[1] == 'STATUS' for row in begins), 32)
        self.assertEqual(sum(row[1] == 'SELECT' for row in begins), 6)
        self.assertEqual(output.count('ECHO7_TRIAL_END\t'), 40)
        self.assertEqual(output.count('ECHO7_TRIAL_WORD\t'), 40 * 96)
        self.assertRegex(output, r'ECHO7_TRIAL_DONE\t1\t32\t\d+')
        statuses = [int(row[0]) for row in begins if row[1] == 'STATUS']
        words = {}
        for serial, address, bits in re.findall(r'^ECHO7_TRIAL_WORD\t(\d+)\t(\d+)\t([01]{32})$', output, re.M):
            words.setdefault(int(serial), {})[int(address)] = int(bits, 2)
        frames = [words[serial][3] for serial in statuses]
        self.assertEqual(frames[1], frames[2])
        self.assertIn(0, frames)
        self.assertEqual(words[statuses[1]][91], 0, 'bad current sample must remain in output')
        report = sum(words[statuses[0]][13+i] << (32*i) for i in range(5))
        self.assertEqual((report >> 123) & 65535, 0, 'old request transition must remain in output')

    def testThreeTrialsRemainBoundedAndComplete(self):
        code, output = self.invoke(trials=3)
        self.assertEqual(code, 0, output)
        self.assertEqual(output.count('FIXTURE_SESSION_STARTED'), 1)
        self.assertEqual(output.count('FIXTURE_CLEAR_ACCEPTED'), 1)
        self.assertRegex(output, r'ECHO7_TRIAL_DONE\t3\t96\t\d+')

    def testTypedV3TrialUsesActualRequestAndReportWirePositions(self):
        from trial_stream import parseTrialStream
        code, output = self.invoke(typed=True)
        self.assertEqual(code, 0, output)
        records, done = parseTrialStream(output, 0x12345678)
        self.assertEqual(done['statusRecords'], 32)
        selected = [row for row in records if row['phase'] == 'SELECT']
        self.assertEqual(len(selected), 6)
        for bay, row in enumerate(selected, 1):
            self.assertEqual(row['decoded']['contractVersion'], 3)
            self.assertEqual(row['decoded']['activeRequest']['markerType'], 1)
            self.assertEqual(row['decoded']['activeRequest']['digit'], bay)
            self.assertNotIn('bayId', row['decoded']['targetReport'])
        status = [row['decoded'] for row in records if row['phase'] == 'STATUS']
        self.assertEqual(status[0]['targetReport']['requestTag'], 0)
        self.assertEqual(status[0]['targetReport']['markerType'], 1)
        self.assertEqual(status[0]['targetReport']['digit'], 1)
        self.assertIn(0, [row['frameId'] for row in status])

    def testProductionPythonAssessorConsumesRealTclSequence(self):
        # Independent Python re-derives ordering and the denominator from the
        # actual maintained Tcl output. Deliberately bad frames still count.
        from trial_stream import parseTrialStream, TrialRecordReader
        from hardware_measurement import measureTrials
        code, output = self.invoke()
        self.assertEqual(code, 0, output)
        rows, done = parseTrialStream(output, 0x12345678)
        self.assertEqual(done['statusRecords'], 32)
        with tempfile.TemporaryDirectory(dir=echo7.WORK, prefix='trial_assessor_') as folder:
            runner = argparse.Namespace(args=argparse.Namespace(timeout=10), out=Path(folder), result={})
            reader = TrialRecordReader(runner, rows)
            with self.assertRaisesRegex(RuntimeError, '31 sampled observations failed'):
                measureTrials(reader, 1)
            self.assertEqual(reader.position, len(rows))
            self.assertEqual(runner.result['trials'][0]['currentRequestSamples'], 30)
            self.assertEqual(runner.result['trials'][0]['failedSamples'], 30)
            self.assertEqual(len(runner.result['observations']), 31)
            self.assertTrue(runner.result['clearSent'])

    def testCorruptHeaderFailsAndClears(self):
        code, output = self.invoke(corruptHeader=True)
        self.assertNotEqual(code, 0, output)
        self.assertIn('BCTL header changed during frozen status read', output)
        self.assertIn('FIXTURE_CLEAR_ACCEPTED', output)
        self.assertNotIn('ECHO7_TRIAL_DONE', output)

    def testBackwardFrameFailsAndClears(self):
        code, output = self.invoke(reverseFrame=True)
        self.assertNotEqual(code, 0, output)
        self.assertIn('native frame moved backwards', output)
        self.assertIn('FIXTURE_CLEAR_ACCEPTED', output)
        self.assertNotIn('ECHO7_TRIAL_DONE', output)

    def testInvalidCountRejectedBeforeSession(self):
        code, output = self.invoke(trials=4)
        self.assertNotEqual(code, 0, output)
        self.assertIn('requires 1..3 complete trials', output)
        self.assertNotIn('FIXTURE_SESSION_STARTED', output)


if __name__ == '__main__':
    unittest.main()
