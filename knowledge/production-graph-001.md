# Offline production graph: first slice

The baseline and state mirror merged in order: PR 5 at `dcce763`, then PR 6 at
`059ee8a`. The alarm-recency fix is `7033016`; the observer protocol-failure fix is
`bd1dfc3`. Original histories remain intact. The source 0.8.1 mod remains
uninstalled, and gameplay was not resumed.

## Implemented boundary

`client.production_graph` freezes a state-mirror checkpoint and derives a bounded
graph for 1–64 selected observed entities. It represents drills, their observed
mining targets, buffers, inserters, machines, poles and separate belt lanes.
Inserter pickup/drop and drill drop positions intersect observed building
footprints to produce **candidate geometric transfers**. Structural upstream
tracing follows those candidates without assuming an item can traverse them.

Normal projection requires valid, fresh structural observations and a consistent
event state. Expired inventory/power/production domains become unavailable instead
of current facts. Explicit historical mode accepts only legacy replay scope;
original timestamps, scope and validity remain attached. Neither mode produces
an executable plan. Historical charting remains unverified.

Missing or ambiguous endpoints remain unresolved. A partial sample does not prove
that a building is absent outside that sample. Missing furnace recipes and mining
targets stay unknown. A mixed chest is not called full: current observations lack
enough slot/stack information to establish its remaining capacity. Native machine
statuses are recorded as instantaneous conditions, not a sustained bottleneck.

Belt lanes are separate nodes with separately observed contents. Their transfers
are unresolved in this slice, including inserter-to-belt lane selection,
side-loading and underground connections. It is safer to leave these edges absent
than create a false path from a union of both lanes. Filters, inserter hand state,
recipe-specific acceptance, throughput capacities, fluid routing and a layout
compiler remain later work. Existing native emergency control is unchanged.

## Offline evidence

The retained repair-phase mirror was reconstructed and analyzed using its same
64-entity sample. The graph contains 98 nodes and 24 edges: 14 observed mining-target
relations and 10 geometric transfer candidates. It reports 20 unresolved endpoints,
10 unresolved belt connections and 15 unobserved furnace recipes. These are gaps
in this partial historical sample, not proof of 20 broken connections or 15 idle
furnaces. All 55 available native status labels remain attached as observations.

The source hash was unchanged after analysis. Reversing the input selection order
produced the identical graph. Graph JSON, hashes, source/module identities and
aggregate reports remain under ignored runtime storage. No RCON connection or
throughput measurement was made. Prior storage results are unchanged; there is no
work here to chase the disclosed 88.83 percent strict compression result.

Thirteen focused tests cover complete direct feed, translated/rotated geometry
with different entity IDs, disconnected and ambiguous ports, separate lane
contents, partial samples, freshness, destruction/missing entities, historical
authority, deterministic output, cycle-safe tracing and corrupted journals.
These are synthetic topology tests plus an archived projection, not a replay
diagnosis of every earlier coal-feed or science-lane failure.

The first post-merge publication audit rejected GitHub's public service committer
address because it allowed only the user no-reply domain. The guard now also
accepts the exact service no-reply address, with tests retaining rejection of
other addresses and lookalikes. No personal email exposure or history rewriting
was involved. The initial failed audit is retained privately.

Final validation passes 190 project-environment tests and 179 system-Python tests
with 11 optional MCP skips. All 44 mirror/graph tests pass in a fresh exported
checkout. Diff checks, the publication-history guard, redacted history/staged-tree
secret scans and runtime-ignore checks pass on this branch.

Reproduce with private inputs and a new output directory:

```sh
.venv/bin/python -m client.production_graph runtime/analysis/mirror.jsonl \
  --entity-ids runtime/analysis/entity-ids.json \
  --historical --output runtime/analysis/graph-001
```

The command refuses public output paths and existing output directories, verifies
checkpoint/delta checksums, and preserves a failure record if analysis fails.
Omit `--historical` only for reviewed observation scope with valid fresh facts.

## Next work and hard live gates

Continue offline with observed lane connectivity and item acceptance, then
capacities and flow diagnosis. Replay the known coal-feed, mixed-buffer and science
lane failures before relying on that diagnosis. Geometry alone is insufficient.

**No installation or gameplay until launcher provenance and the measurement
harness are reviewed.** Trusted launcher binding is not required for offline
analysis of retained evidence. Live measurement must report RCON/engine observation
cost and event-to-action latency separately from journal storage or replay CPU.

The later compiler takes a charted resource patch and requested plate rate. It
must either satisfy that rate or return a structured infeasibility result with
maximum capacity and the limiting bottleneck. It must never silently lower its
promise. Successful output includes a plan hash, bill of materials, placements,
connections, ordered actions and a bottleneck-derived promised rate.

Validate two locations without coordinate-specific edits. Record ramp-up
separately, then measure 36,000 uninterrupted ticks at speed 1 with ordinary
enemies. Require both furnace production-counter deltas converted to plate counts
and designated sink-delivery deltas to meet at least 95 percent of promised
output. Record starting/ending in-block plate stock, recipe/entity identity and
external transfers. Reject unexplained counter or mass-balance discrepancies;
sink deliveries from preloaded plates cannot stand in for new production.

No pause, reload, human gameplay input, manual inventory repair, hidden handcraft
contribution or mid-run code/configuration edits are permitted. Automatic emergency
handling is allowed and its effects count in the measured result. This contract
is preserved for a later reviewed harness; this graph is not that harness.
