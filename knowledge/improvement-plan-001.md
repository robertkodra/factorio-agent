# From checkpoint practice to a reliable rocket controller

Reviewed 2026-09-10. The game remains paused at the user's request. This is an
analysis and implementation proposal, not a claim that the proposed controller,
factory or benchmark has passed. It extends the
[session retrospective](session-retrospective-001.md) with a fresh journal audit,
inventory accounting and primary speedrunning references.

## The central diagnosis

We have demonstrated useful individual capabilities, but have not coordinated
them into a reliable production schedule. Faster decisions help only when the
next action is useful, supplied and safe. The current factory is a collection
of repaired development fixtures, not the opening we should reproduce.

The improvement should be a hybrid: continuous native emergency handling, one
persistent action executor, a scheduler that understands material flow and
deadlines, and asynchronous strategic advice. Keep the existing fixed operation
boundary and normal game costs. Do not put combat behind an LLM response.

## Fresh evidence from our own run

The audit streamed reconciled job records from three selected phases, deduplicated
by job ID within each phase, and calculated native start-to-finish intervals and
the gap before the next recorded job. Percentiles use nearest rank. These are
game-time intervals, not input-to-render latency, wall-time benchmarks or a
decomposition of the whole session. Failed jobs remain included.

| Selected phase | Completed / recorded jobs | Median / p95 inter-job gap | Longest gap | Time in approach jobs / measured span |
|---|---:|---:|---:|---:|
| Balanced science supply | 68 / 70 | 0.150 / 0.283 s | 8.15 s | 169.2 / 190.1 s |
| Science lane reconstruction | 127 / 128 | 0.150 / 0.350 s | 6.22 s | 62.3 / 105.1 s |
| Final oil-research supply | 43 / 45 | 0.133 / 0.267 s | 84.97 s | 43.2 / 149.0 s |

The final phase's largest gap contained a recorded wait for an automation-science
source. Another gap lasted 13.93 seconds without an explanatory waiting record.
We must instrument the missing cause rather than label every long gap LLM time.
The balanced phase collected batches as small as one, two and three items.
Approach-job time includes any delays within those jobs; it is not independently
measured distance travelled. Nevertheless, the repeated servicing is a strong
candidate for improvement. These phases are different tasks, not an A/B speedup.

Two final-phase science transfers failed with a native negative-amount error.
The transfer helper subtracts source stack-count changes from the amount remaining;
its current tests model ammunition but not partially consumed science packs.
That identifies a regression-test gap, not a proven engine/root-cause diagnosis.
Reproduce with used science packs, filtered lab slots and multiple source stacks;
record actual partial effects and never blindly replay the failed operation.
Preserve item metadata and remaining durability as well as counts.

The final chest audit found 1,600 spare transport belts, 898 gears and 3,658 iron
plates. Belts alone embody 2,400 iron plates; the three categories together embody
7,854 iron plates. Cumulative plate production in this continued world was 15,370,
so the stored categories represent about 51 percent of that amount. This comparison
includes earlier checkpoint history and excludes items outside chests. The stock
is recoverable and not all waste, but no near-term bill of materials justified
holding this much while science required repeated servicing. A full belt chest
is an inventory ceiling, not a production target.

The earlier 203-second factory-damage-to-arrival measurement remains a serious
failure. A half-second polling configuration is not evidence that this delay has
been solved. Local survival against fourteen small biters and ammunition flowing
through three turrets are narrower achievements than defending the whole factory.

## What the speedrunner references actually support

