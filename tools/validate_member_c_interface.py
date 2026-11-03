#!/usr/bin/env python3
"""Exercise the real Member B/C v3 interface through the stationary JTAG wrapper.

This is CAMERA_HW_INTERFACE evidence, not an illumination/recognition accuracy
score. No digit, geometry or successful recognition is injected. Every child
command retains its ordinary echo7 result/log directory. Run only after building
and programming the intended image, with the fixed sheet visible and SW9 down.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

import echo7
from member_b_client import MemberBClient, MemberBClientError
from contract_model import markerEnabled, rotateBbox

MEASUREMENT_FIELDS = ("centreU", "centreV", "boxWidth", "boxHeight", "quality")
RAW_FIELDS = ("rawCameraMode", "rawModeRequested", "rawDisplayActive")


class InterfaceFailure(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise InterfaceFailure(message)


def identity(item):
    return item["markerType"], item["digit"]


def productionProfile(packet, previous=None):
    """Pin this run's advertised algorithm without reinterpreting older builds.

    Readers5,6 and7 are valid interface-validation targets. Reader6
    adds candidate ownership of native white anchor components; it must not be
    silently substituted for a reader5 result. Red/blue calibration thresholds
    may legitimately change during the held-query test, so only the algorithm
    IDs and the fixed, independently defined white profile are pinned here.
    """
    profile = {key: packet[key] for key in
               ("readerAlgorithm", "colourAlgorithm", "whiteMinimum", "whiteMaxSpread")}
    require(profile["readerAlgorithm"] in (5, 6, 7, 8, 9) and profile["colourAlgorithm"] == 3
            and profile["whiteMinimum"] == 84 and profile["whiteMaxSpread"] == 64,
            "validation requires reader5/6/7/8/9, colour3 and fixed white84/spread64")
    require(previous is None or profile == previous,
            "advertised algorithm profile changed during interface validation")
    return profile


def checkGeometry(item):
    require(markerEnabled(*identity(item)), "observation has an invalid typed identity")
    require(0 <= item["centreU"] < 240 and 0 <= item["centreV"] < 320
            and 1 <= item["boxWidth"] <= 240 and 1 <= item["boxHeight"] <= 320
            and 0 < item["quality"] <= 255, "observation has invalid geometry or zero quality")
    # A floor-centred inclusive rectangle must fit inside the public image.
    for centre, size, limit in ((item["centreU"], item["boxWidth"], 240),
                                (item["centreV"], item["boxHeight"], 320)):
        minimum = centre - (size-1)//2
        require(minimum >= 0 and minimum+size <= limit, "observation rectangle extends outside the public image")


def checkQueryBatch(batch, *, selector=None, duplicateBays=(), calibrationPair=False):
    """Check this demo's real typed positions, not a printed-scene score."""
    require(batch["completed"], "query did not complete")
    rows = batch["results"]
    require(bool(rows), "LIST/GET has no terminal result")
    first = rows[0]
    require(first["count"] > 0 and first["reason"] in (0, 1),
            f"query returned no usable observations: reason={first['reason']} count={first['count']}")
    require(len(batch["items"]) == len(rows) == first["count"], "query item count differs from its declared count")
    binding = ("requestTag", "frameId", "captureStartUs", "configVersion", "count", "reason")
    for index, item in enumerate(rows):
        require(all(item[key] == first[key] for key in binding), "query batch identity changed")
        require(item["index"] == index and bool(item["last"]) == (index == len(rows)-1), "query sequence is incomplete")
        checkGeometry(item)
        if selector is not None:
            require(identity(item) == selector, "GET returned another marker type/digit")
    if selector is None:
        require(first["reason"] == 0, "LIST reported GET multiplicity semantics")
    else:
        require(first["reason"] == int(len(rows) > 1), "GET reason does not match its multiplicity")
    positions = [(identity(row), *(row[key] for key in MEASUREMENT_FIELDS[:-1])) for row in rows]
    require(len(positions) == len(set(positions)), "query repeated exactly the same typed position")
    for bay in duplicateBays:
        require(sum(identity(row) == (1, bay) for row in rows) >= 2,
                f"declared duplicate blue{bay} did not produce multiple positions")
    if calibrationPair:
        red = [row for row in rows if identity(row) == (2, 1)]
        reference = [row for row in rows if identity(row) == (3, 15)]
        require(len(red) == len(reference) == 1, "LIST needs exactly one red1 and one proven BJ reference")
        require(red[0]["quality"] == reference[0]["quality"], "same-batch BJ quality differs from its red1 quality")
        require((red[0]["centreU"], red[0]["centreV"]) != (reference[0]["centreU"], reference[0]["centreV"]),
                "BJ returned the red1 centre instead of its own position")
    return {"count": len(rows), "frameId": first["frameId"], "configVersion": first["configVersion"],
            "captureStartUs": first["captureStartUs"], "identities": [list(identity(row)) for row in rows]}


