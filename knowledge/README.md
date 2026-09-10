# Factorio knowledge base

Latest offline implementation: [observed production graph](production-graph-001.md).
The 0.8 baseline and [state-mirror slice](state-mirror-001.md) merged in order after
review corrections. Graph analysis remains offline. The 0.8.1 mod stays uninstalled
and gameplay stopped until launcher provenance and the measurement harness are
reviewed.


Current direction and state: [architecture review response](review-response-001.md).
Controller 0.8.0 completed Oil Gathering in checkpoint practice. That development
ledger is closed with a verified save; no gameplay scheduler is active and no
character was bound at review. The next work is a state mirror, production graph
and verified layout compiler. Oil production, later science and a rocket remain
unverified. All running/paused notes below describe historical stopping points.

Prior analysis: [controller and factory improvement plan](improvement-plan-001.md).
A fresh cadence/stock audit, speedrunner reference archive inspection, phased
factory proposal and implementation priorities extend the paused retrospective.

Current state: [paused practice and consolidated lessons](session-retrospective-001.md).
The user requested a pause; the checkpoint is verified and the executor stopped.
Do not resume gameplay automatically. Earlier running-state notes below are historical.

Latest progress: [restoring useful science flow](science-flow-001.md).
Engine and Fluid handling completed; Oil gathering is running after correcting
circuit input starvation and separating the science belt lanes.

Latest sequence: [supply recovery and automatic science transport](supply-recovery-001.md).
Coal and iron production recovered; science transport works, but ingredient
starvation still prevents sustained research.

Latest failure and correction: [remote factory attack and continuous defense watch](factory-defense-001.md).
Engineer-local combat missed damage to the coal supply. Keep this limitation and
the actual losses visible when judging the newer controller.

Current development: [belt-fed production and cadence](belt-production-001.md).
The updated strategy adopts a fast hand-fed bootstrap before planned furnace
blocks and a bus. Historical stopping points below remain historical.

Current development: [buffered production and fluid observations](production-oil-001.md).
Controller 0.6.0 supersedes the older implementation versions below. Historical
reports retain their original claims; oil and a rocket are still unverified.

Latest implementation: [persistent factory controller and rocket planning](rocket-controller-001.md).
Controller 0.5.1 adds native stack transfers, durable job receipts, research/launch
evidence and a persistent production scheduler. Read that report for current
live validation and the remaining rocket work.


Latest validation: [first live defensive encounter](live-defense-001.md).
Controller 0.4.0 survived fourteen small biters with local Qwen running in shadow
mode. The practice checkpoint is saved and the game stopped; the subsequent
0.4.1 partial-ammunition safeguard is installed and unit-tested. Full factory
control, further combat generalization and learning remain pending.

Read the latest [failed rocket-attempt review](rocket-attempt-001-review.md)
before playing again. Two deaths exposed missing combat response and health
monitoring during travel. The user observed biters attacking and stopped the
game. The later authorized practice used a separate copy and preserved that
original checkpoint and its failure evidence.

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
