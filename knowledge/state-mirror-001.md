# Smelting state mirror: review slice

This is an offline-validated cache and bounded observation interface. Controller
0.8.1 source adds observations only; it was not installed for this work and no
gameplay was resumed. The 0.8 integration baseline is [PR 5](https://github.com/robertkodra/factorio-agent/pull/5),
ending at `074d1e1`. Original PRs 1–4 remain intact. The mirror branch is based on
that baseline and adds a separate review unit. Nothing has been merged.

## What exists

- `StateMirror` stores explicit episode/save/source identity, actor and surface,
  observed ticks and wall timestamps, selected entity structure, inventories,
  power/status, production, player state, research and job outcomes.
- Native events are consumed in order and deduplicated. A page head is not a
  consumed cursor. Gaps, conflicting duplicates and actor changes invalidate
  planning; an explicit snapshot reconciliation is required to recover.
  Recovery records its snapshot fence separately from the last actually consumed
  event sequence. It does not label lost event pages as consumed; recovery reasons
  remain in the journal. Normal pagination never jumps to the advertised head.
- Freshness is per domain: player/power expire after 0.5 seconds, inventory and
  production after 1 second, structure/research after 5 seconds. Game-tick age
  also applies at 60 ticks/second. These are initial conservative limits, not
  validated optimal polling intervals. Guard sampling timestamps are excluded
  from decision revisions while meaningful guard state remains included.
- A plan token names the observed facts it depends on. Expiry, changed revisions,
  safety events or unresolved jobs reject it. It is a cache precondition, not a
  substitute for the executor's normal reach, costs, ownership and collision checks.
- Unknown submissions are reconciled by their exact ID. A missing receipt remains
  unknown and blocks planning. There is no automatic resubmission path.
- `observe_entities` accepts 1–64 known IDs with their observed positions. It
  rejects invalid requests before lookup, filters ownership and charted terrain,
  and returns scoped machine state or missing IDs. It adds no discovery, movement
  or mutation operation. Fluid-neighbour geometry is excluded from this slice.
- Furnace reads include the active recipe and remaining burning fuel energy.
  Missing fields stay unknown; an empty fuel inventory alone is not proof that
  the currently burning fuel has expired.
- `BlockObserver` refreshes the selected block with bounded reads, validates
  identity and reconciles job receipts. Its optional journal records the cache.
  `EmergencyPump` uses a separate connection and thread and never calls a planner
  or model. It queues native events; the existing native reflex and same-event
  production preemption remain the actual emergency input mechanisms.
- The journal writes compact deltas and periodic checkpoints, retaining native
  event payloads, state checksums and record sequence numbers. Replay verifies
  every record and reconstructs independently from each checkpoint suffix.

The legacy autopilot still uses its existing snapshots and authored sites. This
PR does not silently switch it to the mirror. No general production graph, layout
compiler, expansion, rocket planner or live monitor is started by these modules.

## Reproduce the private replay

Inputs are an existing journal, a private identity manifest and 1–64 selected
entity IDs. Output directories must be new and remain under ignored runtime.

```sh
.venv/bin/python -m client.replay_mirror runtime/source/events.jsonl \
  --identity runtime/analysis/identity.json \
  --entity-ids runtime/analysis/entity-ids.json \
  --output runtime/analysis/replay-001
```

The identity contains `episode`, `save_sha256`, `mod_sha256`, `controller`, `base`,
`actor` and `surface`. The source replay here used its recorded 0.8.0 mod source
identity. Legacy factory reads do not carry explicit charting evidence, so their
cache domains are labelled `owned_factory_replay` and cannot authorize gameplay.
No model or Factorio connection is made by this command. It refuses to overwrite
an output directory and preserves an error record on failure.

## Measured replay results

The same fixed sample of 64 previously observed entities was used for four
retained phases: 15 furnaces, 14 drills, 8 chests, 8 inserters, 9 poles and 10 belts.
This is a type-balanced cache sample, not a graph-derived complete production
block. The original journals remain unchanged and their hashes were checked
again after processing.

| Phase | Original journal bytes | Compact journal bytes | Reduction vs original | Reduction vs full scoped state |
|---|---:|---:|---:|---:|
| Initial supply | 730,428,024 | 55,851,998 | 92.35% | 88.27% |
| Recovered supply | 323,771,288 | 25,582,452 | 92.10% | 92.11% |
| Direct-feed preparation | 283,264,281 | 21,140,200 | 92.54% | 82.27% |
| Repair continuation | 89,841,052 | 7,071,012 | 92.13% | 88.53% |
| Total | 1,427,304,645 | 109,645,662 | 92.32% | 88.83% |

The original-size comparison includes selecting 64 entities/fields and omitting
unrelated planning and geometry records. The stricter comparison serializes the
same complete mirrored state, including freshness and receipt metadata, at each
accepted record. It isolates delta storage from scope selection, but is not the
old logger's original format. The 90-percent target is met against the originals
and **not met** against this full-scoped-state comparison. These are storage
results, not gameplay performance improvements.

There were 1,078,308 retained observation projection checks and zero reconstruction
mismatches. Every emitted record and every checkpoint suffix reconstructed the
same state. Per-phase reports retain input hashes, implementation hashes, record
counts and separate CPU timings for decoding, cache updates, encoding/writing and
reconstruction. The full original journals are the evidence for omitted details.

Observation/RCON cost remains unmeasured in the game. The observer fixture verifies
bounded requests and no full-factory reads; replay records zero live RCON calls
and null network/engine latency. The archive has no new native factory-damage
sample, so damage-to-preemption and first-defensive-input latency cannot be
estimated from these phases. Native same-event preemption has Lua fixture coverage;
thread tests show polling during a stalled planner. Neither is a live latency test.

## Review objections and limitations

**Save identity requires provenance outside this API.** The fixed game interface
has no save fingerprint. This slice requires a supplied episode/save/source
manifest, checks actor/controller/surface and rejects tick regression. A different
world or reload with the same actor/version and a later tick cannot be detected
from those observations alone. A trusted launcher must bind fresh provenance to
an actual server instance before unattended live use. A hash supplied by a caller
is not independent evidence that the running server loaded that hash.

**Partial observations need explicit scope.** Missing requested IDs mean not
observed at those positions; they do not invent an attack or destroyed count.
Native destruction tombstones prevent old samples resurrecting an ID. Normal
replacement buildings need newly observed IDs. This observer does not discover
replacements, resource expansion or new topology. Research recipe metadata and
power energy/status are observations, not a solved material-flow or power model.

**Emergency control must stay native.** The separate pump removes model latency
from event polling, but transport stalls, disk stalls and Python scheduling still
exist. The queue does not dispatch a route to a damaged remote site. Existing
native preemption/local defense are preserved; broad factory defense remains
unvalidated. Do not interpret the initial poll interval as a reaction-time bound.

**Preserve the proposed later smelting contract, with stronger accounting.** Test
two locations with no coordinate-specific code edits, a recorded ramp-up followed
by 36,000 uninterrupted ticks at speed 1, ordinary enemies, and at least 95 percent
of promised delivery to a designated sink. Count emergency effects in the result;
exclude pause/reload, human gameplay input, manual inventory repairs, hidden
handcraft contributions and mid-run source/configuration edits. Additionally,
require the requested rate or an explicit infeasibility result, derive the promise
from bottlenecks, and account for initial work in progress and external deliveries.
Otherwise an arbitrarily low promise or preloaded plates can pass without proving
useful new production. No smelting construction is authorized by this report.

## Validation and retained development corrections

The baseline passed 141 tests in the project environment; system Python passed
130 with 11 optional MCP skips. Final mirror validation passes all 171 tests in the project environment;
system Python passes 160 with the same 11 optional MCP skips. Publication checks include the
history guard and redacted secret scans of both history and the staged tree.

The first full suite after adding the MCP operation failed because its round-trip
fixture had no valid example for the new required target list. The fixture was
updated; no gameplay ran. Review of the pinned 2.0.77 API also corrected the fuel
mock: `currently_burning.name` is an item prototype, whose `.name` supplies the
string. Earlier replay passes and their metrics remain as development evidence;
only the final implementation-matched reports should be used for this PR.

Stop here for review. Live installation, smelting construction and broader planning
remain later work.
