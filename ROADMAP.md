# Progression and MCP roadmap

The next milestone is a clean, reproducible early-game run under `POLICY.md`, followed by research that consumes green science. Robot and rocket capability is not yet demonstrated.

## Gameplay milestones

| ID | Goal | Completion evidence | Current evidence |
|---|---|---|---|
| G0 | Establish a clean baseline | Fresh map; initial state and version/seed/mod hashes; no console Lua | Pending |
| G1 | Stable early factory | Powered red/green production, supplied labs, enough fuel/input buffers | Demonstrated in the historical dry run; repeat cleanly |
| G2 | First green-consuming research | `military-2` completed by labs after Military, Steel processing, and green-science prerequisites | Pending; producing green packs alone does not pass |
| G3 | Military science and research | Military-science recipe unlocked; packs produced; a technology requiring military packs completed through labs | Pending |
| G4 | Oil and blue science | Oil processing chain supplies blue packs; blue-consuming research completed | Pending |
| G5 | Working robotics | Robotics/construction robotics completed; powered robot infrastructure; a construction robot builds an item-funded ghost | Pending |
| G6 | Rocket preparation | Required later science produced and consumed; rocket-silo research completed; silo/material pipeline operates | Pending |
| G7 | Rocket launch | Actual launch event plus final save and production/timing record | Pending |

The current 2.0.77 catalog specifies Military 2 as 20 red + 20 green research units, 15 seconds per unit before lab bonuses. Revalidate costs if the game version changes. For G3, choose an actual military-consuming technology from the live catalog, with its prerequisites; do not substitute merely unlocking military science.

Milestones should eventually be evaluated automatically from research/production/robot/launch events. Until that evaluator exists, mark them complete only after inspecting the game evidence. Failed batches and manual recovery remain in the ledger.

## One MCP server, several focused tool groups

Start with one local MCP server around the existing controller. Multiple independent action executors would compete for the same engineer. Separate services only when there is a demonstrated need.

| Group | Intended tools | Existing foundation / missing work |
|---|---|---|
| Observation | Engineer state, local scan, entity inspection, factory state, research state, recipe lookup | Fixed game commands exist for the first five; recipe export should become another fixed command |
| Actions | Validated batches for walking/mining/crafting/building/transfers/configuration/research | Existing tick executor; improve obstacle recovery, placement preflight, and inventory mapping |
| Planning | Material budgets, layouts, production ratios, reachable service positions | Early material calculator exists; richer planner and geometric validation pending |
| Progression | List goals, evaluate goals, observe completion events, write milestone evidence | Roadmap and historical monitor exist; event-driven goal evaluator pending |
| Session | Status, cancellation, explicit pause/resume, checkpoint, recovery | Fixed commands exist; portable orchestration and broader recovery tests pending |
| Performance | Timing, throughput, starvation/fuel/power diagnostics | Existing logs; sustained throughput and bottleneck metrics pending |

The custom RCON client is **not yet a standards-compliant MCP server**. The archived upstream FactorioMCP had that protocol layer, but it also exposed unrestricted Lua and is not approved for new-policy runs. Build a narrow MCP facade with schema-validated tools and persistent RCON transport; expose no generic Lua, shell, or raw-console tool. Status/cancel must remain responsive while a tick job is active, and uncertain mutations must be reconciled by job ID instead of replayed.

## Next implementation order

1. Connect the typed MCP facade to the 0.2.0 fixed operations. Test initialize/tool listing, input validation, cancellation, reconnect, and no mutation replay.
2. Fix navigation oscillation with measurable path progress and bounded recovery. Test trees, poles, belts, collision corners, and unreachable goals.
3. Add complete footprint/power checks and entity-specific inventory access. Preserve real item/reach/collision checks in the game.
4. Add fresh-run manifests and event-based goal evaluation; then repeat G0/G1 and complete G2.
5. Extend oil/fluids, modules, robots, and silo operations only as those stages require them, with normal mechanics and stage-specific tests.

For the next learning run, supply/fuel automation and a larger smelting base matter more than shaving a few milliseconds from tool responses. See `knowledge/next-run.md` for observed material and capacity constraints.
