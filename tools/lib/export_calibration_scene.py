#!/usr/bin/env python3
"""Export a hash-bound recorded native PNG as post-capture RGB565 stimulus.

This is one retained camera acquisition, repeated only by the RTL testbench.
No marker boxes, quads or identity decisions enter the simulated pixel stream.
It does not reconstruct the OV7670 byte timing or assert new camera evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]


def exportScene(fixture,out):
    fixture=Path(fixture).resolve();out=Path(out).resolve()
    indexPath=fixture/'index.json';imagePath=fixture/'frame.png'
    index=json.loads(indexPath.read_text(encoding='utf8'))
    imageHash=hashlib.sha256(imagePath.read_bytes()).hexdigest()
    if index.get('files',{}).get('frame.png')!=imageHash:
        raise ValueError('Recorded PNG does not match its retained acquisition index')
    if index.get('inputSource')!='RECORDED_CAMERA':
        raise ValueError('This exporter requires explicitly recorded camera provenance')
    image=Image.open(imagePath).convert('RGB')
    if image.size!=(320,240):raise ValueError('Expected untransformed native320x240 PNG')
    rgb=list(image.get_flattened_data()if hasattr(image,'get_flattened_data')else image.getdata())
    words=[((r>>3)<<11)|((g>>2)<<5)|(b>>3)for r,g,b in rgb]
    decoded=[(((p>>11)<<3)|(p>>13),(((p>>5)&63)<<2)|((p>>9)&3),((p&31)<<3)|((p>>2)&7))for p in words]
    errors=[abs(a-b)for original,reconstructed in zip(rgb,decoded)for a,b in zip(original,reconstructed)]
    out.mkdir(parents=True,exist_ok=True)
    scenePath=out/'calibration_scene_rgb565.hex'
    scenePath.write_text(''.join(f'{word:04x}\n'for word in words),encoding='ascii')
    manifest={'schema':'ECHO7_CALIBRATION_RECORDED_SCENE_1','inputSource':'ONE_RECORDED_CAMERA_FRAME_REPEATED_IN_RTL',
        'fixture':str(fixture),'sourcePngSha256':imageHash,'sourceIndexSha256':hashlib.sha256(indexPath.read_bytes()).hexdigest(),
        'sourceFrameId':index['frameId'],'sourceBuildId':index['buildId'],'sourceConfigVersion':index['configVersion'],
        'capturedProfile':{name:index[name]for name in ('readerAlgorithm','colourAlgorithm','redMinimum','blueMinimum','whiteMinimum','whiteMaxSpread','orientationProfile','bypassPerspective')},
        'runtimeStimulus':'RGB565 pixels only, row-major native320x240; no candidate, label, ROI or success injection.',
        'runtimeProfile':'Core reset defaults, followed only by actual RTL automatic calibration; recorded profile above is provenance, not a forced runtime configuration.',
        'sceneFile':scenePath.name,'sceneSha256':hashlib.sha256(scenePath.read_bytes()).hexdigest(),
        'width':320,'height':240,'pixelCount':len(words),'pngTo565MaximumChannelDifference':max(errors),
        'pngTo565ChangedChannels':sum(error!=0 for error in errors),
        'limitations':['Post-capture interface replay does not verify OV7670 pins, JTAG, live acquisition or VGA.',
            'Repeated replay frames are deterministic stimuli from one acquisition, not independent camera observations.',
            'The recorded profile is historical; current RTL algorithm/automatic thresholds are separately source-bound by the runner.']}
    (out/'calibration_scene_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',type=Path,default=ROOT/'tests/fixtures/camera/frame15078')
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=exportScene(args.fixture,args.out)
    print(json.dumps({'status':'PASS','level':'VECTOR_GENERATION','sceneSha256':result['sceneSha256'],'sourceFrameId':result['sourceFrameId'],'pixels':result['pixelCount']}))


if __name__=='__main__':main()
