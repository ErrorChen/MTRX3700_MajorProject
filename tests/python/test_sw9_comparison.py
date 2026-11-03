"""Synthetic comparison fixtures only: these are never camera/VGA evidence."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from compare_sw9_trials import compareTrials


def summaries(data):
    """Build fixture transport summaries from deliberately chosen score records."""
    rows = data["observations"]
    data["failures"] = [{"index": index, "frameId": row["status"]["frameId"], "issues": row["issues"]}
                        for index, row in enumerate(rows) if row["issues"]]
    data["status"] = "FAIL" if data["failures"] else "PASS"
    data["exitCode"] = int(bool(data["failures"]))
    data["trialTransport"]["completion"]["statusRecords"] = len(rows)
    data["trials"] = []
    for trial in (1, 2, 3):
        allRows = [row for row in rows if row["trial"] == trial]
        current = [row for row in allRows if row["currentRequestSample"]]
        data["trials"].append({"trial": trial, "currentRequestSamples": len(current),
            "allObservedSamples": len(allRows),
            "modeValues": [int(data["initialStatus"]["bypassPerspective"])],
            "configurationVersions": [data["initialStatus"]["configVersion"]],
            "printedDigitScore": {key: sum(row["regionScore"][key] for row in current)
                                  for key in ("correct", "expected", "missing", "wrongOrAmbiguous", "outside")},
            "captureToCompletionUs": {"minimum": min(row["status"]["processingLatencyUs"] for row in allRows),
                                      "maximum": max(row["status"]["processingLatencyUs"] for row in allRows)}})


def fixture(mode):
    regions = [{"isBlue": index >= 2, "digit": index - 1 if index >= 2 else index + 1,
                "bbox": [10 + index * 30, 10, 25 + index * 30, 30]} for index in range(8)]
    markers = [{"accepted": True, "isBlue": region["isBlue"], "digit": region["digit"],
                "xMin": region["bbox"][0], "yMin": 10, "xMax": region["bbox"][2], "yMax": 30}
               for region in regions]
    state = {"schema": "EBP1", "debugSchemaVersion": 4, "contractVersion": 2, "buildId": 0x5633257e,
        "orientationProfile": 0, "redMinimum": 33, "blueMinimum": 28, "readerAlgorithm": 4,
        "colourAlgorithm": 2, "whiteMinimum": 84, "whiteMaxSpread": 64, "whiteMode": "FIXTURE",
        "whiteThresholdExpression": "fixture", "whiteAnchorThresholdExpression": "fixture",
        "whiteAnchorMinimum": 96, "candidateSizePruning": True, "activeCandidateCapacity": 12,
        "outputCandidateCapacity": 8, "configVersion": 4 + mode, "bypassPerspective": bool(mode),
        "status": {"activeCfgVersion": 4 + mode}, "frameId": 98, "captureStartUs": 1_000_000,
        "completionUs": 1_043_000, "processingLatencyUs": 43_000, "markers": markers,
        "targetReport": {"frameId": 98, "requestTag": 0, "bayId": 15}}
    data = {"schema": "echo7-cli-v1", "command": "test", "level": "CAMERA_HW",
        "inputSource": "LIVE_CAMERA_JTAG_SAMPLED_TRIALS", "clearSent": True,
        "transport": "ONE_BOUNDED_JTAG_SESSION", "runnerSha256": "a" * 64,
        "target": {"cable": "SYNTHETIC", "device": "SYNTHETIC", "index": 2},
        "initialStatus": state, "requestSelections": [], "observations": [],
        "trialTransport": {"returnCode": 0, "completion": {"trials": 3, "statusRecords": 90},
                           "completeRecords": 110, "assessedRecords": 110},
        "truthRegions": {"sha256": "b" * 64, "annotations": {
            "schema": "echo7-test-only-printed-regions-v1", "coordinateSystem": "native320x240",
            "regions": regions, "sourceSha256": "c" * 64,
            "annotation": "SYNTHETIC UNIT TEST; NOT HARDWARE"}}}
    frame = 100
    for trial in (1, 2, 3):
        for bay in range(1, 7):
            tag = trial * 10 + bay
            data["requestSelections"].append({"trial": trial, "requestedBay": bay,
                                             "requestTag": tag, "status": copy.deepcopy(state)})
            for _ in range(5):
                observed = copy.deepcopy(state)
                observed["frameId"] = frame
                observed["targetReport"] = {"frameId": frame, "requestTag": tag, "bayId": bay}
                observed["captureStartUs"] += frame * 40_000
                observed["completionUs"] += frame * 40_000
                data["observations"].append({"trial": trial, "requestedBay": bay, "requestTag": tag,
                    "currentRequestSample": True, "issues": [], "status": observed,
                    "regionScore": {"correct": 8, "expected": 8, "missing": 0, "wrongOrAmbiguous": 0, "outside": 0}})
                frame += 1
    summaries(data)
    return data


def missingSix(row):
    row["status"]["markers"][-1]["accepted"] = False
    row["regionScore"].update(correct=7, missing=1)
    row["issues"] = ["typed_marker_set", "printed_digit_region_mismatch"]


def tenSignFixture(mode):
    """Two additional physical blue signs, each with its own scoring region.

    Their labels are test expectations only. Both modes retain all ten regions
    and all ninety current-request observations, including any failed ones.
    """
    data = fixture(mode)
    additions = [{"isBlue": True, "digit": digit, "bbox": [10 + offset * 30, 60, 25 + offset * 30, 80]}
                 for offset, digit in enumerate((1, 2))]
    data["truthRegions"]["annotations"]["regions"].extend(additions)
    data["truthRegions"]["sha256"] = "d" * 64
    states = [data["initialStatus"], *[selection["status"] for selection in data["requestSelections"]],
              *[row["status"] for row in data["observations"]]]
    for state in states:
        state.update(debugSchemaVersion=7, buildId=0xa9caa52f, readerAlgorithm=5,
                     activeCandidateCapacity=15, outputCandidateCapacity=16, poolLayout="SHARED_TOTAL")
        state["markers"].extend({"accepted": True, "isBlue": True, "digit": region["digit"],
                                  "xMin": region["bbox"][0], "yMin": region["bbox"][1],
                                  "xMax": region["bbox"][2], "yMax": region["bbox"][3]}
                                 for region in additions)
    for row in data["observations"]:
        row["regionScore"].update(correct=10, expected=10)
    summaries(data)
    return data


def typedFixture(mode):
    """Explicit new synthetic schema8/v3 records, not relabelled board evidence."""
    data=tenSignFixture(mode)
    states=[data["initialStatus"],*[s["status"] for s in data["requestSelections"]],
            *[r["status"] for r in data["observations"]]]
    for state in states:
        state.update(debugSchemaVersion=8,contractVersion=3)
        report=state["targetReport"]
        report["digit"]=report.pop("bayId")
        report["markerType"]=1 if report["digit"] in range(1,7) else 0
    return data


class Sw9ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.normal, self.bypass = fixture(0), fixture(1)

    def compare(self, conditions="Synthetic fixture conditions only"):
        return compareTrials(self.normal, self.bypass, conditions)

    def testCurrentTypedContractRetainsAllComparisonRecords(self):
        self.normal,self.bypass=typedFixture(0),typedFixture(1)
        result,code=self.compare()
        self.assertEqual(code,0)
        self.assertEqual(result["difference"]["currentExpectedPerMode"],900)
        self.assertEqual(len(result["modes"]["normal"]["observations"]),90)
        self.bypass["observations"][0]["status"]["targetReport"]["markerType"]=2
        result,code=self.compare()
        self.assertEqual(code,1)
        self.assertIn("current-request label",result["comparisonValidity"]["issues"][0])

    def testContractMustMatchSchemaAndLegacyMissingVersionMeansTwo(self):
        for data in (self.normal,self.bypass):
            for state in [data["initialStatus"],*[s["status"] for s in data["requestSelections"]],
                          *[r["status"] for r in data["observations"]]]:
                state.pop("contractVersion")
        self.assertEqual(self.compare()[1],0)
        self.normal,self.bypass=typedFixture(0),typedFixture(1)
        self.bypass["observations"][0]["status"]["contractVersion"]=2
        result,code=self.compare()
        self.assertEqual(code,1)
        self.assertIn("contract version conflicts",result["comparisonValidity"]["issues"][0])

    def testCompletePairAllowsDifferentConfigurationVersions(self):
        result, code = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "COMPARISON_VALID")
        self.assertEqual(result["modes"]["normal"]["configVersion"], 4)
        self.assertEqual(result["modes"]["bypass"]["configVersion"], 5)
        self.assertEqual(result["modes"]["normal"]["printedDigitScoreCurrent"]["correct"], 720)
        self.assertEqual(result["difference"]["currentExpectedPerMode"], 720)
        self.assertEqual(result["modes"]["bypass"]["acceptance"]["overall"], "PASS")

    def testTenSignsUseNineHundredLabelledOpportunities(self):
        self.normal, self.bypass = tenSignFixture(0), tenSignFixture(1)
        result, code = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(result["difference"]["currentExpectedPerMode"], 900)
        for mode in result["modes"].values():
            self.assertEqual(mode["printedDigitScoreCurrent"]["expected"], 900)
            self.assertEqual([trial["printedDigitScore"]["expected"] for trial in mode["trials"]], [300] * 3)

    def testTenSignFailuresDoNotReduceTheDenominator(self):
        self.normal, self.bypass = tenSignFixture(0), tenSignFixture(1)
        for row in self.bypass["observations"]:
            row["status"]["markers"][7]["accepted"] = False
            row["regionScore"].update(correct=9, missing=1)
            row["issues"] = ["typed_marker_set", "printed_digit_region_mismatch"]
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(result["difference"]["currentExpectedPerMode"], 900)
        self.assertEqual(result["difference"]["currentCorrectNormalMinusBypass"], 90)
        self.assertEqual(result["modes"]["bypass"]["acceptance"]["overall"], "FAIL")
        self.assertEqual(len(result["modes"]["bypass"]["failures"]), 90)

    def testDifferentSceneDenominatorsCannotBeCompared(self):
        self.bypass = tenSignFixture(1)
        result, code = self.compare()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "INVALID_COMPARISON")
        self.assertIn("different scoring denominators", result["comparisonValidity"]["issues"][0])
        self.assertNotIn("difference", result)

    def testFabricatedTenSignDenominatorIsRejected(self):
        self.normal, self.bypass = tenSignFixture(0), tenSignFixture(1)
        for row in self.bypass["observations"]:
            row["regionScore"]["expected"] = 8
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 1)
        self.assertIn("recorded printed score differs", result["comparisonValidity"]["issues"][0])

    def testHistoricalPairCannotInferMatchedConditions(self):
        result, code = self.compare("")
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "UNCONFIRMED_CONDITIONS")
        self.assertFalse(result["difference"]["interpretationAllowed"])

    def testFailedBypassRemainsValidComparisonAndRetainsAllFailures(self):
        for row in self.bypass["observations"]:
            missingSix(row)
        summaries(self.bypass)
        before = copy.deepcopy(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        mode = result["modes"]["bypass"]
        self.assertEqual(mode["recordedRunnerStatus"], "FAIL")
        self.assertEqual(mode["acceptance"]["overall"], "FAIL")
        self.assertEqual(mode["trials"][0]["correctPercent"], 87.5)
        self.assertEqual(len(mode["observations"]), 90)
        self.assertEqual(len(mode["failures"]), 90)
        self.assertEqual(self.bypass, before)

    def testFrozen95PercentTargetDoesNotEraseStrictRunnerFailure(self):
        for offset in (0, 30, 60):
            for row in self.bypass["observations"][offset:offset + 12]:
                missingSix(row)
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        acceptance = result["modes"]["bypass"]["acceptance"]
        self.assertEqual(acceptance["recognitionTarget"], "PASS")
        self.assertEqual(acceptance["strictHardwareRunner"], "FAIL")
        self.assertEqual(acceptance["overall"], "FAIL")

    def testWrongIdFailsEvenAbove95Percent(self):
        row = self.bypass["observations"][0]
        row["status"]["markers"][-1]["digit"] = 5
        row["regionScore"].update(correct=7, wrongOrAmbiguous=1)
        row["issues"] = ["printed_digit_region_mismatch"]
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        self.assertGreater(result["modes"]["bypass"]["trials"][0]["correctPercent"], 95)
        self.assertEqual(result["modes"]["bypass"]["acceptance"]["recognitionTarget"], "FAIL")

    def testModeChangeInOldRequestDrainCannotBeHidden(self):
        drain = copy.deepcopy(self.bypass["observations"][0])
        drain["currentRequestSample"] = False
        drain["status"]["frameId"] = 99
        drain["status"]["targetReport"].update(frameId=99, requestTag=0, bayId=15)
        self.bypass["observations"].insert(0, drain)
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        self.assertEqual(result["modes"]["bypass"]["nonCurrentObservations"], 1)
        self.assertEqual(result["modes"]["bypass"]["printedDigitScoreCurrent"]["expected"], 720)
        drain["status"]["bypassPerspective"] = False
        self.assertEqual(self.compare()[1], 1)

    def testAllObservationLatencyIncludesDrainAndUnsignedTimeWrap(self):
        drain = copy.deepcopy(self.bypass["observations"][0])
        drain["currentRequestSample"] = False
        state = drain["status"]
        state["frameId"] = 99
        state["targetReport"].update(frameId=99, requestTag=0, bayId=15)
        state.update(captureStartUs=0xffff0000, completionUs=(0xffff0000 + 150001) & 0xffffffff,
                     processingLatencyUs=150001)
        drain["issues"] = ["capture_to_completion_latency"]
        self.bypass["observations"].insert(0, drain)
        summaries(self.bypass)
        result, code = self.compare()
        self.assertEqual(code, 0)
        mode = result["modes"]["bypass"]
        self.assertEqual(mode["latencyCurrentRequests"]["maximumUs"], 43000)
        self.assertEqual(mode["latencyAllObservations"]["maximumUs"], 150001)
        self.assertEqual(mode["acceptance"]["latencyTarget"], "FAIL")

    def testDuplicateHeldFrameAndBackwardsFrameFail(self):
        for frame in (100, 99):
            with self.subTest(frame=frame):
                self.bypass = fixture(1)
                self.bypass["observations"][1]["status"]["frameId"] = frame
                self.assertEqual(self.compare()[1], 1)

    def testNativeFrameCounterWrapIsLegal(self):
        for index, row in enumerate(self.bypass["observations"]):
            frame = (65520 + index) & 65535
            row["status"]["frameId"] = frame
            row["status"]["targetReport"]["frameId"] = frame
        self.assertEqual(self.compare()[1], 0)

    def testIncompleteTransportOrMissingSampleCannotPass(self):
        self.bypass["trialTransport"]["completion"]["statusRecords"] = 91
        self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["observations"].pop()
        summaries(self.bypass)
        self.assertEqual(self.compare()[1], 1)

    def testChangedBuildProfileDeviceRunnerOrTruthIsInvalid(self):
        changes = (("runnerSha256", "d" * 64), ("target", {"cable": "other", "device": "other", "index": 2}))
        for field, value in changes:
            with self.subTest(field=field):
                self.bypass = fixture(1)
                self.bypass[field] = value
                self.assertEqual(self.compare()[1], 1)
        for field, value in (("buildId", 7), ("whiteMinimum", 85), ("redMinimum", 34), ("readerAlgorithm", 3)):
            with self.subTest(field=field):
                self.bypass = fixture(1)
                for state in [self.bypass["initialStatus"], *[s["status"] for s in self.bypass["requestSelections"]],
                              *[r["status"] for r in self.bypass["observations"]]]:
                    state[field] = value
                self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["truthRegions"]["sha256"] = "d" * 64
        self.assertEqual(self.compare()[1], 1)

    def testMidTrialConfigurationOrSelectModeChangeIsInvalid(self):
        self.bypass["observations"][10]["status"]["configVersion"] = 6
        self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["requestSelections"][0]["status"]["bypassPerspective"] = False
        self.assertEqual(self.compare()[1], 1)

    def testStaleScoresLatencyAndFailureOmissionsAreRejected(self):
        row = self.bypass["observations"][0]
        row["status"]["markers"][-1]["accepted"] = False
        self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["trials"][0]["printedDigitScore"]["correct"] = 239
        self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["observations"][0]["status"]["processingLatencyUs"] = 1
        self.assertEqual(self.compare()[1], 1)
        self.bypass = fixture(1)
        self.bypass["observations"][0]["issues"] = ["frame_bad"]
        self.assertEqual(self.compare()[1], 1)

    def testSourcePassCannotHideRecordedFailures(self):
        missingSix(self.bypass["observations"][0])
        summaries(self.bypass)
        self.bypass.update(status="PASS", exitCode=0)
        self.assertEqual(self.compare()[1], 1)

    def testMissingFieldsBecomeExplicitInvalidResult(self):
        del self.bypass["initialStatus"]["whiteMode"]
        result, code = self.compare()
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "INVALID_COMPARISON")
        self.assertTrue(result["comparisonValidity"]["issues"])

    def testCliCannotOverwriteInputEvidence(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "input.json"
            source.write_text(json.dumps(self.normal), encoding="utf-8")
            original = source.read_bytes()
            result = subprocess.run([sys.executable, str(ROOT / "tools/compare_sw9_trials.py"),
                "--normal", str(source), "--bypass", str(source), "--out", str(source)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(source.read_bytes(), original)

    def testCliRetainsInputHashesAndReturnsConditionsExitCode(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for name, data in (("normal", self.normal), ("bypass", self.bypass)):
                (folder / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "tools/compare_sw9_trials.py"),
                "--normal", str(folder / "normal.json"), "--bypass", str(folder / "bypass.json"),
                "--out", str(folder / "comparison.json")], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            comparison = json.loads((folder / "comparison.json").read_text())
            self.assertEqual(len(comparison["inputs"]["normal"]["sha256"]), 64)
            self.assertEqual(comparison["status"], "UNCONFIRMED_CONDITIONS")


if __name__ == "__main__":
    unittest.main()
