#!/usr/bin/env bash
# ONLY inside an explicitly disposable privileged build container.
set -euo pipefail
[[ $(id -u) == 0 && ( -e /run/.containerenv || -e /.dockerenv ) ]] || { echo 'This entrypoint is only for the disposable CI container.' >&2; exit 1; }
pacman -Syu --noconfirm --needed archiso base-devel git python sudo shellcheck fish lua qemu-system-x86 edk2-ovmf
useradd --create-home --uid 1000 builder
# This exception is inside the temporary builder, never included in the ISO.
printf 'builder ALL=(ALL) NOPASSWD: ALL\n' >/etc/sudoers.d/mapleos-ci-builder
chmod 440 /etc/sudoers.d/mapleos-ci-builder
chown -R builder:builder /workspace
sudo -u builder bash -c 'cd /workspace && bash scripts/build.sh'
iso=$(find /workspace/out -maxdepth 1 -name '*.iso' -print -quit)
python /workspace/tools/boot_test.py "$iso" --output /workspace/out/BOOT-TESTS.json
