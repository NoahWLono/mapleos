# Release validation

An ISO file existing is not equivalent to a usable operating system. Bind all
results to its SHA256 and source-tree digest in BUILD-MANIFEST.json.
Copy `qa.template.json` to `qa.local.json`; leave unperformed checks false.

## Automated tests

Run the offline source tests. Build with ArchISO. Run `tools/boot_test.py` against
the actual ISO in QEMU under BIOS and UEFI. It boots from the ISO, rather than
bypassing the bootloader with a separately supplied kernel. It watches for a
fixed live-system marker. That marker checks root filesystem availability,
expected binaries, the live account and the disabled SSH service. It does
**not** assert SDDM login, a working GPU, working widgets or the installer.
Keep BUILD-MANIFEST.json, BOOT-TESTS.json, serial logs and packages.txt.

## Manual alpha gates

- Log into SDDM with the live account and select MapleOS. Verify that Hyprland
  reports no configuration errors. Check wallpaper, Waybar, Fish, Fastfetch,
  the app launcher, Super+A and the other documented shortcuts.
- Test virtual/physical network, audio, clipboard and shutdown. Separately
  test Wi-Fi, suspend/resume, brightness and external displays on actual laptops;
  a VM does not establish hardware compatibility.
- Install to a blank VM disk using the documented minimal Archinstall path.
  Finish with the bundled package, reboot twice and run a complete update.
  Verify LUKS unlock where selected, the unique installed password and absence
  of the live marker, public live credentials and copied machine identity.
- Prepare a rootless workspace image. With default flags verify that project
  writes fail, host home/SSH keys are not mounted, provider keys are absent,
  external network is unavailable, privilege escalation fails and the host
  container socket is absent. Then test each explicit opt-in independently.
  Use synthetic canaries, not real secrets. A command-line unit test alone
  cannot prove runtime container isolation.
- Complete redistribution/source-availability review for the exact package
  inventory and imported assets. Record rights and required notices.

Mark `redistribution_review` and the other fields true only after doing the
work. Record reviewer, UTC review time, exact ISO hash and source-tree digest.
The release script will not publish if these are missing or mismatched.
This is a guardrail against accidental claims, not a tamperproof certification
system; a dishonest reviewer can always lie in a JSON file.

## Stable v1.0 requires more

Signed images and update packages, a maintained MapleOS package repository,
a repeatable source-compliance process, upgrades and rollback/recovery tests,
accessibility review, installer recovery, broader graphics/hardware coverage,
and an actual maintenance/support policy. Full Caelestia integration remains
a separate dependency review and UI regression task. No stable v1.0 tag is
created by the supplied alpha publisher.
