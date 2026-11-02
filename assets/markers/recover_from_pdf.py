#!/usr/bin/env python3
"""Recover the supplied REV2 print geometry without inventing a missing taskpack.

Requires pypdf and Pillow. Poppler's pdftocairo/pdftoppm create the page previews.
All coordinates in the JSON are millimetres from the top left of the paper or
normalised to the coloured main rectangle. The scene manifest contains test
expectations only; recognition must never use its marker positions as identities.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from PIL import Image, ImageDraw
from pypdf import PdfReader


assetPath = Path(__file__).resolve().parent
pdfPath = assetPath / "ECHO7_All_Markers_A4_v2.pdf"
expectedPdfHash = "0162b5a7ada3c7d03dcf96baf5a8a5ce077ff8d165aaad8cc228947ff70436a0"
mmPerPoint = 25.4 / 72
pageHeightMm = 210.0


def rounded(value):
    return round(float(value), 5)


def extractShapes():
    """Only coloured rectangle and white polygon drawing operations are needed.

    The source PDF has identity CTM and no transformed paths; reject a future
    source that changes that assumption rather than silently misplace geometry.
    """
    from pypdf.generic import ContentStream
    reader = PdfReader(pdfPath)
    assert len(reader.pages) == 1, "Expected the supplied single-page sheet"
    page = reader.pages[0]
    assert abs(float(page.mediabox.width) * mmPerPoint - 297) < 0.01
    assert abs(float(page.mediabox.height) * mmPerPoint - 210) < 0.01
    colour = None
    path = []
    shapes = []
    for args, op in ContentStream(page.get_contents(), reader).operations:
        if op == b"cm":
            assert list(map(float, args)) == [1, 0, 0, 1, 0, 0], "Unexpected transform"
        elif op == b"rg":
            colour = tuple(round(float(x) * 255) for x in args)
        elif op == b"n":
            path = []
        elif op == b"re":
            x, y, width, height = map(float, args)
            path = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        elif op in (b"m", b"l"):
            path.append(tuple(map(float, args)))
        elif op in (b"f", b"f*"):
            if colour in ((192, 0, 0), (0, 87, 184), (255, 255, 255)) and path:
                points = [[rounded(x * mmPerPoint), rounded(pageHeightMm - y * mmPerPoint)] for x, y in path]
                shapes.append({"rgb": list(colour), "pointsMm": points})
            path = []
    return shapes


def box(points):
    xs, ys = zip(*points)
    return [rounded(min(xs)), rounded(min(ys)), rounded(max(xs)-min(xs)), rounded(max(ys)-min(ys))]


def normalise(points, bounds):
    x, y, width, height = bounds
    return [[rounded((px-x)/width), rounded((py-y)/height)] for px, py in points]


def main():
    assert hashlib.sha256(pdfPath.read_bytes()).hexdigest() == expectedPdfHash, "Source PDF changed; review extraction/order before regenerating"
    shapes = extractShapes()
    coloured = [shape for shape in shapes if shape["rgb"] != [255, 255, 255]]
    assert len(coloured) == 9
    names = [("FUNCTION", 1), ("REFERENCE", None), ("FUNCTION", 2)] + [("BAY", n) for n in range(1, 7)]
    markers = []
    segmentPolygons = {}
    digitSegments = {1:"BC", 2:"ABDEG", 3:"ABCDG", 4:"BCFG", 5:"ACDFG", 6:"ACDEFG"}
    anchorPolygon = None
    for shape, (kind, digit) in zip(coloured, names):
        bounds = box(shape["pointsMm"])
        item = {"kind": kind, "digit": digit, "colour": "red" if shape["rgb"][0] else "blue", "mainBoxMm": bounds}
        polygons = []
        for whiteShape in shapes:
            if whiteShape["rgb"] != [255,255,255]:
                continue
            wx, wy, ww, wh = box(whiteShape["pointsMm"])
            x, y, width, height = bounds
            if wx >= x and wy >= y and wx+ww <= x+width+0.00001 and wy+wh <= y+height+0.00001:
                polygons.append(normalise(whiteShape["pointsMm"], bounds))
        if kind != "REFERENCE":
            assert abs(bounds[2]-54) < 0.001 and abs(bounds[3]-60.75) < 0.001
            for polygon in polygons:
                px, py, pw, ph = box(polygon)
                cx, cy = px+pw/2, py+ph/2
                if cx < .2 and cy < .2:
                    anchorPolygon = polygon
                    continue
                if pw > ph:
                    name = "A" if cy < .3 else ("D" if cy > .7 else "G")
                elif cx < .5:
                    name = "F" if cy < .5 else "E"
                else:
                    name = "B" if cy < .5 else "C"
                segmentPolygons[name] = polygon
            assert len(polygons) == len(digitSegments[digit])+1
        item["whitePolygonsNormalised"] = polygons
        markers.append(item)
    assert set(segmentPolygons) == set("ABCDEFG") and anchorPolygon is not None
    provenance = {
        "status": "RECOVERED_FROM_SUPPLIED_PDF",
        "source": "ECHO7_All_Markers_A4_v2.pdf",
        "sourceSha256": hashlib.sha256(pdfPath.read_bytes()).hexdigest(),
        "missingOriginal": "The taskpack marker_spec.json and scene_manifest.json were not supplied in this checkout.",
        "method": "Exact PDF drawing paths converted from points to millimetres; rounded to five decimal places.",
        "classification": "DESIGN recovery, not the missing original taskpack specification",
    }
    spec = {
        "schema": "ECHO7_MARKERS_RECOVERED_1", "provenance": provenance,
        "paperMm": {"width":297,"height":210,"foldX":148.5},
        "coordinates": "Top-left origin; +x right; +y down; normalised coordinates refer to the main colour rectangle",
        "mainSizeMm": [54,60.75], "activeBayMask":126,
        "colours": {"red":"#C00000","blue":"#0057B8","white":"#FFFFFF"},
        "digitRoiNormalised": [0.25,2/15,0.5,11/15],
        "orientationAnchorPolygonNormalised": anchorPolygon,
        "segmentPolygonsNormalised": dict(sorted(segmentPolygons.items())),
        "digitSegments": digitSegments,
        "calibrationDesign": {
            "status":"PROPOSED_SAMPLE_REGIONS_NOT_HARDWARE_VALIDATED",
            "redSampleBoxNormalised":[0.08,0.30,0.12,0.35],
            "blueSampleBoxNormalisedToReference":[0.1,0.2,0.8,0.6],
            "referenceBelowMainGapMm":2.7,"referenceSizeMm":[54,12.15],
            "note":"These inset ROIs are engineering choices in empty areas of the recovered artwork, not recovered taskpack ROI instructions. Sample raw RGB without old-threshold filtering."
        },
        "markers": markers,
    }
    manifest = {"schema":"ECHO7_SCENE_RECOVERED_1","provenance":provenance,
                "use":"TEST_EXPECTATIONS_ONLY_NEVER_RUNTIME_ID_LOOKUP",
                "inputSource":"PDF_VECTOR_ARTWORK_NOT_CAMERA_CAPTURE",
                "markers":[{k:v for k,v in item.items() if k != "whitePolygonsNormalised"} for item in markers],
                "expectedFormalMarkers":8,"expectedMainBlueRegions":7,
                "replay":{"file":"sheet_320x240.png","format":"RGB_IMAGE_NOT_OV7670_SENSOR_SCENE_OR_GRAB","paperBoxPixels":[10,14,300,212]}}
    (assetPath/"marker_spec.json").write_text(json.dumps(spec,indent=2)+"\n",encoding="utf-8")
    (assetPath/"scene_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    templatePath = assetPath/"templates"
    templatePath.mkdir(exist_ok=True)
    for digit, names in digitSegments.items():
        template = Image.new("L",(64,72),0)
        draw = ImageDraw.Draw(template)
        for polygon in [anchorPolygon]+[segmentPolygons[name] for name in names]:
            draw.polygon([(round(x*64),round(y*72)) for x,y in polygon],fill=255)
        template.save(templatePath/f"digit_{digit}.png")
    for tool in ("pdftocairo","pdftoppm"):
        if not shutil.which(tool):
            raise RuntimeError(f"Required Poppler executable missing: {tool}")
    subprocess.run(["pdftocairo","-svg",str(pdfPath),str(assetPath/"ECHO7_All_Markers_A4_v2.svg")],check=True,timeout=60)
    subprocess.run(["pdftoppm","-f","1","-singlefile","-scale-to","1600","-png",str(pdfPath),str(assetPath/"ECHO7_All_Markers_A4_v2")],check=True,timeout=60)
    page = Image.open(assetPath/"ECHO7_All_Markers_A4_v2.png").convert("RGB")
    replay = Image.new("RGB",(320,240),"white")
    replay.paste(page.resize((300,212),Image.Resampling.LANCZOS),(10,14))
    replay.save(assetPath/"sheet_320x240.png")
    # RGB565 is a logical 320x240 pixel replay, not the sensor's bus timing/byte
    # stream or the staff GRAB schema. The .hex line is one full pixel, MSB first.
    sourcePixels = replay.get_flattened_data() if hasattr(replay,"get_flattened_data") else replay.getdata()
    pixels = [((r>>3)<<11)|((g>>2)<<5)|(b>>3) for r,g,b in sourcePixels]
    (assetPath/"sheet_320x240_rgb565.hex").write_text("".join(f"{value:04x}\n" for value in pixels),encoding="ascii")
    print(json.dumps({"status":"PASS","layer":"ASSET_RECOVERY","sourceSha256":provenance["sourceSha256"],"formalMarkers":8,"segments":7,"templates":6}))


if __name__ == "__main__":
    main()
