#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
REQUIRED=('graphical_login','terminal_and_keybinds','network_and_audio','installed_system_reboot',
          'unique_installed_credentials','agent_readonly_and_network_isolation','redistribution_review')

def check(iso: Path, build: dict, boots: dict, qa: dict) -> list[str]:
    errors=[]
    with iso.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    for name,value in [('build',build.get('iso',{}).get('sha256')),('boots',boots.get('iso_sha256')),('qa',qa.get('iso_sha256'))]:
        if value!=digest: errors.append(f'{name} evidence is not bound to this ISO hash')
    modes={r.get('mode'):r.get('passed') for r in boots.get('results',[])}
    if any(modes.get(m) is not True for m in ('bios','uefi')): errors.append('Both real BIOS and UEFI boot checks must pass')
    if not qa.get('reviewer') or not qa.get('reviewed_utc'): errors.append('Named, dated QA review is required')
    for name in REQUIRED:
        if qa.get('checks',{}).get(name) is not True: errors.append('Missing manual QA: '+name)
    if qa.get('source_tree_sha256')!=build.get('source_tree_sha256'): errors.append('QA does not identify the built source tree')
    return errors

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('iso',type=Path); p.add_argument('qa',type=Path); a=p.parse_args()
    build=json.loads((a.iso.parent/'BUILD-MANIFEST.json').read_text()); boots=json.loads((a.iso.parent/'BOOT-TESTS.json').read_text())
    errors=check(a.iso,build,boots,json.loads(a.qa.read_text()))
    if errors:
        print('\n'.join('BLOCKED: '+e for e in errors),file=sys.stderr); return 1
    print('Release gate passed for this ISO. This remains an unsigned alpha unless you sign the checksums.'); return 0
if __name__=='__main__': raise SystemExit(main())
