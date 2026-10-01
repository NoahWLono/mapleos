#!/usr/bin/env fish
# Public source upload + synchronous GitHub Actions build. No token is embedded.
# Does not publish a release or install/erase anything on your machine.
function fail
    echo "MapleOS: $argv" >&2
    exit 1
end
set -l root (path resolve (path dirname (status filename))/..)
cd "$root"; or fail 'Cannot enter the source directory.'
for tool in gh git python3
    command -q $tool; or fail "Missing $tool. Install github-cli, git and python first."
end
python3 tools/validate.py; or fail 'Source validation failed.'
gh auth status; or fail 'Run gh auth login on your own machine; do not paste a token into chat.'
set -l repo NoahWLono/mapleos
if test (count $argv) -gt 0
    set repo $argv[1]
end
string match -rq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' -- "$repo"; or fail 'Use owner/repository.'
if not test -d .git
    git init -b main; or fail 'Git initialization failed.'
    git add .; or fail 'Git staging failed.'
    git -c user.name='MapleOS contributors' -c user.email='mapleos@users.noreply.github.com' commit -m 'MapleOS Core alpha: Arch ISO recipe and AI workbench'; or fail 'Git commit failed.'
end
if not git diff --quiet; or not git diff --cached --quiet
    fail 'Commit your source changes before building so the build has a precise revision.'
end
if not git remote get-url origin >/dev/null 2>&1
    echo "Creating PUBLIC source repository $repo. No credentials or local home files are included."
    gh repo create "$repo" --public --source . --remote origin --push --description 'Experimental Arch-based MapleOS desktop and permission-scoped AI workbench'; or fail 'Repository creation/push failed. Nothing was force-pushed.'
else
    set -l remote (git remote get-url origin)
    contains -- "$remote" "https://github.com/$repo.git" "https://github.com/$repo" "git@github.com:$repo.git"; or fail 'Existing origin does not match the requested repository.'
    git push -u origin main; or fail 'Push failed; no force-push was attempted.'
end
set -l sha (git rev-parse HEAD)
# Actions may take a moment to index a new workflow after the first push.
set -l launched 0
for attempt in (seq 1 12)
    if gh workflow run build.yml --repo "$repo" --ref main
        set launched 1
        break
    end
    sleep 5
end
test "$launched" = 1; or fail 'Workflow could not be dispatched. Source repository was created; no ISO has been built.'
set -l run_id ''
for attempt in (seq 1 30)
    set run_id (gh run list --repo "$repo" --workflow build.yml --commit "$sha" --event workflow_dispatch --limit 1 --json databaseId --jq '.[0].databaseId // empty')
    if test -n "$run_id"
        break
    end
    sleep 3
end
test -n "$run_id"; or fail 'No workflow run was found; inspect the Actions tab.'
gh run watch "$run_id" --repo "$repo" --exit-status; or fail 'Build or boot test failed. Inspect the build logs; no release was published.'
if test -e out/downloaded
    fail 'out/downloaded already exists; keep or move it before downloading this candidate.'
end
gh run download "$run_id" --repo "$repo" --name mapleos-candidate --dir out/downloaded; or fail 'Artifact download failed.'
echo 'Candidate and build evidence downloaded to out/downloaded.'
echo 'No public ISO release has been created. Follow docs/QA.md, then scripts/publish.sh.'
