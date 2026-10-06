# Working on this repository

- Source of truth: `rules/direct/*.txt`. Build native INCY/Shadowrocket-compatible `.module` files, not complete routing profiles. Do not edit or commit generated `dist/`.
- Each source group produces one module; `modules/all.module` is their union. Do not add source manifests or register groups manually.
- Modules contain only `[Rule]` with `DIRECT` domain rules. Never add DNS settings, IP lists, scripts, MITM, certificates, rewrites, subscriptions, profile IDs or user configuration.
- Personal IPs and original exports stay outside this repository, including documentation, tests and generated outputs. The build must not read local/private profiles.
- Keep domain spelling, case and explicitly listed subdomains. Do not broaden the list to all `.ru`, country IPs or whole services without the owner's request.
- Module semantics are explicit: bare names and `domain:` become `DOMAIN-SUFFIX`; `full:` becomes `DOMAIN`. Reject duplicate resulting rules ignoring case. Do not emit `DOMAIN-KEYWORD` for Direct: support has not been verified.
- `incy://module/onadd/{url}` adds AND enables a module. Label buttons accordingly. Never claim that this is a non-activating profile import. Never import or activate modules on a user's device without permission.
- Preserve the user's existing routing profile and private Direct IPs. Never promise scheduled module auto-update until tested on the target version; distinguish Actions publishing from client refresh.
- Use Python 3.10+ stdlib and plain HTML/CSS/JS. No external assets, telemetry, npm or pip dependencies. Escape source text in HTML; validate rules before publishing.
- Validate with `python3 -m unittest discover -s tests -v`, a local build, `actionlint`, and `git diff --check`. Check output has no `profile.json`, obsolete modules or private data.
- Build deterministically from commit timestamp and SHA. Publish only validated main builds using Pages, never auto-commit generated files. Output folders are disposable managed build directories; never replace unrelated source or user folders.
- Keep UTF-8, LF and a final newline. Comments and documentation are in Russian.
- Use conventional work branches such as `feat/short-slug`, `fix/short-slug`, `docs/short-slug`. No assistant/vendor/environment prefixes; never rename an existing branch without an explicit request.
- Conventional commit messages: English type, completed-work Russian description, then a blank line and `Co-authored-by: Codex <codex@openai.com>`.
- Do not stage, commit or push without explicit authorization for each operation in the current request.
- Everything here is public. Never include secrets, credentials, VPN links or private client data.
