"""Measure retained camera pixels; this script never changes production rules.

Run from the repository root with Python. Counts in each stroke window are
distinct native RGB565 pixel addresses, not the number of upsampled grid cells
or an estimate of physical stroke thickness. Expected scene labels do not enter
the recognition call. Original capture failures remain unchanged.
"""
from pathlib import Path
from collections import deque
import argparse
import hashlib
import json
import math
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'tools/lib'))
import numpy as np
from PIL import Image
from projective_reference import gridAddresses, recogniseProjective, whitePixelsFor, whiteProfileFor
from vision_reference import quantise565


def componentBudget(mask, strictWhite, roi):
    """Independent four-connected counts, including rejected thin components.

    Unlike nativeAnchorScores this does not apply anchor size or closedness
    acceptance. It exposes why the current rule rejects a measured component.
    """
    x0,y0,x1,y1 = roi
    patch = mask[y0:y1+1,x0:x1+1]
    seen = np.zeros_like(patch)
    components = []
    for py,px in np.argwhere(patch):
        if seen[py,px]:
            continue
        queue = deque([(int(py),int(px))])
        seen[py,px] = True
        points = []
        while queue:
            y,x = queue.popleft()
            points.append((y,x))
            for yy,xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
                if (0<=yy<patch.shape[0] and 0<=xx<patch.shape[1]
                        and patch[yy,xx] and not seen[yy,xx]):
                    seen[yy,xx] = True
                    queue.append((yy,xx))
        seedCount = sum(bool(strictWhite[y0+y,x0+x]) for y,x in points)
        if seedCount < 3:
            continue
        ys,xs = zip(*points)
        components.append({'nativeBbox':[x0+min(xs),y0+min(ys),x0+max(xs),y0+max(ys)],
            'width':max(xs)-min(xs)+1, 'height':max(ys)-min(ys)+1,
            'pixels':len(points), 'strictSeedPixels':seedCount,
            'closedInRoi':min(xs)>0 and min(ys)>0 and
                max(xs)<patch.shape[1]-1 and max(ys)<patch.shape[0]-1})
    return components


