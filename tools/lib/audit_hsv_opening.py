#!/usr/bin/env python3
"""Diagnostic horizontal run support; does not alter runtime models or RTL."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tests/python"))
import json
from unittest.mock import patch
import numpy as np
from PIL import Image
import audit_hsv
from vision_reference import quantise565

root=Path(__file__).resolve().parents[2]
originalCleanup=audit_hsv.cleanup


def supportedRuns(mask,colourSelection='both'):
    matches=(mask[:,:-2]!=0)&(mask[:,:-2]==mask[:,1:-1])&(mask[:,:-2]==mask[:,2:])
    keep=np.zeros_like(mask,dtype=bool)
    keep[:,:-2]|=matches;keep[:,1:-1]|=matches;keep[:,2:]|=matches
    affected=np.ones_like(mask,dtype=bool) if colourSelection=='both' else mask==(1 if colourSelection=='red' else 2)
    filtered=np.where(affected&~keep,0,mask).astype(np.uint8)
    return originalCleanup(filtered)


def analyse(image,redMin,selection):
    mask=audit_hsv.hsvMask(image,redMin,32,0)
    with patch.object(audit_hsv,'cleanup',lambda raw:supportedRuns(raw,selection)):
        result=audit_hsv.candidateReport(image,mask)
    oracle=result['oracle']
    return {'accepted':result['accepted'],'rejected':result['rejected'],'overflow':oracle['overflow'],
            'redPeak':oracle['red_max_row_handles'],'bluePeak':oracle['blue_max_row_handles'],'oracle':oracle}


def main():
    inputs=[(frame,root/f'evidence/real_inputs/frame{frame}.png') for frame in (13139,13511,13675)]
    inputs.append((25046,root/'evidence/hsv_audit/frame25046.png'))
    profiles=[]
    for selection in ('both','red','blue'):
        for redMin in (48,37):
            frames=[]
            for frameId,path in inputs:
                image=quantise565(Image.open(path).convert('RGB'))
                frames.append({'frameId':frameId,**analyse(image,redMin,selection)})
            record={'filterColours':selection,'redMinimum':redMin,'blueMinimum':32,'runLength':3,'frames':frames}
            profiles.append(record)
            print(json.dumps({'selection':selection,'redMin':redMin,'frames':[(r['frameId'],len(r['accepted']),r['redPeak'],r['bluePeak'],r['overflow']) for r in frames]}),flush=True)
    image=Image.open(inputs[-1][1]).convert('RGB');gainResults=[]
    for selection in ('both','red','blue'):
        for redMin in (48,37):
            trials=[]
            for gain in (0.5,0.75,1,1.25,1.5,2):
                scaled=quantise565(Image.fromarray(np.clip(np.rint(np.asarray(image,dtype=float)*gain),0,255).astype(np.uint8)))
                trials.append({'gain':gain,'inputSource':'SYNTHETIC_RGB_GAIN_THEN_RGB565','frameId':25046,**analyse(scaled,redMin,selection)})
            gainResults.append({'filterColours':selection,'redMinimum':redMin,'blueMinimum':32,'trials':trials})
            print(json.dumps({'gainSelection':selection,'redMin':redMin,'trials':[(t['gain'],len(t['accepted']),t['redPeak'],t['bluePeak'],t['overflow']) for t in trials]}),flush=True)
    out=root/'build/member_b/hsv_audit_replay/horizontal_run_support.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'schema':'ECHO7_HSV_RUN_SUPPORT_1','layer':'MODEL_DIAGNOSTIC_ONLY','runtimeChanged':False,
        'algorithm':'Preserve all pixels of each same-colour horizontal run length>=3, suppress shorter runs; then original causal OR cleanup',
        'rawColourBank':'Original HSV mask, unchanged by support/cleanup; only candidate extraction sees filtered mask',
        'profiles':profiles,'syntheticGainTrials':gainResults},indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
