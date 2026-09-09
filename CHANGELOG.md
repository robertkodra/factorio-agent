# Changes

## Public source publication — 2026-09-09

- Published reviewed controller source, plans, tests, roadmap, and summarized historical findings with independent Git history.
- Kept historical saves, raw evidence, original commits, runtime credentials/configuration/logs, and private handoff material in a separate private archive.
- Extracted version-specific recipe/technology facts into `data/`, removing run ticks and enabled/researched snapshot flags.
- Routed named notebook runs and live-test reports into ignored runtime storage. The historical reload test now requires an explicit private fixture path.
- Added publication checks and contribution guidance. Gameplay controller Lua is unchanged from the reviewed 0.2.0 source.

## 0.2.0 — 2026-09-09

- Adopted the no-cheats/no-console-Lua policy and progression milestones.
- Replaced active arbitrary Lua diagnostics with fixed `factory` and `research_state` operations. The deprecated notebook query rejects input before opening a connection.
- Added normal-speed, cheat-mode, and allowed-mod checks at bind, submit, and active execution. These are application safeguards, not a tamper-proof sandbox.
- Added run selection, baseline initialization, and closed-run protection.
- Nine original Python tests passed. An isolated Factorio 2.0.77 process loaded a historical save using controller 0.2.0, read fixed observations, rejected unknown cheat-like operations, and preserved tick/inventory/position during observation. The source save was unchanged.
- The MCP protocol facade, further navigation improvements, later science/robots/rocket, and a fresh compliant gameplay run remain untested or unimplemented.

## 0.1.0 — 2026-09-06

Tick-controller experiments demonstrated conveyors, recovery, electricity, red/green science, and fixes for hand-crafting progression and exact mining selection. The [dry-run report](knowledge/dry-run-001.md) retains timings, failures, and limitations. Read-only console Lua was used in historical diagnostics before the stricter policy.
