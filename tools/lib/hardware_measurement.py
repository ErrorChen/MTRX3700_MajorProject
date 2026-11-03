"""Bounded live status trials: preserve failures in the denominator.

These are sparse JTAG observations, not a recording of every intervening frame.
The capture CRC/pixel oracle and physical VGA checks remain separate evidence.
"""
import json
import time
from pathlib import Path
import hashlib
from collections import Counter
from debug_decode import requireAlgorithmMode

# Frozen B datasheet targets. The stricter all-observation development gate is
# retained separately; these values are never adjusted after a failed trial.
CAPTURE_LATENCY_THRESHOLD_US = 150_000
CAPTURE_LATENCY_GOAL_US = 100_000


def markerIdentity(payload, contractVersion=2):
    """Read exact versioned fields without rewriting archived public-v2 data."""
    if contractVersion == 2:
        return (1, payload.get("bayId"))
    if contractVersion == 3:
        if "markerType" not in payload or "digit" not in payload or "bayId" in payload:
            raise ValueError("public v3 marker identity requires markerType/digit, not legacy bayId")
        return (payload["markerType"], payload["digit"])
    raise ValueError(f"unsupported public contract version {contractVersion}")


def baySelectCommand(bay, contractVersion):
    if contractVersion not in (2, 3) or not 1 <= bay <= 6:
        raise ValueError("bay trial requires contract v2/v3 and a bay digit1..6")
    return (1 << 24) | ((1 << 4) if contractVersion == 3 else 0) | bay


