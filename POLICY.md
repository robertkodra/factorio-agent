# Normal-mechanics play policy — 2026-09-09

The objective is to launch a rocket through ordinary Factorio production and research, using agent tools for decisions and inputs. This policy applies to all future runs unless the user explicitly changes it.

## Allowed control

The installed control-only mod may implement fixed, typed actions for walking, normal mining and crafting, inventory transfers, item-funded construction, machine configuration, and ordinary research selection. The character must obey normal collision, reach, materials, crafting/mining durations, and recipe prerequisites. The mod must not change prototypes or recipes. Game speed is 1; only base and `codex-controller` are enabled.

Structured observations may expose the player's inventory, factory, research, production counters, public recipe metadata, and charted surroundings. A spectator camera may follow the engineer. Camera movement must not change the engineer's position or reveal unexplored terrain to the planner.

## Prohibited shortcuts

- No arbitrary console Lua, including `/c`, `/command`, `/silent-command`, and generic `execute_lua` tools, even as a diagnostic shortcut.
- No cheat/editor mode, free items or buildings, instant mining/crafting/research, resource multiplication, speed/reach bonuses, invulnerability, forced victory, or engineer teleportation.
- No direct research-completion flags, world reveal, entity deletion in place of normal mining, or silent recovery grants.
- No erasing failures, pauses, replays, or interventions from the run record.

The custom `/codex-agent` command accepts bounded JSON operations; it does not evaluate supplied code. Factorio supports registered commands separately from arbitrary Lua execution. [Custom command API](https://lua-api.factorio.com/latest/classes/LuaCommandProcessor.html), [console reference](https://wiki.factorio.com/Console).

## Enforcement and limits

Controller 0.2.0 adds fixed `factory` and `research_state` observations. The old `client.play.query()` now rejects input before opening a connection. The named interface has no spawn, teleport, research-grant, or Lua-evaluation operation. Binding, submitting work, and executing active jobs check for normal speed, cheat mode, and the allowed mod set. They reject a violation rather than silently changing the game back.

These are application safeguards, not a tamper-proof sandbox: a machine owner with the server password can still administer Factorio outside the approved client. The tools must not do so. Additional enforcement is needed for all player modifiers, map settings, recipe identity, research-consumption events, and exact placement/event accounting. Keep those limits visible until tested.

Game implementation inside a reviewed mod is Lua; the prohibition concerns arbitrary console execution and mechanics bypasses. This remains a mod-controlled, tool-assisted category even when all normal costs and timing are respected.

## Baselines and milestones

The 2026-09-06 dry run used console Lua for read-only diagnostics. Its action layer used ordinary materials and research; nevertheless it is historical evidence under the new stricter rule, not a clean baseline. Preserve it and its source commit.

For a new baseline, create a fresh map, record version/seed/map settings/mod hashes and initial inventory, and run all gameplay through the bounded interface. Keep both game elapsed and wall elapsed time. Practice pauses are allowed but must be logged; future timed attempts must declare pause/reload rules before starting.

Complete research through labs. Count a rocket only from the actual rocket-launch event. Robot milestones require a real robot action. Each milestone needs a checkpoint and observable evidence, with previous completed steps preserved after a recovery.
