"""Export the real duplicate-sign capacity counterexample for RTL replay.

The image is native camera RGB, not a scene-manifest answer. An independent
whole-image flood fill supplies geometry; the row-graph model checks capacity.
The original FPGA failure remains immutable in the retained input index.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from analyse_capture import cleanup
from candidates_model import FIELDS
from candidates_reclaimed_model import candidates_reclaimed, usable_candidate_size
from vision_reference import colourMask, horizontalRunSupport


def floodFill(mask):
    """Four-connected geometry oracle without streaming labels or slot order."""
    height, width = mask.shape
    seen = np.zeros(mask.shape, dtype=bool)
    found = {1: [], 2: []}
    for y in range(height):
        for x in range(width):
            colour = int(mask[y, x])
            if not colour or seen[y, x]:
                continue
            pending = deque([(x, y)])
            seen[y, x] = True
            xMin = xMax = x
            yMin = yMax = y
            area = 0
            while pending:
                px, py = pending.popleft()
                area += 1
                xMin, xMax = min(xMin, px), max(xMax, px)
                yMin, yMax = min(yMin, py), max(yMax, py)
                for nx, ny in ((px-1, py), (px+1, py), (px, py-1), (px, py+1)):
                    if 0 <= nx < width and 0 <= ny < height and not seen[ny, nx] and mask[ny, nx] == colour:
                        seen[ny, nx] = True
                        pending.append((nx, ny))
            if area >= 32 and usable_candidate_size(xMax-xMin+1, yMax-yMin+1, colour):
                found[colour].append(dict(valid=1, xmin=xMin, xmax=xMax,
                    ymin=yMin, ymax=yMax, area=area, cx=(xMin+xMax)//2, cy=(yMin+yMax)//2))
    for colour in found:
        found[colour].sort(key=lambda b: tuple(b[k] for k in ('ymin', 'xmin', 'ymax', 'xmax', 'area')))
    return found


def export(output):
    source = Path(__file__).resolve().parents[2] / 'tests/fixtures/camera/frame56554'
    index = json.loads((source / 'index.json').read_text(encoding='utf-8'))
    imagePath = source / 'frame.png'
    if hashlib.sha256(imagePath.read_bytes()).hexdigest() != index['files']['frame.png']:
        raise ValueError('retained real capacity input changed')
    raw = colourMask(Image.open(imagePath), index['redMinimum'], index['blueMinimum'], colourAlgorithm=2)
    mask = cleanup(horizontalRunSupport(np.array(raw).reshape(240, 320)))
    expected = floodFill(mask)
    bounded = candidates_reclaimed(mask.tolist(), cap=16, active_capacity=15, prune_unusable=True)
    historical = candidates_reclaimed(mask.tolist(), cap=8, active_capacity=12, prune_unusable=True)
    assert len(expected[1]) == 2 and len(expected[2]) == 9
    assert not bounded['overflow'] and bounded['red'] == expected[1] and bounded['blue'] == expected[2]
    assert historical['blue_output_overflow'] and not historical['blue_active_overflow']
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'completed16_mask.hex').write_text(''.join(f'{int(p):x}\n' for p in mask.flat), encoding='ascii')
    words = [len(expected[1]), len(expected[2])]
    for colour in (1, 2):
        for slot in range(16):
            box = expected[colour][slot] if slot < len(expected[colour]) else {}
            words.extend(box.get(field, 0) for field in FIELDS)
    (output / 'completed16_expected.hex').write_text(''.join(f'{word:08x}\n' for word in words), encoding='ascii')
    (output / 'completed16_manifest.json').write_text(json.dumps(dict(input=index,
        inputPath=source.relative_to(Path(__file__).resolve().parents[2]).as_posix(),
        geometryOracle='independent whole-image four-connected BFS',
        bounded=bounded, historical=historical), indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', '--out', required=True, type=Path)
    export(parser.parse_args().output_dir)
