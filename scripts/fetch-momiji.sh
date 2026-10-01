#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readarray -t lock < <(python3 -c 'import json,sys; x=json.load(open(sys.argv[1]))["momiji"]; print(x["url"]); print(x["commit"])' "$root/sources.lock.json")
repo="$root/cache/momiji"
mkdir -p "$root/cache"
if [[ ! -d "$repo/.git" ]]; then git init "$repo" >/dev/null; fi
# A public source pin is sufficient. No key, credential file or SSH agent is read.
GIT_TERMINAL_PROMPT=0 git -C "$repo" -c credential.helper= fetch --depth=1 "${lock[0]}" "${lock[1]}"
git -C "$repo" checkout --detach "${lock[1]}"
[[ $(git -C "$repo" rev-parse HEAD) == "${lock[1]}" ]]
printf 'Pinned Momiji source: %s\n' "${lock[1]}"
