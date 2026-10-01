#!/usr/bin/env python3
"""Real ISO boot in QEMU BIOS + UEFI. Does not claim desktop/installer validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


MARKER = "MAPLEOS_LIVE_BOOT_OK:0.1.0-alpha.1"


def firmware() -> tuple[Path, Path]:
    """Return matching OVMF CODE and VARS firmware files."""

    override_code = os.environ.get("MAPLE_OVMF_CODE")
    override_vars = os.environ.get("MAPLE_OVMF_VARS")

    if bool(override_code) != bool(override_vars):
        raise RuntimeError(
            "Set both MAPLE_OVMF_CODE and MAPLE_OVMF_VARS, or neither."
        )

    if override_code and override_vars:
        pairs = [
            (Path(override_code), Path(override_vars)),
        ]
    else:
        pairs = [
            (
                Path("/usr/share/edk2/x64/OVMF_CODE.4m.fd"),
                Path("/usr/share/edk2/x64/OVMF_VARS.4m.fd"),
            ),
            (
                Path("/usr/share/OVMF/OVMF_CODE_4M.fd"),
                Path("/usr/share/OVMF/OVMF_VARS_4M.fd"),
            ),
            (
                Path("/usr/share/OVMF/OVMF_CODE.fd"),
                Path("/usr/share/OVMF/OVMF_VARS.fd"),
            ),
        ]

    for code, variables in pairs:
        if code.is_file() and variables.is_file():
            return code, variables

    raise RuntimeError(
        "OVMF firmware pair not found. Install edk2-ovmf, "
        "or set MAPLE_OVMF_CODE and MAPLE_OVMF_VARS."
    )


def run_boot(iso: Path, mode: str, log: Path, timeout: int) -> dict:
    qemu = shutil.which("qemu-system-x86_64")

    if not qemu:
        raise RuntimeError("qemu-system-x86_64 not installed")

    cmd = [
        qemu,
        "-accel",
        "tcg",
        "-m",
        "4096",
        "-smp",
        "2",
        "-boot",
        "order=d",
        "-cdrom",
        str(iso.resolve()),
        "-display",
        "none",
        "-nic",
        "none",
        "-serial",
        "file:" + str(log.resolve()),
        "-no-reboot",
        "-monitor",
        "none",
    ]

    ovmf_temp: tempfile.TemporaryDirectory[str] | None = None

    if mode == "uefi":
        code, vars_template = firmware()

        ovmf_temp = tempfile.TemporaryDirectory(prefix="mapleos-ovmf-")
        vars_copy = Path(ovmf_temp.name) / "OVMF_VARS.fd"

        shutil.copy2(vars_template, vars_copy)

        cmd += [
            "-drive",
            f"if=pflash,format=raw,readonly=on,file={code}",
            "-drive",
            f"if=pflash,format=raw,file={vars_copy}",
        ]

    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("")

    qemu_log = log.with_suffix(".qemu.log")

    start = time.monotonic()
    passed = False

    try:
        with qemu_log.open("w") as err:
            proc = subprocess.Popen(
                cmd,
                stdout=err,
                stderr=err,
            )

            try:
                while time.monotonic() - start < timeout:
                    if log.exists():
                        serial = log.read_text(errors="replace")

                        if MARKER in serial:
                            passed = True
                            break

                    if proc.poll() is not None:
                        break

                    time.sleep(1)

            finally:
                if proc.poll() is None:
                    proc.terminate()

                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()

        if not passed and qemu_log.exists():
            qemu_errors = qemu_log.read_text(errors="replace").strip()

            if qemu_errors:
                print(
                    f"\nQEMU {mode} diagnostics:\n{qemu_errors}\n",
                    flush=True,
                )

        return {
            "mode": mode,
            "passed": passed,
            "elapsed_seconds": round(time.monotonic() - start, 1),
            "serial_log": log.name,
            "qemu_log": qemu_log.name,
            "scope": (
                "bootloader, kernel, root filesystem, live account and "
                "command presence; NOT graphical login"
            ),
        }

    finally:
        if ovmf_temp is not None:
            ovmf_temp.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "iso",
        type=Path,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=420,
    )

    args = parser.parse_args()

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not args.iso.is_file():
        parser.error("ISO does not exist")

    with args.iso.open("rb") as file:
        sha256 = hashlib.file_digest(file, "sha256").hexdigest()

    results = []

    for mode in ("bios", "uefi"):
        try:
            result = run_boot(
                args.iso,
                mode,
                args.output.parent / f"boot-{mode}.serial.log",
                args.timeout,
            )

        except (RuntimeError, OSError) as exc:
            result = {
                "mode": mode,
                "passed": False,
                "error": str(exc),
            }

        results.append(result)

        print(
            json.dumps(result),
            flush=True,
        )

    args.output.write_text(
        json.dumps(
            {
                "iso_sha256": sha256,
                "results": results,
                "graphical_tested": False,
            },
            indent=2,
        )
        + "\n"
    )

    return 0 if all(result["passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
