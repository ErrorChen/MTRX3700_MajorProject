"""Synthetic status transport only; never CAMERA_HW evidence."""
import argparse
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/lib"))
from hardware_measurement import measureTrials,scoreRegions,TrackingAcquisition


class FixtureRunner:
    def __init__(self, folder, failFrame=None, latencies=None, transitionFrame=None):
        self.args=argparse.Namespace(timeout=10)
        self.out=Path(folder)
        self.result={}
        self.frame=0;self.bay=1;self.tag=0;self.failFrame=failFrame;self.cleared=False
        self.latencies=latencies or {};self.transitionFrame=transitionFrame

    def control(self, command=0):
        if command >> 24 == 1:
            self.bay=command & 15;self.tag+=1
        elif command >> 24 == 2:
            self.cleared=True
        else:
            self.frame+=1
        markers=[{"digit":digit,"accepted":True,"isBlue":True} for digit in range(1,7)]
        markers += [{"digit":digit,"accepted":True,"isBlue":False} for digit in (1,2)]
        if self.frame == self.failFrame:
            markers[5]["accepted"]=False
        return {"decoded": {"frameId":self.frame,"bufferDropCount":0,"completionDiscardCount":0,
            "configVersion":1,"processingLatencyUs":self.latencies.get(self.frame,42000+self.frame),"freshAtSnapshot":True,"markers":markers,
            "activeRequest":{"requestTag":self.tag},
            "status":{"faultFlags":0,"activeCfgVersion":1,"calibrated":True,"interactionBusy":False,"perceptionReady":True},
            "targetReport":{"requestTag":self.tag-int(self.frame==self.transitionFrame),"bayId":self.bay,"frameId":self.frame,"configVersion":1,
                            "targetSelected":True,"frameGood":True,"observed":True,"locked":True,"ambiguous":False}}}


