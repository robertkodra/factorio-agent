# Buffered production and fluid observations — 2026-09-10

Controller 0.6.0 adds the geometry and supply controls needed to move beyond
hand-carried science ingredients. This is checkpoint development practice,
continuing the saved Military 2 factory. It is not a fresh timed attempt or a
verified oil-to-rocket controller.

## Implementation

- A fixed read-only `prototype` operation returns static machine dimensions,
  fluid ports, pole ranges and drill radius. Factory observations expose owned
  reciprocal fluid connections, optional segment IDs, locks, mining targets in
  charted chunks and native completed-craft counters.
- Fluid planning maps separate recipe input/output slot numbers to real machine
  ports, including cardinal rotations. Directed connection validation handles
  output-only boxes that do not belong to a fluid segment. A topology check
  does not establish production or throughput.
- Relative smelting cells use a normal electric drill, an ore/fuel chest,
  native inserters, a furnace and an output chest. Ordinary pole-line plans
  account for tile-center rounding and native wire reach.
- The persistent scheduler supports stocked chests, larger recipe buffers,
  batched structure procurement, consumed natural-resource sites and an initial
  direct-transfer phase until a cell's inserters exist. Power and chests precede
  other construction to avoid startup dependency cycles.
- A read-only production audit computes actual craft rates for unchanged
  machine identities/recipes and separate whole-factory item deltas. The latter
  can include hand crafting and must not be attributed entirely to machines.

## Live findings and retained corrections

Electric mining drill research completed through the labs. Static prototype
observations and factory fluid observations run successfully against base
2.0.77. Directed paths were verified from the offshore pump through a pipe to
the boiler, and from the boiler's output to the steam engine.

The first segment-equality diagnostic falsely rejected the working steam feed:
the boiler output has no segment ID. Native reciprocal ports provide the
correct directed connection evidence. That failed diagnostic remains recorded.

The initial construction order built an inserter assembler before its power
connection. The scheduler now establishes power infrastructure first. Another
live failure showed that natural entities have shorter interaction reach than
factory service positions; gathering stances now leave arrival-tolerance margin,
and an out-of-reach result advances the service stance. Earlier failed actions
and scheduler restarts remain in the private ledger.

A lab/crash-wreck gap later stopped the controller. The owned-factory view did
not include the neutral wreck. A southward recovery step also failed; ordinary
eastward walking freed the engineer, followed by a verified clear access lane.
The scheduler now supplements service-position checks with bounded charted
neutral scans and conservatively oriented prototype collision bounds. Incomplete
scans and unobserved terrain still cannot establish complete path clearance.
This recovery was a development intervention, not unattended navigation proof.

Both new electric smelting cells were observed running the complete native
drill → chest → inserter → furnace → output-chest path. Over a 228.72-second
sample they completed 72 and 71 smelts, approximately 37.51 iron plates/minute
combined. Both drills mined real observed iron deposits. This is a measured
sample, not a guarantee of sustained full-run capacity.

Cables, gears, circuits and inserters were produced by the new assemblers. The
source-selection fix chose full 100-plate neighbor buffers after repeated tiny
pickups from the nearest furnace. Ingredient replenishment now uses a half-buffer
threshold, and collection can wait for a small usable batch from a machine that
is demonstrably producing. Usable ready science is delivered before restocking another parallel producer;
otherwise packs can sit beside idle labs. These heuristics still require broader
evaluation.

A second normal steam engine was built and its steam path and electric network
were verified. All three green-science assemblers produced real packs; the four
labs consumed their packs and completed Automation 2 through native research.
The checkpoint is saved, the ledger is closed, and both server and viewer are stopped.

## Remaining rocket work

Survey real oil, build the connected pumpjack/refinery/chemical chain, produce
blue packs and consume them in labs. Expand metal, power and lab capacity from
measured throughput, then demonstrate later science, silo production and an
actual launch. The local Qwen selector remains shadow advice; these changes do
not train model weights or establish competitive performance.


## Closed practice result

| Evidence | Result |
|---|---|
| Research | Electric mining drill at 2:23; Automation 2 at 61:06 from the continued baseline; both native, not script-completed |
| Final recorded interval | 62:37 game / 62:37 wall, plus a separately recorded 97.5-second startup interval |
| New science | 73 red packs and 40 green packs; green-consuming research actually completed |
| Final capacity installed | 2 electric iron drills, 2 steam engines, 4 labs, 3 green assemblers and 5 buffered intermediate cells |
| Intermediate machine crafts | 159 gears, 77 circuits, 57 inserters, 24 belt crafts and 142 cable crafts; multi-item recipes yield more than one item per craft |
| Jobs | 706 total: 682 completed and 24 failed, including one failed manual recovery job |
| Development restarts | 13 scheduler starts across 8 preserved phase journals; 8 intentional interruptions and 3 failure stops |
| Final corrected phase | 41/41 jobs completed without execution failure |
| Engineer and rules | Full final health; no new damage/deaths or gameplay pause transitions; normal speed |
| Source checks | 104 tests pass with MCP dependencies; standard-library run passes with 11 optional tests skipped |

The source checkpoint remains unchanged. The new checkpoint archive and hash
were verified before graceful shutdown. The private ledger retains all failures,
manual scouting/recovery, phase changes, source hashes, observations and save
identities. This includes substantial development time and is not competitive
or unattended completion evidence. Further neutral-obstacle and navigation
validation remains necessary. No blue science or rocket was produced.
