"""Synthetic shared-pool schema/model tests; never hardware evidence."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/lib'),str(ROOT/'tests/python')]
import test_raw_camera_mode as rawTests
from test_raw_camera_mode import fixture, BUILD
from debug_decode import decodeWords, decodeGrabWords, compareMarkerPixels, schemaLayout
from candidates_reclaimed_model import candidates_reclaimed
from compare_sw9_trials import compareTrials
from test_sw9_comparison import fixture as trialFixture
from trial_stream import parseTrialStream
from vision_reference import recognise


def sharedWords(colours=(True, False, True)):
    words=fixture(7)
    words[9]=colours.count(False)|(colours.count(True)<<5)
    for index, blue in enumerate(colours):
        at=24+4*index
        words[at:at+3]=[(int(blue)<<30)|(15<<24),((10+index*4)<<16)|(12+index*4),(20<<16)|22]
    return words


class Schema7SharedPoolTests(unittest.TestCase):
    def testSchema7Has96Words16GlobalSlotsAndExplicitPoolFlag(self):
        result=decodeGrabWords(sharedWords(),BUILD)
        self.assertEqual(result['statusWordCount'],96)
        self.assertEqual(len(result['markers']),16)
        self.assertEqual(result['poolLayout'],'SHARED_TOTAL')
        self.assertEqual((result['redCandidateCount'],result['blueCandidateCount']),(1,2))
        self.assertEqual([m['isBlue'] for m in result['markers'][:3]],[True,False,True])
        self.assertEqual(result['markers'][0]['digit'],15) # Unknown still has its real colour.
        for schema,slots,capacity in ((5,16,8),(6,32,16)):
            old=decodeGrabWords(fixture(schema),BUILD)
            self.assertEqual((old['candidateStorageSlots'],old['outputCandidateCapacity']),(slots,capacity))
            self.assertEqual(old['poolLayout'],'SPLIT_PER_COLOUR')
        with self.assertRaises(ValueError):schemaLayout(8)

    def testSharedCountsAreTotalBoundedAndRequireDenseTypedSlots(self):
        words=sharedWords(tuple([False]*2+[True]*14))
        self.assertEqual(decodeWords(words[:-2])['blueCandidateCount'],14)
        for index,value in ((9,3|(14<<5)),(9,3|(13<<5)),(24+4*2,0),
                            (93,(16<<16)|(15<<8)),(93,(2<<24)|(16<<16)|(15<<8)),
                            (93,(1<<24)|(8<<16)|(15<<8))):
            broken=words.copy();broken[index]=value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):decodeWords(broken[:-2])
        words=sharedWords()
        words[24+4*5]=(1<<31)|(1<<24)
        with self.assertRaisesRegex(ValueError,'outside dense'):decodeWords(words[:-2])

    def testReferenceGlobalSlotZeroAndLegacyUnifiedIndices(self):
        words=sharedWords();words[90]=8
        result=decodeWords(words[:-2])
        self.assertTrue(result['calibrationReferenceValid'])
        self.assertEqual(result['calibrationReferenceMarkerIndex'],0)
        self.assertNotIn('calibrationReferenceBlueIndex',result)
        words[90]=8|(1<<4)
        with self.assertRaisesRegex(ValueError,'reference'):decodeWords(words[:-2]) # Slot1 is red.
        words[90]=8|(3<<4)
        with self.assertRaisesRegex(ValueError,'reference'):decodeWords(words[:-2]) # Slot3 is outside count.
        for schema,blueOffset in ((5,8),(6,16)):
            legacy=fixture(schema);tail=schemaLayout(schema)['tailBase'];bits=5 if schema==6 else 4
            legacy[9]=3<<bits;legacy[tail+2]=8|(2<<4)
            at=24+4*(blueOffset+2);legacy[at:at+3]=[(1<<30)|(15<<24),(10<<16)|20,(20<<16)|24]
            result=decodeWords(legacy[:-2])
            self.assertEqual(result['calibrationReferenceBlueIndex'],2)
            self.assertEqual(result['calibrationReferenceMarkerIndex'],blueOffset+2)

    def testPixelComparisonUsesHeaderColourInsteadOfSlotPartition(self):
        words=sharedWords((True,False))
        expected={'accepted':False,'reasonCode':0,'windowScores':{},'segments':''}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.png';Image.new('RGB',(320,240)).save(path)
            with patch('projective_reference.classifyProjective',return_value=expected) as model:
                result=compareMarkerPixels(path,decodeWords(words[:-2]),Path(folder)/'check')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual([call.args[1]['colour'] for call in model.call_args_list],['blue','red'])
            self.assertEqual([row['index'] for row in result['comparisons']],[0,1])

    def testRaw98WordCaptureRemainsNotRecognitionAndTclReads96(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=rawTests.RawCameraModeTests().rawCapture(folder,schema=7)
            self.assertEqual(runner.result['snapshot']['n_results'],98)
            self.assertEqual(runner.result['recognition']['poolLayout'],'SHARED_TOTAL')
            self.assertEqual(runner.result['glyphAgreement']['status'],'NOT_APPLICABLE_RAW_CAMERA_MODE')
        code,output=rawTests.RawCameraModeTests().invokeRawTcl(schema=7)
        self.assertNotEqual(code,0)
        self.assertEqual(output.count('ECHO7_TRIAL_WORD\t'),96)
        records,_=parseTrialStream(output,BUILD)
        self.assertEqual(records[0]['decoded']['poolLayout'],'SHARED_TOTAL')

    def mask(self, red, blue):
        # Non-overlapping sequential rows keep temporary occupancy1 while
        # exercising total completed capacity, independently of active labels.
        result=[[0]*8 for _ in range(3*(red+blue)+1)]
        for index,colour in enumerate([1]*red+[2]*blue):result[3*index][1:5]=[colour]*4
        return result

    def testSharedPoolBorrowsAcrossColoursAndRejectsOnlyTotalOverflow(self):
        for red,blue,overflow in ((14,2,False),(2,14,False),(8,8,False),(8,9,True),(0,16,False)):
            with self.subTest(red=red,blue=blue):
                result=candidates_reclaimed(self.mask(red,blue),active_capacity=15,min_area=3,shared_capacity=16)
                self.assertEqual(result['overflow'],overflow)
                self.assertEqual(result['sharedOutputOverflow'],overflow)
                self.assertFalse(result['red_active_overflow'] or result['blue_active_overflow'])
                self.assertEqual(len(result['sharedCandidates']),0 if overflow else red+blue)
                if not overflow:
                    self.assertCountEqual([row['descriptor'] for row in result['sharedCandidates']],result['red']+result['blue'])
                    self.assertEqual(result['sharedCandidateOrder'],'MODEL_CANONICAL_GEOMETRY_NOT_RTL_RETIREMENT_ORDER')
        # Schema6 split16/colour history remains valid for the same17 objects.
        self.assertFalse(candidates_reclaimed(self.mask(8,9),cap=16,active_capacity=15,min_area=3)['overflow'])
        self.assertTrue(candidates_reclaimed(self.mask(2,9),min_area=3)['overflow'])

    def testActiveOverflowStillInvalidatesSharedPoolAndOutputIsNotSalvaged(self):
        mask=[[1 if x%2==0 else 0 for x in range(31)] for _ in range(2)]
        result=candidates_reclaimed(mask,min_area=1,active_capacity=15,shared_capacity=16)
        self.assertTrue(result['red_active_overflow'])
        self.assertTrue(result['overflow'])
        self.assertEqual(result['sharedCandidates'],[])

    def testVisionCapacityUsesSharedTotalAndCanonicalColourGeometry(self):
        image=Image.new('RGB',(320,240),'white')
        from PIL import ImageDraw
        draw=ImageDraw.Draw(image)
        for index in range(17):
            x=(index%6)*45+2;y=(index//6)*40+2
            draw.rectangle((x,y,x+23,y+25),fill='#C00000' if index<8 else '#0057B8')
        split=recognise(image,capacity=16,activeCapacity=15,cleanup=True)
        shared=recognise(image,capacity=16,activeCapacity=15,cleanup=True,sharedCapacity=16)
        self.assertFalse(split['overflow'])
        self.assertTrue(shared['overflow'])
        self.assertTrue(shared['boundedCandidateOracle']['sharedOutputOverflow'])
        self.assertFalse(any(marker['accepted'] for marker in shared['markers']))
        self.assertEqual(shared['poolLayout'],'SHARED_TOTAL')
        self.assertIsNone(shared['capacityPerColour'])

    def testComparisonIncludesPoolLayoutSoSameCapacityCannotHideDifferentStorage(self):
        normal,bypass=trialFixture(0),trialFixture(1)
        for state in [bypass['initialStatus'],*[row['status'] for row in bypass['observations']],
                      *[row['status'] for row in bypass['requestSelections']]]:
            state['poolLayout']='SHARED_TOTAL'
        result,code=compareTrials(normal,bypass,'Synthetic conditions only')
        self.assertEqual(code,1)
        self.assertIn('profile',str(result['comparisonValidity']['issues']).lower())


if __name__=='__main__':unittest.main()
