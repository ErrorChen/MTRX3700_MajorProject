"""Independent graph-oracle checks for four-bit active15/output8 capacity.

Generated combs exercise capacity boundaries; they do not recreate the missing
pixels of live frame16493, whose status motivated testing a larger active pool.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/lib'))
from candidates_reclaimed_model import candidates_reclaimed
from debug_decode import decodeWords


def combMask(seeds):
    """Tall individual stems join on the last row, preserving their exact area."""
    width = 4 * (seeds - 1) + 1
    return [[1 if x % 4 == 0 or y == 24 else 0 for x in range(width)] for y in range(25)]


class Capacity15Tests(unittest.TestCase):
    def testThirteenAndFifteenMergeWithExactArea(self):
        for seeds in (13, 15):
            with self.subTest(seeds=seeds):
                mask = combMask(seeds)
                old = candidates_reclaimed(mask, active_capacity=12, prune_unusable=True)
                current = candidates_reclaimed(mask, active_capacity=15, prune_unusable=True)
                self.assertTrue(old['red_active_overflow'])
                self.assertFalse(current['overflow'])
                self.assertEqual(current['red_max_row_handles'], seeds)
                self.assertEqual(len(current['red']), 1)
                self.assertEqual(current['red'][0]['area'], seeds * 24 + len(mask[0]))
                self.assertEqual(current['red'][0]['xmax'], len(mask[0]) - 1)

    def testSixteenthHandleRejectsEntireFrame(self):
        result = candidates_reclaimed(combMask(16), active_capacity=15, prune_unusable=True)
        self.assertTrue(result['red_active_overflow'])
        self.assertFalse(result['red_output_overflow'])
        self.assertFalse(result['frame_valid'])
        self.assertEqual(result['red'], [])
        self.assertEqual(result['blue'], [])
        self.assertEqual(result['red_max_row_handles'], 16)

    def testOutputPoolStillEight(self):
        mask = [[1] if y % 2 == 0 else [0] for y in range(17)]
        result = candidates_reclaimed(mask, min_area=1, active_capacity=15)
        self.assertFalse(result['red_active_overflow'])
        self.assertTrue(result['red_output_overflow'])
        self.assertFalse(result['frame_valid'])

    def testBothColoursUseFullNonzeroLabelRange(self):
        red = combMask(15)
        mask = [row + [0] + [2 if pixel else 0 for pixel in row] for row in red]
        result = candidates_reclaimed(mask, active_capacity=15, prune_unusable=True)
        self.assertFalse(result['overflow'])
        self.assertEqual(result['red_max_row_handles'], 15)
        self.assertEqual(result['blue_max_row_handles'], 15)
        self.assertEqual((result['red'][0]['area'], result['blue'][0]['area']), (417, 417))

    def testSchemaFourCarriesFifteenAndRejectsImpossibleCapacity(self):
        words = [0] * 96
        words[0] = 0x45425031
        words[1] = 0x00040002
        words[93] = (8 << 16) | (15 << 8) | 0xff
        result = decodeWords(words)
        self.assertEqual(result['activeCandidateCapacity'], 15)
        self.assertEqual(result['outputCandidateCapacity'], 8)
        self.assertEqual(result['allocationPeakRed'], 15)
        self.assertEqual(result['allocationPeakBlue'], 15)
        for invalid in (0, 16):
            with self.subTest(capacity=invalid):
                words[93] = (8 << 16) | (invalid << 8)
                with self.assertRaises(ValueError):
                    decodeWords(words)
                with self.assertRaises(ValueError):
                    candidates_reclaimed([[0]], min_area=1, active_capacity=invalid)


if __name__ == '__main__':
    unittest.main()
