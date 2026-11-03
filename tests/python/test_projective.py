#!/usr/bin/env python3
import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""Independent warped artwork, counterfactual and recorded-camera model tests."""
from pathlib import Path
import json
import hashlib
import tempfile
import unittest

import numpy as np
from PIL import Image,ImageDraw
from projective_reference import recogniseProjective,whiteProfileFor,whitePixelsFor
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


def recordedFrames():
    """Six actual acquisitions; all are now known regression/tuning inputs."""
    index=json.loads((root/'tests/fixtures/camera/reader_algorithm2.json').read_text())
    for record in index['records']:yield record['frameId'],root/record['image']


def nativeAnchorCases():
    for name,mode in [('two_valid_anchor_components','two'),('one_anchor_and_one_speck','speck'),
                      ('native_anchor_label_stress','stress'),('sequential_small_components_retire','serial')]:
        image=Image.new('RGB',(320,240),'white');card=singleMarker('BC',size=(72,81));draw=ImageDraw.Draw(card)
        if mode=='two':draw.rectangle((12,5,14,7),fill='white')
        elif mode=='speck':draw.point((13,6),fill='white')
        elif mode=='serial':
            for y in range(1,18,2):draw.point((17,y),fill='white')
        else:
            draw.rectangle((0,0,20,17),fill='#0057B8')
            for x in range(2,20,2):draw.line((x,2,x,12),fill='white',width=1)
        image.paste(card,(100,60))
        yield name,image,0,[('blue',1)] if mode in ('speck','serial') else []


def algorithm2Cases():
    """Immutable historical 75-case ordering for explicit reader-2 replay."""
    full=[('blue',i) for i in range(1,7)]+[('red',1),('red',2)]
    for frameId,path in recordedFrames():
        with Image.open(path) as sourceImage:image=sourceImage.convert('RGB')
        yield f'real_frame{frameId}',image,0,full,'RECORDED_OV7670_STATIONARY_BASELINE'
    for name,image,orientation,expected in warpedCases():yield name,image,orientation,expected,'SYNTHETIC_INDEPENDENT_PERSPECTIVE'
    from export_vision_vectors import cases
    for index,(name,image,orientation) in enumerate(cases()):
        expected=full if index<3 else ([('blue',2)] if name.startswith('orientation_') else [])
        yield name,image,orientation,expected,'SYNTHETIC_PDF_OR_PIXEL_COUNTERFACTUAL'
    original=Image.open(root/'tests/fixtures/camera/frame47630/frame.png').convert('RGB')
    for name,roi,bay in [('erase_anchor2',(211,30,214,36),2),('erase_anchor4',(210,98,214,104),4),
                         ('erase_anchor6',(209,168,213,173),6),('erase_C6',(229,195,233,209),6)]:
        image=original.copy();ImageDraw.Draw(image).rectangle(roi,fill=(16,24,57))
        yield name,image,0,[item for item in full if item!=('blue',bay)],'RECORDED_PIXEL_COUNTERFACTUAL'
    yield 'whole_real_wrong_orientation',original.transpose(Image.Transpose.ROTATE_180),0,[],'RECORDED_PIXEL_COUNTERFACTUAL'
    yield 'whole_real_correct_orientation2',original.transpose(Image.Transpose.ROTATE_180),2,full,'RECORDED_PIXEL_COUNTERFACTUAL'
    for name,image,orientation,expected in nativeAnchorCases():yield name,image,orientation,expected,'SYNTHETIC_NATIVE_ANCHOR_COUNTERFACTUAL'


def algorithm3Cases():
    """Append current real pixels and labelled edits; never replace old inputs."""
    yield from algorithm2Cases()
    index=json.loads((root/'tests/fixtures/camera/reader_algorithm3.json').read_text())
    full=[('blue',i) for i in range(1,7)]+[('red',1),('red',2)]
    for record in index['records']:
        imagePath=root/record['image']
        if hashlib.sha256(imagePath.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError(f"Recorded algorithm-3 input changed: {imagePath}")
        with Image.open(imagePath) as sourceImage:image=sourceImage.convert('RGB')
        yield f"real_frame{record['frameId']}",image,0,full,record['source']
        if record['frameId']==225:
            erased=image.copy();ImageDraw.Draw(erased).rectangle((271,183,274,195),fill=(16,24,57))
            yield 'frame225_C_erased',erased,0,[item for item in full if item!=('blue',6)],'RECORDED_PIXEL_COUNTERFACTUAL'
            yield 'frame225_wrong_orientation',image.transpose(Image.Transpose.ROTATE_180),0,[],'RECORDED_PIXEL_COUNTERFACTUAL'


def algorithm4Cases():
    """Preserve all 78 historical vectors, then append lighting counterexamples.

    Recorded indices bind immutable PNG hashes. The edited C-stroke cases are
    explicitly pixel counterfactuals; their expected labels never enter runtime.
    """
    yield from algorithm3Cases()
    index=json.loads((root/'tests/fixtures/camera/reader_algorithm4.json').read_text())
    full=[('blue',i) for i in range(1,7)]+[('red',1),('red',2)]
    for record in index['records']:
        imagePath=root/record['image']
        if hashlib.sha256(imagePath.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError(f"Recorded algorithm-4 input changed: {imagePath}")
        with Image.open(imagePath) as sourceImage:image=sourceImage.convert('RGB')
        yield f"real_frame{record['frameId']}",image,0,full,record['source']
        erased=image.copy();ImageDraw.Draw(erased).rectangle((269,185,277,202),fill=(16,16,41))
        yield f"frame{record['frameId']}_C_erased",erased,0,[item for item in full if item!=('blue',6)],'RECORDED_PIXEL_COUNTERFACTUAL'
        yield f"frame{record['frameId']}_wrong_orientation",image.transpose(Image.Transpose.ROTATE_180),0,[],'RECORDED_PIXEL_COUNTERFACTUAL'


class ProjectiveTests(unittest.TestCase):
    def test_named_replay_bindings_survive_reordering(self):
        from export_projective_vectors import namedFixtureBindings,RECORDED_SOURCE
        vectors=list(algorithm2Cases())
        # This is the exact former hardcoded recorded index. It is an intentional
        # overflowing synthetic negative, so rejecting its frame was correct.
        oldName,oldImage,_,_,oldSource=next(case for case in vectors if case[0]=='red_rejected_3_4_5_6')
        self.assertEqual(oldName,'red_rejected_3_4_5_6')
        self.assertNotEqual(oldSource,RECORDED_SOURCE)
        self.assertTrue(recogniseProjective(oldImage,readerAlgorithm=2)['overflow'])
        cases=[{'index':index,'name':name,'inputSource':source,'candidateOverflow':False}
               for index,(name,_,_,_,source) in enumerate(vectors)]
        original=namedFixtureBindings(cases,readerAlgorithm=2)
        reordered=[dict(case,index=index) for index,case in enumerate(reversed(cases))]
        moved=namedFixtureBindings(reordered,readerAlgorithm=2)
        self.assertEqual([(r['alias'],r['caseName'],r.get('sourcePngSha256')) for r in original],
                         [(r['alias'],r['caseName'],r.get('sourcePngSha256')) for r in moved])
        self.assertNotEqual([r['index'] for r in original],[r['index'] for r in moved])
        self.assertEqual(len([r for r in original if r['inputSource']==RECORDED_SOURCE]),6)
        selected=next(r for r in original if r['alias']=='recorded_frame13675')
        self.assertEqual(selected['sourcePngSha256'],'3206193dde4003b093b178af412645793c4bc2ce3118a12b535a35110df0e9b8')
        self.assertEqual([r['caseName'] for r in original if r['alias'].startswith('continuous_')],
                         ['pdf_full_page','counterfactual_swapped'])
        poisoned=[dict(case,inputSource='SYNTHETIC_PIXELS') if case['name']=='real_frame13675' else case for case in cases]
        with self.assertRaisesRegex(ValueError,'mislabelled'):namedFixtureBindings(poisoned,readerAlgorithm=2)
        with self.assertRaisesRegex(ValueError,'Duplicate'):namedFixtureBindings(cases+[cases[0]],readerAlgorithm=2)

    def test_named_alias_hashes_and_recorded_pixel_mismatch(self):
        from export_projective_vectors import namedFixtureBindings,writeNamedAliases,rgb565Text
        from vision_reference import quantise565
        vectors=list(algorithm2Cases())
        cases=[{'index':index,'name':name,'inputSource':source,'candidateOverflow':False}
               for index,(name,_,_,_,source) in enumerate(vectors)]
        bindings=namedFixtureBindings(cases,readerAlgorithm=2)
        # Isolated transport fixture: classification is tested independently;
        # these short candidate/expected files check exact alias copying only.
        with tempfile.TemporaryDirectory() as temporary:
            destination=Path(temporary)
            for binding in bindings:
                index=binding['index'];prefix=destination/f'projective_{index}'
                Path(str(prefix)+'_rgb565.hex').write_text(rgb565Text(quantise565(vectors[index][1])),encoding='ascii')
                for suffix in ('candidates','expected'):
                    Path(str(prefix)+f'_{suffix}.hex').write_text(f'{index:08x}\n',encoding='ascii')
            result=writeNamedAliases(destination,cases,readerAlgorithm=2)
            for binding in result['fixtures']:
                for exported in binding['files'].values():
                    self.assertEqual((destination/exported['path']).read_bytes(),(destination/exported['sourcePath']).read_bytes())
                    self.assertEqual(hashlib.sha256((destination/exported['path']).read_bytes()).hexdigest(),exported['sha256'])
            self.assertNotEqual((destination/'continuous_0_rgb565.hex').read_bytes(),
                                (destination/'continuous_1_rgb565.hex').read_bytes())
            selected=next(r for r in bindings if r['alias']=='recorded_frame13675')
            negativeImage=next(case[1] for case in vectors if case[0]=='red_rejected_3_4_5_6')
            (destination/f"projective_{selected['index']}_rgb565.hex").write_text(rgb565Text(quantise565(negativeImage)),encoding='ascii')
            with self.assertRaisesRegex(ValueError,'do not match source PNG'):writeNamedAliases(destination,cases,readerAlgorithm=2)

    def test_warped_digits_rejection_and_orientation(self):
        out.mkdir(parents=True,exist_ok=True)
        records=[]
        for name,image,orientation,expected in warpedCases():
            with self.subTest(name=name):
                result=recogniseProjective(image,orientation=orientation,inputSource='SYNTHETIC_INDEPENDENT_PERSPECTIVE',readerAlgorithm=4)
                actual=sorted((marker['colour'],marker['digit']) for marker in result['markers'] if marker['accepted'])
                records.append({'case':name,'actual':actual,'expected':expected,'pass':actual==expected,
                                'markers':result['markers']})
                self.assertEqual(actual,expected)
        (out/'warp_results.json').write_text(json.dumps({'layer':'MODEL','cases':records},indent=2)+'\n',encoding='utf-8')

    def test_original_full_page_and_counterfactual(self):
        from export_vision_vectors import cases
        for name,image,orientation in list(cases())[:3]:
            with self.subTest(name=name):
                result=recogniseProjective(image,orientation=orientation,inputSource='SYNTHETIC_PDF_COUNTERFACTUAL',readerAlgorithm=4)
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])
                if name=='counterfactual_swapped':
                    top=sorted((m for m in result['markers'] if m['accepted'] and m['colour']=='blue' and m['bbox'][1]<50),key=lambda m:m['bbox'][0])
                    self.assertEqual([m['digit'] for m in top],[2,1])

    def test_recorded_camera_frames(self):
        for frameId,path in recordedFrames():
            with self.subTest(frameId=frameId):
                self.assertTrue(path.is_file(),'Recorded input must be supplied explicitly')
                result=recogniseProjective(Image.open(path),inputSource='RECORDED_OV7670_PART_A',readerAlgorithm=4)
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])
                for marker in result['markers']:
                    if marker['accepted'] and min(marker['edgeSquaredHalfPixelUnits'])<6400:
                        self.assertLessEqual(marker['quality'],192,'Short-edge quality cap applies to geometry, not marker colour')

    def test_calibrated_hsv_and_historical_ratio(self):
        for frameId in (13139,13511,13675):
            image=Image.open(root/f'tests/fixtures/camera/frame{frameId}/frame.png')
            for algorithm,redMin,blueMin in ((0,64,32),(1,37,30)):
                result=recogniseProjective(image,redMin=redMin,blueMin=blueMin,colourAlgorithm=algorithm,
                    readerAlgorithm=1 if algorithm==0 else 2,inputSource='RECORDED_OV7670_PART_A')
                self.assertFalse(result['overflow'])
                self.assertEqual(sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                                 [('blue',i) for i in range(1,7)]+[('red',1),('red',2)])

    def test_algorithm1_history_and_algorithm2_white_semantics(self):
        for frameId,path in recordedFrames():
            result=recogniseProjective(Image.open(path),readerAlgorithm=1)
            expectedCount=5 if frameId==47630 else 4 if frameId==2462 else 8
            self.assertEqual(sum(m['accepted'] for m in result['markers']),expectedCount)
            self.assertEqual(result['whiteProfile']['mode'],'MINIMUM_RGB_CHANNEL')
            self.assertEqual(result['whiteProfile']['minimum'],112)
        profile=whiteProfileFor(2)
        self.assertEqual(profile['mode'],'WEIGHTED_LUMA')
        self.assertEqual(profile['sumMinimum'],384)
        # Actual dim C-stroke RGB and adjacent blue foreground; this verifies
        # signed widened arithmetic, not a mirror of an implementation formula.
        self.assertEqual(whitePixelsFor(np.array([[[99,109,140],[16,24,33]]],dtype=np.uint8),profile).tolist(),[[True,False]])
        with self.assertRaises(ValueError):whiteProfileFor(2,112,64)

    def test_native_anchor_ambiguity_overflow_and_retirement(self):
        for name,image,orientation,expected in nativeAnchorCases():
            result=recogniseProjective(image,orientation=orientation,readerAlgorithm=4)
            actual=sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
            self.assertEqual(actual,expected,name)
            anchor=next(m['windowScores']['anchor'] for m in result['markers'] if 'anchor' in m['windowScores'])
            if name=='two_valid_anchor_components':self.assertTrue(anchor['ambiguous'])
            elif name=='native_anchor_label_stress':self.assertTrue(anchor['overflow'])
            elif name=='sequential_small_components_retire':
                self.assertGreater(anchor['completedComponents'],8)
                self.assertFalse(anchor['overflow'])
                self.assertLessEqual(anchor['peakActiveHandles'],8)

    def test_new_real_pixel_counterfactuals(self):
        records=[]
        for name,image,orientation,expected,source in algorithm2Cases():
            if source!='RECORDED_PIXEL_COUNTERFACTUAL':continue
            result=recogniseProjective(image,orientation=orientation,inputSource=source,readerAlgorithm=2)
            actual=sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
            self.assertEqual(actual,expected,name)
            self.assertFalse(result['overflow'])
            records.append({'case':name,'expected':expected,'actual':actual,'readerAlgorithm':2})
        out.mkdir(parents=True,exist_ok=True)
        (out/'recorded_counterfactual_results.json').write_text(json.dumps({'layer':'MODEL','cases':records},indent=2)+'\n',encoding='utf-8')

    def test_algorithm3_all_inputs_and_historical_order(self):
        historical=list(algorithm2Cases());current=list(algorithm3Cases())
        self.assertEqual(len(historical),75)
        self.assertEqual(len(current),78)
        # Appended actual inputs may not silently change the numbered legacy
        # suite. The exporter also compares preserved algorithm-2 hex bytes.
        for old,new in zip(historical,current):
            self.assertEqual(old[0],new[0]);self.assertEqual(old[1].tobytes(),new[1].tobytes())
            self.assertEqual(old[2:],new[2:])
        records=[]
        for name,image,orientation,expected,source in current:
            with self.subTest(case=name):
                result=recogniseProjective(image,orientation=orientation,inputSource=source,readerAlgorithm=3)
                actual=sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
                self.assertEqual(actual,expected)
                self.assertEqual(result['readerAlgorithm'],3)
                records.append({'case':name,'expected':expected,'actual':actual,'readerAlgorithm':3})
        out.mkdir(parents=True,exist_ok=True)
        (out/'algorithm3_results.json').write_text(json.dumps({'layer':'MODEL','cases':records},indent=2)+'\n',encoding='utf-8')

    def test_algorithm3_named_real_input_and_incompatible_colour_rejected(self):
        from export_projective_vectors import namedFixtureBindings
        vectors=list(algorithm3Cases())
        cases=[{'index':index,'name':name,'inputSource':source,'candidateOverflow':False}
               for index,(name,_,_,_,source) in enumerate(vectors)]
        bindings=namedFixtureBindings(cases,readerAlgorithm=3)
        current=next(row for row in bindings if row['alias']=='recorded_frame225')
        self.assertEqual(current['inputSource'],'RECORDED_OV7670_MEMBER_B')
        self.assertEqual(current['index'],75)
        with self.assertRaisesRegex(ValueError,'HSV'):
            recogniseProjective(Image.new('RGB',(320,240),'white'),colourAlgorithm=0,readerAlgorithm=3)

    def test_algorithm3_preserves_strict_anchor_and_old_reader2_counterexample(self):
        image=Image.open(root/'tests/fixtures/camera/frame225/frame.png').convert('RGB')
        old=recogniseProjective(image,readerAlgorithm=2)
        current=recogniseProjective(image,readerAlgorithm=3)
        self.assertEqual(sum(m['accepted'] for m in old['markers']),7)
        self.assertEqual(sum(m['accepted'] for m in current['markers']),8)
        marker=next(m for m in current['markers'] if m['accepted'] and m['colour']=='blue' and m['digit']==6)
        self.assertEqual(marker['windowScores']['C']['white'],6)
        self.assertEqual(marker['quality'],192)
        legacyImage=Image.open(root/'tests/fixtures/camera/frame47630/frame.png').convert('RGB')
        old=recogniseProjective(legacyImage,readerAlgorithm=2)
        current=recogniseProjective(legacyImage,readerAlgorithm=3)
        for oldMarker in old['markers']:
            if not oldMarker['accepted']:continue
            newMarker=next(m for m in current['markers'] if m['bbox']==oldMarker['bbox'])
            self.assertEqual(newMarker['windowScores']['anchor'],oldMarker['windowScores']['anchor'])
            self.assertTrue(newMarker['accepted'])

    def test_algorithm4_all_inputs_and_historical_order(self):
        historical=list(algorithm3Cases());current=list(algorithm4Cases())
        self.assertEqual(len(current),84)
        for old,new in zip(historical,current):
            self.assertEqual(old[0],new[0]);self.assertEqual(old[1].tobytes(),new[1].tobytes())
            self.assertEqual(old[2:],new[2:])
        records=[]
        for name,image,orientation,expected,source in current:
            with self.subTest(case=name):
                result=recogniseProjective(image,orientation=orientation,inputSource=source,readerAlgorithm=4)
                actual=sorted((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
                self.assertEqual(actual,expected)
                self.assertEqual(result['readerAlgorithm'],4)
                self.assertEqual(result['colourAlgorithm'],2)
                self.assertEqual(result['colourProfile']['blueMin'],20)
                records.append({'case':name,'expected':expected,'actual':actual,'readerAlgorithm':4,
                                'overflow':result['overflow'],'markers':result['markers']})
        out.mkdir(parents=True,exist_ok=True)
        (out/'algorithm4_results.json').write_text(json.dumps({'layer':'MODEL','cases':records},indent=2)+'\n',encoding='utf-8')

    def test_algorithm4_source_bound_fixtures_and_historical_isolation(self):
        from export_projective_vectors import namedFixtureBindings
        vectors=list(algorithm4Cases())
        cases=[{'index':index,'name':name,'inputSource':source,'candidateOverflow':False}
               for index,(name,_,_,_,source) in enumerate(vectors)]
        bindings=namedFixtureBindings(cases,readerAlgorithm=4)
        for frameId,index in ((31285,78),(10699,81)):
            fixture=next(row for row in bindings if row['alias']==f'recorded_frame{frameId}')
            self.assertEqual(fixture['index'],index)
            self.assertEqual(fixture['inputSource'],'RECORDED_OV7670_MEMBER_B')
            image=Image.open(root/fixture['sourcePng'])
            old=recogniseProjective(image,redMin=32,blueMin=28,readerAlgorithm=3)
            self.assertLess(sum(m['accepted'] for m in old['markers']),8)
        for colour in (0,1):
            with self.assertRaisesRegex(ValueError,'HSV'):
                recogniseProjective(Image.new('RGB',(320,240),'white'),colourAlgorithm=colour,readerAlgorithm=4)


if __name__=='__main__':unittest.main(verbosity=2)
