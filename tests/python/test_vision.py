#!/usr/bin/env python3
"""Run the independent pixel reference against artwork and counterfactual pixels.

All inputs are synthetic, including PDF-rendered images. This executable emits
JSON and exits nonzero on any failed assertion. It does not invoke an HDL model.
"""
from __future__ import annotations
import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]

import json
from pathlib import Path
import sys
import traceback

from PIL import Image, ImageDraw, ImageFilter
from vision_reference import recognise, classify, quantise565


repoPath = Path(__file__).resolve().parents[2]
assetPath = repoPath/"assets/markers"
outputPath = repoPath/"build/member_b/vision_tests"
spec = json.loads((assetPath/"marker_spec.json").read_text(encoding="utf-8"))
caseResults = []


def assertThat(condition, message):
    if not condition:
        raise AssertionError(message)


def accepted(result):
    return [marker for marker in result["markers"] if marker["accepted"]]


def runCase(name, procedure):
    try:
        detail = procedure()
        caseResults.append({"name":name,"status":"PASS", "detail":detail})
    except Exception as error:
        caseResults.append({"name":name,"status":"FAIL","error":str(error),"traceback":traceback.format_exc()})


def singleMarker(segments, colour="blue", anchor=True, size=(54,61)):
    image = Image.new("RGB",size,(0,87,184) if colour == "blue" else (192,0,0))
    draw = ImageDraw.Draw(image)
    polygons = [spec["segmentPolygonsNormalised"][name] for name in segments]
    if anchor: polygons.append(spec["orientationAnchorPolygonNormalised"])
    for polygon in polygons:
        draw.polygon([(round(x*size[0]),round(y*size[1])) for x,y in polygon],fill="white")
    return image


def classifySingle(image, colour="blue", orientation=0):
    return classify(quantise565(image),{"colour":colour,"area":image.width*image.height,
                                       "bbox":[0,0,image.width-1,image.height-1]},orientation)[0]


def fullPage():
    image = Image.open(assetPath/"sheet_320x240.png").convert("RGB")
    result = recognise(image,output=outputPath/"full_page",inputSource="SYNTHETIC_PDF_REPLAY")
    identities = sorted((marker["kind"],marker["digit"]) for marker in accepted(result))
    assertThat(identities == [("BAY",n) for n in range(1,7)]+[("FUNCTION",1),("FUNCTION",2)],str(identities))
    assertThat(result["candidateCounts"] == {"red":2,"blue":7},"Candidate count does not match pixel components")
    assertThat(not result["overflow"],"Original full page exceeds CAP8")
    rejected = [marker for marker in result["markers"] if not marker["accepted"]]
    assertThat(len(rejected)==1 and rejected[0]["reason"] == "GEOMETRY","Blank reference must be rejected")
    return {"identities":identities,"counts":result["candidateCounts"],"rejectedReference":rejected[0]["bbox"]}


def swapDigits():
    image = Image.open(assetPath/"sheet_320x240.png").convert("RGB")
    initial = recognise(image)
    cards = {marker["digit"]:marker for marker in accepted(initial) if marker["kind"] == "BAY"}
    firstBox,secondBox = cards[1]["bbox"],cards[2]["bbox"]
    first = image.crop((firstBox[0],firstBox[1],firstBox[2]+1,firstBox[3]+1))
    second = image.crop((secondBox[0],secondBox[1],secondBox[2]+1,secondBox[3]+1))
    image.paste(second,(firstBox[0],firstBox[1]))
    image.paste(first,(secondBox[0],secondBox[1]))
    image.save(outputPath/"swapped.png")
    result = recognise(image,output=outputPath/"swapped",inputSource="SYNTHETIC_PIXEL_COUNTERFACTUAL")
    atFirst = [marker for marker in accepted(result) if marker["bbox"] == firstBox]
    atSecond = [marker for marker in accepted(result) if marker["bbox"] == secondBox]
    assertThat(len(atFirst)==1 and atFirst[0]["digit"]==2,"First position retained its scene answer")
    assertThat(len(atSecond)==1 and atSecond[0]["digit"]==1,"Second position retained its scene answer")
    return {"firstDigit":2,"secondDigit":1}


def deleteStroke():
    image = singleMarker("C")  # Delete B from digit 1, retaining its anchor.
    result = classifySingle(image)
    assertThat(not result["accepted"] and result["reason"] == "UNKNOWN_PATTERN",str(result))
    return result["reason"]


def supportedDigits():
    results = []
    for colour in ("red","blue"):
        for digit,names in spec["digitSegments"].items():
            digit = int(digit)
            result = classifySingle(singleMarker(names,colour),colour)
            shouldAccept = colour == "blue" or digit in (1,2)
            assertThat(result["accepted"] == shouldAccept,f"{colour} {digit}: {result}")
            if shouldAccept:
                assertThat(result["digit"] == digit,"Wrong pixel-derived digit")
                assertThat(result["kind"] == ("BAY" if colour=="blue" else "FUNCTION"),"Wrong marker type")
            results.append([colour,digit,result["accepted"]])
    return results