def measureRecord(directory):
    metadata = json.loads((directory / 'index.json').read_text(encoding='utf-8'))
    imagePath = directory / 'frame.png'
    imageHash = hashlib.sha256(imagePath.read_bytes()).hexdigest()
    if imageHash != metadata['files']['frame.png']:
        raise ValueError(f'Retained camera image hash mismatch: {imagePath}')
    # The compact fixture profile was checked against its original acquisition
    # before migration. Its source capture SHA is preserved; replay needs no
    # historical execution log or complete capture-result document.
    hardwareSchema = metadata['hardwareDebugSchemaVersion']
    image = quantise565(Image.open(imagePath).convert('RGB'))
    strictWhite = whitePixelsFor(np.asarray(image), whiteProfileFor(5), anchor=True)
    strokeWhite = whitePixelsFor(np.asarray(image), whiteProfileFor(5))
    result = recogniseProjective(image, readerAlgorithm=5, colourAlgorithm=2,
        redMin=metadata['redMinimum'], blueMin=metadata['blueMinimum'],
        activeCapacity=15, outputCapacity=16, inputSource='RECORDED_CAMERA')
    # Inclusive windows used by the production projection scorer. Counting
    # unique source addresses avoids treating normalisation repeats as data.
    windows = {'A': (12,4,19,8), 'B': (21,10,24,16), 'C': (21,23,24,29),
               'D': (12,31,19,35), 'E': (7,23,10,29), 'F': (7,10,10,16),
               'G': (12,18,19,21)}
    markers = []
    for marker in result['markers']:
        x0,y0,x1,y1 = marker['bbox']
        measured = {key: marker[key] for key in
            ('colour','bbox','accepted','digit','quality','reasonName','orientationProfile')}
        measured.update(nativeBboxWidth=x1-x0+1, nativeBboxHeight=y1-y0+1,
                        gridSampled=marker.get('gridSampled',False))
        hypotheses = marker.get('orientationHypotheses',[])
        measured['anchorHypotheses'] = [
            {'localCornerOffset': entry['orientation'], 'accepted': entry['anchorGood'],
             'anchor': entry['anchor'],
             'strictComponents': componentBudget(strictWhite, strictWhite, entry['anchor']['roi']),
             'weakSupportedComponents': componentBudget(strokeWhite, strictWhite, entry['anchor']['roi'])}
            for entry in hypotheses]
        if marker.get('edgeSquaredHalfPixelUnits'):
            measured['minimumQuadEdgePixels'] = min(math.sqrt(value)/2
                for value in marker['edgeSquaredHalfPixelUnits'])
        if marker.get('gridSampled'):
            addresses = np.asarray(gridAddresses(marker['coefficients'])).reshape(40,32,2)
            measured['gridCellCount'] = 1280
            measured['uniqueNativeGridPixels'] = len(set(map(tuple, addresses.reshape(-1,2))))
            measured['anchor'] = marker['windowScores']['anchor']
            measured['detectedSegments'] = marker['segments']
            measured['strokeWindows'] = {}
            for name,(left,top,right,bottom) in windows.items():
                sourcePixels = set(map(tuple, addresses[top:bottom+1,left:right+1].reshape(-1,2)))
                score = marker['windowScores'][name]
                measured['strokeWindows'][name] = {
                    'present': name in marker['segments'],
                    'projectedCoveredBins': score['white'],
                    'projectedTotalBins': score['samples'],
                    'uniqueNativeSamples': len(sourcePixels),
                    'uniqueNativeWhiteSamples': sum(bool(strokeWhite[y,x]) for x,y in sourcePixels),
                    'uniqueNativeStrictWhiteSamples': sum(bool(strictWhite[y,x]) for x,y in sourcePixels)}
        markers.append(measured)
    return {'image': imagePath.relative_to(root).as_posix(), 'imageSha256': imageHash,
        'indexSha256': hashlib.sha256((directory/'index.json').read_bytes()).hexdigest(),
        'sourceBuildId': metadata['buildId'], 'hardwareDebugSchemaVersion': hardwareSchema,
        'sourceFrameId': metadata['frameId'], 'sourceConfigVersion': metadata['configVersion'],
        'originalCaptureStatus': metadata['originalResult'],
        'replaySchema': result['schema'], 'readerAlgorithm': 5, 'colourAlgorithm': 2,
        'redMinimum': metadata['redMinimum'], 'blueMinimum': metadata['blueMinimum'],
        'activeCapacity': 15, 'outputCapacity': 16, 'candidateOverflow': result['overflow'],
        'acceptedCount': sum(marker['accepted'] for marker in markers),
        'markers': markers}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=root/'build/member_b/orientation_pixel_budget.json')
    args = parser.parse_args()
    fixtures = root / 'tests/fixtures/camera'
    records = [measureRecord(fixtures/name) for name in ('frame56554','frame16351')]
    sources = ['tools/lib/projective_reference.py','tools/lib/vision_reference.py',
               'tools/lib/candidates_reclaimed_model.py',
               'tools/lib/orientation_pixel_budget.py']
    result = {'schema': 'member-b-orientation-pixel-budget-v1',
        'evidenceLevel': 'MODEL_ON_RETAINED_CAMERA_PIXELS', 'productionRulesModified': False,
        'measurement': 'Distinct native pixel addresses in canonical stroke windows; not physical stroke thickness',
        'sourceSha256': {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in sources},
        'records': records}
    destination = args.out
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    for record in records:
        print(f"frame={record['sourceFrameId']} accepted={record['acceptedCount']} hardwareSchema={record['hardwareDebugSchemaVersion']} replaySchema={record['replaySchema']}")
        for marker in record['markers']:
            anchor = marker.get('anchor',{})
            active = [f"{key}:{value['uniqueNativeWhiteSamples']}/{value['uniqueNativeSamples']}" for key,value in marker.get('strokeWindows',{}).items() if value['present']]
            print(marker['colour'],marker['digit'],marker['bbox'],
                  f"anchor={anchor.get('columns',0)}x{anchor.get('rows',0)}/{anchor.get('white',0)}",
                  f"samples={marker.get('uniqueNativeGridPixels',0)}",','.join(active),marker['reasonName'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
