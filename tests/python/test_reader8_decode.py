"""Reader8 geometry metadata tests; MODEL/HOST evidence, never a new capture."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/lib'),str(ROOT/'tests/python')]
from debug_decode import decodeGrabWords,decodeWords,compareMarkerPixels
from test_raw_camera_mode import BUILD,fixture
from test_run2_decode import withProfile
from test_reader6_decode import markerPacket
from projective_reference import classifyProjective,recogniseProjective,whiteProfileFor
from projective_calibration import pairReference


def digitFields(marker):
    # Complete old marker metadata must remain identical; only the new version
    # number and explicitly new geometry output are removed for this comparison.
    return {key:value for key,value in marker.items() if key not in ('readerAlgorithm','colourQuad')}


def algorithm8Cases():
    """Reader7's retained replay inputs plus explicit new geometry regressions."""
    from test_main_colour_support import algorithm7Cases
    yield from algorithm7Cases()
    folder=ROOT/'tests/fixtures/camera/frame15078'
    profile=json.loads((folder/'index.json').read_text(encoding='utf8'))
    if hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest()!=profile['files']['frame.png']:
        raise ValueError('Recorded frame15078 pixels changed')
    yield 'recorded_frame15078_calibration_geometry',Image.open(folder/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_KNOWN_CALIBRATION_GEOMETRY'
    image=np.zeros((240,320,3),dtype=np.uint8);image[50:56,100:132]=(8,32,120)
    yield 'thin_blue_reference_geometry',Image.fromarray(image),0,[],'SYNTHETIC_BLUE_GEOMETRY_WITHOUT_DIGIT'
    for name,box in (('left',[0,50,31,55]),('top',[100,0,131,5])):
        x0,y0,x1,y1=box;image=np.zeros((240,320,3),dtype=np.uint8)
        image[y0:y1+1,x0:x1+1]=(8,32,120)
        yield f'thin_blue_reference_{name}_boundary',Image.fromarray(image),0,[],'SYNTHETIC_NATIVE_BOUNDARY_GEOMETRY_WITHOUT_DIGIT'


class Reader8DecodeTests(unittest.TestCase):
    def testExplicitVersionPreservesWireLayoutAndHistoricalVersions(self):
        before=decodeGrabWords(markerPacket(7),BUILD)
        current=decodeGrabWords(markerPacket(8),BUILD)
        self.assertEqual(before.pop('readerAlgorithm'),7)
        self.assertEqual(current.pop('readerAlgorithm'),8)
        self.assertEqual(before,current)
        for reader in (5,6,7):
            with self.subTest(reader=reader):
                self.assertEqual(decodeGrabWords(markerPacket(reader),BUILD)['readerAlgorithm'],reader)

    def testReader8RequiresCurrentPrivatePublicColourAndWhiteProfile(self):
        for schema in range(1,8):
            with self.subTest(schema=schema),self.assertRaisesRegex(ValueError,'reader algorithm'):
                decodeWords(withProfile(fixture(schema),3,8)[:-2])
        for colour in (0,1,2):
            with self.subTest(colour=colour),self.assertRaisesRegex(ValueError,'requires HSV colour algorithm 3'):
                decodeWords(withProfile(fixture(8),colour,8)[:-2])
        for reader in (10,255):
            with self.subTest(reader=reader),self.assertRaisesRegex(ValueError,'reader algorithm'):
                decodeWords(withProfile(fixture(8),3,reader)[:-2])
        for minimum,spread in ((83,64),(84,63),(96,64)):
            with self.subTest(minimum=minimum,spread=spread),self.assertRaisesRegex(ValueError,'floor84 and spread64'):
                decodeWords(withProfile(fixture(8),3,8,minimum,spread)[:-2])
        self.assertEqual(whiteProfileFor(8),whiteProfileFor(7))

    def testThinBlueGetsGeometryWithoutBecomingDigitOrChangingRedGate(self):
        image=np.zeros((240,320,3),dtype=np.uint8)
        image[50:56,100:132]=(8,32,120)
        fields={'colour':'blue','area':192,'bbox':[100,50,131,55]}
        old=classifyProjective(Image.fromarray(image),fields,readerAlgorithm=7)
        current=classifyProjective(Image.fromarray(image),fields,readerAlgorithm=8)
        self.assertEqual(current['readerAlgorithm'],8)
        self.assertEqual(digitFields(current),digitFields(old))
        self.assertFalse(current['accepted']);self.assertTrue(current['colourQuad']['valid'])
        self.assertEqual(current['colourQuad']['x'],[199,263,263,199])
        self.assertEqual(current['colourQuad']['y'],[99,99,111,111])
        red=classifyProjective(Image.fromarray(image),{**fields,'colour':'red'},readerAlgorithm=8)
        self.assertFalse(red['colourQuad']['valid'])
        for bypass in (False,True):
            narrow=classifyProjective(Image.fromarray(image),{**fields,'bbox':[100,50,102,55]},bypassPerspective=bypass,readerAlgorithm=8)
            self.assertFalse(narrow['colourQuad']['valid'])
        bypass=classifyProjective(Image.fromarray(image),fields,bypassPerspective=True,readerAlgorithm=8)
        self.assertFalse(bypass['colourQuad']['valid']);self.assertEqual(bypass['colourQuad']['x'],[0]*4)

    def testRealRotatedPixelsPreserveAllDigitResultsAndExposeOwnReferenceQuad(self):
        fixtureDir=ROOT/'tests/fixtures/camera/frame15078'
        profile=json.loads((fixtureDir/'index.json').read_text(encoding='utf8'))
        with Image.open(fixtureDir/'frame.png') as image:
            for bypass in (False,True):
                settings=dict(redMin=profile['redMinimum'],blueMin=profile['blueMinimum'],
                    colourAlgorithm=3,bypassPerspective=bypass,inputSource='RECORDED_CAMERA_MODEL_REGRESSION')
                old=recogniseProjective(image,readerAlgorithm=7,**settings)
                current=recogniseProjective(image,readerAlgorithm=8,**settings)
                self.assertEqual((old['schema'],current['schema']),('ECHO7_PROJECTIVE_MODEL_9','ECHO7_PROJECTIVE_MODEL_10'))
                self.assertEqual([digitFields(m) for m in old['markers']],[digitFields(m) for m in current['markers']])
                if bypass:
                    self.assertTrue(all(not m['colourQuad']['valid'] for m in current['markers']))
                    continue
                red=next(m for m in current['markers'] if m['accepted'] and m['colour']=='red' and m['digit']==1)
                references=[m for m in current['markers'] if not m['accepted'] and m['colour']=='blue' and m['colourQuad']['valid']]
                self.assertEqual(len(references),1)
                asPairs=lambda q:list(map(list,zip(q['x'],q['y'])))
                result=pairReference(asPairs(red['colourQuad']),asPairs(references[0]['colourQuad']),red['bbox'])
                self.assertTrue(result['pairValid'])
                self.assertEqual(len([m for m in current['markers'] if m['accepted']]),8)

    def testMixedDomainAndWrongConfigurationDoNotProduceGeometry(self):
        image=Image.new('RGB',(320,240),(0,0,0))
        fields={'colour':'blue','area':192,'bbox':[100,50,131,55]}
        self.assertFalse(classifyProjective(image,fields,readerAlgorithm=8)['colourQuad']['valid'])
        with self.assertRaisesRegex(ValueError,'requires HSV colour algorithm 3'):
            classifyProjective(image,fields,readerAlgorithm=8,colourAlgorithm=2)
        with self.assertRaisesRegex(ValueError,'requires HSV colour algorithm 3'):
            recogniseProjective(image,readerAlgorithm=8,colourAlgorithm=2)

    def testCapturedPixelComparisonDispatchesExactReader8(self):
        expected={'accepted':True,'reasonCode':0,'digit':4,'quality':201,
                  'orientationProfile':2,'windowScores':{},'segments':''}
        with tempfile.TemporaryDirectory(prefix='echo7_reader8_') as folder:
            image=Path(folder)/'input.png';Image.new('RGB',(320,240),(80,96,80)).save(image)
            with patch('projective_reference.classifyProjective',return_value=expected) as model:
                result=compareMarkerPixels(image,decodeWords(markerPacket(8,True)[:-2]),Path(folder)/'out')
            self.assertEqual(model.call_args.kwargs['readerAlgorithm'],8)
            self.assertEqual(result['status'],'PASS')


if __name__=='__main__':unittest.main()