class TrackingAcquisition:
    """Allow only the specified first two native frames after a new request.

    This is a protocol assessment, not removal of unsuccessful observations.
    The SELECT snapshot can establish the earliest observed current frame. A
    skipped frame consumes the same native-frame budget as an observed frame;
    once any lock is observed, no subsequent unlock receives another grace.
    Declared repeated signs require a zero-measurement ambiguity report. An
    older ambiguity may drain only for a declared repeated previous bay, using
    the same immutable capture-time bound as other previous-request reports.
    """
    def __init__(self, tag, bay, configVersion, selection=None, expectedMatches=1, sceneBlueCounts=None):
        self.tag, self.bay, self.configVersion = tag, bay, configVersion
        self.firstFrame = None
        self.seenLocked = False
        self.selection = selection
        self.expectedMatches = expectedMatches
        self.sceneBlueCounts = sceneBlueCounts or {}

    def observe(self, state):
        report, status = state["targetReport"], state["status"]
        contractVersion = state.get("contractVersion", 2)
        reportIdentity = markerIdentity(report, contractVersion)
        current = (report["requestTag"] == self.tag and reportIdentity == (1, self.bay)
                   and report["frameId"] == state["frameId"])
        if current and self.firstFrame is None:
            self.firstFrame = state["frameId"]
        offset = ((state["frameId"] - self.firstFrame) & 0xffff) if current else None
        reliable = (current and self.expectedMatches == 1
                    and all(report[key] for key in ("targetSelected", "frameGood", "observed"))
                    and not report["ambiguous"] and state["freshAtSnapshot"]
                    and report["configVersion"] == status["activeCfgVersion"] == self.configVersion)
        acquiring = bool(reliable and not report["locked"] and report.get("reason") == 2
                         and not self.seenLocked and offset < 2)
        if reliable and report["locked"]:
            self.seenLocked = True
        publicZero = all(report.get(key) == 0 for key in
            ("observed", "locked", "centreU", "centreV", "boxWidth", "boxHeight", "quality"))
        expectedAmbiguous = bool(current and self.expectedMatches > 1
            and report["targetSelected"] and report["frameGood"] and report["ambiguous"]
            and report.get("reason") == 4 and publicZero and state["freshAtSnapshot"]
            and report["configVersion"] == status["activeCfgVersion"] == self.configVersion)
        oldDrain = previousLocked = previousAmbiguous = False
        selectionOffset = selectionElapsed = captureAgeAtSelection = None
        if self.selection is not None and not current and self.firstFrame is None:
            previous = self.selection["targetReport"]
            previousIdentity = markerIdentity(previous, self.selection.get("contractVersion", 2))
            active = state.get("activeRequest", {})
            activeIdentity = markerIdentity(active, contractVersion)
            selectionOffset = (state["frameId"] - self.selection["frameId"]) & 0xffff
            if "timeUs" in state and "timeUs" in self.selection:
                selectionElapsed = (state["timeUs"] - self.selection["timeUs"]) & 0xffffffff
            if "captureStartUs" in state and "timeUs" in self.selection:
                captureAgeAtSelection = (self.selection["timeUs"] - state["captureStartUs"]) & 0xffffffff
            # SELECT freezes the last completed result, not the current camera
            # SOF. Its frameId can trail an already-started old-request frame by
            # two frames (processing plus publication age), so a one-frame
            # offset bound is not a valid request-acceptance boundary. Require
            # the immutable SOF timestamp to predate the post-ACK freeze instead.
            # The small unsigned age limit also rejects future timestamps and
            # remains correct across uint32 microsecond wrap. No old report is
            # accepted after the first current-tag report has been observed.
            capturedBeforeSelection = (captureAgeAtSelection is not None
                and captureAgeAtSelection <= CAPTURE_LATENCY_THRESHOLD_US
                and report.get("captureStartUs") == state.get("captureStartUs"))
            boundedPrevious = (report["requestTag"] != self.tag
                and (report["requestTag"],reportIdentity) == (previous["requestTag"],previousIdentity)
                and active.get("requestTag") == self.tag and activeIdentity == (1, self.bay)
                and active.get("operation") == 1 and capturedBeforeSelection
                and selectionElapsed is not None and selectionElapsed <= CAPTURE_LATENCY_THRESHOLD_US
                and report["frameId"] == state["frameId"] and report["frameGood"]
                and state["freshAtSnapshot"]
                and report["configVersion"] == status["activeCfgVersion"] == self.configVersion)
            oldDrain = bool(boundedPrevious and not report["ambiguous"] and report.get("reason") == 7 and publicZero)
            previousLocked = bool(boundedPrevious and report.get("reason") == 0
                and not report["ambiguous"]
                and report["targetSelected"] and report["observed"] and report["locked"]
                and 0 <= report.get("centreU",-1) < 240 and 0 <= report.get("centreV",-1) < 320
                and 0 < report.get("boxWidth",0) <= 240 and 0 < report.get("boxHeight",0) <= 320
                and report.get("quality",0) > 0)
            previousAmbiguous = bool(boundedPrevious and report.get("reason") == 4
                and report["ambiguous"] and report["targetSelected"] and publicZero
                and previousIdentity[0] == 1 and self.sceneBlueCounts.get(previousIdentity[1], 1) > 1)
        return {"expectedAcquiring": acquiring, "firstCurrentFrameId": self.firstFrame,
                "nativeFrameOffset": offset, "lockPreviouslyObserved": self.seenLocked,
                "expectedOldRequestDrain": oldDrain, "expectedPreviousLockedReport": previousLocked,
                "expectedPreviousAmbiguousReport": previousAmbiguous,
                "expectedAmbiguous": expectedAmbiguous, "expectedMatchCount": self.expectedMatches,
                "selectionFrameOffset": selectionOffset, "selectionElapsedUs": selectionElapsed,
                "captureAgeAtSelectionUs": captureAgeAtSelection,
                "configurationMatchesRequest": report["configVersion"] == self.configVersion}


def scoreRegions(markers, truth):
    """Test-only spatial association catches swapped IDs with an unchanged set.

    Regions are annotations of photographed printed digits. They are never
    sent to the FPGA or used by any production recognition/selection path.
    """
    accepted=[marker for marker in markers if marker["accepted"]]
    assignments=[[] for _ in truth["regions"]]
    outside=0
    for marker in accepted:
        x=(marker["xMin"]+marker["xMax"])/2
        y=(marker["yMin"]+marker["yMax"])/2
        matches=[index for index,region in enumerate(truth["regions"])
                 if region["bbox"][0]<=x<=region["bbox"][2] and region["bbox"][1]<=y<=region["bbox"][3]]
        if len(matches)==1:assignments[matches[0]].append(marker)
        else:outside+=1
    correct=wrong=missing=0
    for region,assigned in zip(truth["regions"],assignments):
        if not assigned:missing+=1
        elif len(assigned)==1 and assigned[0]["digit"]==region["digit"] and assigned[0]["isBlue"]==region["isBlue"]:
            correct+=1
        else:wrong+=len(assigned)
    return {"correct":correct,"expected":len(truth["regions"]),"missing":missing,
            "wrongOrAmbiguous":wrong,"outside":outside}


