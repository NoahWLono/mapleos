# AI-native design and operating guide

MapleOS puts the AI workbench on Super+A and in the app launcher. It does not
make a provider account mandatory, embed API tokens, start a cloud-connected
agent at login, or let an agent become root simply by asking politely.

## Two distinct tools

`maple ask` is a simple explicit-request client, not an autonomous agent. It
supports a Chat Completions-compatible API. The model name is supplied by the
user because model availability and terms change. Only the prompt and named
`--file` attachments are sent. It never automatically scans a home, clipboard,
browser, project or desktop. It does not infer that a prompt is non-sensitive.
Remote endpoints require HTTPS; HTTP is allowed on loopback. Redirects are
refused. Provider responses and prompts are not persisted to logs by this client.

Example for an independently installed local server and an already loaded model:

```sh
maple ask --base-url http://127.0.0.1:11434/v1 --model YOUR_INSTALLED_MODEL 'Explain a Unix pipe'
# Nothing is sent until the same command includes --yes-send.
```

`MAPLE_AI_API_KEY` supplies an optional key for a remote endpoint. Set it using
a private local shell or secret manager, never in a repo, screenshot or chat.
Requests may consume provider credits. A desktop subscription does not imply
that a separately billed API account or every CLI is included.

`maple agent` is a rootless container launcher for a shell or separately installed
agent CLI. It can run Codex or another tool present in the chosen image. It does
not invent provider approval settings or disable a provider's native safeguards.
The container cannot run with host root, host home mounts or host engine sockets
through this launcher. One selected workspace is the sole host bind mount.

Default policy: read-only workspace, read-only container root, private temporary
home, private /tmp, no network, no automatic image pull, resource limits,
dropped capabilities and no-new-privileges. The image must be a local SHA256
image ID or an explicitly selected digest reference already present on the machine.
No general-purpose OCI image is preloaded in this first ISO recipe.

## Prepare a workspace image explicitly

These commands contact registries and install packages. Run as your regular
user, **not sudo**. They build an image outside the ISO:

```sh
podman pull docker.io/archlinux/archlinux:base
# Inspect the returned digest and keep it with your build record.
podman image inspect docker.io/archlinux/archlinux:base --format '{{index .RepoDigests 0}}'
# Replace DIGEST_REFERENCE below with that complete name@sha256:... value.
podman build --build-arg BASE=DIGEST_REFERENCE -t localhost/maple-dev:local /usr/share/mapleos/containers
podman image inspect localhost/maple-dev:local --format '{{.Id}}'
# Replace LOCAL_IMAGE_ID with the sha256:... ID from the previous command.
maple agent --project ~/Projects/example --image LOCAL_IMAGE_ID -- bash
```

To include Codex, use `--build-arg CODEX_VERSION=EXACT_VERSION` on the build.
The optional npm install is inside the container build, not a privileged
installer piped into your host shell. Choose and review an actual available
version; there is deliberately no hard-coded old version or `latest` alias.
Other providers can be added by an explicit reviewed Containerfile change.
There are no provider binaries in the distributed source or base ISO recipe.

For a networked agent with explicit project editing:

```sh
maple agent --project ~/Projects/example --image LOCAL_IMAGE_ID --write --network -- codex
```

Provider authentication can occur within that disposable session. If using an
API key instead, `--allow-env OPENAI_API_KEY` or `--allow-env CODEX_API_KEY`
forwards only that named key; use the name your selected CLI version supports.
The key then becomes available to **all code inside that container**, not only
the model client. Session credentials in the temporary home disappear on exit.
The launcher does not claim a secret broker or hardware vault.

`--network` means general outbound network, not a domain allowlist. With network
and project reads enabled, an agent can send project data to remote services.
`--write` allows deleting or changing project files. Use a clean checkout,
backups, version control and a deliberate review of changes. A shallow check
for common credential filenames helps catch mistakes but is not a secret scanner.
A container is defense in depth, not a VM or protection against every kernel bug.

## Roadmap, not shipped claims

A native GUI consent dashboard, credential broker, fine-grained outbound proxy,
per-task snapshots, MCP server registry, local-model installer, signed agent
images and NVIDIA OpenShell integration are future work. None is implied by
the current launcher. Super+A opens a terminal status/help workbench, not a
fully developed chat application or omnipotent desktop agent.
