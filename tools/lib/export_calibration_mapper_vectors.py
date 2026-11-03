"""Export signed calibration mapper tests using an independent Fraction DLT.

The oracle solves eight linear equations, rather than copying the RTL's common
denominator coefficient construction. Recorded quad inputs are geometry test
inputs, never runtime sign answers. No ignored build artifact is required.
"""
from fractions import Fraction as F
from pathlib import Path
import argparse,hashlib,json,random
RECORD_WORDS=60
def solve(matrix,rhs):
    a=[[F(x)for x in row]+[F(y)]for row,y in zip(matrix,rhs)]
    for col in range(len(a)):
        pivot=next((i for i in range(col,len(a)) if a[i][col]),None)
        if pivot is None:raise ValueError('singular')
        a[col],a[pivot]=a[pivot],a[col]
        scale=a[col][col];a[col]=[x/scale for x in a[col]]
        for i in range(len(a)):
            if i!=col:
                scale=a[i][col];a[i]=[x-scale*y for x,y in zip(a[i],a[col])]
    return [r[-1] for r in a]
def verdict(quad,samples,count,requireInImage=0xfff):
    if not 1<=count<=12:return 1,[]
    if any(not(-1<=x<=639 and -1<=y<=479)for x,y in quad):return 2,[]
    edges=[(quad[(i+1)%4][0]-quad[i][0],quad[(i+1)%4][1]-quad[i][1])for i in range(4)]
    if any(edges[i][0]*edges[(i+1)%4][1]-edges[i][1]*edges[(i+1)%4][0]<=0 for i in range(4)):return 3,[]
    matrix=[];rhs=[]
    for (u,v),(x,y)in zip(((0,0),(1,0),(1,1),(0,1)),quad):
        matrix.extend(((u,v,1,0,0,0,-u*x,-v*x),(0,0,0,u,v,1,-u*y,-v*y)));rhs.extend((x,y))
    try:h=solve(matrix,rhs)+[F(1)]
    except ValueError:return 4,[]
    mapped=[]
    for index,(a,b) in enumerate(samples[:count]):
        u,v=F(a,320),F(b,320);den=h[6]*u+h[7]*v+h[8]
        if den<=0:return 5,[]
        x=(h[0]*u+h[1]*v+h[2])*8/den;y=(h[3]*u+h[4]*v+h[5])*8/den
        x=x.numerator//x.denominator;y=y.numerator//y.denominator
        if not(-32768<=x<=32767 and -32768<=y<=32767):return 7,[]
        if (requireInImage>>index)&1 and not(0<=x<5120 and 0<=y<3840):return 6,[]
        mapped.append((x,y))
    return 0,mapped
def add(cases,name,quad,samples,count=None,requireInImage=0xfff):
    count=len(samples)if count is None else count
    samples=(samples+[(0,0)]*12)[:12]
    reason,expected=verdict(quad,samples,count,requireInImage)
    cases.append(dict(name=name,quad=quad,samples=samples,count=count,requireInImage=requireInImage,valid=reason==0,reason=reason,expected=expected))

