"""Replay a retained camera failure through independent cleanup/BFS models."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
from vision_reference import colourMask, horizontalRunSupport
from analyse_capture import cleanup
from candidates_reclaimed_model import candidates_reclaimed
from candidates_model import FIELDS


def export(output):
    source = Path(__file__).resolve().parents[2] / 'tests/fixtures/camera/frame30507'
    index = json.loads((source / 'index.json').read_text())
    imagePath = source / 'frame.png'
    if hashlib.sha256(imagePath.read_bytes()).hexdigest() != index['files']['frame.png']:
        raise ValueError('recorded capacity counterexample changed')
    raw = colourMask(Image.open(imagePath), index['redMinimum'], index['blueMinimum'], colourAlgorithm=2)
    mask = cleanup(horizontalRunSupport(np.array(raw).reshape(240, 320)))
    expected = candidates_reclaimed(mask.tolist(), prune_unusable=True, active_capacity=12)
    historical = candidates_reclaimed(mask.tolist(), prune_unusable=True)
    assert historical['red_active_overflow'] and not historical['red_output_overflow']
    assert not expected['overflow'] and expected['red_max_row_handles'] == 9
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    (output/'capacity_mask.hex').write_text(''.join(f'{int(p):x}\n' for p in mask.flat))
    words = []
    for colour in ('red', 'blue'):
        for slot in range(8):
            box = expected[colour][slot] if slot < len(expected[colour]) else {}
            words.extend(box.get(field, 0) for field in FIELDS)
    (output/'capacity_expected.hex').write_text(''.join(f'{word:08x}\n' for word in words))
    (output/'capacity_manifest.json').write_text(json.dumps({'source':index,'activeCapacity':12,
        'outputCapacity':8,'expected':expected,'historical':historical},indent=2)+'\n')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    export(parser.parse_args().out)
