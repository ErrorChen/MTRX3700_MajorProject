"""Host profile/version boundaries only; synthetic packets are not board evidence.

The reader and colour algorithm are explicit fields in each recorded packet.
These tests prevent a new default from reinterpreting historical RUN3 captures
and ensure unsupported combinations fail before any image model is called.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib"), str(ROOT / "tests/python")]
import echo7
from debug_decode import compareMarkerPixels, decodeGrabWords, decodeWords, schemaLayout
from test_raw_camera_mode import BUILD, fixture
from test_schema7_shared_pool import sharedWords
from test_sw9_comparison import fixture as trialFixture
from compare_sw9_trials import compareTrials
from trial_stream import parseTrialStream


def withProfile(words, colour, reader=5, minimum=84, spread=64):
    """Change only the advertised profile in a fresh synthetic packet copy."""
    result = words.copy()
    tail = schemaLayout(result[1] >> 16)["tailBase"]
    result[tail + 7] = (colour << 24) | (reader << 16) | (minimum << 8) | spread
    return result


class Run2DecodeTests(unittest.TestCase):
    def testSchema7Run2ChangesOnlyColourIdentityAndPreservesWhiteMeaning(self):
        old = decodeGrabWords(withProfile(fixture(7), 2), BUILD)
        new = decodeGrabWords(withProfile(fixture(7), 3), BUILD)
        self.assertEqual(new["colourAlgorithm"], 3)
        self.assertEqual((new["statusWordCount"], new["candidateStorageSlots"]), (96, 16))
        self.assertEqual((new["whiteMinimum"], new["whiteMaxSpread"]), (84, 64))
        self.assertEqual(new["whiteAnchorThresholdExpression"], "R+2*G+B >= 384")
        self.assertEqual(new["readerOrientationMode"], "PER_MARKER_ANCHOR")
        self.assertTrue(new["sameFrameVerified"])
        old.pop("colourAlgorithm")
        new.pop("colourAlgorithm")
        self.assertEqual(old, new)

    def testHistoricalColoursZeroOneTwoRemainExplicitForAllCompatibleSchemas(self):
        for schema in range(2, 8):
            for colour, reader, white in ((0, 0, 160), (1, 1, 112), (2, 4, 84)):
                with self.subTest(schema=schema, colour=colour):
                    decoded = decodeGrabWords(withProfile(fixture(schema), colour, reader, white), BUILD)
                    self.assertEqual(decoded["colourAlgorithm"], colour)
                    self.assertEqual(decoded["readerAlgorithm"], reader)
        self.assertEqual(decodeGrabWords(fixture(1), BUILD)["colourAlgorithm"], 0)
        for schema in (6, 7):
            self.assertEqual(decodeGrabWords(withProfile(fixture(schema), 2), BUILD)["colourAlgorithm"], 2)

    def testRun2RequiresSchema7AndReader5(self):
        for schema in range(1, 7):
            reader = 5 if schema == 6 else 4
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                decodeWords(withProfile(fixture(schema), 3, reader)[:-2])
        for reader in range(5):
            with self.subTest(reader=reader), self.assertRaisesRegex(ValueError, "requires schema7/8 and reader"):
                decodeWords(withProfile(fixture(7), 3, reader)[:-2])

    def testUnknownColourFourStillFailsClosed(self):
        for schema in range(2, 8):
            reader = 5 if schema >= 6 else 4
            with self.subTest(schema=schema), self.assertRaisesRegex(ValueError, "unsupported EBP1 colour algorithm"):
                decodeWords(withProfile(fixture(schema), 4, reader)[:-2])

    def testRun2DoesNotRelaxWhiteOrCaptureIdentityChecks(self):
        for minimum, spread in ((83, 64), (96, 64), (84, 63)):
            with self.subTest(minimum=minimum, spread=spread), self.assertRaisesRegex(ValueError, "floor84 and spread64"):
                decodeWords(withProfile(fixture(7), 3, minimum=minimum, spread=spread)[:-2])
        words = withProfile(fixture(7), 3)
        words[-2] += 1
        with self.assertRaisesRegex(ValueError, "FRAME_MISMATCH"):
            decodeGrabWords(words, BUILD)
        with self.assertRaisesRegex(ValueError, "buildId"):
            decodeGrabWords(withProfile(fixture(7), 3), BUILD + 1)

    def testTrialTransportRetainsRecordedRun2Profile(self):
        words = withProfile(fixture(7), 3)[:-2]
        meta = (7 << 24) | (2 << 16) | 96
        lines = ["ECHO7_TRIAL_BEGIN\t0\tINITIAL\t0\t0",
                 f"ECHO7_TRIAL_HEADER\t0\t{0x42444247:032b}{BUILD:032b}{meta:032b}"]
        lines += [f"ECHO7_TRIAL_WORD\t0\t{i}\t{word:032b}" for i, word in enumerate(words)]
        lines.append("ECHO7_TRIAL_END\t0")
        records, done = parseTrialStream("\n".join(lines) + "\n", BUILD)
        self.assertEqual(records[0]["words"], words)
        self.assertEqual(records[0]["decoded"]["colourAlgorithm"], 3)
        self.assertIsNone(done)

    def testCaptureCliPassesRecordedColourRatherThanCurrentModelDefault(self):
        for colour in (2, 3):
            with self.subTest(colour=colour):
                runner = object.__new__(echo7.Runner)
                runner.result = {"recognition": decodeWords(withProfile(fixture(7), colour)[:-2])}
                runner.out = Path("SYNTHETIC_HOST_BOUNDARY_ONLY")
                runner.run = Mock(return_value=(0, ""))
                with patch("debug_decode.compareMarkerPixels", return_value={"status": "PASS"}):
                    runner.assessCapturedPixels()
                label, command = runner.run.call_args.args
                self.assertEqual(label, "pixel_reference")
                for option, value in (("--colour-algorithm", str(colour)), ("--reader-algorithm", "5"),
                                      ("--white-min", "84"), ("--max-spread", "64")):
                    self.assertEqual(command[command.index(option) + 1], value)
                self.assertIn("--shared-pool", command)

    def testPixelComparisonPassesRecordedColourAndExportsUnchangedWhiteMasks(self):
        from PIL import Image
        expected = {"accepted": False, "reasonCode": 0, "windowScores": {}, "segments": ""}
        with tempfile.TemporaryDirectory(prefix="echo7_run_profile_") as folder:
            imagePath = Path(folder) / "synthetic.png"
            # Weighted luminance88 and spread16 pass the unsaturated stroke
            # threshold84 but fail the independently strict anchor threshold96.
            Image.new("RGB", (320, 240), (80, 96, 80)).save(imagePath)
            for colour in (2, 3):
                output = Path(folder) / f"colour{colour}"
                decoded = decodeWords(withProfile(sharedWords((True,)), colour)[:-2])
                with patch("projective_reference.classifyProjective", return_value=expected) as model:
                    result = compareMarkerPixels(imagePath, decoded, output)
                self.assertEqual(result["status"], "PASS")
                self.assertEqual(result["colourAlgorithm"], colour)
                self.assertEqual(model.call_args.kwargs["colourAlgorithm"], colour)
                self.assertEqual(model.call_args.kwargs["readerAlgorithm"], 5)
                for suffix, value in (("white", 255), ("strong_white", 0)):
                    with Image.open(output / f"marker_00_{suffix}.png") as mask:
                        self.assertEqual(mask.getpixel((0, 0)), value)

    def testRun3AndRun2TrialsCannotBeComparedAsOneProfile(self):
        normal, bypass = trialFixture(0), trialFixture(1)
        for data, colour in ((normal, 2), (bypass, 3)):
            for state in [data["initialStatus"], *[row["status"] for row in data["observations"]],
                          *[row["status"] for row in data["requestSelections"]]]:
                state.update(debugSchemaVersion=7, readerAlgorithm=5, colourAlgorithm=colour,
                             activeCandidateCapacity=15, outputCandidateCapacity=16,
                             poolLayout="SHARED_TOTAL", candidateStorageSlots=16)
        result, code = compareTrials(normal, bypass, "Synthetic conditions only")
        self.assertEqual(code, 1)
        self.assertIn("profile", str(result["comparisonValidity"]["issues"]).lower())


if __name__ == "__main__":
    unittest.main()
