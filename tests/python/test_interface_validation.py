"""Offline decisions only; never creates a client or calls JTAG."""
import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "tools"), str(ROOT / "tools/lib")]
from validate_member_c_interface import (InterfaceFailure, checkGeometry, checkQueryBatch,
    productionProfile, sameFramePositions, trackingAssessment)
import validate_member_c_interface as validation


def item(markerType=2, digit=1, **changes):
    result = dict(markerType=markerType, digit=digit, requestTag=8, frameId=65535,
        captureStartUs=0xfffffff0, configVersion=3, count=1, index=0, last=1, reason=0,
        centreU=50, centreV=268, boxWidth=21, boxHeight=40, quality=211)
    result.update(changes)
    return result


def batch(rows):
    return {"completed": True, "results": rows, "items": rows}


def trackedState():
    request = dict(operation=1, requestTag=8, markerType=2, digit=1)
    report = item(frameGood=1, observed=1, locked=1, ambiguous=0, targetSelected=1)
    # x31..70 deliberately has a half-pixel native centre. Rotating the
    # already-rounded native centre gives269; rotating the bbox gives268.
    marker = dict(accepted=True, isBlue=False, digit=1, xMin=31, xMax=70,
                  yMin=40, yMax=60, quality=211)
    return dict(activeRequest=request, targetReport=report, frameId=65535, timeUs=32,
        configVersion=3, status=dict(activeCfgVersion=3, perceptionReady=True, interactionBusy=False),
        markers=[marker], calibrationReferenceValid=False)


