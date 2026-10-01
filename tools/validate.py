#!/usr/bin/env python3
"""Offline source checks. Passing does not imply a bootable or tested ISO."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
SKIP={'build','out','cache','.git','__pycache__','.venv','.pytest_cache'}
def main() -> int:
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in SKIP for x in p.relative_to(ROOT).parts)]
    bash=[]; fish=[]; lua=[]
    for path in files:
        if path.suffix in ('.json','.jsonc'):
            json.loads(path.read_text())
        if path.suffix=='.py' or path.name in ('maple','maple-finish-install'):
            ast.parse(path.read_text(),filename=str(path))
        head=path.read_bytes()[:100]
        if path.suffix=='.sh' or head.startswith(b'#!/usr/bin/env bash') or path.suffix=='.install': bash.append(path)
        if path.suffix=='.fish': fish.append(path)
        if path.suffix=='.lua': lua.append(path)
        if path.relative_to(ROOT).parts[0] in ('overlay','live','src'):
            if re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',path.read_bytes()):
                raise ValueError('Private-key material in runtime tree: '+str(path))
    lock=json.loads((ROOT/'sources.lock.json').read_text())
    assert re.fullmatch(r'[a-f0-9]{40}',lock['momiji']['commit'])
    assert len(lock['import_allowlist'])==4
    for source,target in lock['import_allowlist'].items():
        assert not Path(source).is_absolute() and '..' not in Path(source).parts
        assert target.startswith('usr/share/') and '..' not in Path(target).parts
    package_lines=[x.split('#',1)[0].strip() for x in (ROOT/'packages/core.txt').read_text().splitlines()]
    package_lines=[x for x in package_lines if x]
    assert len(package_lines)==len(set(package_lines)), 'Duplicate packages'
    assert all(re.fullmatch('[a-z0-9@+_.-]+',x) for x in package_lines)
    for path in bash: subprocess.run(['bash','-n',str(path)],check=True)
    for tool,paths,flags in [('shellcheck',bash,['--shell=bash']),('fish',fish,['-n']),('luac',lua,['-p'])]:
        if shutil.which(tool):
            for path in paths: subprocess.run([tool,*flags,str(path)],check=True)
        else: print('SKIP unavailable optional linter: '+tool,flush=True)
    subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,check=True)
    print(f'PASS: source syntax/structure and unit tests ({len(files)} files inspected).',flush=True)
    print('NOT tested here: package resolution, mkarchiso, BIOS/UEFI, graphical session, disk installation, rootless container runtime.')
    return 0
if __name__=='__main__': raise SystemExit(main())
