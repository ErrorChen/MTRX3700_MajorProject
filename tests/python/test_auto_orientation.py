"""Independent rotated artwork for reader5; MODEL evidence, never camera input.

All digit decisions use the generated pixels. Label/angle metadata is used only
to score outputs. The 15-degree grid samples rotation behaviour; it is not proof
for every continuous pose or arbitrarily small/occluded signs.
"""
import math
import collections
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'tools/lib'),str(root/'tests/python')]
import numpy as np
from PIL import Image,ImageDraw
from test_projective import warpedCard,PATTERNS,algorithm4Cases
from test_vision import spec,singleMarker
from vision_reference import colourMask,quantise565
from projective_reference import classifyProjective,recogniseProjective,whiteProfileFor


def rotationQuad(angle,width=96,height=108):
    cosine,sine=math.cos(math.radians(angle)),math.sin(math.radians(angle))
    return [[160+cosine*x-sine*y,120+sine*x+cosine*y] for x,y in
            [(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(-width/2,height/2)]]


def rotatedMarker(pattern,angle,colour='blue',size=(96,108),anchor=True,secondAnchor=False):
    quad=rotationQuad(angle,*size)
    image=warpedCard(pattern,quad,colour,anchor)
    if secondAnchor:
        # Deliberately add an independent opposite-corner orientation anchor.
        # This is a counterfactual image, not extra expected runtime metadata.
        points=[]
        for x,y in spec['orientationAnchorPolygonNormalised']:
            u,v=1-x,1-y
            points.append((quad[0][0]+u*(quad[1][0]-quad[0][0])+v*(quad[3][0]-quad[0][0]),
                           quad[0][1]+u*(quad[1][1]-quad[0][1])+v*(quad[3][1]-quad[0][1])))
        ImageDraw.Draw(image).polygon(points,fill='white')
    return image


def isolatedResult(image,colour='blue',orientation=0,readerAlgorithm=5,bypass=False):
    image=quantise565(image)
    foreground=np.asarray(colourMask(image,48,20,colourAlgorithm=2)).reshape(240,320)!=0
    yy,xx=np.nonzero(foreground)
    candidate={'colour':colour,'area':int(foreground.sum()),
               'bbox':[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]}
    return classifyProjective(image,candidate,orientation=orientation,readerAlgorithm=readerAlgorithm,
                              colourAlgorithm=2,redMin=48,blueMin=20,bypassPerspective=bypass)


def sharedPoolImage(identities):
    """Independent same-size cards; location never supplies runtime identity."""
    image=Image.new('RGB',(320,240),'white')
    for index,(colour,digit) in enumerate(identities):
        image.paste(singleMarker(PATTERNS[digit],colour=colour,size=(48,54)),
                    (8+(index%5)*62,8+(index//5)*58))
    return image


def algorithm5Cases():
    # Preserve source names/hashes and historical vectors as inputs, while the
    # current auto-orientation oracle computes new expectations. A historical
    # wrong-global-profile input is no longer automatically a negative case.
    for name,image,orientation,expected,source in algorithm4Cases():
        yield name,image,orientation,None,source
    identities=[('blue',digit) for digit in range(1,7)]+[('red',digit) for digit in (1,2)]
    for angle in range(0,360,45):
        for colour,digit in identities:
            yield f'auto_{colour}{digit}_{angle:03d}',rotatedMarker(PATTERNS[digit],angle,colour),0,[(colour,digit)],'SYNTHETIC_TEMPLATE_ROTATION'
    for angle in range(0,360,15):
        if angle%45:
            for digit in (2,6):
                yield f'auto_dense_blue{digit}_{angle:03d}',rotatedMarker(PATTERNS[digit],angle),0,[('blue',digit)],'SYNTHETIC_TEMPLATE_ROTATION'
    for name,image in (
        ('auto_no_anchor',rotatedMarker('BC',45,anchor=False)),
        ('auto_multiple_orientation_anchors',rotatedMarker('ABDEG',45,secondAnchor=True)),
        ('auto_reflected_blue2',rotatedMarker('ABDEG',15).transpose(Image.Transpose.FLIP_LEFT_RIGHT)),
        ('auto_unknown8',rotatedMarker(PATTERNS[8],135))):
        yield name,image,0,[],'SYNTHETIC_ROTATED_PIXEL_COUNTERFACTUAL'
    recording=root/'tests/fixtures/camera/frame56554'
    metadata=json.loads((recording/'index.json').read_text(encoding='utf-8'))
    if hashlib.sha256((recording/'frame.png').read_bytes()).hexdigest()!=metadata['files']['frame.png']:
        raise ValueError('Recorded duplicate-scene PNG changed')
    yield 'recorded_duplicate_frame56554_default_profile',Image.open(recording/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_PIXELS_DEFAULT_PROFILE_REPLAY'
    recording=root/'tests/fixtures/camera/frame16351'
    metadata=json.loads((recording/'index.json').read_text(encoding='utf-8'))
    if hashlib.sha256((recording/'frame.png').read_bytes()).hexdigest()!=metadata['files']['frame.png']:
        raise ValueError('Recorded frame16351 PNG changed')
    yield 'recorded_duplicate_frame16351_default_profile',Image.open(recording/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_PIXELS_DEFAULT_PROFILE_REPLAY'
    # New real counterexamples retain their original colour2 acquisition
    # metadata. These current-source vectors explicitly replay the same pixels
    # with the selected exporter profile; no recorded result is rewritten.
    for frameId in (30158,37621):
        recording=root/f'tests/fixtures/camera/frame{frameId}'
        metadata=json.loads((recording/'index.json').read_text(encoding='utf-8'))
        if hashlib.sha256((recording/'frame.png').read_bytes()).hexdigest()!=metadata['files']['frame.png']:
            raise ValueError(f'Recorded frame{frameId} PNG changed')
        yield f'recorded_frame{frameId}_support_counterexample',Image.open(recording/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_PIXELS_DEFAULT_PROFILE_REPLAY'
    for name,identities in (
        ('shared_all_blue16',[('blue',index%6+1) for index in range(16)]),
        ('shared_red14_blue2',[('red',index%2+1) for index in range(14)]+[('blue',5),('blue',6)])):
        yield name,sharedPoolImage(identities),0,identities,'SYNTHETIC_SHARED_POOL_PIXEL_FIXTURE'
    from export_vision_vectors import cases
    original=next(image for name,image,_ in cases() if name=='pdf_full_page')
    yield 'shared_shuffled_full_page',original,0,None,'SYNTHETIC_PIXEL_INPUT_REVERSED_CANDIDATE_ORDER'


class AutomaticOrientationTests(unittest.TestCase):
    def testNativeExportIncludesRejectedHypothesisBranches(self):
        names=('two_valid_anchor_components','native_anchor_label_stress',
               'one_anchor_and_one_speck','sequential_small_components_retire')
        with tempfile.TemporaryDirectory() as directory:
            command=[sys.executable,str(root/'tools/lib/export_projective_vectors.py'),
                     '--reader-algorithm','5','--out',directory]
            for name in names:command.extend(('--case',name))
            completed=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=30)
            self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
            manifest=json.loads((Path(directory)/'anchor_manifest.json').read_text())
            words=[int(line,16) for line in (Path(directory)/'anchor_meta.hex').read_text().splitlines()]
            count=int((Path(directory)/'anchor_count.hex').read_text(),16)
            self.assertEqual(count,16,'Four independent hypotheses must be exported for each usable quad')
            self.assertEqual(len(words),20*count)
            ambiguous=[case for case in manifest['cases'] if case['ambiguous']]
            overflow=[case for case in manifest['cases'] if case['overflow']]
            self.assertEqual([(case['case'],case['orientationHypothesis']) for case in ambiguous],
                             [('two_valid_anchor_components',0)])
            self.assertEqual([(case['case'],case['orientationHypothesis']) for case in overflow],
                             [('native_anchor_label_stress',0)])
            self.assertEqual(sum(words[index*20+16] for index in range(count)),1)
            self.assertEqual(sum(words[index*20+17] for index in range(count)),1)
            self.assertGreaterEqual(manifest['coverage']['valid'],2)

    def testSharedCapacityUsesOnePoolAndExplicitHistoricalSplit(self):
        for identities in ([('blue',index%6+1) for index in range(16)],
                           [('red',index%2+1) for index in range(14)]+[('blue',5),('blue',6)]):
            result=recogniseProjective(sharedPoolImage(identities))
            self.assertEqual(result['candidatePoolMode'],'SHARED')
            self.assertEqual(result['schema'],'ECHO7_PROJECTIVE_MODEL_7')
            self.assertFalse(result['overflow'])
            self.assertEqual(collections.Counter((m['colour'],m['digit']) for m in result['markers'] if m['accepted']),
                             collections.Counter(identities))
        # Seventeen usable regions exceed total16 even when neither colour
        # exceeds16. The legacy schema6 pool remains explicitly reproducible.
        crowded=sharedPoolImage([('blue',1)]*13+[('red',1)]*4)
        current=recogniseProjective(crowded)
        historical=recogniseProjective(crowded,sharedPool=False)
        self.assertTrue(current['overflow'])
        self.assertFalse(any(marker['accepted'] for marker in current['markers']))
        self.assertFalse(historical['overflow'])
        self.assertEqual(historical['candidatePoolMode'],'SPLIT_PER_COLOUR')
        self.assertEqual(historical['schema'],'ECHO7_PROJECTIVE_MODEL_6')
        with self.assertRaisesRegex(ValueError,'historical'):
            recogniseProjective(crowded,readerAlgorithm=4,sharedPool=True)

    def testFormalSignsAcrossMeasuredRotationGrid(self):
        for angle in range(0,360,15):
            for colour,digit in [('blue',i) for i in range(1,7)]+[('red',1),('red',2)]:
                with self.subTest(angle=angle,colour=colour,digit=digit):
                    result=isolatedResult(rotatedMarker(PATTERNS[digit],angle,colour),colour)
                    self.assertTrue(result['accepted'],result)
                    self.assertEqual(result['digit'],digit)
                    self.assertEqual(result['orientationAnchorMatches'],1)

    def testSmallerMarkerPixelBudget(self):
        for angle in range(0,360,15):
            for digit in (2,6):
                with self.subTest(angle=angle,digit=digit):
                    result=isolatedResult(rotatedMarker(PATTERNS[digit],angle,size=(54,60.75)))
                    self.assertTrue(result['accepted'],result)
                    self.assertEqual(result['digit'],digit)

    def testRejectedUnknownDamagedAndAmbiguousAnchors(self):
        for angle in range(0,360,45):
            for pattern in (PATTERNS[0],PATTERNS[7],PATTERNS[8],PATTERNS[9],'','C'):
                with self.subTest(angle=angle,pattern=pattern):
                    self.assertFalse(isolatedResult(rotatedMarker(pattern,angle))['accepted'])
            self.assertFalse(isolatedResult(rotatedMarker('BC',angle,anchor=False))['accepted'])
            multiple=isolatedResult(rotatedMarker('ABDEG',angle,secondAnchor=True))
            self.assertFalse(multiple['accepted'])
            self.assertEqual(multiple['reasonName'],'ANCHOR_ORIENTATION_AMBIGUOUS')
            reflected=rotatedMarker('ABDEG',angle).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            self.assertFalse(isolatedResult(reflected)['accepted'])

    def testGlobalHintDoesNotSupplyPerMarkerOrientation(self):
        image=rotatedMarker('ABDEG',90)
        for hint in range(4):
            result=isolatedResult(image,orientation=hint)
            self.assertTrue(result['accepted'])
            self.assertEqual((result['digit'],result['orientationProfile']),(2,1))
        upright=isolatedResult(rotatedMarker('BC',0))
        self.assertEqual(upright['orientationProfile'],0)
        self.assertEqual(whiteProfileFor(5),whiteProfileFor(4))

    def testHistoricalReaderFourStillRequiresManualProfile(self):
        image=rotatedMarker('ABDEG',90)
        self.assertFalse(isolatedResult(image,orientation=0,readerAlgorithm=4)['accepted'])
        self.assertTrue(isolatedResult(image,orientation=1,readerAlgorithm=4)['accepted'])
        diagonal=isolatedResult(rotatedMarker('ABDEG',45),readerAlgorithm=4)
        self.assertEqual(diagonal['reasonName'],'GEOMETRY')

    def testBypassRetainsAutomaticOrientationButNotPerspectiveRecovery(self):
        result=isolatedResult(rotatedMarker('ABDEG',90),bypass=True)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['digit'],2)
        self.assertTrue(result['bypassPerspective'])

    def testRecordedDuplicatesRemainDistinctAndWeakAnchorsReject(self):
        recording=root/'tests/fixtures/camera/frame56554'
        metadata=json.loads((recording/'index.json').read_text(encoding='utf-8'))
        image=Image.open(recording/'frame.png').convert('RGB')
        self.assertEqual(hashlib.sha256((recording/'frame.png').read_bytes()).hexdigest(),metadata['files']['frame.png'])
        result=recogniseProjective(image,readerAlgorithm=5,redMin=metadata['redMinimum'],
            blueMin=metadata['blueMinimum'],activeCapacity=15,outputCapacity=16,inputSource='RECORDED_CAMERA')
        self.assertFalse(result['overflow'])
        accepted=collections.Counter((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
        self.assertEqual(accepted,collections.Counter([('red',2),('blue',1),('blue',1),
            ('blue',2),('blue',3),('blue',4),('blue',5),('blue',6)]))
        duplicate=[m for m in result['markers'] if m['accepted'] and m['colour']=='blue' and m['digit']==1]
        self.assertEqual({m['orientationProfile'] for m in duplicate},{0,1})
        # Actual counterexample boundaries: red1's anchor touches the image
        # boundary; the rotated extra2 has only a 1x3 strict-white anchor core.
        # Retain these rejections instead of fabricating two missing successes.
        self.assertTrue(any(m['colour']=='red' and m['bbox'][1]==0 and not m['accepted'] for m in result['markers']))
        self.assertTrue(any(m['colour']=='blue' and m['bbox'][0]>270 and m['bbox'][1]>90 and not m['accepted'] for m in result['markers']))

    def testNewRecordedFrameHasTenPixelDerivedSigns(self):
        recording=root/'tests/fixtures/camera/frame16351'
        metadata=json.loads((recording/'index.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((recording/'frame.png').read_bytes()).hexdigest(),metadata['files']['frame.png'])
        result=recogniseProjective(Image.open(recording/'frame.png').convert('RGB'),readerAlgorithm=5,
            redMin=metadata['redMinimum'],blueMin=metadata['blueMinimum'],activeCapacity=15,outputCapacity=16,
            inputSource='RECORDED_CAMERA')
        self.assertFalse(result['overflow'])
        accepted=collections.Counter((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
        self.assertEqual(accepted,collections.Counter([('red',1),('red',2),('blue',1),('blue',1),
            ('blue',2),('blue',2),('blue',3),('blue',4),('blue',5),('blue',6)]))
        rejected=[m for m in result['markers'] if not m['accepted']]
        self.assertEqual(len(rejected),1)
        self.assertEqual((rejected[0]['colour'],rejected[0]['reasonName']),('blue','GEOMETRY'))


if __name__=='__main__':unittest.main()
