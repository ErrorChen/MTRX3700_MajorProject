import sys as _sys
from pathlib import Path as _Path
_repositoryRoot=_Path(__file__).resolve().parents[2]
_sys.path[:0]=[str(_repositoryRoot/"tools/lib"),str(_repositoryRoot/"tools"),str(_repositoryRoot/"tests/python")]
"""Independent HSV equivalence and edge-preserving horizontal support tests."""
import colorsys
import unittest
import numpy as np
from PIL import Image
from vision_reference import colourMask,horizontalRunSupport


class HsvTests(unittest.TestCase):
    def test_integer_predicate_matches_hsv_formula(self):
        # Exhaust every native RGB565 code, with independent floating-point HSV.
        pixels=[];expected=[]
        for value in range(65536):
            r5=(value>>11)&31;g6=(value>>5)&63;b5=value&31
            r=(r5<<3)|(r5>>2);g=(g6<<2)|(g6>>4);b=(b5<<3)|(b5>>2)
            pixels.append((r,g,b));h,s,v=colorsys.rgb_to_hsv(r/255,g/255,b/255);h*=360
            red=(h>=336-1e-9 or h<=1e-9) and s>=0.5-1e-9 and v*255>=48-1e-9
            blue=200-1e-9<=h<=250+1e-9 and s>=0.5-1e-9 and v*255>=32-1e-9
            expected.append(1 if red else 2 if blue else 0)
        image=Image.new('RGB',(256,256));image.putdata(pixels)
        self.assertEqual(colourMask(image,48,32,colourAlgorithm=1),expected)

    def test_run_support_keeps_complete_runs_and_row_boundary(self):
        rows=np.array([[1,1,1,0,2,2,0,1,0,2,2,2],
                       [2,0,1,1,1,1,0,2,2,2,0,1]],dtype=np.uint8)
        expected=np.array([[1,1,1,0,0,0,0,0,0,2,2,2],
                           [0,0,1,1,1,1,0,2,2,2,0,0]],dtype=np.uint8)
        np.testing.assert_array_equal(horizontalRunSupport(rows),expected)

    def test_formal_red_zero_hue_and_orange_distinction(self):
        image=Image.new('RGB',(4,1));image.putdata([(192,0,0),(66,8,16),(148,36,24),(16,24,66)])
        self.assertEqual(colourMask(image,48,32,colourAlgorithm=1),[1,1,0,2])
        self.assertEqual(colourMask(image,64,32,colourAlgorithm=0),[1,1,1,2])


if __name__=='__main__':unittest.main(verbosity=2)
