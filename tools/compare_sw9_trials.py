#!/usr/bin/env python3
"""Compare complete perspective-bypass trials without hiding a failing mode.

The filename retains the old SW9 command compatibility. In schema5+ hardware,
SW8 controls perspective bypass and SW9 selects raw camera, which is excluded
from an algorithm comparison.

This is a host assessment of recorded CAMERA_HW results, not another acquisition.
Exit 0 means that the comparison inputs and caller-attested conditions are valid;
inspect modes.*.acceptance for each mode's independent acceptance. Exit 1 means
invalid/incomplete inputs, and exit 2 means physical conditions were not attested.
No image similarity test can establish unchanged camera, paper or illumination.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from hardware_measurement import CAPTURE_LATENCY_THRESHOLD_US, scoreRegions, sceneExpectations, markerIdentity
from debug_decode import schemaLayout


PROFILE_FIELDS = (
    "schema", "debugSchemaVersion", "contractVersion", "buildId",
    "orientationProfile", "redMinimum", "blueMinimum", "readerAlgorithm",
    "colourAlgorithm", "whiteMinimum", "whiteMaxSpread", "whiteMode",
    "whiteThresholdExpression", "whiteAnchorThresholdExpression",
    "whiteAnchorMinimum", "candidateSizePruning", "activeCandidateCapacity",
    "outputCandidateCapacity",
    "poolLayout",
)
SCORE_FIELDS = ("correct", "expected", "missing", "wrongOrAmbiguous", "outside")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def profileFor(state):
    # Legacy stored JSON predates this explicit field; the version fixes its
    # meaning. A shared total16 pool is never interchangeable with split16/colour.
    layout = schemaLayout(state["debugSchemaVersion"])
    expectedLayout = layout["poolLayout"]
    require(state.get("contractVersion", 2) == layout["contractVersion"],
            "public contract version conflicts with private schema")
    require(state.get("poolLayout", expectedLayout) == expectedLayout, "pool profile conflicts with private schema")
    return {key: (state.get(key, expectedLayout)
                  if key == "poolLayout" else state.get(key, 2) if key == "contractVersion" else state[key]) for key in PROFILE_FIELDS}


def latencySummary(records):
    # Unsigned board time wraps legally; PC/JTAG transfer duration is irrelevant.
    values = [record["status"]["processingLatencyUs"] for record in records]
    return {"count": len(values), "minimumUs": min(values), "maximumUs": max(values),
            "meanUs": sum(values) / len(values)}


def correctBays(markers, truth):
    """Count only unique, correctly typed spatial assignments as bay coverage."""
    assigned = [[] for _ in truth["regions"]]
    for marker in markers:
        if not marker["accepted"]:
            continue
        x = (marker["xMin"] + marker["xMax"]) / 2
        y = (marker["yMin"] + marker["yMax"]) / 2
        matches = [i for i, region in enumerate(truth["regions"])
                   if region["bbox"][0] <= x <= region["bbox"][2]
                   and region["bbox"][1] <= y <= region["bbox"][3]]
        if len(matches) == 1:
            assigned[matches[0]].append(marker)
    return {region["digit"] for region, markersHere in zip(truth["regions"], assigned)
            if region["isBlue"] and len(markersHere) == 1
            and markersHere[0]["isBlue"]
            and markersHere[0]["digit"] == region["digit"]}


def assessMode(data, expectedMode):
    """Reject incomparable records; preserve genuine recognition/tracking failures."""
    require(data["schema"] == "echo7-cli-v1" and data["command"] == "test",
            "expected echo7 hardware test result")
    require(data["level"] == "CAMERA_HW"
            and data["inputSource"] == "LIVE_CAMERA_JTAG_SAMPLED_TRIALS",
            "input is not live camera trial evidence")
    require(data["status"] in ("PASS", "FAIL"), "trial run did not reach a verdict")
    require(data["exitCode"] == (0 if data["status"] == "PASS" else 1),
            "source exit code disagrees with source verdict")
    require(data["clearSent"] is True, "trial session lacks its final CLEAR")
    require(data["transport"] == "ONE_BOUNDED_JTAG_SESSION", "unknown trial transport")
    require(len(data["runnerSha256"]) == 64, "missing runner identity")
    require(set(data["target"]) >= {"cable", "device", "index"}, "missing target identity")

    initial = data["initialStatus"]
    profile = profileFor(initial)
    configVersion = initial["configVersion"]
    observations = data["observations"]
    require(len(observations) >= 90, "fewer than 90 observations")
    transport = data["trialTransport"]
    require(transport["returnCode"] == 0 and transport["completion"]["trials"] == 3
            and transport["completion"]["statusRecords"] == len(observations)
            and transport["completeRecords"] == transport["assessedRecords"],
            "incomplete transport or omitted observations")

    truthRecord = data["truthRegions"]
    truth = truthRecord["annotations"]
    require(len(truthRecord["sha256"]) == 64
            and truth["schema"] == "echo7-test-only-printed-regions-v1"
            and truth["coordinateSystem"] == "native320x240",
            "missing versioned printed-region annotations")
    expectedScene = sceneExpectations(truth)
    if "expectedScene" in data:
        require(data["expectedScene"] == expectedScene, "source scene expectations differ from truth regions")

    selections = data["requestSelections"]
    selectionKeys = [(s["trial"], s["requestedBay"]) for s in selections]
    requiredKeys = [(trial, bay) for trial in range(1, 4) for bay in range(1, 7)]
    require(selectionKeys == requiredKeys, "selection order must be 1-6 in each of three trials")
    tags = {key: s["requestTag"] for key, s in zip(selectionKeys, selections)}
    # Check initial/SELECT snapshots as well as sampled reports. A mode switch
    # during a trial is incomparable even if its final summary happens to pass.
    states = [initial, *[s["status"] for s in selections],
              *[record["status"] for record in observations]]
    for state in states:
        require(not any(state.get(field, False) for field in
                        ("rawCameraMode", "rawModeRequested", "rawDisplayActive")),
                "RAW_CAMERA_MODE: paused/raw samples are not algorithm comparison evidence")
        require(state["bypassPerspective"] == bool(expectedMode),
                "unexpected perspective-bypass mode (SW8 in schema5+; historical SW9)")
        require(state["configVersion"] == configVersion
                and state["status"]["activeCfgVersion"] == configVersion,
                "configuration changed within one mode")
        require(profileFor(state) == profile,
                "profile/build changed within one mode")

    lastFrame = None
    lastSelectionIndex = -1
    seenFrames = set()
    failedIndices = []
    for index, record in enumerate(observations):
        key = (record["trial"], record["requestedBay"])
        require(key in tags and record["requestTag"] == tags[key], "unexpected request identity")
        selectionIndex = requiredKeys.index(key)
        require(selectionIndex >= lastSelectionIndex, "trial/selection observations are out of order")
        lastSelectionIndex = selectionIndex
        state = record["status"]
        frame = state["frameId"]
        require(isinstance(frame, int) and 0 <= frame <= 65535 and frame not in seenFrames,
                "duplicate/invalid native frame; held samples cannot add evidence")
        require(lastFrame is None or 0 < ((frame - lastFrame) & 0xffff) < 0x8000,
                "native frame order moved backwards or became ambiguous")
        seenFrames.add(frame)
        lastFrame = frame
        report = state["targetReport"]
        current = (report["requestTag"] == record["requestTag"]
                   and markerIdentity(report,state.get("contractVersion",2)) == (1,record["requestedBay"])
                   and report["frameId"] == frame)
        require(record["currentRequestSample"] == current, "incorrect current-request label")
        elapsed = (state["completionUs"] - state["captureStartUs"]) & 0xffffffff
        require(state["processingLatencyUs"] == elapsed, "latency differs from board timestamps")
        score = scoreRegions(state["markers"], truth)
        require(record["regionScore"] == score, "recorded printed score differs from actual marker records")
        if record["issues"]:
            failedIndices.append(index)
    require([failure["index"] for failure in data["failures"]] == failedIndices,
            "failure records were omitted or duplicated")
    for failure in data["failures"]:
        original = observations[failure["index"]]
        require(failure["frameId"] == original["status"]["frameId"]
                and failure["issues"] == original["issues"], "failure record was changed")
    require((data["status"] == "FAIL") == bool(failedIndices), "source verdict hides/adds failures")

    require([summary["trial"] for summary in data["trials"]] == [1, 2, 3],
            "expected exactly three trial summaries")
    currentRecords = [record for record in observations if record["currentRequestSample"]]
    require(len(currentRecords) == 90, "expected exactly 90 current-request reports")
    trials = []
    for trial, recordedSummary in zip(range(1, 4), data["trials"]):
        allRows = [record for record in observations if record["trial"] == trial]
        rows = [record for record in currentRecords if record["trial"] == trial]
        require(len(rows) == 30 and Counter(r["requestedBay"] for r in rows) ==
                Counter({bay: 5 for bay in range(1, 7)}), "trial must contain five current reports per bay")
        score = {key: sum(record["regionScore"][key] for record in rows) for key in SCORE_FIELDS}
        require(recordedSummary["currentRequestSamples"] == 30
                and recordedSummary["allObservedSamples"] == len(allRows)
                and recordedSummary["printedDigitScore"] == score,
                "trial summary differs from retained observations")
        require(recordedSummary["modeValues"] == [expectedMode]
                and recordedSummary["configurationVersions"] == [configVersion],
                "trial mode/configuration summary differs from records")
        allLatency, currentLatency = latencySummary(allRows), latencySummary(rows)
        require(recordedSummary["captureToCompletionUs"]["minimum"] == allLatency["minimumUs"]
                and recordedSummary["captureToCompletionUs"]["maximum"] == allLatency["maximumUs"],
                "trial latency summary differs from retained observations")
        bays = set().union(*(correctBays(row["status"]["markers"], truth) for row in rows))
        recognitionPass = (score["correct"] * 100 >= score["expected"] * 95
                           and score["wrongOrAmbiguous"] == 0 and score["outside"] == 0
                           and bays == set(range(1, 7)))
        trials.append({"trial": trial, "currentRequestSamples": len(rows),
                       "allObservedSamples": len(allRows), "printedDigitScore": score,
                       "correctPercent": score["correct"] * 100 / score["expected"],
                       "correctlyObservedBays": sorted(bays),
                       "recognitionTarget": "PASS" if recognitionPass else "FAIL",
                       "latencyTarget": "PASS" if allLatency["maximumUs"] <= CAPTURE_LATENCY_THRESHOLD_US else "FAIL",
                       "latencyAllObservations": allLatency, "latencyCurrentRequests": currentLatency})
    recognitionPass = all(trial["recognitionTarget"] == "PASS" for trial in trials)
    latencyPass = all(trial["latencyTarget"] == "PASS" for trial in trials)
    return {"mode": expectedMode, "configVersion": configVersion, "profile": profile, "expectedScene": expectedScene,
            "recordedRunnerStatus": data["status"], "recordedRunnerReason": data.get("reason", ""),
            "acceptance": {"recognitionTarget": "PASS" if recognitionPass else "FAIL",
                           "latencyTarget": "PASS" if latencyPass else "FAIL",
                           "strictHardwareRunner": data["status"],
                           "overall": "PASS" if recognitionPass and latencyPass and data["status"] == "PASS" else "FAIL"},
            "trials": trials, "currentRequestObservations": len(currentRecords),
            "allObservedSamples": len(observations), "nonCurrentObservations": len(observations) - len(currentRecords),
            "printedDigitScoreCurrent": {key: sum(trial["printedDigitScore"][key] for trial in trials) for key in SCORE_FIELDS},
            "latencyCurrentRequests": latencySummary(currentRecords),
            "latencyAllObservations": latencySummary(observations),
            # Retain the complete original observation/failure payloads. In
            # particular a failed bypass is data, not grounds to prune samples.
            "observations": copy.deepcopy(observations), "failures": copy.deepcopy(data["failures"])}


def compareTrials(normal, bypass, conditionsConfirmed=""):
    result = {"schema": "echo7-sw9-comparison-v1", "status": "INVALID_COMPARISON",
              "evidenceLevel": "HOST_COMPARISON_OF_RECORDED_CAMERA_HW",
              "comparisonValidity": {"status": "INVALID", "issues": []},
              "physicalConditionsAttestation": conditionsConfirmed.strip(),
              "scope": "One fixed photographed scene; sparse sampled frames, not general pose/lighting accuracy. Physical conditions are caller-attested, never inferred from images.",
              "targets": {"correctPercentMinimum": 95, "wrongIdsMaximum": 0,
                          "correctBlueBaysPerTrial": [1, 2, 3, 4, 5, 6],
                          "maximumBoardLatencyUs": CAPTURE_LATENCY_THRESHOLD_US}, "modes": {}}
    try:
        normalMode, bypassMode = assessMode(normal, 0), assessMode(bypass, 1)
        result["modes"] = {"normal": normalMode, "bypass": bypassMode}
        for key in ("target", "runnerSha256"):
            require(normal[key] == bypass[key], f"mode inputs have different {key}")
        # Count every annotated physical sign in every current-request sample,
        # including failures. Extra duplicate signs increase the population;
        # the old eight-sign total720 is not a universal comparison denominator.
        expectedPerMode = normalMode["printedDigitScoreCurrent"]["expected"]
        require(expectedPerMode == bypassMode["printedDigitScoreCurrent"]["expected"],
                "mode inputs have different scoring denominators")
        require(normal["truthRegions"]["sha256"] == bypass["truthRegions"]["sha256"]
                and normal["truthRegions"]["annotations"] == bypass["truthRegions"]["annotations"],
                "mode inputs have different truth regions")
        require(normalMode["profile"] == bypassMode["profile"], "mode inputs have different profile/build")
        result["comparisonValidity"] = {"status": "VALID" if conditionsConfirmed.strip() else "UNCONFIRMED_CONDITIONS", "issues": []}
        result["status"] = "COMPARISON_VALID" if conditionsConfirmed.strip() else "UNCONFIRMED_CONDITIONS"
        result["difference"] = {
            "interpretationAllowed": bool(conditionsConfirmed.strip()),
            "currentCorrectNormalMinusBypass": normalMode["printedDigitScoreCurrent"]["correct"] - bypassMode["printedDigitScoreCurrent"]["correct"],
            "currentExpectedPerMode": expectedPerMode,
            "allObservedMaximumLatencyNormalMinusBypassUs": normalMode["latencyAllObservations"]["maximumUs"] - bypassMode["latencyAllObservations"]["maximumUs"],
            "meaning": "Descriptive differences only. COMPARISON_VALID is not acceptance of either mode; see modes.*.acceptance. No generalised improvement is claimed."}
        return result, 0 if conditionsConfirmed.strip() else 2
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        result["comparisonValidity"]["issues"].append(str(exc))
        return result, 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", type=Path, required=True)
    parser.add_argument("--bypass", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="output JSON file")
    parser.add_argument("--conditions-confirmed", default="", metavar="STATEMENT",
                        help="Who confirmed camera/focus/sheet/illumination were unchanged for these exact runs; omit for historical/unmatched runs")
    args = parser.parse_args(argv)
    # The evidence files are immutable inputs, including a failed run. Never
    # allow a convenient --out spelling to overwrite one of those inputs.
    if args.out.resolve() in (args.normal.resolve(), args.bypass.resolve()):
        print(json.dumps({"status": "INVALID_COMPARISON", "exitCode": 1,
                          "reason": "output must not overwrite either input evidence file"}))
        return 1
    try:
        inputBytes = {name: path.read_bytes() for name, path in (("normal", args.normal), ("bypass", args.bypass))}
        data = {name: json.loads(payload.decode("utf-8-sig")) for name, payload in inputBytes.items()}
        result, code = compareTrials(data["normal"], data["bypass"], args.conditions_confirmed)
        result["inputs"] = {name: {"path": str(path), "sha256": hashlib.sha256(inputBytes[name]).hexdigest()}
                            for name, path in (("normal", args.normal), ("bypass", args.bypass))}
    except (OSError, ValueError, UnicodeError) as exc:
        result, code = {"schema": "echo7-sw9-comparison-v1", "status": "INVALID_COMPARISON", "reason": str(exc)}, 1
    result["exitCode"] = code
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "exitCode": code, "output": str(args.out),
                      "acceptance": {name: mode["acceptance"] for name, mode in result.get("modes", {}).items()},
                      "issues": result.get("comparisonValidity", {}).get("issues", [result.get("reason", "")])}))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