def buildCases():
    cases=[]
    def case(*args,**kwargs):add(cases,*args,**kwargs)
    roi=[(26,96),(58,96),(58,224),(26,224),(0,334),(320,334),(320,398),(0,398),(64,64),(256,64),(256,256),(64,256)]
    base=[(40,40),(240,40),(240,240),(40,240)]
    case('translated_square',base,roi)
    for rotation in range(4):case(f'quarter_turn_{rotation}',base[rotation:]+base[:rotation],roi)
    case('one_half_pixel_quad',[(200,200),(201,200),(201,201),(200,201)],[(1,1),(319,319),(0,0),(320,320)])
    edgeQuad=[(-1,-1),(639,-1),(639,479),(-1,479)]
    case('native_extreme_edges_inset',edgeQuad,[(1,1),(319,1),(319,319),(1,319)])
    case('native_edge_outside_required',edgeQuad,[(160,160),(0,0)])
    case('native_edge_guards_permitted',edgeQuad,[(0,0),(320,320),(-32,360),(352,360)],requireInImage=0)
    case('mixed_guard_roi_mask',edgeQuad,[(160,160),(-32,360),(352,360),(1,1)],requireInImage=0b1001)
    case('red1_frame15078',[(247,1),(353,33),(343,175),(233,153)],roi)
    # Real frame15078 raw-domain quad [[116,81],[168,91],[170,103],[116,96]],
    # expanded by half a pixel in the same native quadrants as the reader.
    # Input origin: tests/fixtures/camera/frame15078/frame.png, SHA256 below.
    case('blue_strip_frame15078',[(231,161),(337,181),(341,207),(231,193)],[(64,64),(256,64),(256,256),(64,256)])
    for count in (0,13,15):case(f'invalid_count_{count}',base,roi,count)
    for corner in range(4):
        q=list(base);q[corner]=(-2,q[corner][1]);case(f'input_negative_{corner}',q,roi)
        q=list(base);q[corner]=(640,q[corner][1]);case(f'input_right_{corner}',q,roi)
        q=list(base);q[corner]=(q[corner][0],480);case(f'input_bottom_{corner}',q,roi)
    for name,quad in [('collinear',[(20,20),(40,20),(60,20),(80,20)]),('bowtie',[base[i]for i in (0,2,1,3)]),('reversed',base[::-1]),('duplicate',[base[i]for i in (0,1,1,3)])]:case(name,quad,roi)
    case('outside_at_last_point',base,[(160,160),(1023,1023)])
    case('negative_denominator',[(200,100),(240,100),(360,300),(80,300)],[(160,160),(160,1023)],requireInImage=0)
    case('negative_fraction_floor',[(20,20),(221,20),(221,220),(20,220)],[(-33,0),(-34,0),(0,-33)],requireInImage=0)
    case('signed_UV_minimum',base,[(-1024,-1024),(1023,1023)],requireInImage=0)
    # Exact signed16 boundary values, constructed by independent rational
    # search over convex trapezoids. Values outside signed16 must reject even
    # for guards that have requireInImage=0.
    for target,parameters in ((-32769,(182,535,456,338,-695)),(-32768,(151,583,300,218,-620)),
                              (32768,(10,536,230,338,786)),(32767,(260,525,106,264,511))):
        x0,x1,leftHeight,rightHeight,u=parameters
        q=[(x0,0),(x1,0),(x1,rightHeight),(x0,leftHeight)]
        case(f'signed16_boundary_{target}',q,[(u,0)],requireInImage=0)
    rng=random.Random(3700)
    for index in range(384):
        x0=rng.randrange(5,220);y0=rng.randrange(5,160);w=rng.randrange(12,150);h=rng.randrange(12,140)
        quad=[(x0+rng.randrange(-4,5),y0+rng.randrange(-4,5)),(x0+w+rng.randrange(-4,5),y0+rng.randrange(-4,5)),
              (x0+w+rng.randrange(-4,5),y0+h+rng.randrange(-4,5)),(x0+rng.randrange(-4,5),y0+h+rng.randrange(-4,5))]
        rotation=index%4;quad=quad[rotation:]+quad[:rotation]
        samples=[(rng.randrange(-1024 if index%7==0 else 0,1024 if index%3==0 else 321),
                  rng.randrange(-1024 if index%11==0 else 0,1024 if index%5==0 else 440))for _ in range(12)]
        case(f'random_projective_{index}',quad,samples,requireInImage=0 if index%7==0 else 0xfff)
    for width,height in ((2,2),(4,8),(16,120),(200,8),(600,460)):
        q=[(4,4),(4+width,4),(4+width,4+height),(4,4+height)]
        case(f'extent_{width}_{height}',q,[(0,0),(320,0),(320,320),(0,320),(1023,0),(0,1023)])
    return cases

def export(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);cases=buildCases();words=[]
    for case in cases:
        expected=(case['expected']+[(0,0)]*12)[:12]
        words.extend([case['count'],int(case['valid']),case['reason'],case['requireInImage']]+[v for p in case['quad']for v in p]+[p[0]for p in case['samples']]+[p[1]for p in case['samples']]+[p[0]for p in expected]+[p[1]for p in expected])
    assert len(words)==RECORD_WORDS*len(cases)
    (out/'calibration_mapper_count.hex').write_text(f'{len(cases):08x}\n')
    vectorPath=out/'calibration_mapper_vectors.hex';vectorPath.write_text(''.join(f'{v&0xffffffff:08x}\n'for v in words))
    summary={'schema':'CALIBRATION_MAPPER_VECTORS_2','recordWords':RECORD_WORDS,
        'oracle':'Exact Fraction eight-equation DLT, independent of DUT coefficient formula',
        'rounding':'floor signed native Q4; requireInImage is an independent per-point mask',
        'recordedInput':{'path':'tests/fixtures/camera/frame15078/frame.png','sha256':'23a288f2f07c645eee27703d4980f1b0ad9c4feced0b80b57e83db3abed1fb39','use':'Only measured geometric corners; no runtime identities or expected results'},
        'cases':cases,'count':len(cases),'reasonCounts':{str(reason):sum(c['reason']==reason for c in cases)for reason in range(8)},
        'vectorsSha256':hashlib.sha256(vectorPath.read_bytes()).hexdigest()}
    (out/'calibration_mapper_vectors.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);args=parser.parse_args()
    summary=export(args.out)
    print(json.dumps({key:summary[key]for key in ('schema','count','reasonCounts','vectorsSha256')}))
if __name__=='__main__':main()
