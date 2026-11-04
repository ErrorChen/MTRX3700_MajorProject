"""Datasheet identity/presentation checks with synthetic inputs, not board proof."""
from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import render_member_b_datasheet as sheet


def fixtureIndex(reader=6, colour=3, count=10):
    return dict(source=dict(sha256="a"*64, buildId=0xaaaaaaaa),
        algorithm=dict(readerAlgorithm=reader, colourAlgorithm=colour, whiteMinimum=84, whiteMaxSpread=64),
        candidatePool=dict(mode="SHARED_TOTAL", totalCompletedSlots=16, activePerColour=15),
        display=dict(algorithmBypassSwitch="SW8", rawCameraSwitch="SW9", bypassPerspective=False),
        scene=dict(description="SYNTHETIC TEST ONLY: fixed printed sheet with duplicate blue1/2.",
            printedMarkerCount=count, nativeWidth=320, nativeHeight=240, orientationProfile=0,
            conditions="PENDING measured operating ranges; no physical acceptance is claimed."), records={})


def boardFor(index):
    profile = sheet.indexProfile(index)
    return dict(buildId=index["source"]["buildId"], **index["algorithm"],
        poolLayout=index["candidatePool"]["mode"], activeCandidateCapacity=index["candidatePool"]["activePerColour"],
        outputCandidateCapacity=profile["outputCapacity"], orientationProfile=index["scene"]["orientationProfile"],
        bypassPerspective=index["display"]["bypassPerspective"], rawCameraMode=False,
        rawModeRequested=False, rawDisplayActive=False, processingLatencyUs=45000)


class DatasheetProfileTests(unittest.TestCase):
    def testMetadataCannotBeInferredFromCapacityOrMissingFields(self):
        for group, key in (("algorithm", "readerAlgorithm"), ("candidatePool", "mode"),
                           ("display", "algorithmBypassSwitch"), ("display", "rawCameraSwitch"),
                           ("display", "bypassPerspective"), ("scene", "printedMarkerCount"),
                           ("scene", "conditions")):
            index = fixtureIndex(); del index[group][key]
            with self.subTest(group=group, key=key), self.assertRaisesRegex(ValueError, "missing explicit"):
                sheet.indexProfile(index)
        index = fixtureIndex(); index["source"]["buildId"] = -1
        with self.assertRaisesRegex(ValueError, "unsigned 32-bit"):
            sheet.indexProfile(index)

    def testHistoricalAndCurrentAlgorithmsHaveExplicitMeanings(self):
        for reader, colour in ((4, 2), (5, 2), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3)):
            self.assertEqual(sheet.indexProfile(fixtureIndex(reader, colour))["reader"], reader)
        for reader, colour in ((6, 2), (6, 4), (7, 2), (8, 2), (9, 2), (10, 3), (4, 3)):
            with self.subTest(reader=reader, colour=colour), self.assertRaisesRegex(ValueError, "profile"):
                sheet.indexProfile(fixtureIndex(reader, colour))
        historical = fixtureIndex(4, 2, 8)
        historical["candidatePool"]["mode"] = "SPLIT_PER_COLOUR"
        historical["display"].update(algorithmBypassSwitch="SW9", rawCameraSwitch=None)
        profile = sheet.indexProfile(historical)
        self.assertEqual((profile["outputCapacity"], profile["comparisonSwitch"], profile["rawSwitch"]), (8, "SW9", None))
        current = sheet.indexProfile(fixtureIndex(count=8))
        self.assertEqual((current["outputCapacity"], current["comparisonSwitch"]), (16, "SW8"))

    def testActualRecordMustMatchIndexBuildAlgorithmModePoolAndDenominator(self):
        index = fixtureIndex()
        board = boardFor(index)
        record = dict(level="CAMERA_HW", initialStatus=board,
            observations=[dict(trial=1, status=copy.deepcopy(board))],
            trials=[dict(currentRequestSamples=30, printedDigitScore=dict(expected=300))])
        with tempfile.TemporaryDirectory(prefix="datasheet_record_") as folder:
            path = Path(folder) / "synthetic.json"
            def read(value):
                path.write_text(json.dumps(value), encoding="utf-8")
                return sheet.readRecord(index, "trials", path)
            self.assertEqual(read(record)[0], record)
            for key, value in (("readerAlgorithm", 5), ("colourAlgorithm", 2), ("poolLayout", "SPLIT_PER_COLOUR"),
                               ("bypassPerspective", True), ("orientationProfile", 1), ("rawDisplayActive", True)):
                bad = copy.deepcopy(record); bad["initialStatus"][key] = value
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, "profile|raw-camera"):
                    read(bad)
            bad = copy.deepcopy(record); bad["observations"][0]["status"]["readerAlgorithm"] = 5
            with self.assertRaisesRegex(ValueError, "observation0"):
                read(bad)
            bad = copy.deepcopy(record); bad["trials"][0]["printedDigitScore"]["expected"] = 240
            with self.assertRaisesRegex(ValueError, "denominator"):
                read(bad)
            bad = copy.deepcopy(record); bad["initialStatus"]["buildId"] += 1
            with self.assertRaisesRegex(ValueError, "board identity"):
                read(bad)

    def testRealCalibrationTraceIsRequiredWithoutHashGate(self):
        index = fixtureIndex()
        record = dict(level="CAMERA_HW", boardStatus=dict(decoded=boardFor(index)), command="calibrate")
        with tempfile.TemporaryDirectory(prefix="datasheet_binding_") as folder:
            path = Path(folder) / "synthetic.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            index["records"]["calibration"] = dict(path=str(path))
            with self.assertRaisesRegex(ValueError, "real-pixel frame trace"):
                sheet.readRecord(index, "calibration", None)

    def testMissingMeasurementsStayPendingInSourceBoundOnePagePdf(self):
        index = fixtureIndex(count=8)  # Shared16 capacity must not imply ten signs.
        with tempfile.TemporaryDirectory(prefix="datasheet_pdf_") as folder:
            source = Path(folder) / "index.json"
            source.write_text(json.dumps(index), encoding="utf-8")
            output = Path(folder) / "synthetic.pdf"
            with patch.object(sys, "argv", ["render_member_b_datasheet.py", "--index", str(source), "--out", str(output)]), redirect_stdout(io.StringIO()):
                sheet.main()
            pdf = PdfReader(output)
            self.assertEqual(len(pdf.pages), 1)
            text = " ".join(pdf.pages[0].extract_text().split())
            for phrase in ("Reader6/colour3", "candidate-bbox component ownership", "8 declared printed signs", "SW8=0", "SW9 is separate", "PENDING"):
                self.assertIn(phrase, text)
            self.assertNotIn("Reader5 should", text)
            self.assertNotIn("ten printed signs", text)
            sidecar = json.loads(output.with_suffix(".pdf.json").read_text())
            self.assertEqual(sidecar["buildId"], index["source"]["buildId"])
            self.assertEqual(sidecar["index"], str(source))
            self.assertEqual(sidecar["level"], "DOCUMENT_GENERATION_NOT_HARDWARE_VALIDATION")
            self.assertIsNone(sidecar["hardware"])


if __name__ == "__main__":
    unittest.main()
