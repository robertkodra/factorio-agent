# Progression and MCP roadmap

The [state-mirror slice](knowledge/state-mirror-001.md) is now ready for offline review;
its new observation contract is source-only. Do not advance to live construction
until reviewed.

The objective is repeatable normal-mechanics rocket completion. Military 2 and
Oil Gathering have completed in checkpoint practice; connected oil production,
later science and a launch remain unverified. Follow the
[architecture review gates](knowledge/review-response-001.md) before further
factory expansion. Fresh-map generalization and competitive performance are
separate demonstrations, not consequences of passing executor tests.

## Gameplay milestones

| ID | Goal | Completion evidence | Current evidence |
|---|---|---|---|
| G0 | Establish a clean baseline | Fresh map; initial state and version/seed/mod hashes; no console Lua | Recorded for responsiveness and the separate learning attempt; the latter records controller upgrades and recovery |
| G1 | Stable early factory | Powered red/green production, supplied labs, enough fuel/input buffers | Partial: red/green production and research demonstrated in checkpoint practice; sustained input supply and a clean fresh-map repeat remain pending |
| G2 | First green-consuming research | `military-2` completed by labs after Military, Steel processing, and green-science prerequisites | Demonstrated in checkpoint practice with native completion; fresh-map repetition pending |
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

The optional [MCP stdio facade](MCP.md) wraps the fixed RCON client using the official Python SDK. It exposes 19 schema-validated tools and persistent RCON transport, including local placement and charted water/pollution observations, with no generic Lua, shell, or raw-console tool. Submission returns immediately; status/cancel operate while a tick job is active. Uncertain mutations must be reconciled by job ID instead of replayed. SDK/stdio/socket tests, historical-save compatibility and a [fresh conveyor responsiveness test](knowledge/responsiveness-001.md) pass. Fresh automated red/green production remains pending. The archived upstream FactorioMCP exposed unrestricted Lua and remains unsuitable for new-policy runs.

## Next implementation order

The [review response](knowledge/review-response-001.md) defines the acceptance
criteria and supersedes the older extension-by-extension order:

1. Review a single identified 0.8 baseline, including supported Python tests,
   event/transfer correctness and clear source/runtime identities.
2. Build a reconstructable state mirror with sequenced native events, bounded
   reconciliation reads, stale-state handling and measured observation costs.
3. Build a production graph that diagnoses disconnected and starved paths from
   observations, then compile and live-verify one reusable production block.
4. Add backward phase planning with infrastructure, power, logistics and defense
   costs; validate oil through launch in checkpoint integration exercises.
5. Require a clean fixed-seed launch with frozen code, then at least five unseen
   seeds with all failures counted. Optimize completion time after reliability.

The capability table below retains narrower implementation details; implemented
helpers do not establish that the new mirror or compiler exists.

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
| Progress tracking and recovery | Persistent scheduler, source/plan manifests, compact job receipts and native research/launch evidence | Fresh-map completion, later science consumption and final launch checkpoint |
| Oil and later science | Unproven | Sustained oil/chemical production and actual lab consumption at each required tier |
| Robots and construction | Ghost/robot controls not implemented | Item-funded ghost placement and observed normal robot construction |
| Silo and launch | Normal launch action, silo inventory/parts and native launch evidence implemented and unit-tested | Live silo construction, real part consumption, actual launch event and checkpoint |
| Enemy-enabled play | Charted enemy/pollution observations; one turret loaded live | Live defensive encounters, normal equipment/combat/repair controls, automated ammunition supply |

For each fixed benchmark configuration, report completed attempts/total attempts,
ticks to each verified milestone and launch, total wall time including planning,
pauses/reloads, failed batches, and human interventions. Record losses as well as
successes. Optimize repeatable completion before comparing speed across attempts.


## Production-controller implementation update

See [rocket-controller-001](knowledge/rocket-controller-001.md). Source 0.5.1 and
the Python scheduler add normal machine construction/supply, trip completion,
configured corridors, access-position alternatives, resumable private journals,
native research/launch evidence and full rocket material/oil budgeting. Relative
item cells and production-window capacity sizing are available. This replaces
the earlier claims that launch actions and all supply scheduling were missing.
Automatic map-wide layout, resource expansion, connected fluid construction,
repeated enemy survival and a live rocket remain unfinished.


## Buffered production implementation update

Controller 0.6.0 adds static prototype/port metadata, directed fluid-connection
validation, observed mining targets, ordinary powered smelting layouts and
stocked item cells. The scheduler now batches construction procurement, harvests
explicitly surveyed consumable natural sites, prioritizes power before component
production, and considers usable stock when choosing collection trips. Native
craft-rate auditing separates machine evidence from whole-factory item counts.
See [the practice report](knowledge/production-oil-001.md). This supersedes older
claims above that every power/fluid planning capability is absent; a connected
oil chain, blue-consuming research and a launch still require live proof.
