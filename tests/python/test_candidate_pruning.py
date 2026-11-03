"""Size-gate capacity checks; all inputs here are synthetic pixel masks."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/lib"))
import unittest
import hashlib
import json
from PIL import Image
from candidates_reclaimed_model import candidates_reclaimed, usable_candidate_size


def blank():
    return [[0] * 320 for _ in range(240)]


def rectangle(mask, colour, x, y, width, height):
    for row in range(y, y + height):
        mask[row][x:x + width] = [colour] * width


class CandidatePruningTests(unittest.TestCase):
    def testRecordedFrame10699UsesCapturedProfileAndPreservesRetainedBoxes(self):
        # Recorded camera pixels are replayed offline. This does not rerun the
        # camera, qualify reader IDs or turn the original bad frame into a
        # passing hardware result.
        from vision_reference import recognise
        evidence = Path(__file__).resolve().parents[2] / "tests/fixtures/camera/frame10699"
        index = json.loads((evidence / "index.json").read_text())
        imagePath = evidence / "frame.png"
        self.assertEqual(hashlib.sha256(imagePath.read_bytes()).hexdigest(), index["files"][imagePath.name])
        self.assertEqual((index["configVersion"], index["redMinimum"], index["blueMinimum"]), (1, 32, 28))
        results = [recognise(Image.open(imagePath).convert("RGB"),redMin=index["redMinimum"],
            blueMin=index["blueMinimum"],colourAlgorithm=1,whiteMin=96,cleanup=True,pruneUnusable=prune)
            for prune in (False, True)]
        old, new = results
        self.assertEqual(old["candidateCounts"], {"red":5,"blue":10})
        self.assertTrue(old["overflow"])
        self.assertEqual(new["candidateCounts"], {"red":2,"blue":8})
        self.assertFalse(new["overflow"])
        oldBoxes = {(m["colour"],tuple(m["bbox"]),m["area"]) for m in old["markers"]}
        newBoxes = {(m["colour"],tuple(m["bbox"]),m["area"]) for m in new["markers"]}
        self.assertTrue(newBoxes.issubset(oldBoxes))
        for colour in ("red","blue"):
            for field in ("active_overflow","max_row_handles","lifetime_seeds","total_retired"):
                self.assertEqual(old["boundedCandidateOracle"][colour+"_"+field],
                                 new["boundedCandidateOracle"][colour+"_"+field])

    def testRetiredFragmentsCannotExhaustCompletedPool(self):
        mask = blank()
        for i in range(12):
            rectangle(mask, 2, 10, 2 + 5*i, 20, 2)
        rectangle(mask, 2, 50, 100, 24, 24)
        old = candidates_reclaimed(mask)
        explicitOld = candidates_reclaimed(mask, prune_unusable=False)
        new = candidates_reclaimed(mask, prune_unusable=True)
        self.assertEqual(old, explicitOld)
        self.assertTrue(old["blue_output_overflow"])
        self.assertFalse(new["overflow"])
        self.assertEqual(new["blue_size_rejected"], 12)
        self.assertEqual(len(new["blue"]), 1)
        self.assertEqual(new["blue"][0]["area"], 576)
        self.assertEqual(new["blue"][0]["xmin"], 50)
        for field in ("max_row_handles", "lifetime_seeds", "total_retired"):
            self.assertEqual(old["blue_" + field], new["blue_" + field])

    def testRealNinthCandidateStillOverflows(self):
        mask = blank()
        for i in range(9):
            rectangle(mask, 2, 10 + 50*(i % 3), 10 + 50*(i // 3), 24, 24)
        result = candidates_reclaimed(mask, prune_unusable=True)
        self.assertTrue(result["blue_output_overflow"])
        self.assertFalse(result["blue_active_overflow"])
        self.assertEqual(result["blue_qualifying_completed"], 9)
        self.assertFalse(result["frame_valid"])

    def testActiveOverflowIsNeverFiltered(self):
        mask = blank()
        for i in range(9):
            rectangle(mask, 2, 10 + 10*i, 10, 4, 8)
        for prune in (False, True):
            result = candidates_reclaimed(mask, prune_unusable=prune)
            self.assertTrue(result["blue_active_overflow"])
            self.assertTrue(result["overflow"])
            self.assertEqual(result["blue_max_row_handles"], 9)

    def testReferenceAndMainSizeBoundaries(self):
        for width, height in ((20, 3), (3, 20), (24, 24), (320, 3), (3, 240)):
            self.assertTrue(usable_candidate_size(width, height, 2))
        for width, height in ((19, 3), (3, 19), (20, 2), (2, 20), (19, 19)):
            self.assertFalse(usable_candidate_size(width, height, 2))
        self.assertTrue(usable_candidate_size(24, 24, 1))
        for width, height in ((23, 24), (24, 23), (100, 3)):
            self.assertFalse(usable_candidate_size(width, height, 1))
        mask = blank()
        rectangle(mask, 2, 10, 10, 20, 3)
        rectangle(mask, 2, 50, 10, 3, 20)
        rectangle(mask, 1, 100, 10, 24, 24)
        result = candidates_reclaimed(mask, prune_unusable=True)
        self.assertFalse(result["overflow"])
        self.assertEqual([box["area"] for box in result["blue"]], [60, 60])
        self.assertEqual(result["red"][0]["area"], 576)


if __name__ == "__main__":
    unittest.main()
