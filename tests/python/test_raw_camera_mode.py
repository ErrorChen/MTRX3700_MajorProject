"""Host/schema/transport-double checks only; no real camera or VGA is exercised."""
import argparse
import binascii
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
import echo7
from contract_model import FIELD_LAYOUTS, packPayload
from debug_decode import decodeWords, decodeGrabWords, compareMarkerPixels, requireAlgorithmMode
from hardware_measurement import measureTrials
from test_hardware_measurement import FixtureRunner
from test_sw9_comparison import fixture as trialFixture
from compare_sw9_trials import compareTrials


BUILD = 0x12345678
RAW_FIELDS = ("rawCameraMode", "rawModeRequested", "rawDisplayActive")


def setReport(words, **updates):
    fields = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
    fields.update(frameId=9, captureStartUs=1000, configVersion=4)
    fields.update(updates)
    packed = packPayload("targetReport", fields)
    for i in range(5):
        words[13 + i] = (packed >> (32 * i)) & 0xffffffff


def fixture(schema=5, raw=False):
    count = 160 if schema == 6 else 96
    tail = count - 8
    words = [0] * (count + 2)
    words[0], words[1] = 0x45425031, (schema << 16) | 2
    words[2:8] = [20000, 9, 1000, 12000, 4, (33 << 8) | 28]
    words[tail+3], words[tail+4], words[count], words[count+1] = int(not raw), BUILD, 9, BUILD
    words[tail+7] = (160 << 8) | 64 if schema == 1 else (2 << 24) | ((5 if schema in (6, 7) else 4) << 16) | (84 << 8) | 64
    if schema >= 4:
        words[tail+5] = ((16 if schema in (6, 7) else 8) << 16) | (15 << 8) | ((1 << 24) if schema == 7 else 0)
    if raw:
        words[7] |= 0x00e00000
    setReport(words)
    return words


