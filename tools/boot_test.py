#!/usr/bin/env python3
"""Real ISO boot in QEMU BIOS + UEFI. Does not claim desktop/installer validation."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
MARKER='MAPLEOS_LIVE_BOOT_OK:0.1.0-alpha.1'
def firmware() -> Path:
    override=os.environ.get('MAPLE_OVMF_CODE')
    choices=[Path(override)] if override else [Path(p) for p in (
        '/usr/share/edk2/x64/OVMF_CODE.4m.fd','/usr/share/edk2/x64/OVMF_CODE.fd',
        '/usr/share/OVMF/OVMF_CODE_4M.fd','/usr/share/OVMF/OVMF_CODE.fd')]
    for choice in choices:
        if choice.is_file(): return choice
    raise RuntimeError('OVMF firmware not found; install edk2-ovmf, or set MAPLE_OVMF_CODE.')
def run_boot(iso: Path, mode: str, log: Path, timeout: int) -> dict:
    qemu=shutil.which('qemu-system-x86_64')
    if not qemu: raise RuntimeError('qemu-system-x86_64 not installed')
    cmd=[qemu,'-accel','tcg','-m','4096','-smp','2','-boot','order=d','-cdrom',str(iso.resolve()),
         '-display','none','-device','virtio-vga','-nic','none','-serial','file:'+str(log),'-no-reboot','-monitor','none']
    if mode=='uefi': cmd+=['-bios',str(firmware())]
    log.write_text('')  # Never accept a stale marker from a previous run.
    with log.with_suffix('.qemu.log').open('w') as err:
        proc=subprocess.Popen(cmd,stdout=err,stderr=err)
        start=time.monotonic(); passed=False
        try:
            while time.monotonic()-start < timeout and proc.poll() is None:
                if log.exists() and MARKER in log.read_text(errors='replace'):
                    passed=True; break
                time.sleep(1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(timeout=10)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait()
    return {'mode':mode,'passed':passed,'elapsed_seconds':round(time.monotonic()-start,1),'serial_log':log.name,
            'scope':'bootloader, kernel, root filesystem, live account and command presence; NOT graphical login'}
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('iso',type=Path); p.add_argument('--output',type=Path,required=True); p.add_argument('--timeout',type=int,default=420)
    a=p.parse_args(); a.output.parent.mkdir(parents=True,exist_ok=True)
    if not a.iso.is_file(): p.error('ISO does not exist')
    with a.iso.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
    results=[]
    for mode in ('bios','uefi'):
        try: result=run_boot(a.iso,mode,a.output.parent/f'boot-{mode}.serial.log',a.timeout)
        except (RuntimeError,OSError) as exc: result={'mode':mode,'passed':False,'error':str(exc)}
        results.append(result); print(json.dumps(result),flush=True)
    a.output.write_text(json.dumps({'iso_sha256':sha,'results':results,'graphical_tested':False},indent=2)+'\n')
    return 0 if all(r['passed'] for r in results) else 1
if __name__=='__main__': raise SystemExit(main())
