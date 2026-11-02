#!/usr/bin/env python3
"""Index current files/runs without rewriting historical evidence.

Original provenance remains in evidence/metadata.json, with old paths explained
by relocation_index.json. This collector needs no removed demonstration trees.
"""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess

root=Path(__file__).resolve().parents[2]
out=root/'evidence'

def main():
    out.mkdir(parents=True,exist_ok=True)
    hashFile=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    sources={}
    for folder in ('rtl','quartus','tools','tests'):
        for path in sorted((root/folder).rglob('*')):
            if path.is_file() and path.suffix.lower() in ('.sv','.v','.svh','.qsf','.qpf','.sdc','.qsys','.py','.tcl','.json') and not any(p in ('db','incremental_db','output_files','__pycache__','vga_sink') for p in path.parts):
                sources[path.relative_to(root).as_posix()]=hashFile(path)
    runs=[]
    for path in sorted((root/'build/member_b').glob('*/result.json')):
        try:data=json.loads(path.read_text(encoding='utf-8'))
        except (ValueError,OSError):continue
        runs.append({'path':path.relative_to(root).as_posix(),'sha256':hashFile(path),
                     **{key:data.get(key) for key in ('command','status','level','startedUtc','inputSource')}})
    retained=[{'path':p.relative_to(root).as_posix(),'sha256':hashFile(p),'bytes':p.stat().st_size}
              for p in sorted(out.rglob('*')) if p.is_file() and p.name!='current_index.json']
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    record={'schema':'ECHO7_CURRENT_EVIDENCE_INDEX_2','collectedUtc':datetime.now(timezone.utc).isoformat(),
        'gitHead':head,'sourceFiles':sources,'runIndex':runs,'retainedEvidence':retained,
        'historicalProvenance':'metadata.json','pathRelocation':'relocation_index.json',
        'boundary':'An index is not validation. Use each run status, source hashes and layer. Old evidence is never promoted to current acceptance.'}
    (out/'current_index.json').write_text(json.dumps(record,indent=2)+chr(10),encoding='utf-8')
    print(json.dumps({'status':'PASS','action':'INDEX_ONLY','sourceFiles':len(sources),'runs':len(runs),'retainedFiles':len(retained)}))

if __name__=='__main__':main()
