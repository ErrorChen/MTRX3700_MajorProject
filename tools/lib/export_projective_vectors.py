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
from test_projective import warpedCases,algorithm2Cases,algorithm3Cases,algorithm4Cases

root=Path(__file__).resolve().parents[2]

RECORDED_SOURCE='RECORDED_OV7670_STATIONARY_BASELINE'


def rgb565Text(image):
    """The replay input is decoded pixels, never an OV7670 byte-stream dump."""
    return ''.join(f'{((r>>3)<<11)|((g>>2)<<5)|(b>>3):04x}\n' for r,g,b in pixelsOf(image))


def namedFixtureBindings(vectorCases,readerAlgorithm=9):
    """Resolve semantic fixtures by unique name, independently of list order.

    A physical recording must also match the preserved acquisition index. This
    rejects a synthetic case accidentally labelled as a recorded input, even if
    its former numeric position happens to be the one a bench once loaded.
    """
    inputIndex=json.loads((root/'tests/fixtures/camera/reader_algorithm2.json').read_text())
    if readerAlgorithm>=3:
        inputIndex['records']+=json.loads((root/'tests/fixtures/camera/reader_algorithm3.json').read_text())['records']
    if readerAlgorithm>=4:
        inputIndex['records']+=json.loads((root/'tests/fixtures/camera/reader_algorithm4.json').read_text())['records']
    recordedPrefix='real_frame' if readerAlgorithm>=2 else 'recorded_camera_'
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
        caseName=f'real_frame{frameId}' if readerAlgorithm>=2 else f'recorded_camera_{frameId}'
        # Algorithm 1 intentionally retains only its four historical recordings.
        if readerAlgorithm==1 and frameId not in (13139,13511,13675,25046):continue
        case=byName.get(caseName)
        sourceKind=record['source'] if record['source']=='RECORDED_OV7670_MEMBER_B' else RECORDED_SOURCE
        if case is None or case['inputSource']!=sourceKind or case['candidateOverflow']:
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


