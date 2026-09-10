# Persistent factory plans

The scheduler consumes a private, versioned JSON plan describing surveyed sites.
Keep real map coordinates and run output under ignored `runtime/`. It controls
an already running, bound engineer with controller 0.5.1, base 2.0.77, normal
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

- `version: 1`, `target: "military-2"` or `"rocket"`.
- `sites`: unique `id`, `entity`, `position: {x, y}` and `stand: {x, y}`.
  Optional `build`, `direction`, `recipe`, `requires` (technology names),
  `fuel_min`, `fuel_target`, `ammo_min`, `ammo_target`.
- Optional `input_site`/`output_site` on a recipe machine refer to configured
  chest sites. The generated item cell includes the intervening inserters.
- `sources`: `site`, `inventory` (`output`, `fuel`, or `chest`), `item`, and an
  optional nonnegative `reserve`. Reserve coal in opposing coal drills.
- `engineer_ammo_reserve`: full-magazine-count replenishment threshold.
  Native stack transfers preserve a partially used magazine; count thresholds
  are not exact remaining-round forecasts.
- Optional `corridors`: `nodes` mapping names to positions and `edges` containing
  pairs of node names. These must describe observed, suitable travel corridors.
  The graph guides the normal game pathfinder; it does not certify safety.

Structures without recipes are built before production demand, subject to their
`requires` gates. Recipe machines are constructed on demand. Their ingredients
are supplied from existing output, recursively configured production cells, or
normal hand crafting of unlocked solid recipes. Machines still need adequate
power, mining inputs and connected fluids; placement alone does not prove these.

The controller checks milestones from actual research state and launch events.
Raw factory snapshots and source hashes are evidence, not a tamper-proof replay.
The process duration includes planning and observation work. Ending the Python
process leaves the game and any submitted job running; save and stop the server
when ending a practice session.


`client.fluid_routes.pipe_route` converts explicitly surveyed tile sets and
verified fluid endpoints into item-funded surface-pipe sites. Existing pipe
reservations prevent crossings or side contact with another fluid. It cannot
infer machine ports or route through unknown terrain. Its output still needs
native placement checks and an observed flow test; no live oil chain has passed.
