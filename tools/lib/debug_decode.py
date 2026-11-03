"""Decode versioned EBP1 status and separate QRP3 query packets.

Words are low-word-first for packed structures. A frozen status is a coherent
board observation; a GRAB image requires the additional native frame binding.
"""
from contract_model import FIELD_LAYOUTS, unpackPayload, freshTime


def schemaLayout(debugSchema):
    """Private packet geometry and its exact public contract version.

    Schemas 1..5 retain eight candidates per colour; schema6 retains16 per
    colour. Schema7 has16 total shared slots. Four-bit active labels remain
    separate from these completed stores. Schema8 retains that geometry and
    introduces the public-v3 typed request/report fields.
    """
    if debugSchema not in (1, 2, 3, 4, 5, 6, 7, 8):
        raise ValueError("unsupported EBP1 schema")
    capacity = 16 if debugSchema >= 6 else 8
    markerCount = capacity if debugSchema >= 7 else 2 * capacity
    return {"wordCount": 24 + 4 * markerCount + 8, "tailBase": 24 + 4 * markerCount,
            "capacity": capacity, "markerCount": markerCount, "sharedPool": debugSchema >= 7,
            "poolLayout": "SHARED_TOTAL" if debugSchema >= 7 else "SPLIT_PER_COLOUR",
            "countBits": 5 if debugSchema >= 6 else 4,
            "contractVersion": 3 if debugSchema == 8 else 2}


def requireAlgorithmMode(decoded):
    """Reject paused/requested/display-raw states as algorithm trial evidence.

    The three bits have different timing boundaries and may legitimately differ
    during a switch transition. They are not a corruption test; any asserted bit
    means that a stable normal/perspective-only trial is not currently valid.
    Older schemas have no raw switch and remain compatible through False defaults.
    """
    if any(decoded.get(field, False) for field in
           ("rawCameraMode", "rawModeRequested", "rawDisplayActive")):
        raise RuntimeError("RAW_CAMERA_MODE: algorithm trials require SW9 down and both capture/display returned to processing mode")


