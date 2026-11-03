"""Scaled calibration geometry/purity checks; synthetic tests are not board evidence."""
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lib'))
from audit_calibration import paired, sample


def rotate(box,rotation):
    x0,y0,x1,y1=box
    return ((20+x0,10+y0,20+x1,10+y1),
            (250-y1,20+x0,250-y0,20+x1),
            (220-x1,235-y1,220-x0,235-y0),
            (20+y0,220-x1,20+y1,220-x0))[rotation]


class ReferencePairingTests(unittest.TestCase):
    def checkAllRotations(self,card,reference,expected):
        for rotation in range(4):
            with self.subTest(rotation=rotation,card=card,reference=reference):
                nativeCard,nativeReference=rotate(card,rotation),rotate(reference,rotation)
                self.assertEqual(paired(nativeCard,nativeReference,rotation),expected)
                if expected:self.assertFalse(paired(nativeCard,nativeReference,rotation^2))

    def testMeasuredFrame30158NoLongerFailsOneBBoxEdge(self):
        # Numbers transcribed from CRC/frame-bound capture30158. No image file
        # or answer manifest is required at runtime or by this geometric test.
        card=(36,5,107,94);reference=(41,96,108,116)
        self.assertFalse(paired(card,reference,pairingAlgorithm=1))
        self.assertTrue(paired(card,reference))
        self.checkAllRotations((0,0,71,89),(5,91,72,111),True)

    def testCentreToleranceScalesAndRejectsTheFirstOutsidePixel(self):
        for scale in range(1,5):
            width,height=24*scale,30*scale
            card=(0,0,width-1,height-1);top=height+scale;bottom=top+6*scale-1
            tolerance=(width+15)//16
            self.checkAllRotations(card,(2*scale,top,25*scale-1,bottom),True)
            for sign in (-1,1):
                for outside in (0,1):
                    shift=sign*(tolerance+outside)
                    self.checkAllRotations(card,(shift,top,width-1+shift,bottom),not outside)
        # A universal4px rule would accept this at the small scale. The new
        # tolerance isceil24/16=2px and must reject the same3px displacement.
        self.checkAllRotations((0,0,23,29),(3,31,26,36),False)

    def testWidthHeightGapAndOverlapAreStillRequired(self):
        for scale in range(1,5):
            width,height=24*scale,30*scale;card=(0,0,width-1,height-1)
            top=height+scale;refHeight=6*scale
            for refWidth,expected in [((width*8+9)//10,True),((width*8+9)//10-1,False),
                                      (width*12//10,True),(width*12//10+1,False)]:
                left=(width-refWidth)//2
                self.checkAllRotations(card,(left,top,left+refWidth-1,top+refHeight-1),expected)
            for heightOfReference,expected in [(height//10,True),(height//10-1,False),
                                                (height*3//10,True),(height*3//10+1,False)]:
                self.checkAllRotations(card,(0,top,width-1,top+heightOfReference-1),expected)
            for gap,expected in [(height//8,True),(height//8+1,False),(-1,False)]:
                self.checkAllRotations(card,(0,height+gap,width-1,height+gap+refHeight-1),expected)
        self.assertFalse(paired((10,10,10,19),(11,20,11,21)))
        self.assertFalse(paired((10,10,9,19),(10,20,10,21)))

    def testDoubledCentresAvoidFlooringAwayHalfPixelFailure(self):
        # width72 ->tolerance5. Strip centre displacement5.5 must fail,
        # although separately floored centres would be only5pixels apart.
        self.checkAllRotations((0,0,71,89),(8,91,74,111),False)
        self.checkAllRotations((0,0,71,89),(7,91,74,111),True)

    def testNeighbouringBlueCardAndSecondReferenceStayDistinct(self):
        card=(0,0,71,89)
        self.checkAllRotations(card,(140,91,207,111),False)
        self.checkAllRotations(card,(5,91,72,160),False)
        # Both geometrically plausible strips must reach the existing core
        # uniqueness counter; neither can be silently picked as the reference.
        self.assertEqual(sum(paired(card,box) for box in [(5,91,72,99),(5,101,72,109)]),2)

    def testRawSamplingStillRejectsContaminationWithoutMaskFiltering(self):
        rgb=np.full((240,320,3),140,dtype=np.uint8)
        red=(36,5,107,94);blue=(41,96,108,116)
        rgb[5:95,36:108]=(96,12,12);rgb[96:117,41:109]=(16,28,80)
        baseline=sample(Image.fromarray(rgb),red,blue)
        self.assertTrue(baseline['frameSampleGood'])
        self.assertEqual(baseline['red']['sampleCount'],252)
        self.assertEqual(baseline['blue']['sampleCount'],492)
        for pixel in [(255,255,255),(0,0,0),(200,100,0),(0,0,255)]:
            with self.subTest(pixel=pixel):
                dirty=rgb.copy();dirty[106,75]=pixel
                result=sample(Image.fromarray(dirty),red,blue)
                self.assertFalse(result['frameSampleGood'])
                self.assertEqual(result['blue']['sampleCount'],492)

    def testUnsupportedModelSettingsReject(self):
        for kwargs in [{'rotation':4},{'pairingAlgorithm':3}]:
            with self.assertRaises(ValueError):paired((0,0,71,89),(5,91,72,111),**kwargs)


if __name__=='__main__':unittest.main()