def unknownDigits():
    results = []
    for digit,pattern in {0:"ABCDEF",7:"ABC",8:"ABCDEFG",9:"ABCDFG"}.items():
        result = classifySingle(singleMarker(pattern))
        assertThat(not result["accepted"] and result["reason"]=="UNKNOWN_PATTERN",f"digit {digit}: {result}")
        results.append(digit)
    return results


def rotations():
    base = singleMarker("ABDEG")
    transforms = [None,Image.Transpose.ROTATE_270,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_90]
    for orientation in range(4):
        image = base if orientation==0 else base.transpose(transforms[orientation])
        result = classifySingle(image,orientation=orientation)
        assertThat(result["accepted"] and result["digit"]==2,f"orientation {orientation}: {result}")
        if orientation:
            wrong = classifySingle(image,orientation=0)
            assertThat(not wrong["accepted"],f"Wrong orientation accepted {orientation}")
    return "Four native orientations with matching profile; wrong profiles rejected"


def shapeRejects():
    examples = {"blank":singleMarker(""),"missing_anchor":singleMarker("BC",anchor=False),
                "blurred":singleMarker("ABDEG").filter(ImageFilter.GaussianBlur(3)),
                "undersized":singleMarker("BC",size=(20,23))}
    filled = singleMarker("ABDEG")
    ImageDraw.Draw(filled).rectangle((21,18,33,24),fill="white")
    examples["filled_hole"] = filled
    details = {}
    for name,image in examples.items():
        result = classifySingle(image)
        assertThat(not result["accepted"],f"{name}: {result}")
        details[name] = result["reason"]
    return details


def overflow():
    image = Image.new("RGB",(320,240),"white")
    for row in range(3):
        for column in range(3):
            image.paste(singleMarker("BC"),(10+column*100,8+row*76))
    result = recognise(image,output=outputPath/"overflow",inputSource="SYNTHETIC_CAPACITY_STRESS")
    assertThat(result["candidateCounts"]["blue"]==9 and result["overflow"],"Missing explicit overflow")
    assertThat(not accepted(result) and not result["frameGood"],"Overflow produced trusted partial recognition")
    return result["candidateCounts"]


def noiseComponents():
    image = Image.open(assetPath/"sheet_320x240.png").convert("RGB")
    draw = ImageDraw.Draw(image)
    for index in range(16):
        draw.point((5+index*8,230),fill=(0,87,184))
    result = recognise(image,inputSource="SYNTHETIC_NOISE")
    assertThat(result["allComponentsBeforeAreaGate"]["blue"]==23,"Noise components not counted")
    assertThat(result["candidateCounts"]["blue"]==7 and len(accepted(result))==8,"Small noise affected area-filtered identities")
    return {"counts":result["candidateCounts"],"all":result["allComponentsBeforeAreaGate"],
            "limit":"This BFS area test does not prove streaming active-label capacity under noise"}


def calibratedProfile():
    image = Image.open(assetPath/"sheet_320x240.png").convert("RGB")
    result = recognise(image,redMin=255,blueMin=255)
    assertThat(not accepted(result),"Runtime profile minima were ignored")
    assertThat(result["colourProfile"]["redMin"]==255 and result["colourProfile"]["blueMin"]==255,"Profile provenance missing")
    return result["colourProfile"]


def actualCleanup():
    image = Image.open(assetPath/"sheet_320x240.png").convert("RGB")
    result = recognise(image,cleanup=True,output=outputPath/"part_a_cleanup",inputSource="SYNTHETIC_PDF_REPLAY")
    assertThat(len(accepted(result))==8 and not result["overflow"],"Part A cleanup changed formal identities")
    assertThat(result["boundedCandidateOracle"]["frame_valid"],"Bounded oracle rejected nominal page")
    return {"counts":result["candidateCounts"],"cleanup":result["cleanup"],"boundedOracle":result["boundedCandidateOracle"]}


def main():
    outputPath.mkdir(parents=True,exist_ok=True)
    for name,procedure in [("full_page_8_markers_and_reference",fullPage),("counterfactual_swap_1_2",swapDigits),
        ("counterfactual_delete_stroke",deleteStroke),("all_digits_colour_type",supportedDigits),
        ("unknown_0_7_8_9",unknownDigits),("orientation_profiles",rotations),("shape_and_blur_rejection",shapeRejects),
        ("capacity_overflow",overflow),("noise_components",noiseComponents),
        ("runtime_colour_profile",calibratedProfile),("actual_part_a_cleanup",actualCleanup)]:
        runCase(name,procedure)
    result = {"schema":"ECHO7_VISION_TESTS_1","layer":"MODEL","inputSource":"SYNTHETIC_ARTWORK_AND_COUNTERFACTUALS",
              "status":"FAIL" if any(case["status"]=="FAIL" for case in caseResults) else "PASS",
              "cases":caseResults}
    (outputPath/"results.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
