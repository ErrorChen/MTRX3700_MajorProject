#!/usr/bin/env python3
"""Pixel-only Member B reference; no scene manifest or position-to-ID lookup.

The BFS is an independent connected-component oracle, not a cycle-accurate model
of Part A's bounded streaming implementation. All resulting evidence is MODEL.
The seven-segment sampling windows match the proposed RTL integer arithmetic.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


WINDOW_SCALE = 240
# Half-open ranges in the canonical coloured bbox. Pixel centres are tested as
# offset*240+120, without independently cropping/recentring white glyphs.
WINDOWS = {
    "A": (90, 36, 150, 44), "B": (166, 60, 176, 100),
    "C": (166, 140, 176, 180), "D": (90, 196, 150, 204),
    "E": (64, 140, 74, 180), "F": (64, 60, 74, 100),
    "G": (90, 116, 150, 124), "anchor": (18, 17, 30, 27),
    "upperHole": (96, 72, 144, 96), "lowerHole": (96, 144, 144, 168),
}
DIGITS = {"BC": 1, "ABDEG": 2, "ABCDG": 3, "BCFG": 4, "ACDFG": 5, "ACDEFG": 6}


def pixelsOf(image):
    return list(image.get_flattened_data()) if hasattr(image, "get_flattened_data") else list(image.getdata())


def quantise565(image):
    """The hardware widens RGB565 by bit replication, not zero-padding."""
    pixels = []
    for red, green, blue in pixelsOf(image.convert("RGB")):
        red >>= 3
        green >>= 2
        blue >>= 3
        pixels.append(((red << 3) | (red >> 2), (green << 2) | (green >> 4), (blue << 3) | (blue >> 2)))
    result = Image.new("RGB", image.size)
    result.putdata(pixels)
    return result


def colourMask(image, redMin=64, blueMin=32, numerator=3, denominator=2, colourAlgorithm=0):
    """Algorithms 0/1 retain historical ratio/HSV pixel semantics.

    HSV H is in degrees, S >= 1/2. Red wraps through [-24,0], including pure
    red H=0; algorithm 1 blue is [200,250], algorithm 2 is [200,260].
    The latter preserves measured dark blue gutters after RGB565 quantisation.
    All comparisons use signed integer products; calibrated V is independent.
    """
    if colourAlgorithm not in (0,1,2):raise ValueError('colourAlgorithm must be 0, 1 or 2')
    values = []
    for red, green, blue in pixelsOf(image):
        if colourAlgorithm==0:
            redHit = red >= redMin and red*denominator >= green*numerator and red*denominator >= blue*numerator
            blueHit = blue >= blueMin and blue*denominator >= red*numerator and blue*denominator >= green*numerator
        else:
            maximum=max(red,green,blue);delta=maximum-min(red,green,blue)
            saturated=delta>0 and 2*delta>=maximum
            redHit=saturated and red==maximum and red>=redMin and -24*delta<=60*(green-blue)<=0
            blueUpper=10 if colourAlgorithm==1 else 20
            blueHit=saturated and blue==maximum and blue>=blueMin and -40*delta<=60*(red-green)<=blueUpper*delta
        values.append(0 if redHit == blueHit else (1 if redHit else 2))
    return values


def horizontalRunSupport(mask):
    """Preserve an entire same-colour horizontal run iff its length is >=3.

    The mask is a 2-D uint8 array. No row boundary wraps and both ends of a
    qualifying run remain, unlike erosion. Only CCL sees this support filter;
    the raw mask remains the reader's same-frame corner foreground.
    """
    import numpy as np
    triples=(mask[:,:-2]!=0)&(mask[:,:-2]==mask[:,1:-1])&(mask[:,:-2]==mask[:,2:])
    keep=np.zeros_like(mask,dtype=bool)
    keep[:,:-2]|=triples;keep[:,1:-1]|=triples;keep[:,2:]|=triples
    return np.where(keep,mask,0).astype(np.uint8)


def components(mask, width, height, minimumArea=32):
    """Four-connected pixels; a distinct colour never joins another component."""
    visited = bytearray(width*height)
    result = []
    allCounts = {1:0,2:0}
    for start, colour in enumerate(mask):
        if not colour or visited[start]:
            continue
        visited[start] = 1
        queue = deque([start])
        xMin = xMax = start % width
        yMin = yMax = start // width
        area = 0
        while queue:
            index = queue.popleft()
            x, y = index % width, index // width
            area += 1
            xMin, xMax = min(xMin,x), max(xMax,x)
            yMin, yMax = min(yMin,y), max(yMax,y)
            neighbours = []
            if x: neighbours.append(index-1)
            if x+1 < width: neighbours.append(index+1)
            if y: neighbours.append(index-width)
            if y+1 < height: neighbours.append(index+width)
            for neighbour in neighbours:
                if not visited[neighbour] and mask[neighbour] == colour:
                    visited[neighbour] = 1
                    queue.append(neighbour)
        allCounts[colour] += 1
        if area >= minimumArea:
            result.append({"colour":"red" if colour == 1 else "blue", "area":area,
                           "bbox":[xMin,yMin,xMax,yMax]})
    return result, allCounts


def whiteMask(image, whiteMin=160):
    values = [255 if min(pixel) >= whiteMin and max(pixel)-min(pixel) <= 64 else 0 for pixel in pixelsOf(image)]
    result = Image.new("L",image.size)
    result.putdata(values)
    return result


def canonicalCrop(image, bbox, orientation):
    """orientation is the anticlockwise quarter-turn applied to the native crop.

    It changes only digit interpretation. Reports always keep the native bbox.
    orientation=0 is print-upright in the original native RGB image.
    """
    xMin,yMin,xMax,yMax = bbox
    crop = image.crop((xMin,yMin,xMax+1,yMax+1))
    transforms = [None,Image.Transpose.ROTATE_90,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_270]
    return crop if orientation == 0 else crop.transpose(transforms[orientation])


def classify(image, candidate, orientation=0, whiteMin=160):
    crop = canonicalCrop(image,candidate["bbox"],orientation)
    width,height = crop.size
    result = {**candidate, "kind":"UNKNOWN", "digit":None,"quality":0,"accepted":False,
              "orientationProfile":orientation,"canonicalSize":[width,height],"reason":"GEOMETRY", "windowScores":{}}
    # 8/9 canonical aspect ratio, with a deliberately bounded perspective margin.
    # This is an initial DESIGN gate; camera measurement must validate it.
    if width < 24 or height < 27 or width*10 < height*7 or width*10 > height*11:
        return result,crop,whiteMask(crop,whiteMin)
    mask = whiteMask(crop,whiteMin)
    white = pixelsOf(mask)
    for name,(left,top,right,bottom) in WINDOWS.items():
        samples = [white[y*width+x] != 0 for y in range(height) for x in range(width)
                   if left*width <= WINDOW_SCALE*x+WINDOW_SCALE//2 < right*width
                   and top*height <= WINDOW_SCALE*y+WINDOW_SCALE//2 < bottom*height]
        on = sum(samples)
        total = len(samples)
        result["windowScores"][name] = {"white":on,"samples":total,"permille":on*1000//total if total else 0}
    scores = result["windowScores"]
    if any(scores[name]["samples"] < 2 for name in "ABCDEFG"):
        result["reason"] = "INSUFFICIENT_WINDOW_PIXELS"
        return result,crop,mask
    enabled = []
    for name in "ABCDEFG":
        on,total = scores[name]["white"],scores[name]["samples"]
        if on*100 >= total*60:
            enabled.append(name)
        elif on*100 <= total*30:
            pass
        else:
            result["reason"] = "UNCERTAIN_STROKE"
            return result,crop,mask
    pattern = "".join(enabled)
    result["segments"] = pattern
    if scores["anchor"]["samples"] < 2 or scores["anchor"]["white"]*2 < scores["anchor"]["samples"]:
        result["reason"] = "DIRECTION_ANCHOR"
        return result,crop,mask
    if any(scores[name]["samples"] < 2 or scores[name]["white"]*5 > scores[name]["samples"] for name in ("upperHole","lowerHole")):
        result["reason"] = "FILLED_HOLE"
        return result,crop,mask
    digit = DIGITS.get(pattern)
    if digit is None or (candidate["colour"] == "red" and digit not in (1,2)):
        result["reason"] = "UNKNOWN_PATTERN"
        return result,crop,mask
    result.update(kind="FUNCTION" if candidate["colour"] == "red" else "BAY",digit=digit,
                  quality=255 if all(scores[name]["white"]*10 >= scores[name]["samples"]*8 for name in enabled) else 192,
                  accepted=True,reason="OK")
    return result,crop,mask


def recognise(image, orientation=0, capacity=8, output=None, inputSource="UNSPECIFIED", redMin=64, blueMin=32, cleanup=False,whiteMin=160,colourAlgorithm=0,pruneUnusable=False):
    assert orientation in range(4)
    image = quantise565(image)
    width,height = image.size
    if not 0<=redMin<=255 or not 0<=blueMin<=255 or not 0<=whiteMin<=255:
        raise ValueError("Colour minima must be unsigned 8-bit values")
    rawMask = colourMask(image,redMin,blueMin,colourAlgorithm=colourAlgorithm)
    mask = rawMask
    boundedOracle = None
    if cleanup:
        # Reuse the existing independent Part A mathematical cleanup and
        # row-reclaimed capacity oracle; never substitute a different filter.
        import numpy as np
        from analyse_capture import cleanup as partACleanup
        from candidates_reclaimed_model import candidates_reclaimed
        candidateInput=np.array(rawMask,dtype=np.uint8).reshape(height,width)
        if colourAlgorithm in (1,2):candidateInput=horizontalRunSupport(candidateInput)
        cleaned = partACleanup(candidateInput)
        mask = cleaned.reshape(-1).tolist()
        boundedOracle = candidates_reclaimed(cleaned.tolist(),cap=capacity,min_area=32,prune_unusable=pruneUnusable)
    candidates,allCounts = components(mask,width,height)
    beforeSizeCounts = {colour:sum(item["colour"] == colour for item in candidates) for colour in ("red","blue")}
    if pruneUnusable:
        from candidates_reclaimed_model import usable_candidate_size
        candidates = [item for item in candidates if usable_candidate_size(
            item["bbox"][2]-item["bbox"][0]+1,item["bbox"][3]-item["bbox"][1]+1,
            1 if item["colour"] == "red" else 2)]
    counts = {colour:sum(item["colour"] == colour for item in candidates) for colour in ("red","blue")}
    overflow = any(count > capacity for count in counts.values()) or bool(boundedOracle and boundedOracle["overflow"])
    peak = {colour:max((sum(item["colour"] == colour and item["bbox"][1] <= y <= item["bbox"][3] for item in candidates) for y in range(height)),default=0) for colour in counts}
    result = {"schema":"ECHO7_VISION_MODEL_1","layer":"MODEL","inputSource":inputSource,
              "imageSize":[width,height],"orientationProfile":orientation,"capacityPerColour":capacity,
              "colourProfile":{"redMin":redMin,"blueMin":blueMin,"colourAlgorithm":colourAlgorithm,
                   **({'ratioNumerator':3,'ratioDenominator':2} if colourAlgorithm==0 else
                      {'redSignedHueDegrees':[-24,0],'blueHueDegrees':[200,250 if colourAlgorithm==1 else 260],'minimumSaturation':0.5,'horizontalRunSupport':3})},
              "whiteProfile":{"minimum":whiteMin,"maximumChannelSpread":64,"source":"FIXED_MODEL_PARAMETER_NOT_AUTOMATIC_COLOUR_CALIBRATION"},
              "cleanup":("RUN3_THEN_PART_A_CAUSAL_LEFT_OR_UPPER" if colourAlgorithm in (1,2) else "PART_A_CAUSAL_RAW_LEFT_OR_UPPER") if cleanup else "NONE",
              "boundedCandidateOracle":boundedOracle,
              "candidateCounts":counts,"allComponentsBeforeAreaGate":{"red":allCounts[1],"blue":allCounts[2]},
              "modelPeakOverlappingBboxes":peak,"overflow":overflow,"frameGood":not overflow,
              "capacityBoundary":"Independent BFS; counts do not prove streaming active-label or row-scheduling bounds", "markers":[]}
    if pruneUnusable:
        result["candidateSizePruning"] = {"enabled":True,"beforeSizeGate":beforeSizeCounts,
            "rejected":{colour:beforeSizeCounts[colour]-counts[colour] for colour in counts},
            "redMinimumDimensions":[24,24],"blueMinimumLongShortDimensions":[20,3],
            "scope":"Retired components only; active handles and overflow remain unpruned"}
    outPath = Path(output) if output else None
    if outPath: outPath.mkdir(parents=True,exist_ok=True)
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    for index,candidate in enumerate(candidates):
        marker,crop,white = classify(image,candidate,orientation,whiteMin)
        marker["candidateIndex"] = index
        if overflow:
            marker["accepted"] = False
            marker["quality"] = 0
            marker["reason"] = "FRAME_CAPACITY_OVERFLOW"
        if outPath:
            cropName,maskName = f"candidate_{index:02d}_rgb.png",f"candidate_{index:02d}_white.png"
            crop.save(outPath/cropName)
            white.save(outPath/maskName)
            marker.update(cropFile=cropName,maskFile=maskName)
        result["markers"].append(marker)
        draw.rectangle(candidate["bbox"],outline="lime" if marker["accepted"] else "orange")
        draw.text(tuple(candidate["bbox"][:2]),str(marker["digit"]) if marker["accepted"] else "?",fill="black")
    if outPath:
        maskImage = Image.new("RGB",(width,height))
        palette = [(0,0,0),(255,0,0),(0,0,255)]
        maskImage.putdata([palette[value] for value in mask])
        maskImage.save(outPath/"colour_mask.png")
        if cleanup:
            maskImage.putdata([palette[value] for value in rawMask])
            maskImage.save(outPath/"raw_colour_mask.png")
        overlay.save(outPath/"recognition.png")
        (outPath/"vision.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image",type=Path)
    parser.add_argument("--orientation",type=int,choices=range(4),default=0)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--red-min",type=int,default=64)
    parser.add_argument("--blue-min",type=int,default=32)
    parser.add_argument("--cleanup",action="store_true",help="Apply the actual Part A causal filter and bounded-capacity reference")
    parser.add_argument("--white-min",type=int,default=160,help="Fixed MODEL diagnostic parameter; not automatic red/blue calibration")
    parser.add_argument("--source",required=True,choices=("SYNTHETIC_PDF_REPLAY","RECORDED_CAMERA","LIVE_CAMERA"))
    args = parser.parse_args()
    result = recognise(Image.open(args.image).convert("RGB"),args.orientation,output=args.out,inputSource=args.source,
                       redMin=args.red_min,blueMin=args.blue_min,cleanup=args.cleanup,whiteMin=args.white_min)
    result["inputSha256"] = hashlib.sha256(args.image.read_bytes()).hexdigest()
    (args.out/"vision.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    return 1 if result["overflow"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
