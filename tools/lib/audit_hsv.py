#!/usr/bin/env python3
"""Diagnostic HSV study from labelled, unfiltered camera ROIs.

This script does not change the runtime segmentation model or RTL. H is in
degrees, S in [0,1], and V in camera RGB 8-bit units. Synthetic illumination
scales are labelled image transformations and never hardware lighting tests.
Formula reference: https://docs.opencv.org/4.x/de/d25/imgproc_color_conversions.html
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tests/python"))
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
import projective_reference
from vision_reference import colourMask,quantise565

ROOT=Path(__file__).resolve().parents[2]
from analyse_capture import cleanup
from candidates_reclaimed_model import candidates_reclaimed

# Chosen visually before calculating HSV. Every inclusive raw pixel is kept.
# The name is a sampling label only; it never supplies a recognised digit.
ROIS={'red1':('red',[51,30,56,60]),'red2':('red',[45,177,50,207]),
      'orange':('orange',[260,90,280,140]),'blue1':('blue',[172,35,180,60]),
      'blueReference':('blue',[56,98,90,103])}


def hsvValues(pixels):
    rgb=np.asarray(pixels,dtype=np.float64)
    maximum=rgb.max(axis=-1);minimum=rgb.min(axis=-1);delta=maximum-minimum
    denominator=np.where(delta==0,1,delta)
    hue=np.zeros_like(maximum)
    for channel,offset,numerator in [(2,240,rgb[...,0]-rgb[...,1]),(1,120,rgb[...,2]-rgb[...,0]),(0,0,rgb[...,1]-rgb[...,2])]:
        hue=np.where((maximum==rgb[...,channel])&(delta!=0),offset+60*numerator/denominator,hue)
    hue%=360
    saturation=np.divide(delta,maximum,out=np.zeros_like(delta),where=maximum!=0)
    return hue,saturation,maximum


def hsvMask(image,redMin=37,blueMin=30,redUpper=0):
    rgb=np.asarray(image,dtype=np.int32)
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    maximum=rgb.max(axis=2);delta=maximum-rgb.min(axis=2)
    # Exact division-free HSV predicates. Red wraps at zero; blue stays within
    # the B-maximum sector. No conversion to rounded 8-bit hue is involved.
    saturated=(delta*2>=maximum)&(delta>0)
    red=(maximum==r)&(r>=redMin)&saturated&(60*(g-b)>=-24*delta)&(60*(g-b)<=redUpper*delta)
    blue=(maximum==b)&(b>=blueMin)&saturated&(60*(r-g)>=-40*delta)&(60*(r-g)<=10*delta)
    return np.where(red,1,np.where(blue,2,0)).astype(np.uint8)


def percentiles(values):
    if not len(values):return None
    return dict(zip(('min','p05','median','p95','max'),np.percentile(values,[0,5,50,95,100]).tolist()))


def pixelStats(pixels):
    hue,saturation,value=hsvValues(pixels)
    signedHue=np.where(hue>180,hue-360,hue)
    return {'count':len(pixels),'rgbMinimum':pixels.min(axis=0).tolist(),'rgbMaximum':pixels.max(axis=0).tolist(),
            'rgbMedian':np.median(pixels,axis=0).tolist(),'hueDegreesSigned':percentiles(signedHue),
            'saturation':percentiles(saturation),'value8':percentiles(value)} if len(pixels) else {'count':0}


def roiReport(image):
    rgb=np.asarray(image,dtype=np.int32)
    masks={'rgbDefault':np.array(colourMask(image,64,32,colourAlgorithm=0)).reshape(240,320),
           'rgbCalibrated':np.array(colourMask(image,37,30,colourAlgorithm=0)).reshape(240,320),
           'hsvUpper0':hsvMask(image),'hsvUpper1':hsvMask(image,redUpper=1),
           'hsvUpper2':hsvMask(image,redUpper=2)}
    output={}
    for name,(label,box) in ROIS.items():
        x0,y0,x1,y1=box;pixels=rgb[y0:y1+1,x0:x1+1].reshape(-1,3)
        hue,saturation,value=hsvValues(pixels)
        colourOnly=(saturation>=0.5)&(value>=24)
        output[name]={'labelForMeasurementOnly':label,'inclusiveRoi':box,'raw':pixelStats(pixels),
            'colourOnly':pixelStats(pixels[colourOnly]),'colourOnlySelection':'S>=0.5 and V>=24, independent of old mask or target hue',
            'classificationFractions':{key:{'red':float(np.mean(mask[y0:y1+1,x0:x1+1]==1)),
                'blue':float(np.mean(mask[y0:y1+1,x0:x1+1]==2))} for key,mask in masks.items()}}
    return output,masks


def candidateReport(image,mask):
    cleaned=cleanup(mask)
    oracle=candidates_reclaimed(cleaned.tolist(),cap=8,min_area=32)
    accepted=[];rejected=[]
    # The local audit substitutes only pixel segmentation; the unchanged
    # projective classifier still reads actual white pixels and chooses IDs.
    with patch.object(projective_reference,'colourMask',lambda *args,**kwargs:mask.reshape(-1).tolist()):
        for colour in ('red','blue'):
            for entry in oracle[colour]:
                candidate={'colour':colour,'bbox':[entry['xmin'],entry['ymin'],entry['xmax'],entry['ymax']],'area':entry['area']}
                decision=projective_reference.classifyProjective(image,candidate)
                simple={key:decision[key] for key in ('colour','bbox','digit','quality','reasonName')}
                (accepted if decision['accepted'] else rejected).append(simple)
    return {'oracle':oracle,'accepted':accepted,'rejected':rejected}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'build/member_b/hsv_audit_replay')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    inputs=[(frame,ROOT/f'evidence/real_inputs/frame{frame}.png') for frame in (13139,13511,13675)]
    inputs.append((25046,ROOT/'evidence/hsv_audit/frame25046.png'))
    records=[];contact=Image.new('RGB',(960,4*270),'white');draw=ImageDraw.Draw(contact)
    for row,(frameId,path) in enumerate(inputs):
        image=quantise565(Image.open(path).convert('RGB'));rois,masks=roiReport(image)
        annotated=image.copy();painter=ImageDraw.Draw(annotated)
        for name,(_,box) in ROIS.items():painter.rectangle(box,outline='lime');painter.text((box[0],box[1]),name,fill='yellow')
        contact.paste(annotated,(0,row*270+25));draw.text((3,row*270+5),f'Actual frame {frameId}: manual raw ROIs',fill='black')
        for column,key in enumerate(('rgbCalibrated','hsvUpper0'),1):
            palette=np.array([[0,0,0],[255,0,0],[0,80,255]],dtype=np.uint8)
            contact.paste(Image.fromarray(palette[masks[key]]),(column*320,row*270+25));draw.text((column*320+3,row*270+5),key,fill='black')
        gainTrials=[]
        for gain in (0.5,0.75,1,1.25,1.5,2):
            scaled=quantise565(Image.fromarray(np.clip(np.rint(np.asarray(image,dtype=np.float64)*gain),0,255).astype(np.uint8)))
            trial,_=roiReport(scaled)
            gainTrials.append({'gain':gain,'source':'SYNTHETIC_UNIFORM_RGB_GAIN_THEN_RGB565_QUANTISATION',
                'roiStatistics':trial,'clippedChannelFraction':float(np.mean(np.asarray(image)*gain>255))})
        record={'frameId':frameId,'inputSource':'REAL_OV7670_PART_A','path':str(path.relative_to(ROOT)).replace('\\','/'),
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rois':rois,'syntheticGainTrials':gainTrials,
                'rgbCalibratedCandidates':candidateReport(image,masks['rgbCalibrated']),
                'proposedHsvCandidates':candidateReport(image,masks['hsvUpper0'])}
        records.append(record)
        print(json.dumps({'frameId':frameId,'hsvAccepted':[(m['colour'],m['digit']) for m in record['proposedHsvCandidates']['accepted']],
                          'overflow':record['proposedHsvCandidates']['oracle']['overflow'],
                          'orangeFractions':rois['orange']['classificationFractions']}),flush=True)
    contact.save(args.out/'hsv_mask_contact_sheet.png')
    Image.open(inputs[-1][1]).save(args.out/'frame25046.png')
    result={'schema':'ECHO7_HSV_AUDIT_1','layer':'MODEL_ANALYSIS_OF_REAL_INPUTS','runtimeChanged':False,
            'reference':'https://docs.opencv.org/4.13.0/de/d25/imgproc_color_conversions.html#color_convert_rgb_hsv',
            'hueUnits':'degrees (not OpenCV 8-bit H/2)','proposal':{'redSignedDegrees':[-24,0],'blueDegrees':[200,250],
              'minimumSaturation':0.5,'redValueMinimum':37,'blueValueMinimum':30},
            'exactIntegerPredicates':{'red':'R=max && R>=redMin && delta>0 && 2*delta>=R && -24*delta<=60*(G-B)<=0',
                                      'blue':'B=max && B>=blueMin && delta>0 && 2*delta>=B && -40*delta<=60*(R-G)<=10*delta'},
            'frames':records,'limitations':['Four frames from one camera/lighting scene are not illumination generalisation',
              'Uniform RGB multiplication is synthetic and does not model changing spectrum, AWB, clipping or noise',
              'Orange hues overlap zero in earlier images; narrow-red rejection is empirical, not a guarantee for all orange materials',
              'Runtime/RTL models are unchanged; the proposed masks are diagnostic only']}
    (args.out/'hsv_audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return 0


if __name__=='__main__':raise SystemExit(main())
