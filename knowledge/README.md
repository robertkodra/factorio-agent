# Factorio knowledge base

Start with the [strategy playbook](strategy.md), then the [next-run plan](next-run.md). The [historical dry-run report](dry-run-001.md) preserves failed batches, corrected milestones, and validation limits. Original saves and detailed run traces are privately archived; this public folder contains reviewed summaries only.

The [speedrun preparation](speedrun-preparation.md) turns the research into a
staged practice route, a capacity/fuel calculator and a timed-test protocol. Its
checkpoint rehearsal produced 30 automatic red packs, completed Electric mining
drill and recovered an exhausted iron line. Green-consuming research and
continuous input supply remain pending.

The [Speedrun.com study](speedrun-study.md) records category/timing rules,
version-matched human reference runs and proposed experiments for travel,
production order, reserves and execution overhead.

The subsequent [live responsiveness test](responsiveness-001.md) started a fresh
map under the current policy, completed the 29-action conveyor opening, and
measured MCP latency, cancellation, and reconnection with the Steam client
connected. It also reduced large-batch validation overhead. It does not establish
red/green production on a fresh run or later science capability.

The [enemy-enabled learning attempt](learning-001.md) completed Automation and
Gun turret, powered two labs and verified one loaded turret. It added bounded
navigation recovery, native crafting progression, charted water/pollution reads
and explicit ammunition-slot transfers. It still used hand-crafted science and
manual supplies; no live defensive encounter or green-consuming research passed.

The dry run continued a conveyor test and produced 114 red packs and 20 green packs, completing Automation and Logistics. It did not complete green-consuming research. Its 31:26 game / 32:25 wall timing includes planning, recovery, and debugging; it is not a fresh or competitive baseline.

## Verified early-game lessons

- Use the pinned [2.0.77 catalog](../data/README.md) for recipe costs. A recipe's costs do not establish that it is unlocked.
- The observed progression needed 50 iron plates for Steam power, 10 copper plates for Electronics, and normal lab crafting for red-science unlocks. The fresh learning attempt showed that the earlier ownership fix was insufficient; controller 0.3.1 uses the player crafting adapter and retains ownership, with the unlock verified from a new lab craft.
- Direct drill-to-furnace placement started useful smelting sooner than the earlier demonstration conveyor line, which accumulated ore away from its furnace.
- A nearby huge rock yielded 38 stone and 28 coal in one mining action. This is a measured yield for that rock, not a guarantee for every rock.
- A facing pair of coal drills can supply startup fuel. Verify both inventories and provide initial fuel before treating it as operational.
- Queue hand crafting while walking when ingredients are available. Construction and production can overlap.
- Select the exact mining entity: overlapping tree canopies caused the earlier target-selection bug.
- Check complete building footprints, engineer stance, and every inserter's power and pickup/drop positions. Poles and assemblers being powered did not prove inserter coverage.
- Navigation oscillation required cancellation and intermediate waypoints. Controller 0.3.0 now stops after bounded progress retries; automatic service-position selection is still pending.
- Balance delivery across labs and retain material reserves for miners, furnaces, and fuel. Assembler capacity alone is not sustained throughput.

The next target is a clean G0/G1 run followed by Military 2, as defined in the [roadmap](../ROADMAP.md). Oil, military science, blue science, robotics, and rocket production require separate demonstrations.

References: [Factorio quick start](https://wiki.factorio.com/Quick_Start_Guide), [burner mining drill](https://wiki.factorio.com/Burner_mining_drill), and [science packs](https://wiki.factorio.com/Science_pack). The checked-in catalog and measured results take precedence over assumptions about other game versions.