| Source | Reviewed evidence | Implication for us |
|---|---|---|
| [Zaspar, Default Settings 1:59:01, base 2.0.77](https://www.speedrun.com/factorio/runs/yvk04e8m) | Run page refreshed; linked ZIP downloaded, integrity/hash checked; replay and initial/final state data present. Embedded preview inspected: silo, surrounding beacons, adjacent assembler rows and belt corridors. | A version-matched reference is available for studying the whole construction sequence. The end-state image alone cannot establish its opening, exact ratios, module contents or throughput. |
| [Nefrums' historical guide](https://www.speedrun.com/factorio/guides/jg8lg) | Previously saved primary slide text reread: burner production, hand-fed intermediates, first half iron line, smelting expansion, circuits, miners/inserters and limited gear chests. The [video index](https://www.youtube.com/watch?v=ExLrmK1c7tA) identifies these phases. | Your hand-fed opening is a sound candidate. Start productive small blocks, reinvest in extraction, and cap stores. Recompute old quantities and recipes for base 2.0.77; do not copy its permissive map settings into our enemy-enabled benchmark. |
| [OverCraft's Phoenix guide](https://www.speedrun.com/factorio/guides/cl454) | Author's description emphasizes limited walking, phased construction and production sized to the launch. Linked PDF not studied in this review. | Budget the next phase and group trips. A large general-purpose factory is not automatically the quickest way to one rocket. |
| [Gotyoke's historical TAS](https://github.com/gotyoke/Factorio-AnyPct-TAS) | Author describes tick-based execution and overlap with walking; explains why robots had a different cost-benefit balance for that scripted route. | Borrow prepared execution and overlap, then test robot investment for our own executor. The old fixed-map/version route does not establish an adaptive 2.0 capability. |
| [TAS Generator](https://github.com/theis999/Factorio-TAS-Generator) | README describes compiled step lists, but also fixed rock yields and unavailable construction robots. | Useful architecture reference, not a drop-in controller under our no-cheat policy. Do not adopt altered resource yields. |

The reference save remains private and unmodified. Its archive directory name
does not exactly match the time on the run page; use the verified run-page time,
not the filename, for the reference. Only archive structure and the embedded
preview were inspected; neither the full replay nor a complete factory entity
inventory has been analysed. Do not present this as a replay study already done.

For the next replay study, use a separate version-matched, base-only instance
and a copy of the file. Keep our paused world untouched. Record the opening,
first electric smelting, first simultaneous red/green consumption, oil/blue,
robots, later science and silo phases. At each phase capture machine counts,
input sources, buffer limits, walks, supply interruptions, defensive placement
and the material bill for the next phase. Align video and replay timing before
comparing splits. A saved end-state cannot tell us when a machine first worked.
Extract principles from expert maps; held-out random-map tests must acquire
their own charted knowledge.

## Proposed factory route

### 1. A productive opening before extensive transport

Use hand-fed drill/furnace cells and a repeatable service circuit. Reinvest early
iron in mining and smelting while reserving fuel, a lab/power startup and defense.
After Automation, use a small set of hand-fed assemblers for gears and cable,
then circuits. The opening ends when a funded electric production block can be
activated, not when an arbitrary burner count is reached. Compare longer burner
investment with earlier electrification on matched checkpoints.

### 2. Expandable smelting and a short distribution spine

Reserve terrain for iron expansion, copper, later steel and engineer access.
Activate a small part of the iron block immediately, then expand toward the
user's 12-by-2 arrangement. Put early circuits and construction supplies near
their plate source, with dedicated short feeds. Belt copper once the servicing
cost and production demand justify it. Do not duplicate our long retrofit routes.

At normal quality, with adequate fuel, power, ore, insertion and both belt lanes:

| Smelting arrangement | Nominal iron/copper plates per minute | Electric ore drills needed at nominal 30/min each |
|---|---:|---:|
| 8 stone furnaces | 150 | 5 |
| 24 stone furnaces, 12-by-2 | 450 | 15 |
| 48 stone furnaces, 24-by-2 | 900 | 30 |
| 24 steel furnaces | 900 | 30 |

The smaller stone block fills half a yellow belt; upgrading it to steel can fill
the whole belt, but also requires twice the ore supply. Our eight-furnace row has
only one sixth of a yellow belt's nominal output. A wider bus alone cannot fix
that. These calculations use the [furnace rates](https://wiki.factorio.com/Stone_furnace),
[steel furnace](https://wiki.factorio.com/Steel_furnace),
[belt capacity](https://wiki.factorio.com/Transport_belt) and
[drill rate](https://wiki.factorio.com/Electric_mining_drill).

### 3. A capped construction mall and balanced starter science

Use output limits derived from the next construction bill plus a reserve.
Give each item a replenishment threshold and a higher stopping threshold to
avoid one-item errands. Existing, planned and in-flight stock all count toward
the limit. Put surplus storage after critical consumers; shared chests need
explicit space allocation. Limit the chest using normal controls or add a narrow
reviewed operation if that control is missing. A planner number alone cannot
limit an unconditionally belt-fed assembler.

A candidate second-stage science block is five red and six green assembler-1s:
30 packs/minute of each, requiring 225 iron and 75 copper plates/minute for those
packs and their intermediates. A 24-stone-furnace iron block nominally leaves
225 iron/minute for expansion and defense; eight copper furnaces leave 75
copper/minute. These are calculations from the pinned capacity tool, not a
validated build. Intermediate machines, inserters, lab research duration and
power must also support the rate. Start smaller while constructing the block;
do not wait for all eleven assemblers before producing useful science.

Use direct cable-to-circuit insertion where practical. Keep red/green transport
lanes deliberate and verify actual consumption. Increase science only when
upstream capacity and the next technology's demand support it.

### 4. Plan backward from the next research and the rocket

For each phase calculate remaining science, trigger items, building materials,
fuel, ammunition and long-lead intermediates. Prioritize the chain delaying the
next completion. Bring oil extraction, engines, steel and advanced circuits
online early enough for their next consumers. Stop optional surplus production
when its remaining demand is met. Do not mechanically build two or three iron
belts, rush robots, add lasers or pursue every optional military technology:
choose each investment from measured shortages, travel savings and enemy risk.

Protect coal, power and exposed mining approaches before waiting for an attack.
Use overlapping loaded turrets and a checked retreat route. Engineer defense
needs normal grenade use, controlled firing/movement and ammunition reserves;
the current reflex is not validated against larger enemies or acid. Evaluate
flamethrowers when oil and approach geometry support them, rather than treating
them as either mandatory or irrelevant to a speed-oriented route.

## Concrete controller changes, in dependency order

| Priority | Work | Acceptance evidence |
|---|---|---|
| P0: action correctness | Reproduce the negative science transfer in `transfer.lua`; expand tests for used items, slot filters and partial effects. Add precise transfer receipts rather than relying only on requested counts. | Real before/after metadata and quantities reconcile; failure never causes a duplicate replay. A passing mock alone is insufficient. |
| P0: continuous emergency control | Add bounded owned-building damage/destruction events; sequence/overflow recovery; a production interrupt preserving the guard; distinguish user stop from emergency preemption. Keep the native reflex operating during planner delays. | Offline tests for destruction, repair between polls, simultaneous threats, duplicate events, blocked construction and disconnect; later natural-attack response measurements. |
| P1: one durable action owner | Move expensive planning outside the executor. Accept versioned, expiring plans with actor/world identity and preconditions. Reconcile jobs after transport uncertainty; a stale plan must not mutate the world. | Inject slow planning and rejected construction without losing observation/defense. User pause/stop always wins. |
| P1: factory health model | Represent drills, power, transport, inserters, buffers and consumers as connected paths. Track output deltas, starvation duration and time until fuel/input runs out. Detect missing expected entities without assuming every disappearance was an attack. | Diagnose our recorded broken coal paths, iron-filled cable chest and mixed science lane; completion requires downstream production to recover. |
| P1: inventory allocation and service scheduling | Allocate construction/science/defense reserves together. Use batch thresholds, visits covering nearby needs, craft/travel overlap and deadline-aware trip selection. Continue useful work while a source replenishes. | Fewer short pickups and approach ticks without delayed research, fuel failures or depleted ammo. Every idle interval has a recorded reason. |
| P2: validated layout compiler | Extend existing furnace/belt templates with input/output lane contracts, inserter pickup/drop geometry, power coverage, material bills, service positions and activation order. | Build each block through normal actions and observe its promised output before composing a larger factory. |
| P2: route optimization and optional model advice | Score alternatives by predicted completion time, supply margin, travel and defense exposure. Qwen may choose among validated candidates asynchronously; mandatory survival rules override it. | Compare predictions with observed splits; discard stale advice. Only then consider learned policies from demonstrations and independent evaluation runs. |

Do not describe strategy documents or prompt edits as reinforcement learning.
A useful learning record is: observed state, chosen action, reason, expected
result, actual result, time/material cost and failure. Repeated evaluation can
improve parameters and route selection without first training a new large model.

## How we decide whether we improved

Keep the existing checkpoint for supply, transfer and defense regressions. Use
a fresh map for opening comparisons. First compare one change at a time across
at least three matched pairs, alternate variant order, retain failures, then
test promising variants on additional seeds not used for tuning. Three pairs
are a screening exercise, not strong evidence of generalization.

Record wall and game time separately. Report native event-to-interruption,
event-to-first-defensive-input and arrival separately; target p95 below 250 ms
for the first defensive input, with sample count and worst case. Record ready
job scheduling delay separately from deliberate supply waits. Require a
ten-game-minute supply segment without manual inventory repairs, and show
lab-starvation duration, research progress, lost buildings and ammo use.

The first implementation bundle should fix transfer correctness and emergency
continuity, then remove unlimited stockpiles and repetitive servicing. The next
gameplay tests should establish supplied research and a reproducible opening.
After that, extend to oil/blue and later science with the same evidence standard.
The ultimate score is repeated, normal-mechanics rocket completion and its
elapsed time—not buildings placed, jobs completed or a faster model benchmark.

Exact audit outputs, the reference archive, its preview and hashes remain under
ignored runtime storage. No current game action, map load or model training was
performed as part of this analysis.
