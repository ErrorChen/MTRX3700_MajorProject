#!/usr/bin/env python3
"""Measure actual recorded RGB and recognised geometry without touching hardware.

The current raw-ROI reference supports native orientationProfile=0 only. A
single same-frame sample predicts a shadow floor; it is not an eight-frame
calibration, a previous-frame ROI stability check, or an exposure/AWB freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS / 'lib'))
from audit_calibration import paired, sample
from vision_reference import quantise565


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bbox(marker):
    return [marker[key] for key in ('xMin', 'yMin', 'xMax', 'yMax')]


def checkedBox(box):
    if not (len(box) == 4 and all(isinstance(value, int) for value in box) and
            0 <= box[0] <= box[2] < 320 and 0 <= box[1] <= box[3] < 240):
        raise ValueError(f'candidate outside inclusive native coordinates: {box}')
    return box


def sceneMeasurement(capturePath, outputPath):
    capturePath, outputPath = Path(capturePath).resolve(), Path(outputPath).resolve()
    capture = json.loads(capturePath.read_text(encoding='utf-8'))
    recognition = capture.get('recognition', {})
    if capture.get('command') != 'capture' or capture.get('status') != 'PASS' or not recognition.get('sameFrameVerified'):
        raise ValueError('requires a successful decoded, frame-bound camera capture result')
    if recognition.get('orientationProfile') != 0:
        raise ValueError('raw ROI reference supports orientationProfile=0; other profiles must be explicitly implemented')
    # Relocation-safe archives take precedence over historical absolute paths.
    folders = [capturePath.parent, Path(capture.get('outputDirectory', capturePath.parent))]
    folder = next((path for path in folders if (path / 'capture/frame.png').is_file()), None)
    if folder is None:
        raise ValueError('capture/frame.png not found beside result or at original outputDirectory')
    imagePath = folder / 'capture/frame.png'
    image = Image.open(imagePath).convert('RGB')
    if image.size != (320, 240):
        raise ValueError('expected native 320x240 image')
    imageArray = np.asarray(image)
    if not np.array_equal(imageArray, np.asarray(quantise565(image))):
        raise ValueError('image pixels are not exact expanded RGB565 values')
    validation = {'imageSize': [320, 240], 'rgb565RoundTrip': 'PASS',
                  'captureResultSameFrameVerified': True, 'dumpCheck': 'NOT_PRESENT'}
    dumpPath = folder / 'capture/dump.bin'
    if dumpPath.is_file():
        if sha256(dumpPath) != capture.get('dumpSha256'):
            raise ValueError('raw dump SHA256 differs from capture result')
        spec = importlib.util.spec_from_file_location('echo7SceneGrab', TOOLS / 'capture/grab.py')
        grab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grab)
        decoded = grab.decode(dumpPath.read_bytes())
        if decoded['offset'] != 0 or decoded['bytes'] != dumpPath.stat().st_size:
            raise ValueError('raw dump framing differs')
        if decoded['results'] != capture['snapshot']['results'] or not np.array_equal(imageArray, grab.frame_rgb(decoded['pixels'])):
            raise ValueError('image or metadata differs from CRC-checked dump')
        validation.update(dumpCheck='CRC_PIXEL_METADATA_PASS', dumpSha256=sha256(dumpPath), crc=decoded['crc'])

    redCount, blueCount = recognition['redCandidateCount'], recognition['blueCandidateCount']
    if not (0 <= redCount <= 8 and 0 <= blueCount <= 8):
        raise ValueError('completed candidate count exceeds output capacity')
    presentIndices = list(range(redCount)) + list(range(8, 8 + blueCount))
    present = [recognition['markers'][index] for index in presentIndices]
    for marker in present:
        checkedBox(bbox(marker))
    redCards = [marker for marker in present if marker['accepted'] and not marker['isBlue'] and marker['digit'] == 1]
    pairs = [(redCard, reference) for redCard in redCards for reference in present
             if reference['isBlue'] and paired(bbox(redCard), bbox(reference))]
    if len(pairs) != 1:
        raise ValueError(f'expected one real red1/geometric blue-reference pair, found {len(pairs)}')
    redCard, reference = pairs[0]
    if reference['accepted']:
        raise ValueError('paired blue reference unexpectedly claims a bay digit')
    rawSamples = sample(image, bbox(redCard), bbox(reference), samplerAlgorithm=2)
    outputPath.mkdir(parents=True, exist_ok=True)
    rgb565 = np.asarray(quantise565(image), dtype=np.int16)
    for colour in ('red', 'blue'):
        measured = rawSamples[colour]
        x0, y0, x1, y1 = checkedBox(measured['sampleBounds'])
        values = rgb565[y0:y1+1, x0:x1+1].reshape(-1, 3)
        # These inset ROI predicates produce rectangular native-pixel windows.
        # Independently check count and extrema before exporting their crops.
        if len(values) != measured['sampleCount'] or values.min(axis=0).tolist() != measured['allRgbMinimum'] or values.max(axis=0).tolist() != measured['allRgbMaximum']:
            raise ValueError(f'{colour} ROI geometry/statistics disagree')
        path = outputPath / f'{colour}_raw_roi.png'
        image.crop((x0, y0, x1+1, y1+1)).save(path)
        measured['crop'] = path.name
        measured['cropSha256'] = sha256(path)

    # Embedded comparison data already follows this captured bbox. Optional
    # external model output is used only when no embedded comparison is present.
    references = {item['index']: item['pixelReference']
                  for item in capture.get('glyphAgreement', {}).get('comparisons', [])}
    projectivePath = folder / 'pixel_reference/projective.json'
    projective = json.loads(projectivePath.read_text(encoding='utf-8')) if projectivePath.is_file() else None
    candidates = []
    for marker in present:
        box = bbox(marker)
        label = ('B' if marker['isBlue'] else 'R') + (str(marker['digit']) if marker['accepted'] else '?')
        cropPath = outputPath / f"candidate_{marker['index']:02d}_{label.replace('?', 'unknown')}.png"
        image.crop((box[0], box[1], box[2]+1, box[3]+1)).save(cropPath)
        item = {**marker, 'type': 'BAY' if marker['isBlue'] else 'FUNCTION',
                'bbox': box, 'widthPixels': box[2]-box[0]+1, 'heightPixels': box[3]-box[1]+1,
                'touchesFrameBoundary': box[0] == 0 or box[1] == 0 or box[2] == 319 or box[3] == 239,
                'crop': cropPath.name, 'cropSha256': sha256(cropPath)}
        model = references.get(marker['index'])
        if model is None and projective:
            matches = [candidate for candidate in projective['markers']
                       if candidate['bbox'] == box and (candidate['colour'] == 'blue') == marker['isBlue']]
            if len(matches) == 1:
                model = matches[0]
        if model is not None:
            if model.get('bbox') != box or (model.get('colour') == 'blue') != marker['isBlue']:
                raise ValueError('projective comparison belongs to a different candidate')
            budget = {key: model[key] for key in ('quad', 'quadHalfPixels', 'areaPixels', 'uniqueSourceSamples',
                      'minimumHorizontalEdgePixels', 'edgeSquaredHalfPixelUnits', 'foregroundCount') if key in model}
            if 'edgeSquaredHalfPixelUnits' in budget:
                budget['edgeLengthsPixels'] = [math.sqrt(value) / 2 for value in budget['edgeSquaredHalfPixelUnits']]
                budget['minimumEdgePixels'] = min(budget['edgeLengthsPixels'])
            budget['evidenceLevel'] = 'MODEL_GEOMETRY_ON_RECORDED_CAMERA'
            item['resolutionBudget'] = budget
        candidates.append(item)

    # Labels preserve native geometry. Enlarging nearest-neighbour pixels is a
    # viewing aid and cannot create more optical resolution.
    scale, banner = 3, 64
    overlay = Image.new('RGB', (960, 784), '#181818')
    overlay.paste(image.resize((960, 720), Image.Resampling.NEAREST), (0, banner))
    draw = ImageDraw.Draw(overlay)
    draw.text((8, 7), f"RECORDED CAMERA / MODEL ROI MEASUREMENT | frame {recognition['frameId']} cfg {recognition['configVersion']} build {recognition['buildId']:08x}", fill='white')
    draw.text((8, 24), 'Yellow: red raw ROI. Green: paired blue raw ROI. R/B labels: actual captured FPGA candidates.', fill='white')
    draw.text((8, 41), 'Same-image ROI model only; not the held previous-frame ROI or eight fresh calibration samples.', fill='white')
    def scaled(box):
        return [box[0]*scale, box[1]*scale+banner, (box[2]+1)*scale-1, (box[3]+1)*scale+banner-1]
    for item in candidates:
        coordinates = scaled(item['bbox'])
        colour = '#52a9ff' if item['isBlue'] else '#ff7777'
        draw.rectangle(coordinates, outline=colour, width=2)
        label = ('B' if item['isBlue'] else 'R') + (str(item['digit']) if item['accepted'] else '?')
        draw.text((coordinates[0]+2, coordinates[1]+2), f"{label} q{item['quality']}", fill='white', stroke_width=1, stroke_fill='black')
    for colour, ink in (('red', 'yellow'), ('blue', '#00ff00')):
        draw.rectangle(scaled(rawSamples[colour]['sampleBounds']), outline=ink, width=3)
    overlay.save(outputPath / 'raw_rois_annotated.png')
    result = {
        'schema': 'echo7-recorded-scene-measurement-v1', 'status': 'PASS',
        'evidenceLevel': 'MODEL_ON_RECORDED_CAMERA', 'inputSource': 'RECORDED_OV7670_RGB565',
        'captureResult': str(capturePath), 'captureResultSha256': sha256(capturePath),
        'rawImage': str(imagePath), 'rawImageSha256': sha256(imagePath), 'validation': validation,
        'toolSha256': sha256(Path(__file__)),
        'referenceToolSha256': {name: sha256(TOOLS / 'lib' / name) for name in ('audit_calibration.py', 'vision_reference.py')},
        'buildId': recognition['buildId'], 'buildIdHex': f"{recognition['buildId']:08x}",
        'frameId': recognition['frameId'], 'captureStartUs': recognition['captureStartUs'],
        'configVersion': recognition['configVersion'], 'orientationProfile': 0,
        'recordedActiveProfile': {'redMinimum': recognition['redMinimum'], 'blueMinimum': recognition['blueMinimum']},
        'pair': {'redMarkerIndex': redCard['index'], 'blueReferenceIndex': reference['index'],
                 'redBox': bbox(redCard), 'blueReferenceBox': bbox(reference), 'uniqueGeometricPair': True},
        'modelRoiContext': {
            'geometrySource': 'CURRENT_CAPTURE_SAME_FRAME_CANDIDATE_BBOX',
            'frameId': recognition['frameId'],
            'diagnosticOnly': True,
            'description': 'Model applies current-image candidate geometry to this same image. It does not reconstruct the FPGA held previous-frame ROI or its eight accepted sampling frames.',
        },
        'capturedCoreLastOwnedSample': {
            'evidenceSource': 'PERSISTED_FPGA_STATUS_IN_CAPTURE',
            'redSamples': recognition['redSamples'],
            'blueSamples': recognition['blueSamples'],
            'calibrationSampleFrames': recognition['calibrationSampleFrames'],
            'calibrationLastSample': recognition['calibrationLastSample'],
            'description': 'Counts belong to the last owned calibration sample using held previous-frame ROI geometry; they are persisted until another owned sample. They are not counts from this captured image or a fresh eight-frame verification. No equality with rawSamples is expected or asserted.',
        },
        'rawSamples': rawSamples,
        'singleFrameShadowPrediction': {'redMinimum': rawSamples['red']['shadowMinimum'],
                                       'blueMinimum': rawSamples['blue']['shadowMinimum'],
                                       'formula': 'floor(darkest raw dominant channel / 2)',
                                       'eligibleSingleFrame': rawSamples['frameSampleGood']},
        'actualCandidates': candidates,
        'actualAcceptedTypedIds': sorted(('B' if item['isBlue'] else 'R')+str(item['digit']) for item in candidates if item['accepted']),
        'capacity': {key: recognition[key] for key in ('activeCandidateCapacity', 'outputCandidateCapacity',
                     'allocationPeakRed', 'allocationPeakBlue', 'candidateOverflow', 'frameGood')},
        'projectiveJsonSha256': sha256(projectivePath) if projectivePath.is_file() else None,
        'annotatedImage': 'raw_rois_annotated.png',
        'limitations': ['Single recorded image, not eight new consecutive sampling frames or a measured calibration commit.',
                       'rawSamples uses current-image bbox geometry only. Captured core counts describe its persisted last owned sample with held previous-frame ROI geometry and need not match these model counts.',
                       'Same-frame ROIs do not validate previous-frame ROI stability, inter-frame colour stability or permission cancellation.',
                       'No white-balance/exposure freeze or camera register readback was performed.',
                       'Geometry is in native pixels; lux, colour temperature, paper coverage and minimum physical stroke width are not measured here.',
                       'A scaled preview adds no optical information. Boundary contact remains explicitly recorded.'],
    }
    (outputPath / 'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='echo7 capture result.json')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = sceneMeasurement(args.capture, args.out)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'FAIL', 'reason': str(error)}))
        return 1
    print(json.dumps({'status': result['status'], 'evidenceLevel': result['evidenceLevel'],
                      'frameId': result['frameId'], 'configVersion': result['configVersion'],
                      'samples': {key: result['rawSamples'][key]['sampleCount'] for key in ('red', 'blue')},
                      'singleFrameShadowPrediction': result['singleFrameShadowPrediction'],
                      'output': str(args.out)}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