def sceneExpectations(truth=None):
    """Declare scoring expectations only; these labels are never sent to BCTL.

    Repeated blue numbers are an ambiguity test. Both red functions and every
    bay1..6 remain mandatory, so a reduced scene cannot silently lower coverage.
    """
    if truth is None:
        return {"red": [1, 2], "blue": list(range(1, 7)),
                "blueMatchesByBay": {str(bay): 1 for bay in range(1, 7)}, "printedRegionCount": 8}
    regions = truth.get("regions", [])
    for region in regions:
        bbox = region.get("bbox", [])
        if (type(region.get("isBlue")) is not bool or type(region.get("digit")) is not int
                or len(bbox) != 4 or any(type(value) is not int for value in bbox)
                or not 0 <= bbox[0] <= bbox[2] < 320 or not 0 <= bbox[1] <= bbox[3] < 240):
            raise ValueError("truth regions require typed digits and native320x240 integer bboxes")
    red = sorted(region["digit"] for region in regions if not region["isBlue"])
    blue = sorted(region["digit"] for region in regions if region["isBlue"])
    if red != [1, 2] or set(blue) != set(range(1, 7)) or len(blue) > 16:
        raise ValueError("truth regions require exactly red1/2 and at least one of every blue1..6, at most16 blue signs")
    counts = Counter(blue)
    return {"red": red, "blue": blue, "blueMatchesByBay": {str(bay): counts[bay] for bay in range(1, 7)},
            "printedRegionCount": len(regions)}


