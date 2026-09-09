# Speedrun preparation — 2026-09-09

Start with a repeatable early-game segment through **Military 2**, then extend
the route toward a rocket. Connection latency is already small relative to
travel, production and planning. The immediate work is to keep machines supplied,
build from complete material budgets, and recover without repeating completed
actions. This is an agent-controlled practice route under [POLICY.md](../POLICY.md).

## What to learn from strong players

The [Speedrun.com study](speedrun-study.md) distinguishes the current categories
and version-matched runs from older guides. Continue studying
[Zaspar's 2.0.77 Default Settings run](https://www.speedrun.com/factorio/runs/yvk04e8m)
for sequencing and local decisions. Its human-run time is a reference, not an
eligibility or performance claim for this mod-controlled agent.

[Phredward's guide using AntiElitz's design](https://www.speedrun.com/factorio/guides/li2kd)
emphasizes adapting the layout to resources, checking working builds, supplying
buffers and handling enemies periodically. Apply those principles, but recompute
recipes and prerequisites from the pinned 2.0.77 catalog. The guide's old research
order and practice map suggestions are not the current category rules.

Our experiments should prioritize:

1. **Combine trips.** Collect metal, refuel and queue available crafts along the
   same route. Keep construction reserves separate from science ingredients.
2. **Start useful production early.** Power, configure, feed and check each small
   block before expanding it. Inspect inserter pickup/drop positions and actual
   lab inputs; an assembled layout alone is insufficient evidence.
3. **Use stock readiness, not queue submission, as a dependency.** Wait for the
   specific required item count before a transfer or placement. A `craft` action
   only queues work. `wait_inventory` without entity coordinates can wait for
   main-inventory stock; `await_craft` waits for the whole queue.
4. **Budget time away.** Leave enough fuel, ingredients, ammunition and remaining
   ore for the planned trip plus a stated margin. Recheck after expanding load.
5. **Measure production deltas.** A fueled drill can have exhausted its tiny ore
   footprint. Detect stalled output before adding downstream science capacity.

## Checkpoint rehearsal: observed once

A new ledger continued the earlier enemy-enabled learning checkpoint using
controller 0.3.2 throughout. This was not a fresh opening or an uninterrupted
speedrun. All actions used the fixed interface, at normal speed and normal costs.

| Check | Result |
|---|---|
| Combined collection, refueling and crafting | 24 actions completed in 34.80 game seconds; 32.83 seconds of walking overlapped queued crafting |
| Automatic science | Two assembler-1 machines fed two powered labs through correctly oriented, powered inserters |
| Sampled output | 24 red packs in 124.15 game seconds: **11.60 packs/minute**, versus nominal capacity 12 |
| Research | Electric mining drill completed through the labs; its recipe was then observed enabled |
| Time to research completion observation | **2:53.75 game / 5:31.65 wall** from this continuation's baseline, including planning and practice pauses |
| Input supply | Hand-crafted gears and manually supplied copper buffers; no continuous input-delivery claim |
| Failure retained | One batch attempted a gear transfer before queued gears finished; recovery waited for crafting and resumed at the unfinished work |
| Depletion recovery | One iron drill had no ore left in its 2×2 area; normally mined and relocated the drill/furnace onto charted ore, then verified new plate output |

The collection timing is one observation of overlap, not a measured improvement
against a matched control. The throughput window includes discrete production
and polling boundaries. Research timing is its first observation; exact
research-completion event capture is still missing.

The complete rehearsal, including the depletion diagnosis and recovery, has seven
batches: six completed and one failed, with 63 completed actions out of 69 planned
actions across those batches. Twenty explicit pause transitions are retained.
There were no reloads or controller upgrades. The earlier electric-mining
checkpoint remains preserved alongside the final recovery checkpoint. Raw
observations, event sequences, source identity and verified save hashes stay in
ignored runtime storage.

Thirty red packs were produced automatically in total by the end of the
continuation. No green science was produced and **G1/G2 remain incomplete**.
There was no observed damage or defensive encounter. One loaded turret does not
establish protection for the remote power/science and copper sites.

## Size the factory before adding science

Use the new read-only calculator:

```sh
python3 -m client.capacity --red 2 --green 0 --iron-per-minute 45 --copper-per-minute 15
python3 -m client.capacity --red 2 --green 1 --iron-per-minute 45 --copper-per-minute 15
python3 -m client.capacity --red 4 --green 2 --iron-per-minute 105 --copper-per-minute 45
```

| Science assemblers | Nominal red/green per minute | Iron plates/minute | Copper plates/minute |
|---|---:|---:|---:|
| 2 red | 12 / 0 | 24 | 12 |
| 2 red, 1 green | 12 / 5 | 51.5 | 19.5 |
| 4 red, 2 green | 24 / 10 | 103 | 39 |

These demands include gears, circuits, cables, inserters and belts inside the
science recipes. They exclude construction, defense, transport capacity and the
machines that make intermediates. Use measured supply or a clearly declared
capacity assumption for the supply arguments. Three burner-fed iron lines and
one copper line have theoretical capacities of 45 and 15 plates/minute, but the
rehearsal's depleted drill temporarily reduced the iron ceiling to 30.

For a three-minute absence with 25% extra time, reserve **9 coal per burner drill
and 6 per stone furnace**, calculated independently at full rated draw. These are
target whole-item inventories, not amounts to add blindly. Subtract existing
whole fuel items. Boiler reserves must use the expected network load or a
conservative rated draw and account for inventory/refill capacity.

The calculation uses assembler-1 speed 0.5, burner drill speed 0.25, 150 kW drill
draw, 90 kW furnace draw and coal at 4 MJ. The pinned recipes provide crafting
times and ingredient quantities. Sources checked on 2026-09-09:
[assembler](https://wiki.factorio.com/Assembling_machine_1),
[burner drill](https://wiki.factorio.com/Burner_mining_drill),
[furnace](https://wiki.factorio.com/Stone_furnace),
[coal](https://wiki.factorio.com/Coal).

## Next route and readiness gates

1. **Fresh bootstrap:** rock resources, self-feeding coal pair, useful iron/copper
   smelting, power and native lab craft. Choose drills by visible ore coverage and
   lifetime, not only proximity. Record a new save and manifest before acting.
2. **Small red block:** Automation, loaded defenses as needed, electric mining and
   Logistics. Start a supplied two-red block while expanding extraction, smelting
   and the power network. Automate gears and fuel delivery before spending the
   remaining iron on additional science machines.
3. **Green and defense:** complete Steel processing, Military and logistic-science
   prerequisites; supply green assemblers, maintain ammunition and check the
   charted pollution/approach area. Pass G1 only with powered red/green production,
   supplied labs and stated reserves. Pass G2 only when Military 2 is completed.
4. **Oil and blue:** establish oil extraction, refining, plastics, sulfur/acid and
   advanced circuits. Verify native oil-trigger progression and fluid connections
   before assuming the static technology plan is executable. Complete research
   consuming blue science, with a separate military-science demonstration.
5. **Robotics and later science:** validate normal robot construction, then build
   production/utility science and the silo supply chain. Start long-lead steel,
   circuits, modules and rocket ingredients according to their measured deficits;
   avoid unlimited buffers that consume the next milestone's materials.
6. **Launch:** implement and test narrow silo/launch controls, consume real rocket
   ingredients and record an actual launch event. Silo research alone is not a win.

The existing dependency planner can estimate the full research workload:

```sh
python3 -m client.progression rocket-silo military-2 gun-turret electric-mining-drill construction-robotics
```

With the pinned catalog, this declared target set needs 6,125 red, 5,905 green,
3,450 blue, 1,600 purple and 1,000 yellow packs before lab-productivity savings.
It excludes optional military-science research and other optional upgrades.
Trigger items and the factory/rocket materials are additional requirements.
The returned dependency order is not an optimized schedule, and fluid material
planning is intentionally unavailable. Do not use old rocket-control-unit
recipes or Space Age rocket costs for this base-game route.

## First timed test protocol

Prepare a fixed-seed, default-enemy, base-2.0.77 **tool-assisted** benchmark.
Declare that the layout is known from practice. Use the same seed, source/mod
hashes, initial save and prepared route for comparisons. A later random-map test
must acquire its own charted knowledge.

The first scored segment ends at Military 2, not rocket launch. Before scoring,
demonstrate the whole segment once in practice, including sustained inputs and
enemy handling. The current checkpoint has not yet passed that gate.

Start wall timing immediately before first resume and tick timing from the
paused baseline. Count all subsequent observation, decision, execution and
recovery time. A pause, reload, manual game input or source change makes that
attempt an interrupted practice attempt; preserve its time and failure reason.
Keep earlier work and reconcile job IDs after uncertainty. A client deadline
does not itself cancel a game job.

For each variant, run at least three independent attempts before drawing a speed
conclusion. Report completed/attempted runs, median/range of completion times,
milestone splits, failed batches, recoveries, pauses/reloads, starvation windows,
damage and ammunition use. Change one strategy at a time. First compare combined
service trips; then construction activation order and reserve sizing. Optimize
the measured bottleneck after repeatable completion.