def sameFramePositions(state, selector):
    """Use this frozen frame's measured bboxes, never a manifest or slot answer."""
    if selector == (3, 15):
        if not state["calibrationReferenceValid"]:
            return []
        marker = state["markers"][state["calibrationReferenceMarkerIndex"]]
        require(marker["isBlue"] and not marker["accepted"], "BJ metadata does not name a rejected blue reference region")
        markers = [{**marker, "quality": state["calibrationReferenceQuality"]}]
    else:
        markers = [marker for marker in state["markers"] if marker["accepted"]
                   and (1 if marker["isBlue"] else 2, marker["digit"]) == selector]
    return [{**rotateBbox(marker["xMin"], marker["xMax"], marker["yMin"], marker["yMax"]),
             "quality": marker["quality"]} for marker in markers]


def trackingAssessment(state, request, mode="locked"):
    """Return a pending reason or prove a report against its same-frame pixels.

    The pixels themselves are checked by the separate capture/recognition suite;
    here the comparison is to the FPGA's actual same-frame marker descriptors.
    An inconsistent successful report fails immediately, rather than being
    hidden by polling until some later report happens to agree.
    """
    require(state["activeRequest"] == request, "active tracking request changed unexpectedly")
    report, status = state["targetReport"], state["status"]
    if report["requestTag"] != request["requestTag"]:
        return "WAIT_CURRENT_REQUEST"
    require(identity(report) == identity(request), "current-tag report changed the requested marker type/digit")
    if report["configVersion"] != status["activeCfgVersion"] or state["configVersion"] != status["activeCfgVersion"]:
        return "WAIT_CURRENT_CONFIG"
    if report["frameId"] != state["frameId"]:
        return "WAIT_SAME_FRAME"
    if mode == "clear":
        if report["targetSelected"] or report["reason"] != 1:
            return "WAIT_NO_SELECTION"
        require(not report["ambiguous"] and not report["observed"] and not report["locked"]
                and all(report[key] == 0 for key in MEASUREMENT_FIELDS), "CLEAR left public measurements")
        return "PASS"
    age = (state["timeUs"] - report["captureStartUs"]) & 0xffffffff
    if not status["perceptionReady"] or status["interactionBusy"] or age > 150000:
        return "WAIT_READY_FRESH_REPORT"
    if not report["frameGood"] or not report["targetSelected"]:
        require(not report["locked"] and not report["ambiguous"], "bad/unselected frame claimed a lock or ambiguity")
        return "WAIT_GOOD_SELECTED_FRAME"
    positions = sameFramePositions(state, identity(request))
    if report["locked"]:
        require(report["observed"] and not report["ambiguous"] and len(positions) == 1,
                "locked report is not supported by exactly one same-frame matching marker")
        require(report["reason"] == 0, "locked report has a non-OK reason")
        checkGeometry(report)
        require(all(report[key] == positions[0][key] for key in MEASUREMENT_FIELDS),
                "locked report geometry/quality differs from the same-frame marker bbox")
    if report["ambiguous"]:
        require(len(positions) >= 2, "ambiguous report has fewer than two same-frame matching positions")
        require(report["reason"] == 4 and not report["observed"] and not report["locked"]
                and all(report[key] == 0 for key in MEASUREMENT_FIELDS), "ambiguous report leaked a public measurement or reason")
    if mode == "ambiguous":
        if not report["ambiguous"] or report["reason"] != 4:
            return "WAIT_AMBIGUITY"
        return "PASS"
    if not report["observed"] or not report["locked"] or report["ambiguous"]:
        return "WAIT_UNIQUE_LOCK"
    return "PASS"


