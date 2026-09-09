# Progression and MCP roadmap

The next milestone is a clean, reproducible early-game run under `POLICY.md`, followed by research that consumes green science. Robot and rocket capability is not yet demonstrated.

## Gameplay milestones

| ID | Goal | Completion evidence | Current evidence |
|---|---|---|---|
| G0 | Establish a clean baseline | Fresh map; initial state and version/seed/mod hashes; no console Lua | Recorded for responsiveness and the separate learning attempt; the latter records controller upgrades and recovery |
| G1 | Stable early factory | Powered red/green production, supplied labs, enough fuel/input buffers | Partial: current-policy checkpoint continuation has automatic red delivery and Electric mining drill; green and continuous input supply remain pending |
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

The optional [MCP stdio facade](MCP.md) wraps the fixed RCON client using the official Python SDK. It exposes 15 schema-validated tools and persistent RCON transport, including local placement and charted water/pollution observations, with no generic Lua, shell, or raw-console tool. Submission returns immediately; status/cancel operate while a tick job is active. Uncertain mutations must be reconciled by job ID instead of replayed. SDK/stdio/socket tests, historical-save compatibility and a [fresh conveyor responsiveness test](knowledge/responsiveness-001.md) pass. Fresh automated red/green production remains pending. The archived upstream FactorioMCP exposed unrestricted Lua and remains unsuitable for new-policy runs.

## Next implementation order

1. **Implemented:** MCP facade through controller 0.3.2, including initialization/tool listing, input validation, cancellation, reconnect, and no mutation replay. See [MCP.md](MCP.md) for setup and test scope.
2. **Partial:** measurable path-progress watchdog and bounded retries pass a live blocked-tree test. Add automatic reachable service positions and test more poles, belts, corners and unreachable targets.
3. **Partial:** local normal-placement preflight and explicit turret ammo access exist. Add planning for power/fluid/inserter connections and complete entity-specific inventory mappings.
4. Add fresh-run manifests and event-based goal evaluation; then repeat G0/G1 and complete G2.
5. Extend oil/fluids, modules, robots, and silo operations only as those stages require them, with normal mechanics and stage-specific tests.

For the next learning run, supply/fuel automation and a larger smelting base matter more than shaving a few milliseconds from tool responses. See [speedrun preparation](knowledge/speedrun-preparation.md) for measured red production, depletion recovery, capacity/fuel calculations and the Military 2 test protocol.

## What a full rocket-playing agent still needs

The first target is reliable solo completion under the existing normal-mechanics
policy. Competitive performance then needs repeated measurements under declared
map, enemy, pause, and reload rules; no speed target is established yet.

| Capability | Current state | Evidence needed before relying on it |
|---|---|---|
| Agent connection and bounded actions | MCP/RCON tested live; fresh conveyor sequence, cancellation, and reconnect pass | Repeat powered red/green production on a fresh map |
| Navigation and construction | Bounded progress watchdog; local placement preflight | Automatic reachable service positions, broader obstacle cases, power and fluid connection planning |
| Economy and planning | Research dependencies, ordered crafting budgets and hand-authored batches | Automatic fuel/input reserves, concurrent production, bottleneck detection, recovery from starvation |
| Version-specific knowledge | Static catalog plus live enabled-recipe names; sourced strategy playbook | Fixed live recipe/technology metadata and fluid/by-product planning |
| Progress tracking and recovery | Saved job state and notebook helpers | Fresh-run manifests, checkpoint hashes, research-consumption events, resumable milestone planner |
| Oil and later science | Unproven | Sustained oil/chemical production and actual lab consumption at each required tier |
| Robots and construction | Ghost/robot controls not implemented | Item-funded ghost placement and observed normal robot construction |
| Silo and launch | Silo inventory/launch operations not implemented | Narrow reviewed actions, real material consumption, actual rocket launch event, final checkpoint |
| Enemy-enabled play | Charted enemy/pollution observations; one turret loaded live | Live defensive encounters, normal equipment/combat/repair controls, automated ammunition supply |

For each fixed benchmark configuration, report completed attempts/total attempts,
ticks to each verified milestone and launch, total wall time including planning,
pauses/reloads, failed batches, and human interventions. Record losses as well as
successes. Optimize repeatable completion before comparing speed across attempts.
