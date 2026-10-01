#!/usr/bin/env python3
"""Create GitHub-compatible release assets, with a verified multipart fallback."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
LIMIT=1800*1024*1024

def sha(path: Path) -> str:
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def export(iso: Path, out: Path, part_limit: int=LIMIT) -> dict:
    if out.exists(): raise ValueError('Release directory already exists; refusing stale mixed artifacts')
    out.mkdir(parents=True)
    result={'schema':1,'name':iso.name,'bytes':iso.stat().st_size,'sha256':sha(iso),'parts':[]}
    if iso.stat().st_size < 2*1024**3:
        dest=out/iso.name; shutil.copyfile(iso,dest)
        result['parts'].append({'name':dest.name,'sha256':sha(dest),'bytes':dest.stat().st_size})
    else:
        with iso.open('rb') as src:
            index=0
            while True:
                data=src.read(min(part_limit,8*1024*1024))
                if not data: break
                part=out/f'{iso.name}.part{index:03d}'
                remaining=part_limit-len(data)
                with part.open('wb') as dst:
                    dst.write(data)
                    while remaining:
                        chunk=src.read(min(remaining,8*1024*1024))
                        if not chunk: break
                        dst.write(chunk); remaining-=len(chunk)
                result['parts'].append({'name':part.name,'sha256':sha(part),'bytes':part.stat().st_size})
                index+=1
    (out/'ISO-MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    shutil.copy2(Path(__file__).with_name('reassemble.py'),out/'reassemble.py')
    for name in ('BUILD-MANIFEST.json','BOOT-TESTS.json','packages.txt'):
        if (iso.parent/name).is_file(): shutil.copy2(iso.parent/name,out/name)
    lines=[f'{sha(f)}  {f.name}' for f in sorted(out.iterdir()) if f.is_file()]
    (out/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('iso',type=Path); p.add_argument('output',type=Path); a=p.parse_args()
    export(a.iso,a.output)
