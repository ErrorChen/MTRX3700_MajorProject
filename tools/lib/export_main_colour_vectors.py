#!/usr/bin/env python3
"""Independent raw-colour/descriptor oracle vectors for the bounded reader7 CCL.

This input contains no digit answers. Full native 320x240 colour bits, original
candidate boxes, and all sixteen expected native supports are explicit. The
manifest preserves rejected cases, active-label overflow and input provenance.
"""
import argparse,json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tests/python'))
from test_main_colour_support import mainColourCases
from projective_reference import mainColourSupport


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--case',action='append',dest='caseNames')
    args=parser.parse_args();cases=list(mainColourCases())
    if args.caseNames:
        wanted=set(args.caseNames);cases=[case for case in cases if case['name'] in wanted]
        if {case['name'] for case in cases}!=wanted:raise ValueError('Unknown main-colour vector case')
    args.out.mkdir(parents=True,exist_ok=True);rows=[];manifest=[]
    for index,case in enumerate(cases):
        result=mainColourSupport(case['mask'],case['bbox'])
        row=[*case['bbox'],int(result['valid']),int(result['overflow']),result['foregroundCount'],result['mainArea'],
             result['allocationPeak'],0xffffffff if result['overflow'] else result['completedComponents'],
             *[value for point in result['supportPoints'] for value in point]]
        assert len(row)==42
        rows.extend(row)
        (args.out/f'main_colour_{index}.hex').write_text(''.join('1\n' if bit else '0\n' for bit in case['mask'].reshape(-1)),encoding='ascii')
        manifest.append({'index':index,**{k:v for k,v in case.items() if k!='mask'},'expected':result})
    (args.out/'main_colour_meta.hex').write_text(''.join(f'{value&0xffffffff:08x}\n' for value in rows),encoding='ascii')
    (args.out/'main_colour_count.hex').write_text(f'{len(cases):08x}\n',encoding='ascii')
    (args.out/'main_colour_record_words.hex').write_text('0000002a\n',encoding='ascii')
    data={'schema':'ECHO7_MAIN_COLOUR_VECTORS_1','readerAlgorithm':7,'recordWords':42,'activeCapacity':8,
          'wordLayout':'bbox xMin,yMin,xMax,yMax; valid,overflow,rawCount,mainArea,allocationPeak,componentCount; sixteen supportX,supportY pairs',
          'boundary':'MODEL oracle and explicit synthetic descriptors, not RTL simulation or another live camera acquisition.',
          'coverage':{'valid':sum(c['expected']['valid'] for c in manifest),'invalid':sum(not c['expected']['valid'] for c in manifest),
                      'overflow':sum(c['expected']['overflow'] for c in manifest)},'cases':manifest}
    (args.out/'main_colour_manifest.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'status':'PASS','layer':'VECTOR_GENERATION','cases':len(cases),'coverage':data['coverage'],'out':str(args.out)}))


if __name__=='__main__':main()
