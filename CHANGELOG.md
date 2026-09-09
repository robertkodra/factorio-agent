# Changes

## Enemy-enabled learning and controller 0.3.2 — 2026-09-09

- Added a sourced strategy playbook and research/defense budgets, with explicit limits for old speedrun guides and version-specific recipes.
- A fresh development attempt established burner production, steam power, two labs, Automation, Gun turret and one turret with ten magazines. The [learning report](knowledge/learning-001.md) preserves two cancelled/five failed batches, three controller upgrades, pauses and recovery. Automated science and live combat remain pending.
- Fixed native crafting progression through player ownership, bounded navigation oscillation, and added charted water/pollution observations, local placement checks and explicit character/turret ammo inventories. Ordered craft budgeting accounts for the cost of new crafts even when a product already exists.
- All 36 unit tests and the isolated historical reload/MCP check passed. A current six-tool live sample measured 16.90 ms median engineer observations and 33.43 ms placement checks; 635 logged benchmark calls had no errors. These are local response measurements, not autonomous gameplay or frame-pacing results.

## Live responsiveness and batch validation — 2026-09-09

- Tested the Steam client against a fresh 2.0.77 map: the 29-action conveyor opening completed in 7,504 ticks, with 12 consecutive belt-placement ticks and normal crafting/walking overlap. Twenty moving-job cancellations and a live MCP reconnect passed.
- Measured roughly 17 ms median observation responses. A paired comparison reduced the 512-action submission median from 88.72 ms to 38.67 ms by selecting the action schema from its required type discriminator, preserving the full advertised validation contract. All 25 tests pass, including validation-equivalence coverage.
- Added an explicit live benchmark harness that keeps raw results under runtime and a [reviewed aggregate report](knowledge/responsiveness-001.md). The fresh test checkpoint is private; no new science or rocket milestone is claimed.

## MCP connection — 2026-09-09

- Added an optional local stdio MCP server using the official Python SDK, with 13 fixed tools, strict per-action schemas, and a persistent RCON connection. Existing CLI clients retain their standard-library-only setup.
- Added explicit dropped-response reconciliation by job ID, no automatic mutation replay, responsive tool discovery, and distinction between definite controller rejection and uncertain transport failure.
- Added MCP SDK/stdio/socket tests and an optional `--mcp` historical fixture check. The live check passed initialization with protocol 2025-11-25, observation, invalid-action rejection, and submit/status/cancel on an isolated copy in Factorio 2.0.77. Tick, engineer position, inventory, and the source save hash were preserved.
- The first live attempt correctly failed the mod policy because omitted bundled expansions defaulted to enabled. Setup and isolated tests now explicitly disable Space Age, Quality, and Elevated Rails; the subsequent live test verified only base and controller were active. The failed attempt's private runtime directory is retained.
- No controller Lua or gameplay milestone changed. Fresh G0/G1, green-consuming research, robust navigation, sustained supply planning, and later science/robots/rocket remain pending.

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
