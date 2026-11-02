"""Decode the exact EBP1/contract-v2 words emitted by perceptionCore.

Words are low-word-first for packed structures. A frozen status is a coherent
board observation; a GRAB image requires the additional native frame binding.
"""
from contract_model import FIELD_LAYOUTS, unpackPayload, freshTime


def decodeWords(words):
    if len(words) != 96 or any(not isinstance(w, int) or not 0 <= w <= 0xffffffff for w in words):
        raise ValueError("EBP1 requires exactly 96 unsigned 32-bit words")
    debugSchema = words[1] >> 16
    if words[0] != 0x45425031 or debugSchema not in (1, 2) or words[1] & 0xffff != 2:
        raise ValueError("unsupported EBP1 magic/schema/contract")

    def payload(name, first, count):
        value = sum(words[first + i] << (32 * i) for i in range(count))
        return unpackPayload(name, value)

    status = payload("status", 10, 3)
    report = payload("targetReport", 13, 5)
    event = payload("userEvent", 18, 4)
    request = unpackPayload("targetRequest", words[88])
    markers = []
    for index in range(16):
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
    if not report["observed"] and any(report[k] for k in ("centreU", "centreV", "boxWidth", "boxHeight", "quality", "locked")):
        raise ValueError("unobserved target report contains a public measurement")
    diagnosticReserved = words[94] >> 4 if debugSchema == 1 else words[94] & 0x0000fff0
    if (words[3] >> 16 or words[6] >> 16 or words[91] >> 1
            or words[93] >> 8 or diagnosticReserved):
        raise ValueError("EBP1 reserved fields are nonzero")
    # Schema 1 used a 16-bit reader ID and always used ratio segmentation.
    # Schema 2 explicitly identifies colour and reader algorithms in one byte
    # each; old captures must never be silently reinterpreted as HSV inputs.
    readerAlgorithm = words[95] >> 16 if debugSchema == 1 else (words[95] >> 16) & 255
    colourAlgorithm = 0 if debugSchema == 1 else words[95] >> 24
    if readerAlgorithm not in ((0, 1) if debugSchema == 1 else (0, 1, 2)):
        raise ValueError("unsupported EBP1 reader algorithm")
    if colourAlgorithm not in (0, 1):
        raise ValueError("unsupported EBP1 colour algorithm")
    whiteMinimum, whiteSpread = (words[95] >> 8) & 255, words[95] & 255
    if readerAlgorithm == 2 and (whiteMinimum != 96 or whiteSpread != 64):
        raise ValueError("reader algorithm 2 requires weighted-luma floor96 and spread64")
    captureAge = (words[2] - words[4]) & 0xffffffff
    return {"schema": "EBP1", "debugSchemaVersion": debugSchema, "contractVersion": 2, "timeUs": words[2], "frameId": words[3],
            "captureStartUs": words[4], "completionUs": words[5], "configVersion": words[6],
            "orientationProfile": (words[7] >> 18) & 3, "redMinimum": (words[7] >> 8) & 255,
            "blueMinimum": words[7] & 255, "bufferDropCount": words[8],
            "redCandidateCount": words[9] & 15, "blueCandidateCount": (words[9] >> 4) & 15,
            "status": status, "targetReport": report, "userEvent": event, "activeRequest": request,
            "redSamples": words[22], "blueSamples": words[23], "markers": markers,
            "calibrationSampleFrames": words[89], "reportValid": bool(words[90] & 2),
            "frameGood": bool(words[91]), "allocationPeakRed": words[93] & 15,
            "allocationPeakBlue": (words[93] >> 4) & 15,
            "candidateOverflow": bool(words[94] & 4), "candidateError": bool(words[94] & 2),
            "candidateOverrun": bool(words[94] & 1), "transportFaultSticky": bool(words[94] & 8),
            "completionDiscardCount": (words[94] >> 16) if debugSchema == 2 else 0,
            "buildId": words[92], "readerAlgorithm": readerAlgorithm,
            "colourAlgorithm": colourAlgorithm,
            "whiteMinimum": whiteMinimum, "whiteMaxSpread": whiteSpread,
            "whiteMode": "QUARTER_WEIGHTED_LUMA" if readerAlgorithm == 2 else "MIN_RGB_CHANNEL",
            "whiteThresholdExpression": "R+2*G+B >= 4*whiteMinimum" if readerAlgorithm == 2 else "min(R,G,B) >= whiteMinimum",
            "userEventValid": bool(words[90] & 1), "captureAgeAtSnapshotUs": captureAge,
            "processingLatencyUs": (words[5] - words[4]) & 0xffffffff,
            "freshAtSnapshot": freshTime(words[2], words[4], 150000)}


def checkGrabSchema(words):
    if words and words[0] in (0x45504131, 0x45504132):
        raise ValueError("LEGACY_CAPTURE: Part A EPA1/EPA2 snapshots are historical evidence only; program the current PartBDebug build before live capture")
    if not words or words[0] != 0x45425031:
        raise ValueError("unsupported capture result schema; expected Member B EBP1")


