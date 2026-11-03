"""Recorded-schema crop selection; synthetic metadata is not camera evidence."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from measure_recorded_scene import presentCandidates


class SceneSlotTests(unittest.TestCase):
    def testSharedBlueNineAndInterleavedRedAreNotEightPerColour(self):
        colours = [True, False] + [True]*7 + [False, True]
        markers = [dict(index=i, isBlue=colours[i] if i < len(colours) else False) for i in range(16)]
        result = presentCandidates(dict(debugSchemaVersion=8, redCandidateCount=2,
            blueCandidateCount=9, markers=markers))
        self.assertEqual([item['index'] for item in result], list(range(11)))

    def testHistoricalSplitEightAndSixteenRetainTheirOffsets(self):
        for schema, capacity in ((5, 8), (6, 16)):
            markers = [dict(index=i, isBlue=i >= capacity) for i in range(capacity*2)]
            result = presentCandidates(dict(debugSchemaVersion=schema, redCandidateCount=2,
                blueCandidateCount=3, markers=markers))
            self.assertEqual([item['index'] for item in result], [0, 1, capacity, capacity+1, capacity+2])

    def testMalformedCapacityArrayAndColourFailBeforeCropping(self):
        base = dict(debugSchemaVersion=8, redCandidateCount=0, blueCandidateCount=1,
            markers=[dict(index=i, isBlue=True) for i in range(16)])
        for changes in (dict(redCandidateCount=16), dict(blueCandidateCount=17),
                        dict(markers=base['markers'][:-1]), dict(blueCandidateCount=-1),
                        dict(redCandidateCount=1, blueCandidateCount=0)):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                presentCandidates({**base, **changes})


if __name__ == '__main__':
    unittest.main()
