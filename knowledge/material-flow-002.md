# Offline material-flow review unit

PR 7 is the merged observed-topology foundation. This separate unit adds a
conservative evidence layer; it contains no layout compiler, game connection,
mod installation or live measurement. The leftover development server was
gracefully stopped after a new checkpoint passed ZIP and hash verification.
The source 0.8.1 controller remains uninstalled.

## Implemented contract

- Surface lanes and underground internal lines retain separate node identities.
  Directed normalized native line relations represent straight runs, turns,
  side-loading into one lane and underground endpoints without merging both
  lanes. Missing relation evidence stays unknown; positions or mixed contents
  do not manufacture a native connection.
- Inserter pickup candidates remain separate per lane and share one hand node.
  Explicit observed lane ports take precedence. A known straight ordinary belt
  supports a geometric far-lane drop candidate; curves and underground mouths
  require resolved lane evidence. Missing shape is not assumed straight.
- Machine recipe inputs, outputs and chemical furnace fuel are separate ports.
  Recipe facts come from the pinned base catalog. Unsupported versions or
  unobserved recipes yield unknown acceptance.
- Accessible inventory slots, filters and stack sizes establish room bounds.
  Aggregate contents can establish an upper bound with explicit accessible-slot
  and stack-size evidence. A mixture alone does not establish a full buffer.
- Requested capacity applies to a specified simple route carrying one material.
  It is not an optimization over every possible route or a whole-factory result.
  Finite upper cuts identify the limiting node or direct edge. Alternative paths
  outside that route are not ruled out.

The interval classifier returns `feasible` only at or below the established lower
bound, `infeasible` only above a finite upper bound, and otherwise `unknown` with
the missing observations. The requested rate is never reduced. Current retained
snapshots prove no positive joint supply/service lower bound, so the route
analyzer keeps their lower bound at zero. It does **not** label a positive rate
feasible just because it is below a belt or furnace nameplate upper bound.

Observed craft-counter deltas are reported separately. They do not establish
recipe continuity, sink delivery, a capacity guarantee or continuous operation.
No observed-rate number is fed back as a theoretical lower bound.

## Optional normalized evidence

The mirror can preserve these additional fields when an observation contains
them. The current 0.8.1 collector and old journals do not supply most of them.
This PR defines and tests their offline consumption; it does not claim a live
collector has been implemented or validated.

| Domain | Fields | Meaning |
|---|---|---|
| Structure | `transport_lines` | At most four line records with `index`, `complete`, and bounded `outputs` containing observed entity/line pairs. Completeness applies to that line's direct outputs. External or missing owners are not added to the selected graph. |
| Structure | `belt_shape`, `inserter_ports` | Native belt shape and explicitly resolved pickup/drop lane endpoints. |
| Inventory | `inventory_slots`, `stack_sizes` | Complete accessible slot list after the chest bar, including filters, normal-quality item counts, and explicit item stack sizes. |
| Production | `crafting_speed`, `productivity_bonus` | Effective metadata for an output-rate upper bound; missing values remain unknown. |

A future reviewed collector must resolve native transport-line aliases and
underground line indices, stay inside the selected owned/charted entities, and
validate these fields against Factorio 2.0.77. Arbitrary manually supplied
sidecar data must not be promoted to live observation authority.

The runtime API exposes [direct line relations and line identity](https://lua-api.factorio.com/latest/classes/LuaTransportLine.html)
and [belt shape](https://lua-api.factorio.com/latest/classes/LuaEntity.html#belt_shape).
The ordinary [belt system](https://wiki.factorio.com/Belt_transport_system) provides
the base unstacked lane upper bounds. [Inserter mechanics](https://wiki.factorio.com/Inserters#Inserters_and_transport_belts)
motivate separate pickup lanes and the straight-belt drop candidate. These
references were inspected during development; latest API documentation is not
itself a version-matched runtime validation.

## Failure replay and remaining evidence

`python3 -m client.material_flow` reconstructs private mirror journals without
hard-coded site IDs, records per-frame diagnoses and source hashes, and refuses
public output or overwriting an existing report directory. Corrupt checksums
fail; unavailable or stale facts produce unknown results. Source tapes are never
modified. Repeated per-frame results are samples, not distinct failure events.

- Coal-feed diagnosis separates an observed fuel-starvation symptom from its
  unknown upstream cause. Empty fuel inventory alone is insufficient while a
  burner may still contain burning fuel.
- A buffer unable to accept a required ingredient can be diagnosed when its
  room upper bound is zero. This local obstruction does not prove every
  alternative supply route is blocked.
- Red and green packs sharing a lane remain an observation, not proof of a jam.
  Ordered items, lab acceptance and a continuous motion/delivery window are
  required to establish the historical science obstruction. Missing historical
  fields are not filled from the narrative retrospective.

Synthetic tests exercise all three failure classes, lane relations, material
compatibility, unknown evidence and interval boundaries with changed entity IDs.
Retained journal replays test the available historical evidence independently of
these richer synthetic fixtures. Their detailed outputs remain private.

Four retained journals were replayed across 12,338 mirror frames without changing
their source hashes or making live calls. Their relevant diagnostic samples all
remain unknown: the required native lane links, slot/stack metadata and motion
windows were not present. This is an observability gap, not evidence that the
historical failures did not occur or that all three causes were independently
reproduced. The earlier qualitative retrospectives remain separate evidence.

## Review gates

This is an offline draft. Positive guaranteed production rates, a native collector
for the richer lane/slot contract, and a confident historical science-lane root
cause remain unproven. They are explicit review gaps, not completed milestones.
Do not merge on the assumption that the synthetic lane cases constitute engine
validation. No compiler belongs in this PR.

The strict 88.83 percent compression result is unchanged. Next live evidence is
observation cost and event-to-action latency, only after trusted-launcher and
measurement-harness review. Any later throughput harness still needs production
counter deltas, sink-delivery deltas and beginning/ending in-block stock.