def decodeGrabWords(words, expectedBuildId):
    checkGrabSchema(words)
    if len(words) != 98:
        raise ValueError("B GRAB requires 98 words including native capture binding and buildId")
    decoded = decodeWords(words[:96])
    capturedFrame = words[96]
    if capturedFrame > 65535 or decoded["frameId"] != capturedFrame or decoded["targetReport"]["frameId"] != capturedFrame:
        raise ValueError("FRAME_MISMATCH: pixels, recognition and target report do not describe the same native frame")
    if words[97] != expectedBuildId or decoded["buildId"] != expectedBuildId:
        raise ValueError("B GRAB buildId differs from the successful source/SOF manifest")
    decoded["buildId"] = words[97]
    decoded["sameFrameVerified"] = True
    return decoded


def compareMarkerPixels(imagePath, decoded, output):
    """Independent white-pixel classification of the reported colour bboxes.

    A hardware bbox is a legitimate search ROI; the label still comes entirely
    from that ROI's captured white pixels. No paper slot or manifest ID is read.
    This check proves glyph agreement, not a model of streaming label capacity.
    """
    import json
    from pathlib import Path
    from PIL import Image
    from vision_reference import classify, pixelsOf
    from projective_reference import classifyProjective

    image = Image.open(imagePath).convert("RGB")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    comparisons = []
    redCount, blueCount = decoded["redCandidateCount"], decoded["blueCandidateCount"]
    if redCount > 8 or blueCount > 8:
        raise ValueError("CAP8 candidate counts exceed the implemented array bounds")
    for index in list(range(redCount)) + list(range(8, 8 + blueCount)):
        measured = decoded["markers"][index]
        bbox = [measured[k] for k in ("xMin", "yMin", "xMax", "yMax")]
        if not (0 <= bbox[0] <= bbox[2] < 320 and 0 <= bbox[1] <= bbox[3] < 240):
            raise ValueError("candidate bbox is not an in-frame colour main area")
        candidate = {"colour": "blue" if index >= 8 else "red", "bbox": bbox}
        if decoded["readerAlgorithm"] in (1, 2):
            expected = classifyProjective(image, candidate, decoded["orientationProfile"],
                decoded["redMinimum"], decoded["blueMinimum"], decoded["whiteMinimum"],
                decoded["whiteMaxSpread"], output / f"marker_{index:02d}_projective",
                colourAlgorithm=decoded["colourAlgorithm"], readerAlgorithm=decoded["readerAlgorithm"])
            crop = image.crop((bbox[0], bbox[1], bbox[2]+1, bbox[3]+1))
            mask = Image.new("L", crop.size)
            mask.putdata([255 if ((pixel[0]+2*pixel[1]+pixel[2] >= 4*decoded["whiteMinimum"])
                                  if decoded["readerAlgorithm"] == 2 else (min(pixel) >= decoded["whiteMinimum"]))
                          and max(pixel)-min(pixel) <= decoded["whiteMaxSpread"] else 0
                          for pixel in pixelsOf(crop)])
        else:
            expected, crop, mask = classify(image, candidate, decoded["orientationProfile"], decoded["whiteMinimum"])
        crop.save(output / f"marker_{index:02d}_rgb.png")
        mask.save(output / f"marker_{index:02d}_white.png")
        differences = []
        if bool(measured["accepted"]) != bool(expected["accepted"]):
            differences.append("accepted")
        if measured["accepted"] and expected["accepted"]:
            differences.extend(field for field in ("digit", "quality") if measured[field] != expected[field])
        if decoded["readerAlgorithm"] in (1, 2):
            if measured["reason"] != expected["reasonCode"]:
                differences.append("reason")
            if expected["windowScores"]:
                expectedSegments = sum(1 << bit for bit, name in enumerate("ABCDEFG") if name in expected["segments"])
                if measured["segments"] != expectedSegments:
                    differences.append("segments")
        comparisons.append({"index": index, "match": not differences, "differences": differences,
                            "measured": measured, "pixelReference": expected})
    result = {"schema": "echo7-captured-glyph-check-v1", "level": "CAMERA_HW_WITH_MODEL_COMPARISON",
              "source": "RECORDED_CAMERA_SAME_FRAME", "frameId": decoded["frameId"],
              "readerAlgorithm": decoded["readerAlgorithm"], "comparedCandidateCount": len(comparisons),
              "whiteMode": decoded["whiteMode"], "whiteMinimum": decoded["whiteMinimum"],
              "whiteMaxSpread": decoded["whiteMaxSpread"],
              "debugSchemaVersion": decoded["debugSchemaVersion"], "colourAlgorithm": decoded["colourAlgorithm"],
              "status": "PASS" if all(c["match"] for c in comparisons) else "FAIL", "comparisons": comparisons}
    (output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