class HardwareValidation:
    def __init__(self, args, out, result):
        self.args, self.out, self.result = args, out, result
        self.deadline = time.monotonic() + args.timeout
        self.client = MemberBClient(quartusBin=args.quartus_bin, cable=args.cable,
                                    device=args.device, timeout=min(30, args.timeout))
        self.target = None
        self.configVersion = None

    def save(self):
        pending = self.out / "result.tmp"
        pending.write_text(json.dumps(self.result, indent=2) + "\n", encoding="utf-8")
        pending.replace(self.out / "result.json")

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, "overall interface validation deadline exceeded")
        return max(1, min(30, math.ceil(remaining)))

    def check(self, name, condition, **details):
        self.result["checks"].append({"name": name, "status": "PASS" if condition else "FAIL", **details})
        self.save()
        require(condition, name)

    def register(self, label, child):
        path = Path(child["outputDirectory"]) / "result.json"
        self.result["calls"].append({"label": label, "command": child.get("command"),
            "status": child.get("status"), "exitCode": child.get("exitCode"),
            "resultPath": str(path), "resultSha256": echo7.digest(path) if path.is_file() else None})
        self.save()
        if child.get("exitCode"):
            if child["exitCode"] == 2:
                raise echo7.Blocked(child.get("reason", "child environment blocked"))
            raise InterfaceFailure(child.get("reason", "child transaction failed"))
        actual = child.get("target")
        require(actual is not None, "child did not identify its actual FPGA target")
        if self.target is None:
            self.target = actual
            self.result["target"] = actual
            # Subsequent calls must resolve this exact identity, not a new
            # apparently unique device that appeared after the first call.
            self.client.options.update(cable=actual["cable"], device=actual["device"])
        require(actual == self.target, "FPGA target changed during interface validation")
        packet = child.get("boardStatus", {}).get("decoded", child.get("queryTransaction", {}))
        require(packet.get("buildId") == self.result["expectedBuildId"], "board buildId differs from the expected successful build")
        require(packet.get("debugSchemaVersion") == 8 and packet.get("contractVersion") == 3,
                "validation requires private schema8/public contract3")
        if "boardStatus" in child:
            require(not any(packet[key] for key in RAW_FIELDS), "SW9 must be down with capture and display processing active")
            self.result["algorithmProfile"] = productionProfile(packet, self.result.get("algorithmProfile"))
            self.save()
        self.remaining()
        return child

    def call(self, label, method, *args):
        self.client.options["timeout"] = self.remaining()
        try:
            child = getattr(self.client, method)(*args)
        except MemberBClientError as exc:
            self.register(label, exc.result)
            raise
        return self.register(label, child)

    def runnerAction(self, label, *, calibration=False):
        """Only the deliberate held-query setup bypasses the complete-list API.

        Opcode8 enqueues a real public LIST and leaves its response backpressured;
        it cannot inject a digit or a successful observation. Calibration follows
        the existing real-red1 eight-frame workflow and busy-rejection check.
        """
        options = argparse.Namespace(command="calibrate" if calibration else "held_query_setup",
            quartus_bin=self.args.quartus_bin, modelsim_bin=None, cable=self.target["cable"],
            device=self.target["device"], timeout=self.remaining(), arm=True, verify_busy=True)
        runner = echo7.Runner(options)
        try:
            if calibration:
                runner.execute()
            else:
                runner.control(8 << 24)
            runner.result.update(status="PASS", exitCode=0)
        except Exception as exc:
            runner.result.update(status="BLOCKED" if isinstance(exc, echo7.Blocked) else "FAIL",
                exitCode=2 if isinstance(exc, echo7.Blocked) else 1, reason=str(exc))
        runner.result["finishedUtc"] = datetime.now(timezone.utc).isoformat()
        (runner.out / "result.json").write_text(json.dumps(runner.result, indent=2) + "\n", encoding="utf-8")
        return self.register(label, runner.result)

    def state(self, label):
        return self.call(label, "status")["boardStatus"]["decoded"]

    def poll(self, label, request, mode="locked", initial=None, held=False):
        deadline = min(self.deadline, time.monotonic() + 60)
        state = initial
        while time.monotonic() < deadline:
            if state is None:
                state = self.state(label)
            require(state["status"]["activeCfgVersion"] == self.configVersion,
                    "configuration changed outside the explicit held-query calibration step")
            if held:
                require(state["queryBusy"], "held query disappeared before it was drained")
            assessment = trackingAssessment(state, request, mode)
            self.result["trackingPolls"].append({"label": label, "assessment": assessment,
                "frameId": state["frameId"], "report": state["targetReport"],
                "timeUs": state["timeUs"], "queryBusy": state["queryBusy"]})
            self.save()
            if assessment == "PASS":
                self.check(label, True, mode=mode, request=request, frameId=state["frameId"],
                           report=state["targetReport"])
                return state
            state = None
            time.sleep(0.05)
        raise InterfaceFailure(f"{label}: no matching {mode} report before the bounded wait expired")

    def track(self, label, markerType, digit=None, *, ambiguous=False, held=False):
        state = self.call(label, "track", markerType, digit)["boardStatus"]["decoded"]
        from query_transport import markerSelector
        requested = markerSelector(markerType, digit)
        request = dict(state["activeRequest"])
        self.check(label + " request accepted", request["operation"] == 1 and identity(request) == requested,
                   request=request)
        return self.poll(label + " report", request, "ambiguous" if ambiguous else "locked", state, held)

    def clear(self, label, *, held=False):
        state = self.call(label, "clear")["boardStatus"]["decoded"]
        request = dict(state["activeRequest"])
        self.check(label + " request", request["operation"] == 0 and identity(request) == (0, 15), request=request)
        return self.poll(label + " report", request, "clear", state, held)

    def preserve(self, label, request):
        state = self.state(label)
        self.check(label, state["activeRequest"] == request,
                   expected=request, actual=state["activeRequest"])
        require(state["status"]["activeCfgVersion"] == self.configVersion, "unexpected calibration/configuration change")
        return state

    def query(self, label, request, markerType=None, digit=None, *, pair=False):
        if markerType is None:
            child = self.call(label, "markers")
            selector = None
        else:
            from query_transport import markerSelector
            selector = markerSelector(markerType, digit)
            child = self.call(label, "locate", markerType, digit)
        batch = child["queryTransaction"]
        duplicates = self.args.expect_duplicate_bays if markerType is None else (
            [digit] if markerType == "bay" and digit in self.args.expect_duplicate_bays else [])
        details = checkQueryBatch(batch, selector=selector, duplicateBays=duplicates, calibrationPair=pair)
        self.check(label, details["configVersion"] == self.configVersion, **details)
        self.preserve(label + " preserves tracking", request)
        return batch

    def execute(self):
        initial = self.state("initial identity")
        readyDeadline = min(self.deadline, time.monotonic() + 60)
        while not (initial["status"]["perceptionReady"] and initial["status"]["calibrated"]
                   and not initial["status"]["interactionBusy"]):
            require(time.monotonic() < readyDeadline, "initial real calibration/perception did not become ready")
            initial = self.state("wait initial real calibration")
        self.configVersion = initial["status"]["activeCfgVersion"]
        self.check("initial actual profile ready", True, configVersion=self.configVersion)
        self.call("initial abandoned query recovery", "drain")
        tracked = self.track("track blue3", "bay", 3)
        selected = dict(tracked["activeRequest"])
        self.query("LIST while blue3 tracked", selected, pair=True)
        for bay in sorted({1, *self.args.expect_duplicate_bays}):
            self.query(f"GET blue{bay}", selected, "bay", bay)
        self.query("GET red1", selected, "function", 1)
        self.query("GET BJ", selected, "reference")
        self.track("track red1", "function", 1)
        self.track("track red2", "function", 2)
        self.track("track BJ", "reference")
        for bay in self.args.expect_duplicate_bays:
            self.track(f"duplicate blue{bay} remains ambiguous", "bay", bay, ambiguous=True)
        cleared = self.clear("CLEAR before LIST")
        self.query("LIST after CLEAR", dict(cleared["activeRequest"]), pair=True)

        held = self.runnerAction("enqueue real LIST without reading")['boardStatus']['decoded']
        self.check("unread LIST is busy", held["queryBusy"], frameId=held["frameId"], timeUs=held["timeUs"])
        oldConfig = self.configVersion
        progressDeadline = min(self.deadline, time.monotonic() + 30)
        while True:
            progress = self.state("camera progresses while query held")
            require(progress["queryBusy"], "query was consumed without READ_QUERY")
            delta = (progress["frameId"] - held["frameId"]) & 0xffff
            if 0 < delta < 0x8000:
                break
            require(delta == 0 and time.monotonic() < progressDeadline, "camera did not progress while query was backpressured")
        self.check("camera progresses while query held", True, initialFrame=held["frameId"],
                   laterFrame=progress["frameId"], nativeFrameDelta=delta)
        self.track("SELECT red1 while query held", "function", 1, held=True)
        cleared = self.clear("CLEAR while query held", held=True)
        heldRequest = dict(cleared["activeRequest"])
        if self.args.calibrate_held:
            calibrated = self.runnerAction("real eight-frame calibration while query held", calibration=True)
            state = calibrated["boardStatus"]["decoded"]
            self.configVersion = state["status"]["activeCfgVersion"]
            self.check("held-query calibration commits once", state["queryBusy"]
                and ((self.configVersion-oldConfig) & 0xffff) == 1
                and calibrated["calibrationAssessment"]["configurationCommitted"],
                oldConfig=oldConfig, newConfig=self.configVersion,
                assessment=calibrated["calibrationAssessment"])
        drained = self.call("drain actual held query", "drain")["queryTransaction"]
        old = drained["drainedReplies"]
        self.check("held query drained without replacement query", bool(old) and not drained["results"] and not drained["items"],
                   records=len(old))
        # We first observe this held batch during drain. A timestamp before the
        # enqueue freeze, and the old configuration after a real commit, prove
        # it was not restamped at PC retrieval; this is not a before/after byte
        # comparison of packets that were never read before the calibration.
        original = old[0]
        self.check("held query keeps its original configuration/time",
            all(row["configVersion"] == oldConfig and row["captureStartUs"] == original["captureStartUs"]
                and row["frameId"] == original["frameId"] for row in old)
            and ((held["timeUs"]-original["captureStartUs"]) & 0xffffffff) < 0x80000000,
            enqueueTimeUs=held["timeUs"], originalCaptureStartUs=original["captureStartUs"],
            originalConfigVersion=original["configVersion"], currentConfigVersion=self.configVersion)
        require(original["count"] > 0 and original["reason"] == 0, "held LIST did not preserve a real nonempty good-frame batch")
        after = self.preserve("drain preserves active request", heldRequest)
        self.check("query idle after draining", not after["queryBusy"])
        latest = self.query("new LIST after held-query recovery", heldRequest, pair=True)
        difference = (latest["results"][0]["captureStartUs"]-original["captureStartUs"]) & 0xffffffff
        self.check("new query uses a newer capture", 0 < difference < 0x80000000,
                   previousCaptureStartUs=original["captureStartUs"], newCaptureStartUs=latest["results"][0]["captureStartUs"])


