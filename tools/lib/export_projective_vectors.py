#!/usr/bin/env python3
"""Reproducible native pixel/foreground/mask/candidate/projective RTL vectors."""
import argparse,hashlib,json,shutil
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"tests/python"))
import numpy as np
from PIL import Image
from vision_reference import quantise565,colourMask,recognise,pixelsOf
from projective_reference import classifyProjective,gridAddresses,whiteProfileFor,whitePixelsFor
from export_vision_vectors import cases,packCandidate
from test_projective import warpedCases,algorithm2Cases

root=Path(__file__).resolve().parents[2]

RECORDED_SOURCE='RECORDED_OV7670_STATIONARY_BASELINE'


def rgb565Text(image):
    """The replay input is decoded pixels, never an OV7670 byte-stream dump."""
    return ''.join(f'{((r>>3)<<11)|((g>>2)<<5)|(b>>3):04x}\n' for r,g,b in pixelsOf(image))


def namedFixtureBindings(vectorCases,readerAlgorithm=2):
    """Resolve semantic fixtures by unique name, independently of list order.

    A physical recording must also match the preserved acquisition index. This
    rejects a synthetic case accidentally labelled as a recorded input, even if
    its former numeric position happens to be the one a bench once loaded.
    """
    inputIndex=json.loads((root/'evidence/reader_algorithm2_inputs/index.json').read_text())
    recordedPrefix='real_frame' if readerAlgorithm==2 else 'recorded_camera_'
    wantedNames={f"{recordedPrefix}{record['frameId']}" for record in inputIndex['records']}
    wantedNames.update(('pdf_full_page','counterfactual_swapped'))
    byName={}
    for case in vectorCases:
        # General orientation cases intentionally share historical names across
        # two suites. Only names used as stable semantic aliases must be unique.
        if case['name'] not in wantedNames:continue
        if case['name'] in byName:raise ValueError(f"Duplicate fixture name: {case['name']}")
        byName[case['name']]=case
    bindings=[]
    for record in inputIndex['records']:
        frameId=record['frameId']
        caseName=f'real_frame{frameId}' if readerAlgorithm==2 else f'recorded_camera_{frameId}'
        # Algorithm 1 intentionally retains only its four historical recordings.
        if readerAlgorithm==1 and frameId not in (13139,13511,13675,25046):continue
        case=byName.get(caseName)
        if case is None or case['inputSource']!=RECORDED_SOURCE or case['candidateOverflow']:
            raise ValueError(f'Recorded fixture missing, mislabelled or overflowed: {caseName}')
        imagePath=root/record['image']
        actualHash=hashlib.sha256(imagePath.read_bytes()).hexdigest()
        if actualHash!=record['sha256']:raise ValueError(f'Recorded PNG hash changed: {imagePath}')
        bindings.append({'alias':f'recorded_frame{frameId}','caseName':caseName,'index':case['index'],
                         'inputSource':case['inputSource'],'frameId':frameId,'sourcePng':record['image'],
                         'sourcePngSha256':actualHash,'files':{}})
    for alias,caseName in (('continuous_0','pdf_full_page'),('continuous_1','counterfactual_swapped')):
        case=byName.get(caseName)
        if case is None or not case['inputSource'].startswith('SYNTHETIC_') or case['candidateOverflow']:
            raise ValueError(f'Synthetic continuous fixture missing, mislabelled or overflowed: {caseName}')
        bindings.append({'alias':alias,'caseName':caseName,'index':case['index'],
                         'inputSource':case['inputSource'],'files':{}})
    return bindings


