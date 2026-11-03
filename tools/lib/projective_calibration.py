"""Forward-only calibration geometry oracle; all coordinates are explicit.

Inputs are the production reader's already-expanded half-pixel quads, ordered
clockwise in native image coordinates (positive screen-coordinate area). The
red quad starts at its independently recognised orientation anchor. Blue quad
start is arbitrary; exactly one cyclic correspondence must pass. This module
never infers a marker ID or reads a scene-manifest answer.

Canonical mapper inputs use scale320. Output vertices use native Q4, rounded
down, including negative values. This deliberately differs from the previous
build-only nearest-Q4 experiment and is the maintained hardware oracle.
"""
from __future__ import annotations

CALIBRATION_GEOMETRY_VERSION = 1
CANONICAL_SCALE = 320
EXPECTED_STRIP = ((0,334),(320,334),(320,398),(0,398))
RED_SAMPLE = ((26,96),(58,96),(58,224),(26,224))
BLUE_SAMPLE = ((64,64),(256,64),(256,256),(64,256))
# Each entry is (canonical axis, bound, corner indices, allowed cross sign).
# A u-line points along +v, so its right-hand side has cross<=0. A v-line
# points along +u, so its lower screen side has cross>=0. These signs require
# positive-area geometry and positive projective denominators throughout.
GUARDS = ((0,-32,(0,3),-1),(0,32,(0,3),1),
          (0,288,(1,2),-1),(0,352,(1,2),1),
          (1,320,(0,1),1),(1,360,(0,1),-1),
          (1,352,(2,3),1),(1,456,(2,3),-1))


def _quad(value):
    if len(value)!=4 or any(len(point)!=2 for point in value):
        raise ValueError('A quadrilateral requires four x,y pairs')
    if any(isinstance(v,bool) or not isinstance(v,int) for p in value for v in p):
        raise ValueError('Geometry coordinates must be integers')
    return [list(point) for point in value]


def cross(a,b,point):
    """Signed twice-triangle area; no division or centre rounding."""
    return (b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])


def positiveConvex(quad):
    return all(cross(quad[i],quad[(i+1)%4],quad[(i+2)%4])>0 for i in range(4))


def halfQuadCoefficients(quadHalf):
    """Integer forward H from signed11-bit half-pixel vertices.

    Coefficients retain half-pixel units. Normalise determinant sign, without
    normalising precision or computing an inverse. Degenerate/negative-winding
    input is rejected by pairReference; mapper tests may inspect it separately.
    """
    quad=_quad(quadHalf)
    if any(not -1024<=v<=1023 for point in quad for v in point):
        raise ValueError('Half-pixel input exceeds signed11-bit range')
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=quad
    dx1,dx2,dx3=x1-x2,x3-x2,x0-x1+x2-x3
    dy1,dy2,dy3=y1-y2,y3-y2,y0-y1+y2-y3
    determinant=dx1*dy2-dx2*dy1
    g=dx3*dy2-dx2*dy3;h=dx1*dy3-dx3*dy1
    values=[(x1-x0)*determinant+g*x1,(x3-x0)*determinant+h*x3,x0*determinant,
            (y1-y0)*determinant+g*y1,(y3-y0)*determinant+h*y3,y0*determinant,
            g,h,determinant]
    return [-v for v in values] if determinant<0 else values


