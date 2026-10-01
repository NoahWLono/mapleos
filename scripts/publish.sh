#!/usr/bin/env bash
# Publish only an actual built ISO with matching boot + manual QA evidence.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
[[ $# == 3 ]] || { echo "Usage: $0 path/to/mapleos.iso qa.local.json owner/repo" >&2; exit 2; }
iso=$(realpath -- "$1"); qa=$(realpath -- "$2"); repo=$3
[[ "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || { echo 'Invalid repository name' >&2; exit 2; }
python3 tools/validate.py
python3 tools/release_gate.py "$iso" "$qa"
# Bind the upload to exactly the sources that built the artifact.
python3 - "$iso" <<'PYCODE'
import json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from manifest import source_digest
m=json.loads((Path(sys.argv[1]).parent/'BUILD-MANIFEST.json').read_text())
if source_digest()!=m['source_tree_sha256']:
    raise SystemExit('Source tree differs from the built ISO. Restore the build revision before publishing.')
PYCODE
gh auth status
git rev-parse --is-inside-work-tree >/dev/null
[[ -z $(git status --porcelain) ]] || { echo 'Commit source changes first.' >&2; exit 1; }
version=$(cat VERSION)
[[ "$version" == *alpha* ]] || { echo 'This publisher is deliberately alpha-only.' >&2; exit 1; }
dest="$(dirname -- "$iso")/release"
python3 tools/release_assets.py "$iso" "$dest"
# Include review evidence, then generate sums without hashing the sums themselves.
cp -- "$qa" "$dest/QA.json"
if [[ -n ${MAPLE_SIGNING_KEY:-} ]]; then
    gpg --armor --export "$MAPLE_SIGNING_KEY" > "$dest/mapleos-signing-key.asc"
fi
python3 - "$dest" <<'PYCODE'
import hashlib,sys
from pathlib import Path
root=Path(sys.argv[1]); lines=[]
for p in sorted(root.iterdir()):
    if p.is_file() and p.name not in {'SHA256SUMS','SHA256SUMS.asc'}:
        with p.open('rb') as f: value=hashlib.file_digest(f,'sha256').hexdigest()
        lines.append(value+'  '+p.name)
(root/'SHA256SUMS').write_text('\n'.join(lines)+'\n')
PYCODE
if [[ -n ${MAPLE_SIGNING_KEY:-} ]]; then
    gpg --local-user "$MAPLE_SIGNING_KEY" --armor --detach-sign "$dest/SHA256SUMS"
else
    echo 'Publishing an UNSIGNED alpha. SHA256 is not an authenticity signature.' >&2
fi
# Existing repository must be the intended one. Creation normally happens in cloud-build.fish.
gh repo view "$repo" --json nameWithOwner >/dev/null
remote=$(git remote get-url origin)
[[ "$remote" == "https://github.com/$repo.git" || "$remote" == "https://github.com/$repo" || "$remote" == "git@github.com:$repo.git" ]] || { echo 'Origin does not match publication target.' >&2; exit 1; }
git push origin main
sha=$(git rev-parse HEAD)
gh release create "v$version" --repo "$repo" --target "$sha" --prerelease \
    --title "MapleOS $version · Core Alpha" --notes-file docs/RELEASE-NOTES.md -- "$dest"/*