class HardwareMeasurementTests(unittest.TestCase):
    def acquisitionState(self, frame, locked=False, reason=2, tag=7, config=1):
        return {"frameId":frame,"freshAtSnapshot":True,"status":{"activeCfgVersion":config},
                "targetReport":{"requestTag":tag,"bayId":3,"frameId":frame,"configVersion":config,
                    "targetSelected":True,"frameGood":True,"observed":True,"ambiguous":False,
                    "locked":locked,"reason":reason}}

    def testAcquisitionAllowsTwoFramesThenRequiresLock(self):
        tracker=TrackingAcquisition(7,3,1)
        self.assertTrue(tracker.observe(self.acquisitionState(100))["expectedAcquiring"])
        self.assertTrue(tracker.observe(self.acquisitionState(101))["expectedAcquiring"])
        self.assertFalse(tracker.observe(self.acquisitionState(102))["expectedAcquiring"])
        self.assertTrue(tracker.observe(self.acquisitionState(102,locked=True,reason=0))["lockPreviouslyObserved"])

    def testSkippedFramesCannotExtendAcquisition(self):
        tracker=TrackingAcquisition(7,3,1)
        tracker.observe(self.acquisitionState(65535))
        self.assertTrue(tracker.observe(self.acquisitionState(0))["expectedAcquiring"])
        result=tracker.observe(self.acquisitionState(2))
        self.assertEqual(result["nativeFrameOffset"],3)
        self.assertFalse(result["expectedAcquiring"])

    def testUnlockAfterAnyLockCannotReenterGrace(self):
        tracker=TrackingAcquisition(7,3,1)
        tracker.observe(self.acquisitionState(100,locked=True,reason=0))
        self.assertFalse(tracker.observe(self.acquisitionState(101))["expectedAcquiring"])
        self.assertFalse(tracker.observe(self.acquisitionState(500))["expectedAcquiring"])

    def testAcquisitionNeedsCurrentTagConfigurationReasonAndGoodObservation(self):
        tracker=TrackingAcquisition(7,3,1)
        self.assertFalse(tracker.observe(self.acquisitionState(1,tag=6))["expectedAcquiring"])
        self.assertIsNone(tracker.firstFrame)
        self.assertFalse(tracker.observe(self.acquisitionState(10,config=2))["expectedAcquiring"])
        tracker=TrackingAcquisition(7,3,1)
        for field in ("frameGood","observed","targetSelected"):
            state=self.acquisitionState(10);state["targetReport"][field]=False
            self.assertFalse(tracker.observe(state)["expectedAcquiring"])
        state=self.acquisitionState(10);state["targetReport"]["ambiguous"]=True
        self.assertFalse(tracker.observe(state)["expectedAcquiring"])
        self.assertFalse(tracker.observe(self.acquisitionState(10,reason=3))["expectedAcquiring"])

    def testTrialRetainsAcquiringFramesAndOriginalStrictVerdict(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder)
            originalControl=runner.control
            ordinal=0
            def control(command=0):
                nonlocal ordinal
                result=originalControl(command)
                report=result["decoded"]["targetReport"]
                if command>>24==1:
                    ordinal=0
                    report["requestTag"]-=1  # SELECT can still show an old frame.
                elif command==0 and runner.tag:
                    ordinal+=1
                    report["locked"]=ordinal>=3
                    report["reason"]=0 if report["locked"] else 2
                return result
            runner.control=control
            measureTrials(runner,1)
            self.assertEqual(len(runner.result["observations"]),30)
            self.assertEqual(len(runner.result["strictAllLockedFailures"]),12)
            self.assertEqual(runner.result["failures"],[])
            summary=runner.result["trials"][0]
            self.assertEqual(summary["acquiringSamples"],12)
            self.assertEqual(summary["lockedSamples"],18)
            self.assertEqual(summary["passedSamples"],30)
            self.assertTrue(runner.cleared)

    def drainState(self, frame=101, timeUs=2000, captureStartUs=900):
        state=self.acquisitionState(frame,tag=6)
        state["timeUs"]=timeUs
        state["captureStartUs"]=captureStartUs
        state["activeRequest"]={"requestTag":7,"bayId":3,"operation":1}
        state["targetReport"].update(bayId=2,reason=7,observed=0,locked=0,
            centreU=0,centreV=0,boxWidth=0,boxHeight=0,quality=0,captureStartUs=captureStartUs)
        return state

    def testOldRequestDrainIsBoundedAndNeverNewTargetAcquisition(self):
        selected=self.drainState(100,1000)
        tracker=TrackingAcquisition(7,3,1,selected)
        result=tracker.observe(self.drainState())
        self.assertTrue(result["expectedOldRequestDrain"])
        self.assertFalse(result["expectedAcquiring"])
        self.assertIsNone(tracker.firstFrame)
        # The frozen SELECT frame is the most recent completed frame, not the
        # camera frame active at the command. A forward offset of two is valid
        # when its immutable capture time still precedes the freeze.
        self.assertTrue(tracker.observe(self.drainState(102,3000))["expectedOldRequestDrain"])
        self.assertFalse(tracker.observe(self.drainState(101,151001))["expectedOldRequestDrain"])
        self.assertTrue(tracker.observe(self.acquisitionState(102))["expectedAcquiring"])
        self.assertFalse(tracker.observe(self.drainState(101,2000))["expectedOldRequestDrain"])

    def testActualTwoFrameOffsetUsesCaptureTimeRatherThanCompletedFrame(self):
        # Transcribed timing from real frame16449; this is a host regression
        # fixture, not another hardware observation or a new independent trial.
        selected=self.drainState(16447,2549236721,2549154162)
        state=self.drainState(16449,2549311574,2549234130)
        result=TrackingAcquisition(7,3,1,selected).observe(state)
        self.assertTrue(result["expectedOldRequestDrain"])
        self.assertEqual(result["selectionFrameOffset"],2)
        self.assertEqual(result["captureAgeAtSelectionUs"],2591)
        self.assertEqual(result["selectionElapsedUs"],74853)

    def testOldDrainRejectsFutureStaleAndMismatchedCaptureTimestamps(self):
        selected=self.drainState(100,200000,160000)
        for capture in (200001, 49999):
            with self.subTest(captureStartUs=capture):
                state=self.drainState(102,210000,capture)
                self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        state=self.drainState(102,210000,199900)
        state["targetReport"]["captureStartUs"]-=1
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        for field in ("captureStartUs", "timeUs"):
            state=self.drainState(102,210000,199900)
            del state[field]
            self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        state=self.drainState(102,210000,199900)
        state["freshAtSnapshot"]=False
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])

    def testOldDrainBoardTimeWrapRetainsOrderingAndLateRejection(self):
        selected=self.drainState(65535,0xfffffff0,0xffff0000)
        state=self.drainState(1,0x20,0xffffffe0)
        result=TrackingAcquisition(7,3,1,selected).observe(state)
        self.assertTrue(result["expectedOldRequestDrain"])
        self.assertEqual(result["captureAgeAtSelectionUs"],16)
        self.assertEqual(result["selectionElapsedUs"],48)
        self.assertEqual(result["selectionFrameOffset"],2)
        state=self.drainState(1,0x20,0x10)
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        state=self.drainState(1,(0xfffffff0+150001)&0xffffffff,0xffffffe0)
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])

    def testOldDrainRejectsWrongReasonTagConfigAndCorruptPublicFields(self):
        selected=self.drainState(100,1000)
        for changes in ({"reason":1},{"requestTag":5},{"configVersion":2},{"quality":1},
                        {"observed":1},{"locked":1},{"frameGood":0},{"ambiguous":1}):
            with self.subTest(changes=changes):
                state=self.drainState();state["targetReport"].update(changes)
                self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        state=self.drainState();state["activeRequest"]["requestTag"]=8
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])
        state=self.drainState();del state["timeUs"]
        self.assertFalse(TrackingAcquisition(7,3,1,selected).observe(state)["expectedOldRequestDrain"])

    def testValidPreviousLockIsOnlyABoundedTransition(self):
        selected=self.drainState(100,1000)
        state=self.drainState()
        state["targetReport"].update(reason=0,observed=1,locked=1,centreU=30,centreV=80,boxWidth=20,boxHeight=30,quality=192)
        tracker=TrackingAcquisition(7,3,1,selected)
        self.assertTrue(tracker.observe(state)["expectedPreviousLockedReport"])
        self.assertFalse(tracker.seenLocked)
        self.assertIsNone(tracker.firstFrame)
        state["frameId"]=state["targetReport"]["frameId"]=102
        self.assertTrue(tracker.observe(state)["expectedPreviousLockedReport"])
        state["captureStartUs"]=state["targetReport"]["captureStartUs"]=1001
        self.assertFalse(tracker.observe(state)["expectedPreviousLockedReport"])

    def testPixelLabelSwapCannotHideInUnchangedIdSet(self):
        truth={"regions":[{"bbox":[0,0,20,20],"isBlue":True,"digit":1},
                          {"bbox":[30,0,50,20],"isBlue":True,"digit":2}]}
        markers=[{"accepted":True,"isBlue":True,"digit":2,"xMin":2,"xMax":18,"yMin":2,"yMax":18},
                 {"accepted":True,"isBlue":True,"digit":1,"xMin":32,"xMax":48,"yMin":2,"yMax":18}]
        self.assertEqual(sorted(m['digit'] for m in markers),[1,2])
        self.assertEqual(scoreRegions(markers,truth)['wrongOrAmbiguous'],2)
        markers[0]['digit'],markers[1]['digit']=1,2
        self.assertEqual(scoreRegions(markers,truth)['correct'],2)

    def testFailureStaysInThirtySampleDenominatorAndStillClears(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder,failFrame=4)
            with self.assertRaisesRegex(RuntimeError,"no success-only filtering"):
                measureTrials(runner,1)
            self.assertEqual(len(runner.result["observations"]),30)
            self.assertEqual(runner.result["trials"][0]["failedSamples"],1)
            self.assertEqual(runner.result["trials"][0]["typedSetPasses"],29)
            self.assertTrue(runner.cleared)

    def testThreeTrialsHaveNinetyDistinctFramesAndTiming(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder)
            measureTrials(runner,3)
            self.assertEqual(len({r["status"]["frameId"] for r in runner.result["observations"]}),90)
            self.assertEqual([t["passedSamples"] for t in runner.result["trials"]],[30,30,30])
            self.assertEqual(runner.result["trials"][0]["captureToCompletionUs"]["maximum"],42031)
            self.assertTrue(runner.cleared)

    def testLatencyThresholdBoundaryAndGoalAreIndependent(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder,latencies={4:150000})
            measureTrials(runner,1)
            timing=runner.result["trials"][0]["latencyTarget"]
            self.assertEqual(timing["status"],"PASS")
            self.assertEqual(timing["measuredMaximumUs"],150000)
            self.assertFalse(timing["goalMet"])

    def testSlowInvalidFrameCannotBeRemovedFromLatencyPopulation(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder,failFrame=4,latencies={4:150001})
            with self.assertRaisesRegex(RuntimeError,"no success-only filtering"):
                measureTrials(runner,1)
            self.assertEqual(runner.result["trials"][0]["latencyTarget"]["status"],"FAIL")
            failure=next(record for record in runner.result["observations"] if record["status"]["frameId"]==4)
            self.assertIn("capture_to_completion_latency",failure["issues"])
            self.assertIn("typed_marker_set",failure["issues"])
            self.assertTrue(runner.cleared)

    def testOldRequestTransitionStillCountsTowardsTimingMaximum(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=FixtureRunner(folder,transitionFrame=2,latencies={2:150001})
            with self.assertRaisesRegex(RuntimeError,"no success-only filtering"):
                measureTrials(runner,1)
            trial=runner.result["trials"][0]
            self.assertEqual(trial["allObservedSamples"],31)
            self.assertEqual(trial["currentRequestSamples"],30)
            self.assertEqual(trial["passedSamples"],30)
            self.assertEqual(trial["captureToCompletionUs"]["maximum"],150001)
            self.assertEqual(trial["latencyTarget"]["status"],"FAIL")
            self.assertTrue(runner.cleared)


if __name__ == "__main__":
    unittest.main()
