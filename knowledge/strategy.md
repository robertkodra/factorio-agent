# Gameplay strategy and evidence

Scope: base Factorio **2.0.77**, normal mechanics, enemies enabled, one engineer.
Last source review: **2026-09-09**. This is a working playbook, not a proven
rocket route. Use the installed catalog for costs and the live world for state.

## What to learn from experienced players

The [Speedrun.com study](speedrun-study.md) adds current category rules, a
version-matched Default Settings reference, and five proposed experiments.
Use its distinction between random-map real-time runs and fixed-map practice
when interpreting comparisons. It also identifies which videos and guides were
actually inspected, and which remain study candidates.

[Nefrums' beginner speedrun guide](https://docs.google.com/presentation/d/1XgyTdHzQM1cQrv1YpZJuRGtMv6AE9j4h6Phdn4Fe8-c/edit)
was read through its public text export. Its useful principles are to expand
mining before the next consuming build, feed production directly where practical,
keep hand crafting active during travel, buffer slow intermediates, and inspect
each completed build before leaving it. These are candidates for our planner.

Its suggested map has very rich resources, maximum starting area, and pollution
diffusion set to zero. Its research list includes rocket control units and older
unlock ordering. Therefore neither its defense assumptions nor its exact shopping
lists transfer to our default-settings 2.0.77 attempt. We have not replayed its
complete route, inspected every illustrated layout, or verified a current record.

The [official quick-start guide](https://wiki.factorio.com/Tutorial:Quick_start_guide)
supplies the basic sequence: resources, smelting, power, automation and research.
Our implementation must also check machine recipes, orientation, power, actual
input delivery, output space and lab consumption. A placed building is not proof
of a working production chain.

## Enemy model

On our base-game world, plan for biters, spitters and worms. Enemy expansion can
create new nests; a once-clear route can become unsafe. Evolution increases with
time, pollution production and nest destruction. Killing nests is a strategic
tradeoff, not a universal solution.
[Enemy mechanics](https://wiki.factorio.com/Enemies).

Pollution reaching nests supports attack groups. Trees and terrain absorb some
of the cloud, but this does not undo the evolution contribution of pollution
already produced. Reducing unnecessary production and protecting the approaches
to polluting infrastructure are separate tasks.
[Pollution mechanics](https://wiki.factorio.com/Pollution).

Gun turrets require magazines and can work without electricity; inserters can
refill them. A turret without ammunition is not a defense. Overlapping coverage,
ammunition reserves and replacement capacity are our proposed early defense.
[Gun turret mechanics](https://wiki.factorio.com/Gun_turret).

Current observation limits: `scan` covers at most 128 tiles around the engineer,
and only charted chunks. Zero nearby results does **not** establish world safety.
Controller 0.3.0 adds charted pollution queries, enemy force/health in scans and
explicit turret-ammo access. Controller 0.3.2 also observes the engineer's ammo
slots and allows explicit transfers from them. We still need threat response, normal equipment/
repair/combat actions and a live defensive encounter before claiming enemy
readiness. Do not compensate by revealing the map or spawning targets.

## Opening to test

1. Record the fresh map, settings, source identity, starting inventory and ticks.
   Scout accessible rock, coal, iron, copper, water and visible threats.
2. Use rock products to start direct iron smelting. Reinvest early plates in
   additional miners and furnaces; establish a facing coal-drill pair and copper
   production. Reserve fuel before crafting discretionary machines.
3. Complete production-triggered unlocks through real production. Build steam
   power and a lab, then research Automation. Bootstrap science with hand feeding
   while establishing continuous plate and coal supply.
4. Budget science, expansion **and defense** together. Research Gun turret and
   allocate magazines before growing beyond the area we can inspect and defend.
5. Move bulk work to electric mining, smelting arrays and a small construction
   supply area. Expand power and fuel alongside demand. Connect automated red and
   green packs to supplied labs; complete Military 2 through those labs.

Order is conditional: a local threat can make defense the immediate next task;
an empty fuel buffer can take priority over research. Numeric reserve thresholds
must be calibrated from consumption and travel time, not treated as game rules.

## Decision loop

Observe → identify the limiting supply or risk → budget a short batch → execute
while existing machines work → verify the intended change → update the record.

- Priorities: survive, preserve fuel/power, restore stalled production, expand
  the current bottleneck, then spend surplus on the next milestone.
- Before a batch: check unlocks, available items, a service stance, full building
  footprints, intended connections, and a recovery route.
- During a batch: watch progress, damage, fuel and research; cancel stalled work
  explicitly. Reconcile an uncertain submission by its original job ID.
- After a batch: verify production deltas and inventories, not just placement
  counts. Separate nominal recipe capacity from measured sustained output.
- Practice pauses, failed jobs, operator adaptations and reloads remain recorded.
  A successful checkpoint becomes a regression fixture, not evidence of a faster
  fresh run.

## How knowledge graduates

Use four statuses: **sourced**, **hypothesis**, **observed once**, **reproduced**.
Every strategy entry needs its conditions, expected benefit, failure conditions,
source or run reference, and next falsifiable test. Record counterexamples beside
successes. Only promote a strategy after the cited experiment passes; mark it
stale when the game/mod version or map/enemy settings change.

Keep reviewed principles and aggregate run reports here. Keep exact coordinates,
saves, raw observations and machine/player details in ignored `runtime/runs/`.
The private archive remains historical evidence; its old Git history never enters
this public repository.

The [first learning attempt](learning-001.md) provides observed-once evidence for
the mining/coal/power opening, native research unlock and one loaded turret. It
also records failed navigation, budgeting, crafting and inventory assumptions.
Combat and sustained automatic science have not graduated beyond planned work.

## Research and defense budget

```sh
python3 -m client.progression automation gun-turret electric-mining-drill logistics military-2 --supplies '{"gun-turret":2,"firearm-magazine":40}'
```

This pinned-catalog calculation requires 220 red and 20 green packs, including
prerequisites. Those packs plus two turrets and forty magazines require 790 iron
and 270 copper plates. It excludes infrastructure, fuel and production-trigger
items unless supplied explicitly. Dependency order is not a travel/production
schedule. Use live inventory with `client.materials.craft_budget` for ordered new
crafts; `budget` instead estimates desired final stock and credits existing
products. Total production is not material currently in the engineer's inventory.
Check `research_state.enabled_recipes` separately. Oil/fluid production chains
are outside this material model.
