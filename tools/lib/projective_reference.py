#!/usr/bin/env python3
"""Pixel-derived quadrilateral normalisation and seven-stroke projection model.

No grid position or scene-manifest answer participates in recognition. The
integer homography maps a 32x40 canonical grid into the same native RGB image.
The fixed white floor is an explicit diagnostic/build parameter, not an output
of automatic red/blue calibration. Source minima/spread must match the capture.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw
from vision_reference import colourMask,quantise565,recognise,DIGITS
from candidates_reclaimed_model import candidates_reclaimed


def canonicalOffsets(x,y,width,height,orientation):
    if orientation==0:return x,y
    if orientation==1:return y,width-1-x
    if orientation==2:return width-1-x,height-1-y
    return height-1-y,x


def extractCorners(foreground,bbox,orientation=0):
    x0,y0,x1,y1=bbox
    width,height=x1-x0+1,y1-y0+1
    canonicalWidth,canonicalHeight=(height,width) if orientation&1 else (width,height)
    yy,xx=np.nonzero(foreground[y0:y1+1,x0:x1+1])
    if not len(xx):return None
    u,v=canonicalOffsets(xx,yy,width,height,orientation)
    plus=u*canonicalHeight+v*canonicalWidth
    minus=u*canonicalHeight-v*canonicalWidth
    indices=[int(np.argmin(plus)),int(np.argmax(minus)),int(np.argmax(plus)),int(np.argmin(minus))]
    return [[int(xx[index])+x0,int(yy[index])+y0] for index in indices]


def supportCorners(foreground,bbox):
    """Sixteen fixed directional supports; bounded, pixel-only quad recovery.

    The diameter endpoints and maximum signed distances on either side recover
    four corners without assuming they lie near the native bbox diagonals.
    Directional scores use only coefficients -2..2. Duplicate support points
    are deliberately retained: RTL examines the same ordered 120 pairs.
    """
    x0,y0,x1,y1=bbox
    yy,xx=np.nonzero(foreground[y0:y1+1,x0:x1+1])
    if not len(xx):return None
    directions=((1,0),(2,1),(1,1),(1,2),(0,1),(-1,2),(-1,1),(-2,1),
                (-1,0),(-2,-1),(-1,-1),(-1,-2),(0,-1),(1,-2),(1,-1),(2,-1))
    points=[]
    for a,b in directions:
        index=int(np.argmax(a*xx+b*yy))
        points.append((int(xx[index])+x0,int(yy[index])+y0))
    first,second=max(((a,b) for a in range(15) for b in range(a+1,16)),
        key=lambda pair:sum((points[pair[0]][axis]-points[pair[1]][axis])**2 for axis in (0,1)))
    a,b=points[first],points[second]
    cross=lambda point:(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0])
    quad=[list(a),list(min(points,key=cross)),list(b),list(max(points,key=cross))]
    if len(set(map(tuple,quad)))!=4:return None
    base=min(range(4),key=lambda index:(sum(quad[index]),quad[index][1],quad[index][0]))
    return quad[base:]+quad[:base]


def homographyCoefficients(corners,orientation=0,continuous=False):
    # Native corner centres become canonical outer pixel edges in half-pixel
    # units. Rotate the expansion with the chosen canonical orientation.
    offsets=[(-1,-1),(1,-1),(1,1),(-1,1)]
    def rotateOffset(dx,dy):
        return [(dx,dy),(-dy,dx),(-dx,-dy),(dy,-dx)][orientation]
    quad=[]
    sumX,sumY=sum(p[0] for p in corners),sum(p[1] for p in corners)
    for (x,y),(dx,dy) in zip(corners,offsets):
        if continuous:
            dx=(4*x>sumX)-(4*x<sumX);dy=(4*y>sumY)-(4*y<sumY)
        else:dx,dy=rotateOffset(dx,dy)
        quad.append([2*x+dx,2*y+dy])
    (x0,y0),(x1,y1),(x2,y2),(x3,y3)=quad
    dx1,dx2,dx3=x1-x2,x3-x2,x0-x1+x2-x3
    dy1,dy2,dy3=y1-y2,y3-y2,y0-y1+y2-y3
    determinant=dx1*dy2-dx2*dy1
    g=dx3*dy2-dx2*dy3
    h=dx1*dy3-dx3*dy1
    coefficients=[(x1-x0)*determinant+g*x1,(x3-x0)*determinant+h*x3,x0*determinant,
                  (y1-y0)*determinant+g*y1,(y3-y0)*determinant+h*y3,y0*determinant,g,h,determinant]
    if determinant<0:coefficients=[-value for value in coefficients]
    return coefficients,quad


def gridAddresses(coefficients):
    a,b,c,d,e,f,g,h,determinant=coefficients
    addresses=[]
    for gy in range(40):
        v=(2*gy+1)*4
        for gx in range(32):
            u=(2*gx+1)*5
            denominator=g*u+h*v+determinant*320
            if denominator<=0:return None
            # Coefficients have 2x native coordinates. Add one denominator before
            # dividing by two denominators for nearest-pixel, ties upward.
            x=(a*u+b*v+c*320+denominator)//(2*denominator)
            y=(d*u+e*v+f*320+denominator)//(2*denominator)
            if not 0<=x<320 or not 0<=y<240:return None
            addresses.append([x,y])
    return addresses


def projectionScores(white):
    scores={}
    for name,top,bottom in [('A',4,8),('G',18,21),('D',31,35)]:
        bits=white[top:bottom+1,12:20].any(axis=0)
        scores[name]={'white':int(bits.sum()),'samples':8,'projectionBits':sum(int(value)<<bit for bit,value in enumerate(bits))}
    for name,left,right,top,bottom in [('B',21,24,10,16),('C',21,24,23,29),('F',7,10,10,16),('E',7,10,23,29)]:
        bits=white[top:bottom+1,left:right+1].any(axis=1)
        scores[name]={'white':int(bits.sum()),'samples':7,'projectionBits':sum(int(value)<<bit for bit,value in enumerate(bits))}
    anchor=white[1:6,0:6]
    scores['anchor']={'white':int(anchor.sum()),'samples':30,'rows':int(anchor.any(axis=1).sum()),'columns':int(anchor.any(axis=0).sum())}
    for name,top in [('upperHole',12),('lowerHole',24)]:
        scores[name]={'white':int(white[top:top+4,13:19].sum()),'samples':24}
    return scores


def whiteProfileFor(readerAlgorithm=5,whiteMin=None,maxSpread=64):
    """Resolve explicit historical/new white-bank semantics, never relabel them.

    Algorithms 1 and 2 retain their exact recorded semantics. Algorithm 3 rounds
    weighted brightness only for strokes/holes; its native anchor still uses
    the exact algorithm-2 floor, which preserves separation from the paper.
    These fixed profiles are not calibrated by the red/blue interaction.
    """
    if readerAlgorithm not in (1,2,3,4,5):raise ValueError('readerAlgorithm must be 1..5')
    if whiteMin is None:whiteMin=112 if readerAlgorithm==1 else 84 if readerAlgorithm>=4 else 96
    if not 0<=whiteMin<=255 or not 0<=maxSpread<=255:raise ValueError('White profile fields must be unsigned 8-bit')
    if readerAlgorithm in (2,3) and (whiteMin!=96 or maxSpread!=64):
        raise ValueError(f'Reader algorithm {readerAlgorithm} requires fixed weighted-luma minimum 96 and maximum channel spread 64')
    if readerAlgorithm>=4 and (whiteMin!=84 or maxSpread!=64):
        raise ValueError('Reader algorithms 4/5 require weighted-luma minimum 84 and maximum channel spread 64')
    profile={'mode':{1:'MINIMUM_RGB_CHANNEL',2:'WEIGHTED_LUMA',3:'ROUNDED_STROKES_STRICT_ANCHOR',4:'UNSATURATED_STROKES_STRICT_ANCHOR',5:'UNSATURATED_STROKES_STRICT_ANCHOR'}[readerAlgorithm],
        'minimum':whiteMin,'maximumChannelSpread':maxSpread,'source':'FIXED_PARAMETER_NOT_AUTOMATIC_CALIBRATION'}
    if readerAlgorithm==2:profile.update(sumWeights=[1,2,1],sumMinimum=384)
    if readerAlgorithm==3:profile.update(sumWeights=[1,2,1],sumMinimum=382,anchorSumMinimum=384,roundingBias=2)
    if readerAlgorithm>=4:profile.update(sumWeights=[1,2,1],sumMinimum=334,anchorSumMinimum=384,
        anchorMinimum=96,roundingBias=2,weakSaturationNumerator=1,weakSaturationDenominator=2,
        strongWhiteIncludedInStrokes=True)
    return profile


def whitePixelsFor(array,profile,*,anchor=False):
    """White predicate from bit-replicated RGB565; signed 16-bit arithmetic.

    The caller selects the native-anchor predicate explicitly. Array size and
    expected digit never select a threshold. Historical profiles ignore this
    selector because their anchor and stroke predicates were identical.
    """
    source=np.asarray(array,dtype=np.int16)
    sumMinimum=profile.get('anchorSumMinimum',profile.get('sumMinimum')) if anchor else profile.get('sumMinimum')
    intensity=(source.min(axis=2)>=profile['minimum']) if profile['mode']=='MINIMUM_RGB_CHANNEL' else (
        source[:,:,0]+2*source[:,:,1]+source[:,:,2]>=sumMinimum)
    spread=np.ptp(source,axis=2)
    if profile['mode']=='UNSATURATED_STROKES_STRICT_ANCHOR' and not anchor:
        # Keep strict white a subset of stroke white. The new dim branch is
        # disjoint from the colour S>=1/2 predicate regardless of calibrated V.
        strong=source[:,:,0]+2*source[:,:,1]+source[:,:,2]>=profile['anchorSumMinimum']
        intensity=strong|(intensity&(2*spread<source.max(axis=2)))
    return intensity&(spread<=profile['maximumChannelSpread'])


def packedGlyphClasses(array,colourForeground,profile):
    """Algorithm-3 two-bit storage oracle: 00 background, 01 colour, 10 weak
    white, 11 strict white. RGB565/HSV mutual exclusion is exhaustively tested.
    A future profile violating it fails explicitly instead of losing a bit.
    """
    if profile['mode'] not in ('ROUNDED_STROKES_STRICT_ANCHOR','UNSATURATED_STROKES_STRICT_ANCHOR'):
        raise ValueError('Packed split-white classes require reader algorithm 3 or 4')
    foreground=np.asarray(colourForeground,dtype=bool)
    rounded=whitePixelsFor(array,profile)
    strict=whitePixelsFor(array,profile,anchor=True)
    if foreground.shape!=rounded.shape:raise ValueError('Colour/white shapes differ')
    if np.any(foreground&rounded):raise ValueError('Colour and white overlap; two-bit encoding is not lossless')
    return (rounded.astype(np.uint8)<<1)|strict.astype(np.uint8)|foreground.astype(np.uint8)


def nativeAnchorScores(nativeWhite,quadHalfPixels,capacity=8):
    """Read a bounded native white neighbourhood without normalisation aliases.

    The existing canonical corner order already incorporates orientation. Four
    integer affine points define a search rectangle around the physical anchor.
    Four-connected white components touching that rectangle's perimeter are
    paper/background evidence and cannot become an anchor. Exactly one small
    closed component must qualify. Its count/rows/columns are native units.

    The independent row-graph oracle measures transient handles including alias
    labels. Only active handle overflow rejects: completed components retire
    continuously and are not held in an eight-object output array.
    """
    q=np.asarray(quadHalfPixels,dtype=np.int64);spanHalf=q.max(axis=0)-q.min(axis=0)
    numerators=np.array([20*q[0]+s*(q[1]-q[0])+t*(q[3]-q[0]) for s in (-3,5) for t in (-1,4)])
    x0,y0=np.maximum(numerators.min(axis=0)//40-1,(0,0))
    x1,y1=np.minimum((numerators.max(axis=0)+39)//40+1,(319,239))
    roi=[int(x0),int(y0),int(x1),int(y1)]
    patch=np.asarray(nativeWhite[y0:y1+1,x0:x1+1],dtype=bool)
    height,width=patch.shape
    oracle=candidates_reclaimed(patch.astype(int).tolist(),cap=capacity,min_area=1)
    visited=np.zeros_like(patch,dtype=bool);eligible=[];completedCount=0
    for py,px in np.argwhere(patch):
        if visited[py,px]:continue
        visited[py,px]=True;queue=deque([(int(py),int(px))]);points=[]
        while queue:
            cy,cx=queue.popleft();points.append((cy,cx))
            for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0<=ny<height and 0<=nx<width and patch[ny,nx] and not visited[ny,nx]:
                    visited[ny,nx]=True;queue.append((ny,nx))
        completedCount+=1
        ys,xs=zip(*points);boxWidth=max(xs)-min(xs)+1;boxHeight=max(ys)-min(ys)+1
        closed=min(xs)>0 and max(xs)<width-1 and min(ys)>0 and max(ys)<height-1
        if (closed and len(points)>=3 and boxWidth>=2 and boxHeight>=2 and
            100*boxWidth<=11*spanHalf[0] and 100*boxHeight<=11*spanHalf[1] and
            200*len(points)<=spanHalf[0]*spanHalf[1]):
            eligible.append({'white':len(points),'rows':boxHeight,'columns':boxWidth,
                'bbox':[int(x0+min(xs)),int(y0+min(ys)),int(x0+max(xs)),int(y0+max(ys))]})
    overflow=bool(oracle['red_active_overflow'])
    result={'white':0,'samples':width*height,'rows':0,'columns':0,'roi':roi,
        'source':'NATIVE_LOCAL_CLOSED_COMPONENT','units':'native pixels/rows/columns',
        'capacity':capacity,'peakActiveHandles':oracle['red_max_row_handles'],
        'completedComponents':completedCount,'eligibleCount':min(2,len(eligible)),
        'ambiguous':len(eligible)>1,'overflow':overflow}
    if len(eligible)==1 and not overflow:result.update(eligible[0])
    return result


def classifyAutomatic(image,candidate,orientation,redMin,blueMin,whiteMin,maxSpread,output,colourAlgorithm,bypassPerspective,activeCapacity):
    """Reader5: exactly one valid native anchor among four cyclic hypotheses.

    Marker orientation names a corner offset from native min(x+y), ties y,x.
    It is neither a continuous angle nor the externally configured coordinate
    profile. No expected digit, scene cell or candidate order enters selection.
    """
    image=quantise565(image);profile=whiteProfileFor(5,whiteMin,maxSpread)
    if image.size!=(320,240) or orientation not in range(4):raise ValueError('Invalid native image/orientation hint')
    if colourAlgorithm not in (2,3):raise ValueError('Reader5 requires HSV colour algorithm2 or 3')
    bbox=list(map(int,candidate['bbox']));x0,y0,x1,y1=bbox
    result={**candidate,'readerAlgorithm':5,'colourAlgorithm':colourAlgorithm,'accepted':False,'digit':None,
        'kind':'UNKNOWN','quality':0,'orientationProfile':orientation,'reasonCode':1,'reasonName':'GEOMETRY',
        'quad':None,'windowScores':{},'inputWhiteProfile':profile,'segments':'','gridSampled':False,
        'orientationMode':'AUTO_UNIQUE_NATIVE_ANCHOR','orientationHypotheses':[],'bypassPerspective':bool(bypassPerspective)}
    if not (0<=x0<=x1<320 and 0<=y0<=y1<240 and x1-x0+1>=24 and y1-y0+1>=24):return result
    foreground=np.asarray(colourMask(image,redMin,blueMin,colourAlgorithm=colourAlgorithm)).reshape(240,320)!=0
    result['foregroundCount']=int(foreground[y0:y1+1,x0:x1+1].sum())
    quad=([[x0,y0],[x1,y0],[x1,y1],[x0,y1]] if bypassPerspective else supportCorners(foreground,bbox))
    if quad is None or result['foregroundCount']<32:return result
    nativeWhite=whitePixelsFor(np.asarray(image,dtype=np.int16),profile,anchor=True)
    choices=[]
    for offset in range(4):
        hypothesis=(orientation+offset)&3
        corners=quad[hypothesis:]+quad[:hypothesis]
        coefficients,quad2=homographyCoefficients(corners,hypothesis,continuous=True)
        cross=[(quad2[(i+1)%4][0]-quad2[i][0])*(quad2[(i+2)%4][1]-quad2[(i+1)%4][1])-
               (quad2[(i+1)%4][1]-quad2[i][1])*(quad2[(i+2)%4][0]-quad2[(i+1)%4][0]) for i in range(4)]
        edges=[sum((quad2[(i+1)%4][axis]-quad2[i][axis])**2 for axis in (0,1)) for i in range(4)]
        area=sum(quad2[i][0]*quad2[(i+1)%4][1]-quad2[(i+1)%4][0]*quad2[i][1] for i in range(4))
        if min(cross)<=0 or min(edges)<4*24*24 or area<8*400:return result
        anchor=nativeAnchorScores(nativeWhite,quad2)
        good=anchor['white']>=3 and anchor['rows']>=2 and anchor['columns']>=2
        result['orientationHypotheses'].append({'orientation':hypothesis,'anchorGood':good,
            'quad':corners,'quadHalfPixels':quad2,'anchor':anchor})
        if good:choices.append((hypothesis,corners))
    if len(choices)!=1:
        result.update(reasonCode=4,reasonName='ANCHOR_ORIENTATION_AMBIGUOUS' if len(choices)>1 else 'ANCHOR_OR_HOLE',
                      quad=quad[orientation:]+quad[:orientation],orientationAnchorMatches=min(2,len(choices)))
        if output:
            out=Path(output);out.mkdir(parents=True,exist_ok=True)
            image.crop((x0,y0,x1+1,y1+1)).save(out/'native_crop.png')
            (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        return result
    selected,corners=choices[0]
    classified=classifyProjective(image,candidate,selected,redMin,blueMin,whiteMin,maxSpread,output,
        colourAlgorithm,5,bypassPerspective,activeCapacity,_automaticHypothesis=True,_corners=corners)
    classified.update(orientationMode='AUTO_UNIQUE_NATIVE_ANCHOR',orientationAnchorMatches=1,
        orientationHypotheses=result['orientationHypotheses'])
    if output:(Path(output)/'result.json').write_text(json.dumps(classified,indent=2)+'\n',encoding='utf-8')
    return classified


def classifyProjective(image,candidate,orientation=0,redMin=48,blueMin=None,whiteMin=None,maxSpread=64,output=None,colourAlgorithm=None,readerAlgorithm=5,bypassPerspective=False,activeCapacity=None,_automaticHypothesis=False,_corners=None):
    if activeCapacity is None:activeCapacity=15 if readerAlgorithm>=4 else 8
    if blueMin is None:blueMin=20 if readerAlgorithm>=4 else 32
    if colourAlgorithm is None:colourAlgorithm=3 if readerAlgorithm==5 else 2 if readerAlgorithm==4 else 1
    if readerAlgorithm==5 and not _automaticHypothesis:
        return classifyAutomatic(image,candidate,orientation,redMin,blueMin,whiteMin,maxSpread,output,colourAlgorithm,bypassPerspective,activeCapacity)
    image=quantise565(image)
    if image.size!=(320,240):raise ValueError('Projective native frame must be 320x240')
    if orientation not in range(4):raise ValueError('orientation must be 0..3')
    profile=whiteProfileFor(readerAlgorithm,whiteMin,maxSpread)
    if readerAlgorithm==3 and colourAlgorithm!=1:
        raise ValueError('Reader algorithm 3 packed glyph classes require HSV colour algorithm 1')
    if readerAlgorithm==4 and colourAlgorithm!=2:
        raise ValueError('Reader algorithm 4 packed glyph classes require HSV colour algorithm 2')
    if readerAlgorithm==5 and colourAlgorithm not in (2,3):
        raise ValueError('Reader algorithm 5 requires HSV colour algorithm 2 or 3')
    if readerAlgorithm!=5 and colourAlgorithm==3:
        raise ValueError('Colour algorithm 3 requires reader algorithm 5')
    if any(not 0<=value<=255 for value in (redMin,blueMin)):raise ValueError('Thresholds must be unsigned 8-bit')
    bbox=list(map(int,candidate['bbox']));x0,y0,x1,y1=bbox
    result={**candidate,'readerAlgorithm':readerAlgorithm,'colourAlgorithm':colourAlgorithm,'accepted':False,'digit':None,'kind':'UNKNOWN','quality':0,
            'orientationProfile':orientation,'reasonCode':1,'reasonName':'GEOMETRY','quad':None,'windowScores':{},
            'inputWhiteProfile':profile,'segments':''}
    width,height=x1-x0+1,y1-y0+1
    canonicalWidth,canonicalHeight=(height,width) if orientation&1 else (width,height)
    if not (0<=x0<=x1<320 and 0<=y0<=y1<240 and width>=24 and height>=24):return result
    foreground=np.array(colourMask(image,redMin,blueMin,colourAlgorithm=colourAlgorithm),dtype=np.uint8).reshape(240,320)!=0
    foregroundCount=int(foreground[y0:y1+1,x0:x1+1].sum())
    result['foregroundCount']=foregroundCount
    if foregroundCount<32:return result
    corners=_corners if _corners is not None else extractCorners(foreground,bbox,orientation)
    if bypassPerspective and readerAlgorithm<5:
        axisCorners=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        corners=axisCorners[orientation:]+axisCorners[:orientation]
    result['bypassPerspective']=bool(bypassPerspective)
    result['quad']=corners
    if corners is None or len(set(map(tuple,corners)))!=4:return result
    coefficients,quad2=homographyCoefficients(corners,orientation,continuous=readerAlgorithm>=5)
    result['quadHalfPixels']=quad2;result['coefficients']=coefficients
    crossProducts=[]
    for index in range(4):
        p,q,r=quad2[index],quad2[(index+1)%4],quad2[(index+2)%4]
        crossProducts.append((q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0]))
    edgeSquared=[sum((quad2[(i+1)%4][axis]-quad2[i][axis])**2 for axis in (0,1)) for i in range(4)]
    areaTwice=sum(quad2[i][0]*quad2[(i+1)%4][1]-quad2[i][1]*quad2[(i+1)%4][0] for i in range(4))
    result.update(crossProducts=crossProducts,edgeSquaredHalfPixelUnits=edgeSquared,areaPixels=areaTwice/8,
                  touchesFrameBoundary=x0==0 or y0==0 or x1==319 or y1==239)
    if min(crossProducts)<=0 or min(edgeSquared)<4*24*24 or areaTwice<8*400:return result
    if coefficients[-1]==0:return result
    addresses=gridAddresses(coefficients)
    if addresses is None:
        result.update(reasonCode=6,reasonName='PROJECTIVE_RANGE');return result
    result['gridSampled']=True
    source=np.asarray(image,dtype=np.int16)
    rectified=np.array([source[y,x] for x,y in addresses],dtype=np.int16).reshape(40,32,3)
    white=whitePixelsFor(rectified,profile)
    scores=projectionScores(white)
    if readerAlgorithm>=2:scores['anchor']=nativeAnchorScores(whitePixelsFor(source,profile,anchor=True),quad2)
    result['windowScores']=scores
    result['uniqueSourceSamples']=len(set(map(tuple,addresses)))
    result['minimumHorizontalEdgePixels']=math.sqrt(min(edgeSquared[0],edgeSquared[2]))/2
    pattern=''.join(name for name in 'ABCDEFG' if scores[name]['white']*10>=scores[name]['samples']*6)
    uncertain=any(scores[name]['samples']*3<scores[name]['white']*10<scores[name]['samples']*6 for name in 'ABCDEFG')
    anchor=scores['anchor']
    shapeGood=anchor['white']>=3 and anchor['rows']>=2 and anchor['columns']>=2 and all(scores[name]['white']*5<=scores[name]['samples'] for name in ('upperHole','lowerHole'))
    result['segments']=pattern
    digit=DIGITS.get(pattern)
    if uncertain:result.update(reasonCode=3,reasonName='UNCERTAIN_STROKE')
    elif not shapeGood:result.update(reasonCode=4,reasonName='ANCHOR_OR_HOLE')
    elif digit is None or (candidate['colour']=='red' and digit>2):result.update(reasonCode=5,reasonName='UNKNOWN_PATTERN')
    else:
        strong=all(scores[name]['white']*10>=scores[name]['samples']*8 for name in pattern)
        highResolution=min(edgeSquared)>=4*40*40
        result.update(accepted=True,digit=digit,kind='FUNCTION' if candidate['colour']=='red' else 'BAY',
                      quality=255 if strong and highResolution and anchor['white']>=4 else 192,reasonCode=0,reasonName='OK')
    if output:
        out=Path(output);out.mkdir(parents=True,exist_ok=True)
        image.crop((x0,y0,x1+1,y1+1)).save(out/'native_crop.png')
        Image.fromarray(rectified.astype(np.uint8)).save(out/'rectified_rgb.png')
        Image.fromarray((white*255).astype(np.uint8)).save(out/'rectified_white.png')
        if readerAlgorithm>=2:
            ax0,ay0,ax1,ay1=scores['anchor']['roi']
            image.crop((ax0,ay0,ax1+1,ay1+1)).save(out/'native_anchor_rgb.png')
            nativeWhite=whitePixelsFor(source,profile,anchor=True)
            Image.fromarray((nativeWhite[ay0:ay1+1,ax0:ax1+1]*255).astype(np.uint8)).save(out/'native_anchor_white.png')
        overlay=image.copy();draw=ImageDraw.Draw(overlay);draw.line(corners+[corners[0]],fill='yellow',width=1)
        for index,(x,y) in enumerate(corners):draw.text((x,y),str(index),fill='lime')
        overlay.crop((max(0,x0-4),max(0,y0-4),min(320,x1+5),min(240,y1+5))).save(out/'corners.png')
        result['artifacts']=str(out)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def recogniseProjective(image,orientation=0,redMin=48,blueMin=None,whiteMin=None,maxSpread=64,cleanup=True,output=None,inputSource='UNSPECIFIED',colourAlgorithm=None,readerAlgorithm=5,bypassPerspective=False,activeCapacity=None,outputCapacity=None,sharedPool=None):
    if activeCapacity is None:activeCapacity=15 if readerAlgorithm>=4 else 8
    if outputCapacity is None:outputCapacity=16 if readerAlgorithm>=5 else 8
    if sharedPool is None:sharedPool=readerAlgorithm==5
    if sharedPool and readerAlgorithm!=5:
        raise ValueError('Shared completed candidates require reader5; historical readers retain split pools')
    if blueMin is None:blueMin=20 if readerAlgorithm>=4 else 32
    if colourAlgorithm is None:colourAlgorithm=3 if readerAlgorithm==5 else 2 if readerAlgorithm==4 else 1
    image=quantise565(image)
    profile=whiteProfileFor(readerAlgorithm,whiteMin,maxSpread)
    if readerAlgorithm==3 and colourAlgorithm!=1:
        raise ValueError('Reader algorithm 3 packed glyph classes require HSV colour algorithm 1')
    if readerAlgorithm==4 and colourAlgorithm!=2:
        raise ValueError('Reader algorithm 4 packed glyph classes require HSV colour algorithm 2')
    if readerAlgorithm==5 and colourAlgorithm not in (2,3):
        raise ValueError('Reader algorithm 5 requires HSV colour algorithm 2 or 3')
    if readerAlgorithm!=5 and colourAlgorithm==3:
        raise ValueError('Colour algorithm 3 requires reader algorithm 5')
    base=recognise(image,orientation=orientation,redMin=redMin,blueMin=blueMin,cleanup=cleanup,inputSource=inputSource,
                   colourAlgorithm=colourAlgorithm,pruneUnusable=readerAlgorithm>=3,activeCapacity=activeCapacity,capacity=outputCapacity,
                   sharedCapacity=outputCapacity if sharedPool else None)
    result={key:value for key,value in base.items() if key!='markers'}
    result.update(schema='ECHO7_PROJECTIVE_MODEL_7' if sharedPool else 'ECHO7_PROJECTIVE_MODEL_6' if readerAlgorithm==5 else 'ECHO7_PROJECTIVE_MODEL_5' if readerAlgorithm==4 else 'ECHO7_PROJECTIVE_MODEL_4' if readerAlgorithm==3 else 'ECHO7_PROJECTIVE_MODEL_3',
                  readerAlgorithm=readerAlgorithm,colourAlgorithm=colourAlgorithm,markers=[],whiteProfile=profile,
                  candidatePoolMode='SHARED' if sharedPool else 'SPLIT_PER_COLOUR',
                  candidateOrder='MODEL_CANONICAL_GEOMETRY_NOT_RTL_RETIREMENT_ORDER')
    out=Path(output) if output else None
    if out:out.mkdir(parents=True,exist_ok=True)
    for index,candidate in enumerate(base['markers']):
        fields={key:candidate[key] for key in ('colour','area','bbox')}
        marker=classifyProjective(image,fields,orientation,redMin,blueMin,profile['minimum'],maxSpread,out/f'candidate_{index:02d}' if out else None,colourAlgorithm=colourAlgorithm,readerAlgorithm=readerAlgorithm,bypassPerspective=bypassPerspective)
        if result['overflow']:marker.update(accepted=False,quality=0,reasonCode=7,reasonName='FRAME_CAPACITY_OVERFLOW')
        marker['candidateIndex']=index;result['markers'].append(marker)
    if out:(out/'projective.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--source',required=True,choices=('SYNTHETIC_REPLAY','RECORDED_CAMERA','PIXEL_COUNTERFACTUAL'))
    parser.add_argument('--orientation',type=int,choices=range(4),default=0)
    parser.add_argument('--red-min',type=int,default=48);parser.add_argument('--blue-min',type=int,help='Default: 20 for reader4; 32 for historical readers')
    parser.add_argument('--colour-algorithm',type=int,choices=(0,1,2,3),help='Default: HSV3/RUN2 for reader5; HSV2/RUN3 for reader4; historical HSV1 for readers1-3')
    parser.add_argument('--reader-algorithm',type=int,choices=(1,2,3,4,5),default=5)
    parser.add_argument('--output-capacity',type=int,choices=(8,16),help='Completed pool capacity; shared16 for reader5, per-colour8 for historical readers')
    poolGroup=parser.add_mutually_exclusive_group()
    poolGroup.add_argument('--shared-pool',action='store_true',dest='sharedPool',default=None,help='One shared completed pool (default reader5/private schema7)')
    poolGroup.add_argument('--split-pool',action='store_false',dest='sharedPool',help='Historical separate colour pools, including reader5/private schema6')
    parser.add_argument('--active-capacity',type=int,choices=range(1,16),help='Temporary labels; current production15, historical schema1-3 use8')
    parser.add_argument('--bypass-perspective',action='store_true',help='R9 axis-aligned bbox baseline; identity still comes from pixels')
    parser.add_argument('--white-min',type=int,help='Fixed profiles: reader1 min-RGB112; reader2/3 luma96; reader4 dim unsaturated84/strict anchor96');parser.add_argument('--max-spread',type=int,default=64)
    args=parser.parse_args()
    result=recogniseProjective(Image.open(args.image),args.orientation,args.red_min,args.blue_min,args.white_min,args.max_spread,output=args.out,inputSource=args.source,colourAlgorithm=args.colour_algorithm,readerAlgorithm=args.reader_algorithm,bypassPerspective=args.bypass_perspective,activeCapacity=args.active_capacity,outputCapacity=args.output_capacity,sharedPool=args.sharedPool)
    print(json.dumps(result))
    return int(result['overflow'])


if __name__=='__main__':raise SystemExit(main())
