# Persistent factory plans

The scheduler consumes a private, versioned JSON plan describing surveyed sites.
Keep real map coordinates and run output under ignored `runtime/`. It controls
an already running, bound engineer with controller 0.6.0, base 2.0.77, normal
speed and local defense enabled. It does not create a fresh factory by itself.

```sh
python3 -m client.rocket_plan --minutes 120 > runtime/rocket-budget.json
python3 -m client.layouts automation-science-pack --prefix red > runtime/red-cell.json
python3 -m client.autopilot --plan runtime/factory-plan.json --output runtime/runs/example --seconds 600
```

Use `--resume` with the same plan and output directory after inspecting an
interruption. The journal reconciles any pending ID before choosing new work.
A changed layout or target requires a new plan/journal; preserve its predecessor.
Do not run a second action executor against the same engineer.

The plan object contains:

- `version: 1`, `target`: a finite catalog technology, `"rocket"`, or
  `"infrastructure"`. Infrastructure completion proves that every requested
  building exists and belts have the requested direction/endpoint type. It does
  not prove power, item flow, throughput or a research milestone.
- Optional `construction_batch_size` (1–20, default 1) procures several missing
  structures of the same kind per trip, counting only unlocked planned sites.
- `sites`: unique `id`, `entity`, `position: {x, y}` and `stand: {x, y}`.
  Optional `build`, `direction`, `recipe`, `requires` (technology names),
  `fuel_min`, `fuel_target`, `ammo_min`, `ammo_target`.
  A normal underground-belt site may include `belt_type: "input" | "output"`;
  these plans require controller 0.7.0. The fixed action uses normal placement,
  actual inventory costs and native underground pairing limits.
- Optional `input_site`/`output_site` on a recipe machine refer to configured
  chest sites. Optional `input_inserter`/`output_inserter` references let normal
  direct machine transfers bootstrap production until those arms exist.
  `batch_size` (1–100 crafts) sizes recipe buffers; replenishment begins below
  half that level instead of replacing each consumed item. The generated item cell
  includes the intervening inserters.
- `sources`: `site`, `inventory` (`output`, `fuel`, or `chest`), `item`, and an
  optional nonnegative `reserve`. Reserve coal in opposing coal drills.
- `engineer_ammo_reserve`: full-magazine-count replenishment threshold.
  Native stack transfers preserve a partially used magazine; count thresholds
  are not exact remaining-round forecasts.
- Optional `corridors`: `nodes` mapping names to positions and `edges` containing
  pairs of node names. These must describe observed, suitable travel corridors.
  The graph guides the normal game pathfinder; it does not certify safety.

Structures without recipes are built before production demand, subject to their
`requires` gates. Power poles precede chests, then other structures, to prevent
assembler/inserter startup cycles. Recipe machines are constructed on demand;
`eager: true` requests their construction with infrastructure.

A chest can declare `stock_min` and `stock_target` item/count maps for fuel or
other supplies. An `external_inputs: true` recipe site waits for its native
inserters instead of receiving direct ingredient deliveries.

A previously surveyed tree/rock site may declare `gather: "wood"` (or its real
mined product), without `build`. The scheduler walks, confirms the named entity
locally, and mines normally. Its completed or confirmed-absent site is recorded
as consumed. This is for consumable natural entities, not a renewable ore node.

Recipe ingredients are supplied from existing output, recursively configured production cells, or
normal hand crafting of unlocked solid recipes. Machines still need adequate
power, mining inputs and connected fluids; placement alone does not prove these.

The controller checks milestones from actual research state and launch events.

`client.belt_routes.belt_route` expands explicitly selected cardinal waypoints
into a directed surface route. Nearby stocked surface-belt placements are
batched, with native local preflight for every tile before submission.
`underground_pair` creates two endpoints within a caller-supplied native span;
verify reciprocal native neighbour IDs and actual flow after placement.

`clear_belt_trees: true` permits normal mining of a locally scanned neutral tree
whose observed bounds intersect a blocked surface-belt footprint. It does not
remove structures, wrecks or hidden entities. Each clearing job is journaled and
the next placement is reobserved. Other obstructions stop construction.

