from pathlib import Path
import json,sys
import numpy as np
from PIL import Image
from unittest.mock import patch
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/lib'))
import audit_hsv
from vision_reference import quantise565

def twoDimensionalCleanup(mask):
 left=np.zeros_like(mask,dtype=bool);above=np.zeros_like(mask,dtype=bool)
 left[:,1:]=mask[:,1:]==mask[:,:-1];above[1:,:]=mask[1:,:]==mask[:-1,:]
 return np.where((mask!=0)&left&above,mask,0).astype(np.uint8)

def threeOfFourCleanup(mask):
 left=np.zeros_like(mask,dtype=bool);above=np.zeros_like(mask,dtype=bool);diagonal=np.zeros_like(mask,dtype=bool)
 left[:,1:]=mask[:,1:]==mask[:,:-1];above[1:,:]=mask[1:,:]==mask[:-1,:];diagonal[1:,1:]=mask[1:,1:]==mask[:-1,:-1]
 count=left.astype(np.uint8)+above.astype(np.uint8)+diagonal.astype(np.uint8)
 return np.where((mask!=0)&(count>=2),mask,0).astype(np.uint8)

inputs=[(frame,root/f'evidence/real_inputs/frame{frame}.png') for frame in (13139,13511,13675)]
inputs.append((25046,root/'evidence/hsv_audit/frame25046.png'))
results=[]
for filterName,filterFunction in [('AND_LEFT_ABOVE',twoDimensionalCleanup),('CURRENT_PLUS_TWO_OF_LEFT_ABOVE_DIAGONAL',threeOfFourCleanup)]:
 for redMin in (32,37,40,48):
  rows=[]
  for frame,path in inputs:
   image=quantise565(Image.open(path).convert('RGB'));mask=audit_hsv.hsvMask(image,redMin,32,0)
   with patch.object(audit_hsv,'cleanup',filterFunction):result=audit_hsv.candidateReport(image,mask)
   oracle=result['oracle']
   rows.append({'frameId':frame,'accepted':result['accepted'],'rejected':result['rejected'],
                'overflow':oracle['overflow'],'redPeak':oracle['red_max_row_handles'],'bluePeak':oracle['blue_max_row_handles'],
                'redCount':len(oracle['red']),'blueCount':len(oracle['blue']),'oracle':oracle})
  profile={'cleanup':filterName,'redHue':[-24,0],'redValueMinimum':redMin,'blueHue':[200,250],'blueValueMinimum':32,'saturationMinimum':0.5,'frames':rows}
  results.append(profile)
  print(json.dumps({'cleanup':filterName,'v':redMin,'frames':[(r['frameId'],len(r['accepted']),r['redPeak'],r['bluePeak'],r['overflow']) for r in rows]}),flush=True)
out=root/'build/member_b/hsv_audit_replay/hsv_cleanup_matrix.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'schema':'ECHO7_HSV_CLEANUP_MATRIX_1','layer':'MODEL_DIAGNOSTIC_ONLY','runtimeChanged':False,'profiles':results},indent=2)+'\n',encoding='utf-8')
