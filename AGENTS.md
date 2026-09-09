# Factorio project rules

Read `HANDOFF.md`, `POLICY.md`, `ROADMAP.md`, `PUBLICATION.md`, and `knowledge/README.md` before development.

- Work on a branch, preserve unrelated changes, and use reviewed pull requests for subsequent development.
- Follow normal game mechanics. Never send arbitrary Lua through console, RCON, or MCP. Never grant items/research, alter speed/reach/recipes, teleport the engineer, or bypass collision, reach, durations, and inventory costs.
- Use fixed `/codex-agent` operations. Add missing capabilities as narrow reviewed mod code with relevant tests; do not add a generic Lua executor.
- Observe the player's factory and charted surroundings only. Do not expose hidden-world information.
- Historical experiments predate the no-console-Lua policy. Preserve their failures and limitations in aggregate reports; start a fresh map for compliant baselines.
- Count actual milestone completion. Green-pack production is not green-consuming research. The next concrete target is `military-2`, following its prerequisites.
- Keep exact run records privately: ticks, wall time, pauses, failures, interventions, version/seed/mod identity, and checkpoint hashes. Do not erase failed attempts.
- This public repository excludes saves, raw logs/observations, runtime files, environment files, credentials, personal paths, private identities, installed SDKs, and game binaries. Review aggregate findings before publishing. All new notebook output stays under ignored `runtime/`.
- Do not import old private Git history, branches, or bundles into this repository. Do not assume removing a file from the latest commit removes it from history.
- Run unit tests and `python3 scripts/check_publication.py --history` before publication, plus a dedicated secret scanner. Do not print secret contents in audit output.
- This is a tool-assisted controller. Do not claim unattended rocket readiness, human speedrun eligibility, or measured visual smoothness without validation.

User instructions take precedence. Authorized development, read-only inspection, local tests, and reversible fixes do not need another permission round.
