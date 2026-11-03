"""Host version/dispatch boundaries using synthetic packets, never board proof.

Reader6 owns anchor components by their centre inside the candidate's bbox.
Reader5 recordings keep the former unfiltered component interpretation even
when the current projective model defaults to6.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
from debug_decode import compareMarkerPixels, decodeGrabWords, decodeWords
import echo7
from test_raw_camera_mode import BUILD, fixture
from test_run2_decode import withProfile
from trial_stream import parseTrialStream


def markerPacket(reader=6, accepted=False):
    words = withProfile(fixture(8), 3, reader)
    words[9] = 1 << 5  # One blue candidate at shared slot0; its slot is not an ID.
    words[24:27] = [(1 << 30) | (15 << 24), (10 << 16) | 20, (20 << 16) | 30]
    if accepted:
        words[24] = (1 << 31) | (1 << 30) | (2 << 28) | (4 << 24) | (201 << 16)
    return words


class Reader6DecodeTests(unittest.TestCase):
    def testReader6RequiresSchema8AndColour3(self):
        decoded = decodeGrabWords(markerPacket(), BUILD)
        self.assertEqual((decoded["debugSchemaVersion"], decoded["contractVersion"],
                          decoded["readerAlgorithm"], decoded["colourAlgorithm"]), (8, 3, 6, 3))
        self.assertTrue(decoded["sameFrameVerified"])
        for schema in range(1, 8):
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, "reader algorithm"):
                decodeWords(withProfile(fixture(schema), 3, 6)[:-2])
        for colour in (0, 1, 2):
            with self.subTest(colour=colour), self.assertRaisesRegex(ValueError, "requires HSV colour algorithm 3"):
                decodeWords(withProfile(fixture(8), colour, 6)[:-2])

    def testHistoricalReader5RemainsReadableWithoutChangingWhiteOrCoordinates(self):
        old = decodeGrabWords(markerPacket(5), BUILD)
        new = decodeGrabWords(markerPacket(6), BUILD)
        self.assertEqual(old.pop("readerAlgorithm"), 5)
        self.assertEqual(new.pop("readerAlgorithm"), 6)
        self.assertEqual(old, new)
        for schema, colours in ((6, (2,)), (7, (2, 3)), (8, (2, 3))):
            for colour in colours:
                with self.subTest(schema=schema, colour=colour):
                    historical = decodeGrabWords(withProfile(fixture(schema), colour, 5), BUILD)
                    self.assertEqual((historical["readerAlgorithm"], historical["colourAlgorithm"]), (5, colour))

    def testReader7MainComponentVersionIsExplicitAndDoesNotChangeWireLayout(self):
        old = decodeGrabWords(markerPacket(6), BUILD)
        new = decodeGrabWords(markerPacket(7), BUILD)
        self.assertEqual(old.pop("readerAlgorithm"), 6)
        self.assertEqual(new.pop("readerAlgorithm"), 7)
        self.assertEqual(old, new)
        for schema in range(1, 8):
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, "reader algorithm"):
                decodeWords(withProfile(fixture(schema), 3, 7)[:-2])
        for colour in (0, 1, 2):
            with self.subTest(colour=colour), self.assertRaisesRegex(ValueError, "requires HSV colour algorithm 3"):
                decodeWords(withProfile(fixture(8), colour, 7)[:-2])

    def testFutureAlgorithmsAndWrongWhiteOrCaptureBindingFail(self):
        for reader in (10, 255):
            with self.subTest(reader=reader), self.assertRaisesRegex(ValueError, "reader algorithm"):
                decodeWords(withProfile(fixture(8), 3, reader)[:-2])
        with self.assertRaisesRegex(ValueError, "colour algorithm"):
            decodeWords(withProfile(fixture(8), 4, 6)[:-2])
        for minimum, spread in ((83, 64), (96, 64), (84, 63)):
            with self.subTest(minimum=minimum, spread=spread), self.assertRaisesRegex(ValueError, "floor84 and spread64"):
                decodeWords(withProfile(fixture(8), 3, 6, minimum, spread)[:-2])
        bad = markerPacket(); bad[-2] += 1
        with self.assertRaisesRegex(ValueError, "FRAME_MISMATCH"):
            decodeGrabWords(bad, BUILD)
        with self.assertRaisesRegex(ValueError, "buildId"):
            decodeGrabWords(markerPacket(), BUILD+1)

    def testTrialTransportRetainsActualReaderId(self):
        for reader in (5, 6, 7):
            words = markerPacket(reader)[:-2]
            meta = (8 << 24) | (3 << 16) | 96
            lines = ["ECHO7_TRIAL_BEGIN\t0\tINITIAL\t0\t0",
                     f"ECHO7_TRIAL_HEADER\t0\t{0x42444247:032b}{BUILD:032b}{meta:032b}"]
            lines += [f"ECHO7_TRIAL_WORD\t0\t{i}\t{word:032b}" for i, word in enumerate(words)]
            lines.append("ECHO7_TRIAL_END\t0")
            records, done = parseTrialStream("\n".join(lines)+"\n", BUILD)
            self.assertIsNone(done)
            self.assertEqual(records[0]["words"], words)
            self.assertEqual(records[0]["decoded"]["readerAlgorithm"], reader)

    def testCaptureCliUsesProjectiveReplayWithRecordedReaderAndColour(self):
        for reader in (5, 6, 7):
            runner = object.__new__(echo7.Runner)
            runner.result = {"recognition": decodeWords(markerPacket(reader)[:-2])}
            runner.out = Path("SYNTHETIC_HOST_BOUNDARY_ONLY")
            runner.run = Mock(return_value=(0, ""))
            with patch("debug_decode.compareMarkerPixels", return_value={"status": "PASS"}):
                runner.assessCapturedPixels()
            label, command = runner.run.call_args.args
            self.assertEqual(label, "pixel_reference")
            self.assertEqual(Path(command[1]).name, "projective_reference.py")
            for option, value in (("--reader-algorithm", str(reader)), ("--colour-algorithm", "3"),
                                  ("--white-min", "84"), ("--max-spread", "64")):
                self.assertEqual(command[command.index(option)+1], value)
            self.assertIn("--shared-pool", command)

    def testPixelComparisonPinsRecordedReaderAndStillChecksOrientation(self):
        expected = dict(accepted=True, reasonCode=0, digit=4, quality=201,
                        orientationProfile=2, windowScores={}, segments="")
        with tempfile.TemporaryDirectory(prefix="echo7_reader_version_") as folder:
            path = Path(folder) / "synthetic.png"
            # This colour is a valid unsaturated stroke but fails the strict
            # anchor threshold. Reader6 must not change either white predicate.
            Image.new("RGB", (320, 240), (80, 96, 80)).save(path)
            for reader in (5, 6, 7):
                for orientation in (2, 3):
                    out = Path(folder) / f"reader{reader}_orientation{orientation}"
                    with patch("projective_reference.classifyProjective",
                               return_value={**expected, "orientationProfile": orientation}) as model:
                        result = compareMarkerPixels(path, decodeWords(markerPacket(reader, True)[:-2]), out)
                    self.assertEqual(model.call_args.kwargs["readerAlgorithm"], reader)
                    self.assertEqual(model.call_args.kwargs["colourAlgorithm"], 3)
                    self.assertEqual(result["readerAlgorithm"], reader)
                    self.assertEqual(result["status"], "PASS" if orientation == 2 else "FAIL")
                    self.assertEqual(result["comparisons"][0]["differences"], [] if orientation == 2 else ["orientation"])
                    for suffix, pixel in (("white", 255), ("strong_white", 0)):
                        with Image.open(out / f"marker_00_{suffix}.png") as mask:
                            self.assertEqual(mask.getpixel((0, 0)), pixel)


if __name__ == "__main__":
    unittest.main()
