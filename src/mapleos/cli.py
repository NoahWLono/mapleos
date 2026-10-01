"""MapleOS AI workbench. Standard library only; no ambient agent privileges."""
from __future__ import annotations
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

VERSION = "0.1.0-alpha.1"
MAX_FILE_BYTES = 128 * 1024
MAX_CONTEXT_BYTES = 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
ALLOWED_ENV = {"OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"}
IMAGE_RE = re.compile(r"(?:[a-zA-Z0-9./_:-]+@)?sha256:[a-f0-9]{64}\Z")
SENSITIVE_NAMES = {".env", ".env.local", ".env.production", ".ssh", ".aws", ".gnupg", ".kube", "credentials.json"}

class MapleError(ValueError):
    pass

def validate_project(value: str, home: Path | None = None) -> Path:
    path = Path(value).expanduser().resolve(strict=True)
    home = (home or Path.home()).resolve()
    if not path.is_dir():
        raise MapleError("The workspace must be a directory.")
    forbidden = [Path(x) for x in ("/", "/home", "/root", "/etc", "/usr", "/var", "/tmp", "/mnt", "/media", "/run", "/dev", "/proc", "/sys", "/opt")]
    if path == home or path in home.parents or path in forbidden:
        raise MapleError("Select one project, not your home directory or a system root.")
    for base in map(Path, ("/etc", "/usr", "/run", "/dev", "/proc", "/sys")):
        if path.is_relative_to(base):
            raise MapleError("System directories cannot be agent workspaces.")
    # Podman's mount parser treats these characters as delimiters.
    if any(c in str(path) for c in (",", "\n", "\r", "\x00")):
        raise MapleError("Workspace paths cannot contain commas or newlines.")
    return path

def sensitive_paths(project: Path) -> list[str]:
    # Conservative shallow check, not a promise that the tree is secret-free.
    return sorted(p.name for p in project.iterdir()
                  if p.name in SENSITIVE_NAMES or p.name.startswith('.env.')
                  or p.suffix in {'.pem', '.key', '.p12', '.pfx'})

def agent_command(args: argparse.Namespace, uid: int | None = None, gid: int | None = None) -> list[str]:
    uid = os.geteuid() if uid is None else uid
    gid = os.getgid() if gid is None else gid
    if uid == 0:
        raise MapleError("Agent workspaces must run as a regular user, never with sudo.")
    project = validate_project(args.project)
    if not IMAGE_RE.fullmatch(args.image):
        raise MapleError("Use an image digest (registry/name@sha256:...) or a local sha256: image ID, not a mutable tag.")
    suspects = sensitive_paths(project)
    if suspects and not args.allow_sensitive_files:
        raise MapleError("Potential credentials in workspace: " + ', '.join(suspects)
                         + ". Use a clean checkout, or explicitly accept with --allow-sensitive-files.")
    for key in args.allow_env:
        if key not in ALLOWED_ENV:
            raise MapleError("Only individually named provider keys can be forwarded; not arbitrary host environment variables.")
        if not os.environ.get(key):
            raise MapleError(f"Requested key {key} is not set.")
    mount = f"type=bind,src={project},destination=/workspace"
    if not args.write:
        mount += ",ro=true"
    command = ["podman", "run", "--rm", "--pull=never", "--init",
               "--userns=keep-id", "--user", f"{uid}:{gid}",
               "--cap-drop=all", "--security-opt=no-new-privileges",
               "--read-only", "--pids-limit=256", "--memory=2g", "--cpus=2",
               "--network=" + ("pasta" if args.network else "none"),
               "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m",
               "--tmpfs", f"/home/maple:rw,nosuid,nodev,size=128m,uid={uid},gid={gid},mode=700",
               "--env", "HOME=/home/maple", "--env", "XDG_CONFIG_HOME=/home/maple/.config",
               "--workdir=/workspace", "--mount", mount]
    if sys.stdin.isatty() and sys.stdout.isatty():
        command += ["-it"]
    else:
        command += ["-i"]
    for key in args.allow_env:
        command += ["--env", key]  # Podman reads value from its environment, never argv.
    command.append(args.image)
    payload = list(args.command)
    if payload and payload[0] == "--":
        payload.pop(0)
    command += payload or ["bash"]
    return command

