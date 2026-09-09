# Dry run 001 — red and green science

Completed a learning run through green-science production and Logistics research. The factory produced **114 red packs and 20 green packs**, and delivered both kinds into the two labs. No research consuming green science was completed.

## Timing and scope

**31:26 game time; 32:25 wall time.** This continued the earlier conveyor test at tick 22,859; it was not a fresh-map run. It includes planning, mistakes, recovery, and live controller debugging. Game speed stayed at 1. Wall time was about 59 seconds longer because of preparation/diagnostic pauses and the restart. These are learning-run measurements, not competitive timing.

Version: Factorio 2.0.77, seed 20260906, base game plus the control-only `codex-controller` mod. Space Age, Quality, and Elevated Rails were disabled. No items, technology completions, movement-speed changes, or engineer teleports were granted. Scripted construction and structured observations make this a tool-assisted run.

| Milestone | Game elapsed | Wall elapsed |
|---|---:|---:|
| Self-feeding coal pair | 2:08 | 2:17 |
| Copper smelting | 4:41 | 4:50 |
| Electronics unlocked | 5:25 | 5:34 |
| First red pack | 14:01 | 15:00 |
| Electricity and two supplied labs | 15:35 | 16:34 |
| Automation researched | 16:28 | 17:27 |
| Two red assemblers feeding labs | 18:36 | 19:35 |
| Six-machine science campus; delivery powered | 27:14 | 28:13 |
| Green-science recipe unlocked | 27:32 | 28:31 |
| First green pack | 28:12 | 29:11 |
| Logistics researched | 31:20 | 32:19 |
| Final checkpoint | 31:26 | 32:25 |

Research and first-production timestamps are first observations, generally sampled every five seconds after the monitor started. The raw “First produced: iron-plate” entry detects pre-existing production and must not be used as a fresh-start milestone. The raw four-red-delivery entry at tick 109,749 was premature: one inserter was unpowered. The table uses the verified campus milestone at tick 120,928 instead.

## Final factory

- Two facing coal drills that fuel each other.
- Three burner-drill/stone-furnace iron lines and two copper lines.
- One offshore pump, boiler, and steam engine, with a pole route to the factory.
- Four red-science assemblers, two green-science assemblers, six output inserters, and two labs.
- Completed technologies: Steam power, Electronics, Automation science pack, Automation, Logistic science pack, and Logistics.

Science crafting and insertion into labs are automatic from supplied buffers. Fuel, metal collection, gears, and circuit ingredients still require planned batches. The final twenty green packs consist of ordinary crafted items in the machines/labs; green-consuming research was not tested. Military science, blue science, oil, robotics, and rocket production were not reached.

The boiler's final top-up was cancelled when the approach path oscillated beside a pole. It had seven coal remaining at the final checkpoint. All five metal lines had already received their fuel service. These are historical observations, not a current server status.

## What the run taught us

**Two controller defects were repaired and verified live.** A detached engineer could craft inventory items without updating normal force statistics or craft-item research triggers. Temporarily attaching the original player during hand crafting fixed gear statistics and the lab-to-red-science unlock. Exact entity selection fixed mining an overlapping tree. These changes are in the installed client mod and server source.

**Planning and navigation are the larger remaining bottlenecks.** We encountered tree/pole oscillation, insufficient approach distance, construction collisions, an omitted belt footprint, a missing inserter power connection, and a material shortfall caused by assuming three rather than five gears per assembler. We recovered from each failed or cancelled batch and retained the partial work already completed. Balanced lab supply also mattered: moving eight red packs to the second lab restored simultaneous research.

The run submitted 26 batches: 13 completed without a batch failure, 10 failed and were recovered through later batches, and 3 were cancelled for navigation recovery. There were 341 successfully completed action steps. These counts include learning/debugging attempts, not just a polished final route.

The [next-run plan](next-run.md) has material budgets, production-capacity calculations, and the controller backlog. The current three iron/two copper lines cannot continuously supply the nominal four-red/two-green science capacity; more extraction/smelting and automated input delivery are required.

## Confidence

The early-game chain is now demonstrated: mining, smelting, power, normal research unlocks, assemblers, inserters, and red/green science. This supports confidence in continuing the game with supervision and recovery. It does not yet support an unattended full rocket run or a record-time claim. Later production stages and robust obstacle handling still require separate tests.

## Public evidence scope

This report summarizes the private experiment record. Original saves, raw action/event logs, factory snapshots, and historical commits remain privately archived and are not included here. The run used read-only console Lua for diagnostics before the stricter [policy](../POLICY.md) was adopted; it is not a compliant fresh-map baseline. The corrected milestones, failures, and untested stages above are intentionally retained. A later isolated reload verified fixed observations with controller 0.2.0; no new gameplay was claimed.
