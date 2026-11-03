"""Reader6 anchor ownership: real regression and independent pixel counterfacts.

The preserved frame270 is a known tuning input, captured with reader5 and SW8
bypass. Its normal/reader6 replay does not constitute another camera acquisition
or a held-out generalisation sample. No expected identity enters the recogniser.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'tools/lib'),str(root/'tests/python')]
import numpy as np
from PIL import Image,ImageDraw
from projective_reference import classifyProjective,nativeAnchorScores,recogniseProjective,whiteProfileFor
from test_auto_orientation import algorithm5Cases,rotatedMarker,isolatedResult
from test_projective import PATTERNS,warpedCard


def neighbourAnchorImage(ownAnchor=True):
    """One actual glyph plus an independent white blob outside its colour bbox.

    The black surround makes the neighbour a closed native component. It is in
    the wrong corner's broad search ROI, but its centre is outside this sign.
    The coordinates construct test pixels; they are never a runtime lookup.
    """
    image=warpedCard(PATTERNS[3],[[100,70],[180,70],[180,160],[100,160]],anchor=ownAnchor)
    draw=ImageDraw.Draw(image)
    draw.rectangle([93,143,99,177],fill='black')
    draw.rectangle([96,156,98,158],fill='white')
    return image


def algorithm6Cases():
    # Historical inputs remain unchanged; only the explicitly versioned oracle
    # differs. Preserve their source tags and do not rename them as new samples.
    yield from algorithm5Cases()
    path=root/'tests/fixtures/camera/frame270'
    metadata=json.loads((path/'index.json').read_text(encoding='utf-8'))
    if hashlib.sha256((path/'frame.png').read_bytes()).hexdigest()!=metadata['files']['frame.png']:
        raise ValueError('Recorded frame270 pixels changed')
    yield 'recorded_frame270_anchor_ownership',Image.open(path/'frame.png').convert('RGB'),0,None,'RECORDED_CAMERA_KNOWN_ANCHOR_REGRESSION'
    yield 'owner_neighbour_plus_own_anchor',neighbourAnchorImage(),0,[('blue',3)],'SYNTHETIC_NEIGHBOUR_ANCHOR_COUNTERFACTUAL'
    yield 'owner_neighbour_without_own_anchor',neighbourAnchorImage(False),0,[],'SYNTHETIC_NEIGHBOUR_ANCHOR_COUNTERFACTUAL'


class AnchorOwnershipTests(unittest.TestCase):
    quad=[[80,80],[280,80],[280,280],[80,280]]

    def mask(self,*boxes):
        image=np.zeros((240,320),dtype=bool)
        for x0,y0,x1,y1 in boxes:image[y0:y1+1,x0:x1+1]=True
        return image

    def testDoubledCentresIncludeExactBoundaryRejectHalfPixelOutside(self):
        # Every component is closed and otherwise eligible. Half-pixel cases
        # would be wrongly accepted by flooring first at maxX/maxY boundaries.
        cases=[([44,44,46,46],[45,40,140,140],True),
               ([44,44,45,46],[45,40,140,140],False),
               ([44,44,46,46],[0,40,45,140],True),
               ([45,44,46,46],[0,40,45,140],False),
               ([44,44,46,46],[40,45,140,140],True),
               ([44,44,46,45],[40,45,140,140],False),
               ([44,44,46,46],[40,0,140,45],True),
               ([44,45,46,46],[40,0,140,45],False)]
        for component,owner,accepted in cases:
            with self.subTest(component=component,owner=owner):
                white=self.mask(component)
                self.assertGreater(nativeAnchorScores(white,self.quad)['white'],0)
                result=nativeAnchorScores(white,self.quad,ownerBbox=owner)
                self.assertEqual(result['white']>0,accepted)
                self.assertEqual(result['outsideOwnerCount'],int(not accepted))

    def testOwnBoundaryMayStraddleButNeighbourDoesNotOwnAnchor(self):
        # Full-box containment would regress legitimate quantised own anchors.
        own=[44,44,46,46];neighbour=[55,44,57,46];owner=[45,40,50,140]
        white=self.mask(own,neighbour)
        historical=nativeAnchorScores(white,self.quad)
        self.assertTrue(historical['ambiguous'])
        result=nativeAnchorScores(white,self.quad,ownerBbox=owner)
        self.assertEqual(result['bbox'],own)
        self.assertEqual((result['eligibleCount'],result['outsideOwnerCount']),(1,1))
        neighbourOnly=nativeAnchorScores(self.mask(neighbour),self.quad,ownerBbox=owner)
        self.assertEqual(neighbourOnly['white'],0)
        self.assertEqual(neighbourOnly['eligibleCount'],0)
        twoOwn=nativeAnchorScores(white,self.quad,ownerBbox=[40,40,140,140])
        self.assertTrue(twoOwn['ambiguous'])
        self.assertEqual(twoOwn['white'],0,'Ownership cannot waive unique-anchor rejection')

    def testMissingOrInvalidOwnerNeverFabricatesSuccess(self):
        white=self.mask([44,44,46,46])
        historical=nativeAnchorScores(white,self.quad)
        self.assertNotIn('ownershipMode',historical)
        self.assertEqual(historical,nativeAnchorScores(white,self.quad,ownerBbox=None))
        for owner in ([0,0,320,239],[0,0,319,240],[50,0,49,239],[-1,0,319,239]):
            with self.subTest(owner=owner),self.assertRaises(ValueError):
                nativeAnchorScores(white,self.quad,ownerBbox=owner)

    def testNeighbourPixelCounterfactualAndDeletedOwnAnchor(self):
        candidate={'colour':'blue','bbox':[100,70,180,160],'area':6000}
        old=classifyProjective(neighbourAnchorImage(),candidate,readerAlgorithm=5,colourAlgorithm=3)
        self.assertEqual(old['reasonName'],'ANCHOR_ORIENTATION_AMBIGUOUS')
        new=classifyProjective(neighbourAnchorImage(),candidate,readerAlgorithm=6,colourAlgorithm=3)
        self.assertTrue(new['accepted'])
        self.assertEqual(new['digit'],3)
        self.assertEqual(new['orientationAnchorMatches'],1)
        deleted=classifyProjective(neighbourAnchorImage(False),candidate,readerAlgorithm=6,colourAlgorithm=3)
        self.assertFalse(deleted['accepted'])
        self.assertFalse(deleted['gridSampled'],'An outside anchor cannot choose the glyph orientation')

    def testRecordedFrame270RetainsProvenanceAndBlue2Rejection(self):
        folder=root/'tests/fixtures/camera/frame270'
        metadata=json.loads((folder/'index.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((folder/'frame.png').read_bytes()).hexdigest(),metadata['files']['frame.png'])
        self.assertEqual((metadata['frameId'],metadata['readerAlgorithm'],metadata['colourAlgorithm']),(270,5,3))
        self.assertTrue(metadata['bypassPerspective'],'Preserve actual acquisition mode')
        image=Image.open(folder/'frame.png').convert('RGB')
        previous=recogniseProjective(image,readerAlgorithm=5,colourAlgorithm=3)
        current=recogniseProjective(image,readerAlgorithm=6,colourAlgorithm=3)
        identities=lambda result:Counter((m['colour'],m['digit']) for m in result['markers'] if m['accepted'])
        self.assertEqual(identities(previous),Counter([('red',2),('blue',5),('blue',6)]))
        self.assertEqual(identities(current),Counter([('red',2),('blue',3),('blue',4),('blue',5),('blue',6)]))
        blue2=next(m for m in current['markers'] if m['bbox']==[244,8,279,74])
        self.assertEqual((blue2['reasonName'],blue2['segments']),('UNKNOWN_PATTERN','ABDG'))
        self.assertEqual(blue2['orientationAnchorMatches'],1)
        self.assertFalse(blue2['accepted'])
        self.assertFalse(current['overflow'])

    def testReaderSixDefaultsAndHistoricalProfilesRemainExplicit(self):
        image=neighbourAnchorImage()
        current=recogniseProjective(image,readerAlgorithm=6)
        self.assertEqual((current['readerAlgorithm'],current['colourAlgorithm']),(6,3))
        self.assertEqual(current['schema'],'ECHO7_PROJECTIVE_MODEL_8')
        self.assertEqual(whiteProfileFor(6),whiteProfileFor(5))
        for colour in (2,3):
            historical=recogniseProjective(image,readerAlgorithm=5,colourAlgorithm=colour)
            self.assertEqual(historical['readerAlgorithm'],5)
            self.assertEqual(historical['schema'],'ECHO7_PROJECTIVE_MODEL_7')
            self.assertFalse(any(m['accepted'] for m in historical['markers']))
            self.assertTrue(all('ownerBbox' not in h['anchor'] for m in historical['markers']
                                for h in m.get('orientationHypotheses',[])))
        with self.assertRaisesRegex(ValueError,'1..9'):
            recogniseProjective(image,readerAlgorithm=10)

    def testRotationAndNegativePixelsKeepOwnershipAndUniqueAnchorRules(self):
        for angle in range(0,360,45):
            for colour,digit in [('blue',i) for i in range(1,7)]+[('red',1),('red',2)]:
                with self.subTest(angle=angle,colour=colour,digit=digit):
                    result=isolatedResult(rotatedMarker(PATTERNS[digit],angle,colour),colour,readerAlgorithm=6)
                    self.assertTrue(result['accepted'],result)
                    self.assertEqual(result['digit'],digit)
            for pattern in (PATTERNS[0],PATTERNS[7],PATTERNS[8],PATTERNS[9],'','C'):
                self.assertFalse(isolatedResult(rotatedMarker(pattern,angle),readerAlgorithm=6)['accepted'])
            self.assertFalse(isolatedResult(rotatedMarker('BC',angle,anchor=False),readerAlgorithm=6)['accepted'])
            self.assertFalse(isolatedResult(rotatedMarker('ABDEG',angle,secondAnchor=True),readerAlgorithm=6)['accepted'])

    def testVectorSchemaCarriesOriginalOwnerAndPreservesLegacyPrefix(self):
        with tempfile.TemporaryDirectory() as directory:
            legacyRows=[]
            for algorithm,recordWords in ((5,20),(6,24)):
                output=Path(directory)/str(algorithm)
                completed=subprocess.run([sys.executable,str(root/'tools/lib/export_projective_vectors.py'),
                    '--reader-algorithm',str(algorithm),'--case','one_anchor_and_one_speck','--out',str(output)],
                    cwd=root,capture_output=True,text=True,timeout=30)
                self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
                manifest=json.loads((output/'anchor_manifest.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['recordWords'],recordWords)
                self.assertEqual(int((output/'anchor_record_words.hex').read_text(),16),recordWords)
                words=[int(line,16) for line in (output/'anchor_meta.hex').read_text().splitlines()]
                self.assertEqual(len(words),recordWords*len(manifest['cases']))
                self.assertEqual(manifest['schema'],f'ECHO7_NATIVE_ANCHOR_VECTORS_{2 if algorithm==6 else 1}')
                if algorithm==5:legacyRows=[words[index:index+20] for index in range(0,len(words),20)]
                if algorithm==6:
                    projective=json.loads((output/'projective_manifest.json').read_text())
                    candidates=projective['cases'][0]['expected']
                    for index,row in enumerate(manifest['cases']):
                        self.assertEqual(words[index*24:index*24+20],legacyRows[index],
                                         'The unchanged own-anchor input must retain the legacy 20-word prefix')
                        self.assertEqual(words[index*24+20:index*24+24],candidates[row['slot']]['bbox'])
                        self.assertEqual(row['ownerBbox'],candidates[row['slot']]['bbox'])


if __name__=='__main__':unittest.main()