def validate_api_url(value: str) -> str:
    if any(c.isspace() for c in value):
        raise MapleError("API URL must not contain whitespace.")
    try:
        p = urllib.parse.urlsplit(value)
        _ = p.port  # Validate the port even before a request is authorized.
    except ValueError as exc:
        raise MapleError("Invalid API URL or port.") from exc
    if not p.hostname or p.username or p.password or p.query or p.fragment:
        raise MapleError("Use an API base URL without credentials, query, or fragment.")
    try:
        local = ipaddress.ip_address(p.hostname).is_loopback
    except ValueError:
        local = p.hostname.lower() == "localhost"
    if p.scheme != "https" and not (p.scheme == "http" and local):
        raise MapleError("Remote API connections require HTTPS; HTTP is allowed only on loopback.")
    return value.rstrip('/')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise MapleError("API redirect refused to prevent credential forwarding.")

def make_chat_request(prompt: str, paths: list[str], model: str) -> dict:
    if not prompt.strip() or not model.strip():
        raise MapleError("A non-empty prompt and explicit model name are required.")
    total = len(prompt.encode('utf-8'))
    parts = [prompt]
    for value in paths:
        path = Path(value).expanduser().resolve(strict=True)
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            raise MapleError(f"File must be a regular UTF-8 text file under 128 KiB: {path.name}")
        with path.open('rb') as f:
            raw = f.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES or b'\0' in raw:
            raise MapleError("Binary or oversized input file refused.")
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise MapleError("Only UTF-8 text files are accepted.") from exc
        total += len(raw)
        if total > MAX_CONTEXT_BYTES:
            raise MapleError("Explicit request context exceeds 1 MiB.")
        parts.append(f"\nExplicit attachment: {path.name}\n{content}")
    if total > MAX_CONTEXT_BYTES:
        raise MapleError("Request exceeds 1 MiB.")
    return {"model": model, "messages": [{"role": "user", "content": '\n'.join(parts)}]}

def ask(args: argparse.Namespace) -> int:
    base = validate_api_url(args.base_url)
    prompt = args.prompt or sys.stdin.read(MAX_CONTEXT_BYTES + 1)
    request = make_chat_request(prompt, args.file, args.model)
    if not args.yes_send:
        print(f"Destination: {base}\nModel: {args.model}\nExplicit attachments: {len(args.file)}")
        print("The request may send confidential text and incur provider charges. Nothing has been sent.")
        print("Review the prompt and attachments, then add --yes-send to authorize this request.")
        return 2
    headers = {"Content-Type": "application/json", "User-Agent": "MapleOS/" + VERSION}
    key = os.environ.get("MAPLE_AI_API_KEY")
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(request).encode(), headers=headers, method="POST")
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=90) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise MapleError("Provider response exceeded 8 MiB.")
        payload = json.loads(body)
        text = payload["choices"][0]["message"]["content"]
        if not isinstance(text, str):
            raise MapleError("Provider did not return text content.")
        print(text)
        return 0
    except urllib.error.HTTPError as exc:
        # Never echo a response body: it could contain secrets.
        raise MapleError(f"Provider returned HTTP {exc.code}; response body withheld.") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise MapleError("API connection failed; check the endpoint and network.") from exc
    except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
        raise MapleError("Invalid Chat Completions-compatible response.") from exc

