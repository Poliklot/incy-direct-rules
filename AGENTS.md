# Working on this repository

- Source of truth: `rules/direct/*.txt` and `profile.base.json`. Do not edit or commit generated `dist/`.
- Preserve domain spelling and explicitly listed subdomains unless the owner requests a change. Do not expand this personal Direct list to all `.ru`, country IPs or broad service groups.
- Keep `GlobalProxy: "true"`: only listed domains bypass the proxy. The import link must use `autorouting/add`, not auto-activating `onadd`.
- Use Python stdlib. Run `python3 -m unittest discover -s tests -v` and a local build after changes. Lint workflow changes with `actionlint` when available.
- Build deterministically from source commit timestamp and SHA. Publish only validated main builds using Pages, never auto-commit generated files.
- Keep files UTF-8, LF, with a final newline. Rule comments and documentation are in Russian.
- Use conventional work branches, e.g. `feat/short-slug`, `fix/short-slug`, `docs/short-slug`. No assistant, vendor or execution-environment prefixes; never rename an existing branch without an explicit request.
- Conventional commit messages: type in English, description in Russian, phrased as completed work. For assistant-assisted commits in this public personal project, append `Co-authored-by: Codex <codex@openai.com>` after a blank line.
- Do not stage, commit or push without the owner's explicit authorization for the respective operation in the current request.
- Everything here is public. Never include secrets, VPN subscription links, credentials or private client data.
