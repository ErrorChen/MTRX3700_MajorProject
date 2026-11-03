#!/usr/bin/env python3
"""Render B's frozen targets as one A4 page with source-checked measurements.

Requires reportlab and pypdf. No hardware command is executed. Missing current
camera results stay PENDING. The index's existing records.trials/calibration
entries are used when available, or supply explicit --hardware/--calibration.
Repeat --calibration for each attempt, or put three {path, sha256} entries in
index.records.calibrationTrials. A lone calibration record is not three trials.
The source identity must match the recorded board before numbers are displayed.
"""
import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def readRecord(index, name, explicit, record=None):
    record = record or index.get("records", {}).get(name)
    path = explicit or (Path(record["path"]) if record else None)
    if path is None:
        return None, None
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    if not explicit and record.get("sha256") and digest(path) != record["sha256"]:
        raise ValueError(f"{name} evidence hash differs from index")
    result = json.loads(path.read_text(encoding="utf-8"))
    board = result.get("initialStatus", result.get("boardStatus", {}).get("decoded", {}))
    if board.get("buildId") != index["source"]["buildId"]:
        raise ValueError(f"{name} board identity does not match indexed source")
    if result.get("level") != "CAMERA_HW":
        raise ValueError(f"{name} is not labelled CAMERA_HW")
    if name == "calibration":
        if result.get("command") != "calibrate" or not result.get("calibrationTrace"):
            raise ValueError("calibration record has no real-pixel frame trace")
    return result, path


