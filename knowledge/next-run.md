# Next opening: hypotheses to test

These are improvements suggested by dry run 001, not a validated speedrun route.

1. Start from a fresh, fixed-seed save with the repaired crafting controller. Record a baseline before the first action. Keep game time and wall time separate.
2. Mine a nearby large rock, bootstrap the facing coal-drill pair, then start iron and copper production in parallel. The old conveyor demonstration is not a useful production opening.
3. Budget the complete next milestone from the version-specific recipe catalog before queuing crafts. An assembler needs five gears. Two assemblers, two output inserters, and forty red packs cost 132 iron plates and 52 copper plates when all intermediates are included.
4. Queue hand crafting during long walks. Do not wait for an entire large crafting queue before doing unrelated fuel or material transfers.
5. Select an actual reachable construction stance. A building footprint can collide with the engineer, a tree canopy, or an existing pole even when its center looks clear. Resource mining needs a closer stance than the general interaction reach check permits.
6. Validate every inserter's power and pickup/drop positions after construction. Connected poles and powered assemblers do not prove that the inserter between them has coverage.
7. Keep working-capital reserves for more miners, furnaces, fuel, and power. A science-machine count is only useful if metal production can sustain it.
8. Automate delivery of fuel, plates, gears, and circuits. Dry run 001 uses batch-supplied ingredients; its science output and lab insertion are automatic, but its input supply is not continuous.

## Production capacity model

For normal-quality assemblers, the game catalog gives five recipe-seconds per red pack and six per green pack. At assembler-1 speed 0.5, this means six red packs/minute or five green packs/minute per machine, before input or electricity shortages. The four-red/two-green campus therefore has nominal capacities of 24 red/minute and 10 green/minute. These are calculated capacities, not measured sustained throughput. [Assembler reference](https://wiki.factorio.com/Assembling_machine_1).

A red pack costs two iron plates and one copper plate including its gear. A green pack costs 5.5 iron plates and 1.5 copper plates when belts and cables are produced in even batches. Running both groups at those capacities needs 103 iron plates/minute and 39 copper plates/minute, before any construction budget.

The live prototype reports burner mining speed 0.25 and iron-ore mining time 1 second. A directly paired burner drill therefore limits a smelting line to approximately 15 plates/minute. A stone furnace itself can smelt 18.75 iron or copper plates/minute. At least seven iron burner lines and three copper burner lines would be needed for the calculated campus demand, assuming continuous supply and no transport losses. The dry run's three iron and two copper lines are below that target. Electric drills and proper smelting arrays should replace this bootstrap arrangement. [Furnace reference](https://wiki.factorio.com/Stone_furnace).

## Controller work still needed

- Detect lack of progress along a path, including oscillation. The current watchdog detects an unmoving engineer, but small back-and-forth motion can postpone recovery until the whole step times out.
- Let service actions choose a reachable stance within the actual action radius instead of demanding unnecessary exact waypoints.
- Make placement preflight include the engineer's intended final position, power coverage, and neighboring footprints.
- Generalize inventory names for laboratories, chemistry, oil, rockets, and other later-game machinery. The current aliases share numeric inventory IDs with some machines; that should become an explicit per-entity mapping.
- Add threshold-driven fuel/material collection and research scheduling. Keep mutation IDs and progress logs so an interrupted planner can resume without repeating completed steps.
- Validate oil, blue science, modules, robotics, and rocket production in subsequent runs. None of those stages is proven by this early-game test.

## Scope of the budgeting helper

`python3 -m client.materials '{"assembling-machine-1":2,"inserter":2,"automation-science-pack":40}'` reads the saved recipe export and rounds intermediate batches while accounting for supplied inventory. It is validated for the early deterministic solid-item recipes used here. Its recipe time sum does not model concurrent factory machines, travel, mining, unlock requirements, power, or machine crafting speed. It is not yet an oil/by-product or rocket planner.
