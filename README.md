# MapleOS 🍁

**Arch roots. Maple personality. AI tools with explicit permissions.**

Version: **0.1.0-alpha.1, Core edition**. This checkout is an experimental source
and build project, **not a built, boot-tested, or published ISO**. Read
`BUILD-STATUS.json` for the work actually performed in the originating session.

MapleOS is a downstream Arch Linux distribution project. It keeps Arch's kernel,
package manager, rolling repositories and software ecosystem, while owning a
Maple desktop, live image, installable settings package and AI workbench.
It is not an independent kernel or an Arch package-repository fork.

## What is in this source bundle

The repository contains an ArchISO profile generator, an installable
`mapleos-core` package recipe, a Maple Hyprland/Fish/Foot desktop, an original
SDDM theme, an offline welcome page, a standard-library AI CLI, a rootless
agent launcher, an installation finalizer, real QEMU BIOS/UEFI boot tests,
GitHub Actions workflows, release checksums/multipart handling and QA gates.

Four Momiji inputs are pinned to commit
`654d2ddf4c45dd40afece7a52b4b93f4e7445d63`: Maple wallpaper, Maple ASCII,
and the two Caelestia Lua override files. They are fetched at build time,
not copied from any local home directory. The Caelestia snippets are staged
as integration references, **not enabled as a full Caelestia desktop**.

This first candidate uses official-repository Hyprland + Waybar so that
unreviewed AUR dependencies do not silently run as root. Exact Momiji/Caelestia
parity is a documented follow-on gate, not a feature falsely marked complete.
No proprietary apps, provider accounts, API keys or model weights are bundled.

## Start on Momiji: cloud build

Review the source, then from the extracted directory:

```fish
sudo pacman -Syu --needed github-cli git python
# Only needed when gh is not already authenticated:
gh auth login
fish scripts/cloud-build.fish NoahWLono/mapleos
```

The script creates a **public source repository** when no origin exists,
pushes the source, dispatches the supplied workflow, waits for its result,
and downloads the candidate **only after the build and both boot tests pass**.
It uses the local GitHub login; no token is included or requested in chat.
This cloud route necessarily creates the source repository before building.
For an ISO-before-repository route, use the local build below instead.
It does not alter Momiji's rice, partition a disk, or publish a release.

Actions availability, billing limits and permissions are those of your account.
No paid runner, hosting account, domain purchase or subscription is configured.
If a build fails, the script stops and preserves diagnostic logs. This source
has not yet run on an Arch builder, so first-build fixes may be necessary.

## Local build in an Arch VM

Use a disposable x86_64 Arch VM with a working network, approximately 8 GiB RAM
and at least 30 GiB free build storage. These are planning allowances, not a
measured requirement. Run as a regular user:

```sh
sudo pacman -Syu --needed archiso base-devel git python sudo shellcheck fish lua qemu-system-x86 edk2-ovmf
bash scripts/build.sh
python3 tools/boot_test.py out/mapleos-0.1.0-alpha.1-x86_64.iso --output out/BOOT-TESTS.json
```

The actual ISO filename is printed by the build. Official package names are
resolved before ISO construction; unavailable dependencies cause a hard failure.
No package is silently dropped. Arch package versions are captured, not pinned
to a historical mirror, so this is **not yet bit-for-bit reproducible**.

## AI-native, not AI-required

`maple doctor` shows tools. `maple ask` talks to an explicit local or remote
Chat Completions-compatible endpoint. `maple agent` runs commands or installed
agent CLIs in a digest-selected rootless container. Default policy is offline,
project-read-only, no host home and no ambient credentials. Model/provider
setup is optional and explicit. The base desktop remains usable without AI.

See [AI-NATIVE.md](docs/AI-NATIVE.md) for actual commands and limitations.
The launcher and API client are real code, not a claim that a full autonomous
OS agent or model is preinstalled.

## From candidate to a public download

Perform [QA.md](docs/QA.md) against the exact ISO and fill `qa.local.json`.
Then run the publisher from the same source tree that produced the image:

```sh
bash scripts/publish.sh out/downloaded/mapleos-0.1.0-alpha.1-x86_64.iso qa.local.json NoahWLono/mapleos
```

It verifies the ISO hash, both boot results, manual tests and source digest,
then publishes an explicitly marked **prerelease**, never stable v1.0.
See [HOSTING.md](docs/HOSTING.md) for signing and assets larger than GitHub's limit.
Do not change false QA flags to true without performing the corresponding tests.

## Validation

```sh
python3 tools/validate.py
PYTHONPATH=src python3 -m mapleos.cli doctor
```

Source checks are deliberately distinct from build, boot, graphical and install
testing. The local report names every unperformed category.

New code is MIT licensed. Upstream assets and packages retain separate rights.
Read `THIRD_PARTY.md` before any binary redistribution.
