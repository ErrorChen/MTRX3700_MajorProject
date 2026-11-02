from pathlib import Path
import json,sys
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/lib'))
from audit_hsv import hsvMask,candidateReport,ROIS
from vision_reference import quantise565
inputs=[(frame,root/f'evidence/real_inputs/frame{frame}.png') for frame in (13139,13511,13675)]
inputs.append((25046,root/'evidence/hsv_audit/frame25046.png'))
results=[]
for upper in (0,1,2,-1,-2):
 for redMin in (32,40,48):
  rows=[]
  for frame,path in inputs:
   image=quantise565(Image.open(path).convert('RGB'));mask=hsvMask(image,redMin,32,upper)
   result=candidateReport(image,mask);oracle=result['oracle']
   fractions={}
   for name,(kind,(x0,y0,x1,y1)) in ROIS.items():
    fractions[name]=float(np.mean(mask[y0:y1+1,x0:x1+1]==(2 if kind=='blue' else 1)))
   row={'frameId':frame,'accepted':[(m['colour'],m['digit']) for m in result['accepted']],
        'overflow':oracle['overflow'],'redPeak':oracle['red_max_row_handles'],'bluePeak':oracle['blue_max_row_handles'],
        'redCount':len(oracle['red']),'blueCount':len(oracle['blue']),'roiFractions':fractions}
   rows.append(row)
  setting={'redHue':[-24,upper],'redValueMinimum':redMin,'blueHue':[200,250],'blueValueMinimum':32,'saturationMinimum':0.5,'frames':rows}
  results.append(setting)
  print(json.dumps({'upper':upper,'v':redMin,'frames':[(r['frameId'],len(r['accepted']),r['redPeak'],r['bluePeak'],r['overflow']) for r in rows]}),flush=True)
out=root/'build/member_b/hsv_audit_replay/hsv_profile_matrix.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'schema':'ECHO7_HSV_PROFILE_MATRIX_1','layer':'MODEL_DIAGNOSTIC_ONLY','runtimeChanged':False,'profiles':results},indent=2)+'\n',encoding='utf-8')