def doctor() -> int:
    checks = {name: shutil.which(name) for name in ("podman", "git", "python", "fish", "codex", "claude", "ollama")}
    print(f"MapleOS workbench {VERSION}")
    print("Provider CLIs and model weights are optional, not included or authenticated by default.")
    for name, path in checks.items():
        print(f"  {name:10s} {'available' if path else 'not installed'}")
    print("Default agent policy: one read-only workspace; no network; no host home; no ambient keys.")
    print("Network opt-in permits general outbound access, not a provider-domain allowlist.")
    print("Container isolation is defense in depth, not a proof against kernel exploits.")
    print("Use `maple agent --help`, `maple ask --help`, or `maple welcome`.")
    return 0

def workbench() -> int:
    doctor()
    if not sys.stdin.isatty():
        return 0
    while True:
        print("\n[1] Agent launcher help  [2] API client help  [3] Offline welcome  [4] Host shell  [q] Quit")
        try:
            choice = input("Maple > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); return 0
        if choice in ("q", "quit", "exit"):
            return 0
        if choice in ("1", "2"):
            # Ask argparse for help in a child, so its SystemExit does not close the workbench.
            subprocess.run([sys.executable, "-m", "mapleos.cli", "agent" if choice == "1" else "ask", "--help"],
                           env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1])}, check=False)
        elif choice == "3":
            subprocess.run(["xdg-open", "/usr/share/mapleos/welcome/index.html"], check=False)
        elif choice == "4":
            print("Opening your ordinary USER shell, not an agent sandbox. Use maple agent for scoped execution.")
            subprocess.run([shutil.which("fish") or "/bin/bash"], check=False)
        else:
            print("Choose 1, 2, 3, 4, or q. Nothing was sent to an AI provider.")

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="maple", description="MapleOS: your machine, your agents, your permission.")
    parser.add_argument('--version', action='version', version=VERSION)
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('doctor', help='Show local tools without contacting providers')
    sub.add_parser('workbench', help='Open the terminal workbench')
    sub.add_parser('welcome', help='Open the offline first-run guide')
    agent = sub.add_parser('agent', help='Run a command/agent in a rootless, project-scoped container')
    agent.add_argument('--project', default='.')
    agent.add_argument('--image', required=True)
    agent.add_argument('--write', action='store_true', help='Allow edits in the mounted project')
    agent.add_argument('--network', action='store_true', help='Allow outbound network, including possible data exfiltration')
    agent.add_argument('--allow-env', action='append', default=[], choices=sorted(ALLOWED_ENV))
    agent.add_argument('--allow-sensitive-files', action='store_true')
    agent.add_argument('--dry-run', action='store_true')
    agent.add_argument('command', nargs=argparse.REMAINDER)
    chat = sub.add_parser('ask', help='Send an explicit request to a local or remote compatible API')
    chat.add_argument('prompt', nargs='?')
    chat.add_argument('--model', required=True)
    chat.add_argument('--base-url', default=os.environ.get('MAPLE_AI_BASE_URL', 'http://127.0.0.1:11434/v1'))
    chat.add_argument('--file', action='append', default=[])
    chat.add_argument('--yes-send', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action in (None, 'doctor'):
            return doctor()
        if args.action == 'workbench':
            return workbench()
        if args.action == 'welcome':
            return subprocess.run(['xdg-open', '/usr/share/mapleos/welcome/index.html'], check=False).returncode
        if args.action == 'ask':
            return ask(args)
        if args.action == 'agent':
            command = agent_command(args)
            if args.dry_run:
                print(shlex.join(command)); return 0
            if not shutil.which('podman'):
                raise MapleError('Podman is not installed.')
            # Subprocess environment excludes unrelated credentials. Runtime vars
            # below are needed by rootless Podman, never forwarded into the guest.
            keys = {'PATH','HOME','USER','LOGNAME','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','TERM','LANG','LC_ALL'} | set(args.allow_env)
            clean_env = {k:v for k,v in os.environ.items() if k in keys}
            return subprocess.run(command, env=clean_env, check=False).returncode
    except (MapleError, OSError) as exc:
        print(f"maple: {exc}", file=sys.stderr); return 1
    return 1

if __name__ == '__main__':
    raise SystemExit(main())
