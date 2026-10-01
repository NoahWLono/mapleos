# MapleOS source validation report

**Version:** 0.1.0-alpha.1, Core alpha  
**Session date:** October 1, 2026  
**Artifact:** Source bundle. No ISO was built, booted, signed or hosted.

## Checks actually performed

| Check | Result |
|---|---|
| Unit/regression tests | **61 passed** |
| Python source parsing | Passed |
| Bash script syntax (`bash -n`) | Passed |
| Workflow YAML parsing | Passed for both workflows; neither workflow ran |
| Local HTTP integration | Passed against a synthetic loopback server |
| API request consent | Verified: no request sent without explicit consent flag |
| Pinned Git object import | Tested against a synthetic local Git repository |
| Release evidence checks | Tested with synthetic files, not operating-system images |
| Multipart reassembly | Tested with synthetic parts, including corruption/path/overwrite checks |

These tests inspect command construction and source behavior. They do not prove
that the chosen packages resolve, the ISO boots, the desktop displays correctly,
or a running container enforces the requested isolation.

## Checks not performed

ShellCheck, Fish parsing and Lua parsing were unavailable in this sandbox.
The supplied Arch CI builder installs these tools and runs the checks there.
Arch package resolution, actual package construction, ArchISO, BIOS/UEFI boots,
SDDM/Hyprland runtime, real installation and rootless Podman runtime tests were
not performed. The release gates correctly remain pending.

## Publication status

No GitHub repository was created. No source was pushed. No Actions workflow was
started. No release or publicly downloadable ISO exists from this session.
The original `NoahWLono/momiji-dots` repository was read but not modified.
The GitHub connector reported account repository permissions, but exposed no
write actions for creating repositories, pushing code or publishing releases.
The sandbox also lacked a working Arch build environment and build privileges.

## Scope of this candidate

The first recipe includes Maple's pinned artwork/ASCII inputs, Hyprland with a
Waybar fallback, Fish/Foot defaults, an SDDM theme, an optional API client and a
rootless agent launcher. Caelestia integration references are retained but the
complete Caelestia environment is not bundled. No model weights, agent-provider
accounts or API keys are included. Upstream assets are fetched at build time;
source/redistribution review remains a required public-release gate.

## Re-run source validation

```sh
python3 tools/validate.py
```

For the real build and QA sequence, use README.md, docs/QA.md and BUILD-STATUS.json.
Do not interpret a successful source check as a completed operating-system release.