class InterfaceValidationTests(unittest.TestCase):
    def testFirstAdvertisedReaderPinsTheRunWithoutPinningCalibratedThresholds(self):
        for reader in (5, 6, 7, 8, 9):
            packet = dict(readerAlgorithm=reader, colourAlgorithm=3, whiteMinimum=84,
                          whiteMaxSpread=64, redMinimum=33, blueMinimum=20)
            profile = productionProfile(packet)
            self.assertEqual(profile["readerAlgorithm"], reader)
            self.assertEqual(productionProfile({**packet, "redMinimum": 40, "blueMinimum": 35}, profile), profile)
            with self.assertRaisesRegex(InterfaceFailure, "profile changed"):
                productionProfile({**packet, "readerAlgorithm": 6 if reader == 5 else 5}, profile)
            for changes in (dict(readerAlgorithm=4), dict(readerAlgorithm=10), dict(colourAlgorithm=2),
                            dict(colourAlgorithm=4), dict(whiteMinimum=96), dict(whiteMaxSpread=63)):
                with self.subTest(reader=reader, changes=changes), self.assertRaisesRegex(InterfaceFailure, "requires reader"):
                    productionProfile({**packet, **changes})

    def testRegistrationRetainsActualProfileAndStillRejectsBuildChange(self):
        # Exercise the registration boundary without constructing a client or
        # invoking any external process. Its normal result file is retained.
        for reader in (5, 6, 7, 8, 9):
            with tempfile.TemporaryDirectory(prefix="interface_profile_") as folder:
                runner = object.__new__(validation.HardwareValidation)
                runner.out = Path(folder)
                runner.result = dict(calls=[], expectedBuildId=0x12345678)
                runner.target = dict(cable="SYNTHETIC_NO_JTAG", device="2")
                packet = dict(buildId=0x12345678, debugSchemaVersion=8, contractVersion=3,
                    readerAlgorithm=reader, colourAlgorithm=3, whiteMinimum=84, whiteMaxSpread=64,
                    rawCameraMode=False, rawModeRequested=False, rawDisplayActive=False)
                child = dict(outputDirectory=str(Path(folder) / "child"), target=runner.target,
                    exitCode=0, status="PASS", boardStatus=dict(decoded=packet))
                with patch.object(runner, "remaining", return_value=30):
                    runner.register("initial", child)
                    self.assertEqual(json.loads((Path(folder) / "result.json").read_text())["algorithmProfile"],
                                     productionProfile(packet))
                    packet["readerAlgorithm"] = 6 if reader == 5 else 5
                    with self.assertRaisesRegex(InterfaceFailure, "profile changed"):
                        runner.register("changed", child)
                    packet["readerAlgorithm"] = reader
                    packet["buildId"] += 1
                    with self.assertRaisesRegex(InterfaceFailure, "buildId"):
                        runner.register("wrongBuild", child)

    def testSameFrameBBoxRotationAndUnsignedTimeWrap(self):
        state = trackedState()
        self.assertEqual(sameFramePositions(state, (2, 1))[0]["centreV"], 268)
        self.assertEqual(trackingAssessment(state, state["activeRequest"]), "PASS")
        state["targetReport"]["centreV"] = 269
        with self.assertRaisesRegex(InterfaceFailure, "bbox"):
            trackingAssessment(state, state["activeRequest"])

    def testWrongTypeWithCurrentTagIsFailureNotAPollingRetry(self):
        state = trackedState()
        state["targetReport"]["markerType"] = 1
        with self.assertRaisesRegex(InterfaceFailure, "type/digit"):
            trackingAssessment(state, state["activeRequest"])
        state["targetReport"]["requestTag"] = 7
        self.assertEqual(trackingAssessment(state, state["activeRequest"]), "WAIT_CURRENT_REQUEST")

    def testUnknownFrameConfigAndExpiredDataCannotPass(self):
        for field, value, expected in (("frameId", 0, "WAIT_SAME_FRAME"),
                                       ("configVersion", 2, "WAIT_CURRENT_CONFIG")):
            state = trackedState(); state["targetReport"][field] = value
            self.assertEqual(trackingAssessment(state, state["activeRequest"]), expected)
        state = trackedState(); state["timeUs"] = 200000
        self.assertEqual(trackingAssessment(state, state["activeRequest"]), "WAIT_READY_FRESH_REPORT")
        state = trackedState(); state["activeRequest"] = {**state["activeRequest"], "requestTag": 9}
        with self.assertRaisesRegex(InterfaceFailure, "request changed"):
            trackingAssessment(state, trackedState()["activeRequest"])

    def testDuplicatesNeedZeroMeasurementsAndCannotLockEvenWhileWaitingForAmbiguity(self):
        state = trackedState()
        state["markers"].append({**state["markers"][0], "xMin": 100, "xMax": 139})
        with self.assertRaisesRegex(InterfaceFailure, "exactly one"):
            trackingAssessment(state, state["activeRequest"], "ambiguous")
        state["targetReport"].update(observed=0, locked=0, ambiguous=1, reason=4,
            centreU=0, centreV=0, boxWidth=0, boxHeight=0, quality=0)
        self.assertEqual(trackingAssessment(state, state["activeRequest"], "ambiguous"), "PASS")
        state["targetReport"]["quality"] = 1
        with self.assertRaisesRegex(InterfaceFailure, "leaked"):
            trackingAssessment(state, state["activeRequest"], "ambiguous")

    def testReferenceUsesActualBlueBoxAndAssociatedQuality(self):
        state = trackedState()
        state["markers"].append(dict(accepted=False, isBlue=True, digit=15,
            xMin=20, xMax=90, yMin=70, yMax=80, quality=0))
        state.update(calibrationReferenceValid=True, calibrationReferenceMarkerIndex=1,
                     calibrationReferenceQuality=211)
        measured = sameFramePositions(state, (3, 15))
        self.assertEqual(measured, [dict(centreU=75, centreV=264, boxWidth=11, boxHeight=71, quality=211)])
        state["markers"][1]["accepted"] = True
        with self.assertRaisesRegex(InterfaceFailure, "reference region"):
            sameFramePositions(state, (3, 15))

    def testClearMustInvalidatePublicMeasurements(self):
        state = trackedState()
        state["activeRequest"].update(operation=0, markerType=0, digit=15)
        state["targetReport"].update(markerType=0, digit=15, targetSelected=0, reason=1,
            observed=0, locked=0, ambiguous=0, centreU=0, centreV=0, boxWidth=0, boxHeight=0, quality=0)
        self.assertEqual(trackingAssessment(state, state["activeRequest"], "clear"), "PASS")
        state["targetReport"]["centreU"] = 1
        with self.assertRaisesRegex(InterfaceFailure, "CLEAR"):
            trackingAssessment(state, state["activeRequest"], "clear")

    def testListReferenceQualityAndDistinctCoordinates(self):
        rows = [item(count=2, index=0, last=0), item(3, 15, count=2, index=1, last=1, centreU=90)]
        self.assertEqual(checkQueryBatch(batch(rows), calibrationPair=True)["count"], 2)
        rows[1]["quality"] = 210
        with self.assertRaisesRegex(InterfaceFailure, "BJ quality"):
            checkQueryBatch(batch(rows), calibrationPair=True)
        rows[1]["quality"] = 211; rows[1]["centreU"] = 50
        with self.assertRaisesRegex(InterfaceFailure, "red1 centre"):
            checkQueryBatch(batch(rows), calibrationPair=True)

    def testDuplicateGetIsAllowedButSceneExpectationMustActuallyMatch(self):
        rows = [item(1, 1, count=2, index=0, last=0, reason=1),
                item(1, 1, count=2, index=1, last=1, reason=1, centreU=90)]
        self.assertEqual(checkQueryBatch(batch(rows), selector=(1, 1), duplicateBays=[1])["count"], 2)
        with self.assertRaisesRegex(InterfaceFailure, "blue2"):
            checkQueryBatch(batch(rows), selector=(1, 1), duplicateBays=[2])
        with self.assertRaisesRegex(InterfaceFailure, "another marker"):
            checkQueryBatch(batch(rows), selector=(2, 1))
        rows[1]["centreU"] = rows[0]["centreU"]
        with self.assertRaisesRegex(InterfaceFailure, "same typed position"):
            checkQueryBatch(batch(rows), selector=(1, 1))

    def testEmptyBadStaleOrInconsistentQueryDoesNotPassDemoAcceptance(self):
        for reason in (2, 3, 4, 5, 6):
            with self.assertRaisesRegex(InterfaceFailure, "no usable"):
                checkQueryBatch(batch([item(count=0, reason=reason)]))
        for change in (dict(index=1), dict(last=0), dict(count=2), dict(quality=0), dict(centreU=0)):
            with self.subTest(change=change), self.assertRaises(InterfaceFailure):
                checkQueryBatch(batch([item(**change)]))

    def testMissingBuildIsStructuredEnvironmentBlockWithoutCallingHardware(self):
        with tempfile.TemporaryDirectory(prefix="interface_missing_build_") as folder:
            output = io.StringIO()
            with patch.object(validation.echo7, "WORK", Path(folder)), \
                    patch.object(validation.HardwareValidation, "execute", side_effect=AssertionError("must not touch hardware")) as execute, \
                    redirect_stdout(output):
                code = validation.main([])
            self.assertEqual(code, 2)
            execute.assert_not_called()
            record = json.loads(output.getvalue())
            self.assertEqual(record["status"], "BLOCKED")
            self.assertEqual(record["calls"], [])
            self.assertEqual(json.loads((Path(record["outputDirectory"]) / "result.json").read_text())["exitCode"], 2)

    def testInvalidExpectedBuildIsStructuredFailureWithoutCallingHardware(self):
        with tempfile.TemporaryDirectory(prefix="interface_invalid_build_") as folder:
            output = io.StringIO()
            with patch.object(validation.echo7, "WORK", Path(folder)), \
                    patch.object(validation.HardwareValidation, "execute", side_effect=AssertionError("must not touch hardware")) as execute, \
                    redirect_stdout(output):
                code = validation.main(["--expected-build-id", "0x100000000"])
            self.assertEqual(code, 1)
            execute.assert_not_called()
            record = json.loads(output.getvalue())
            self.assertEqual(record["status"], "FAIL")
            self.assertEqual(record["calls"], [])


if __name__ == "__main__":
    unittest.main()