def decodeWords(words):
    if len(words) < 2 or any(type(w) is not int or not 0 <= w <= 0xffffffff for w in words):
        raise ValueError("EBP1 requires unsigned 32-bit words")
    debugSchema = words[1] >> 16
    layout = schemaLayout(debugSchema)
    if len(words) != layout["wordCount"]:
        raise ValueError(f"EBP1 schema{debugSchema} requires exactly {layout['wordCount']} unsigned 32-bit words")
    contractVersion = layout["contractVersion"]
    if words[0] != 0x45425031 or words[1] & 0xffff != contractVersion:
        raise ValueError("unsupported EBP1 magic/schema/contract")
    tail, capacity, countBits = layout["tailBase"], layout["capacity"], layout["countBits"]
    countMask = (1 << countBits) - 1
    redCount, blueCount = words[9] & countMask, (words[9] >> countBits) & countMask
    if words[9] >> (2 * countBits) or redCount > capacity or blueCount > capacity:
        raise ValueError("candidate counts exceed schema capacity or contain reserved bits")
    if layout["sharedPool"] and redCount + blueCount > capacity:
        raise ValueError("candidate counts exceed shared completed pool capacity")

    def payload(name, first, count):
        value = sum(words[first + i] << (32 * i) for i in range(count))
        return unpackPayload(name, value, contractVersion=contractVersion)

    status = payload("status", 10, 3)
    report = payload("targetReport", 13, 5)
    event = payload("userEvent", 18, 4)
    request = unpackPayload("targetRequest", words[tail], contractVersion=contractVersion)
    markers = []
    for index in range(layout["markerCount"]):
        at = 24 + 4 * index
        descriptor, xs, ys, reserved = words[at:at+4]
        marker = {"index": index, "accepted": bool(descriptor >> 31), "isBlue": bool((descriptor >> 30) & 1),
                  "orientation": (descriptor >> 28) & 3, "digit": (descriptor >> 24) & 15,
                  "quality": (descriptor >> 16) & 255, "reason": (descriptor >> 8) & 255,
                  "segments": descriptor & 127, "xMin": (xs >> 16) & 511, "xMax": xs & 511,
                  "yMin": (ys >> 16) & 255, "yMax": ys & 255}
        if descriptor & 128 or reserved or xs & 0xfe00fe00 or ys & 0xff00ff00:
            raise ValueError(f"marker{index} has nonzero reserved bits")
        if marker["accepted"]:
            validDigits = range(1, 7) if marker["isBlue"] else (1, 2)
            if marker["digit"] not in validDigits:
                raise ValueError(f"marker{index} claims an unsupported digit/type")
            if not (0 <= marker["xMin"] <= marker["xMax"] < 320 and 0 <= marker["yMin"] <= marker["yMax"] < 240):
                raise ValueError(f"marker{index} bbox is outside native pixels")
        markers.append(marker)
    if layout["sharedPool"]:
        present = markers[:redCount+blueCount]
        if sum(not marker["isBlue"] for marker in present) != redCount:
            raise ValueError("shared candidate slot colours differ from red/blue counts")
        if any(marker["accepted"] for marker in markers[redCount+blueCount:]):
            raise ValueError("accepted marker lies outside dense shared candidate slots")
    if not report["observed"] and any(report[k] for k in ("centreU", "centreV", "boxWidth", "boxHeight", "quality", "locked")):
        raise ValueError("unobserved target report contains a public measurement")
    diagnosticReserved = words[tail+6] >> 4 if debugSchema == 1 else words[tail+6] & 0x0000fff0
    # word7: RGB floors[15:0], reserved[17:16], orientation[19:18],
    # perspective[20] since schema3, frame-bound raw[21], synchronised request[22]
    # and display-packet mode[23] since schema5. Future bits must not be ignored.
    allowedProfileBits = 0x000cffff | (0x00100000 if debugSchema >= 3 else 0)
    if debugSchema >= 5:
        allowedProfileBits |= 0x00e00000
    if (words[3] >> 16 or words[6] >> 16 or words[tail+3] >> 1
            or (words[tail+5] >> 24 != 1 if debugSchema >= 7 else words[tail+5] >> (24 if debugSchema >= 4 else 8)) or diagnosticReserved
            or words[7] & ~allowedProfileBits
            or words[tail+2] >> (17 if debugSchema >= 8 else 8 if debugSchema >= 6 else 7 if debugSchema >= 5 else 3 if debugSchema >= 4 else 2)):
        raise ValueError("EBP1 reserved fields are nonzero")
    rawCameraMode = bool(words[7] & (1 << 21)) if debugSchema >= 5 else False
    calibrationReferenceValid = bool(words[tail+2] & 8) if debugSchema >= 5 else False
    calibrationReferenceIndex = (words[tail+2] >> 4) & (capacity-1) if debugSchema >= 5 else 0
    calibrationReferenceMarkerIndex = calibrationReferenceIndex if layout["sharedPool"] else capacity+calibrationReferenceIndex
    if debugSchema >= 8:
        from contract_model import markerEnabled
        if not calibrationReferenceValid and ((words[tail+2] >> 8) & 255):
            raise ValueError("invalid calibration reference carries stale quality")
        if report["observed"] and not markerEnabled(report["markerType"], report["digit"]):
            raise ValueError("observed typed target report has invalid identity")
    if rawCameraMode and (words[tail+3] or words[9] or any(m["accepted"] for m in markers)
                          or calibrationReferenceValid):
        raise ValueError("raw-camera completed frame claims good recognition, candidates, accepted markers or calibration reference")
    if calibrationReferenceValid:
        reference = markers[calibrationReferenceMarkerIndex]
        referenceInRange = calibrationReferenceIndex < redCount+blueCount if layout["sharedPool"] else calibrationReferenceIndex < blueCount
        if (not words[tail+3] or not referenceInRange
                or reference["accepted"] or not reference["isBlue"]
                or not 0 <= reference["xMin"] <= reference["xMax"] < 320
                or not 0 <= reference["yMin"] <= reference["yMax"] < 240):
            raise ValueError("calibration reference is not a good-frame, in-range rejected blue candidate")
    # A public valid/ready report may be stalled from an earlier frame. Its
    # identity/observed values are not required to match raw completed metadata
    # here; GRAB independently checks its stricter captured-frame binding.
    # Schema 1 used a 16-bit reader ID and always used ratio segmentation.
    # Schema 2 explicitly identifies colour and reader algorithms in one byte
    # each; old captures must never be silently reinterpreted as HSV inputs.
    readerAlgorithm = words[tail+7] >> 16 if debugSchema == 1 else (words[tail+7] >> 16) & 255
    colourAlgorithm = 0 if debugSchema == 1 else words[tail+7] >> 24
    if readerAlgorithm not in ((0, 1) if debugSchema == 1 else range(10) if debugSchema == 8 else range(6) if debugSchema >= 6 else range(5)):
        raise ValueError("unsupported EBP1 reader algorithm")
    if colourAlgorithm not in (0, 1, 2, 3):
        raise ValueError("unsupported EBP1 colour algorithm")
    # Colour3 changes horizontal run support from three pixels to two while
    # retaining colour2's HSV gate and the subsequent causal cleanup. It was
    # introduced for shared-pool schema7/reader5. Reader6 adds ownership of
    # anchor components by the candidate bbox and was first published in
    # schema8 with colour3. Keep historical reader5/colour2 and reader5/colour3
    # explicit: neither may acquire reader6's component filter during replay.
    if colourAlgorithm == 3 and (debugSchema not in (7, 8) or readerAlgorithm not in (5, 6, 7, 8, 9)):
        raise ValueError("colour algorithm 3 requires schema7/8 and reader algorithm 5, 6, 7, 8 or 9")
    if readerAlgorithm == 3 and colourAlgorithm != 1:
        raise ValueError("reader algorithm 3 requires HSV colour algorithm 1")
    if readerAlgorithm == 4 and colourAlgorithm != 2:
        raise ValueError("reader algorithm 4 requires HSV colour algorithm 2")
    if readerAlgorithm == 5 and colourAlgorithm not in (2, 3):
        raise ValueError("reader algorithm 5 requires HSV colour algorithm 2 or 3")
    if readerAlgorithm in (6, 7, 8, 9) and colourAlgorithm != 3:
        raise ValueError(f"reader algorithm {readerAlgorithm} requires HSV colour algorithm 3")
    whiteMinimum, whiteSpread = (words[tail+7] >> 8) & 255, words[tail+7] & 255
    if readerAlgorithm in (2, 3) and (whiteMinimum != 96 or whiteSpread != 64):
        raise ValueError(f"reader algorithm {readerAlgorithm} requires weighted-luma floor96 and spread64")
    if readerAlgorithm in (4, 5, 6, 7, 8, 9) and (whiteMinimum != 84 or whiteSpread != 64):
        raise ValueError(f"reader algorithm {readerAlgorithm} requires weighted-luma floor84 and spread64")
    activeCapacity = (words[tail+5] >> 8) & 255 if debugSchema >= 4 else 8
    outputCapacity = (words[tail+5] >> 16) & 255 if debugSchema >= 4 else 8
    if not 1 <= activeCapacity <= 15 or outputCapacity != capacity:
        raise ValueError("unsupported active/output candidate capacity")
    captureAge = (words[2] - words[4]) & 0xffffffff
    return {"schema": "EBP1", "debugSchemaVersion": debugSchema, "statusWordCount": layout["wordCount"],
            "contractVersion": contractVersion, "timeUs": words[2], "frameId": words[3],
            "captureStartUs": words[4], "completionUs": words[5], "configVersion": words[6],
            "orientationProfile": (words[7] >> 18) & 3, "redMinimum": (words[7] >> 8) & 255,
            "bypassPerspective": bool(words[7] & (1 << 20)) if debugSchema >= 3 else False,
            "rawCameraMode": rawCameraMode,
            "rawModeRequested": bool(words[7] & (1 << 22)) if debugSchema >= 5 else False,
            "rawDisplayActive": bool(words[7] & (1 << 23)) if debugSchema >= 5 else False,
            "calibrationReferenceValid": calibrationReferenceValid,
            "calibrationReferenceIndex": calibrationReferenceIndex,
            "calibrationReferenceMarkerIndex": calibrationReferenceMarkerIndex,
            **({"calibrationReferenceQuality": (words[tail+2] >> 8) & 255,
                "queryBusy": bool(words[tail+2] & (1 << 16))} if debugSchema >= 8 else {}),
            **({"calibrationReferenceBlueIndex": calibrationReferenceIndex} if not layout["sharedPool"] else {}),
            "blueMinimum": words[7] & 255, "bufferDropCount": words[8],
            "redCandidateCount": redCount, "blueCandidateCount": blueCount,
            "status": status, "targetReport": report, "userEvent": event, "activeRequest": request,
            "redSamples": words[22], "blueSamples": words[23], "markers": markers,
            "calibrationSampleFrames": words[tail+1] & 15 if debugSchema >= 4 else words[tail+1],
            "calibrationLastSample": ({"frameId": words[tail+1] >> 16,
                "checks": {name: bool(words[tail+1] & (1 << (8+bit))) for bit, name in enumerate(
                    ("samplerGood", "frameGood", "red1Paired", "geometryStable", "windowStable"))}}
                if debugSchema >= 4 else None),
            "activeCandidateCapacity": activeCapacity, "outputCandidateCapacity": outputCapacity,
            "poolLayout": layout["poolLayout"], "sharedCandidatePool": layout["sharedPool"],
            "candidateStorageSlots": layout["markerCount"],
            "userEventHeld": bool(words[tail+2] & 4) if debugSchema >= 4 else False, "reportValid": bool(words[tail+2] & 2),
            "frameGood": bool(words[tail+3]), "allocationPeakRed": words[tail+5] & 15,
            "allocationPeakBlue": (words[tail+5] >> 4) & 15,
            "candidateOverflow": bool(words[tail+6] & 4), "candidateError": bool(words[tail+6] & 2),
            "candidateOverrun": bool(words[tail+6] & 1), "transportFaultSticky": bool(words[tail+6] & 8),
            "completionDiscardCount": (words[tail+6] >> 16) if debugSchema >= 2 else 0,
            "buildId": words[tail+4], "readerAlgorithm": readerAlgorithm,
            "colourAlgorithm": colourAlgorithm,
            "whiteMinimum": whiteMinimum, "whiteMaxSpread": whiteSpread,
            "whiteMode": {2: "QUARTER_WEIGHTED_LUMA", 3: "ROUNDED_STROKES_STRICT_ANCHOR", 4: "UNSATURATED_STROKES_STRICT_ANCHOR", 5: "UNSATURATED_STROKES_STRICT_ANCHOR", 6: "UNSATURATED_STROKES_STRICT_ANCHOR", 7: "UNSATURATED_STROKES_STRICT_ANCHOR", 8: "UNSATURATED_STROKES_STRICT_ANCHOR", 9: "UNSATURATED_STROKES_STRICT_ANCHOR"}.get(readerAlgorithm, "MIN_RGB_CHANNEL"),
            "readerOrientationMode": "PER_MARKER_ANCHOR" if readerAlgorithm in (5, 6, 7, 8, 9) else "CONFIGURED_QUARTER_TURN",
            "whiteThresholdExpression": ("R+2*G+B >= 384 OR (R+2*G+B+2 >= 4*whiteMinimum AND 2*(max(R,G,B)-min(R,G,B)) < max(R,G,B))" if readerAlgorithm in (4, 5, 6, 7, 8, 9) else
                "R+2*G+B+2 >= 4*whiteMinimum" if readerAlgorithm == 3 else
                "R+2*G+B >= 4*whiteMinimum" if readerAlgorithm == 2 else "min(R,G,B) >= whiteMinimum"),
            **({"whiteAnchorThresholdExpression": "R+2*G+B >= 4*whiteMinimum",
                "candidateSizePruning": True} if readerAlgorithm == 3 else {}),
            **({"whiteAnchorThresholdExpression": "R+2*G+B >= 384", "whiteAnchorMinimum": 96,
                "candidateSizePruning": True} if readerAlgorithm in (4, 5, 6, 7, 8, 9) else {}),
            "userEventValid": bool(words[tail+2] & 1), "captureAgeAtSnapshotUs": captureAge,
            "processingLatencyUs": (words[5] - words[4]) & 0xffffffff,
            "freshAtSnapshot": freshTime(words[2], words[4], 150000)}


