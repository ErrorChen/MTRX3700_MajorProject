"""Strictly decode one bounded JTAG session into the existing trial assessor.

The transport records real frozen board words. Replay here means assessing
already received records, not generating camera data or repeating held frames.
Every complete record is retained, including old-request and failed frames.
"""
from pathlib import Path
import json
import re

from debug_decode import decodeWords, schemaLayout
from hardware_measurement import measureTrials


def parseTrialStream(output, expectedBuildId):
    records = []
    current = None
    done = None
    for line in output.splitlines():
        if not line.startswith("ECHO7_TRIAL_"):
            continue
        fields = line.split("\t")
        kind = fields[0].removeprefix("ECHO7_TRIAL_")
        if kind == "BEGIN":
            if current is not None or len(fields) != 5 or int(fields[1]) != len(records):
                raise ValueError("invalid or nested trial record boundary")
            if fields[2] not in ("INITIAL", "SELECT", "STATUS", "CLEAR"):
                raise ValueError("unknown trial record phase")
            current = dict(serial=int(fields[1]), phase=fields[2], trial=int(fields[3]),
                           bay=int(fields[4]), words=[])
        elif kind == "DONE":
            if current is not None or done is not None or len(fields) != 4:
                raise ValueError("invalid trial completion record")
            done = dict(trials=int(fields[1]), statusRecords=int(fields[2]), elapsedMs=int(fields[3]))
        else:
            if current is None or len(fields) < 2 or int(fields[1]) != current["serial"] or done:
                raise ValueError("trial record serial/order mismatch")
            if kind == "HEADER":
                if len(fields) != 3 or "header" in current or not re.fullmatch("[01]{96}", fields[2]):
                    raise ValueError("invalid trial header")
                current["header"] = fields[2]
            elif kind == "ACTION":
                if len(fields) != 4 or "action" in current or not re.fullmatch("[01]{32}", fields[3]):
                    raise ValueError("invalid trial action acknowledgement")
                current["action"] = dict(opcode=int(fields[2]), meta=int(fields[3], 2))
            elif kind == "WORD":
                if len(fields) != 4 or int(fields[2]) != len(current["words"]) or not re.fullmatch("[01]{32}", fields[3]):
                    raise ValueError("incomplete, duplicated or reordered trial words")
                current["words"].append(int(fields[3], 2))
            elif kind == "END":
                if len(fields) != 2 or "header" not in current:
                    raise ValueError("trial frozen snapshot is incomplete")
                header = current["header"]
                magic, buildId, meta = (int(header[i:i+32], 2) for i in (0, 32, 64))
                wordCount = schemaLayout(meta >> 24)["wordCount"]
                if len(current["words"]) != wordCount:
                    raise ValueError("trial frozen snapshot is incomplete")
                decoded = decodeWords(current["words"])
                if (magic != 0x42444247 or buildId != expectedBuildId or decoded["buildId"] != buildId
                        or meta >> 24 != decoded["debugSchemaVersion"] or (meta >> 16) & 255 != 2
                        or meta & 255 != wordCount):
                    raise ValueError("trial source/schema/header identity mismatch")
                action = current.get("action")
                opcode = {"SELECT": 1, "CLEAR": 2}.get(current["phase"])
                if opcode is not None:
                    if action is None or action["opcode"] != opcode:
                        raise ValueError("trial command has no matching action acceptance")
                    actionMeta = action["meta"]
                    if actionMeta >> 24 != meta >> 24 or (actionMeta >> 16) & 255 != 2 or actionMeta & 255 != wordCount:
                        raise ValueError("trial action has incompatible schema")
                    if actionMeta & 0x7000:
                        raise ValueError("trial SELECT/CLEAR was rejected")
                elif action is not None:
                    raise ValueError("unexpected action attached to read-only snapshot")
                current["decoded"] = decoded
                records.append(current)
                current = None
            else:
                raise ValueError("unknown trial stream record")
    if current is not None:
        raise ValueError("truncated frozen trial snapshot")
    return records, done


class TrialRecordReader:
    """Feed actual ordered records to the same assessor used by host tests."""
    def __init__(self, runner, records):
        self.args, self.out, self.result = runner.args, runner.out, runner.result
        self.records = records
        self.position = 0
        self.selections = 0
        self.context = None

    def control(self, command=0):
        if self.position >= len(self.records):
            raise RuntimeError("JTAG trial stream ended before all required observations")
        record = self.records[self.position]
        expected = ((1 << 24) | record["bay"] if record["phase"] == "SELECT" else
                    2 << 24 if record["phase"] == "CLEAR" else 0)
        if command != expected:
            raise RuntimeError("JTAG record sequence differs from the independent host trial assessor")
        if self.position == 0 and record["phase"] != "INITIAL":
            raise RuntimeError("JTAG trials have no initial baseline")
        if record["phase"] == "SELECT":
            context = (self.selections // 6 + 1, self.selections % 6 + 1)
            if (record["trial"], record["bay"]) != context:
                raise RuntimeError("trial selection labels are out of order")
            self.context = context
            self.selections += 1
        elif record["phase"] == "STATUS":
            if (record["trial"], record["bay"]) != self.context:
                raise RuntimeError("trial observation labels do not match the selection")
        elif record["trial"] or record["bay"] or (record["phase"] == "INITIAL" and self.position != 0):
            raise RuntimeError("invalid initial/clear trial label")
        self.position += 1
        return {"decoded": record["decoded"]}


def measureLiveTrials(runner, trials, expectedBuildId):
    runner.result.update(level="CAMERA_HW", inputSource="LIVE_CAMERA_JTAG_SAMPLED_TRIALS",
                         transport="ONE_BOUNDED_JTAG_SESSION")
    target = runner.target()
    script = Path(__file__).resolve().parents[1] / "tcl/jtag_control.tcl"
    code, output = runner.run("bctl_trials", [runner.qt("quartus_stp"), "-t", script,
        "trial-stream", target["cable"], target["device"], str(trials), str(min(900, max(1, int(runner.args.timeout))))], checked=False)
    records, done = parseTrialStream(output, expectedBuildId)
    # Raw stdout is already in the runner log; this structured copy makes every
    # complete frozen record reviewable before any metric can raise an error.
    (runner.out / "trial_stream.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
    runner.result["trialTransport"] = dict(returnCode=code, completion=done, completeRecords=len(records))
    reader = TrialRecordReader(runner, records)
    try:
        measureTrials(reader, trials)
    finally:
        runner.result["trialTransport"]["assessedRecords"] = reader.position
    if code or not done or done["trials"] != trials or done["statusRecords"] != sum(r["phase"] == "STATUS" for r in records):
        raise RuntimeError("JTAG trial session did not complete exactly the requested trials")
    if reader.position != len(records) or not records or records[-1]["phase"] != "CLEAR":
        raise RuntimeError("JTAG trial stream contains unassessed records or lacks CLEAR")
