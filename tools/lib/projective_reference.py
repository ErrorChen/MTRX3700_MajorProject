#!/usr/bin/env python3
"""Pixel-derived quadrilateral normalisation and seven-stroke projection model.

No grid position or scene-manifest answer participates in recognition. The
integer homography maps a 32x40 canonical grid into the same native RGB image.
The fixed white floor is an explicit diagnostic/build parameter, not an output
of automatic red/blue calibration. Source minima/spread must match the capture.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw
from vision_reference import colourMask,quantise565,recognise,DIGITS


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


def homographyCoefficients(corners,orientation=0):
    # Native corner centres become canonical outer pixel edges in half-pixel
    # units. Rotate the expansion with the chosen canonical orientation.
    offsets=[(-1,-1),(1,-1),(1,1),(-1,1)]
    def rotateOffset(dx,dy):
        return [(dx,dy),(-dy,dx),(-dx,-dy),(dy,-dx)][orientation]
    quad=[]
    for (x,y),(dx,dy) in zip(corners,offsets):
        dx,dy=rotateOffset(dx,dy);quad.append([2*x+dx,2*y+dy])
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


def classifyProjective(image,candidate,orientation=0,redMin=48,blueMin=32,whiteMin=112,maxSpread=64,output=None,colourAlgorithm=1):
    image=quantise565(image)
    if image.size!=(320,240):raise ValueError('Projective native frame must be 320x240')
    if orientation not in range(4):raise ValueError('orientation must be 0..3')
    if any(not 0<=value<=255 for value in (redMin,blueMin,whiteMin,maxSpread)):raise ValueError('Thresholds must be unsigned 8-bit')
    bbox=list(map(int,candidate['bbox']));x0,y0,x1,y1=bbox
    result={**candidate,'readerAlgorithm':1,'colourAlgorithm':colourAlgorithm,'accepted':False,'digit':None,'kind':'UNKNOWN','quality':0,
            'orientationProfile':orientation,'reasonCode':1,'reasonName':'GEOMETRY','quad':None,'windowScores':{},
            'inputWhiteProfile':{'minimum':whiteMin,'maximumChannelSpread':maxSpread},'segments':''}
    width,height=x1-x0+1,y1-y0+1
    canonicalWidth,canonicalHeight=(height,width) if orientation&1 else (width,height)
    if not (0<=x0<=x1<320 and 0<=y0<=y1<240 and width>=24 and height>=24):return result
    foreground=np.array(colourMask(image,redMin,blueMin,colourAlgorithm=colourAlgorithm),dtype=np.uint8).reshape(240,320)!=0
    foregroundCount=int(foreground[y0:y1+1,x0:x1+1].sum())
    result['foregroundCount']=foregroundCount
    if foregroundCount<32:return result
    corners=extractCorners(foreground,bbox,orientation)
    result['quad']=corners
    if corners is None or len(set(map(tuple,corners)))!=4:return result
    coefficients,quad2=homographyCoefficients(corners,orientation)
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
    source=np.asarray(image,dtype=np.int16)
    rectified=np.array([source[y,x] for x,y in addresses],dtype=np.int16).reshape(40,32,3)
    white=(rectified.min(axis=2)>=whiteMin)&(np.ptp(rectified,axis=2)<=maxSpread)
    scores=projectionScores(white);result['windowScores']=scores
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
        overlay=image.copy();draw=ImageDraw.Draw(overlay);draw.line(corners+[corners[0]],fill='yellow',width=1)
        for index,(x,y) in enumerate(corners):draw.text((x,y),str(index),fill='lime')
        overlay.crop((max(0,x0-4),max(0,y0-4),min(320,x1+5),min(240,y1+5))).save(out/'corners.png')
        result['artifacts']=str(out)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def recogniseProjective(image,orientation=0,redMin=48,blueMin=32,whiteMin=112,maxSpread=64,cleanup=True,output=None,inputSource='UNSPECIFIED',colourAlgorithm=1):
    image=quantise565(image)
    base=recognise(image,orientation=orientation,redMin=redMin,blueMin=blueMin,cleanup=cleanup,inputSource=inputSource,colourAlgorithm=colourAlgorithm)
    result={key:value for key,value in base.items() if key!='markers'}
    result.update(schema='ECHO7_PROJECTIVE_MODEL_2',readerAlgorithm=1,colourAlgorithm=colourAlgorithm,markers=[],
                  whiteProfile={'minimum':whiteMin,'maximumChannelSpread':maxSpread,'source':'FIXED_PARAMETER_NOT_AUTOMATIC_CALIBRATION'})
    out=Path(output) if output else None
    if out:out.mkdir(parents=True,exist_ok=True)
    for index,candidate in enumerate(base['markers']):
        fields={key:candidate[key] for key in ('colour','area','bbox')}
        marker=classifyProjective(image,fields,orientation,redMin,blueMin,whiteMin,maxSpread,out/f'candidate_{index:02d}' if out else None,colourAlgorithm=colourAlgorithm)
        if result['overflow']:marker.update(accepted=False,quality=0,reasonCode=7,reasonName='FRAME_CAPACITY_OVERFLOW')
        marker['candidateIndex']=index;result['markers'].append(marker)
    if out:(out/'projective.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--source',required=True,choices=('SYNTHETIC_REPLAY','RECORDED_CAMERA','PIXEL_COUNTERFACTUAL'))
    parser.add_argument('--orientation',type=int,choices=range(4),default=0)
    parser.add_argument('--red-min',type=int,default=48);parser.add_argument('--blue-min',type=int,default=32)
    parser.add_argument('--colour-algorithm',type=int,choices=(0,1),default=1,help='0=historical ratio; 1=HSV plus run3 candidate support')
    parser.add_argument('--white-min',type=int,default=112);parser.add_argument('--max-spread',type=int,default=64)
    args=parser.parse_args()
    result=recogniseProjective(Image.open(args.image),args.orientation,args.red_min,args.blue_min,args.white_min,args.max_spread,output=args.out,inputSource=args.source,colourAlgorithm=args.colour_algorithm)
    print(json.dumps(result))
    return int(result['overflow'])


if __name__=='__main__':raise SystemExit(main())
