#!/usr/bin/env python3
"""Create one installable MapleOS package payload from an allowlisted source pin."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def packages() -> list[str]:
    return sorted({line.split('#',1)[0].strip() for line in (ROOT/'packages/core.txt').read_text().splitlines()} - {''})

def tracked_bytes(repo: Path, commit: str, name: str) -> bytes:
    # Read the pinned Git object, not a possibly dirty working-tree file.
    if not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise ValueError('Invalid commit pin')
    parts = Path(name).parts
    if Path(name).is_absolute() or '..' in parts:
        raise ValueError('Unsafe source path')
    record = subprocess.check_output(['git','-C',str(repo),'ls-tree',commit,'--',name], text=True)
    if not record.startswith('100644 blob ') and not record.startswith('100755 blob '):
        raise ValueError(f'Only tracked regular files can be imported: {name}')
    raw = subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{name}'])
    if len(raw) > 25*1024*1024:
        raise ValueError('Oversized source asset')
    return raw

def stage(repo: Path, dest: Path) -> None:
    if dest.exists():
        raise ValueError('Payload output already exists; refusing to merge stale artifacts')
    lock = json.loads((ROOT/'sources.lock.json').read_text())
    pin = lock['momiji']['commit']
    actual = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'], text=True).strip()
    if actual != pin:
        raise ValueError(f'Momiji HEAD differs from pin {pin}')
    shutil.copytree(ROOT/'overlay',dest)
    shutil.copytree(ROOT/'src/mapleos',dest/'usr/lib/mapleos/mapleos',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    provenance = {'upstream':lock['momiji'],'assets':{}}
    for source, target in lock['import_allowlist'].items():
        target_path = Path(target)
        if target_path.is_absolute() or '..' in target_path.parts:
            raise ValueError('Unsafe destination path')
        content = tracked_bytes(repo,pin,source)
        if source.endswith('.png') and not content.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Wallpaper is not a PNG')
        path = dest/target_path; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(content)
        provenance['assets'][source] = {'target':target,'sha256':hashlib.sha256(content).hexdigest()}
    share = dest/'usr/share/mapleos'
    (share/'SOURCE-PROVENANCE.json').write_text(json.dumps(provenance,indent=2)+'\n')
    shutil.copytree(ROOT/'docs',share/'docs')
    shutil.copytree(ROOT/'containers',share/'containers')
    license_dir = dest/'usr/share/licenses/mapleos-core'; license_dir.mkdir(parents=True)
    for name in ['LICENSE','THIRD_PARTY.md']:
        shutil.copy2(ROOT/name,license_dir/name)
    (dest/'etc/sudoers.d/20-mapleos-wheel').chmod(0o440)

def write_pkgbuild(work: Path) -> None:
    version = (ROOT/'VERSION').read_text().strip().replace('-','_')
    deps = ' '.join("'"+name+"'" for name in packages())
    if any(not re.fullmatch(r'[a-z0-9@+_.-]+',p) for p in packages()):
        raise ValueError('Invalid package name')
    (work/'PKGBUILD').write_text(f"""# Generated from tracked MapleOS sources; no downloaded build scripts.
    pkgname=mapleos-core
    pkgver={version}
    pkgrel=1
    pkgdesc='MapleOS desktop and project-scoped AI workbench'
    arch=('any')
    url='https://github.com/NoahWLono/mapleos'
    license=('MIT' 'custom:MapleOS-assets')
    depends=({deps})
    install=mapleos-core.install
    options=('!strip')
    package() {{
        cp -a "$startdir/payload/." "$pkgdir/"
    }}
""")
    shutil.copy2(ROOT/'packaging/mapleos-core.install',work/'mapleos-core.install')

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument('repo',type=Path); parser.add_argument('work',type=Path)
    args=parser.parse_args(); args.work.mkdir(parents=True,exist_ok=False)
    stage(args.repo,args.work/'payload'); write_pkgbuild(args.work)
    return 0
if __name__=='__main__':
    raise SystemExit(main())
