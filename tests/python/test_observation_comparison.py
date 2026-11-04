"""Synthetic host records only; these tests do not establish camera acceptance."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import compare_observations as comparison


def run(number, bypass):
    profile = {key: 1 for key in comparison.PROFILE_FIELDS}
    profile.update(buildId=0xE7070004, debugSchemaVersion=8, contractVersion=3,
                   redMinimum=41, blueMinimum=37, poolLayout="shared16")
    rows = []
    for i in range(3):
        c = dict(mode="VISION_ONLY", inputSource="REAL_CAMERA", digit=1, switchMask=1, stableMask=1,
                 selection="VALID", frameId=number * 10 + i, configVersion=2, requestTag=3,
                 rawCameraMode=False, sourceHealthyFresh=i != 1, targetObserved=i != 1,
                 targetLockedFresh=i != 1, taskArmed=False, motionPermit=False, state="IDLE")
        b = {**profile, "frameId": 100 + number * 10 + i, "configVersion": 2,
             "captureStartUs": i * 40000, "completionUs": i * 40000 + 25000, "processingLatencyUs": 25000,
             "status": {"activeCfgVersion": 2}, "activeRequest": {"operation": 1, "markerType": 1, "digit": 1, "requestTag": 3},
             "bypassPerspective": bypass, "rawCameraMode": False, "rawModeRequested": False, "rawDisplayActive": False,
             "frameGood": i != 1, "freshAtSnapshot": True, "candidateOverflow": i == 1}
        b["targetReport"] = dict(targetSelected=True, markerType=1, digit=1, requestTag=3,
                                  configVersion=2, frameId=b["frameId"], captureStartUs=b["captureStartUs"],
                                  frameGood=i != 1, ambiguous=False, observed=i != 1, locked=i != 1)
        rows.append({"index": i, "complete": True,
                     "cctl": {"readStartSeconds": i, "readEndSeconds": i + .1, "state": c},
                     "bctl": {"readStartSeconds": i + .1, "readEndSeconds": i + .3, "state": b}})
    return {"schema": "echo7-observation-v1", "status": "COMPLETE", "label": "SYNTHETIC HOST TEST",
            "startedAtUtc": f"2026-01-01T00:00:{number:02d}+00:00", "requestedSamples": 3,
            "inputSource": "LIVE_FPGA_JTAG_READONLY", "transport": "ONE_PERSISTENT_JTAG_SESSION",
            "operations": ["STATUS", "BSTATUS"], "samples": rows}


class ObservationComparisonTests(unittest.TestCase):
    def groups(self): return [run(i, False) for i in range(3)], [run(i + 3, True) for i in range(3)]

    def test_paired_summary_retains_bad_frames_without_equating_c_and_b_frame_ids(self):
        result = comparison.compare(*self.groups(), "synthetic unchanged-condition statement")
        self.assertEqual(result["status"], "COMPARISON_VALID")
        for pair in result["pairs"]:
            self.assertEqual(pair["normal"]["bctl"]["distinctFrames"]["badFrames"], 1)
            self.assertEqual(pair["normal"]["bctl"]["distinctFrames"]["locked"], 2)
            self.assertEqual(pair["normal"]["cctl"]["distinctFrames"]["healthy"], 2)

    def test_held_bad_frame_is_retained_but_does_not_become_a_new_frame(self):
        data = run(0, False)
        data["samples"][2]["bctl"]["state"] = copy.deepcopy(data["samples"][1]["bctl"]["state"])
        result = comparison.assess_run(data, False)
        self.assertEqual(result["bctl"]["allPolls"]["badFrames"], 2)
        self.assertEqual(result["bctl"]["distinctFrames"]["badFrames"], 1)
        self.assertEqual(result["bctl"]["heldPolls"], 1)

    def test_conditions_missing_never_claims_valid_comparison(self):
        self.assertEqual(comparison.compare(*self.groups(), "")["status"], "UNCONFIRMED_CONDITIONS")

    def test_profile_target_raw_mode_and_reused_trial_are_rejected(self):
        mutations = [lambda groups: groups[1][0]["samples"][0]["bctl"]["state"].update(blueMinimum=20),
                     lambda groups: groups[0][0]["samples"][0]["cctl"]["state"].update(digit=2),
                     lambda groups: groups[0][0]["samples"][0]["bctl"]["state"].update(rawDisplayActive=True),
                     lambda groups: groups[1][0].update(startedAtUtc=groups[0][0]["startedAtUtc"]),
                     lambda groups: groups[0][0]["samples"][0]["bctl"]["state"].update(processingLatencyUs=999)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                groups = self.groups(); mutate(groups)
                with self.assertRaises(ValueError): comparison.compare(*groups, "synthetic conditions")


if __name__ == "__main__": unittest.main()
