#!/usr/bin/env python3
"""Check the active repository layout/dependency closure, not FPGA behaviour."""
from pathlib import Path
import json,re,subprocess

root=Path(__file__).resolve().parents[1]
errors=[]
for oldName in ('ECHOPHACE1','alltest','Chassis + emergencystop',
                'Chassis + Robot Adaptor Board','V2026.3 Camera Code'):
    if (root/oldName).exists():errors.append(f'Obsolete project root remains: {oldName}')
projects=list((root/'quartus').glob('*.qpf'))
if [p.name for p in projects]!=['PartBDebug.qpf']:errors.append('Exactly one active Quartus project is required')
qsf=root/'quartus/PartBDebug.qsf'
sourceText=qsf.read_text(encoding='utf-8')
if 'TOP_LEVEL_ENTITY perceptionDemoTop' not in sourceText or 'DEVICE 5CSEMA5F31C6' not in sourceText:
    errors.append('Unexpected active top/device')
dependencies=[]
for kind,name in re.findall(r'^set_global_assignment -name (\w+_FILE) (.+)$',sourceText,re.M):
    dependency=(qsf.parent/name.strip().strip('"{}')).resolve()
    dependencies.append(dependency)
    if not dependency.is_relative_to(root) or not dependency.is_file():errors.append(f'Missing or external {kind}: {name}')
manifest=json.loads((root/'tests/rtl/manifest.json').read_text())
for test in manifest['tests']:
    for name in test['sources']:
        if not (root/name).is_file():errors.append(f'Missing {test["name"]} source: {name}')
for name in ('docs/MEMBER_C_INTERFACE.md','assets/markers/marker_spec.json',
             'assets/markers/scene_manifest.json','assets/markers/ECHO7_All_Markers_A4_v2.pdf'):
    if not (root/name).is_file():errors.append(f'Missing retained input: {name}')
readmes=sorted(p.name for p in root.glob('*README*.md'))
if readmes!=['README.md','VERSION_README.md']:errors.append('Use the main and version README pair')
for sample,expected in [('build/example.log',True),('quartus/db/generated.cdb',True),
                        ('assets/markers/sheet_320x240_rgb565.hex',False),
                        ('assets/markers/ECHO7_All_Markers_A4_v2.pdf',False)]:
    result=subprocess.run(['git','check-ignore','--no-index','--quiet',sample],cwd=root,timeout=10)
    if (result.returncode==0)!=expected:errors.append(f'Incorrect ignore rule for {sample}')
result={'level':'STRUCTURAL','status':'FAIL' if errors else 'PASS','activeProject':'PartBDebug',
        'projectDependencies':len(dependencies),'rtlBenches':len(manifest['tests']),'errors':errors,
        'limitation':'This check does not run RTL simulation, synthesis, timing or hardware.'}
print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