def decodeQueryWords(words, expectedBuildId=None):
    """Decode one independently framed QRP3 record, never an EBP1 snapshot.

    The five payload words are low-word-first. An empty/error transaction has
    one explicit terminal record; an accepted query may contain up to sixteen
    actual observations, including duplicate identities at different positions.
    Cross-record tag/frame/config/count and ordering are checked by the stream
    parser, rather than treating each structurally valid packet as a full list.
    """
    from contract_model import markerEnabled
    if len(words) != 8 or any(type(word) is not int or not 0 <= word <= 0xffffffff for word in words):
        raise ValueError("QRP3 requires exactly eight unsigned 32-bit words")
    if words[0] != 0x51525033 or words[7] != 0x00000308:
        raise ValueError("unsupported QRP3 magic/schema/contract")
    if expectedBuildId is not None and words[6] != expectedBuildId:
        raise ValueError("QRP3 buildId differs from expected board identity")
    payload = sum(words[index+1] << (32*index) for index in range(5))
    result = unpackPayload("queryResult", payload, contractVersion=3)
    count, index, reason = result["count"], result["index"], result["reason"]
    if count > 16 or reason == 7:
        raise ValueError("QRP3 count/reason is outside the public contract")
    geometry = ("centreU", "centreV", "boxWidth", "boxHeight", "quality")
    if count == 0:
        if (index != 0 or result["last"] != 1 or reason not in range(2, 7)
                or result["markerType"] != 0 or result["digit"] != 15
                or any(result[field] for field in geometry)):
            raise ValueError("QRP3 empty/error result must have terminal NONE/F and zero measurement")
    else:
        if (index >= count or bool(result["last"]) != (index == count-1)
                or reason not in (0, 1) or (reason == 1 and count < 2)
                or not markerEnabled(result["markerType"], result["digit"])):
            raise ValueError("QRP3 item identity/count/index/last/reason is inconsistent")
        if (result["centreU"] >= 240 or result["centreV"] >= 320
                or not 1 <= result["boxWidth"] <= 240 or not 1 <= result["boxHeight"] <= 320):
            raise ValueError("QRP3 geometry is outside public 240x320 coordinates")
    return {"schema": "QRP3", "debugSchemaVersion": 8, "contractVersion": 3,
            "buildId": words[6], **result}


