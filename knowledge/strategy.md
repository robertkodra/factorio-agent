# Gameplay strategy and evidence

Scope: base Factorio **2.0.77**, normal mechanics, enemies enabled, one engineer.
Last source review: **2026-09-10**. This is a working playbook, not a proven
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

The experienced-player feedback from the current practice changes our priority:
bootstrap abundant plates quickly with hand-fed burner mining and smelting,
then use assemblers for gears, circuits and construction supplies before paying
for long transport runs. The current checkpoint retrofit is a development
exercise, not the intended fresh-map opening. Do not copy its long empty belts
and repeated cross-factory supply trips into the opening route.

Reserve the eventual iron, copper and steel corridors before filling the space
with temporary cells. Start an expandable 12-by-2 furnace block when ore,
construction supplies, fuel and power can support it; expand or upgrade according
to measured demand. Leave room for additional iron lines, copper and later steel,
with branches for science and a compact construction supply area. Two or three
iron lines and one copper line are planning options, not a demonstrated optimal
rocket factory. Defense and engineer access must fit the same layout.

At normal quality without bonuses, 24 stone furnaces nominally produce 7.5
iron/copper plates per second; 48 produce 15. Upgrading the 24 to steel furnaces
raises nominal output to 15, the capacity of a yellow belt. These are calculated
capacities assuming both output lanes, ore, fuel and power are adequately
supplied, not measured output from this agent.
[Furnace rates](https://wiki.factorio.com/Stone_furnace),
[steel furnace](https://wiki.factorio.com/Steel_furnace),
[belt capacity](https://wiki.factorio.com/Transport_belt).

The layout library now contains opposing 12-by-2 and 24-by-2 templates. Their
geometry is unit-tested; these full blocks have not yet passed a live run.
The smaller eight-furnace row is the current integration fixture.

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

Factory-wide damage must preempt production even when the engineer is healthy.
The [remote-attack failure](factory-defense-001.md) demonstrates why a quiet local
reflex is insufficient. Keep a continuous watch during planning and between
production phases, and place loaded defenses along vulnerable supply approaches.

### Early combat study

The user's SMG, grenade and kiting advice agrees with the historical
[Phredward / AntiElitz default-settings guide](https://www.speedrun.com/factorio/guides/li2kd).
Its cached slide text explicitly calls for turret/grenade fighting, a grenade
assembler after Military 2, and carrying combat supplies when establishing oil.
It later mentions car and landmine tactics. This supports studying those tools;
it does not prove that the old route is optimal under 2.0.77.

An ordinary grenade kills small biters in one hit. Medium enemies need more
damage, so do not use enemy colour alone as a throw policy. Test grouping,
minimum separation, escape space and nearby factory exposure before releasing a
grenade. Normal grenade use and this kiting controller are not implemented yet.
[Grenade mechanics](https://wiki.factorio.com/Grenade),
[enemy health and resistance](https://wiki.factorio.com/Enemies).

Flamethrower turrets can use crude oil directly, but need a working pipe supply
and suitable coverage for their firing arc and minimum range. Compare their
complete setup cost and avoided losses against gun/ammunition upgrades and
lasers; do not assume that lasers are the required response to big biters.
[Flamethrower turret](https://wiki.factorio.com/Flamethrower_turret).

The refreshed closest reference is [Zaspar's Default Settings 1:59:01 on 2.0.77](https://www.speedrun.com/factorio/runs/yvk04e8m).
Its run metadata is verified; the full combat segments have not been reviewed.

### Execution

Keep the local executor responsible for routine construction and supply while
the strategic planner thinks. Queue normal handcrafting without holding the
engineer in an explicit await job, and approach the next site while its item is
being crafted. At arrival, recheck native stock; do not oscillate between nearby
unfinished sites. Belt batches must preflight every included tile before any
placement is submitted. On an observed tree obstruction, a configured belt plan
may normally mine that tree and reobserve; other obstructions need correction.

Measure the full distribution of time between jobs, including process downtime,
recovery and interventions. A low median hides long stalls. Report idle time and
long-tail gaps separately from walking, crafting and build execution time with
`client.cadence`. Do not call native execution time model inference latency.

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