class RawCameraModeTests(unittest.TestCase):
    def testSchema5NormalAndRawExplicitlyDecode(self):
        for raw in (False, True):
            with self.subTest(raw=raw):
                decoded = decodeGrabWords(fixture(raw=raw), BUILD)
                self.assertEqual(decoded["debugSchemaVersion"], 5)
                self.assertEqual([decoded[key] for key in RAW_FIELDS], [raw] * 3)
                self.assertEqual(decoded["frameGood"], not raw)
                self.assertTrue(decoded["sameFrameVerified"])

    def testLegacySchemasHaveFalseRawFields(self):
        for schema in range(1, 5):
            with self.subTest(schema=schema):
                decoded = decodeWords(fixture(schema)[:96])
                self.assertEqual([decoded[key] for key in RAW_FIELDS], [False] * 3)
                requireAlgorithmMode(decoded)

    def testUnknownSchemaAndReservedBitsFail(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            decodeWords(fixture(8)[:96])
        for schema, bit in ((5, 16), (5, 17), (5, 24), (5, 31), (4, 21), (3, 22), (2, 20)):
            with self.subTest(schema=schema, bit=bit):
                words = fixture(schema)
                words[7] |= 1 << bit
                with self.assertRaisesRegex(ValueError, "reserved"):
                    decodeWords(words[:96])
        for schema, bit in ((5, 7), (5, 31), (4, 3), (3, 2)):
            with self.subTest(schema=schema, word=90, bit=bit):
                words = fixture(schema)
                words[90] |= 1 << bit
                with self.assertRaisesRegex(ValueError, "reserved"):
                    decodeWords(words[:96])

    def referenceWords(self):
        words = fixture()
        words[9] = 3 << 4
        words[90] = (2 << 4) | 8  # Blue candidate2, not digit2.
        at = 24 + (8 + 2) * 4
        words[at] = (1 << 30) | (15 << 24)
        words[at + 1] = (70 << 16) | 130
        words[at + 2] = (90 << 16) | 107
        return words

    def testCalibrationReferenceHasExplicitValidityNotInventedDigit(self):
        decoded = decodeWords(self.referenceWords()[:96])
        self.assertTrue(decoded["calibrationReferenceValid"])
        self.assertEqual(decoded["calibrationReferenceIndex"], 2)
        reference = decoded["markers"][10]
        self.assertFalse(reference["accepted"])
        self.assertEqual(reference["digit"], 15)
        words = self.referenceWords()
        words[90] &= ~8
        self.assertFalse(decodeWords(words[:96])["calibrationReferenceValid"])
        for schema in range(1, 5):
            decoded = decodeWords(fixture(schema)[:96])
            self.assertFalse(decoded["calibrationReferenceValid"])
            self.assertEqual(decoded["calibrationReferenceIndex"], 0)

    def testCalibrationReferenceRejectsBadFrameIndexBboxAndAcceptedBay(self):
        at = 24 + 10 * 4
        changes = ((91, 0), (9, 2 << 4), (at, (1 << 31) | (1 << 30) | (1 << 24)),
                   (at, 15 << 24), (at + 1, (319 << 16) | 320), (at + 2, (239 << 16) | 240))
        for index, value in changes:
            with self.subTest(index=index, value=value):
                words = self.referenceWords()
                words[index] = value
                with self.assertRaisesRegex(ValueError, "reference|bbox"):
                    decodeWords(words[:96])
        words = fixture(raw=True)
        words[90] |= 8
        with self.assertRaisesRegex(ValueError, "raw-camera completed"):
            decodeWords(words[:96])

    def testRawCompletedFrameCannotClaimRecognition(self):
        for field in ("frameGood", "redCount", "blueCount", "acceptedMarker"):
            with self.subTest(field=field):
                words = fixture(raw=True)
                if field == "frameGood": words[91] = 1
                elif field == "redCount": words[9] = 1
                elif field == "blueCount": words[9] = 16
                else: words[24] = (1 << 31) | (1 << 24) | (255 << 16)
                with self.assertRaisesRegex(ValueError, "raw-camera completed"):
                    decodeWords(words[:96])

    def testRawSwitchTimingBitsCanLegitimatelyDiffer(self):
        for flags in range(8):
            with self.subTest(flags=flags):
                words = fixture(raw=bool(flags & 1))
                words[7] = (words[7] & ~0x00e00000) | (flags << 21)
                decoded = decodeWords(words[:96])
                self.assertEqual([decoded[key] for key in RAW_FIELDS], [bool(flags & (1 << bit)) for bit in range(3)])
                if flags:
                    with self.assertRaisesRegex(RuntimeError, "RAW_CAMERA_MODE"):
                        requireAlgorithmMode(decoded)
                else:
                    requireAlgorithmMode(decoded)

    def testBctlAllowsHeldOldValidReportButGrabBindingStaysStrict(self):
        words = fixture(raw=True)
        setReport(words, frameId=7, observed=1, locked=1, frameGood=1,
                  centreU=20, centreV=30, boxWidth=40, boxHeight=50, quality=192)
        words[90] = 2  # Valid/ready payload may still be waiting for C.
        decoded = decodeWords(words[:96])
        self.assertEqual(decoded["targetReport"]["frameId"], 7)
        self.assertTrue(decoded["targetReport"]["observed"])
        self.assertFalse(decoded["frameGood"])
        with self.assertRaisesRegex(ValueError, "FRAME_MISMATCH"):
            decodeGrabWords(words, BUILD)

    def testRawGrabStillRejectsWrongFrameOrBuild(self):
        words = fixture(raw=True)
        words[96] += 1
        with self.assertRaisesRegex(ValueError, "FRAME_MISMATCH"):
            decodeGrabWords(words, BUILD)
        with self.assertRaisesRegex(ValueError, "buildId"):
            decodeGrabWords(fixture(raw=True), BUILD + 1)

    def testRawCaptureAssessmentSkipsPixelClassifiersWithoutVacuousPass(self):
        runner = object.__new__(echo7.Runner)
        runner.result = {"recognition": decodeWords(fixture(raw=True)[:96])}
        runner.out = Path("NOT_AN_IMAGE_DIRECTORY")
        runner.run = Mock(side_effect=AssertionError("raw capture must not run recognition model"))
        with patch("debug_decode.compareMarkerPixels", side_effect=AssertionError("raw capture must not classify pixels")):
            runner.assessCapturedPixels()
        self.assertEqual(runner.result["glyphAgreement"]["status"], "NOT_APPLICABLE_RAW_CAMERA_MODE")
        self.assertEqual(runner.result["recognitionAssessment"]["level"], "CAMERA_HW_CAPTURE_ONLY")
        self.assertIn("not recognition", runner.result["captureMeaning"])
        runner.run.assert_not_called()
        with self.assertRaisesRegex(ValueError, "NOT_APPLICABLE_RAW_CAMERA_MODE"):
            compareMarkerPixels("NONEXISTENT", runner.result["recognition"], "NONEXISTENT")

    def testRequestedRawDoesNotDiscardAlreadyProcessedCapture(self):
        words = fixture()
        words[7] |= 1 << 22
        runner = object.__new__(echo7.Runner)
        runner.result = {"recognition": decodeWords(words[:96])}
        runner.out = Path("SYNTHETIC")
        runner.run = Mock(return_value=(0, ""))
        with patch("debug_decode.compareMarkerPixels", return_value={"status": "PASS"}) as compare:
            runner.assessCapturedPixels()
        compare.assert_called_once()
        runner.run.assert_called_once()
        self.assertNotIn("recognitionAssessment", runner.result)

    def testBctlSchemas5Through7ActionAcceptedAndSchema8Rejected(self):
        for schema in (5, 6, 7, 8):
            with self.subTest(schema=schema):
                words = fixture(schema)[:-2]
                meta = (schema << 24) | 0x00028000 | len(words)
                header = f"{0x42444247:032b}{BUILD:032b}{meta:032b}"
                lines = [f"ECHO7_HEADER\t{header}", f"ECHO7_ACTION\t1\t{meta:032b}"]
                lines.extend(f"ECHO7_WORD\t{i}\t{word:032b}" for i, word in enumerate(words))
                runner = object.__new__(echo7.Runner)
                runner.result = {}
                runner.target = lambda: {"cable": "SYNTHETIC", "device": "SYNTHETIC"}
                runner.qt = lambda name: "NOT_EXECUTED"
                runner.run = lambda *args, **kwargs: (0, "\n".join(lines))
                if schema in (5, 6, 7):
                    state = runner.control((1 << 24) | 3)
                    self.assertEqual(state["schema"], schema)
                else:
                    with self.assertRaisesRegex(RuntimeError, "schema"):
                        runner.control((1 << 24) | 3)

    def testAlgorithmComparisonRefusesEachRawFlagIncludingSelectSnapshot(self):
        for flag in RAW_FIELDS:
            for location in ("initialStatus", "requestSelections", "observations"):
                with self.subTest(flag=flag, location=location):
                    normal, bypass = trialFixture(0), trialFixture(1)
                    state = bypass[location] if location == "initialStatus" else bypass[location][0]["status"]
                    state[flag] = True
                    comparison, code = compareTrials(normal, bypass, "Synthetic conditions only")
                    self.assertEqual(code, 1)
                    self.assertIn("RAW_CAMERA_MODE", comparison["comparisonValidity"]["issues"][0])

    def testAlgorithmTrialRetainsInitialOrMidTrialRawRejection(self):
        for phase in ("INITIAL", "SELECT", "STATUS"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                runner = FixtureRunner(folder)
                original = runner.control
                calls = 0
                def control(command=0):
                    nonlocal calls
                    state = original(command)
                    currentPhase = "INITIAL" if calls == 0 else "SELECT" if command >> 24 == 1 else "STATUS"
                    calls += 1
                    if currentPhase == phase:
                        state["decoded"]["rawModeRequested"] = True
                    return state
                runner.control = control
                with self.assertRaisesRegex(RuntimeError, "RAW_CAMERA_MODE"):
                    measureTrials(runner, 1)
                rejected = runner.result["rawModeRejections"]
                self.assertEqual(rejected[0]["phase"], phase)
                self.assertTrue(rejected[0]["status"]["rawModeRequested"])
                self.assertEqual(json.loads((Path(folder) / "raw_mode_rejections.json").read_text()), rejected)

    def rawCapture(self, folder, corruptCrc=False, schema=5):
        """Use the real independent GRAB decoder; only JTAG transport is doubled."""
        from PIL import Image
        folder = Path(folder)
        out = folder / "out"
        out.mkdir()
        words = fixture(schema, raw=True)
        payload = struct.pack(">4sHHHHH", b"GRAB", 1, 2, 2, 1, len(words))
        payload += struct.pack(f">{len(words)}I", *words) + struct.pack(">4H", 0xf800, 0x07e0, 0x001f, 0xffff)
        payload += struct.pack(">H", binascii.crc_hqx(payload, 0xffff) ^ int(corruptCrc))
        target = {"cable": "SYNTHETIC", "device": "SYNTHETIC", "index": 2}
        before = {"count": 0, "ack": 0, "busy": 0, "ready": 0, "mode": 0, "source": 0}
        after = {"count": 1, "ack": 1, "busy": 0, "ready": 1, "mode": 0, "source": 1}
        metadata = {"schema": "echo7-snapshot-transaction-v1", "verified": True, "mode": "fresh",
            "target": {key: target[key] for key in ("cable", "device")}, "requestBefore": before,
            "accepted": after, "readBefore": after, "readAfter": after, "requestedToggle": 1,
            "startedHostMs": 1, "acceptedHostMs": 2, "readStartedHostMs": 3, "readFinishedHostMs": 4,
            "memoryWords": len(payload) // 2}
        runner = object.__new__(echo7.Runner)
        runner.args = argparse.Namespace(held=False, timeout=1)
        runner.result, runner.out = {}, out
        runner.target = lambda: target
        runner.qt = lambda name: "NOT_EXECUTED"
        def transport(name, args, **kwargs):
            self.assertEqual(name, "capture")
            capture = out / "capture"
            capture.mkdir()
            (capture / "dump.bin").write_bytes(payload)
            (capture / "snapshot_metadata.json").write_text(json.dumps(metadata))
            image = Image.new("RGB", (2, 2))
            image.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)])
            image.save(capture / "frame.png")
            return 0, "SYNTHETIC TRANSPORT; NOT CAMERA_HW"
        runner.run = transport
        (folder / "last_build.json").write_text(json.dumps({"source": {"buildId": BUILD}}))
        with patch.object(echo7, "WORK", folder), patch.object(echo7, "STATE", folder / "device.json"):
            runner.capture()
        return runner

    def testRawCaptureStillChecksFreshTransactionCrcFrameAndBuild(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = self.rawCapture(folder)
            self.assertTrue(runner.result["fresh"])
            self.assertEqual(runner.result["snapshotTransactionValidation"]["status"], "PASS")
            self.assertEqual(runner.result["snapshot"]["n_results"], 98)
            self.assertTrue(runner.result["recognition"]["sameFrameVerified"])
            self.assertEqual(runner.result["glyphAgreement"]["status"], "NOT_APPLICABLE_RAW_CAMERA_MODE")
            self.assertTrue((runner.out / "capture/frame.png").exists())
            self.assertFalse((runner.out / "pixel_reference").exists())
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "GRAB decode/CRC failed"):
                self.rawCapture(folder, corruptCrc=True)

    def invokeRawTcl(self, schema=5, operation="trial-stream"):
        tool = echo7.discover("quartus_sh")
        words = fixture(schema, raw=True)[:-2]
        with tempfile.TemporaryDirectory(dir=echo7.WORK, prefix="raw_tcl_fixture_") as folder:
            script = Path(folder) / "driver.tcl"
            fixtureText = r'''
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
proc read_source_data {args} {return [bits $::source 32]}
proc write_source_data {args} {
    set binary [lindex $args [expr {[lsearch $args -value]+1}]]
    set ::source 0
    foreach bit [split $binary ""] {set ::source [expr {($::source<<1)|$bit}]}
}
proc read_probe_data {args} {
    set address [expr {($::source>>8)&255}]
    set word [lindex $::words $address]
    set meta [expr {(SCHEMA<<24)|(2<<16)|((($::source>>31)&1)<<15)|[llength $::words]}]
    return "[bits 0x42444247 32][bits 0x12345678 32][bits $meta 32][bits $word 32]"
}
set ::words {WORDS}
set argv [list OPERATION_ARGS]
source SCRIPT
'''.replace("WORDS", " ".join(str(word) for word in words)).replace("SCHEMA", str(schema)).replace(
                "SCRIPT", "{" + (ROOT / "tools/tcl/jtag_control.tcl").as_posix() + "}").replace(
                "OPERATION_ARGS", "trial-stream fixtureCable fixtureDevice 1 30" if operation == "trial-stream"
                else "control fixtureCable fixtureDevice [expr {1<<24}]")
            script.write_text(fixtureText, encoding="utf-8")
            result = subprocess.run([tool, "-t", str(script)], capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout + result.stderr

    def testActualTclEmitsRawRecordBeforeAlgorithmTrialFails(self):
        code, output = self.invokeRawTcl()
        self.assertNotEqual(code, 0)
        self.assertEqual(output.count("ECHO7_TRIAL_WORD\t"), 96)
        self.assertIn("ECHO7_TRIAL_END\t0", output)
        self.assertIn("RAW_CAMERA_MODE", output)
        self.assertNotIn("ECHO7_TRIAL_DONE", output)

    def testActualTclRefusesUnknownSchemaBeforeSendingAction(self):
        code, output = self.invokeRawTcl(schema=8, operation="control")
        self.assertNotEqual(code, 0)
        self.assertIn("unsupported BCTL schema before action", output)
        self.assertNotIn("ECHO7_ACTION", output)


if __name__ == "__main__":
    unittest.main()