def checkGrabSchema(words):
    if words and words[0] in (0x45504131, 0x45504132):
        raise ValueError("LEGACY_CAPTURE: Part A EPA1/EPA2 snapshots are historical evidence only; program the current PartBDebug build before live capture")
    if not words or words[0] != 0x45425031:
        raise ValueError("unsupported capture result schema; expected Member B EBP1")


def decodeGrabWords(words, expectedBuildId):
    checkGrabSchema(words)
    if len(words) < 2:
        raise ValueError("B GRAB requires a schema header")
    wordCount = schemaLayout(words[1] >> 16)["wordCount"]
    if len(words) != wordCount + 2:
        raise ValueError(f"B GRAB requires {wordCount+2} words including native capture binding and buildId")
    decoded = decodeWords(words[:wordCount])
    capturedFrame = words[wordCount]
    if capturedFrame > 65535 or decoded["frameId"] != capturedFrame or decoded["targetReport"]["frameId"] != capturedFrame:
        raise ValueError("FRAME_MISMATCH: pixels, recognition and target report do not describe the same native frame")
    if words[wordCount+1] != expectedBuildId or decoded["buildId"] != expectedBuildId:
        raise ValueError("B GRAB buildId differs from the successful source/SOF manifest")
    decoded["buildId"] = words[wordCount+1]
    decoded["sameFrameVerified"] = True
    return decoded


