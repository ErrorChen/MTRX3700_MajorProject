#!/usr/bin/env python3
"""Export independent pixel/model expectations for sevenSegmentReader RTL.

The generated banks are synthetic logical 320x240 white masks. They are not
sensor bus streams and do not validate candidate scheduling or physical input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tests/python"))

from PIL import Image, ImageDraw, ImageFilter
from vision_reference import quantise565, whiteMask, pixelsOf, colourMask, components, classify
from test_vision import singleMarker


repoPath = Path(__file__).resolve().parents[2]
REASONS = {"OK":0,"GEOMETRY":1,"INSUFFICIENT_WINDOW_PIXELS":2,"UNCERTAIN_STROKE":3,
           "DIRECTION_ANCHOR":4,"FILLED_HOLE":4,"UNKNOWN_PATTERN":5}


def packCandidate(candidate):
    xmin,ymin,xmax,ymax = candidate["bbox"]
    fields = [(1,1),(xmin,9),(xmax,9),(ymin,8),(ymax,8),(candidate["area"],17),((xmin+xmax)//2,9),((ymin+ymax)//2,8)]
    word = 0
    for value,width in fields:
        assert 0 <= value < 1 << width
        word = (word << width) | value
    return word


def sheetWithCards(cards):
    image = Image.new("RGB",(320,240),"white")
    for index,(card,x,y) in enumerate(cards):
        image.paste(card,(x,y))
    return image


def cases():
    original = Image.open(repoPath/"assets/markers/sheet_320x240.png").convert("RGB")
    yield "pdf_full_page",original,0
    initial,_ = components(colourMask(quantise565(original)),320,240)
    classified = [classify(quantise565(original),candidate)[0] for candidate in initial]
    cards = {m["digit"]:m for m in classified if m["accepted"] and m["colour"]=="blue"}
    swapped = original.copy()
    first,second = cards[1]["bbox"],cards[2]["bbox"]
    extract = lambda b:original.crop((b[0],b[1],b[2]+1,b[3]+1))
    swapped.paste(extract(second),(first[0],first[1]))
    swapped.paste(extract(first),(second[0],second[1]))
    yield "counterfactual_swapped",swapped,0
    cornerRemoved = original.copy()
    for candidate in initial:
        cornerRemoved.putpixel(tuple(candidate["bbox"][:2]),(255,255,255))
    yield "candidate_first_colour_pixel_missing",cornerRemoved,0
    for orientation,operation in enumerate((None,Image.Transpose.ROTATE_270,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_90)):
        card = singleMarker("ABDEG")
        if operation is not None: card = card.transpose(operation)
        image = sheetWithCards([(card,40,50)])
        yield f"orientation_{orientation}",image,orientation
        if orientation:
            yield f"wrong_orientation_{orientation}",image,0
    yield "unsupported_0_7_8_9",sheetWithCards([(singleMarker(pattern),15+i*72,50) for i,pattern in enumerate(("ABCDEF","ABC","ABCDEFG","ABCDFG"))]),0
    yield "red_rejected_3_4_5_6",sheetWithCards([(singleMarker(pattern,"red"),15+i*72,50) for i,pattern in enumerate(("ABCDG","BCFG","ACDFG","ACDEFG"))]),0
    yield "blank_delete_missing_anchor",sheetWithCards([(singleMarker(""),10,60),(singleMarker("C"),100,60),(singleMarker("BC",anchor=False),200,60)]),0
    filled = singleMarker("ABDEG")
    ImageDraw.Draw(filled).rectangle((21,18,33,24),fill="white")
    yield "blur_shape_and_undersize",sheetWithCards([(singleMarker("ABDEG").filter(ImageFilter.GaussianBlur(3)),10,60),(filled,100,60),(singleMarker("BC",size=(20,23)),200,60)]),0
    yield "empty_frame",Image.new("RGB",(320,240),"white"),0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",required=True,type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    evidence = []
    vectorCases = list(cases())
    (args.out/"vision_count.hex").write_text(f"{len(vectorCases):08x}\n",encoding="ascii")
    for index,(name,image,orientation) in enumerate(vectorCases):
        image = quantise565(image)
        mask = whiteMask(image)
        candidates,_ = components(colourMask(image),320,240)
        candidateWords = [0]*16
        expectedWords = [0x000f0001]*16  # invalid geometry, digit F
        counts = {"red":0,"blue":0}
        expected = []
        for candidate in candidates:
            colour = candidate["colour"]
            slot = counts[colour]+(8 if colour=="blue" else 0)
            counts[colour] += 1
            assert counts[colour] <= 8, "Reader vector must not silently truncate capacity"
            candidateWords[slot] = packCandidate(candidate)
            marker = classify(image,candidate,orientation)[0]
            digit = marker["digit"] if marker["accepted"] else 15
            expectedWords[slot] = (int(marker["accepted"])<<24) | (digit<<16) | (marker["quality"]<<8) | REASONS[marker["reason"]]
            expected.append({"slot":slot,**marker})
        prefix = args.out/f"vision_{index}"
        image.save(prefix.with_suffix(".png"))
        # Full logical RGB565 pixel input for an independent core replay. Unlike
        # the reader's candidate fixtures this exercises the actual colour and
        # candidate pipeline when a bench applies the real row-idle budget.
        rgb565 = [((red>>3)<<11)|((green>>2)<<5)|(blue>>3) for red,green,blue in pixelsOf(image)]
        Path(str(prefix)+"_rgb565.hex").write_text("".join(f"{value:04x}\n" for value in rgb565),encoding="ascii")
        Path(str(prefix)+"_white.hex").write_text("".join("1\n" if value else "0\n" for value in pixelsOf(mask)),encoding="ascii")
        Path(str(prefix)+"_candidates.hex").write_text("".join(f"{word:018x}\n" for word in candidateWords),encoding="ascii")
        Path(str(prefix)+"_expected.hex").write_text("".join(f"{word:08x}\n" for word in expectedWords),encoding="ascii")
        Path(str(prefix)+"_orientation.hex").write_text(f"{orientation:x}\n",encoding="ascii")
        evidence.append({"index":index,"name":name,"orientation":orientation,"candidateCounts":counts,
                         "imageSha256":hashlib.sha256(prefix.with_suffix(".png").read_bytes()).hexdigest(),"expected":expected})
    manifest = {"schema":"ECHO7_VISION_RTL_VECTORS_1","inputSource":"SYNTHETIC_PDF_AND_PIXEL_COUNTERFACTUALS",
                "reference":"vision_reference.py","boundary":"Reader only; candidate descriptors come from independent BFS; white mask is synchronous RAM stimulus", "cases":evidence}
    (args.out/"vision_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","layer":"VECTOR_GENERATION","cases":len(evidence),"output":str(args.out)}))


if __name__ == "__main__":
    main()