def expectedBuild(args):
    if args.expected_build_id is not None:
        require(0 <= args.expected_build_id <= 0xffffffff, "expected buildId must fit32bits")
        return args.expected_build_id, {"source": "EXPLICIT_ARGUMENT"}
    path = echo7.WORK / "last_build.json"
    if not path.is_file():
        raise echo7.Blocked("no last_build.json; build/program first or supply --expected-build-id")
    record = json.loads(path.read_text(encoding="utf-8"))
    require(record.get("status") == "PASS", "last_build.json does not describe a successful build")
    return record["source"]["buildId"], {"path": str(path), "sha256": echo7.digest(path),
        "sourceSha256": record["source"]["sha256"], "sofSha256": record.get("sof", {}).get("sha256")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quartus-bin")
    parser.add_argument("--cable")
    parser.add_argument("--device", help="Exact discovered device name or chain index string")
    parser.add_argument("--timeout", type=int, default=600,
        help="Overall deadline in seconds, checked between calls; each external phase is also bounded to at most30s")
    parser.add_argument("--expected-build-id", type=lambda value: int(value, 0),
        help="Expected unsigned buildId (e.g.0x12345678); default: successful build/member_b/last_build.json")
    parser.add_argument("--expect-duplicate-bays", nargs="*", type=int, choices=range(1, 7), default=[],
        help="Declare physically repeated bay IDs, e.g.1 2; require multiple GET positions and zero-measurement SELECT ambiguity")
    parser.add_argument("--calibrate-held", action="store_true",
        help="Perform one real red1 eight-frame calibration while a query response is deliberately stalled")
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    args.expect_duplicate_bays = sorted(set(args.expect_duplicate_bays))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out = echo7.WORK / (stamp + "_member_c_interface")
    out.mkdir(parents=True, exist_ok=False)
    result = {"schema": "echo7-member-c-interface-validation-v1", "status": "RUNNING",
        "level": "CAMERA_HW_INTERFACE", "inputSource": "LIVE_FPGA_PUBLIC_INTERFACE_JTAG",
        "outputDirectory": str(out), "startedUtc": datetime.now(timezone.utc).isoformat(),
        "scriptSha256": echo7.digest(__file__), "arguments": vars(args), "calls": [], "checks": [], "trackingPolls": [],
        "scope": "Typed public-interface transactions on a fixed scene; NOT illumination robustness or printed-digit accuracy scoring.",
        "limits": "Sparse JTAG snapshots cannot alone prove exactly three consecutive acquisition frames. Same-frame report geometry is checked against FPGA marker metadata; separate fresh RGB/CRC/pixel comparison and physical VGA evidence remain necessary.",
        "deadlineMeaning": "No new calls after the overall deadline; a current call has at most two bounded external phases plus bounded process cleanup.",
        "recoveryCommand": "python tools/echo7.py markers --drain"}
    validation = HardwareValidation(args, out, result)
    try:
        result["expectedBuildId"], result["expectedBuildSource"] = expectedBuild(args)
        validation.save()
        validation.execute()
        result.update(status="PASS", exitCode=0)
    except echo7.Blocked as exc:
        result.update(status="BLOCKED", exitCode=2, reason=str(exc))
    except (OSError, RuntimeError, ValueError, KeyError, IndexError, TypeError, ImportError) as exc:
        result.update(status="FAIL", exitCode=1, reason=str(exc))
    result["finishedUtc"] = datetime.now(timezone.utc).isoformat()
    validation.save()
    print(json.dumps(result, indent=2))
    return result["exitCode"]


if __name__ == "__main__":
    raise SystemExit(main())