def compareMarkerPixels(imagePath, decoded, output):
    """Independent white-pixel classification of the reported colour bboxes.

    A hardware bbox is a legitimate search ROI; the label still comes entirely
    from that ROI's captured white pixels. No paper slot or manifest ID is read.
    This check proves glyph agreement, not a model of streaming label capacity.
    """
    if decoded.get("rawCameraMode", False):
        raise ValueError("NOT_APPLICABLE_RAW_CAMERA_MODE: raw camera frames have no recognition result to compare")
    import json
    from pathlib import Path
    from PIL import Image
    import numpy as np
    from vision_reference import classify
    from projective_reference import classifyProjective, whiteProfileFor, whitePixelsFor

    image = Image.open(imagePath).convert("RGB")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    comparisons = []
    redCount, blueCount = decoded["redCandidateCount"], decoded["blueCandidateCount"]
    capacity = decoded.get("outputCandidateCapacity", 8)
    if redCount > capacity or blueCount > capacity:
        raise ValueError("candidate counts exceed the implemented array bounds")
    indices = (list(range(redCount+blueCount)) if decoded.get("sharedCandidatePool", False) else
               list(range(redCount)) + list(range(capacity, capacity + blueCount)))
    for index in indices:
        measured = decoded["markers"][index]
        bbox = [measured[k] for k in ("xMin", "yMin", "xMax", "yMax")]
        if not (0 <= bbox[0] <= bbox[2] < 320 and 0 <= bbox[1] <= bbox[3] < 240):
            raise ValueError("candidate bbox is not an in-frame colour main area")
        candidate = {"colour": "blue" if measured["isBlue"] else "red", "bbox": bbox}
        if decoded["readerAlgorithm"] in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            expected = classifyProjective(image, candidate, decoded["orientationProfile"],
                decoded["redMinimum"], decoded["blueMinimum"], decoded["whiteMinimum"],
                decoded["whiteMaxSpread"], output / f"marker_{index:02d}_projective",
                colourAlgorithm=decoded["colourAlgorithm"], readerAlgorithm=decoded["readerAlgorithm"],
                bypassPerspective=decoded.get("bypassPerspective",False))
            crop = image.crop((bbox[0], bbox[1], bbox[2]+1, bbox[3]+1))
            profile = whiteProfileFor(decoded["readerAlgorithm"], decoded["whiteMinimum"], decoded["whiteMaxSpread"])
            cropArray = np.asarray(crop, dtype=np.int16)
            mask = Image.fromarray((whitePixelsFor(cropArray, profile)*255).astype(np.uint8))
            if decoded["readerAlgorithm"] in (3, 4, 5, 6, 7, 8, 9):
                strongMask = Image.fromarray((whitePixelsFor(cropArray, profile, anchor=True)*255).astype(np.uint8))
                strongMask.save(output / f"marker_{index:02d}_strong_white.png")
        else:
            expected, crop, mask = classify(image, candidate, decoded["orientationProfile"], decoded["whiteMinimum"])
        crop.save(output / f"marker_{index:02d}_rgb.png")
        mask.save(output / f"marker_{index:02d}_white.png")
        differences = []
        if bool(measured["accepted"]) != bool(expected["accepted"]):
            differences.append("accepted")
        if measured["accepted"] and expected["accepted"]:
            differences.extend(field for field in ("digit", "quality") if measured[field] != expected[field])
            if decoded["readerAlgorithm"] in (5, 6, 7, 8, 9) and measured["orientation"] != expected["orientationProfile"]:
                differences.append("orientation")
        if decoded["readerAlgorithm"] in (1, 2, 3, 4, 5, 6, 7, 8, 9):
            if measured["reason"] != expected["reasonCode"]:
                differences.append("reason")
            if expected["windowScores"]:
                expectedSegments = sum(1 << bit for bit, name in enumerate("ABCDEFG") if name in expected["segments"])
                if measured["segments"] != expectedSegments:
                    differences.append("segments")
        comparisons.append({"index": index, "match": not differences, "differences": differences,
                            "measured": measured, "pixelReference": expected})
    invalidFrame = not decoded["frameGood"] or any(decoded.get(key, False) for key in
        ("candidateOverflow", "candidateError", "candidateOverrun"))
    result = {"schema": "echo7-captured-glyph-check-v1", "level": "CAMERA_HW_WITH_MODEL_COMPARISON",
              "source": "RECORDED_CAMERA_SAME_FRAME", "frameId": decoded["frameId"],
              "readerAlgorithm": decoded["readerAlgorithm"], "comparedCandidateCount": len(comparisons),
              "whiteMode": decoded["whiteMode"], "whiteMinimum": decoded["whiteMinimum"],
              "whiteMaxSpread": decoded["whiteMaxSpread"],
              "debugSchemaVersion": decoded["debugSchemaVersion"], "colourAlgorithm": decoded["colourAlgorithm"],
              "status": "PASS" if comparisons and not invalidFrame and all(c["match"] for c in comparisons) else "FAIL",
              "reason": "INVALID_CAPTURED_FRAME" if invalidFrame else "NO_CANDIDATES_TO_COMPARE" if not comparisons else "PIXEL_COMPARISON",
              "comparisons": comparisons}
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
