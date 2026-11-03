#!/usr/bin/env python3
"""Emit explicit half-pixel/Q4 calibration geometry vectors, never digit IDs.

The 64-word record is fixed and documented in the manifest. Signed values are
32-bit two's-complement hexadecimal. A testbench must independently run the
real mapper/pairing FSM and compare valid and both polygons, including clearing
invalid results. This exporter alone is MODEL/VECTOR_GENERATION evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests/python'))
from test_projective_calibration import calibrationCases
from projective_calibration import pairReference

WORD_LAYOUT={
    '0..3':'inclusive native red bbox: xMin,yMin,xMax,yMax',
    '4..11':'red half-pixel quad: x0,y0,...,x3,y3; signed11',
    '12..19':'blue half-pixel quad: x0,y0,...,x3,y3; signed11',
    '20':'blueIsBay; accepted bays must never be a reference',
    '21':'expected pairValid',
    '22..29':'expected own red inset polygon Q4 x0,y0,...; unsigned13',
    '30..37':'expected own blue inset polygon Q4 x0,y0,...; unsigned13',
    '38':'diagnostic cyclicMatchCount; not a hardware output',
    '39':'diagnostic matched cyclic shift, or FFFFFFFF',
    '40..47':'diagnostic expected reference quad Q4, zero if unmappable',
    '48..55':'diagnostic measured blue quad Q4',
    '56':'redQuad.valid', '57':'blueQuad.valid', '58':'redBox.valid',
    '59..63':'reserved zero'}


def flatten(points):return [value for point in points for value in point]


def exportVectors(outputDir,extraCases=None):
    cases=list(calibrationCases());sources=[]
    # Keep the first frozen811-record dataset's ordering when the recorded
    # descriptors are supplied. Newly discovered arithmetic negatives append.
    appendedNames={'rounded_red_roi_zero_cross','extrapolated_reference_pole','expected_reference_outside_image',
                   'frame15078_blue_start_1','frame15078_blue_start_2','frame15078_blue_start_3'}
    appended=[case for case in cases if case['name'] in appendedNames]
    cases=[case for case in cases if case['name'] not in appendedNames]
    if extraCases is not None:
        payload=extraCases.read_bytes();data=json.loads(payload.decode('utf8'))
        if not isinstance(data,dict) or data.get('schema')!='echo7-calibration-geometry-inputs-v1':
            raise ValueError('Unexpected extra-case schema')
        if not isinstance(data.get('cases'),list):raise ValueError('Missing extra cases')
        cases.extend(data['cases'])
        sources.append({'path':str(extraCases),'sha256':hashlib.sha256(payload).hexdigest()})
    cases.extend(appended)
    outputDir.mkdir(parents=True,exist_ok=True);words=[];manifest=[]
    names=set()
    for index,case in enumerate(cases):
        if case['name'] in names:raise ValueError('Duplicate geometry case name')
        names.add(case['name'])
        args={key:case[key] for key in ('redQuadHalf','blueQuadHalf','redBox','blueIsBay')}
        for key in ('redQuadValid','blueQuadValid','redBoxValid'):
            if key in case:args[key]=case[key]
        result=pairReference(**args)
        row=[*case['redBox'],*flatten(case['redQuadHalf']),*flatten(case['blueQuadHalf']),
             int(case['blueIsBay']),int(result['pairValid']),*flatten(result['redPolygon']),
             *flatten(result['bluePolygon']),result['cyclicMatchCount'],
             0xffffffff if result['cyclicShift'] is None else result['cyclicShift'],
             *flatten(result['expectedStripQ4'] or [[0,0]]*4),*flatten(result['actualStripQ4']),
             int(case.get('redQuadValid',True)),int(case.get('blueQuadValid',True)),int(case.get('redBoxValid',True)),0,0,0,0,0]
        assert len(row)==64
        words.extend(row);manifest.append({'index':index,**case,'expected':result})
    (outputDir/'calibration_geometry_meta.hex').write_text(''.join(f'{value&0xffffffff:08x}\n' for value in words),encoding='ascii')
    (outputDir/'calibration_geometry_count.hex').write_text(f'{len(cases):08x}\n',encoding='ascii')
    (outputDir/'calibration_geometry_record_words.hex').write_text('00000040\n',encoding='ascii')
    data={'schema':'ECHO7_CALIBRATION_GEOMETRY_VECTORS_1','recordWords':64,'wordLayout':WORD_LAYOUT,
        'canonicalScale':320,'mappedFractionBits':4,'rounding':'FLOOR_INCLUDING_NEGATIVE',
        'formalReferenceApproximation':'V=334/320 and398/320; each differs from47/45 and56/45 by1/1440',
        'boundary':'Explicit geometry descriptors only; index and order do not encode marker identity. No new camera or RTL acceptance.',
        'extraInputSources':sources,'coverage':{'cases':len(cases),
            'valid':sum(c['expected']['pairValid'] for c in manifest),
            'invalid':sum(not c['expected']['pairValid'] for c in manifest)},'cases':manifest}
    (outputDir/'calibration_geometry_manifest.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--extra-cases',type=Path)
    args=parser.parse_args();result=exportVectors(args.out,args.extra_cases)
    print(json.dumps({'status':'PASS','level':'VECTOR_GENERATION','out':str(args.out),**result['coverage']}))


if __name__=='__main__':main()