def measureTrials(runner, trials):
    runner.result.update(level="CAMERA_HW", inputSource="LIVE_CAMERA_JTAG_SAMPLED_TRIALS",
                         metricBoundary="typed-ID set coverage; requires independent visual label checks for absolute accuracy",
                         trials=[], observations=[], failures=[], strictAllLockedFailures=[], requestSelections=[],
                         trackingAssessment="First two current native frame offsets may be REPORT_ACQUIRING=2. Before any current report only the SELECT snapshot's previous request may drain: its matching capture timestamp must predate the post-ACK SELECT freeze by at most150000 board us, and observation must follow that freeze by at most150000 us. Native frame offset is diagnostic only because the frozen completed frame can lag camera SOF. Reason7 requires public zeros; a valid previous locked report is also only a transition. Neither is a new-target observation. Future, late, corrupt, wrong-tag/config or unbounded old reports fail. All samples and the former all-locked verdict remain recorded.")
    initial = runner.control()["decoded"]
    runner.result["initialStatus"] = initial
    def checkAlgorithmState(state, phase, trial=0, bay=0):
        # The frozen record is meaningful camera/status evidence even though it
        # cannot be admitted to a stable algorithm trial. Preserve it before
        # failing, including when the physical switch changes mid-session.
        if any(state.get(field, False) for field in
               ("rawCameraMode", "rawModeRequested", "rawDisplayActive")):
            rejected = runner.result.setdefault("rawModeRejections", [])
            rejected.append({"phase": phase, "trial": trial, "requestedBay": bay, "status": state})
            (runner.out / "raw_mode_rejections.json").write_text(json.dumps(rejected, indent=2), encoding="utf-8")
        requireAlgorithmMode(state)
    checkAlgorithmState(initial, "INITIAL")
    for counter in ("bufferDropCount", "completionDiscardCount"):
        if initial[counter] == 0xffff:
            raise RuntimeError(f"{counter} is saturated; reset before measuring new drops")
    truth=None
    if getattr(runner.args,"truth_regions",None):
        truthPath=Path(runner.args.truth_regions)
        truth=json.loads(truthPath.read_text(encoding="utf-8"))
        runner.result["truthRegions"]={"path":str(truthPath),"sha256":hashlib.sha256(truthPath.read_bytes()).hexdigest(),"annotations":truth}
        runner.result["metricBoundary"]="Fixed photographed scene with explicit test-only printed-digit regions; sparse observations, not general accuracy."
    expectedScene = sceneExpectations(truth)
    runner.result["expectedScene"] = expectedScene
    runner.result["trackingAssessment"] += " Declared duplicate blue numbers require current reason4/ambiguous with all public measurements zero. A previous declared-duplicate ambiguity may drain under the same capture-time/tag/config boundary before the first current report. It is retained and never counted as a current observation."
    blueCounts = {int(bay): count for bay, count in expectedScene["blueMatchesByBay"].items()}
    runner.result["initialStatus"] = initial
    records = runner.result["observations"]
    failures = runner.result["failures"]
    lastFrame = None
    deadline = time.monotonic() + runner.args.timeout
    for trial in range(1, trials + 1):
        trialRecords = []
        allTrialRecords = []
        for bay in range(1, 7):
            selected = runner.control(baySelectCommand(bay, initial.get("contractVersion", 2)))["decoded"]
            checkAlgorithmState(selected, "SELECT", trial, bay)
            tag = selected["activeRequest"]["requestTag"]
            acquisition = TrackingAcquisition(tag, bay, selected["status"]["activeCfgVersion"], selected,
                                               expectedMatches=blueCounts[bay], sceneBlueCounts=blueCounts)
            selectionAssessment = acquisition.observe(selected)
            runner.result["requestSelections"].append({"trial": trial, "requestedBay": bay,
                "requestTag": tag, "status": selected, "trackingAssessment": selectionAssessment})
            collected = 0
            while collected < 5:
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"trial timeout: trial={trial} bay={bay} samples={collected}; all partial records retained")
                state = runner.control()["decoded"]
                checkAlgorithmState(state, "STATUS", trial, bay)
                frameId = state["frameId"]
                if lastFrame is not None:
                    delta = (frameId - lastFrame) & 0xffff
                    if delta == 0:
                        continue
                    if delta >= 0x8000:
                        raise RuntimeError("sampled native frame moved backwards or exceeded unambiguous sequence interval")
                lastFrame = frameId
                report, status = state["targetReport"], state["status"]
                red = sorted(m["digit"] for m in state["markers"] if m["accepted"] and not m["isBlue"])
                blue = sorted(m["digit"] for m in state["markers"] if m["accepted"] and m["isBlue"])
                issues = []
                if state["processingLatencyUs"] > CAPTURE_LATENCY_THRESHOLD_US:
                    issues.append("capture_to_completion_latency")
                current = (report["requestTag"] == tag and markerIdentity(report, state.get("contractVersion", 2)) == (1, bay)
                           and report["frameId"] == frameId)
                tracking = acquisition.observe(state)
                # Old reports are retained as transition observations. Current
                # rejected/unlocked/bad observations count towards the five.
                if red != expectedScene["red"] or blue != expectedScene["blue"]:
                    issues.append("typed_marker_set")
                strictlyUnreliable = not all(report[key] for key in ("targetSelected", "frameGood", "observed", "locked")) or report["ambiguous"]
                if strictlyUnreliable and not any(tracking[key] for key in
                    ("expectedAcquiring", "expectedAmbiguous", "expectedOldRequestDrain", "expectedPreviousAmbiguousReport")):
                    issues.append("target_unreliable_or_unlocked")
                if current and blueCounts[bay] > 1 and not tracking["expectedAmbiguous"]:
                    issues.append("expected_target_ambiguity")
                if not current and not any(tracking[key] for key in
                    ("expectedOldRequestDrain", "expectedPreviousLockedReport", "expectedPreviousAmbiguousReport")):
                    issues.append("unexpected_old_request_report")
                if not state.get("frameGood", report["frameGood"]) or any(state.get(key, False) for key in
                    ("candidateOverflow", "candidateError", "candidateOverrun")):
                    issues.append("captured_frame_bad")
                if current and not tracking["configurationMatchesRequest"]:
                    issues.append("request_configuration_changed")
                if report["configVersion"] != status["activeCfgVersion"] or not state["freshAtSnapshot"]:
                    issues.append("stale_report")
                if not status["calibrated"] or status["interactionBusy"] or not status["perceptionReady"]:
                    issues.append("interaction_not_ready")
                for key in ("bufferDropCount", "completionDiscardCount"):
                    if state[key] != initial[key] or state[key] == 0xffff:
                        issues.append(key)
                if status["faultFlags"] & ~initial["status"]["faultFlags"] & 7:
                    issues.append("new_frame_fault")
                record = {"trial": trial, "requestedBay": bay, "requestTag": tag,
                          "currentRequestSample": current, "issues": issues, "status": state,
                          "trackingAssessment": tracking}
                if truth:
                    score=scoreRegions(state["markers"],truth)
                    record["regionScore"]=score
                    if score["correct"]!=score["expected"] or score["outside"] or score["wrongOrAmbiguous"]:
                        issues.append("printed_digit_region_mismatch")
                records.append(record)
                allTrialRecords.append(record)
                strictIssues = list(issues)
                if strictlyUnreliable and "target_unreliable_or_unlocked" not in strictIssues:
                    strictIssues.append("target_unreliable_or_unlocked")
                record["strictAllLockedIssues"] = strictIssues
                if strictIssues:
                    runner.result["strictAllLockedFailures"].append({"index": len(records)-1,
                        "frameId": frameId, "issues": strictIssues})
                if issues:
                    failures.append({"index": len(records)-1, "frameId": frameId, "issues": issues})
                (runner.out / "trial_observations.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
                if current:
                    collected += 1
                    trialRecords.append(record)
        summary = {"trial": trial, "currentRequestSamples": len(trialRecords),
                   "allObservedSamples": len(allTrialRecords),
                   "passedSamples": sum(not record["issues"] for record in trialRecords),
                   "failedSamples": sum(bool(record["issues"]) for record in trialRecords),
                   "acquiringSamples": sum(record["trackingAssessment"]["expectedAcquiring"] for record in trialRecords),
                   "expectedAmbiguousSamples": sum(record["trackingAssessment"]["expectedAmbiguous"] for record in trialRecords),
                   "lockedSamples": sum(bool(record["status"]["targetReport"]["locked"]) for record in trialRecords),
                   "oldRequestDrainSamples": sum(record["trackingAssessment"]["expectedOldRequestDrain"] for record in allTrialRecords),
                   "previousLockedTransitionSamples": sum(record["trackingAssessment"]["expectedPreviousLockedReport"] for record in allTrialRecords),
                   "previousAmbiguousTransitionSamples": sum(record["trackingAssessment"]["expectedPreviousAmbiguousReport"] for record in allTrialRecords),
                   "strictAllLockedFailedSamples": sum(bool(record["strictAllLockedIssues"]) for record in trialRecords),
                   "typedSetPasses": sum("typed_marker_set" not in record["issues"] for record in trialRecords),
                   "captureToCompletionUs": {
                       "minimum": min(record["status"]["processingLatencyUs"] for record in allTrialRecords),
                       "maximum": max(record["status"]["processingLatencyUs"] for record in allTrialRecords),
                       "population": "All observed completions, including invalid and old-request transition records"},
                   "modeValues": sorted(set(int(record["status"].get("bypassPerspective", False)) for record in trialRecords)),
                   "configurationVersions": sorted(set(record["status"]["configVersion"] for record in trialRecords))}
        maximumLatency = summary["captureToCompletionUs"]["maximum"]
        summary["latencyTarget"] = {"status": "PASS" if maximumLatency <= CAPTURE_LATENCY_THRESHOLD_US else "FAIL",
                                    "thresholdUs": CAPTURE_LATENCY_THRESHOLD_US,
                                    "goalUs": CAPTURE_LATENCY_GOAL_US,
                                    "measuredMaximumUs": maximumLatency,
                                    "goalMet": maximumLatency <= CAPTURE_LATENCY_GOAL_US}
        runner.result["trials"].append(summary)
        if truth:
            summary["printedDigitScore"]={key:sum(record["regionScore"][key] for record in trialRecords)
                for key in ("correct","expected","missing","wrongOrAmbiguous","outside")}
        (runner.out / "trial_summary.json").write_text(json.dumps(runner.result["trials"], indent=2), encoding="utf-8")
    runner.control(2 << 24)
    runner.result["clearSent"] = True
    if failures:
        raise RuntimeError(f"{len(failures)} sampled observations failed; all {len(records)} retained, no success-only filtering")
