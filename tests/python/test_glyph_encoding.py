"""Exhaustive RGB565 coverage of lossless two-bit glyph-bank classes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/lib"))
import unittest

import numpy as np
from PIL import Image
from vision_reference import colourMask
from projective_reference import whiteProfileFor, whitePixelsFor, packedGlyphClasses


class GlyphEncodingTests(unittest.TestCase):
    def testAllRgb565WordsDecodeThreeIndependentPredicates(self):
        values = np.arange(65536, dtype=np.uint32)
        red, green, blue = values >> 11, (values >> 5) & 63, values & 31
        rgb = np.stack(((red << 3) | (red >> 2), (green << 2) | (green >> 4),
                        (blue << 3) | (blue >> 2)), axis=1).astype(np.uint8).reshape(256, 256, 3)
        # Floors zero cover a superset of every permitted unsigned floor.
        # Increasing either calibrated floor cannot introduce overlap.
        foreground = np.array(colourMask(Image.fromarray(rgb), 0, 0, colourAlgorithm=1)).reshape(256, 256) != 0
        profile = whiteProfileFor(3)
        packed = packedGlyphClasses(rgb, foreground, profile)
        rounded = whitePixelsFor(rgb, profile)
        strict = whitePixelsFor(rgb, profile, anchor=True)
        np.testing.assert_array_equal(packed == 1, foreground)
        np.testing.assert_array_equal((packed & 2) != 0, rounded)
        np.testing.assert_array_equal(packed == 3, strict)
        self.assertFalse(np.any(foreground & rounded))
        self.assertEqual(int(((packed & 2) != 0).sum()), 6336)
        self.assertEqual(int((packed == 2).sum()), 56)

    def testMeasuredBoundaryAndHistoricalReader2RemainDistinct(self):
        pixels = np.array([[[82, 93, 115], [99, 109, 140], [16, 24, 33]]], dtype=np.uint8)
        self.assertEqual(whitePixelsFor(pixels, whiteProfileFor(2)).tolist(), [[False, True, False]])
        self.assertEqual(whitePixelsFor(pixels, whiteProfileFor(3)).tolist(), [[True, True, False]])
        self.assertEqual(whitePixelsFor(pixels, whiteProfileFor(3), anchor=True).tolist(), [[False, True, False]])
        self.assertEqual(whiteProfileFor(2)["sumMinimum"], 384)
        self.assertNotIn("anchorSumMinimum", whiteProfileFor(2))
        for minimum, spread in ((95, 64), (96, 63)):
            with self.assertRaises(ValueError):
                whiteProfileFor(3, minimum, spread)

    def testInvalidOverlapCannotSilentlyOverwriteColour(self):
        # An incompatible future colour rule must fail rather than reinterpret
        # bright white as colour or use an undocumented fifth storage class.
        with self.assertRaisesRegex(ValueError, "overlap"):
            packedGlyphClasses(np.array([[[255, 255, 255]]]), [[True]], whiteProfileFor(3))

    def testReader4AllRgb565ValuesRemainLosslessWithoutAnotherRamPlane(self):
        values = np.arange(65536, dtype=np.uint32)
        red, green, blue = values >> 11, (values >> 5) & 63, values & 31
        rgb = np.stack(((red << 3) | (red >> 2), (green << 2) | (green >> 4),
                        (blue << 3) | (blue >> 2)), axis=1).astype(np.uint8).reshape(256, 256, 3)
        foreground = np.array(colourMask(Image.fromarray(rgb), 0, 0, colourAlgorithm=2)).reshape(256, 256) != 0
        profile = whiteProfileFor(4)
        strokes = whitePixelsFor(rgb, profile)
        strict = whitePixelsFor(rgb, profile, anchor=True)
        packed = packedGlyphClasses(rgb, foreground, profile)
        self.assertFalse(np.any(strict & ~strokes), 'Strong anchor white must remain a subset')
        self.assertFalse(np.any(foreground & strokes), 'No calibrated V may create a fifth class')
        np.testing.assert_array_equal(packed == 1, foreground)
        np.testing.assert_array_equal((packed & 2) != 0, strokes)
        np.testing.assert_array_equal(packed == 3, strict)
        np.testing.assert_array_equal(strict, whitePixelsFor(rgb, whiteProfileFor(2)))

    def testReader4MeasuredDimStrokeAndColourBoundary(self):
        # Real frame31285 C-stroke; saturated examples would alias colour if
        # the lower brightness floor were applied without its S<1/2 condition.
        pixels = np.array([[[82,85,99], [57,81,115], [57,113,115], [16,12,33], [90,16,12]]], dtype=np.uint8)
        profile = whiteProfileFor(4)
        self.assertEqual(whitePixelsFor(pixels, profile).tolist(), [[True,False,True,False,False]])
        self.assertEqual(whitePixelsFor(pixels, profile, anchor=True).tolist(), [[False,False,True,False,False]])
        self.assertEqual(whitePixelsFor(pixels, whiteProfileFor(3)).tolist(), [[False,False,True,False,False]])
        image = Image.fromarray(pixels)
        self.assertEqual(colourMask(image,0,0,colourAlgorithm=1), [0,2,0,0,0])
        self.assertEqual(colourMask(image,0,0,colourAlgorithm=2), [0,2,0,2,0])
        for minimum, spread in ((96,64),(84,63)):
            with self.assertRaises(ValueError):whiteProfileFor(4,minimum,spread)


if __name__ == "__main__":
    unittest.main()
