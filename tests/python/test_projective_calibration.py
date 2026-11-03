"""Scale320/floor-Q4 geometry tests; synthetic inputs are not board evidence."""
from pathlib import Path
import math
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lib'))
from projective_calibration import (EXPECTED_STRIP,halfQuadCoefficients,
    mapCalibrationPoint,pairReference,polygonContains,positiveConvex)


def expandNativeQuad(points):
    """Independent direct transcription of the reader's radial half expansion."""
    sumX=sum(p[0] for p in points);sumY=sum(p[1] for p in points)
    return [[2*x+((4*x>sumX)-(4*x<sumX)),2*y+((4*y>sumY)-(4*y<sumY))] for x,y in points]


def nativeBox(points):
    return [min(p[0] for p in points),min(p[1] for p in points),
            max(p[0] for p in points),max(p[1] for p in points)]


def transform(points,matrix):
    result=[]
    for x,y in points:
        point=matrix@np.array([x,y,1.])
        result.append([int(math.floor(point[0]/point[2]+.5)),int(math.floor(point[1]/point[2]+.5))])
    return result


def calibrationCases():
    """Explicit inputs for host tests and the independent RTL vector consumer.

    No candidate slot implies a digit. Names describe geometry only. Native
    quads are rounded before the production half expansion; the original
    scale320 artwork approximation is not reused as the synthetic ground truth.
    """
    unit=((0,0),(1,0),(1,1),(0,1));bar=((0,47/45),(1,47/45),(1,56/45),(0,56/45))
    centre=np.array([[1,0,-.5],[0,1,-.5],[0,0,1.]])
    translation=np.array([[1,0,160],[0,1,120],[0,0,1.]])
    for angle in range(0,360,10):
        c,s=math.cos(math.radians(angle)),math.sin(math.radians(angle))
        for width in (24,32,40,60,80):
            scaleRotation=np.array([[width*c,-width*1.125*s,0],[width*s,width*1.125*c,0],[0,0,1.]])
            for profile,(px,py) in enumerate(((0,0),(.12,.08),(-.08,.12))):
                perspective=np.array([[1,0,0],[0,1,0],[px,py,1.]])
                matrix=translation@scaleRotation@perspective@centre
                red=transform(unit,matrix);blue=transform(bar,matrix)
                yield {'name':f'geometry_a{angle}_w{width}_p{profile}',
                    'category':'NOMINAL_GEOMETRY_POSITIVE','angle':angle,'width':width,
                    'projectiveTerms':[px,py],'redQuadHalf':expandNativeQuad(red),
                    'blueQuadHalf':expandNativeQuad(blue),'redBox':nativeBox(red),'blueIsBay':False}
    red=[[110,40],[170,40],[170,108],[110,108]]
    negative={'partly_over_red':((0,.95),(1,.95),(1,1.15),(0,1.15)),
        'excessive_gap':((0,1.15),(1,1.15),(1,1.35),(0,1.35)),
        'wrong_side':((0,-.25),(1,-.25),(1,-.05),(0,-.05)),
        'lateral_shift':((.2,47/45),(1.2,47/45),(1.2,56/45),(.2,56/45)),
        'too_thick':((0,47/45),(1,47/45),(1,47/45+.5),(0,47/45+.5)),
        'too_thin':((0,47/45),(1,47/45),(1,47/45+.04),(0,47/45+.04))}
    matrix=np.array([[60,0,110],[0,68,40],[0,0,1.]])
    for name,points in negative.items():
        blue=transform(points,matrix)
        yield {'name':name,'category':'WRONG_REFERENCE','redQuadHalf':expandNativeQuad(red),
            'blueQuadHalf':expandNativeQuad(blue),'redBox':nativeBox(red),'blueIsBay':False}
    # Actual recorded frame15078, independently detected native component
    # corners. This does not create another independent recording or claim a
    # completed eight-frame calibration. The maintained fixture supplies pixels.
    yield {'name':'recorded_frame15078','category':'RECORDED_GEOMETRY',
        'redQuadHalf':[[247,1],[353,33],[343,175],[233,153]],
        'blueQuadHalf':[[231,161],[337,181],[341,207],[231,193]],
        'redBox':[117,1,176,87],'blueIsBay':False}
    baseline={'redQuadHalf':[[199,79],[319,79],[319,215],[199,215]],
        'blueQuadHalf':[[199,221],[319,221],[319,249],[199,249]],
        'redBox':[100,40,159,107],'blueIsBay':False}
    invalids={
        'accepted_bay':{'blueIsBay':True},
        'red_invalid_flag':{'redQuadValid':False},
        'blue_invalid_flag':{'blueQuadValid':False},
        'box_invalid_flag':{'redBoxValid':False},
        'red_box_outside':{'redBox':[100,40,320,107]},
        'red_box_reversed':{'redBox':[100,40,99,107]},
        'blue_reverse_winding':{'blueQuadHalf':list(reversed(baseline['blueQuadHalf']))},
        'blue_duplicate_corner':{'blueQuadHalf':[[199,221],[199,221],[319,249],[199,249]]},
        'red_outside_halfpixel':{'redQuadHalf':[[199,-2],[319,-2],[319,215],[199,215]]},
        'blue_outside_halfpixel':{'blueQuadHalf':[[519,221],[640,221],[640,249],[519,249]]},
        'tiny_rounded_red_roi':{'redQuadHalf':[[200,200],[201,200],[201,201],[200,201]],
            'blueQuadHalf':[[200,202],[201,202],[201,203],[200,203]],'redBox':[100,100,100,100]}}
    for name,changed in invalids.items():
        yield {'name':name,'category':'INVALID_GEOMETRY',**baseline,**changed}
    # Append-only vector additions: actual integer projections, not assumed
    # failures based solely on small dimensions. The first ROI has a zero
    # cross after floor-Q4 mapping despite a positive-convex input quad.
    for name,quad,box in (
        ('rounded_red_roi_zero_cross',[[210,208],[212,210],[212,213],[211,211]],[105,104,106,107]),
        ('extrapolated_reference_pole',[[213,204],[215,202],[214,215],[210,209]],[105,101,108,108]),
        ('expected_reference_outside_image',[[199,339],[319,339],[319,475],[199,475]],[100,170,159,237])):
        yield {'name':name,'category':'INVALID_GEOMETRY',**baseline,'redQuadHalf':quad,'redBox':box}
    blue=[[231,161],[337,181],[341,207],[231,193]]
    for shift in (1,2,3):
        yield {'name':f'frame15078_blue_start_{shift}','category':'RECORDED_GEOMETRY',
            'redQuadHalf':[[247,1],[353,33],[343,175],[233,153]],
            'blueQuadHalf':blue[shift:]+blue[:shift],
            'redBox':[117,1,176,87],'blueIsBay':False}


class ProjectiveCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.red=[[199,79],[319,79],[319,215],[199,215]]
        self.blue=[[199,221],[319,221],[319,249],[199,249]]
        self.box=[100,40,159,107]

    def pair(self,**changes):
        values={'redQuadHalf':self.red,'blueQuadHalf':self.blue,'redBox':self.box,'blueIsBay':False}
        values.update(changes);return pairReference(**values)

    def testMapperFloorIncludingNegativeAndRangeRejection(self):
        coefficients=[1,0,0,0,1,0,0,0,1]
        self.assertEqual(mapCalibrationPoint(coefficients,-1,1),[-1,0])
        self.assertEqual(mapCalibrationPoint(coefficients,-40,40),[-1,1])
        self.assertEqual(mapCalibrationPoint(coefficients,-41,41),[-2,1])
        self.assertIsNone(mapCalibrationPoint([0]*9,0,0))
        self.assertIsNone(mapCalibrationPoint([0,0,4096,0,0,0,0,0,1],0,0))
        self.assertEqual(mapCalibrationPoint([0,0,-4096,0,0,0,0,0,1],0,0),[-32768,0])

    def testFormalApproximationBoundIsRecordedExactly(self):
        from fractions import Fraction
        self.assertEqual(EXPECTED_STRIP,((0,334),(320,334),(320,398),(0,398)))
        for integer,formal in ((334,Fraction(47,45)),(398,Fraction(56,45))):
            self.assertEqual(abs(Fraction(integer,320)-formal),Fraction(1,1440))

    def testIdentityForwardHAndOwnInsets(self):
        coefficients=halfQuadCoefficients(self.red)
        self.assertEqual(mapCalibrationPoint(coefficients,0,0),[1592,632])
        self.assertEqual(mapCalibrationPoint(coefficients,320,320),[2552,1720])
        result=self.pair();self.assertTrue(result['pairValid'])
        self.assertEqual(result['cyclicMatchCount'],1)
        self.assertEqual(result['redPolygon'],[[1670,958],[1766,958],[1766,1393],[1670,1393]])
        self.assertEqual(result['bluePolygon'],[[1784,1812],[2360,1812],[2360,1947],[1784,1947]])
        # Moving the actual strip changes its own sampling polygon. It cannot
        # sample the predicted position while ignoring the measured component.
        moved=self.pair(blueQuadHalf=[[x,y+2] for x,y in self.blue])
        self.assertTrue(moved['pairValid']);self.assertNotEqual(result['bluePolygon'],moved['bluePolygon'])

    def testCyclicOrderDoesNotInventAnIdentity(self):
        baseline=self.pair();points=set(map(tuple,baseline['bluePolygon']))
        for shift in range(4):
            value=self.pair(blueQuadHalf=self.blue[shift:]+self.blue[:shift])
            self.assertTrue(value['pairValid']);self.assertEqual(value['cyclicMatchCount'],1)
            self.assertEqual(set(map(tuple,value['bluePolygon'])),points)
            self.assertEqual(value['bluePolygon'],baseline['bluePolygon'])
        self.assertFalse(self.pair(blueIsBay=True)['pairValid'])

    def testInvalidGeometryAndOutputsFailClosed(self):
        variants=[{'blueQuadHalf':list(reversed(self.blue))},
            {'blueQuadHalf':[self.blue[0],self.blue[0],self.blue[2],self.blue[3]]},
            {'blueQuadHalf':[[x+500,y] for x,y in self.blue]},
            {'redQuadHalf':[[x,-2 if i<2 else y] for i,(x,y) in enumerate(self.red)]},
            {'redBox':[100,40,400,107]},{'redBox':[100,40,99,107]}]
        for kwargs in variants:
            with self.subTest(kwargs=kwargs):
                result=self.pair(**kwargs);self.assertFalse(result['pairValid'])
                self.assertEqual(result['redPolygon'],[[0,0]]*4)
                self.assertEqual(result['bluePolygon'],[[0,0]]*4)

    def testRecordedRotatedInputAndAllExplicitWrongReferences(self):
        for case in calibrationCases():
            if case['category']=='NOMINAL_GEOMETRY_POSITIVE':continue
            result=pairReference(**{k:case[k] for k in ('redQuadHalf','blueQuadHalf','redBox','blueIsBay',
                'redQuadValid','blueQuadValid','redBoxValid') if k in case})
            with self.subTest(name=case['name']):
                self.assertEqual(result['pairValid'],case['category']=='RECORDED_GEOMETRY')

    def testScaleRotationPerspectiveMatrixRetainsRejects(self):
        rejected=[];total=0
        for case in calibrationCases():
            if case['category']!='NOMINAL_GEOMETRY_POSITIVE':continue
            total+=1
            result=pairReference(**{k:case[k] for k in ('redQuadHalf','blueQuadHalf','redBox','blueIsBay')})
            if not result['pairValid']:rejected.append(case['name'])
        self.assertEqual(total,540)
        # This explicit expected reject set is established from the floor-Q4
        # matrix, not inherited from the older nearest-Q4 experiment.
        self.assertEqual(rejected,['geometry_a50_w24_p2','geometry_a140_w24_p2',
                                   'geometry_a230_w24_p2','geometry_a320_w24_p2'])

    def testNativeSamplingIncludesBoundaryWithoutMaskFiltering(self):
        poly=[[16,16],[48,16],[48,48],[16,48]]
        self.assertTrue(positiveConvex(poly))
        self.assertEqual([(x,y) for y in range(5) for x in range(5) if polygonContains(poly,x,y)],
                         [(x,y) for y in (1,2,3) for x in (1,2,3)])


if __name__=='__main__':unittest.main()
