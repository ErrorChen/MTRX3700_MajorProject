#!/usr/bin/env python3
"""Replay actual raw colourSampler ROIs and candidate capacity after calibration.

This is MODEL evidence from recorded camera RGB, not a claim that the board
committed a profile. It applies the previous frame's ROI to the next image,
then checks the same-frame geometry as the RTL does. No old colour mask filters
the sampling pixels. Three retained frames do not replace eight fresh samples.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from projective_reference import recogniseProjective
from vision_reference import quantise565


def paired(card, reference, rotation=0, pairingAlgorithm=2):
    """Mirror the configured-quadrant RTL predicate in native pixel units.

    Algorithm2 compares doubled centres with ceil(cardWidth/16) tolerance and
    at least80% main-card overlap. It has no fixed pixel alignment allowance.
    Algorithm1 is retained only for reproducing historical audits. Neither
    version estimates arbitrary-angle calibration geometry from the marker ID.
    """
    if rotation not in range(4):raise ValueError('unsupported configured orientation')
    if pairingAlgorithm not in (1,2):raise ValueError('unsupported pairing algorithm')
    x0,y0,x1,y1=card
    bx0,by0,bx1,by1=reference
    width,height=(y1-y0+1,x1-x0+1) if rotation&1 else (x1-x0+1,y1-y0+1)
    refWidth,refHeight=(by1-by0+1,bx1-bx0+1) if rotation&1 else (bx1-bx0+1,by1-by0+1)
    low,high=(y0,y1) if rotation&1 else (x0,x1)
    refLow,refHigh=(by0,by1) if rotation&1 else (bx0,bx1)
    gap=(by0-y1-1,x0-bx1-1,y0-by1-1,bx0-x1-1)[rotation]
    if pairingAlgorithm==1:
        aligned=abs(refLow-low)<=4 and abs(refHigh-high)<=4
    else:
        centreDelta2=refLow+refHigh-low-high
        centreTolerance=(width+15)//16
        overlap=max(0,min(high,refHigh)-max(low,refLow)+1)
        aligned=abs(centreDelta2)<=2*centreTolerance and overlap*5>=width*4
    if min(width,height,refWidth,refHeight)<=0:return False
    return (gap>=0 and gap*8<=height and width*8<=refWidth*10<=width*12
            and height<=refHeight*10<=height*3 and aligned)


def sample(image, redBox, blueBox, samplerAlgorithm=2):
    if samplerAlgorithm not in (1,2):raise ValueError('unsupported sampler algorithm')
    rgb=np.asarray(quantise565(image),dtype=np.int16)
    yy,xx=np.indices((240,320))
    x0,y0,x1,y1=redBox
    width,height=x1-x0+1,y1-y0+1
    u,v=xx-x0,yy-y0
    redHit=(xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1)&(u*100>=width*8)&(u*100<width*18)&(v*10>=height*3)&(v*10<height*7)
    x0,y0,x1,y1=blueBox
    width,height=x1-x0+1,y1-y0+1
    blueHit=(xx>=x0)&(xx<=x1)&(yy>=y0)&(yy<=y1)&((xx-x0)*5>=width)&((xx-x0)*5<width*4)&((yy-y0)*5>=height)&((yy-y0)*5<height*4)
    results={}
    for name,mask,channel,otherChannels in [('red',redHit,0,[1,2]),('blue',blueHit,2,[0,1])]:
        values=rgb[mask]
        low,high=int(values[:,channel].min()),int(values[:,channel].max())
        other=int(values[:,otherChannels].max())
        sy,sx=np.nonzero(mask)
        results[name]={'sampleCount':len(values),'channelMinimum':low,'channelMaximum':high,
                       'otherChannelMaximum':other,'shadowMinimum':low//2 if samplerAlgorithm==2 else (low+high)>>2,
                       'sampleBounds':[int(sx.min()),int(sy.min()),int(sx.max()),int(sy.max())],
                       'allRgbMinimum':values.min(axis=0).tolist(),'allRgbMaximum':values.max(axis=0).tolist(),
                       'meanRgb':values.mean(axis=0).tolist()}
    red,blue=results['red'],results['blue']
    results['frameSampleGood']=(red['sampleCount']>=16 and blue['sampleCount']>=16
        and red['channelMinimum']>=32 and blue['channelMinimum']>=24
        and all(item['channelMinimum']>item['otherChannelMaximum']+8
                and item['channelMaximum']-item['channelMinimum']<=80
                and item['otherChannelMaximum']<224
                and (samplerAlgorithm==1 or item['channelMaximum']<248) for item in (red,blue)))
    results['samplerAlgorithm']=samplerAlgorithm
    return results


def profileSummary(image, redMin, blueMin):
    result=recogniseProjective(image,redMin=redMin,blueMin=blueMin,inputSource='RECORDED_CAMERA',colourAlgorithm=0,readerAlgorithm=1)
    return {key:result[key] for key in ('colourProfile','candidateCounts','allComponentsBeforeAreaGate','boundedCandidateOracle','overflow')} | {
        'acceptedMarkers':[{'colour':m['colour'],'digit':m['digit'],'bbox':m['bbox'],'quality':m['quality']}
                           for m in result['markers'] if m['accepted']]}


def audit(inputDirectory, outputDirectory):
    outputDirectory.mkdir(parents=True,exist_ok=True)
    results=[]
    heldPair=None
    for frameId in (13139,13511,13675):
        image=Image.open(inputDirectory/f'frame{frameId}.png').convert('RGB')
        recognised=recogniseProjective(image,redMin=64,inputSource='RECORDED_CAMERA',colourAlgorithm=0,readerAlgorithm=1)
        cards=[m for m in recognised['markers'] if m['accepted'] and m['colour']=='red' and m['digit']==1]
        pairs=[(card['bbox'],blue['bbox']) for card in cards for blue in recognised['markers'] if blue['colour']=='blue' and paired(card['bbox'],blue['bbox'],pairingAlgorithm=1)]
        if len(pairs)!=1:raise AssertionError(f'Expected unique measured red1/reference pair, got {pairs}')
        currentPair=pairs[0]
        # This entry point reproduces the retained algorithm1 historical audit.
        # New callers use sample(..., samplerAlgorithm=2) and new evidence IDs.
        samples=sample(image,*currentPair,samplerAlgorithm=1)
        previousSamples=sample(image,*(heldPair or currentPair),samplerAlgorithm=1)
        stationary=heldPair is None or all(abs(a-b)<=3 for current,previous in zip(currentPair,heldPair) for a,b in zip(current,previous))
        trials=[]
        for redMin,blueMin in [(64,32),(samples['red']['shadowMinimum'],samples['blue']['shadowMinimum'])]:
            trials.append(profileSummary(image,redMin,blueMin))
        record={'frameId':frameId,'pairedRedBox':currentPair[0],'pairedBlueBox':currentPair[1],
                'sameFrameRoiSamples':samples,'previousFrameRoiSamples':previousSamples,
                'previousRoiStationary':stationary,'profileTrials':trials}
        overlay=image.copy();draw=ImageDraw.Draw(overlay)
        for colour in ('red','blue'):draw.rectangle(samples[colour]['sampleBounds'],outline='yellow' if colour=='red' else 'lime')
        overlay.resize((960,720),Image.Resampling.NEAREST).save(outputDirectory/f'frame{frameId}_sample_rois.png')
        results.append(record);heldPair=currentPair
    shadowRed=min(r['previousFrameRoiSamples']['red']['shadowMinimum'] for r in results)
    shadowBlue=min(r['previousFrameRoiSamples']['blue']['shadowMinimum'] for r in results)
    combined=[]
    for record in results:
        image=Image.open(inputDirectory/f"frame{record['frameId']}.png")
        combined.append({'frameId':record['frameId'],**profileSummary(image,shadowRed,shadowBlue)})
    output={'schema':'ECHO7_COLOUR_SAMPLE_AUDIT_1','layer':'MODEL','inputSource':'RECORDED_OV7670_PART_A',
            'orientationProfile':0,'rtlFormula':'(rawChannelMinimum + rawChannelMaximum) >> 2',
            'rawSamplingBeforeSegmentation':True,'frames':results,
            'combinedShadowProfile':{'redMin':shadowRed,'blueMin':shadowBlue},'combinedProfileTrials':combined,
            'limitation':'Three retained images are diagnostics only, not eight consecutive fresh calibration samples or a board commit.'}
    (outputDirectory/'calibration_profile_audit.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.inputs,args.out)
    print(json.dumps({'layer':result['layer'],'combinedShadowProfile':result['combinedShadowProfile'],
        'frames':[{'frameId':r['frameId'],'sampleGood':r['sameFrameRoiSamples']['frameSampleGood'],
        'stationary':r['previousRoiStationary'],'samples':r['sameFrameRoiSamples']} for r in result['frames']],
        'trials':[{'frameId':r['frameId'],'overflow':r['overflow'],'accepted':len(r['acceptedMarkers']),
                   'capacity':r['boundedCandidateOracle']} for r in result['combinedProfileTrials']]}))
    return 0


if __name__=='__main__':raise SystemExit(main())
