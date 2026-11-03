"""Synthetic schema/capacity/transport tests, never hardware acceptance."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
from debug_decode import decodeWords, decodeGrabWords, compareMarkerPixels, schemaLayout
from candidates_reclaimed_model import candidates_reclaimed
import test_raw_camera_mode as rawTests
from test_raw_camera_mode import fixture, BUILD
from trial_stream import parseTrialStream


class Schema6CapacityTests(unittest.TestCase):
    def testLegacyAndNewPacketLengthsRemainDistinct(self):
        for schema in range(1, 7):
            for raw in ((False, True) if schema >= 5 else (False,)):
                words = fixture(schema, raw)
                result = decodeGrabWords(words, BUILD)
                self.assertEqual(result["statusWordCount"], 160 if schema == 6 else 96)
                self.assertEqual(len(result["markers"]), 32 if schema == 6 else 16)
                self.assertEqual(result["outputCandidateCapacity"], 16 if schema == 6 else 8)
                self.assertEqual(result["rawCameraMode"], raw)
        for words in (fixture(6)[:96], fixture(5)[:-2] + [0]*64):
            with self.assertRaisesRegex(ValueError, "requires exactly"):
                decodeWords(words)
        with self.assertRaisesRegex(ValueError, "schema"):
            schemaLayout(8)

    def testCount16AndFinalBlueSlotAreNotTruncated(self):
        words = fixture(6)
        words[9] = 16 | (16 << 5)
        at = 24 + 31*4
        words[at:at+3] = [(1 << 31) | (1 << 30) | (6 << 24) | (255 << 16), (100 << 16) | 150, (80 << 16) | 130]
        decoded = decodeWords(words[:-2])
        self.assertEqual((decoded["redCandidateCount"], decoded["blueCandidateCount"]), (16, 16))
        self.assertTrue(decoded["markers"][31]["accepted"])
        self.assertEqual(decoded["markers"][31]["digit"], 6)
        for badCount in (17, 17 << 5, 1 << 10):
            words[9] = badCount
            with self.assertRaisesRegex(ValueError, "candidate counts"):
                decodeWords(words[:-2])

    def testReferenceIndex15UsesFourBitsAndNewBlueOffset(self):
        words = fixture(6)
        words[9], words[154] = 16 << 5, (15 << 4) | 8
        at = 24 + 31*4
        words[at:at+3] = [(1 << 30) | (15 << 24), (100 << 16) | 150, (80 << 16) | 90]
        result = decodeWords(words[:-2])
        self.assertEqual(result["calibrationReferenceIndex"], 15)
        self.assertTrue(result["calibrationReferenceValid"])
        for position, value in ((154, 1 << 8), (9, 15 << 5), (155, 0), (at, 0)):
            broken = words.copy()
            broken[position] = value
            with self.assertRaises(ValueError):
                decodeWords(broken[:-2])

    def testNewCapacityAndReaderProfilesFailClosed(self):
        words = fixture(6)
        for position, value in ((157, (8 << 16) | (15 << 8)), (157, (16 << 16) | (16 << 8)),
                                (159, (1 << 24) | (5 << 16) | (84 << 8) | 64),
                                (159, (2 << 24) | (5 << 16) | (96 << 8) | 64),
                                (159, (2 << 24) | (6 << 16) | (84 << 8) | 64)):
            broken = words.copy()
            broken[position] = value
            with self.assertRaises(ValueError):
                decodeWords(broken[:-2])

    def testRawSchema6StillBindsFrameBuildAndEmptyMetadata(self):
        words = fixture(6, True)
        for position, value in ((160, 10), (161, BUILD+1), (156, BUILD+1), (155, 1), (9, 1 << 5)):
            broken = words.copy()
            broken[position] = value
            with self.assertRaises(ValueError):
                decodeGrabWords(broken, BUILD)

    def testRealDecoderRawCaptureUses162WordsAndNoRecognitionClaim(self):
        helper = rawTests.RawCameraModeTests()
        with tempfile.TemporaryDirectory() as folder:
            runner = helper.rawCapture(folder, schema=6)
            self.assertEqual(runner.result["snapshot"]["n_results"], 162)
            self.assertEqual(runner.result["frameId"], 9)
            self.assertEqual(runner.result["glyphAgreement"]["status"], "NOT_APPLICABLE_RAW_CAMERA_MODE")

    def testActualTclReadEmitsAll160WordsBeforeRawTrialRejection(self):
        code, output = rawTests.RawCameraModeTests().invokeRawTcl(schema=6)
        self.assertNotEqual(code, 0)
        self.assertEqual(output.count("ECHO7_TRIAL_WORD\t"), 160)
        self.assertIn("ECHO7_TRIAL_END\t0", output)
        self.assertIn("RAW_CAMERA_MODE", output)
        records, done = parseTrialStream(output, BUILD)
        self.assertEqual(len(records[0]["words"]), 160)
        self.assertTrue(records[0]["decoded"]["rawCameraMode"])
        self.assertIsNone(done)

    def testTrialLengthAndHeaderMustAgree(self):
        words = fixture(6)[:-2]
        meta = (6 << 24) | (2 << 16) | 160
        lines = ["ECHO7_TRIAL_BEGIN\t0\tSELECT\t1\t6",
                 f"ECHO7_TRIAL_ACTION\t0\t1\t{meta:032b}",
                 f"ECHO7_TRIAL_HEADER\t0\t{0x42444247:032b}{BUILD:032b}{meta:032b}"]
        lines += [f"ECHO7_TRIAL_WORD\t0\t{i}\t{word:032b}" for i, word in enumerate(words)]
        lines += ["ECHO7_TRIAL_END\t0"]
        text = "\n".join(lines)
        records, _ = parseTrialStream(text, BUILD)
        self.assertEqual(records[0]["decoded"]["outputCandidateCapacity"], 16)
        for broken in (text.replace(f"{meta:032b}", f"{(meta-64):032b}"), "\n".join(lines[:-2] + lines[-1:])):
            with self.assertRaises(ValueError):
                parseTrialStream(broken, BUILD)

    def testEmptyBadFrameOverflowIsNotVacuousGlyphPass(self):
        from PIL import Image
        for badFrame in (False, True):
            words = fixture(6)
            words[155], words[158] = int(not badFrame), 4 if badFrame else 0
            with tempfile.TemporaryDirectory() as folder:
                folder = Path(folder)
                image = folder / "synthetic.png"
                Image.new("RGB", (320, 240)).save(image)
                result = compareMarkerPixels(image, decodeWords(words[:-2]), folder / "check")
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["comparedCandidateCount"], 0)
                self.assertEqual(result["reason"], "INVALID_CAPTURED_FRAME" if badFrame else "NO_CANDIDATES_TO_COMPARE")
                self.assertEqual(json.loads((folder / "check/comparison.json").read_text()), result)

    def testPixelOracleReadsBlueSlot16AndChecksAutomaticOrientation(self):
        from PIL import Image
        words = fixture(6)
        words[9] = 1 << 5
        at = 24 + 16*4
        words[at:at+3] = [(1 << 31) | (1 << 30) | (2 << 28) | (6 << 24) | (255 << 16),
                         (100 << 16) | 150, (80 << 16) | 130]
        expected = {"accepted": True, "digit": 6, "quality": 255, "reasonCode": 0,
                    "segments": "", "windowScores": {}, "orientationProfile": 2}
        with tempfile.TemporaryDirectory() as folder:
            image = Path(folder) / "synthetic.png"
            Image.new("RGB", (320, 240)).save(image)
            with patch("projective_reference.classifyProjective", return_value=expected) as model:
                result = compareMarkerPixels(image, decodeWords(words[:-2]), Path(folder) / "match")
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["comparisons"][0]["index"], 16)
                self.assertEqual(model.call_args.args[1]["colour"], "blue")
                self.assertEqual(model.call_args.kwargs["readerAlgorithm"], 5)
                expected["orientationProfile"] = 1
                result = compareMarkerPixels(image, decodeWords(words[:-2]), Path(folder) / "mismatch")
                self.assertEqual(result["status"], "FAIL")
                self.assertEqual(result["comparisons"][0]["differences"], ["orientation"])

    def testCompletedCapacity16IsIndependentOfActive15(self):
        def serialMask(count):
            mask = [[0] * 12 for _ in range(count*3+1)]
            for index in range(count):
                mask[3*index][2:6] = [2]*4
            return mask
        for count, overflow in ((9, False), (16, False), (17, True)):
            result = candidates_reclaimed(serialMask(count), cap=16, active_capacity=15, min_area=3)
            self.assertEqual(result["overflow"], overflow)
            self.assertFalse(result["blue_active_overflow"])
            self.assertEqual(result["blue_output_overflow"], overflow)
            self.assertEqual(len(result["blue"]), 0 if overflow else count)
        self.assertTrue(candidates_reclaimed(serialMask(9), min_area=3)["overflow"])
        with self.assertRaisesRegex(ValueError, "active capacity"):
            candidates_reclaimed(serialMask(9), cap=16, active_capacity=16, min_area=3)


if __name__ == "__main__":
    unittest.main()
