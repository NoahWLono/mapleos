# Redistribution and source review

The source bundle contains newly authored build code. It does not contain a
compiled OS, the upstream Momiji repository, provider binaries, or model weights.
At build time, four allowlisted files are read from the pinned Momiji commit.
No broad license grant is inferred merely because a repository is public.

The project owner requested a shareable MapleOS based on their dotfiles and
Maple character. Before **public binary distribution**, record the applicable
rights/license for each imported file and any third-party material embedded in it.
The `redistribution_review` release gate must remain false until that review is
complete. In particular, this source repository's MIT license does not silently
relicense wallpaper, character artwork, Caelestia snippets, Arch components,
or someone else's packages.

Keep Arch package license files in the ISO. Record the exact package inventory,
retain needed notices, and satisfy the source-availability/source-offer obligations
of every component that requires them. An inventory or link to Arch's website is
not, by itself, a declaration that every redistribution obligation is satisfied.
Have this process reviewed before broad distribution.

The local `[mapleos-build]` repository is a temporary build input for MapleOS's
own freshly built package. Its unsigned-package exception is scoped to that
local repository and is not added to the installed machine's pacman configuration.
Official Arch packages retain their normal signature requirements.

No proprietary apps, paid accounts, API keys, model weights, or user credentials
are bundled. Cloud-provider and model terms apply separately after user opt-in.
MapleOS is an independent project, not an official Arch Linux, OpenAI, Anthropic,
Hyprland, or Caelestia product. A name/trademark clearance has not been performed.