def writeNamedAliases(outputDir,vectorCases,readerAlgorithm=2):
    """Write stable replay aliases and an auditable source-to-export hash chain."""
    bindings=namedFixtureBindings(vectorCases,readerAlgorithm)
    for binding in bindings:
        suffixes=('rgb565','candidates','expected') if binding['alias'].startswith('continuous_') else ('rgb565',)
        for suffix in suffixes:
            source=outputDir/f"projective_{binding['index']}_{suffix}.hex"
            sourceHash=hashlib.sha256(source.read_bytes()).hexdigest()
            if 'sourcePng' in binding:
                with Image.open(root/binding['sourcePng']) as original:
                    expectedText=rgb565Text(quantise565(original.convert('RGB')))
                if source.read_text(encoding='ascii')!=expectedText:
                    raise ValueError(f"Recorded replay pixels do not match source PNG: {binding['caseName']}")
                binding['decodedRgb565LfSha256']=hashlib.sha256(expectedText.encode('ascii')).hexdigest()
            destination=outputDir/f"{binding['alias']}_{suffix}.hex"
            shutil.copyfile(source,destination)
            binding['files'][suffix]={'path':destination.name,'sourcePath':source.name,'sha256':sourceHash}
    result={'schema':'ECHO7_NAMED_REPLAY_FIXTURES_1','readerAlgorithm':readerAlgorithm,'fixtures':bindings,
            'boundary':'Recorded aliases replay one preserved camera PNG through the post-capture RTL pixel interface; this is not a new camera acquisition.'}
    (outputDir/'named_fixtures.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--colour-algorithm',type=int,choices=(0,1),default=1)
    parser.add_argument('--reader-algorithm',type=int,choices=(1,2),default=2)
    parser.add_argument('--red-min',type=int,default=48);parser.add_argument('--blue-min',type=int,default=32)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.reader_algorithm==2:
        vectors=list(algorithm2Cases())
    else:
        # Keep the exact historical 63-case ordering and white semantics.
        legacy=list(cases())
        legacy.extend((name,image,orientation) for name,image,orientation,expected in warpedCases())
        for frameId in (13139,13511,13675):legacy.append((f'recorded_camera_{frameId}',Image.open(root/f'evidence/real_inputs/frame{frameId}.png'),0))
        legacy.append(('recorded_camera_25046',Image.open(root/'evidence/hsv_audit/frame25046.png'),0))
        vectors=[(name,image,orientation,None,'RECORDED_OV7670_STATIONARY_BASELINE' if name.startswith('recorded_camera_') else 'SYNTHETIC_PIXELS') for name,image,orientation in legacy]
    whiteProfile=whiteProfileFor(args.reader_algorithm)
    (args.out/'projective_count.hex').write_text(f'{len(vectors):08x}\n',encoding='ascii')
    manifest=[];anchorRows=[];anchorManifest=[]
    for index,(name,image,orientation,expectedIds,inputSource) in enumerate(vectors):
        image=quantise565(image);array=np.asarray(image,dtype=np.int16)
        foreground=np.array(colourMask(image,args.red_min,args.blue_min,colourAlgorithm=args.colour_algorithm)).reshape(240,320)!=0
        white=whitePixelsFor(array,whiteProfile)
        base=recognise(image,cleanup=True,redMin=args.red_min,blueMin=args.blue_min,colourAlgorithm=args.colour_algorithm)
        candidateWords=[0]*16;expectedWords=[0x000f0001]*16;mapWords=[0xfffff]*(16*1280)
        counts={'red':0,'blue':0};expected=[]
        for candidate in base['markers']:
            fields={key:candidate[key] for key in ('colour','bbox','area')}
            colour=fields['colour'];slot=counts[colour]+(8 if colour=='blue' else 0);counts[colour]+=1
            assert counts[colour]<=8,'No truncated candidate vector permitted'
            candidateWords[slot]=packCandidate(fields)
            marker=classifyProjective(image,fields,orientation=orientation,redMin=args.red_min,blueMin=args.blue_min,
                                     colourAlgorithm=args.colour_algorithm,readerAlgorithm=args.reader_algorithm)
            digit=marker['digit'] if marker['accepted'] else 15
            expectedWords[slot]=(int(marker['accepted'])<<24)|(digit<<16)|(marker['quality']<<8)|marker['reasonCode']
            if marker['reasonCode'] not in (1,6):
                addresses=gridAddresses(marker['coefficients'])
                for pixel,(x,y) in enumerate(addresses):mapWords[slot*1280+pixel]=(y<<9)|x
            expected.append({'slot':slot,**marker})
            if args.reader_algorithm==2 and 'anchor' in marker['windowScores']:
                anchor=marker['windowScores']['anchor'];quad=marker['quadHalfPixels'];roi=anchor['roi']
                row=[index,*[coordinate for point in quad for coordinate in point],*roi,
                     anchor['white'],anchor['columns'],anchor['rows'],int(anchor['ambiguous']),int(anchor['overflow']),
                     min(8,anchor['peakActiveHandles']),0xffffffff if anchor['overflow'] else anchor['completedComponents']]
                assert len(row)==20
                anchorRows.append(row)
                anchorManifest.append({'sourceIndex':index,'case':name,'slot':slot,'quadHalfPixels':quad,**anchor})
        prefix=args.out/f'projective_{index}'
        image.save(prefix.with_suffix('.png'))
        Path(str(prefix)+'_colour.hex').write_text(''.join('1\n' if bit else '0\n' for bit in foreground.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_white.hex').write_text(''.join('1\n' if bit else '0\n' for bit in white.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_candidates.hex').write_text(''.join(f'{word:018x}\n' for word in candidateWords),encoding='ascii')
        Path(str(prefix)+'_expected.hex').write_text(''.join(f'{word:08x}\n' for word in expectedWords),encoding='ascii')
        Path(str(prefix)+'_orientation.hex').write_text(f'{orientation:x}\n',encoding='ascii')
        Path(str(prefix)+'_map.hex').write_text(''.join(f'{word:05x}\n' for word in mapWords),encoding='ascii')
        Path(str(prefix)+'_rgb565.hex').write_text(rgb565Text(image),encoding='ascii')
        manifest.append({'index':index,'name':name,'orientation':orientation,'expected':expected,
                         'inputSource':inputSource,'expectedIds':expectedIds,'candidateOverflow':base['overflow']})
    namedFixtures=writeNamedAliases(args.out,manifest,args.reader_algorithm)
    (args.out/'projective_manifest.json').write_text(json.dumps({'schema':'ECHO7_PROJECTIVE_VECTORS_3','colourAlgorithm':args.colour_algorithm,
        'readerAlgorithm':args.reader_algorithm,'redMinimum':args.red_min,'blueMinimum':args.blue_min,
        'whiteProfile':whiteProfile,'whiteMin':whiteProfile['minimum'],'maximumSpread':64,
        'namedFixtures':namedFixtures['fixtures'],'cases':manifest},indent=2)+'\n',encoding='utf-8')
    (args.out/'anchor_count.hex').write_text(f'{len(anchorRows):08x}\n',encoding='ascii')
    (args.out/'anchor_meta.hex').write_text(''.join(f'{value&0xffffffff:08x}\n' for row in anchorRows for value in row),encoding='ascii')
    (args.out/'anchor_manifest.json').write_text(json.dumps({'schema':'ECHO7_NATIVE_ANCHOR_VECTORS_1','readerAlgorithm':args.reader_algorithm,
        'recordWords':20,'cases':anchorManifest},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','layer':'VECTOR_GENERATION','readerAlgorithm':args.reader_algorithm,
        'cases':len(vectors),'nativeAnchorRois':len(anchorRows),'out':str(args.out)}))

if __name__=='__main__':main()
