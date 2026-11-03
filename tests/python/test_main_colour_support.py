"""Reader7 independent domain/capacity stresses and known real pixel regressions."""
from collections import Counter
import hashlib,json
from pathlib import Path
import sys,unittest
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'tools/lib'),str(root/'tests/python')]
import numpy as np
from PIL import Image,ImageDraw
from projective_reference import (mainColourSupport,classifyProjective,recogniseProjective,
                                  colourMask,quantise565,SUPPORT_DIRECTIONS)
from vision_reference import recognise
from test_auto_orientation import rotatedMarker
from test_anchor_ownership import algorithm6Cases


def algorithm7Cases():
    yield from algorithm6Cases()
    folder=root/'tests/fixtures/camera/frame364'
    index=json.loads((folder/'index.json').read_text(encoding='utf8'))
    if hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest()!=index['files']['frame.png']:
        raise ValueError('Recorded frame364 input changed')
    yield 'recorded_frame364_main_domain_regression',Image.open(folder/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_KNOWN_MAIN_DOMAIN_REGRESSION'
    for case in mainDescriptorCases():
        yield case['name'],case['image'],0,[],'SYNTHETIC_EXPLICIT_PIXEL_DESCRIPTOR_UNIT_STRESS'


def mainDescriptorCases():
    """Deliberately inconsistent descriptors for the full reader's fail-closed path.

    The exporter labels these overrides explicitly. They do not claim the
    streaming camera CCL produced the supplied mixed/empty descriptors.
    """
    def entry(name,image,bbox=None):
        image=quantise565(image)
        mask=np.asarray(colourMask(image,48,20,colourAlgorithm=3)).reshape(240,320)!=0
        if bbox is None:
            yy,xx=np.nonzero(mask);bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
        return {'name':name,'image':image,'candidates':[{'colour':'blue','bbox':bbox,'area':int(mask.sum())}]}
    islands={'left':(98,92,104,106),'top':(132,52,146,58),
             'right':(216,92,222,106),'bottom':(132,182,146,188)}
    for side,box in islands.items():
        image=rotatedMarker('ABDEG',0);ImageDraw.Draw(image).rectangle(box,fill='#0057B8')
        yield entry('main_mixed_bbox_'+side,image)
    image=Image.new('RGB',(320,240),'white');draw=ImageDraw.Draw(image)
    draw.rectangle([50,50,89,89],fill='#0057B8');draw.rectangle([110,50,149,89],fill='#0057B8')
    yield entry('main_equal_area_components',image)
    yield entry('main_empty_descriptor',Image.new('RGB',(320,240),'white'),[50,50,90,90])
    image=Image.new('RGB',(320,240),'white');draw=ImageDraw.Draw(image)
    for x in range(50,83,4):draw.line([x,50,x,89],fill='#0057B8')
    yield entry('main_nine_active_labels',image)


def mainColourCases():
    """Raw bit-plane plus explicit descriptor, including non-camera stresses.

    These coordinates construct test pixels; no expected digit is fed to the
    support reader. Some mixed descriptors deliberately are not production CCL
    output. Their source labels keep that boundary explicit.
    """
    def blank():return np.zeros((240,320),dtype=bool)
    def row(name,mask,bbox,reason):
        return {'name':name,'mask':mask,'bbox':bbox,'expectedReason':reason,
                'inputSource':'SYNTHETIC_RAW_COLOUR_DESCRIPTOR_UNIT_STRESS'}
    mask=blank();mask[20:60,10:40]=1
    yield row('solid_rectangle_ties',mask,[10,20,39,59],'OK')
    yield row('empty_roi',blank(),[10,20,39,59],'EMPTY')
    mask=blank();mask[239,319]=1
    yield row('last_native_pixel',mask,[319,239,319,239],'OK')
    mask=blank();mask[10:14,10:14]=1;mask[10:14,20:24]=1
    yield row('equal_area_components',mask,[10,10,23,13],'LARGEST_AREA_TIE')
    mask=blank();mask[10,10]=1;mask[11,11]=1
    yield row('diagonal_is_not_connected',mask,[10,10,11,11],'LARGEST_AREA_TIE')
    for side,point,bbox in (('left',(90,70),[70,80,119,119]),('right',(90,129),[80,80,129,119]),
                            ('top',(70,90),[80,70,119,119]),('bottom',(129,90),[80,80,119,129])):
        mask=blank();mask[80:120,80:120]=1;mask[point]=1
        yield row('mixed_bbox_'+side,mask,bbox,'BBOX_MISMATCH')
    mask=blank();mask[10,10:101]=1;mask[230,10:101]=1;mask[10:231,10]=1;mask[10:231,100]=1
    for y in range(15,215,10):mask[y,50]=1
    yield row('twenty_small_components_retire',mask,[10,10,100,230],'OK')
    mask=blank();mask[0,:]=1;mask[239,:]=1;mask[:,0]=1;mask[:,319]=1
    yield row('full_native_frame_boundary',mask,[0,0,319,239],'OK')
    mask=blank();mask[:,0]=1
    yield row('one_column_native_boundary',mask,[0,0,0,239],'OK')
    mask=blank()
    for x in range(10,39,4):mask[10:18,x]=1
    mask[18:22,10:39]=1
    yield row('eight_labels_merge_and_tie',mask,[10,10,38,21],'OK')
    overflow=mask.copy();overflow[18,42]=1
    yield row('merged_aliases_hold_until_row_end',overflow,[10,10,42,21],'ACTIVE_LABEL_OVERFLOW')
    mask=blank()
    for x in range(10,43,4):mask[10:14,x]=1
    yield row('nine_active_seeds_overflow',mask,[10,10,42,13],'ACTIVE_LABEL_OVERFLOW')
    # The selected real domain is a measured colour candidate, not a truth-grid
    # answer. Keep original source frame/profile/version labels in the manifest.
    for frameId,red,blue in ((270,48,20),(364,28,24)):
        folder=root/f'tests/fixtures/camera/frame{frameId}'
        image=quantise565(Image.open(folder/'frame.png').convert('RGB'))
        mask=np.asarray(colourMask(image,red,blue,colourAlgorithm=3)).reshape(240,320)!=0
        if frameId==270:
            yield {'name':'frame270_blue2_domain','mask':mask,'bbox':[244,8,279,74],
                   'inputSource':'KNOWN_RECORDED_CAMERA_EXPLICIT_CANDIDATE','frameId':270,
                   'imageSha256':hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest(),
                   'redMinimum':red,'blueMinimum':blue,'colourAlgorithm':3,'expectedReason':'OK'}
        else:
            candidates=recognise(image,cleanup=True,redMin=red,blueMin=blue,colourAlgorithm=3,
                                 pruneUnusable=True,activeCapacity=15,capacity=16,sharedCapacity=16)['markers']
            for index,candidate in enumerate(candidates):
                yield {'name':f'frame364_candidate_{index}','mask':mask,'bbox':candidate['bbox'],
                       'inputSource':'KNOWN_RECORDED_CAMERA_RAW_CANDIDATE','frameId':364,
                       'imageSha256':hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest(),
                       'redMinimum':red,'blueMinimum':blue,'colourAlgorithm':3}


class MainColourSupportTests(unittest.TestCase):
    def testIndependentDomainsBoundsAndCapacityCases(self):
        for case in mainColourCases():
            with self.subTest(case=case['name']):
                result=mainColourSupport(case['mask'],case['bbox'])
                if 'expectedReason' in case:self.assertEqual(result['reason'],case['expectedReason'])
                if not result['valid']:
                    self.assertEqual(result['supportPoints'],[[0,0]]*16)
                    self.assertEqual((result['foregroundCount'],result['mainArea']),(0,0))
                else:self.assertEqual(result['mainBbox'],case['bbox'])
                if case['name']=='twenty_small_components_retire':
                    self.assertEqual(result['completedComponents'],21)
                    self.assertLessEqual(result['peakActiveHandles'],8)
                if case['name']=='eight_labels_merge_and_tie':
                    self.assertEqual(result['allocationPeak'],8)
                    self.assertEqual(result['completedComponents'],1)
                if result['overflow']:self.assertEqual(result['allocationPeak'],9)

    def testTieBreakUsesGlobalRasterOrderNotMergeOrBfsOrder(self):
        for case in mainColourCases():
            if case['name'] not in ('solid_rectangle_ties','eight_labels_merge_and_tie','full_native_frame_boundary'):continue
            result=mainColourSupport(case['mask'],case['bbox'])
            y0,x0=case['bbox'][1],case['bbox'][0]
            y1,x1=case['bbox'][3],case['bbox'][2]
            points=[(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1) if case['mask'][y,x]]
            expected=[]
            for dx,dy in SUPPORT_DIRECTIONS:
                maximum=max(dx*x+dy*y for x,y in points)
                # Literal raster scan is independent of component traversal.
                expected.append(list(next((x,y) for x,y in points if dx*x+dy*y==maximum)))
            self.assertEqual(result['supportPoints'],expected)

    def testMixedDescriptorCannotPublishSmallerMainCardGeometry(self):
        islands={'left':(98,92,104,106),'top':(132,52,146,58),
                 'right':(216,92,222,106),'bottom':(132,182,146,188)}
        for side,box in islands.items():
            image=rotatedMarker('ABDEG',0);ImageDraw.Draw(image).rectangle(box,fill='#0057B8')
            image=quantise565(image)
            mask=np.asarray(colourMask(image,48,20,colourAlgorithm=3)).reshape(240,320)!=0
            yy,xx=np.nonzero(mask);bbox=[int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
            result=classifyProjective(image,{'colour':'blue','bbox':bbox,'area':int(mask.sum())},readerAlgorithm=7)
            with self.subTest(side=side):
                self.assertFalse(result['accepted'])
                self.assertEqual(result['reasonName'],'MAIN_COLOUR_BBOX_MISMATCH')
                self.assertEqual(result['bbox'],bbox)
                self.assertFalse(result['gridSampled'])

    def testFrame270IsPixelDerivedBlue2RepairAndFrame364RemainsTen(self):
        for frameId,red,blue,expected in ((270,48,20,6),(364,28,24,10)):
            image=Image.open(root/f'tests/fixtures/camera/frame{frameId}/frame.png')
            old=recogniseProjective(image,redMin=red,blueMin=blue,readerAlgorithm=6)
            new=recogniseProjective(image,redMin=red,blueMin=blue,readerAlgorithm=7)
            self.assertEqual(sum(m['accepted'] for m in new['markers']),expected)
            previous={tuple(m['bbox']):m for m in old['markers'] if m['accepted']}
            current={tuple(m['bbox']):m for m in new['markers']}
            for box,marker in previous.items():
                self.assertTrue(current[box]['accepted'])
                self.assertEqual(current[box]['digit'],marker['digit'])
            if frameId==270:
                marker=current[(244,8,279,74)]
                self.assertEqual((marker['digit'],marker['segments'],marker['quality']),(2,'ABDEG',192))
                self.assertEqual(marker['quad'],[[253,8],[279,22],[275,74],[244,61]])
                self.assertEqual(marker['mainColourSupport']['mainArea'],1443)
                self.assertEqual(marker['mainColourSupport']['foregroundCount'],1468)

    def testBypassKeepsReaderSixScanAndAxisBoxSemantics(self):
        image=Image.open(root/'tests/fixtures/camera/frame270/frame.png')
        results=[recogniseProjective(image,readerAlgorithm=version,bypassPerspective=True) for version in (6,7)]
        fields=('accepted','digit','quality','reasonCode','bbox','quad','segments','orientationProfile','foregroundCount')
        for old,new in zip(results[0]['markers'],results[1]['markers']):
            self.assertEqual({k:old.get(k) for k in fields},{k:new.get(k) for k in fields})
            self.assertNotIn('mainColourSupport',new)

    def testCurrentReaderEightAndExplicitHistoricalSevenAndSix(self):
        image=rotatedMarker('ABDEG',0)
        current=recogniseProjective(image)
        self.assertEqual((current['readerAlgorithm'],current['colourAlgorithm'],current['schema']),
                         (9,3,'ECHO7_PROJECTIVE_MODEL_11'))
        previous=recogniseProjective(image,readerAlgorithm=7)
        self.assertEqual((previous['readerAlgorithm'],previous['colourAlgorithm'],previous['schema']),
                         (7,3,'ECHO7_PROJECTIVE_MODEL_9'))
        self.assertTrue(all('colourQuad' not in marker for marker in previous['markers']))
        self.assertEqual([(m['accepted'],m['digit'],m['quality'],m['bbox']) for m in current['markers']],
                         [(m['accepted'],m['digit'],m['quality'],m['bbox']) for m in previous['markers']])
        historical=recogniseProjective(image,readerAlgorithm=6)
        self.assertEqual(historical['schema'],'ECHO7_PROJECTIVE_MODEL_8')
        self.assertTrue(any(m['accepted'] for m in historical['markers']))
        self.assertTrue(all('mainColourSupport' not in m for m in historical['markers']))


if __name__=='__main__':unittest.main()
