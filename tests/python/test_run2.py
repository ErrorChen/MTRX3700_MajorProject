"""Versioned RUN2 preprocessing; real input repair and explicit rejection limits."""
from pathlib import Path
from collections import Counter
import hashlib,itertools,json,subprocess,sys,tempfile,unittest
root=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(root/'tools/lib'),str(root/'tests/python')]
import numpy as np
from PIL import Image,ImageDraw
from projective_reference import recogniseProjective
from vision_reference import horizontalRunSupport


def recordedImage(frameId):
    directory=root/f'tests/fixtures/camera/frame{frameId}'
    index=json.loads((directory/'index.json').read_text(encoding='utf-8'))
    path=directory/'frame.png'
    if hashlib.sha256(path.read_bytes()).hexdigest()!=index['files']['frame.png']:
        raise AssertionError(f'Recorded input{frameId} hash mismatch')
    return Image.open(path).convert('RGB'),index


def accepted(result):
    return Counter((marker['colour'],marker['digit']) for marker in result['markers'] if marker['accepted'])


class RunTwoTests(unittest.TestCase):
    def testIndependentMaximalRunOracleAndRowEdges(self):
        # All3^7 complete rows, rather than copying the local hardware predicate.
        rows=np.asarray(list(itertools.product(range(3),repeat=7)),dtype=np.uint8)
        for length in (2,3):
            expected=np.zeros_like(rows)
            for y,row in enumerate(rows):
                first=0
                while first<len(row):
                    last=first+1
                    while last<len(row) and row[last]==row[first]:last+=1
                    if row[first] and last-first>=length:expected[y,first:last]=row[first]
                    first=last
            np.testing.assert_array_equal(horizontalRunSupport(rows,length),expected)
        np.testing.assert_array_equal(horizontalRunSupport(rows),horizontalRunSupport(rows,3))
        for length in (0,1,4):
            with self.assertRaisesRegex(ValueError,'2 or 3'):horizontalRunSupport(rows,length)

    def testCurrentDefaultAndExplicitHistoricalProfile(self):
        blank=Image.new('RGB',(320,240),'white')
        current=recogniseProjective(blank)
        oldFive=recogniseProjective(blank,readerAlgorithm=5,colourAlgorithm=2)
        oldFour=recogniseProjective(blank,readerAlgorithm=4)
        self.assertEqual(current['colourAlgorithm'],3)
        self.assertEqual(current['cleanup'],'RUN2_THEN_PART_A_CAUSAL_LEFT_OR_UPPER')
        self.assertEqual(current['colourProfile']['horizontalRunSupport'],2)
        for historical in (oldFive,oldFour):
            self.assertEqual(historical['colourAlgorithm'],2)
            self.assertEqual(historical['cleanup'],'RUN3_THEN_PART_A_CAUSAL_LEFT_OR_UPPER')
            self.assertEqual(historical['colourProfile']['horizontalRunSupport'],3)
        with self.assertRaises(ValueError):recogniseProjective(blank,readerAlgorithm=4,colourAlgorithm=3)

    def testRealTwoPixelBridgeRestoresRotatedBlueOne(self):
        image,index=recordedImage(37621)
        self.assertEqual(index['colourAlgorithm'],2,'The real old acquisition must retain its recorded version')
        expected=Counter([('red',1),('red',2),('blue',1),('blue',1),('blue',2),('blue',2),
                          ('blue',3),('blue',4),('blue',5),('blue',6)])
        for redMinimum,blueMinimum in ((48,20),(33,28)):
            old=recogniseProjective(image,redMin=redMinimum,blueMin=blueMinimum,colourAlgorithm=2)
            new=recogniseProjective(image,redMin=redMinimum,blueMin=blueMinimum,colourAlgorithm=3)
            self.assertFalse(old['overflow']);self.assertFalse(new['overflow'])
            self.assertEqual(accepted(old),expected-Counter([('blue',1)]))
            self.assertEqual(accepted(new),expected)
            extra=[m for m in new['markers'] if m['colour']=='blue' and m['bbox'][0]>270 and m['bbox'][1]<75]
            self.assertEqual(len(extra),1)
            self.assertEqual((extra[0]['bbox'],extra[0]['digit'],extra[0]['segments'],extra[0]['quality'],extra[0]['orientationProfile']),
                             ([278,21,306,70],1,'BC',192,1))
            oracle=new['boundedCandidateOracle']
            self.assertLessEqual(oracle['red_max_row_handles'],15)
            self.assertLessEqual(oracle['blue_max_row_handles'],15)

    def testThinNativeAnchorRemainsRejected(self):
        image,index=recordedImage(30158)
        for algorithm in (2,3):
            result=recogniseProjective(image,redMin=index['redMinimum'],blueMin=index['blueMinimum'],colourAlgorithm=algorithm)
            self.assertFalse(result['overflow'])
            self.assertEqual(sum(accepted(result).values()),9)
            extra=[m for m in result['markers'] if m['colour']=='blue' and m['bbox'][0]>=273 and 70<m['bbox'][1]<105]
            self.assertEqual(len(extra),1)
            self.assertFalse(extra[0]['accepted'])
            self.assertEqual(extra[0]['reasonName'],'ANCHOR_OR_HOLE')
            self.assertEqual(extra[0]['orientationAnchorMatches'],0)

    def testNoiseCapacityStillFailsClosed(self):
        original,_=recordedImage(37621)
        for colour in ((192,0,0),(0,87,184)):
            for width in (1,2):
                image=original.copy();draw=ImageDraw.Draw(image)
                for index in range(16):draw.rectangle((5+index*5,122,5+index*5+width-1,126),fill=colour)
                result=recogniseProjective(image,redMin=33,blueMin=28,colourAlgorithm=3)
                self.assertEqual(result['overflow'],width==2)
                if width==2:
                    self.assertEqual(accepted(result),Counter())
                    self.assertTrue(all(m['reasonName']=='FRAME_CAPACITY_OVERFLOW' for m in result['markers']))
                else:self.assertEqual(sum(accepted(result).values()),10)

    def testExporterKeepsExplicitOldCleanupAndNewDefault(self):
        for explicit,expectedAlgorithm,expectedCount in ((False,3,10),(True,2,9)):
            with tempfile.TemporaryDirectory() as directory:
                command=[sys.executable,str(root/'tools/lib/export_projective_vectors.py'),'--out',directory,
                         '--case','recorded_frame37621_support_counterexample']
                if explicit:command.extend(('--colour-algorithm','2'))
                completed=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=45)
                self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)
                manifest=json.loads((Path(directory)/'projective_manifest.json').read_text())
                self.assertEqual(manifest['colourAlgorithm'],expectedAlgorithm)
                self.assertEqual(len(manifest['cases']),1)
                self.assertEqual(sum(marker['accepted'] for marker in manifest['cases'][0]['expected']),expectedCount)


if __name__=='__main__':unittest.main(verbosity=2)
