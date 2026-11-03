import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""MODEL checks for frozen status and same-frame GRAB schema boundaries."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from contract_model import LEGACY_V2_FIELD_LAYOUTS as FIELD_LAYOUTS, packPayload
from debug_decode import decodeWords, decodeGrabWords, compareMarkerPixels


def fixture():
    words = [0] * 98
    words[0] = 0x45425031
    words[1] = 0x00010002
    words[2], words[3], words[4], words[5] = 20000, 9, 1000, 12000
    fields = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
    fields["frameId"] = 9
    packed = packPayload("targetReport", fields, contractVersion=2)
    for i in range(5):
        words[13 + i] = (packed >> (32 * i)) & 0xffffffff
    words[96] = 9
    words[97] = 0x12345678
    words[92] = 0x12345678
    words[95] = (160 << 8) | 64
    return words


class DebugDecodeTests(unittest.TestCase):
    def testLegacyCaptureRejectedExplicitly(self):
        for magic in (0x45504131, 0x45504132):
            with self.assertRaisesRegex(ValueError, "LEGACY_CAPTURE"):
                decodeGrabWords([magic] + [0] * 77, 0)

    def testMatchingFrameAndBuild(self):
        decoded = decodeGrabWords(fixture(), 0x12345678)
        self.assertTrue(decoded["sameFrameVerified"])
        self.assertEqual(decoded["frameId"], 9)
        self.assertEqual(decoded["processingLatencyUs"], 11000)
        self.assertEqual(decoded["debugSchemaVersion"], 1)
        self.assertEqual(decoded["colourAlgorithm"], 0)

    def testSchema2ExplicitHsvAndUnknownAlgorithms(self):
        words = fixture()
        words[1] = 0x00020002
        words[95] = (1 << 24) | (1 << 16) | (112 << 8) | 64
        decoded = decodeGrabWords(words, 0x12345678)
        self.assertEqual(decoded["debugSchemaVersion"], 2)
        self.assertEqual(decoded["colourAlgorithm"], 1)
        self.assertEqual(decoded["readerAlgorithm"], 1)
        self.assertEqual(decoded["whiteMinimum"], 112)
        words[95] |= 2 << 24
        with self.assertRaisesRegex(ValueError, "colour algorithm"):
            decodeWords(words[:96])
        words[1] = 0x00010002
        with self.assertRaisesRegex(ValueError, "reader algorithm"):
            decodeWords(words[:96])

    def testCompletionDiscardCountAndReservedBits(self):
        words = fixture()[:96]
        self.assertEqual(decodeWords(words)["completionDiscardCount"], 0)
        words[94] = (17 << 16) | 15
        with self.assertRaisesRegex(ValueError, "reserved"):
            decodeWords(words)  # schema 1 never assigned the upper counter bits
        words[1] = 0x00020002
        decoded = decodeWords(words)
        self.assertEqual(decoded["completionDiscardCount"], 17)
        self.assertTrue(decoded["candidateOverflow"])
        self.assertTrue(decoded["transportFaultSticky"])
        words[94] = 0xffff0000
        self.assertEqual(decodeWords(words)["completionDiscardCount"], 0xffff)
        words[94] |= 0x10
        with self.assertRaisesRegex(ValueError, "reserved"):
            decodeWords(words)

    def testReader2WhiteThresholdHasExplicitDifferentMeaning(self):
        words = fixture()[:96]
        words[1] = 0x00020002
        words[95] = (1 << 24) | (2 << 16) | (96 << 8) | 64
        decoded = decodeWords(words)
        self.assertEqual(decoded["readerAlgorithm"], 2)
        self.assertEqual(decoded["whiteMinimum"], 96)
        self.assertEqual(decoded["whiteMode"], "QUARTER_WEIGHTED_LUMA")
        self.assertEqual(decoded["whiteThresholdExpression"], "R+2*G+B >= 4*whiteMinimum")
        words[95] = (1 << 24) | (1 << 16) | (112 << 8) | 64
        legacy = decodeWords(words)
        self.assertEqual(legacy["whiteMode"], "MIN_RGB_CHANNEL")
        self.assertEqual(legacy["whiteMinimum"], 112)
        for white, spread in ((112, 64), (96, 63)):
            words[95] = (1 << 24) | (2 << 16) | (white << 8) | spread
            with self.assertRaisesRegex(ValueError, "weighted-luma"):
                decodeWords(words)
        words[1] = 0x00010002
        words[95] = (2 << 16) | (96 << 8) | 64
        with self.assertRaisesRegex(ValueError, "reader algorithm"):
            decodeWords(words)

    def testReader3ExplicitSplitThresholdsAndHistoricalIsolation(self):
        words = fixture()[:96]
        words[1] = 0x00020002
        words[95] = (1 << 24) | (3 << 16) | (96 << 8) | 64
        decoded = decodeWords(words)
        self.assertEqual(decoded["readerAlgorithm"], 3)
        self.assertEqual(decoded["whiteMode"], "ROUNDED_STROKES_STRICT_ANCHOR")
        self.assertEqual(decoded["whiteThresholdExpression"], "R+2*G+B+2 >= 4*whiteMinimum")
        self.assertEqual(decoded["whiteAnchorThresholdExpression"], "R+2*G+B >= 4*whiteMinimum")
        self.assertTrue(decoded["candidateSizePruning"])
        words[95] = (3 << 16) | (96 << 8) | 64
        with self.assertRaisesRegex(ValueError, "HSV"):
            decodeWords(words)
        words[95] = (1 << 24) | (2 << 16) | (96 << 8) | 64
        legacy = decodeWords(words)
        self.assertEqual(legacy["whiteThresholdExpression"], "R+2*G+B >= 4*whiteMinimum")
        self.assertNotIn("candidateSizePruning", legacy)
        for white, spread in ((95, 64), (96, 63)):
            words[95] = (1 << 24) | (3 << 16) | (white << 8) | spread
            with self.assertRaisesRegex(ValueError, "weighted-luma"):
                decodeWords(words)
        words[95] = (1 << 24) | (5 << 16) | (96 << 8) | 64
        with self.assertRaisesRegex(ValueError, "reader algorithm"):
            decodeWords(words)

    def testReader4WhiteAndColourProfilesAreExplicit(self):
        words = fixture()[:96]
        words[1] = 0x00020002
        words[95] = (2 << 24) | (4 << 16) | (84 << 8) | 64
        decoded = decodeWords(words)
        self.assertEqual(decoded['readerAlgorithm'], 4)
        self.assertEqual(decoded['colourAlgorithm'], 2)
        self.assertEqual(decoded['whiteMode'], 'UNSATURATED_STROKES_STRICT_ANCHOR')
        self.assertEqual(decoded['whiteAnchorMinimum'], 96)
        self.assertEqual(decoded['whiteAnchorThresholdExpression'], 'R+2*G+B >= 384')
        self.assertIn('2*(max(R,G,B)-min(R,G,B))', decoded['whiteThresholdExpression'])
        for colour, minimum, spread in ((1, 84, 64), (2, 96, 64), (2, 84, 63)):
            words[95] = (colour << 24) | (4 << 16) | (minimum << 8) | spread
            with self.assertRaises(ValueError):decodeWords(words)

    def testPixelComparisonSelectsRecordedReaderAndExportsItsWhiteMask(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix="reader_semantics_") as folder:
            imagePath = Path(folder) / "pixel.png"
            Image.new("RGB", (320, 240), (80, 112, 80)).save(imagePath)
            for algorithm, minimum, expectedWhite in ((1, 112, 0), (2, 96, 255), (3, 96, 255)):
                words = fixture()[:96]
                words[1] = 0x00020002
                words[9] = 1
                words[91] = 1  # Synthetic good-frame prerequisite for glyph agreement.
                words[24] = 4 << 8
                words[95] = (1 << 24) | (algorithm << 16) | (minimum << 8) | 64
                reference = {"accepted": False, "reasonCode": 4, "windowScores": {}, "segments": ""}
                with patch("projective_reference.classifyProjective", return_value=reference) as model:
                    output = Path(folder) / f"algorithm{algorithm}"
                    result = compareMarkerPixels(imagePath, decodeWords(words), output)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(model.call_args.kwargs["readerAlgorithm"], algorithm)
                self.assertEqual(model.call_args.kwargs["colourAlgorithm"], 1)
                self.assertEqual(model.call_args.args[5], minimum)
                with Image.open(output / "marker_00_white.png") as mask:
                    self.assertEqual(mask.getpixel((0, 0)), expectedWhite)

    def testReader3ExportsSeparateStrokeAndAnchorMasks(self):
        from PIL import Image
        with tempfile.TemporaryDirectory(prefix="split_white_") as folder:
            imagePath = Path(folder) / "pixel.png"
            # This exact RGB565 triplet was measured in real frame 225's C
            # stroke: sum383 passes rounded strokes, but not strict anchors.
            Image.new("RGB", (320, 240), (82, 93, 115)).save(imagePath)
            words = fixture()[:96]
            words[1] = 0x00020002; words[9] = 1; words[24] = 4 << 8
            words[91] = 1  # This test exercises white masks, not a bad/overflow frame.
            words[95] = (1 << 24) | (3 << 16) | (96 << 8) | 64
            reference = {"accepted": False, "reasonCode": 4, "windowScores": {}, "segments": ""}
            output = Path(folder) / "algorithm3"
            with patch("projective_reference.classifyProjective", return_value=reference):
                result = compareMarkerPixels(imagePath, decodeWords(words), output)
            self.assertEqual(result["status"], "PASS")
            with Image.open(output / "marker_00_white.png") as mask:
                self.assertEqual(mask.getpixel((0, 0)), 255)
            with Image.open(output / "marker_00_strong_white.png") as mask:
                self.assertEqual(mask.getpixel((0, 0)), 0)

    def testWrongFrameAndBuildRejected(self):
        words = fixture()
        words[96] = 10
        with self.assertRaisesRegex(ValueError, "FRAME_MISMATCH"):
            decodeGrabWords(words, 0x12345678)
        with self.assertRaisesRegex(ValueError, "buildId"):
            decodeGrabWords(fixture(), 0x12345679)

    def testSchemaAndReservedRejected(self):
        words = fixture()[:96]
        words[1] = 1
        with self.assertRaises(ValueError):
            decodeWords(words)
        words = fixture()[:96]
        words[93] = 0x100
        with self.assertRaises(ValueError):
            decodeWords(words)

    def testUnsupportedPixelDigitRejected(self):
        words = fixture()[:96]
        words[24] = 0xc7000000  # accepted blue 7 is forbidden, even at a known slot
        with self.assertRaisesRegex(ValueError, "unsupported digit"):
            decodeWords(words)


if __name__ == "__main__":
    unittest.main()
