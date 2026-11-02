#!/usr/bin/env python3
"""Reproducible native pixel/foreground/mask/candidate/projective RTL vectors."""
import argparse,json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tests/python"))
import numpy as np
from PIL import Image
from vision_reference import quantise565,colourMask,recognise,pixelsOf
from projective_reference import classifyProjective,gridAddresses
from export_vision_vectors import cases,packCandidate
from test_projective import warpedCases

root=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--colour-algorithm',type=int,choices=(0,1),default=1)
    parser.add_argument('--red-min',type=int,default=48);parser.add_argument('--blue-min',type=int,default=32)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    vectors=list(cases())
    vectors.extend((name,image,orientation) for name,image,orientation,expected in warpedCases())
    for frameId in (13139,13511,13675):
        vectors.append((f'recorded_camera_{frameId}',Image.open(root/f'evidence/real_inputs/frame{frameId}.png'),0))
    vectors.append(('recorded_camera_25046',Image.open(root/'evidence/hsv_audit/frame25046.png'),0))
    (args.out/'projective_count.hex').write_text(f'{len(vectors):08x}\n',encoding='ascii')
    manifest=[]
    for index,(name,image,orientation) in enumerate(vectors):
        image=quantise565(image);array=np.asarray(image,dtype=np.int16)
        foreground=np.array(colourMask(image,args.red_min,args.blue_min,colourAlgorithm=args.colour_algorithm)).reshape(240,320)!=0
        white=(array.min(axis=2)>=112)&(np.ptp(array,axis=2)<=64)
        base=recognise(image,cleanup=True,redMin=args.red_min,blueMin=args.blue_min,colourAlgorithm=args.colour_algorithm)
        candidateWords=[0]*16;expectedWords=[0x000f0001]*16;mapWords=[0xfffff]*(16*1280)
        counts={'red':0,'blue':0};expected=[]
        for candidate in base['markers']:
            fields={key:candidate[key] for key in ('colour','bbox','area')}
            colour=fields['colour'];slot=counts[colour]+(8 if colour=='blue' else 0);counts[colour]+=1
            assert counts[colour]<=8,'No truncated candidate vector permitted'
            candidateWords[slot]=packCandidate(fields)
            marker=classifyProjective(image,fields,orientation=orientation,redMin=args.red_min,blueMin=args.blue_min,colourAlgorithm=args.colour_algorithm)
            digit=marker['digit'] if marker['accepted'] else 15
            expectedWords[slot]=(int(marker['accepted'])<<24)|(digit<<16)|(marker['quality']<<8)|marker['reasonCode']
            if marker['reasonCode'] not in (1,6):
                addresses=gridAddresses(marker['coefficients'])
                for pixel,(x,y) in enumerate(addresses):mapWords[slot*1280+pixel]=(y<<9)|x
            expected.append({'slot':slot,**marker})
        prefix=args.out/f'projective_{index}'
        image.save(prefix.with_suffix('.png'))
        Path(str(prefix)+'_colour.hex').write_text(''.join('1\n' if bit else '0\n' for bit in foreground.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_white.hex').write_text(''.join('1\n' if bit else '0\n' for bit in white.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_candidates.hex').write_text(''.join(f'{word:018x}\n' for word in candidateWords),encoding='ascii')
        Path(str(prefix)+'_expected.hex').write_text(''.join(f'{word:08x}\n' for word in expectedWords),encoding='ascii')
        Path(str(prefix)+'_orientation.hex').write_text(f'{orientation:x}\n',encoding='ascii')
        Path(str(prefix)+'_map.hex').write_text(''.join(f'{word:05x}\n' for word in mapWords),encoding='ascii')
        pixels=[((r>>3)<<11)|((g>>2)<<5)|(b>>3) for r,g,b in pixelsOf(image)]
        Path(str(prefix)+'_rgb565.hex').write_text(''.join(f'{word:04x}\n' for word in pixels),encoding='ascii')
        manifest.append({'index':index,'name':name,'orientation':orientation,'expected':expected,
                         'inputSource':'RECORDED_OV7670_PART_A' if name.startswith('recorded_camera_') else 'SYNTHETIC_PIXELS'})
    (args.out/'projective_manifest.json').write_text(json.dumps({'schema':'ECHO7_PROJECTIVE_VECTORS_2','colourAlgorithm':args.colour_algorithm,
        'redMinimum':args.red_min,'blueMinimum':args.blue_min,'whiteMin':112,'maximumSpread':64,'cases':manifest},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','layer':'VECTOR_GENERATION','cases':len(vectors),'out':str(args.out)}))

if __name__=='__main__':main()
