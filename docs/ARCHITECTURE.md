# MapleOS architecture and maintenance boundary

The first milestone is an x86_64 Arch derivative, not a fork of Linux or pacman.
Arch supplies the bootable package base and security updates. MapleOS owns the
small `mapleos-core` package, desktop defaults, image build, workbench, onboarding,
installation integration, release evidence and future downstream update policy.

Build flow:

```
Pinned Momiji objects + MapleOS source
    -> allowlisted staging
    -> mapleos-core.pkg.tar.zst (unprivileged makepkg)
    -> local build-only package repository
    -> current ArchISO releng + live-only overlay
    -> mkarchiso (privileged, disposable builder)
    -> ISO + package inventory + hashes
    -> BIOS/UEFI QEMU boot
    -> human desktop/install/agent/license review
    -> optional signature + GitHub prerelease
```

The public live user is created only on live boot. Installed systems are built
by Archinstall and receive the same pacman-managed MapleOS package, not a clone
of a running live session. Personal dotfiles are never bulk-copied.

Official Arch repos retain upstream signature checks. The unsigned local repo
exception is only for MapleOS's own build output. It does not become a general
unsigned repository on installed systems. No AUR helper runs automatically.
No proprietary application binaries or model weights are redistributed here.

The pinned Momiji commit makes the selected assets stable. Rolling Arch package
resolution and a freshly resolved builder image mean rebuilds can still differ.
The build records a resolved container digest, package versions, source-tree
hash and ISO checksum. That is traceability, not bit-for-bit reproducibility.

Agent policy is enforced through rootless container flags, not an LLM prompt.
The independent API client requires explicit send consent and explicit files.
Model execution, provider tooling, credentials and model downloads remain user
choices. The privileged ISO builder is **not** the agent runtime and its temporary
sudo configuration is never part of the installed OS.

Future updates must supply signed `mapleos-core` packages or a signed repository.
The alpha relies on normal `pacman -Syu` for upstream Arch updates; it does not yet
provide an automatic MapleOS downstream updater, system rollback guarantees or
long-term hardware support. Never leave users believing a wallpaper project has
inherited the support obligations or QA coverage of a mature distribution.
