"""Independent capacity and calibrated failure-history regression."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/lib'))
from candidates_reclaimed_model import candidates_reclaimed
from calibration_measurement import evaluateCalibration
from debug_decode import decodeWords
from export_capacity_vectors import export
import tempfile


class ActiveCapacityTests(unittest.TestCase):
    def testRecordedFailureAndOutputBounds(self):
        with tempfile.TemporaryDirectory() as directory:
            export(directory)
            result=json.loads((Path(directory)/'capacity_manifest.json').read_text())
        self.assertTrue(result['historical']['red_active_overflow'])
        self.assertFalse(result['expected']['overflow'])
        self.assertEqual(len(result['expected']['blue']),7)
        mask=[[1 if x%2==0 else 0 for x in range(25)] for _ in range(2)]
        self.assertTrue(candidates_reclaimed(mask,min_area=1,active_capacity=12)['red_active_overflow'])
        mask=[[1] if y%2==0 else [0] for y in range(17)]
        result=candidates_reclaimed(mask,min_area=1,active_capacity=12)
        self.assertFalse(result['red_active_overflow'])
        self.assertTrue(result['red_output_overflow'])
        for capacity in (0,16):
            with self.assertRaises(ValueError):candidates_reclaimed([[0]],min_area=1,active_capacity=capacity)

    def testSchemaFourHasExplicitCapacityAndPersistentSample(self):
        words=[0]*96
        words[0]=0x45425031;words[1]=0x00040002
        words[89]=(30507<<16)|(0x19<<8)|7
        words[90]=4;words[93]=(8<<16)|(12<<8)|0x59
        result=decodeWords(words)
        self.assertEqual(result['activeCandidateCapacity'],12)
        self.assertEqual(result['outputCandidateCapacity'],8)
        self.assertTrue(result['userEventHeld'])
        self.assertEqual(result['calibrationSampleFrames'],7)
        self.assertEqual(result['calibrationLastSample']['frameId'],30507)
        self.assertFalse(result['calibrationLastSample']['checks']['frameGood'])
        words[93]=0
        with self.assertRaises(ValueError):decodeWords(words)
        words[1]=0x00030002
        words[90]=0  # Schema3 has no held-event bit; do not relabel a schema4 payload.
        self.assertEqual(decodeWords(words)['activeCandidateCapacity'],8)

    def testBusyAcceptanceCannotHideCalibrationFailure(self):
        trace=[{'boardTimeUs':100,'frameId':1,'configVersion':65535,'sampleWord':0,'statusUpper':20}]
        final={'configVersion':65535,'calibrationSampleFrames':7}
        result=evaluateCalibration(trace,final,0x04026060)
        self.assertTrue(result['busyRequestRejected'])
        self.assertEqual(result['status'],'FAIL')
        final.update(configVersion=0,calibrationSampleFrames=8)
        trace.append({'boardTimeUs':800100,'frameId':20,'configVersion':0,'sampleWord':8,'statusUpper':308})
        result=evaluateCalibration(trace,final,0x04026060)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['observedTraceToCommitUs'],800000)
        self.assertEqual(result['confirmedAttemptToCommitUpperBoundUs'],800000)


if __name__=='__main__':unittest.main()
