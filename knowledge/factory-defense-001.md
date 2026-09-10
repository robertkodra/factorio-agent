# Remote factory attack: failure and first response fix

This checkpoint practice is not a competitive run. Exact observations, failed
jobs, actor identities, locations and checkpoint hashes remain private.

## What failed

The user noticed the base-attack icon while the engineer was elsewhere. Thirteen
coal-conveyor tiles were lost. The first saved damaged-building sample preceded
the engineer's arrival by about 203 game seconds; roughly 28 seconds of that was
the final response journey. The nearby spawners are a plausible source, not
verified attribution of that attack.

The local reflex watched enemies near the engineer. The native damage event
adapter recorded only engineer damage. A separate factory snapshot watcher
retained the evidence but had no dispatch authority. Consequently an intact
engineer and a quiet local scan did not mean the factory was safe.

The initial damage inspection was incomplete. A later comparison with the same
attack snapshot found five additional missing boiler-coal conveyor tiles and
the coal drill's power connection. The separate smelting-row coal drill and five
of its conveyor tiles were also absent. Therefore the initial thirteen-tile
repair did not establish complete supply recovery. These additional absences
predate the new watch; they are not evidence of a new post-fix attack. Exact
before/after inventories and the wider missing-entity comparison remain private.

All thirteen belt tiles were replaced using actual inventory. The existing
loaded turret was normally relocated to cover the attacked conveyor and given
its seventeen recovered magazines. A preparatory attempt to craft more turrets
failed for insufficient materials; its preceding magazine craft remained queued.
No damage, item loss or failed attempt is erased by the repair. The engineer
remained alive at full health during the recorded response.

## Implemented response

`client.factory_defense` compares owned-building health at approximately half-
second intervals inside the persistent scheduler, including during active jobs.
A new decrease preempts a production job by its exact ID. The fixed 0.7.0 cancel
operation also disables the local guard, so the client immediately restores it
before dispatch. This is two commands, not atomic interruption; a transport
failure remains a risk requiring a native interface improvement.

The dispatcher approaches a configured, observed loaded turret near the damage.
The native local reflex still owns combat. It holds the station until the area
has been quiet for ten game seconds. An uncovered alert stops normal scheduling
and is logged; arbitrary assaults on nests are not generated. `target: defense`
keeps an idle watch process alive, and `watch_after_target` can retain watch after
a production milestone instead of exiting between planning phases.

A further correction keeps this watch alive when placement preflight rejects a
footprint. Production suspension persists across a same-journal restart; a new,
corrected plan is needed to continue building. Unit coverage verifies that no
construction batch is submitted, the blocked placement is not retried on resume,
and subsequent factory damage still dispatches defense. This does not cover every
fatal process error or establish measured attack response in the live game.

Unit tests cover remote damage, repair discrimination, loaded-station selection,
quiet holding, exact-job preemption, guard restoration and cancellation accounting.
The watch is running in the live game. Its response to another real attack has
not yet been measured. Polling can miss destruction between samples or damage
masked by repair. It is not a native damage/destruction event feed, guaranteed
subsecond response, comprehensive coverage or autonomous defense readiness.

## Center-fed defense cluster

The user's proposed layout was applied as a smaller first stage: the existing
center turret supplies two outer turrets covering exposed approaches. Two powered
long-handed inserters transfer real magazines directly from the center. Native
inventory observations confirmed ten magazines in each outer turret, with twenty
remaining in the center after replenishment. The scheduler continues fuel and
ammunition maintenance after verifying construction.

This transfer pattern and the ten-magazine automatic receiving limit agree with
the [gun turret documentation](https://wiki.factorio.com/Gun_turret). Turrets can
fire without electricity; these inserters need power to keep distributing ammo.
The cluster has not yet faced a measured attack. Its current reserve is finite,
and the center and feed arms remain shared points of failure. Expand coverage
according to observed approaches and keep the supply path behind the firing line;
do not assume a full ring is the best early use of iron and copper.

## Next validation

Add bounded owned-factory damage/destruction events and an interrupt operation
that preserves the guard. Measure event-to-cancel, event-to-dispatch, arrival,
losses, ammunition and remaining power during natural attacks. Preserve all
failures and human interventions. Add normal grenade use and test movement,
grouping and escape routes before relying on grenade kiting.

Recovery must also verify the entire damaged production path: resource drill,
power, conveyor continuity, receiving fuel inventories and actual downstream
output. A loaded turret and repaired visible belt segment are insufficient.