The scheduler queues handcrafting without an explicit await action and may
approach the next building while its item crafts. It still checks inventory at
arrival. Corridor destinations and interpolated waypoints avoid newly observed
factory footprints; this remains a heuristic over native pathfinding.

`client.layouts.smelting_block` supplies opposing 12-by-2 and 24-by-2 furnace
templates with one central output belt. These templates require surveyed space,
separate ore/coal input lanes, power and a live throughput test.
Raw factory snapshots and source hashes are evidence, not a tamper-proof replay.
The process duration includes planning and observation work. Ending the Python
process leaves the game and any submitted job running; save and stop the server
when ending a practice session.


`client.fluid_routes.pipe_route` converts explicitly surveyed tile sets and
verified fluid endpoints into item-funded surface-pipe sites. Existing pipe
reservations prevent crossings or side contact with another fluid. It cannot
infer machine ports or route through unknown terrain. Its output still needs
native placement checks and an observed flow test; no live oil chain has passed.


`client.layouts.smelting_cell` plans an electric drill feeding a mixed ore/fuel
chest, normal inserters, a stone furnace and an output chest. Check real ore
coverage, collision, every inserter port and powered operation.
`client.layouts.pole_line` spaces ordinary small poles within their wire reach;
its endpoints, all terrain and local stances still require validation.

Controller 0.6.0's read-only `prototype` operation supplies static port geometry.
`client.fluid_ports.recipe_ports` maps pinned recipe input/output slot numbers
to those ports and rotates them with the machine. Native factory observations
include fluid segment IDs, fluid locks, mining targets and completed-craft
counters. Matching segments establish a connection, not sufficient throughput.

Use `python3 -m client.production_audit runtime/before.json runtime/after.json`
for observed production deltas over a measured game-time interval. Snapshots
must belong to the same world; whole-factory item counters may include hand
crafting, while unchanged machine identities/recipes expose native craft rates.

Output-only fluid boxes may have no segment ID. Use `fluid_path` to validate
reciprocal native ports and permitted flow direction across such boundaries.

Material collection estimates travel per usable stock, so a nearly empty nearest
furnace does not monopolize pickups. A currently producing machine can accumulate
a small usable batch before collection; science uses a smaller threshold. These
are bounded scheduling heuristics, not an optimal route or throughput guarantee.

Service stances also exclude conservative collision bounds for nearby neutral
obstacles returned by a bounded charted scan. Static geometry is fetched through
the fixed `prototype` operation and cached. The scan refreshes after movement
or ten game seconds. This does not certify a route: a truncated scan can omit
obstacles, and neutral geometry outside that local sample remains unknown.

Optional `local_transfer_radius` accepts 0 through 3 tiles, default 0. For an
observed existing inventory within that radius, the planner can put/take from
its current position instead of first walking to the configured stance. Normal
game reach checks still apply; after a reach/approach failure the planner uses
stance-based navigation for that site. This does not affect mining or building.

Lab supplies prioritize the scarcest required colour across the configured labs.
Available intermediate pickups are batched to reduce repeated collection trips.
Neither policy guarantees continuous research without connected ingredient flow.

`defense_stations` lists configured gun-turret site IDs. With stations configured,
owned-building health is sampled even during a pending job. New damage interrupts
production and dispatches to a loaded station within 36 tiles of the damage.
An uncovered alarm holds normal scheduling and is logged. Use `target: defense`
for a persistent watch, or `watch_after_target: true` to retain monitoring after
the normal milestone. Process deadlines still apply. See the
[failure and limits](../knowledge/factory-defense-001.md); polling is not a native
destruction-event feed. Keep exactly one executor during any plan handoff.

With `defense_stations` configured, a blocked placement suspends production
instead of stopping the scheduler. The journal records the rejected action;
no part of its preflighted batch is submitted. Damage monitoring, defense dispatch
and fuel/ammunition maintenance continue. Resuming that same journal retains the
suspension. Prepare a corrected plan and a new journal, preserving the previous
record, before resuming construction. This handles a definite blocked footprint;
transport uncertainty and other fatal errors still stop the process.

Fuel and ammunition maintenance retain priority over construction. Optional
production-buffer refills follow construction selection, so a hungry distant
buffer cannot preempt every build; when a needed construction component is
unavailable, upstream buffer feeding can still unblock it.
