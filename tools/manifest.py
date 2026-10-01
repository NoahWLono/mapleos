#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
SKIP={'.git','build','out','cache','__pycache__','.pytest_cache','.venv'}
def digest(path: Path) -> str:
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def source_digest() -> str:
    h=hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(part in SKIP for part in rel.parts) or p.suffix=='.pyc' or p.name=='qa.local.json': continue
        h.update(rel.as_posix().encode()+b'\0'+digest(p).encode()+b'\n')
    return h.hexdigest()
def main() -> int:
    iso=Path(sys.argv[1]); output=Path(sys.argv[2])
    try: commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True).strip()
    except subprocess.CalledProcessError: commit=None
    versions=subprocess.check_output(['pacman','-Q','archiso','pacman'],text=True).splitlines()
    result={'schema':1,'version':(ROOT/'VERSION').read_text().strip(),'created_utc':datetime.now(timezone.utc).isoformat(),
      'iso':{'name':iso.name,'bytes':iso.stat().st_size,'sha256':digest(iso)},'source_commit':commit,'source_tree_sha256':source_digest(),
      'sources':json.loads((ROOT/'sources.lock.json').read_text()),'builder_packages':versions,
      'reproducibility':'Source-pinned Momiji assets; rolling Arch packages. NOT bit-for-bit reproducible.',
      'tested':{'build':True,'bios_boot':False,'uefi_boot':False,'graphical_login':False,'installed_system':False,'agent_runtime':False},
      'signing':'unsigned candidate; SHA256 detects corruption, not publisher authenticity'}
    output.write_text(json.dumps(result,indent=2)+'\n'); return 0
if __name__=='__main__': raise SystemExit(main())
