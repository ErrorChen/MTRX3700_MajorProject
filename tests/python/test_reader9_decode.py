"""Reader9 MODEL/HOST evidence; recordings retain their original reader7 IDs.

The native masks below are deliberately synthetic interface stress inputs. They
do not represent microphone, new camera, FPGA or physical VGA verification.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools/lib'),str(ROOT/'tests/python')]
from projective_reference import (classifyProjective,recogniseProjective,whiteProfileFor,
    thinAnchorSeedScores,weakAnchorSupportScores,whitePixelsFor,nativeAnchorScores)
from debug_decode import decodeWords,decodeGrabWords,compareMarkerPixels
from test_raw_camera_mode import BUILD,fixture
from test_run2_decode import withProfile
from test_reader6_decode import markerPacket


def recorded(frameId):
    folder=ROOT/f'tests/fixtures/camera/frame{frameId}'
    profile=json.loads((folder/'index.json').read_text(encoding='utf8'))
    if hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest()!=profile['files']['frame.png']:
        raise ValueError(f'Recorded frame{frameId} pixels changed')
    return Image.open(folder/'frame.png').convert('RGB'),profile


def thinSynthetic(pattern,angle=0,colour='blue',*,strongSeed=True,weakSupport=True):
    """Independent printed-glyph pixels with a dim anchor edge, no runtime ID."""
    from test_auto_orientation import rotatedMarker,rotationQuad
    image=rotatedMarker(pattern,angle,colour=colour,anchor=False)
    q=np.asarray(rotationQuad(angle));point=q[0]+.1*(q[1]-q[0])+.08889*(q[3]-q[0])
    x,y=map(round,point);draw=ImageDraw.Draw(image)
    if angle%180==0:
        support=(x-1,y-2,x+1,y+1);seed=(x,y-2,x,y+1)
    else:
        support=(x-2,y-1,x+1,y+1);seed=(x-2,y,x+1,y)
    if weakSupport:draw.rectangle(support,fill=(90,90,99))
    if strongSeed:draw.line(seed,fill='white',width=1)
    return image


def algorithm9Cases():
    from test_reader8_decode import algorithm8Cases
    yield from algorithm8Cases()
    for frameId in (45625,63647):
        image,profile=recorded(frameId)
        yield f'recorded_frame{frameId}_thin_anchor',image,0,None,'RECORDED_CAMERA_KNOWN_READER7_ANCHOR_FAILURE'
    image,_=recorded(15078)
    draw=ImageDraw.Draw(image);draw.rectangle((285,223,287,225),fill=(90,90,99));draw.line((286,223,286,225),fill='white')
    yield 'reader9_strong_anchor_wrong_second_seed',image,0,None,'RECORDED_PIXEL_COUNTERFACTUAL'
    image,_=recorded(45625);draw=ImageDraw.Draw(image)
    draw.rectangle((285,223,287,225),fill=(90,90,99));draw.line((286,223,286,225),fill='white')
    yield 'reader9_two_thin_orientations',image,0,None,'RECORDED_PIXEL_COUNTERFACTUAL'
    image,_=recorded(45625);draw=ImageDraw.Draw(image)
    draw.point((269,182),fill=(90,90,99));draw.point((270,182),fill='white')
    yield 'reader9_weak_foreign_strong_bridge',image,0,None,'RECORDED_PIXEL_COUNTERFACTUAL'
    from test_auto_orientation import PATTERNS
    for colour,digit in [('blue',n) for n in range(1,7)]+[('red',1),('red',2)]:
        for angle in (0,90,180,270):
            yield f'reader9_thin_{colour}{digit}_{angle}',thinSynthetic(PATTERNS[digit],angle,colour),0,[(colour,digit)],'SYNTHETIC_GENERIC_THIN_ANCHOR'
    yield 'reader9_thin_unknown8',thinSynthetic(PATTERNS[8]),0,[],'SYNTHETIC_UNKNOWN_DIGIT_WITH_VALID_THIN_ANCHOR'
    yield 'reader9_deleted_strong_anchor',thinSynthetic(PATTERNS[6],strongSeed=False),0,[],'SYNTHETIC_ANCHOR_DELETION'


def seedMasks():
    strong=np.zeros((240,320),dtype=bool);strong[180:183,268]=True
    weak=strong.copy();weak[180:183,267]=True;weak[180:182,269]=True
    quad=[[533,351],[593,353],[585,467],[527,473]]
    owner=[264,176,296,236]
    return strong,weak,quad,owner


def digitIdentity(marker):
    return {key:marker[key] for key in ('accepted','digit','quality','reasonCode','reasonName','orientationProfile','quad','segments','windowScores')}


class Reader9DecodeTests(unittest.TestCase):
    def testVersionGateKeepsAllHistoricalLayouts(self):
        old=decodeGrabWords(markerPacket(8),BUILD);new=decodeGrabWords(markerPacket(9),BUILD)
        self.assertEqual(old.pop('readerAlgorithm'),8);self.assertEqual(new.pop('readerAlgorithm'),9)
        self.assertEqual(old,new)
        for reader in (5,6,7,8):self.assertEqual(decodeGrabWords(markerPacket(reader),BUILD)['readerAlgorithm'],reader)
        for schema in range(1,8):
            with self.subTest(schema=schema),self.assertRaisesRegex(ValueError,'reader algorithm'):
                decodeWords(withProfile(fixture(schema),3,9)[:-2])
        for colour in (0,1,2):
            with self.subTest(colour=colour),self.assertRaisesRegex(ValueError,'requires HSV colour algorithm 3'):
                decodeWords(withProfile(fixture(8),colour,9)[:-2])
        for reader in (10,255):
            with self.subTest(reader=reader),self.assertRaisesRegex(ValueError,'reader algorithm'):
                decodeWords(withProfile(fixture(8),3,reader)[:-2])
        for minimum,spread in ((83,64),(84,63),(96,64)):
            with self.subTest(minimum=minimum),self.assertRaisesRegex(ValueError,'floor84 and spread64'):
                decodeWords(withProfile(fixture(8),3,9,minimum,spread)[:-2])
        self.assertEqual(whiteProfileFor(9),whiteProfileFor(8))

    def testPixelDispatchPreservesExplicitReader9(self):
        expected={'accepted':True,'reasonCode':0,'digit':4,'quality':201,'orientationProfile':2,'windowScores':{},'segments':''}
        with tempfile.TemporaryDirectory(prefix='echo7_reader9_') as folder:
            image=Path(folder)/'input.png';Image.new('RGB',(320,240)).save(image)
            with patch('projective_reference.classifyProjective',return_value=expected) as model:
                result=compareMarkerPixels(image,decodeWords(markerPacket(9,True)[:-2]),Path(folder)/'out')
            self.assertEqual(model.call_args.kwargs['readerAlgorithm'],9)
            self.assertEqual(result['status'],'PASS')

    def testActual45625FailureRequiresOneThinSeedAndKeepsHistoricalRejection(self):
        image,profile=recorded(45625);fields={'colour':'blue','bbox':[264,176,296,236]}
        settings=dict(redMin=profile['redMinimum'],blueMin=profile['blueMinimum'],colourAlgorithm=3)
        old=classifyProjective(image,fields,readerAlgorithm=8,**settings)
        new=classifyProjective(image,fields,readerAlgorithm=9,**settings)
        self.assertFalse(old['accepted']);self.assertEqual(old['reasonName'],'ANCHOR_OR_HOLE')
        self.assertEqual((new['accepted'],new['digit'],new['quality']),(True,6,192))
        self.assertEqual(new['thinSeedCount'],1);self.assertFalse(new['strictAnchorHazard'])
        support=new['thinAnchorSupport']
        self.assertEqual((support['white'],support['strictSeedCount'],support['rows'],support['columns']),(3,3,3,3))
        self.assertEqual(support['weakSupportCount'],8);self.assertEqual(support['strictSeedBbox'],[268,180,268,182])
        self.assertTrue(new['colourQuad']['valid']);self.assertEqual(new['orientationAnchorMatches'],1)
        for reader in (7,8,9):
            baseline=classifyProjective(image,fields,readerAlgorithm=reader,bypassPerspective=True,**settings)
            self.assertFalse(baseline['accepted'])
            if reader>=8:self.assertFalse(baseline['colourQuad']['valid'])

    def testCompleteWeakDomainAndForeignStrongGuards(self):
        strong,weak,quad,owner=seedMasks();seed=thinAnchorSeedScores(strong,quad,ownerBbox=owner)
        self.assertEqual((seed['eligibleCount'],seed['count'],seed['bbox']),(1,3,[268,180,268,182]))
        positive=weakAnchorSupportScores(strong,weak,quad,seed,ownerBbox=owner)
        self.assertEqual((positive['white'],positive['columns'],positive['rows']),(3,3,3))
        variants=[]
        border=weak.copy();border[180,260:268]=True;variants.append(('roi_border',strong,border))
        foreign=strong.copy();foreign[182,270]=True;bridge=weak.copy();bridge[182,269:271]=True
        variants.append(('foreign_strong',foreign,bridge))
        huge=weak.copy();huge[177:187,264:274]=True;variants.append(('oversized',strong,huge))
        variants.append(('one_dimension',strong,strong.copy()))
        missing=strong.copy();missing[181,268]=False;variants.append(('missing_seed',missing,weak))
        inconsistent=weak.copy();inconsistent[181,268]=False;variants.append(('strong_not_weak',strong,inconsistent))
        overflowing=weak.copy();overflowing[173,260:277:2]=True
        variants.append(('weak_label_overflow',strong,overflowing))
        for name,s,w in variants:
            with self.subTest(name=name):
                result=weakAnchorSupportScores(s,w,quad,seed,ownerBbox=owner)
                self.assertEqual(result['white'],0)
                if name=='weak_label_overflow':self.assertTrue(result['overflow'])
        for changed in ({**seed,'count':4},{**seed,'bbox':[267,180,268,182]},
                        {**seed,'bbox':[260,180,260,182]}):
            self.assertEqual(weakAnchorSupportScores(strong,weak,quad,changed,ownerBbox=owner)['white'],0)

    def testNoStrongSeedTwoPixelsAndMultipleSeedsAreNotOne(self):
        strong,weak,quad,owner=seedMasks()
        for changed in (np.zeros_like(strong),strong & (np.indices(strong.shape)[0]!=182)):
            self.assertEqual(thinAnchorSeedScores(changed,quad,ownerBbox=owner)['eligibleCount'],0)
        strong[184:187,272]=True
        seeds=thinAnchorSeedScores(strong,quad,ownerBbox=owner)
        self.assertEqual(seeds['eligibleCount'],2);self.assertFalse(seeds['valid'])

    def testOriginalStrongDecisionSurvivesWrongSecondThinOrientation(self):
        image,_=recorded(15078);draw=ImageDraw.Draw(image)
        draw.rectangle((285,223,287,225),fill=(90,90,99));draw.line((286,223,286,225),fill='white')
        fields={'colour':'blue','bbox':[264,176,296,236]};settings=dict(redMin=41,blueMin=33,colourAlgorithm=3)
        old=classifyProjective(image,fields,readerAlgorithm=8,**settings)
        new=classifyProjective(image,fields,readerAlgorithm=9,**settings)
        self.assertTrue(old['accepted']);self.assertEqual(old['digit'],6)
        self.assertEqual(digitIdentity(old),digitIdentity(new));self.assertEqual(new['anchorSupportMode'],'STRICT_COMPONENT')

    def testGlobalThinUniquenessAndFailedRescanGeometryOrder(self):
        fields={'colour':'blue','bbox':[264,176,296,236]};settings=dict(redMin=41,blueMin=33,colourAlgorithm=3,readerAlgorithm=9)
        image,_=recorded(45625);draw=ImageDraw.Draw(image)
        draw.rectangle((285,223,287,225),fill=(90,90,99));draw.line((286,223,286,225),fill='white')
        multiple=classifyProjective(image,fields,**settings)
        self.assertFalse(multiple['accepted']);self.assertEqual(multiple['thinSeedCount'],2)
        self.assertNotIn('thinAnchorSupport',multiple)
        image,_=recorded(45625);draw=ImageDraw.Draw(image)
        draw.point((269,182),fill=(90,90,99));draw.point((270,182),fill='white')
        rejected=classifyProjective(image,fields,**settings)
        self.assertFalse(rejected['accepted']);self.assertEqual(rejected['thinSeedCount'],1)
        self.assertEqual(rejected['thinAnchorSupport']['supportReason'],'FOREIGN_STRONG_COMPONENT')
        self.assertEqual(rejected['colourQuadAttemptOrientation'],0)
        self.assertEqual(rejected['colourQuad']['orientationProfile'],0)
        self.assertEqual(rejected['orientationHypotheses'][-1]['orientation'],3)

    def testFourStrongPixelsRemainFourAndFallbackQualityIsCapped(self):
        from test_auto_orientation import PATTERNS
        image=thinSynthetic(PATTERNS[6])
        result=recogniseProjective(image,readerAlgorithm=9,colourAlgorithm=3)
        accepted=[m for m in result['markers'] if m['accepted']]
        self.assertEqual(len(accepted),1)
        self.assertEqual((accepted[0]['digit'],accepted[0]['quality']),(6,192))
        self.assertEqual(accepted[0]['thinAnchorSupport']['white'],4)
        self.assertEqual(accepted[0]['thinAnchorSupport']['strictSeedCount'],4)

    def testSameRuleAcrossAllFormalDigitsColoursAndFourRotations(self):
        from test_auto_orientation import PATTERNS
        for colour,digit in [('blue',n) for n in range(1,7)]+[('red',1),('red',2)]:
            for angle in (0,90,180,270):
                with self.subTest(colour=colour,digit=digit,angle=angle):
                    result=recogniseProjective(thinSynthetic(PATTERNS[digit],angle,colour),readerAlgorithm=9)
                    accepted=[m for m in result['markers'] if m['accepted']]
                    self.assertEqual([(m['colour'],m['digit']) for m in accepted],[(colour,digit)])
                    self.assertEqual(accepted[0]['anchorSupportMode'],'STRICT_THIN_SEED_WEAK_SUPPORT')
                    self.assertEqual(accepted[0]['quality'],192)

    def testDeletedAnchorAndUnsupportedStrongLineRejectUnknownGlyphKeepsFallbackFlag(self):
        from test_auto_orientation import PATTERNS
        for kwargs in ({'strongSeed':False},{'weakSupport':False},{'strongSeed':False,'weakSupport':False}):
            with self.subTest(kwargs=kwargs):
                result=recogniseProjective(thinSynthetic(PATTERNS[6],**kwargs),readerAlgorithm=9)
                self.assertFalse(any(m['accepted'] for m in result['markers']))
        result=recogniseProjective(thinSynthetic(PATTERNS[8]),readerAlgorithm=9)
        marker=next(m for m in result['markers'] if m['anchorSupportMode']=='STRICT_THIN_SEED_WEAK_SUPPORT')
        self.assertFalse(marker['accepted']);self.assertEqual(marker['reasonCode'],5)

    def testSourceBoundHeldOut63647IsNotAClaimOfSplitCardRepair(self):
        image,profile=recorded(63647);settings=dict(redMin=profile['redMinimum'],blueMin=profile['blueMinimum'],colourAlgorithm=3)
        old=recogniseProjective(image,readerAlgorithm=8,**settings)
        new=recogniseProjective(image,readerAlgorithm=9,**settings)
        fullOld=next(m for m in old['markers'] if m['bbox']==[264,176,296,236])
        fullNew=next(m for m in new['markers'] if m['bbox']==[264,176,296,236])
        self.assertFalse(fullOld['accepted']);self.assertEqual(fullOld['reasonCode'],4)
        self.assertEqual((fullNew['accepted'],fullNew['digit'],fullNew['quality']),(True,6,192))
        inner=next(m for m in new['markers'] if m['bbox']==[274,208,293,225])
        self.assertFalse(inner['accepted']);self.assertEqual(inner['reasonCode'],1)


if __name__=='__main__':unittest.main()
