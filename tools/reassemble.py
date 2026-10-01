#!/usr/bin/env python3
"""Run beside ISO-MANIFEST.json and all parts. No network access or shell calls."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import os

def name_only(value: str) -> str:
    if not isinstance(value,str) or Path(value).name != value or value in ('.','..','') or '\\' in value:
        raise ValueError('Unsafe filename in manifest')
    return value

def reassemble(root: Path) -> Path:
    data=json.loads((root/'ISO-MANIFEST.json').read_text())
    output=root/name_only(data['name'])
    parts=data['parts']
    if not parts or len(parts)>1000: raise ValueError('Invalid part count')
    seen=set()
    for part in parts:
        name=name_only(part['name'])
        if name in seen: raise ValueError('Duplicate part')
        seen.add(name)
        path=root/name
        if path.is_symlink() or not path.is_file(): raise ValueError('Part must be a regular file')
        with path.open('rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
        if actual!=part['sha256'] or path.stat().st_size!=part['bytes']: raise ValueError(f'Corrupt/missing part: {name}')
    if len(parts)==1 and parts[0]['name']==output.name:
        if parts[0]['sha256']!=data['sha256'] or parts[0]['bytes']!=data['bytes']: raise ValueError('Manifest hash/size mismatch')
        return output
    if output.exists() or output.is_symlink(): raise ValueError('Output already exists; refusing overwrite')
    temp=output.with_name(output.name+'.assembling')
    h=hashlib.sha256(); size=0; created=False
    try:
        with temp.open('xb') as dst:
            created=True
            for part in parts:
                with (root/part['name']).open('rb') as src:
                    for chunk in iter(lambda:src.read(8*1024*1024),b''):
                        dst.write(chunk); h.update(chunk); size+=len(chunk)
        if h.hexdigest()!=data['sha256'] or size!=data['bytes']:
            raise ValueError('Reassembled ISO failed verification')
        # link+unlink avoids replacing any file created while reassembly ran.
        os.link(temp,output); temp.unlink()
    except BaseException:
        if created and temp.is_file() and not temp.is_symlink(): temp.unlink()
        raise
    return output
if __name__=='__main__': print(reassemble(Path(__file__).resolve().parent))
