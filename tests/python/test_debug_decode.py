import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""MODEL checks for frozen status and same-frame GRAB schema boundaries."""
import unittest
from contract_model import FIELD_LAYOUTS, packPayload
from debug_decode import decodeWords, decodeGrabWords


def fixture():
    words = [0] * 98
    words[0] = 0x45425031
    words[1] = 0x00010002
    words[2], words[3], words[4], words[5] = 20000, 9, 1000, 12000
    fields = {name: 0 for name, _ in FIELD_LAYOUTS["targetReport"]}
    fields["frameId"] = 9
    packed = packPayload("targetReport", fields)
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
