"""Synthetic trace assessment; these tests are not camera/calibration evidence."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tools/lib"))
from calibration_measurement import evaluateCalibration


def assessment(elapsedUs, startState=0, startUs=100):
    trace=[{"boardTimeUs":startUs,"configVersion":65535,"statusUpper":startState<<5},
           {"boardTimeUs":(startUs+elapsedUs)&0xffffffff,"configVersion":0,"statusUpper":9<<5}]
    final={"configVersion":0,"calibrationSampleFrames":8}
    return evaluateCalibration(trace,final,0x04026060)


class CalibrationMeasurementTests(unittest.TestCase):
    def testFrozenBoundaryAndGoal(self):
        result=assessment(2_000_000)
        self.assertEqual(result["status"],"PASS")
        self.assertEqual(result["timingTarget"]["status"],"PASS")
        self.assertFalse(result["timingTarget"]["goalMet"])
        self.assertTrue(assessment(1_000_000)["timingTarget"]["goalMet"])

    def testOneMicrosecondOverCannotPassTiming(self):
        result=assessment(2_000_001)
        self.assertTrue(result["configurationCommitted"])
        self.assertEqual(result["status"],"FAIL")
        self.assertEqual(result["timingTarget"]["status"],"FAIL")
        self.assertIn("conservative timing bound",result["reason"])

    def testMissingPreConfirmationStartIsNotMeasured(self):
        result=assessment(1_000_000,startState=2)
        self.assertEqual(result["status"],"PASS")  # completion, not timing
        self.assertEqual(result["timingTarget"]["status"],"NOT_MEASURED")
        self.assertIsNone(result["timingTarget"]["goalMet"])
        self.assertIsNone(result["confirmedAttemptToCommitUpperBoundUs"])

    def testBoardTimeAndConfigWrapKeepTheElapsedDuration(self):
        result=assessment(800_000,startUs=0xfffffff0)
        self.assertEqual(result["timingTarget"]["status"],"PASS")
        self.assertEqual(result["confirmedAttemptToCommitUpperBoundUs"],800_000)


if __name__=="__main__":unittest.main()
