#!/usr/bin/env python3
import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""Independent warped artwork, counterfactual and recorded-camera model tests."""
from pathlib import Path
import json
import unittest

import numpy as np
from PIL import Image,ImageDraw
from projective_reference import recogniseProjective
from test_vision import singleMarker

root=Path(__file__).resolve().parents[2]
out=root/'build/member_b/projective_tests'
POSES={
    'front':[(30,30),(84,30),(84,91),(30,91)],
    'horizontal_perspective':[(120,30),(153,45),(157,109),(116,115)],
    'opposite_perspective':[(60,60),(109,39),(112,120),(67,111)],
    'vertical_perspective':[(170,30),(229,34),(215,83),(180,80)],
    'roll_and_perspective':[(100,25),(151,39),(135,103),(82,88)],
}
PATTERNS={1:'BC',2:'ABDEG',3:'ABCDG',4:'BCFG',5:'ACDFG',6:'ACDEFG',0:'ABCDEF',7:'ABC',8:'ABCDEFG',9:'ABCDFG'}


def warpedCard(pattern,quad,colour='blue',anchor=True):
    source=singleMarker(pattern,colour,anchor,size=(256,288))
    # Independent eight-equation fit and Pillow inverse perspective resampler;
    # this does not call the recogniser's integer mapping/corner implementation.
    matrix=[];rhs=[]
    for (sx,sy),(dx,dy) in zip([(0,0),(256,0),(256,288),(0,288)],quad):
        matrix.extend([[sx,sy,1,0,0,0,-dx*sx,-dx*sy],[0,0,0,sx,sy,1,-dy*sx,-dy*sy]])
        rhs.extend([dx,dy])
    forward=np.append(np.linalg.solve(np.array(matrix),np.array(rhs)),1).reshape(3,3)
    inverse=np.linalg.inv(forward);inverse/=inverse[2,2]
    return source.transform((320,240),Image.Transform.PERSPECTIVE,tuple(inverse.reshape(-1)[:8]),
                            Image.Resampling.BICUBIC,fillcolor='white')


def warpedCases():
    for pose,quad in POSES.items():
        for digit in range(1,7):yield f'{pose}_{digit}',warpedCard(PATTERNS[digit],quad),0,[('blue',digit)]
    for digit in (0,7,8,9):yield f'unknown_perspective_{digit}',warpedCard(PATTERNS[digit],POSES['horizontal_perspective']),0,[]
    yield 'no_anchor_perspective',warpedCard('BC',POSES['horizontal_perspective'],anchor=False),0,[]
    yield 'blank_perspective',warpedCard('',POSES['horizontal_perspective']),0,[]
    yield 'deleted_stroke_perspective',warpedCard('C',POSES['horizontal_perspective']),0,[]
    for orientation,operation in enumerate((None,Image.Transpose.ROTATE_270,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_90)):
        card=singleMarker('ABDEG',size=(54,61))
        if operation is not None:card=card.transpose(operation)
        image=Image.new('RGB',(320,240),'white');image.paste(card,(80,80))
        yield f'orientation_{orientation}',image,orientation,[('blue',2)]
        if orientation:yield f'wrong_orientation_{orientation}',image,0,[]


class ProjectiveTests(unittest.TestCase):
    def test_warped_digits_rejection_and_orientation(self):
        out.mkdir(parents=True,exist_ok=True)
        records=[]
        for name,image,orientation,expected in warpedCases():
            with self.subTest(name=name):
                result=recogniseProjective(image,orientation=orientation,inputSource='SYNTHETIC_INDEPENDENT_PERSPECTIVE')
                actual=sorted((marker['colour'],marker['digit']) for marker in result['markers'] if marker['accepted'])
                records.append({'case':name,'actual':actual,'expected':expected,'pass':actual==expected,
                                'markers':result['markers']})
                self.assertEqual(actual,expected)
        (out/'warp_results.json').write_text(json.dumps({'layer':'MODEL','cases':records},indent=2)+'\n',encoding='utf-8')

    def test_original_full_page_and_counterfactual(self):
        from export_vision_vectors import cases
        for name,image,orientation in list(cases())[:3]:
            with self.subTest(name=name):
                result=recogniseProjective(image,orientation=orientation,inputSource='SYNTHETIC_PDF_COUNTERFACTUAL')
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])
                if name=='counterfactual_swapped':
                    top=sorted((m for m in result['markers'] if m['accepted'] and m['colour']=='blue' and m['bbox'][1]<50),key=lambda m:m['bbox'][0])
                    self.assertEqual([m['digit'] for m in top],[2,1])

    def test_recorded_camera_frames(self):
        for frameId in (13139,13511,13675,25046):
            with self.subTest(frameId=frameId):
                path=root/(f'evidence/real_inputs/frame{frameId}.png' if frameId!=25046 else 'evidence/hsv_audit/frame25046.png')
                self.assertTrue(path.is_file(),'Recorded input must be supplied explicitly')
                result=recogniseProjective(Image.open(path),inputSource='RECORDED_OV7670_PART_A')
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])
                for marker in result['markers']:
                    if marker['accepted'] and min(marker['edgeSquaredHalfPixelUnits'])<6400:
                        self.assertLessEqual(marker['quality'],192,'Short-edge quality cap applies to geometry, not marker colour')

    def test_calibrated_hsv_and_historical_ratio(self):
        for frameId in (13139,13511,13675):
            image=Image.open(root/f'evidence/real_inputs/frame{frameId}.png')
            for algorithm,redMin,blueMin in ((0,64,32),(1,37,30)):
                result=recogniseProjective(image,redMin=redMin,blueMin=blueMin,colourAlgorithm=algorithm,inputSource='RECORDED_OV7670_PART_A')
                self.assertFalse(result['overflow'])
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])


if __name__=='__main__':unittest.main(verbosity=2)
