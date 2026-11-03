"""Synthetic status/annotation checks, not camera or digit-reader evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools/lib"), str(ROOT / "tools"), str(ROOT / "tests/python")]
from hardware_measurement import measureTrials, sceneExpectations, TrackingAcquisition
from test_hardware_measurement import FixtureRunner
from test_sw9_comparison import fixture as comparisonFixture, summaries
from compare_sw9_trials import compareTrials


def truthFixture():
    signs = [(False, 1), (False, 2), *[(True, digit) for digit in (1, 1, 2, 2, 3, 4, 5, 6)]]
    return {"schema": "echo7-test-only-printed-regions-v1", "coordinateSystem": "native320x240",
            "annotation": "SYNTHETIC UNIT TEST; NOT HARDWARE", "sourceSha256": "c" * 64,
            "regions": [{"isBlue": colour, "digit": digit, "bbox": [5+index*30, 20, 25+index*30, 50]}
                        for index, (colour, digit) in enumerate(signs)]}


def markersFor(truth):
    return [{"accepted": True, "isBlue": r["isBlue"], "digit": r["digit"],
             **dict(zip(("xMin", "yMin", "xMax", "yMax"), r["bbox"]))} for r in truth["regions"]]


class DuplicateRunner(FixtureRunner):
    def __init__(self, folder, fault=None, uniqueAcquire=False):
        super().__init__(folder)
        self.truth = truthFixture()
        path = Path(folder) / "synthetic_truth.json"
        path.write_text(json.dumps(self.truth))
        self.args.truth_regions = path
        self.fault, self.uniqueAcquire, self.ordinal = fault, uniqueAcquire, 0

    def control(self, command=0):
        result = super().control(command)
        state = result["decoded"]
        state["markers"] = markersFor(self.truth)
        state["frameGood"] = True
        report = state["targetReport"]
        report.update(reason=0, centreU=50, centreV=100, boxWidth=30, boxHeight=40, quality=255)
        if self.bay in (1, 2):
            report.update(reason=4, ambiguous=True, observed=False, locked=False,
                          centreU=0, centreV=0, boxWidth=0, boxHeight=0, quality=0)
        if command >> 24 == 1:
            self.ordinal = 0
            if self.uniqueAcquire:
                report["requestTag"] -= 1
        elif command == 0 and self.tag:
            self.ordinal += 1
            if self.uniqueAcquire and self.bay >= 3:
                report["locked"] = self.ordinal >= 3
                report["reason"] = 0 if report["locked"] else 2
        if self.fault and command == 0 and self.tag:
            self.fault(state, self.frame, self.bay)
        return result


class DuplicateSceneTests(unittest.TestCase):
    def testDeclaredDuplicateSceneScoresAllTenAndRequiresAmbiguity(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = DuplicateRunner(folder, uniqueAcquire=True)
            measureTrials(runner, 1)
            summary = runner.result["trials"][0]
            self.assertEqual(summary["printedDigitScore"]["correct"], 300)
            self.assertEqual(summary["printedDigitScore"]["expected"], 300)
            self.assertEqual(summary["expectedAmbiguousSamples"], 10)
            self.assertEqual(summary["acquiringSamples"], 8)
            self.assertEqual(summary["lockedSamples"], 12)
            self.assertEqual(runner.result["expectedScene"]["blueMatchesByBay"],
                             {"1": 2, "2": 2, "3": 1, "4": 1, "5": 1, "6": 1})
            self.assertFalse(runner.result["failures"])
            self.assertEqual(len(runner.result["strictAllLockedFailures"]), 18)
            self.assertTrue(runner.cleared)

    def testMissingCopyWrongNumberFakeLockAndBadFrameRemainFailures(self):
        def missing(state): state["markers"][3]["accepted"] = False
        def wrong(state): state["markers"][3]["digit"] = 6
        def fakeLock(state): state["targetReport"].update(ambiguous=False, observed=True, locked=True, reason=0)
        def geometry(state): state["targetReport"]["centreU"] = 1
        def badFrame(state): state.update(frameGood=False, candidateOverflow=True)
        faults = [(missing, "typed_marker_set"), (wrong, "printed_digit_region_mismatch"),
                  (fakeLock, "expected_target_ambiguity"), (geometry, "expected_target_ambiguity"),
                  (badFrame, "captured_frame_bad")]
        for apply, issue in faults:
            with self.subTest(fault=apply.__name__), tempfile.TemporaryDirectory() as folder:
                runner = DuplicateRunner(folder, lambda state, frame, bay: apply(state) if frame == 2 else None)
                with self.assertRaisesRegex(RuntimeError, "all 30 retained"):
                    measureTrials(runner, 1)
                self.assertEqual(len(runner.result["observations"]), 30)
                self.assertIn(issue, runner.result["observations"][0]["issues"])
                retained = json.loads((Path(folder) / "trial_observations.json").read_text())
                self.assertIn(issue, retained[0]["issues"])

    def testUndeclaredOrUnexpectedAmbiguityCannotPassUniqueScene(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = DuplicateRunner(folder)
            runner.args.truth_regions = None
            with self.assertRaises(RuntimeError): measureTrials(runner, 1)
            self.assertIn("target_unreliable_or_unlocked", runner.result["observations"][0]["issues"])
        def ambiguousUnique(state, frame, bay):
            if frame == 12:
                state["targetReport"].update(ambiguous=True, observed=False, locked=False, reason=4,
                    centreU=0, centreV=0, boxWidth=0, boxHeight=0, quality=0)
        with tempfile.TemporaryDirectory() as folder:
            runner = DuplicateRunner(folder, ambiguousUnique)
            with self.assertRaises(RuntimeError): measureTrials(runner, 1)
            self.assertIn("target_unreliable_or_unlocked", runner.result["observations"][10]["issues"])

    def testTruthCannotDropBayOrAddUnsupportedDigitOrWrongCoordinates(self):
        base = truthFixture()
        for change in (lambda truth: truth["regions"].pop(),
                       lambda truth: truth["regions"][2].update(digit=7),
                       lambda truth: truth["regions"][2].update(bbox=[0, 0, 320, 20]),
                       lambda truth: truth["regions"][0].update(digit=2)):
            truth = copy.deepcopy(base)
            change(truth)
            with self.assertRaises(ValueError): sceneExpectations(truth)

    def oldAmbiguous(self, frame=101, timeUs=210000, captured=199900):
        return {"frameId": frame, "timeUs": timeUs, "captureStartUs": captured, "freshAtSnapshot": True,
                "status": {"activeCfgVersion": 1}, "activeRequest": {"operation": 1, "requestTag": 7, "bayId": 3},
                "targetReport": {"frameId": frame, "captureStartUs": captured, "requestTag": 6, "bayId": 1,
                    "configVersion": 1, "frameGood": True, "targetSelected": True, "reason": 4,
                    "ambiguous": True, "observed": 0, "locked": 0, "centreU": 0, "centreV": 0,
                    "boxWidth": 0, "boxHeight": 0, "quality": 0}}

    def tracker(self):
        return TrackingAcquisition(7, 3, 1, self.oldAmbiguous(100, 200000, 160000),
                                   sceneBlueCounts={1: 2, 2: 2, 3: 1})

    def testPreviousAmbiguousReportOnlyDrainsInsideImmutableTimestampBoundary(self):
        tracker = self.tracker()
        result = tracker.observe(self.oldAmbiguous())
        self.assertTrue(result["expectedPreviousAmbiguousReport"])
        self.assertFalse(result["expectedAmbiguous"])
        self.assertIsNone(tracker.firstFrame)
        current = self.oldAmbiguous(102)
        current["targetReport"].update(requestTag=7, bayId=3, reason=2, ambiguous=False, observed=True)
        tracker.observe(current)
        self.assertFalse(tracker.observe(self.oldAmbiguous())["expectedPreviousAmbiguousReport"])
        undeclared = TrackingAcquisition(7, 3, 1, self.oldAmbiguous(100, 200000, 160000))
        self.assertFalse(undeclared.observe(self.oldAmbiguous())["expectedPreviousAmbiguousReport"])

    def testPreviousAmbiguityRejectsWrongTagFutureLateGeometryConfigAndBadFrame(self):
        for changes, top in (({"requestTag": 5}, {}), ({"centreU": 1}, {}), ({"quality": 1}, {}),
                             ({"frameGood": False}, {}), ({"configVersion": 2}, {}),
                             ({"captureStartUs": 200001}, {"captureStartUs": 200001}),
                             ({}, {"timeUs": 350001}), ({}, {"freshAtSnapshot": False})):
            with self.subTest(changes=changes, top=top):
                state = self.oldAmbiguous()
                state.update(top)
                state["targetReport"].update(changes)
                self.assertFalse(self.tracker().observe(state)["expectedPreviousAmbiguousReport"])

    def testTrialRetainsOldAmbiguitiesWithoutCountingThemAsCurrentReports(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = DuplicateRunner(folder)
            original = runner.control
            previous, pending, selectionTime = None, None, None
            def control(command=0):
                nonlocal previous, pending, selectionTime
                result = original(command)
                state = result["decoded"]
                state["timeUs"] = 100000 + state["frameId"]*40000
                state["captureStartUs"] = state["timeUs"]-20000
                state["targetReport"]["captureStartUs"] = state["captureStartUs"]
                state["activeRequest"].update(operation=1, bayId=runner.bay)
                if command >> 24 == 1 and runner.bay in (2, 3):
                    pending = copy.deepcopy(previous["targetReport"])
                    selectionTime = state["timeUs"]
                    state["targetReport"] = copy.deepcopy(pending)
                elif command == 0 and pending is not None:
                    state["captureStartUs"] = selectionTime-1000
                    state["targetReport"] = pending
                    state["targetReport"].update(frameId=state["frameId"], captureStartUs=state["captureStartUs"])
                    pending = None
                if command == 0:
                    previous = copy.deepcopy(state)
                return result
            runner.control = control
            measureTrials(runner, 1)
            self.assertEqual(len(runner.result["observations"]), 32)
            summary = runner.result["trials"][0]
            self.assertEqual(summary["currentRequestSamples"], 30)
            self.assertEqual(summary["previousAmbiguousTransitionSamples"], 2)
            old = [r for r in runner.result["observations"] if not r["currentRequestSample"]]
            self.assertEqual(len(old), 2)
            self.assertTrue(all(r["trackingAssessment"]["expectedPreviousAmbiguousReport"] for r in old))
            self.assertFalse(runner.result["failures"])

    def testComparisonDenominatorUsesAllDeclaredCopies(self):
        normal, bypass = comparisonFixture(0), comparisonFixture(1)
        truth = truthFixture()
        for data in (normal, bypass):
            data["truthRegions"]["annotations"] = truth
            for state in [data["initialStatus"], *[r["status"] for r in data["requestSelections"]],
                          *[r["status"] for r in data["observations"]]]:
                state["markers"] = markersFor(truth)
            for row in data["observations"]:
                row["regionScore"].update(correct=10, expected=10)
            summaries(data)
        result, code = compareTrials(normal, bypass, "Synthetic test conditions only")
        self.assertEqual(code, 0)
        self.assertEqual(result["modes"]["normal"]["printedDigitScoreCurrent"]["expected"], 900)
        self.assertEqual(result["modes"]["normal"]["expectedScene"]["printedRegionCount"], 10)


if __name__ == "__main__":
    unittest.main()