def writeNamedAliases(outputDir,vectorCases,readerAlgorithm=9,sharedPool=None):
    """Write stable replay aliases and an auditable source-to-export hash chain."""
    bindings=namedFixtureBindings(vectorCases,readerAlgorithm)
    if sharedPool is None:sharedPool=readerAlgorithm>=5
    for binding in bindings:
        suffixes=('rgb565','candidates','expected') if binding['alias'].startswith('continuous_') else ('rgb565',)
        if sharedPool and binding['alias'].startswith('continuous_'):
            suffixes+=('candidate_colours',)
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
    parser.add_argument('--colour-algorithm',type=int,choices=(0,1,2,3))
    parser.add_argument('--reader-algorithm',type=int,choices=(1,2,3,4,5,6,7,8,9),default=9)
    parser.add_argument('--capture-result',type=Path,help='One actual verified GRAB result and its recorded profile; no synthetic substitutions')
    parser.add_argument('--bypass-perspective',action='store_true')
    poolGroup=parser.add_mutually_exclusive_group()
    poolGroup.add_argument('--shared-pool',action='store_true',dest='sharedPool',default=None)
    poolGroup.add_argument('--split-pool',action='store_false',dest='sharedPool',help='Historical reader5/schema6 separate pools; requires its historical 32-slot RTL consumer')
    parser.add_argument('--case',action='append',dest='caseNames',help='Export only named cases for an attributable targeted RTL replay')
    parser.add_argument('--red-min',type=int,default=48);parser.add_argument('--blue-min',type=int)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    if args.colour_algorithm is None:
        args.colour_algorithm=3 if args.reader_algorithm>=5 else 2 if args.reader_algorithm==4 else 1
    if args.blue_min is None:args.blue_min=20 if args.reader_algorithm>=4 else 32
    captureBinding=None
    activeCapacity=15 if args.reader_algorithm>=4 else 8
    outputCapacity=16 if args.reader_algorithm>=5 else 8
    sharedPool=args.reader_algorithm>=5 if args.sharedPool is None else args.sharedPool
    if args.capture_result:
        capture=json.loads(args.capture_result.read_text(encoding='utf-8'))
        measured=capture['recognition']
        if measured.get('rawCameraMode'):
            raise ValueError('R7 recognition replay requires an algorithm-enabled capture; raw-camera mode intentionally has no recogniser output')
        if not capture.get('fresh') or not measured.get('sameFrameVerified'):
            raise ValueError('R7 input must be a verified fresh same-frame camera acquisition')
        imagePath=args.capture_result.parent/'capture/frame.png'
        args.reader_algorithm=measured['readerAlgorithm'];args.colour_algorithm=measured['colourAlgorithm']
        args.red_min=measured['redMinimum'];args.blue_min=measured['blueMinimum']
        activeCapacity=measured['activeCandidateCapacity'] if measured['debugSchemaVersion']>=4 else 8
        outputCapacity=measured['outputCandidateCapacity']
        sharedPool=measured['debugSchemaVersion']>=7
        captureBinding={'frameId':measured['frameId'],'configVersion':measured['configVersion'],
            'buildId':measured['buildId'],'captureResultSha256':hashlib.sha256(args.capture_result.read_bytes()).hexdigest(),
            'imageSha256':hashlib.sha256(imagePath.read_bytes()).hexdigest(),
            'capturedBypassPerspective':measured['bypassPerspective'],
            'boundary':'Recorded camera pixels replayed offline; this simulation is not another live acquisition.'}
        vectors=[(f"held_out_frame{measured['frameId']}",Image.open(imagePath),
            measured['orientationProfile'],None,'RECORDED_CAMERA_EXPLICIT_PROFILE')]
    elif args.reader_algorithm==9:
        from test_reader9_decode import algorithm9Cases
        vectors=list(algorithm9Cases())
    elif args.reader_algorithm==8:
        from test_reader8_decode import algorithm8Cases
        vectors=list(algorithm8Cases())
    elif args.reader_algorithm==7:
        from test_main_colour_support import algorithm7Cases
        vectors=list(algorithm7Cases())
    elif args.reader_algorithm==6:
        from test_anchor_ownership import algorithm6Cases
        vectors=list(algorithm6Cases())
    elif args.reader_algorithm==5:
        from test_auto_orientation import algorithm5Cases
        vectors=list(algorithm5Cases())
    elif args.reader_algorithm==4:
        vectors=list(algorithm4Cases())
    elif args.reader_algorithm==3:
        vectors=list(algorithm3Cases())
    elif args.reader_algorithm==2:
        vectors=list(algorithm2Cases())
    else:
        # Keep the exact historical 63-case ordering and white semantics.
        legacy=list(cases())
        legacy.extend((name,image,orientation) for name,image,orientation,expected in warpedCases())
        for frameId in (13139,13511,13675):legacy.append((f'recorded_camera_{frameId}',Image.open(root/f'tests/fixtures/camera/frame{frameId}/frame.png'),0))
        legacy.append(('recorded_camera_25046',Image.open(root/'tests/fixtures/camera/frame25046/frame.png'),0))
        vectors=[(name,image,orientation,None,'RECORDED_OV7670_STATIONARY_BASELINE' if name.startswith('recorded_camera_') else 'SYNTHETIC_PIXELS') for name,image,orientation in legacy]
    if args.caseNames:
        wanted=set(args.caseNames)
        vectors=[vector for vector in vectors if vector[0] in wanted]
        if {vector[0] for vector in vectors}!=wanted:raise ValueError('Requested projective case was not found or uniquely named')
    if sharedPool and args.reader_algorithm<5:
        raise ValueError('Shared completed pool requires reader5/6/7')
    whiteProfile=whiteProfileFor(args.reader_algorithm)
    (args.out/'projective_count.hex').write_text(f'{len(vectors):08x}\n',encoding='ascii')
    (args.out/'projective_slot_count.hex').write_text(f'{outputCapacity if sharedPool else 2*outputCapacity:08x}\n',encoding='ascii')
    (args.out/'projective_shared_pool.hex').write_text(f'{int(sharedPool):x}\n',encoding='ascii')
    manifest=[];anchorRows=[];anchorManifest=[]
    descriptorOverrides={}
    if args.reader_algorithm>=7 and not args.capture_result:
        from test_main_colour_support import mainDescriptorCases
        descriptorOverrides={case['name']:case['candidates'] for case in mainDescriptorCases()}
    for index,(name,image,orientation,expectedIds,inputSource) in enumerate(vectors):
        image=quantise565(image);array=np.asarray(image,dtype=np.int16)
        foreground=np.array(colourMask(image,args.red_min,args.blue_min,colourAlgorithm=args.colour_algorithm)).reshape(240,320)!=0
        white=whitePixelsFor(array,whiteProfile)
        strongWhite=whitePixelsFor(array,whiteProfile,anchor=True)
        base=recognise(image,cleanup=True,redMin=args.red_min,blueMin=args.blue_min,colourAlgorithm=args.colour_algorithm,
                       pruneUnusable=args.reader_algorithm>=3,activeCapacity=activeCapacity,capacity=outputCapacity,
                       sharedCapacity=outputCapacity if sharedPool else None)
        slots=outputCapacity if sharedPool else 2*outputCapacity
        candidateWords=[0]*slots;expectedWords=[0x000f0001]*slots;mapWords=[0xfffff]*(slots*1280)
        candidateColours=[0]*slots
        expectedColourQuads=[0]*(slots*9)
        expectedThinSupport=[0]*slots
        expectedOrientations=[orientation]*slots
        counts={'red':0,'blue':0};expected=[]
        candidateRows=descriptorOverrides.get(name,base['markers'])
        # This fixture changes only the explicit input-slot permutation. The
        # recogniser must follow the independent colour bitmap and pixels.
        if sharedPool and name.startswith('shared_shuffled_'):
            candidateRows=list(reversed(candidateRows))
        for candidateNumber,candidate in enumerate(candidateRows):
            fields={key:candidate[key] for key in ('colour','bbox','area')}
            colour=fields['colour'];slot=candidateNumber if sharedPool else counts[colour]+(outputCapacity if colour=='blue' else 0);counts[colour]+=1
            assert slot<slots and counts[colour]<=outputCapacity,'No truncated candidate vector permitted'
            candidateWords[slot]=packCandidate(fields)
            candidateColours[slot]=int(colour=='blue')
            marker=classifyProjective(image,fields,orientation=orientation,redMin=args.red_min,blueMin=args.blue_min,
                                     colourAlgorithm=args.colour_algorithm,readerAlgorithm=args.reader_algorithm,bypassPerspective=args.bypass_perspective)
            digit=marker['digit'] if marker['accepted'] else 15
            expectedWords[slot]=(int(marker['accepted'])<<24)|(digit<<16)|(marker['quality']<<8)|marker['reasonCode']
            expectedOrientations[slot]=marker['orientationProfile']
            expectedThinSupport[slot]=int(marker.get('anchorSupportMode')=='STRICT_THIN_SEED_WEAK_SUPPORT')
            if args.reader_algorithm>=8:
                quad=marker['colourQuad']
                expectedColourQuads[slot*9:slot*9+9]=[int(quad['valid']),
                    *[coordinate for point in zip(quad['x'],quad['y']) for coordinate in point]]
            if marker.get('gridSampled',marker['reasonCode'] not in (1,6)):
                addresses=gridAddresses(marker['coefficients'])
                for pixel,(x,y) in enumerate(addresses):mapWords[slot*1280+pixel]=(y<<9)|x
            expected.append({'slot':slot,**marker})
            # Reader5's prepass can reject before a glyph grid/windowScores
            # exists. Export every actually evaluated native hypothesis so
            # missing, multiple-component and active-overflow ROIs remain in
            # the independent native-reader bench. In particular, do not
            # filter out the very negative branches that the bench must prove.
            anchorInputs=[]
            if args.reader_algorithm>=5:
                anchorInputs=[(hypothesis['anchor'],hypothesis['quadHalfPixels'],hypothesis['orientation'])
                              for hypothesis in marker.get('orientationHypotheses',[])]
            elif args.reader_algorithm>=2 and 'anchor' in marker['windowScores']:
                anchorInputs=[(marker['windowScores']['anchor'],marker['quadHalfPixels'],marker['orientationProfile'])]
            for anchor,quad,anchorOrientation in anchorInputs:
                roi=anchor['roi']
                row=[index,*[coordinate for point in quad for coordinate in point],*roi,
                     anchor['white'],anchor['columns'],anchor['rows'],int(anchor['ambiguous']),int(anchor['overflow']),
                     min(8,anchor['peakActiveHandles']),0xffffffff if anchor['overflow'] else anchor['completedComponents']]
                assert len(row)==20
                if args.reader_algorithm>=6:
                    # Native pixels, inclusive original candidate bbox. This is
                    # geometry input to the reader, never a digit/orientation
                    # answer. Keep historical 20-word records byte-for-byte.
                    row.extend(fields['bbox'])
                anchorRows.append(row)
                anchorManifest.append({'sourceIndex':index,'case':name,'slot':slot,
                    'orientationHypothesis':anchorOrientation,'quadHalfPixels':quad,**anchor})
        prefix=args.out/f'projective_{index}'
        image.save(prefix.with_suffix('.png'))
        Path(str(prefix)+'_colour.hex').write_text(''.join('1\n' if bit else '0\n' for bit in foreground.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_white.hex').write_text(''.join('1\n' if bit else '0\n' for bit in white.reshape(-1)),encoding='ascii')
        # Historical readers use identical white predicates for both consumers;
        # the additional file leaves all of their existing hex bytes unchanged.
        Path(str(prefix)+'_strong_white.hex').write_text(''.join('1\n' if bit else '0\n' for bit in strongWhite.reshape(-1)),encoding='ascii')
        Path(str(prefix)+'_candidates.hex').write_text(''.join(f'{word:018x}\n' for word in candidateWords),encoding='ascii')
        if sharedPool:
            Path(str(prefix)+'_candidate_colours.hex').write_text(''.join(f'{value:x}\n' for value in candidateColours),encoding='ascii')
        Path(str(prefix)+'_expected.hex').write_text(''.join(f'{word:08x}\n' for word in expectedWords),encoding='ascii')
        Path(str(prefix)+'_orientation.hex').write_text(f'{orientation:x}\n',encoding='ascii')
        Path(str(prefix)+'_expected_orientation.hex').write_text(''.join(f'{value:x}\n' for value in expectedOrientations),encoding='ascii')
        if args.reader_algorithm>=8:
            Path(str(prefix)+'_expected_colour_quads.hex').write_text(''.join(f'{value&0xffffffff:08x}\n' for value in expectedColourQuads),encoding='ascii')
        if args.reader_algorithm==9:
            # Successful anchor fallback remains selected even if a later
            # stroke/unknown-pattern check rejects the digit. SW8 is always0.
            Path(str(prefix)+'_expected_thin_support.hex').write_text(''.join(f'{value:x}\n' for value in expectedThinSupport),encoding='ascii')
        Path(str(prefix)+'_map.hex').write_text(''.join(f'{word:05x}\n' for word in mapWords),encoding='ascii')
        Path(str(prefix)+'_rgb565.hex').write_text(rgb565Text(image),encoding='ascii')
        manifest.append({'index':index,'name':name,'orientation':orientation,'expected':expected,
                         'candidateSource':'EXPLICIT_PIXEL_DESCRIPTOR_UNIT_STRESS' if name in descriptorOverrides else 'MODEL_COLOUR_CANDIDATES',
                         'inputSource':inputSource,'expectedIds':expectedIds,'candidateOverflow':base['overflow']})
    namedFixtures={'fixtures':[]} if args.capture_result or args.caseNames else writeNamedAliases(args.out,manifest,args.reader_algorithm,sharedPool)
    (args.out/'projective_manifest.json').write_text(json.dumps({'schema':'ECHO7_PROJECTIVE_VECTORS_8' if args.reader_algorithm==9 else 'ECHO7_PROJECTIVE_VECTORS_7' if args.reader_algorithm==8 else 'ECHO7_PROJECTIVE_VECTORS_6' if args.reader_algorithm>=7 else 'ECHO7_PROJECTIVE_VECTORS_5' if args.reader_algorithm>=6 else 'ECHO7_PROJECTIVE_VECTORS_4' if sharedPool else 'ECHO7_PROJECTIVE_VECTORS_3','colourAlgorithm':args.colour_algorithm,
        'readerAlgorithm':args.reader_algorithm,'redMinimum':args.red_min,'blueMinimum':args.blue_min,'bypassPerspective':args.bypass_perspective,
        'whiteProfile':whiteProfile,'whiteMin':whiteProfile['minimum'],'maximumSpread':64,
        'activeCapacity':activeCapacity,'outputCapacity':outputCapacity,'captureBinding':captureBinding,
        'candidatePoolMode':'SHARED' if sharedPool else 'SPLIT_PER_COLOUR',
        **({'colourQuadRecordWords':9,'colourQuadLayout':'valid; signed half-pixel x0,y0,x1,y1,x2,y2,x3,y3',
            'colourQuadSource':'SAME_FRAME_RAW_MAIN_COMPONENT; independent of digit acceptance'} if args.reader_algorithm>=8 else {}),
        **({'anchorFallback':'STRICT_ZERO_GLOBAL_UNIQUE_THIN_SEED_CLOSED_WEAK_SUPPORT','fallbackQualityMaximum':192,
            'bypassAnchorFallback':False,'thinSupportFileSuffix':'_expected_thin_support.hex',
            'thinSupportMeaning':'One bit per slot: fallback supplied the anchor, including later rejected glyphs'} if args.reader_algorithm==9 else {}),
        'candidateOrder':'MODEL_CANONICAL_GEOMETRY_NOT_RTL_RETIREMENT_ORDER; shared_shuffled cases reverse the explicit slot order',
        'namedFixtures':namedFixtures['fixtures'],'cases':manifest},indent=2)+'\n',encoding='utf-8')
    (args.out/'anchor_count.hex').write_text(f'{len(anchorRows):08x}\n',encoding='ascii')
    recordWords=24 if args.reader_algorithm>=6 else 20
    (args.out/'anchor_record_words.hex').write_text(f'{recordWords:08x}\n',encoding='ascii')
    (args.out/'anchor_meta.hex').write_text(''.join(f'{value&0xffffffff:08x}\n' for row in anchorRows for value in row),encoding='ascii')
    (args.out/'anchor_manifest.json').write_text(json.dumps({'schema':'ECHO7_NATIVE_ANCHOR_VECTORS_2' if args.reader_algorithm>=6 else 'ECHO7_NATIVE_ANCHOR_VECTORS_1','readerAlgorithm':args.reader_algorithm,
        'recordWords':recordWords,'ownerBboxWordOffsets':{'xMin':20,'yMin':21,'xMax':22,'yMax':23} if args.reader_algorithm>=6 else None,
        'coverage':{'valid':sum(row['white']>0 for row in anchorManifest),
        'ambiguous':sum(row['ambiguous'] for row in anchorManifest),'overflow':sum(row['overflow'] for row in anchorManifest)},
        'cases':anchorManifest},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','layer':'VECTOR_GENERATION','readerAlgorithm':args.reader_algorithm,
        'cases':len(vectors),'nativeAnchorRois':len(anchorRows),'out':str(args.out)}))

if __name__=='__main__':main()
