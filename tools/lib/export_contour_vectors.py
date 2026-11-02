"""Independent floating HSV + image-neighbour oracle; synthetic display RGB."""
from pathlib import Path
import colorsys
import argparse
import json
import numpy as np

HERE = Path(__file__).resolve().parent
W, H = 640, 480


def writeVectors(output, records, expected, controls, info):
    """Use an exclusive namespace in the CLI's shared vector directory.

    In particular, expected.hex belongs to the connected-component bench.
    Overwriting it once broke a real combined regression before RTL ran.
    """
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, values in [('input', records), ('expected', expected), ('profile', controls)]:
        (output / f'contour_{name}.hex').write_text(''.join(f'{value:08x}\n' for value in values))
    (output / 'contour_vector_count.hex').write_text(f'{len(records):08x}\n')
    (output / 'contour_vectors.json').write_text(json.dumps({
        'source': 'SYNTHETIC_DISPLAY_RGB',
        'oracle': 'Python colorsys HSV + whole-image neighbours',
        'frames': info, 'totalPixels': len(records)}, indent=2) + '\n')


def palette(redFloor, blueFloor):
    colour = np.zeros(65536, dtype=np.uint8)
    pixels = np.empty(65536, dtype=np.uint32)
    for value in range(65536):
        red5, green6, blue5 = value >> 11, (value >> 5) & 63, value & 31
        r, g, b = (red5 << 3) | (red5 >> 2), (green6 << 2) | (green6 >> 4), (blue5 << 3) | (blue5 >> 2)
        hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        degrees = hue * 360
        if sat >= .5 and max(r, g, b) >= redFloor and r > g and r > b and (degrees >= 336 - 1e-9 or degrees <= 1e-9):
            colour[value] = 1
        elif sat >= .5 and max(r, g, b) >= blueFloor and b > r and b > g and 200 - 1e-9 <= degrees <= 250 + 1e-9:
            colour[value] = 2
        pixels[value] = (r << 22) | (g << 12) | (b << 2)
    return colour, pixels


def image(exhaustive=False):
    y, x = np.indices((H, W))
    picture = np.full((H, W), 0xffff, np.uint16)
    # Same-colour separated disks, a concave L, a ring/hole, a diagonal band,
    # one/two-pixel components, adjacent red->blue->background and all edges.
    picture[(x-70)**2+(y-70)**2 < 35**2] = 0xc000
    picture[(x-170)**2+(y-70)**2 < 35**2] = 0xc000
    picture[((x>260)&(x<290)&(y>30)&(y<150)) | ((x>260)&(x<370)&(y>120)&(y<150))] = 0x02b7
    dist=(x-460)**2+(y-90)**2
    picture[(dist<60**2)&(dist>35**2)] = 0x02b7
    picture[(x>40)&(x<260)&(abs(y-x-170)<7)] = 0xc000
    picture[(x>320)&(x<540)&(y>240)&(y<280)] = 0x02b7  # no digit/reference bar
    picture[180,10]=0xc000;picture[180,12:14]=0x02b7
    picture[190,10:13]=[0xc000,0x02b7,0xffff]
    picture[0,:20]=0xc000;picture[-1,-20:]=0x02b7
    picture[230:250,0]=0xc000;picture[230:250,-1]=0x02b7
    picture[330:380,350:450]=0xcb20  # orange must remain raw, without outlines
    if exhaustive:
        picture.ravel()[:65536]=np.arange(65536,dtype=np.uint16)
    return picture


def export(output):
    output.mkdir(parents=True, exist_ok=True)
    records=[];expected=[];controls=[];info=[]
    for index,(redFloor,blueFloor,count,exhaustive) in enumerate([
        (48,32,W*H,False),(64,80,W*H,True),(112,96,10000,False),(37,30,W*H,False)]):
        labels,pixels=palette(redFloor,blueFloor)
        pic=image(exhaustive);mask=labels[pic];raw=pixels[pic]
        left=np.zeros_like(mask);left[:,1:]=mask[:,:-1]
        above=np.zeros_like(mask);above[1:]=mask[:-1]
        h=mask!=left;v=mask!=above
        boundary=np.zeros_like(mask,dtype=bool);boundary[:,-1]=mask[:,-1]!=0;boundary[-1,:]=mask[-1,:]!=0
        edge=h|v|boundary
        selected=np.where(mask!=0,mask,np.where(h&(left!=0),left,above))
        rendered=raw.copy();rendered[edge&(selected==1)]=0x3ff00000;rendered[edge&(selected==2)]=0x3ff
        data=raw.ravel()[:count].astype(np.uint32).copy();gold=rendered.ravel()[:count].copy()
        data[0]|=1<<31;gold[0]|=1<<31;data[-1]|=1<<30;gold[-1]|=1<<30
        records.extend(data.tolist());expected.extend(gold.tolist())
        # Inputs change mid-frame; the DUT must retain the floors sampled at SOP.
        controls.extend([redFloor<<8|blueFloor]+[(255 if n%2 else 0)<<8 | (0 if n%2 else 255) for n in range(1,count)])
        info.append({'frame':index,'redMinimum':redFloor,'blueMinimum':blueFloor,'pixels':count,'exhaustiveRgb565':exhaustive})
    writeVectors(output, records, expected, controls, info)
    print(json.dumps({'totalPixels':len(records),'frames':len(info)}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    export(parser.parse_args().out)