def mapCalibrationPoint(coefficients,sampleU,sampleV):
    """Map scale320 canonical coordinates to signed Q4 using exact floor.

    Python // is floor for negative numerators. An RTL signed division that
    truncates toward zero needs an explicit negative-remainder correction.
    Nonpositive denominators fail closed; no coordinate clipping is performed.
    """
    a,b,c,d,e,f,g,h,z=coefficients
    denominator=g*sampleU+h*sampleV+z*CANONICAL_SCALE
    if denominator<=0:return None
    point=[8*(a*sampleU+b*sampleV+c*CANONICAL_SCALE)//denominator,
           8*(d*sampleU+e*sampleV+f*CANONICAL_SCALE)//denominator]
    return point if all(-32768<=value<=32767 for value in point) else None


def _mapPolygon(coefficients,canonical):
    points=[mapCalibrationPoint(coefficients,*point) for point in canonical]
    return None if any(point is None for point in points) else points


def _within(quad,xMin,xMax,yMin,yMax):
    return quad is not None and all(xMin<=x<=xMax and yMin<=y<=yMax for x,y in quad)


def _edgeSquared(quad):
    return [(quad[(i+1)%4][0]-quad[i][0])**2+
            (quad[(i+1)%4][1]-quad[i][1])**2 for i in range(4)]


def polygonContains(polygon,x,y):
    """Include a native pixel centre on a positive-convex Q4 polygon edge."""
    point=(x*16,y*16)
    return all(cross(polygon[i],polygon[(i+1)%4],point)>=0 for i in range(4))


def pairReference(redQuadHalf,blueQuadHalf,redBox,blueIsBay=False,
                  redQuadValid=True,blueQuadValid=True,redBoxValid=True):
    """Return geometry validity and each object's own inset sampling polygon.

    Coordinates in redBox are inclusive native xMin,yMin,xMax,yMax. This is a
    per-pair oracle: the caller must additionally require a unique recognised
    red1 and exactly one successful blue candidate in the same frame/config.
    Raw RGB count/purity, frame stability and commit permission remain separate
    required checks. A valid result is not a completed calibration.
    """
    red=_quad(redQuadHalf);blue=_quad(blueQuadHalf)
    redCoefficients=halfQuadCoefficients(red)
    blueCoefficients=halfQuadCoefficients(blue)
    if len(redBox)!=4:raise ValueError('redBox requires four inclusive bounds')
    xMin,yMin,xMax,yMax=redBox
    validBox=0<=xMin<=xMax<320 and 0<=yMin<=yMax<240
    tolerance=[((xMax-xMin+8)//8)*16,((yMax-yMin+8)//8)*16]
    expected=_mapPolygon(redCoefficients,EXPECTED_STRIP)
    actual=[[8*x,8*y] for x,y in blue]
    redSample=_mapPolygon(redCoefficients,RED_SAMPLE)
    blueSample=_mapPolygon(blueCoefficients,BLUE_SAMPLE)
    referenceGeometryGood=(redQuadValid and blueQuadValid and redBoxValid and
        validBox and not blueIsBay and _within(red,-1,639,-1,479) and
        _within(blue,-1,639,-1,479) and positiveConvex(red) and
        positiveConvex(blue) and expected is not None and positiveConvex(expected) and
        _within(expected,-8,5112,-8,3832) and _within(actual,-8,5112,-8,3832))
    sampleGeometryGood=(redSample is not None and blueSample is not None and
        positiveConvex(redSample) and positiveConvex(blueSample) and
        _within(redSample,0,5119,0,3839) and _within(blueSample,0,5119,0,3839))
    lines=[]
    for axis,bound,indices,sign in GUARDS:
        canonical=((bound,0),(bound,320)) if axis==0 else ((0,bound),(320,bound))
        line=_mapPolygon(redCoefficients,canonical)
        lines.append((line,indices,sign))
    guardSetupGood=all(line is not None and line[0]!=line[1] for line,_,_ in lines)
    expectedEdges=_edgeSquared(expected) if expected is not None else [0]*4
    cycles=[]
    for shift in range(4):
        measured=actual[shift:]+actual[:shift]
        errorsGood=expected is not None and all(abs(measured[i][axis]-expected[i][axis])<=tolerance[axis]
            for i in range(4) for axis in range(2))
        measuredEdges=_edgeSquared(measured)
        edgesGood=all(e>0 and e<=4*a<=9*e for a,e in zip(measuredEdges,expectedEdges))
        guardsGood=guardSetupGood and all(sign*cross(line[0],line[1],measured[i])>=0
            for line,indices,sign in lines for i in indices)
        good=referenceGeometryGood and sampleGeometryGood and errorsGood and edgesGood and guardsGood
        cycles.append({'shift':shift,'cornerErrorsPass':bool(errorsGood),'edgeLengthsPass':edgesGood,
                       'halfplanesPass':bool(guardsGood),'pairPass':bool(good)})
    matches=[cycle['shift'] for cycle in cycles if cycle['pairPass']]
    valid=len(matches)==1
    if valid:
        # The unique correspondence defines the blue polygon's public corner
        # order. Re-map its own measured quad after that cyclic reorder; do not
        # return the arbitrary component support ordering or the expected quad.
        shift=matches[0]
        matchedBlue=blue[shift:]+blue[:shift]
        blueSample=_mapPolygon(halfQuadCoefficients(matchedBlue),BLUE_SAMPLE)
    return {'geometryVersion':CALIBRATION_GEOMETRY_VERSION,'pairValid':valid,
            'redPolygon':redSample if valid else [[0,0] for _ in range(4)],
            'bluePolygon':blueSample if valid else [[0,0] for _ in range(4)],
            'cyclicMatchCount':len(matches),'cyclicShift':matches[0] if valid else None,
            'expectedStripQ4':expected,'actualStripQ4':actual,'axisToleranceQ4':tolerance,
            'referenceGeometryGood':bool(referenceGeometryGood),'sampleGeometryGood':bool(sampleGeometryGood),
            'guardSetupGood':bool(guardSetupGood),'cycles':cycles}
