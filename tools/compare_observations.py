#!/usr/bin/env python3
"""Describe three paired SW8 normal/bypass runs from chassis_debug observe.

Reads files only. Valid comparison means matching build/profile/physical target,
not six-bay acceptance, ground docking or image-to-UART latency measurement.
Bad/unlocked/held samples are retained in both poll and distinct-frame summaries.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROFILE_FIELDS = ("buildId", "debugSchemaVersion", "contractVersion", "orientationProfile",
                  "redMinimum", "blueMinimum", "readerAlgorithm", "colourAlgorithm",
                  "whiteMinimum", "whiteMaxSpread", "whiteMode", "whiteAnchorMinimum",
                  "candidateSizePruning", "activeCandidateCapacity", "outputCandidateCapacity", "poolLayout")


def require(condition, reason):
    if not condition: raise ValueError(reason)


def summary(states, kind, digit):
    if kind == "cctl":
        return {"samples": len(states),
                "healthy": sum(bool(s["sourceHealthyFresh"]) for s in states),
                "observed": sum(bool(s["targetObserved"]) for s in states),
                "locked": sum(bool(s["targetLockedFresh"]) for s in states),
                "armed": sum(bool(s["taskArmed"]) for s in states),
                "motionPermitted": sum(bool(s["motionPermit"]) for s in states),
                "states": {name: sum(s["state"] == name for s in states) for name in sorted({s["state"] for s in states})}}
    def current(s):
        report = s["targetReport"]
        return (report["targetSelected"] and report["markerType"] == 1 and report["digit"] == digit
                and report["requestTag"] == s["activeRequest"]["requestTag"]
                and report["configVersion"] == s["configVersion"]
                and report["frameId"] == s["frameId"] and report["captureStartUs"] == s["captureStartUs"])
    def usable(s):
        return (current(s) and s["frameGood"] and s["targetReport"]["frameGood"]
                and s["freshAtSnapshot"] and not s["targetReport"]["ambiguous"]
                and not any(s.get(key, False) for key in ("candidateOverflow", "candidateError", "candidateOverrun")))
    latencies = [s["processingLatencyUs"] for s in states]
    return {"samples": len(states), "badFrames": sum(not s["frameGood"] for s in states),
            "currentTargetReports": sum(bool(current(s)) for s in states),
            "observed": sum(bool(usable(s) and s["targetReport"]["observed"]) for s in states),
            "locked": sum(bool(usable(s) and s["targetReport"]["locked"]) for s in states),
            "stale": sum(not s["freshAtSnapshot"] for s in states),
            "candidateFaults": sum(any(s.get(key, False) for key in
                                         ("candidateOverflow", "candidateError", "candidateOverrun")) for s in states),
            "captureToCompletionUs": {"min": min(latencies), "max": max(latencies),
                                      "mean": sum(latencies) / len(latencies)},
            "latencyMeaning": "FPGA capture-to-completion only; not image-change-to-UART or physical response latency"}


def assess_run(data, bypass):
    require(data["schema"] == "echo7-observation-v1" and data["status"] == "COMPLETE", "run is not complete observe output")
    require(data["inputSource"] == "LIVE_FPGA_JTAG_READONLY" and
            data["transport"] == "ONE_PERSISTENT_JTAG_SESSION" and data["operations"] == ["STATUS", "BSTATUS"],
            "run did not use the read-only observation path")
    rows = data["samples"]
    require(len(rows) >= 3 and all(row["complete"] for row in rows), "need at least three complete polls per run")
    if data.get("requestedSamples") is not None:
        require(len(rows) == data["requestedSamples"], "requested poll count was not retained")
    cstates, bstates = [row["cctl"]["state"] for row in rows], [row["bctl"]["state"] for row in rows]
    target = {key: cstates[0][key] for key in ("mode", "inputSource", "digit", "switchMask", "stableMask")}
    digit = target["digit"]
    require(target["mode"] in ("VISION_ONLY", "INTEGRATED") and target["inputSource"] == "REAL_CAMERA", "not real camera mode")
    require(1 <= digit <= 6 and target["switchMask"] == target["stableMask"] == 1 << (digit - 1), "physical selection is not one-hot")
    profile = {key: bstates[0][key] for key in PROFILE_FIELDS}
    cconfig, ctag = cstates[0]["configVersion"], cstates[0]["requestTag"]
    bconfig, btag = bstates[0]["configVersion"], bstates[0]["activeRequest"]["requestTag"]
    previous, lastEnd = None, -1.0
    for index, (row, cstate, bstate) in enumerate(zip(rows, cstates, bstates)):
        require(row["index"] == index and lastEnd <= row["cctl"]["readStartSeconds"] <= row["cctl"]["readEndSeconds"]
                <= row["bctl"]["readStartSeconds"] <= row["bctl"]["readEndSeconds"], "read sequence/times are not ordered")
        lastEnd = row["bctl"]["readEndSeconds"]
        require(all(cstate[key] == value for key, value in target.items()) and cstate["selection"] == "VALID",
                "physical target or mode changed during run")
        require(cstate["configVersion"] == cconfig and cstate["requestTag"] == ctag, "CCTL request/config changed during run")
        require(all(bstate[key] == value for key, value in profile.items()), "camera profile changed during run")
        require(bstate["configVersion"] == bconfig and bstate["status"]["activeCfgVersion"] == bconfig
                and bstate["activeRequest"]["requestTag"] == btag, "BCTL request/config changed during run")
        require(bstate["activeRequest"]["operation"] == 1 and bstate["activeRequest"]["markerType"] == 1
                and bstate["activeRequest"]["digit"] == digit, "BCTL selected target differs from physical target")
        require(bstate["bypassPerspective"] == bypass, "SW8 mode differs from declared normal/bypass input")
        require(not cstate["rawCameraMode"] and not any(bstate[key] for key in
                    ("rawCameraMode", "rawModeRequested", "rawDisplayActive")), "SW9/raw display is not an algorithm trial")
        frame = bstate["frameId"]
        require(previous is None or 0 <= ((frame - previous) & 65535) < 32768, "B frame order moved backwards")
        previous = frame
        require(bstate["processingLatencyUs"] == ((bstate["completionUs"] - bstate["captureStartUs"]) & 0xffffffff),
                "latency disagrees with FPGA timestamps")
    result = {"label": data["label"], "startedAtUtc": data["startedAtUtc"], "target": target,
              "profile": profile, "configVersion": {"cctl": cconfig, "bctl": bconfig},
              "requestTag": {"cctl": ctag, "bctl": btag}, "bypass": bypass}
    for kind, states in (("cctl", cstates), ("bctl", bstates)):
        seen, distinct = set(), []
        for state in states:
            key = ((state["requestTag"], state["configVersion"], state["frameId"]) if kind == "cctl"
                   else (state["buildId"], state["configVersion"], state["frameId"], state["captureStartUs"]))
            if key not in seen:
                seen.add(key); distinct.append(state)
        result[kind] = {"allPolls": summary(states, kind, digit), "distinctFrames": summary(distinct, kind, digit),
                        "heldPolls": len(states) - len(distinct)}
    return result


def compare(normal, bypass, conditions):
    require(len(normal) == len(bypass) == 3, "exactly three runs per mode are required")
    runs = [assess_run(data, mode) for mode, group in ((False, normal), (True, bypass)) for data in group]
    require(len({run["startedAtUtc"] for run in runs}) == 6, "one run was reused as more than one trial")
    require(all(run["profile"] == runs[0]["profile"] and run["target"] == runs[0]["target"] for run in runs),
            "comparison build/profile/physical target/mode differs")
    require(all(run["cctl"]["allPolls"]["samples"] == runs[0]["cctl"]["allPolls"]["samples"] for run in runs),
            "matched comparison requires the same poll count in all six runs")
    return {"schema": "echo7-observation-comparison-v1",
            "status": "COMPARISON_VALID" if conditions.strip() else "UNCONFIRMED_CONDITIONS",
            "conditionsConfirmed": conditions, "profile": runs[0]["profile"], "target": runs[0]["target"],
            "pairs": [{"trial": i + 1, "normal": runs[i], "bypass": runs[i + 3]} for i in range(3)],
            "scope": "Descriptive paired camera observations only. Failures retained; no six-bay, navigation, docking or physical latency acceptance.",
            "snapshotMeaning": "CCTL/BCTL freeze independently; their frame IDs are not required or claimed to match."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--normal", nargs=3, type=Path, required=True, metavar="JSON")
    parser.add_argument("--bypass", nargs=3, type=Path, required=True, metavar="JSON")
    parser.add_argument("--conditions-confirmed", default="", metavar="STATEMENT",
                        help="operator statement that scene/position/light/focus were unchanged for these exact runs")
    parser.add_argument("--out", type=Path, required=True, help="new output JSON, never overwrite input/evidence")
    args = parser.parse_args(argv)
    if args.out.exists(): parser.error("output exists; refusing to overwrite")
    result = {"schema": "echo7-observation-comparison-v1", "status": "INVALID_COMPARISON"}
    try:
        require(len({path.resolve() for path in args.normal + args.bypass}) == 6, "six distinct run files are required")
        groups = [[json.loads(path.read_text(encoding="utf-8-sig")) for path in group] for group in (args.normal, args.bypass)]
        result = compare(*groups, args.conditions_confirmed)
        code = 0 if result["status"] == "COMPARISON_VALID" else 2
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        result["reason"], code = str(error), 1
    result["inputs"] = {"normal": list(map(str, args.normal)), "bypass": list(map(str, args.bypass))}
    result["exitCode"] = code
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as output: json.dump(result, output, indent=2)
    print(json.dumps({"status": result["status"], "path": str(args.out), "reason": result.get("reason")}))
    return code


if __name__ == "__main__": raise SystemExit(main())
