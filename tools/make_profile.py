#!/usr/bin/env python3
"""Derive a live profile from the INSTALLED ArchISO releng profile."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]

def make_profile(upstream: Path, dest: Path, localrepo: Path, package: Path) -> None:
    if dest.exists():
        raise ValueError('Profile already exists; refusing stale mixed output')
    text=(upstream/'profiledef.sh').read_text()
    match=re.search(r'^bootmodes=\((.*?)\)',text,re.M|re.S)
    if not match:
        raise ValueError('Unsupported ArchISO profile: cannot discover bootmodes')
    # Keep the upstream boot layout; fail instead of guessing a changed API.
    bootmodes=match.group(0)
    if 'bios.syslinux' not in bootmodes or 'uefi.systemd-boot' not in bootmodes:
        raise ValueError('Expected x86_64 BIOS and systemd-boot profile support')
    shutil.copytree(upstream,dest,symlinks=True)
    live=dest/'airootfs'
    # Drop upstream root autologin, networkd and SSH customizations, but retain
    # ArchISO writable Pacman keyring initialization. Archinstall/pacstrap requires
    # pacman-init.service and etc-pacman.d-gnupg.mount in the live environment.
    for relative in ["root", "etc/systemd/network", "etc/ssh/sshd_config.d"]:
        path=live/relative
        if path.exists(): shutil.rmtree(path)

    system=live/"etc/systemd/system"
    if system.exists():
        keep={"pacman-init.service", "etc-pacman.d-gnupg.mount"}
        for child in list(system.iterdir()):
            if child.name in keep:
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()

        wants=system/"multi-user.target.wants"
        wants.mkdir(parents=True, exist_ok=True)
        (wants/"pacman-init.service").symlink_to("../pacman-init.service")

    shutil.copytree(ROOT/"live", live, dirs_exist_ok=True)
    (live/"root").mkdir(exist_ok=True, mode=0o750)
    system=live/"etc/systemd/system"; system.mkdir(parents=True, exist_ok=True)
    links={
        'multi-user.target.wants/NetworkManager.service':'/usr/lib/systemd/system/NetworkManager.service',
        'multi-user.target.wants/systemd-resolved.service':'/usr/lib/systemd/system/systemd-resolved.service',
        'sysinit.target.wants/systemd-timesyncd.service':'/usr/lib/systemd/system/systemd-timesyncd.service',
        'multi-user.target.wants/mapleos-live-setup.service':'/etc/systemd/system/mapleos-live-setup.service',
        'multi-user.target.wants/mapleos-live-check.service':'/etc/systemd/system/mapleos-live-check.service',
        'display-manager.service':'/usr/lib/systemd/system/sddm.service',
        'default.target':'/usr/lib/systemd/system/graphical.target',
        'sshd.service':'/dev/null','sshd.socket':'/dev/null',
    }
    for relative, target in links.items():
        path=system/relative; path.parent.mkdir(parents=True,exist_ok=True); path.symlink_to(target)
    # No pre-baked machine identity, host SSH keys or live account home.
    (live/'etc/machine-id').write_text('')
    (live/'etc/passwd').write_text('root:x:0:0:root:/root:/usr/bin/bash\n')
    (live/'etc/shadow').write_text('root:!:14871::::::\n'); (live/'etc/shadow').chmod(0o400)
    (live/'etc/group').write_text('root:x:0:\nwheel:x:10:\n')
    (live/'etc/gshadow').write_text('root:!::\nwheel:!::\n'); (live/'etc/gshadow').chmod(0o400)
    # Preserve signed Arch package policy; unsigned policy applies ONLY to this
    # local directory containing packages just built from the tracked project.
    pacman=(dest/'pacman.conf').read_text()
    pacman += f'\n[mapleos-build]\nSigLevel = Optional TrustAll\nServer = file://{localrepo.resolve()}\n'
    (dest/'pacman.conf').write_text(pacman)
    with (dest/'packages.x86_64').open('a') as f: f.write('\nmapleos-core\narchinstall\n')
    packages_dir=live/'opt/mapleos-pkgs'; packages_dir.mkdir(parents=True)
    shutil.copy2(package,packages_dir/package.name)
    with package.open('rb') as f: package_sha=hashlib.file_digest(f,'sha256').hexdigest()
    (packages_dir/'checksums.json').write_text(json.dumps({package.name:package_sha})+'\n')
    version=(ROOT/'VERSION').read_text().strip()
    executables=[str('/'+p.relative_to(live).as_posix()) for p in live.rglob('*') if p.is_file() and not p.is_symlink() and p.stat().st_mode & 0o111]
    permissions='\n'.join(f'  ["{name}"]="0:0:755"' for name in sorted(executables))
    (dest/'profiledef.sh').write_text(f"""#!/usr/bin/env bash
# shellcheck disable=SC2034
iso_name="mapleos"
iso_label="MAPLE_001"
iso_publisher="MapleOS contributors"
iso_application="MapleOS Core Alpha Live ISO"
iso_version="{version}"
install_dir="maple"
arch="x86_64"
buildmodes=('iso')
{bootmodes}
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '15')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/etc/gshadow"]="0:0:400"
  ["/root"]="0:0:750"
{permissions}
)
""")
    # Change human-facing boot menu text only, not template boot variables.
    for sub in ('syslinux','efiboot','grub'):
        directory=dest/sub
        if not directory.exists(): continue
        for file in directory.rglob('*'):
            if file.is_file() and not file.is_symlink():
                try: original=file.read_text()
                except UnicodeDecodeError: continue
                file.write_text(original.replace('Arch Linux install medium','MapleOS Core Alpha live medium').replace('Arch Linux (','MapleOS ('))

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument('output',type=Path); p.add_argument('localrepo',type=Path); p.add_argument('package',type=Path)
    p.add_argument('--upstream',type=Path,default=Path('/usr/share/archiso/configs/releng'))
    a=p.parse_args(); make_profile(a.upstream,a.output,a.localrepo,a.package); return 0
if __name__=='__main__': raise SystemExit(main())