def measurements(hardware, calibrations):
    accuracy = "PENDING current, independent camera trials and printed-label scoring."
    latency = "PENDING current three-trial board-time measurement."
    convergence = "PENDING current real-pixel calibration completion and timing."
    if hardware:
        trials = hardware.get("trials", [])
        if len(trials) != 3:
            accuracy = f"INCOMPLETE: {len(trials)}/3 trials recorded."
            scores = [trial.get("printedDigitScore") for trial in trials]
            if scores and all(scores):
                accuracy += " " + "; ".join(
                    f"T{i+1}: {score['correct']}/{score['expected']}, wrong {score['wrongOrAmbiguous']}"
                    for i, score in enumerate(scores))
            values = [record["status"]["processingLatencyUs"] for record in hardware.get("observations", [])]
            latency = (f"INCOMPLETE {len(trials)}/3; observed max {max(values)/1000:.3f} ms, including failures."
                       if values else "INCOMPLETE: no observed completion times.")
        else:
            scores = [trial.get("printedDigitScore") for trial in trials]
            if all(scores):
                accuracy = "; ".join(
                    f"T{i+1}: {score['correct']}/{score['expected']}, wrong {score['wrongOrAmbiguous']}, outside {score['outside']}"
                    for i, score in enumerate(scores))
            else:
                accuracy = "Printed-region score PENDING. Typed-set frames: " + ", ".join(
                    f"T{i+1} {trial['typedSetPasses']}/{trial['currentRequestSamples']}" for i, trial in enumerate(trials))
            observed = [[record["status"]["processingLatencyUs"] for record in hardware.get("observations", [])
                         if record["trial"] == trial["trial"]] for trial in trials]
            if all(observed):
                latency = "; ".join(f"T{i+1} max {max(values)/1000:.3f} ms" for i, values in enumerate(observed))
                latency += ". All observed completions; invalid/transition records retained."
            else:
                latency = "PENDING complete per-trial observation records."
    if calibrations:
        parts = []
        for number, calibration in enumerate(calibrations, 1):
            assessment = calibration.get("calibrationAssessment")
            if not assessment:
                parts.append(f"T{number}: completion assessment PENDING; ACK alone is insufficient.")
                continue
            timing = assessment.get("timingTarget", {})
            bound = assessment.get("confirmedAttemptToCommitUpperBoundUs")
            part = f"T{number}: {assessment['status']}, {assessment['validSampleFrames']}/8 samples; "
            part += (f"bound {bound/1000:.3f} ms ({timing.get('status', 'NOT_ASSESSED')})."
                     if bound is not None else "timing NOT_MEASURED.")
            parts.append(part)
        if len(calibrations) != 3:
            parts.append(f"INCOMPLETE: {len(calibrations)}/3 attempts recorded.")
        convergence = " ".join(parts)
    return accuracy, latency, convergence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True,
                        help="Explicit current run-summary index; historical evidence directories are not implicit inputs")
    parser.add_argument("--hardware", type=Path)
    parser.add_argument("--calibration", type=Path, action="append")
    parser.add_argument("--out", type=Path, default=ROOT / "build/member_b/member_b_datasheet.pdf")
    args = parser.parse_args()
    index = json.loads(args.index.read_text(encoding="utf-8"))
    sourceSha256 = index["source"]["sha256"]
    if len(sourceSha256) != 64 or any(character not in "0123456789abcdef" for character in sourceSha256):
        raise ValueError("datasheet index requires a complete lowercase source SHA256")
    # The evidence index selects the actual source epoch. Historical datasheets
    # retain their original switch and eight-sign scene; current shared-pool
    # evidence uses the user-added duplicate1/2 scene and the new SW8 mapping.
    sharedPool = index.get("candidatePool", {}).get("totalCompletedSlots") == 16
    comparisonSwitch = "SW8" if sharedPool else "SW9"
    population = "ten printed signs (red1/2, blue1/1/2/2/3/4/5/6)" if sharedPool else "eight formal signs"
    scene = ("One unfolded A4 plus the user's two extra rotated blue1/2 signs; " if sharedPool else
             "One unfolded landscape A4, red1/2 and blue1-6; ")
    prediction = ("Reader5 should resolve rotation using a unique native anchor. Very thin/clipped anchors can still reject; duplicate IDs must remain ambiguous." if sharedPool else
                  "Reader4 should recover blue6's weak C stroke. Oblique low-pixel strokes and lighting remain risks.")
    hardware, hardwarePath = readRecord(index, "trials", args.hardware)
    if args.calibration:
        calibrationRecords = [readRecord(index, "calibration", path) for path in args.calibration]
    elif index.get("records", {}).get("calibrationTrials"):
        calibrationRecords = [readRecord(index, "calibration", None, record)
                              for record in index["records"]["calibrationTrials"]]
    else:
        calibrationRecords = [readRecord(index, "calibration", None)]
    calibrationRecords = [(value, path) for value, path in calibrationRecords if value is not None]
    if len({digest(path) for value, path in calibrationRecords}) != len(calibrationRecords):
        raise ValueError("duplicate calibration recording cannot count as another trial")
    accuracy, latency, convergence = measurements(hardware, [value for value, path in calibrationRecords])
    buildId = index["source"]["buildId"]
    try:
        indexLabel = args.index.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        indexLabel = args.index.name
    palette = {"ink": colors.HexColor("#173049"), "blue": colors.HexColor("#0057B8"),
               "light": colors.HexColor("#EDF3F8"), "rule": colors.HexColor("#B9CAD9")}
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12,
                          textColor=palette["ink"], spaceAfter=5, alignment=TA_LEFT)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.1, leading=10.7, spaceAfter=0)
    header = ParagraphStyle("header", parent=cell, textColor=colors.white, fontName="Helvetica-Bold")
    heading = ParagraphStyle("heading", parent=body, fontName="Helvetica-Bold", fontSize=10.5,
                             leading=14, textColor=palette["blue"], spaceBefore=7, spaceAfter=4)
    title = ParagraphStyle("title", parent=heading, fontSize=20, leading=23, spaceBefore=0, spaceAfter=5)
    small = ParagraphStyle("small", parent=body, fontSize=7.8, leading=10)
    para = lambda value, style=body: Paragraph(value, style)
    story = [para("ECHO-7 | Member B datasheet", title),
             para("MTRX3700 Major Project - B contribution for team integration", heading),
             para("Owner SID <b>540207680</b> | Frozen targets: 3 November 2026 | Stationary camera / JTAG input"),
             para("B provides perception, red/blue floor calibration and target reports. Movement and complete-robot acceptance belong to Member C/the team. Microphone input is deferred.")]
    story += [para("Fixed conditions and scope", heading),
              para(scene + "native320 x240 RGB565; fixed oblique camera, orientation profile0. Keep focus, sheet, lighting and switch mode fixed per trial. Lux/colour temperature/pose are not instrumented; no general operating range is claimed.")]
    rows = [[para(text, header) for text in ("Quantity / unit", "Threshold and goal", "Prediction before evaluation", "Measured current evidence")],
            [para("<b>Correct typed markers</b><br/>Correct accepted IDs / " + population + " per sampled frame. Count wrong IDs, rejects, invalid frames and drops.", cell),
             para("<b>Threshold:</b> at least 95% correct; zero wrong IDs; all six bays observed in every trial.<br/><b>Goal:</b> 100% on fixed sheet.", cell),
             para(prediction, cell), para(escape(accuracy), cell)],
            [para("<b>Capture-to-result latency</b><br/>Unsigned board completionUs - captureStartUs, including acquisition; maximum of all observed completions.", cell),
             para("<b>Threshold:</b> at most 150 ms.<br/><b>Goal:</b> at most 100 ms.", cell),
             para("One camera period plus sequential candidate reads. A reader-only 4.34 ms value is not a system prediction.", cell), para(escape(latency), cell)],
            [para("<b>Calibration convergence / retention</b><br/>Confirmed red-1 attempt to successful SOP profile commit. Count attempts, failures and changes.", cell),
             para("<b>Threshold:</b> commit within 2 s with stable valid samples; at most one initial success; rejected samples retain profile.<br/><b>Goal:</b> within 1 s and 100% typed signs after commit.", cell),
             para("Eight valid frames plus recognition/commit overhead. Clipping, contamination or movement should reject the attempt.", cell), para(escape(convergence), cell)]]
    availableWidth = A4[0] - 28 * mm
    table = Table(rows, colWidths=[availableWidth * ratio for ratio in (.25, .25, .23, .27)])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), palette["blue"]),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, palette["light"]]),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("BOX", (0, 0), (-1, -1), .5, palette["rule"]),
                               ("INNERGRID", (0, 0), (-1, -1), .3, palette["rule"]),
                               ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                               ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [table, para("Three-trial rule and measurement boundary", heading),
              para("Run three trials of 30 distinct current-request frames: five per bay in order 1-6. Retain all observed failures and old-request transitions; never select only eventual locks. Score IDs against photographed printed-digit regions, never feed those answers to RTL. Report each trial separately; no best-trial selection."),
              para("Record source/device, mode/configuration, frame/time range, candidates, overflow/drop/discard counts, typed IDs and target tag. A held snapshot is not a new frame. JTAG observations are sparse, not proof that intervening frames passed. Use board time, not image-transfer duration. Calibration's observed IDLE-to-new-version bound is conservative; absent start means NOT_MEASURED.")]
    story += [para("Physical comparison and evidence limits", heading),
              para(f"{comparisonSwitch}=0: measured-quad perspective sampling; {comparisonSwitch}=1: axis-aligned bbox on identical source pixels. Keep anchor/stroke/rejection and tracking; modes bind at SOP and change configuration. Compare matched three-trial conditions. If both modes pass, claim no demonstrated improvement." + (" SW9 is separate pure-camera mode; keep it down for measurement. SELECT1/2 must be ambiguous in this duplicate scene." if sharedPool else "")),
              para("R5 numerical targets are B design choices, not course grading cut-offs. R6 simulation and R7 recorded-input agreement are separate from CAMERA_HW and physical VGA/SW9 checks. This page is a B contribution, not the group's completed datasheet or a whole-robot performance claim.", small),
              Spacer(1, 3),
              para(f"Evidence snapshot: source <b>0x{buildId:08x}</b>; index SHA256 {digest(args.index)[:16]}...<br/>{escape(indexLabel)} | Full frozen protocol: README.md; historical outcomes: VERSION_README.md<br/>Brief: p3 R5-R9; p4 target/bypass rules. Human review and team integration remain required.", small)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(args.out), pagesize=A4, leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=12*mm, bottomMargin=12*mm,
                            title="ECHO-7 Member B contribution datasheet", author="Member B SID 540207680")
    doc.build(story)
    pages = len(PdfReader(args.out).pages)
    if pages != 1:
        raise RuntimeError(f"one-page datasheet overflowed to {pages} pages")
    generation = {"schema": "member-b-datasheet-generation-v1", "status": "PASS",
                      "level": "DOCUMENT_GENERATION_NOT_HARDWARE_VALIDATION",
                      "path": str(args.out), "pages": pages, "sha256": digest(args.out),
                      "sourceSha256": sourceSha256, "buildId": buildId,
                      "indexSha256": digest(args.index),
                      "hardwareSha256": digest(hardwarePath) if hardwarePath else None,
                      "calibrationSha256": [digest(path) for value, path in calibrationRecords]}
    # The exporter verifies this exact PDF and source identity. It never picks
    # up an unrequested old PDF merely because a default output file exists.
    args.out.with_suffix(args.out.suffix + ".json").write_text(json.dumps(generation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(generation, indent=2))


if __name__ == "__main__":
    main()
