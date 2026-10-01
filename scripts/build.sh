#!/usr/bin/env bash
# Run as a regular user on a disposable, up-to-date Arch build host.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
[[ $(id -u) != 0 ]] || { echo 'Run as a regular build user; mkarchiso alone is elevated.' >&2; exit 1; }
[[ "$root" != *[[:space:]]* && "$root" != *,* ]] || { echo 'Build directory must not contain spaces or commas.' >&2; exit 1; }
[[ $(uname -m) == x86_64 ]] || { echo 'This alpha targets x86_64 only.' >&2; exit 1; }
for cmd in pacman makepkg mkarchiso repo-add python3 git sudo; do command -v "$cmd" >/dev/null || { echo "Missing build dependency: $cmd" >&2; exit 1; }; done
[[ ! -e build/package && ! -e build/profile ]] || { echo 'Existing build/profile or build/package: archive or remove the previous build first.' >&2; exit 1; }
python3 tools/validate.py
bash scripts/fetch-momiji.sh
mkdir -p build/localrepo out
python3 tools/stage.py cache/momiji build/package
# Resolve every requested official dependency before the expensive build.
mapfile -t packages < <(python3 -c 'import sys; sys.path.insert(0,"tools"); from stage import packages; print("\n".join(packages()))')
pacman -Si -- "${packages[@]}" >/dev/null
(cd build/package && makepkg --nodeps --noconfirm)
mapfile -t built < <(cd build/package && makepkg --packagelist)
[[ ${#built[@]} == 1 && -f "${built[0]}" ]] || { echo 'Expected exactly one built MapleOS package.' >&2; exit 1; }
package="$root/build/localrepo/$(basename -- "${built[0]}")"
cp -- "${built[0]}" "$package"
repo-add "$root/build/localrepo/mapleos-build.db.tar.gz" "$package"
python3 tools/make_profile.py build/profile build/localrepo "$package"
work=$(mktemp -d "$root/build/archiso.XXXXXXXX")
printf 'ArchISO work directory: %s\n' "$work"
sudo mkarchiso -v -w "$work" -o "$root/out" "$root/build/profile" 2>&1 | tee build/mkarchiso.log
mapfile -t isos < <(find "$root/out" -maxdepth 1 -name '*.iso' -type f)
[[ ${#isos[@]} == 1 ]] || { echo 'Expected one ISO in out/.' >&2; exit 1; }
sudo chown "$(id -u):$(id -g)" "${isos[0]}"
sudo pacman --root "$work/x86_64/airootfs" -Q | tee out/packages.txt >/dev/null
cp "$package" out/
python3 tools/manifest.py "${isos[0]}" out/BUILD-MANIFEST.json
(cd out && sha256sum -- *.iso > SHA256SUMS)
printf '\nISO built, not yet boot-tested: %s\nNext: python3 tools/boot_test.py %q --output out/BOOT-TESTS.json\n' "${isos[0]}" "${isos[0]}"
