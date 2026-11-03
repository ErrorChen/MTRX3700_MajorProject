#!/usr/bin/env python3
"""Independent component-oracle vectors for the reader9 native anchor scan.

Synthetic masks test general geometry, never digit IDs or scene slots. The one
recorded image uses its preserved acquisition profile and measured colour quad.
BFS supplies component membership independently of the RTL row-label schedule.
"""
from pathlib import Path
from collections import deque
import argparse, hashlib, json, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def components(mask, roi):
    x0,y0,x1,y1=roi; seen=set(); result=[]
    for y in range(y0,y1+1):
        for x in range(x0,x1+1):
            if not mask[y,x] or (x,y) in seen: continue
            points={(x,y)}; seen.add((x,y)); queue=deque([(x,y)])
            while queue:
                px,py=queue.popleft()
                for nx,ny in ((px-1,py),(px+1,py),(px,py-1),(px,py+1)):
                    if x0<=nx<=x1 and y0<=ny<=y1 and mask[ny,nx] and (nx,ny) not in seen:
                        seen.add((nx,ny)); points.add((nx,ny)); queue.append((nx,ny))
            result.append(points)
    return result


def bounds(points):
    return [min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points)]


def region(quad):
    # Direct integer version of the original affine anchor search window.
    vertices=[[20*quad[0][a]+s*(quad[1][a]-quad[0][a])+t*(quad[3][a]-quad[0][a]) for a in (0,1)]
              for s,t in ((-3,-1),(-3,4),(5,-1),(5,4))]
    low=[min(p[a] for p in vertices) for a in (0,1)]
    high=[max(p[a] for p in vertices) for a in (0,1)]
    return [max(0,min(319,low[0]//40-1)),max(0,min(239,low[1]//40-1)),
            max(0,min(319,(high[0]+39)//40+1)),max(0,min(239,(high[1]+39)//40+1))]


def oracle(case):
    strong,weak,quad,owner=case['strong'],case['weak'],case['quad'],case['owner']
    roi=region(quad); sx=max(x for x,y in quad)-min(x for x,y in quad); sy=max(y for x,y in quad)-min(y for x,y in quad)
    def common(points):
        b=bounds(points); w=b[2]-b[0]+1; h=b[3]-b[1]+1
        return (b[0]>roi[0] and b[1]>roi[1] and b[2]<roi[2] and b[3]<roi[3] and len(points)>=3 and
                w*100<=sx*11 and h*100<=sy*11 and len(points)*200<=sx*sy and
                2*owner[0]<=b[0]+b[2]<=2*owner[2] and 2*owner[1]<=b[1]+b[3]<=2*owner[3])
    groups=components(weak if case['mode'] else strong,roi)
    seeds=[]; valid=[]; seed=case['seed']; x0,y0,x1,y1,count=seed
    seedPoints={(x,y) for x in range(x0,x1+1) for y in range(y0,y1+1)}
    for group in groups:
        b=bounds(group); w=b[2]-b[0]+1; h=b[3]-b[1]+1
        if common(group) and ((w==1) != (h==1)): seeds.append(group)
        strongPoints={p for p in group if strong[p[1],p[0]]}
        if common(group) and w>=2 and h>=2 and (not case['mode'] or (bool(strongPoints&seedPoints) and not(strongPoints-seedPoints))):
            valid.append(group)
    overflow=case.get('overflow',False); ambiguous=len(valid)>1
    accepted=not overflow and len(valid)==1
    if case['mode']:
        descriptor=(x0<=x1<320 and y0<=y1<240 and x0>=0 and y0>=0 and count>=3 and
                    ((x0==x1)!=(y0==y1)) and count==len(seedPoints) and common(seedPoints))
        allPresent=all(strong[y,x] for x,y in seedPoints) if descriptor else False
        planeMismatch=bool(np.any(strong[roi[1]:roi[3]+1,roi[0]:roi[2]+1]&~weak[roi[1]:roi[3]+1,roi[0]:roi[2]+1]))
        accepted=accepted and descriptor and allPresent and not planeMismatch
    anchor=[0,0,0]
    if accepted:
        b=bounds(valid[0]); anchor=[count if case['mode'] else len(valid[0]),b[2]-b[0]+1,b[3]-b[1]+1]
    thinCount=0 if case['mode'] else min(2,len(seeds)); hazard=not case['mode'] and (overflow or ambiguous)
    thin=[0,0,0,0,0]
    if thinCount==1 and not hazard: thin=bounds(seeds[0])+[len(seeds[0])]
    return dict(roi=roi,anchor=anchor,ambiguous=bool(ambiguous),overflow=bool(overflow),thinCount=thinCount,
                thin=thin,hazard=bool(hazard),support=bool(case['mode'] and accepted))


def syntheticCases():
    result=[]
    def add(name,strong,weak,quad,owner,seed,mode=1,**extra):
        result.append(dict(name=name,strong=strong.copy(),weak=weak.copy(),quad=quad,owner=owner,seed=seed,mode=mode,
                           inputSource='SYNTHETIC_COMPONENT_MASK',**extra))
    def rectangle(mask,b):
        x0,y0,x1,y1=b; mask[y0:y1+1,x0:x1+1]=True
    # Four image rotations, three geometrical scales, both thin dimensions.
    # These masks have no semantic digit field: the same rule sees every seed.
    for size in (30,60,100):
        baseQuad=[(100,60),(100+size,60),(100+size,60+size),(100,60+size)]
        for horizontal in (False,True):
            strong=np.zeros((240,320),bool); weak=strong.copy(); x=100+max(2,size//12); y=60+max(2,size//12)
            seed=[x,y,x+2 if horizontal else x,y if horizontal else y+2,3]
            rectangle(strong,seed[:4]); rectangle(weak,[x-1,y-1,seed[2]+1,seed[3]+1])
            # Width3,height5 must remain below relative limits for small cards.
            if size==30: weak=strong.copy(); rectangle(weak,[x,y,seed[2]+(not horizontal),seed[3]+horizontal])
            for rotation in range(4):
                def rotate(p):
                    px,py=p
                    for _ in range(rotation): px,py=280-py,px-40
                    return px,py
                def rotateMask(mask):
                    rotated=np.zeros_like(mask)
                    for py,px in zip(*np.where(mask)):
                        nx,ny=rotate((int(px),int(py))); rotated[ny,nx]=True
                    return rotated
                quad=[[2*a,2*b] for a,b in map(rotate,baseQuad)]; owner=bounds(list(map(rotate,baseQuad)))
                points=[rotate((px,py)) for py,px in zip(*np.where(strong))]; rotatedSeed=bounds(points)+[3]
                rs,rw=rotateMask(strong),rotateMask(weak)
                prefix=f'scale{size}_dimension{int(horizontal)}_rotation{rotation}'
                add(prefix+'_strict',rs,rw,quad,owner,rotatedSeed,0)
                add(prefix+'_support',rs,rw,quad,owner,rotatedSeed)
    quad=[[200,120],[400,120],[400,320],[200,320]];owner=[100,60,200,160];seed=[108,68,108,70,3]
    strong=np.zeros((240,320),bool);rectangle(strong,seed[:4]);weak=strong.copy();rectangle(weak,[107,68,109,70])
    add('base_strict',strong,weak,quad,owner,seed,0);add('base_support',strong,weak,quad,owner,seed)
    for name,which,pixel,value in [('missing_seed','strong',(108,69),False),('foreign_strong','strong',(109,69),True),
            ('strong_absent_from_weak','weak',(108,69),False)]:
        s,w=strong.copy(),weak.copy();(s if which=='strong' else w)[pixel[1],pixel[0]]=value
        add(name,s,w,quad,owner,seed)
    s,w=strong.copy(),weak.copy();rectangle(w,[107,54,107,70]);add('paper_bridge_to_roi_border',s,w,quad,owner,seed)
    s,w=strong.copy(),weak.copy();rectangle(w,[107,68,130,70]);add('oversize_weak_component',s,w,quad,owner,seed)
    add('no_weak_growth',strong,strong,quad,owner,seed)
    add('owner_excludes_seed',strong,weak,quad,[110,60,200,160],seed)
    for name,badSeed in [('bad_count',[108,68,108,70,4]),('not_thin',[107,68,108,69,4]),
            ('reversed',[109,68,108,70,3]),('out_of_image',[320,68,320,70,3]),('empty',[0,0,0,0,0])]:
        add(name,strong,weak,quad,owner,badSeed)
    s,w=strong.copy(),weak.copy();rectangle(s,[117,68,117,70]);rectangle(w,[116,68,118,70])
    add('two_thin_seeds_saturate',s,w,quad,owner,seed,0)
    # A foreign strong component only rejects when connected to the support.
    add('unconnected_foreign_strong',s,w,quad,owner,seed)
    rectangle(w,[109,69,116,69]);add('weak_bridge_foreign_component',s,w,quad,owner,seed)
    s=np.zeros_like(strong);w=s.copy()
    for x in range(88,106,2):rectangle(w,[x,58,x,61])
    rectangle(w,[107,68,109,70]);rectangle(s,seed[:4]);add('weak_capacity_nine_active',s,w,quad,owner,seed,overflow=True)
    add('strict_capacity_nine_active',w,w,quad,owner,seed,0,overflow=True)
    s=np.zeros_like(strong);rectangle(s,[108,68,109,69]);rectangle(s,[117,68,118,69]);add('strict_ambiguous_hazard',s,s,quad,owner,seed,0)
    return result


def recordedCases():
    # Use the authoritative preserved acquisition profile; do not retune it.
    from projective_reference import whiteProfileFor,whitePixelsFor,mainColourSupport,quadFromSupportPoints,homographyCoefficients
    from vision_reference import quantise565,colourMask
    fixture=ROOT/'tests/fixtures/camera/frame45625'; index=json.loads((fixture/'index.json').read_text()); path=fixture/'frame.png'
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest!=index['files']['frame.png']:raise ValueError('Recorded fixture hash mismatch')
    image=quantise565(Image.open(path).convert('RGB')); array=np.asarray(image,dtype=np.int16)
    profile=whiteProfileFor(8,index['whiteMinimum'],index['whiteMaxSpread'])
    strong=whitePixelsFor(array,profile,anchor=True);weak=whitePixelsFor(array,profile,anchor=False)
    owner=index['recordedFailure']['nativeBox']
    foreground=np.asarray(colourMask(image,index['redMinimum'],index['blueMinimum'],colourAlgorithm=index['colourAlgorithm'])).reshape(240,320)!=0
    support=mainColourSupport(foreground,owner)
    if not support['valid']:raise ValueError('Recorded colour support invalid')
    quad=quadFromSupportPoints(support['supportPoints']);result=[]
    for orientation in range(4):
        _,half=homographyCoefficients(quad[orientation:]+quad[:orientation],orientation,continuous=True)
        case=dict(name=f'recorded45625_orientation{orientation}_strict',mode=0,strong=strong,weak=weak,quad=half,
                  owner=owner,seed=[0,0,0,0,0],inputSource='RECORDED_CAMERA_PIXEL_MASK',pngSha256=digest)
        expectation=oracle(case);result.append(case)
        if expectation['thinCount']==1 and not expectation['hazard']:
            result.append(dict(case,name=f'recorded45625_orientation{orientation}_support',mode=1,seed=expectation['thin']))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True); records=[];words=[]
    for index,case in enumerate(syntheticCases()+recordedCases()):
        expected=oracle(case)
        row=[case['mode']]+[v for point in case['quad'] for v in point]+case['owner']+case['seed']+expected['anchor']+[
            expected['ambiguous'],expected['overflow'],expected['thinCount']]+expected['thin']+[expected['hazard'],expected['support']]+expected['roi']+[0]*5
        assert len(row)==40
        words.extend(row)
        for plane in ('strong','weak'):
            (args.out/f'support_{index}_{plane}.hex').write_text(''.join(f'{int(value):x}\n' for value in case[plane].flat),encoding='ascii')
        records.append({k:v for k,v in case.items() if k not in ('strong','weak')}|{'expected':expected,'index':index})
    (args.out/'support_meta.hex').write_text(''.join(f'{int(v)&0xffffffff:08x}\n' for v in words),encoding='ascii')
    (args.out/'support_count.hex').write_text(f'{len(records):08x}\n',encoding='ascii')
    record=dict(schema='NATIVE_ANCHOR_SUPPORT_1',recordWords=40,count=len(records),records=records,
                boundary='Independent BFS masks verify native scan only; full digit/caller priority uses separate reader9 RTL tests.')
    (args.out/'support_manifest.json').write_text(json.dumps(record,indent=2,default=lambda value:int(value))+'\n',encoding='utf8')
    print(json.dumps({'count':len(records),'acceptedSupport':sum(r['expected']['support'] for r in records),'output':str(args.out)}))


if __name__=='__main__':main()
