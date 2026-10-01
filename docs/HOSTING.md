# Publishing and hosting

Keep source in Git; put large binaries in **GitHub Releases**, not normal Git
commits. The source bundle supplies an Actions build with seven-day artifacts,
which are temporary development outputs, not the permanent public download.

GitHub's releases documentation specifies that each asset must be under 2 GiB.
`tools/release_assets.py` exports a direct ISO below that limit. Larger images
are split into 1800 MiB pieces with per-part and full-image hashes plus a
standalone `reassemble.py`. The reassembler validates names, parts, sizes and
the final hash and refuses to overwrite an existing output.

For a single-click download of a larger ISO, move the binary to deliberately
selected object storage or a mirror later. No paid hosting, DNS, domain or cloud
account has been created. GitHub Pages could host a landing page, but it is not
used here as an ISO distribution service.

Publication requires the same source tree used for the build, actual BIOS and
UEFI results, and a manually completed QA record for the exact image.
`scripts/publish.sh` uploads an explicit GitHub **prerelease**. It never
force-pushes or publishes stable v1.0.

SHA256 checksums detect corruption. An attacker able to replace both an ISO and
its checksums can still fool that check. Supply `MAPLE_SIGNING_KEY` with a key
already controlled on your own machine to create a detached GPG signature over
SHA256SUMS. Keep the private key out of the repo, image, CI logs and chat. Publish
and independently communicate the verified key fingerprint; downloading a
public key beside a compromised ISO is not by itself proof of identity.
Without that key the publisher labels the candidate unsigned. Secure Boot
signing and a signed pacman update repository are separate future work.

References:
https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github

## Create the repository after a local build

The cloud helper creates the source repository before the build. For a local
ISO-first route, finish building and testing, then create the source repository:

```sh
git init -b main
git add .
git commit -m "MapleOS Core alpha source"
gh repo create NoahWLono/mapleos --public --source . --remote origin --push
```

The build output, cache, QA-local file and private-key filenames are ignored by
Git. Review `git status` and the staged changes before committing; filename
filters and pattern checks do not prove that every possible secret is absent.
Then use the documented publisher with the exact ISO and completed QA record.
