# Persistent factory controller and rocket planning

This development cycle adds a deterministic production scheduler, a complete
base-game research/material budget, and a normal rocket launch operation. It is
still a controller under development, not an unattended rocket or speedrun result.

## Execution

The Python scheduler owns one persistent RCON connection and polls at a nominal
100 ms interval. The existing mod reflex owns emergency shooting and movement
on game ticks; Qwen advice remains outside the action path. No model weights
were trained. The scheduler constructs configured machines, makes ordinary
hand crafts, replenishes fuel and science, collects real output, selects
prerequisite research and checks actual completion.

Travel finishes before transfer quantities are recalculated. A persistent
service intent keeps the purpose of a trip from changing on arrival. Travel
corridors use configured, observed waypoints; alternative access positions
avoid observed factory collision boxes. These are bounded recovery measures,
not complete navigation or terrain planning. Placement preflight rejects a
blocked configured footprint before spending an item.

Each run writes private observations, intentions, outcomes, source hashes and
resume state under ignored runtime storage. An intention is durable before
submission. An uncertain reply retains that exact job ID for reconciliation;
it is never automatically resubmitted. A restart requires the same plan hash.
Repeated failures and access-position retries survive process restarts. An
explicitly corrected plan starts a new journal, preserving earlier failures.
A process deadline does not pause the game or cancel an outstanding game job.

Controller 0.5.1 keeps 256 recent full jobs plus up to 65,536 compact receipts.
Receipts retain the exact action fingerprint, outcome, timing and metrics, so
an old ID cannot silently become new work. Hitting the receipt limit fails
closed. The private event stream retains detailed execution records beyond
the bounded in-save event ring.

## Rocket coverage

`python3 -m client.rocket_plan` expands the pinned 2.0.77 prerequisites and all
five required science tiers, one silo and 100 rocket parts. It balances advanced
oil co-products and cracking together, then independently checks conservation
of every selected material. The optional satellite is excluded by default.
Infrastructure must be supplied explicitly; fuel, power, mining, logistics,
travel and defense remain outside this material total.

`--minutes 120 --utilization 0.8` sizes dedicated recipe cells against an assumed
production window. This is not a two-hour completion prediction: unlock delays
shorten the available windows, and the utilization input is an assumption.
No productivity bonuses are credited.

Relative item-only assembly cells include input/output chests, inserters and
power poles. They must pass native placement checks and receive real materials
and power. Fluid ingredients are never inserted directly: the scheduler can
request a configured upstream producer, but real pipe connectivity, extraction
and by-product capacity must work in the game. A bounded surface-pipe router avoids blocked tiles and contact with other
reserved fluids. Machine-port discovery, integrated fluid layout and resource
expansion are not implemented; the pipe router is unit-tested only.

The silo action checks ownership and reach and calls the game's normal launch
method. A successful order does not count as a launch. The milestone evaluator
requires a later native launch event; research events distinguish native
completion from script completion. Launch gating/evidence and basic silo/upstream construction scheduling are
unit-tested. Later-science production and a live rocket test remain unvalidated.

## Live practice findings

The practice continued a privately preserved checkpoint; it was not a fresh
baseline. Controller 0.5.0 successfully moved partially used ammunition into the
engineer's inventory and back using native stack transfers, preserving the
partial magazine. This replaces 0.4.1's temporary rejection safeguard.

The scheduler survived two biter interruptions, resumed work, built science
machines and supplied red packs to a lab. Early failures included inaccessible
service positions, crash-site wreckage occupying a planned assembler footprint,
a route near enemies, repeated fuel detours, and the old 256-job submission
limit. Corrected access positions, surveyed corridors, bulk pickups, buffered
fuel priorities and persistent trip intent address those specific failures.
All earlier journals remain private and intact. A saved checkpoint and a mod
restart were required to install the history fix; this is development practice,
not uninterrupted benchmark timing.

The practice completed Steel processing, the green-science unlock and Military 2
through native lab research. It produced 180 additional red packs and 22 green
packs. The final factory has three red assemblers, one green assembler and two
labs. Intermediates are still hand-crafted by the scheduler, and inventory
transfers still carry much of the material flow.

Military 2 completed after **42:18 game time / 47:23 wall time** from the private
practice baseline. These timings include development and recovery; they are
not a fresh-map or competitive result. Across four journal phases there were
820 submission intentions: 810 completed jobs, seven failed jobs, two defense
cancellations and one rejected submission at the old history limit. Four Python
restarts applied fixes; one saved server/mod restart installed 0.5.1. Earlier
failed plans were preserved. The final phase completed all 592 submitted jobs
without an execution failure, with one of those Python restarts during the phase.

Five new damage events reduced health to 234/250; the engineer recovered
naturally to 250/250, with no new death. The observed pause counter did not
increase. Startup waits and the mod restart remain in the record. A previous
job's compact receipt was retrieved successfully after exceeding the old job
limit. The final checkpoint archive and its private SHA-256 were verified;
the server and viewer are stopped.

All **81 unit tests** pass with the MCP dependencies installed. The standard
library run skips optional MCP tests. Tests cover material/oil conservation,
capacity sizing, resume/replay behavior, trip completion, parallel producer
supply, pipe separation, native stack transfers, research/launch evidence and
1,200 retained job identities. These do not substitute for live later-science,
fluid-connectivity or rocket validation.

## Remaining validation

- Repeat the supplied red/green and Military 2 segment from a fresh map.
- Replace hand-crafted intermediates and long trips with measured automatic
  mining, smelting, belts, inserters and adequate production buffers.
- Build and measure oil extraction, connected fluids, cracking, plastic,
  sulfur, acid, lubricant and every required later science tier.
- Demonstrate silo construction, normal part consumption and a launch event.
- Run repeated enemy-enabled trials with declared settings; report failures,
  pauses/reloads, interventions, wall time and game time as well as successes.
