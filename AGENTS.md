# Working on MapleOS

This repository is an experimental OS distribution, not a disposable user home.

Keep changes scoped to this repository. Never read credentials, browser profiles,
SSH private keys, Wi-Fi profiles or arbitrary files from the builder's home.
Never embed tokens, machine identities, UUIDs or account passwords into the image.
The public maple/maple password is permitted only for the disposable live user.

Run `python3 tools/validate.py` before committing. Build in a disposable Arch VM
or the supplied CI container. Do not claim an ISO exists until mkarchiso succeeds.
Do not claim a desktop/installer works from a shell lint or a boot marker alone.
Do not mark QA checks true without real evidence for the exact ISO hash.

No force-pushes. No automatic public releases. No autonomous block-device writes.
The publisher requires actual boot evidence and manual QA. The source-pinned
Momiji import allowlist is the only permitted upstream home-data input.

Security: default agents run rootless, offline and project-read-only. Network,
project writes and individual provider keys require explicit flags. Never add
blanket sudo, mount the host home, or pass host Docker/Podman sockets to agents.
Do not use prompts, AGENTS.md, or politeness as a claimed security boundary.
