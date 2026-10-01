# Installing the Core alpha

**Test only in a disposable VM until the installation QA gate has passed.**
Back up real data before any OS install. The finalizer does not partition or
format; the separate Arch installer can, after your explicit selections.
This is not a custom graphical installer or a tested one-click install path.

1. Boot the image and sign in as `maple`, password `maple`. These are public
   live-session credentials, never a recommended installed-system password.
2. Connect using NetworkManager and open a terminal. Run `sudo archinstall`.
3. In Arch's interactive installer, choose the **minimal** profile, your actual
   target disk and bootloader, your timezone/locale and a unique regular user.
   Choose a strong unique account password and a separate encryption passphrase.
   Prefer LUKS2 and Btrfs for Momiji-like installations. Do not choose an encrypted
   layout unless you understand how to recover it and have tested its boot path.
4. Complete the installation but do not reboot until MapleOS's package is added.
   Confirm where the installed root is mounted with `findmnt`. The commands
   below assume `/mnt`; do not assume that every archinstall version leaves it
   mounted there. If it unmounts, mount/unlock your **chosen target** using the
   standard Arch instructions before proceeding. No automatic disk guessing is
   implemented here.
5. Run `sudo maple-finish-install /mnt YOUR_USERNAME --confirm-new-install`.
   It verifies a separate mounted fresh Arch root, an existing password-protected
   regular user, absence of an existing rice and the bundled package checksum.
   It installs official dependencies and `mapleos-core`, then copies only absent
   skeleton defaults and switches that user's shell to Fish. Network is required
   to resolve packages. It never copies the live account database, machine ID,
   shared password or host SSH keys.
6. Verify your bootloader, encrypted root mapping, installed user and display
   manager before unmounting and rebooting. The installed root must not contain
   `/etc/mapleos-live`. Test two boots and a full update in the VM.

SDDM requires a normal login; no automatic login is configured. SSH server and
socket are masked initially. Enabling remote access later is a deliberate user
administration task, not something an agent enables behind your back.
The image has no Secure Boot enrollment or signed boot-chain implementation.
Secure Boot support, NVIDIA proprietary drivers, ARM and dual-boot automation
are not claimed in this alpha.

The finalizer has source-level checks but was not executed against a real
installation in the originating session. Treat it as experimental code pending
an end-to-end VM install test.
