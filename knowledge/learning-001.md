# Learning opening 001 — 2026-09-09

A fresh enemy-enabled world reached powered labs, completed **Automation and
Gun turret**, and ended with one turret containing ten magazines. This was an
interactive development attempt with pauses, failed batches and three controller
upgrades. It did not establish automated science, defensive combat, Military 2,
or a repeatable competitive opening.

## Conditions and evidence

- Steam Factorio 2.0.77 on macOS ARM64, base plus controller only, game speed 1.
  Fresh seed `20260906`, default map generation/settings and enemies enabled.
  The previous conveyor experiment was closed and a separate fresh save created.
- The engineer was bound at tick 837 after introduction/setup. All gameplay used
  the fixed JSON interface. No console Lua, item grants or research grants were
  sent. Controller versions progressed from 0.2.0 through 0.3.0, 0.3.1 and 0.3.2.
- Private evidence includes the fresh-map manifest, source/settings hashes,
  planned actions, observations, all 543 engine events, upgrade checkpoints and
  a verified final ZIP/hash. The run ledger is closed and the game left paused.
- Final tick: **39,786**, or **10:49.15 game time** after the baseline. Wall time
  from baseline to checkpoint verification: **80:55.41**, including research,
  reasoning, tests, debugging and recovery. There were 43 recorded pause-setting
  operations; these are not 43 distinct pauses or a pause-duration measurement.
- Of 21 submitted batches, 14 completed, two were cancelled and five failed.
  The engine recorded 162 completed action steps from 186 planned entries.
  Two failed batches were deliberate watchdog/inventory guard tests.

Milestones below are observation times, which may be later than actual completion.
They are not optimized split times.

| Observed milestone | Elapsed game time | Elapsed wall time |
|---|---:|---:|
| Red-science recipe enabled after native lab craft | 6:44.93 | 58:55.87 |
| Automation completed | 9:22.23 | 67:19.65 |
| Gun turret completed | 10:13.50 | 69:08.06 |
| Turret verified with ten magazines | 10:35.73 | 79:55.31 |

## What worked

Three direct burner-to-furnace iron lines, one copper line and a facing coal-drill
pair supplied the opening. Rock mining supplied stone and coal; yields differed
between rocks. Crafting overlapped walking. A shoreline pump, boiler and steam
engine powered two labs, verified by lab energy and completed research.

The force produced 399 iron plates, 111 copper plates, two labs, twenty red packs
and ten magazines by the final checkpoint. Red packs were hand crafted and hand
fed to the labs. No green packs were produced. Fuel and materials still needed
manual collection and delivery; this is a bootstrap factory, not sustained G1.

One turret was placed near the iron production and loaded through normal
inventory transfers. The engineer retained two magazines and full 250/250 health.
The final charted scan found two small biters about 123–127 tiles away; it found
no spawners within the local 128-tile scan. This does not establish safety beyond
that observation. The turret has not been tested against an attack, and the
remote copper/power infrastructure is not covered by this single turret.

## Failures and adaptations

| Failure or limitation | Change and verification |
|---|---|
| Two walks oscillated near blocked service positions; one needed cancellation after a wrapper deadline | Added measurable waypoint progress and two bounded repaths. The repeated blocked goal stopped with `no_path_progress` after about 6.37 game seconds. Choosing another reachable stance remains the planner's job. |
| A lab batch lacked materials | Added ordered new-craft budgeting. Desired final stock and an additional craft are different requests: a lab already in inventory cannot pay for crafting a second lab. |
| The first lab craft did not unlock red science | Controller 0.3.1 uses the owning player's crafting adapter and retains ownership after queue completion. A second normal lab craft produced native events and unlocked the recipe. Historical-save checks had missed this fresh-progression defect. |
| Placement checks returned false at apparently valid shoreline sites | Live testing found the normal character preflight returns false while explicitly paused. All six selected power/lab placements passed when running, then built and operated. Preflight does not itself prove fluid or electrical connections. |
| Turret placement succeeded but loading failed | Crafted magazines occupied character ammunition slots, while transfers read the main inventory. Controller 0.3.2 exposes ammo state and an explicit `player_inventory` choice. Live put/take tests covered both main and ammunition slots, ending with ten magazines in the turret. |
| Reload after the final upgrade reported no bound character | Rebinding the existing connected engineer restored access with the same unit, position, main inventory and health. Record this as recovery work; automatic recovery of player-owned characters across upgrades is not established. |

The deliberate ammo-on-lab test rejected the operation without consuming items.
Additional setup/probe failures included connecting before readiness, a viewer
mod-version mismatch and an out-of-local-range placement query while moving.
They remain in private notes/traces. No failed batch was silently restarted from
its first action; completed work was inspected before recovery.

## Responsiveness after the fixes

Controller 0.3.2 was measured with the Steam viewer connected and the simulation
running at normal speed, after the engineer became idle. Each tool had 50 paired
MCP/direct-RCON samples with alternating order and five warm-ups per transport.
The benchmark recorded 635 calls with no error response or transport exception;
30 additional direct warm-ups completed but were not individually logged.
The scan used radius 64/limit 20; survey used radius 128/water limit 100.
Placement queried a furnace at the engineer's occupied position, returning false;
this measures a negative preflight, not a successful building operation.

| Tool | MCP median | MCP p95 | Direct RCON median |
|---|---:|---:|---:|
| Status | 17.47 ms | 20.21 ms | 16.10 ms |
| Engineer observation | 16.90 ms | 20.17 ms | 15.99 ms |
| Nearby scan | 26.73 ms | 34.50 ms | 16.42 ms |
| Factory | 17.54 ms | 20.32 ms | 15.63 ms |
| Water/pollution survey | 17.28 ms | 20.07 ms | 15.69 ms |
| Local placement preflight | 33.43 ms | 36.38 ms | 32.55 ms |

Engineer position, carried inventory, ammunition and health were unchanged across
the read benchmark. Factory production continued. These timings measure local
tool responses, not model decision time, rendered frame pacing, combat reactions,
or a large late-game factory. The [earlier conveyor report](responsiveness-001.md)
contains separate cancellation and large-batch measurements on controller 0.2.0.

## Validation and next experiment

All 36 unit tests passed, including real Lua execution for navigation, charted
observation boundaries, player crafting and inventory routing. The isolated
historical reload/MCP check also passed with controller 0.3.2 and 15 tools,
preserving its source checkpoint hash, tick, position and inventory. Historical
compatibility remains separate from fresh gameplay evidence.

The next attempt should use 0.3.2 from its initial baseline. First establish
reliable fuel, plates and automatic red/green delivery to powered labs; complete
Military 2 through actual lab consumption. Budget a larger ammunition reserve,
observe pollution and enemy approaches, and add normal repair/combat controls
before depending on unattended defense. Use the [strategy playbook](strategy.md)
to define conditions and pass/fail evidence for each experiment.
