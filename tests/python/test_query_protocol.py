"""Public-v3 host and real Tcl-interpreter checks using synthetic API doubles.

These packets exercise framing and identities, not recognition or physical JTAG.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
import echo7
from contract_model import FIELD_LAYOUTS, packPayload
from debug_decode import decodeGrabWords, decodeQueryWords, decodeWords
from query_transport import markerSelector, parseQueryStream
from test_raw_camera_mode import BUILD, fixture, setReport


def queryPacket(index=0, count=1, *, markerType=1, digit=1, reason=None, **updates):
    fields = {name: 0 for name, _ in FIELD_LAYOUTS["queryResult"]}
    fields.update(requestTag=0x7788, frameId=0xffff, captureStartUs=0xfffffff0,
                  configVersion=3, reason=(0 if count else 2) if reason is None else reason,
                  count=count, index=index, last=int(index == max(0, count-1)),
                  markerType=markerType if count else 0, digit=digit if count else 15,
                  centreU=100 if count else 0, centreV=150 if count else 0,
                  boxWidth=12 if count else 0, boxHeight=30 if count else 0, quality=200 if count else 0)
    fields.update(updates)
    payload = packPayload("queryResult", fields)
    return [0x51525033, *[(payload >> (32*index)) & 0xffffffff for index in range(5)], BUILD, 0x00000308]


def queryText(packets, *, opcode=8, drained=()):
    meta = 0x08038060
    header = f"{0x42444247:032b}{BUILD:032b}{meta:032b}"
    lines = [f"ECHO7_QUERY_SESSION\t{header}"]
    serial = 0
    for phase, group in (("DRAIN", drained), ("RESULT", packets)):
        if phase == "RESULT" and opcode:
            lines.append(f"ECHO7_QUERY_ACTION\t{opcode}\t{meta:032b}")
        for packet in group:
            lines += [f"ECHO7_QUERY_BEGIN\t{serial}\t{phase}", f"ECHO7_QUERY_HEADER\t{serial}\t{header}"]
            lines += [f"ECHO7_QUERY_WORD\t{serial}\t{index}\t{word:032b}" for index, word in enumerate(packet)]
            lines += [f"ECHO7_QUERY_END\t{serial}"]
            serial += 1
    lines.append(f"ECHO7_QUERY_DONE\t{opcode}\t{len(drained)}\t{len(packets)}\t123")
    return "\n".join(lines) + "\n"


class QueryHostTests(unittest.TestCase):
    def testSchema8TypedReportAndLegacyWidthsAreNeverConflated(self):
        words = fixture(8)
        words[88] = packPayload("targetRequest", dict(operation=1, requestTag=0x3344, markerType=2, digit=1))
        setReport(words, requestTag=0x3344, markerType=2, digit=1, targetSelected=1,
                  observed=1, locked=1, centreU=100, centreV=160, boxWidth=12, boxHeight=30, quality=200)
        words[90] = 1 << 16
        result = decodeGrabWords(words, BUILD)
        self.assertEqual(result["contractVersion"], 3)
        self.assertEqual(result["targetReport"]["markerType"], 2)
        self.assertEqual(result["targetReport"]["digit"], 1)
        self.assertNotIn("bayId", result["targetReport"])
        self.assertTrue(result["queryBusy"])
        self.assertEqual(result["activeRequest"]["requestTag"], 0x3344)
        old = decodeGrabWords(fixture(7), BUILD)
        self.assertIn("bayId", old["targetReport"])
        for value in (0x00080002, 0x00070003, 0x00090003):
            broken = words.copy(); broken[1] = value
            with self.assertRaises(ValueError): decodeWords(broken[:-2])
        broken = words.copy(); broken[90] |= 1 << 17
        with self.assertRaisesRegex(ValueError, "reserved"): decodeWords(broken[:-2])

    def testQuery141BitPacketAndAllFiveEmptyReasons(self):
        decoded = decodeQueryWords(queryPacket(markerType=3, digit=15), BUILD)
        self.assertEqual(decoded["markerType"], 3)
        self.assertEqual(decoded["digit"], 15)
        self.assertEqual(decoded["captureStartUs"], 0xfffffff0)
        self.assertEqual(decoded["requestTag"], 0x7788)
        for reason in range(2, 7):
            result = decodeQueryWords(queryPacket(count=0, reason=reason))
            self.assertEqual((result["count"], result["index"], result["last"], result["markerType"], result["digit"]), (0, 0, 1, 0, 15))
        for update in (dict(count=17), dict(count=0, centreU=1), dict(count=0, last=0),
                       dict(reason=7), dict(reason=1), dict(markerType=2, digit=6),
                       dict(markerType=3, digit=1), dict(centreV=320), dict(boxHeight=0)):
            with self.subTest(update=update), self.assertRaises(ValueError): decodeQueryWords(queryPacket(**update))
        for offset, value in ((0, 0x45425031), (5, 1 << 13), (6, BUILD+1), (7, 0x00000207)):
            broken = queryPacket(); broken[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ValueError): decodeQueryWords(broken, BUILD)

    def testListSixteenAndDuplicateGetAreCompleteAndTyped(self):
        packets = [queryPacket(index, 16, digit=index % 6 + 1) for index in range(16)]
        result = parseQueryStream(queryText(packets), 8)
        self.assertEqual(len(result["items"]), 16)
        self.assertTrue(result["completed"])
        self.assertEqual(result["transportCompletion"]["resultCount"], 16)
        duplicate = [queryPacket(index, 2, markerType=2, digit=1, reason=1, centreU=50+index*30) for index in range(2)]
        result = parseQueryStream(queryText(duplicate, opcode=9), 9, (2, 1))
        self.assertEqual([item["centreU"] for item in result["items"]], [50, 80])
        with self.assertRaisesRegex(ValueError, "identity"):
            parseQueryStream(queryText(duplicate, opcode=9), 9, (1, 1))
        self.assertEqual(parseQueryStream(queryText([queryPacket(count=0)], opcode=9), 9, (3, 15))["items"], [])

    def testAbandonedTailDrainDoesNotReplaceCurrentResponse(self):
        abandoned = [queryPacket(index, 3, requestTag=3, digit=2) for index in (1, 2)]
        result = parseQueryStream(queryText([queryPacket(markerType=3, digit=15)], drained=abandoned), 8)
        self.assertEqual([row["index"] for row in result["drainedReplies"]], [1, 2])
        self.assertEqual(result["items"][0]["markerType"], 3)
        drained = parseQueryStream(queryText([], opcode=0, drained=abandoned), 0)
        self.assertEqual(drained["items"], [])
        self.assertIsNone(drained["commandAcceptance"])

    def testSequenceCorruptionAndIncompleteSuccessAreRejected(self):
        packets = [queryPacket(index, 2) for index in range(2)]
        for field, value in (("requestTag", 7), ("frameId", 0), ("captureStartUs", 8), ("configVersion", 4)):
            broken = [packets[0], queryPacket(1, 2, **{field: value})]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "sequence"):
                parseQueryStream(queryText(broken), 8)
        text = queryText(packets)
        mutations = [text.replace("ECHO7_QUERY_DONE", "HIDDEN_DONE"),
                     text.replace("ECHO7_QUERY_WORD\t0\t3", "ECHO7_QUERY_WORD\t0\t2"),
                     text.replace("ECHO7_QUERY_DONE\t8\t0\t2", "ECHO7_QUERY_DONE\t8\t0\t1"),
                     text.replace("ECHO7_QUERY_ACTION\t8", "ECHO7_QUERY_ACTION\t9"),
                     queryText(packets[1:]), queryText([queryPacket(0, 2)])]
        for broken in mutations:
            with self.assertRaises(ValueError): parseQueryStream(broken, 8)

    def testUserIdentityValidationPreventsWrongTypeAndUnsupportedDigits(self):
        self.assertEqual(markerSelector("reference"), (3, 15))
        self.assertEqual(markerSelector("bay", 6), (1, 6))
        self.assertEqual(markerSelector("function", 2), (2, 2))
        for kind, digit in (("bay", 0), ("bay", 7), ("function", 3), ("reference", 1), ("none", 1), ("bay", True)):
            with self.assertRaises(ValueError): markerSelector(kind, digit)

    def testCliQueryUsesOneActualTransportInvocationAndClientPreservesFailure(self):
        runner = object.__new__(echo7.Runner)
        runner.args = type("Args", (), {"timeout": 30})()
        runner.result = {}
        runner.target = lambda: {"cable": "SYNTHETIC", "device": "SYNTHETIC"}
        runner.qt = lambda name: "SYNTHETIC_TRANSPORT"
        runner.run = Mock(return_value=(0, queryText([queryPacket(markerType=2)], opcode=9)))
        runner.query(9, (2, 1))
        self.assertEqual(runner.run.call_count, 1)
        args = runner.run.call_args.args[1]
        self.assertIn("query-stream", args)
        self.assertEqual(args[-2], str((9 << 24) | 0x21))
        self.assertEqual(runner.result["queryTransaction"]["items"][0]["markerType"], 2)
        runner.run = Mock(return_value=(1, "partial packets retained in log"))
        with self.assertRaisesRegex(RuntimeError, "markers --drain"): runner.query(8)

    def testImportableClientRunsTheSameTransactionsAndRetainsFailure(self):
        from member_b_client import MemberBClient, MemberBClientError
        realRunner = echo7.Runner
        runners = []
        response = [0, queryText([queryPacket(markerType=2)], opcode=9)]
        with tempfile.TemporaryDirectory(prefix="query_client_") as folder:
            def factory(args):
                runner = object.__new__(realRunner)
                runner.args, runner.out, runner.result = args, Path(folder), {}
                runner.target = lambda: {"cable": "SYNTHETIC", "device": "SYNTHETIC"}
                runner.qt = lambda name: "SYNTHETIC_TRANSPORT"
                runner.run = Mock(side_effect=lambda *args, **kwargs: tuple(response))
                runners.append(runner)
                return runner
            with patch("echo7.Runner", side_effect=factory):
                result = MemberBClient().locate("function", 1)
                self.assertEqual(result["queryTransaction"]["items"][0]["markerType"], 2)
                self.assertEqual(runners[-1].run.call_count, 1)
                self.assertEqual(runners[-1].run.call_args.args[1][-2], str((9 << 24) | 0x21))
                response[:] = [1, "transport failure"]
                with self.assertRaises(MemberBClientError) as caught:
                    MemberBClient().markers()
                self.assertEqual(caught.exception.result["exitCode"], 1)
                retained = json.loads((Path(folder) / "result.json").read_text())
                self.assertEqual(retained["status"], "FAIL")
                self.assertIn("markers --drain", retained["queryRecoveryCommand"])
                count = len(runners)
                with self.assertRaises(ValueError): MemberBClient().track("function", 6)
                self.assertEqual(len(runners), count)


class QueryTclTests(unittest.TestCase):
    def invoke(self, *, opcode=8, packets=None, old=(), stuck=False, digit=1, markerType=1):
        packets = [queryPacket()] if packets is None else packets
        echo7.WORK.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="query_tcl_", dir=echo7.WORK) as folder:
            path = Path(folder) / "fixture.tcl"
            code = r'''
rename load_package real_load_package
proc load_package {args} {}
rename clock realClock
set fakeMs 0
proc clock {args} {
    if {[lindex $args 0] eq "milliseconds"} {incr ::fakeMs 10;return $::fakeMs}
    return [realClock {*}$args]
}
proc get_hardware_names {} {return {fixtureCable}}
proc get_device_names {args} {return {fixtureDevice}}
proc get_insystem_source_probe_instance_info {args} {return {{0 32 128 BCTL}}}
proc start_insystem_source_probe {args} {}
proc end_insystem_source_probe {} {puts "FIXTURE_COMMANDS\t$::commands"}
proc bits {value width} {
    set result ""
    for {set i [expr {$width-1}]} {$i>=0} {incr i -1} {append result [expr {($value>>$i)&1}]}
    return $result
}
set ::source 0;set ::meta 0x08030060;set ::words {0 0 0 0 0 0 0 0}
set ::queue {OLD};set ::newPackets {PACKETS};set ::scan 0;set ::commands 0;set ::stuck STUCK
proc read_source_data {args} {return [bits $::source 32]}
proc write_source_data {args} {
    set binary [lindex $args [expr {[lsearch $args -value]+1}]]
    set value 0
    foreach bit [split $binary ""] {set value [expr {($value<<1)|$bit}]}
    set changed [expr {(($value ^ $::source) & 0x80000000) != 0}]
    set ::source $value
    if {!$changed} {return}
    set ::meta [expr {0x08030060|((($value>>31)&1)<<15)}]
    set opcode [expr {($value>>24)&15}]
    if {$opcode in {8 9}} {
        if {[llength $::queue] || $::scan} {error "new query overwrote undrained reply"}
        incr ::commands
        set ::scan 2
    } elseif {$opcode == 10} {
        if {[llength $::queue]} {
            set ::words [lindex $::queue 0]
            set ::queue [lrange $::queue 1 end]
            set ::meta [expr {$::meta|0x100}]
        } else {
            set busy [expr {$::scan>0 || $::stuck}]
            set ::meta [expr {$::meta|0x6000|($busy<<8)}]
            if {$::scan>0} {
                incr ::scan -1
                if {$::scan==0} {set ::queue $::newPackets}
            }
        }
    } else {error "fixture unexpected command"}
}
proc read_probe_data {args} {
    set word [lindex $::words [expr {($::source>>8)&255}]]
    return "[bits 0x42444247 32][bits 0x12345678 32][bits $::meta 32][bits $word 32]"
}
set argv [list query-stream fixtureCable fixtureDevice COMMAND DEADLINE]
source SCRIPT
'''
            asTcl = lambda rows: " ".join("{" + " ".join(str(word) for word in row) + "}" for row in rows)
            command = 0 if opcode == 0 else (opcode << 24) | ((markerType << 4) | digit if opcode == 9 else 0)
            code = code.replace("OLD", asTcl(old)).replace("PACKETS", asTcl(packets)).replace("STUCK", str(int(stuck)))
            code = code.replace("COMMAND DEADLINE", f"{command} {1 if stuck else 30}")
            code = code.replace("SCRIPT", "{" + (ROOT / "tools/tcl/jtag_control.tcl").as_posix() + "}")
            path.write_text(code, encoding="utf-8")
            completed = subprocess.run([echo7.discover("quartus_sh"), "-t", str(path)], capture_output=True, text=True, timeout=30)
            return completed.returncode, completed.stdout + completed.stderr

    def testActualTclDrainsOldTailAndReadsAllSixteenInOneSession(self):
        old = [queryPacket(index, 3, requestTag=2) for index in (1, 2)]
        packets = [queryPacket(index, 16, digit=index % 6+1) for index in range(16)]
        code, output = self.invoke(old=old, packets=packets)
        self.assertEqual(code, 0, output)
        result = parseQueryStream(output, 8)
        self.assertEqual(len(result["drainedReplies"]), 2)
        self.assertEqual(len(result["items"]), 16)
        self.assertIn("FIXTURE_COMMANDS\t1", output)
        self.assertEqual(output.count("ECHO7_QUERY_BEGIN"), 18)

    def testActualTclGetAndEmptyAndDrainOnly(self):
        cases = [(9, [queryPacket(index, 2, markerType=2, reason=1) for index in range(2)], (2, 1)),
                 (9, [queryPacket(count=0, reason=3)], (3, 15)),
                 (0, [], None)]
        for opcode, packets, identity in cases:
            with self.subTest(opcode=opcode, identity=identity):
                code, output = self.invoke(opcode=opcode, packets=packets,
                    markerType=identity[0] if identity else 1, digit=identity[1] if identity else 1)
                self.assertEqual(code, 0, output)
                result = parseQueryStream(output, opcode, identity)
                self.assertEqual(len(result["results"]), len(packets))

    def testActualTclPendingOldQueryTimesOutWithoutEnqueue(self):
        code, output = self.invoke(stuck=True)
        self.assertNotEqual(code, 0)
        self.assertIn("query timeout", output)
        self.assertIn("FIXTURE_COMMANDS\t0", output)
        self.assertNotIn("ECHO7_QUERY_ACTION", output)
        self.assertNotIn("ECHO7_QUERY_DONE", output)


if __name__ == "__main__":
    unittest.main()
