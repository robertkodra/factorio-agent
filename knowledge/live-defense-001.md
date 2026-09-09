# First live defensive encounter

Reviewed 2026-09-09. Controller 0.4.0 survived one real encounter with fourteen
small biters while local Qwen inference ran independently. This is evidence for
the early-game reflex, not unattended factory operation or rocket readiness.

## Practice conditions and outcome

The user authorized resuming play after the earlier deaths. This practice used
a copy of the preserved failed checkpoint, not a fresh map or speedrun attempt.
Factorio 2.0.77 ran base plus the controller at speed 1. The loaded checkpoint was
unpaused once at the start; no subsequent gameplay pause was requested. Exact
ticks, wall times, source identity, original failures, observations, UI
interventions and checkpoint hashes remain in ignored runtime storage.
The record also retains one failed out-of-reach mining step before preparation
and the deliberate travel cancellation caused by the defensive interrupt.

The engineer recovered existing equipment, mined and crafted normally, built
steam power and a supplied lab, completed Military research and crafted light
armor and a submachine gun. The pistol was moved with the native inventory UI;
the new gun and crafted ammunition equipped through normal game behavior.

| Encounter measure | Observed result |
|---|---|
| Enemy group | 14 small biters; 14 distinct threat IDs and matching nearby corpses |
| Health | 250 before; minimum 205.2; naturally recovered to 250 afterward |
| Damage | 14 physical hits, totaling 44.8 damage |
| Ammunition | 420 rounds across inventory/equipment before; 364 afterward |
| Production interruption | Travel cancelled on the same tick as `reflex_started` |
| Local guard active | 9.85 game seconds, including retreat/quiet period |
| Pauses, new deaths | None during this practice |

Native firing consumed ammunition while the local controller retreated. The
fight required no model-generated action or manual firing. The recording
captured 189 observation/status pairs across the encounter and immediate exit;
median pair latency was 26.3 ms, 95th percentile 34.7 ms, and the largest observed
sample gap was four ticks. These measure local reads, not rendered frame pacing
or detection latency from an independently timestamped first enemy appearance.
The same-tick cancellation does not establish zero end-to-end reaction time.

Continuous firing substantially slowed movement and biters reached melee range.
The current heuristic has not been validated against worms, spitters, larger
waves, depleted ammunition in live combat, obstacles or multiple simultaneous
factory attacks. One survival must not be generalized to those cases.

## Qwen running alongside the game

The first capture discarded all 229 completed advice responses: a nested guard
sample timestamp invalidated otherwise stable context, and live model latency
was often above the three-second advice limit. Median response time was 3.070
seconds, with a 3.691-second 95th percentile. The earlier offline median of
0.694 seconds did not predict this combined workload.

The supervisor now excludes observation-clock fields from both its comparison
key and the model prompt, retaining threat/state changes and the independent
age limit. In a later capture, 44 of 87 completed responses were usable and 43
were discarded; median response time was 1.527 seconds and the 95th percentile
3.003 seconds. These sequential captures cover different gameplay phases and
cache conditions, so they are not a controlled speedup benchmark. Discarded
advice remains preserved. No advice was connected to the action interface, and
no model weights were trained.

## Ammunition safeguard and continuation

Inspection after combat found that existing name/count inventory transfers
could recreate the spent rounds in a partial magazine. This path was not used
for partial ammunition in this practice. Turret ammunition was split through
the native inventory UI, leaving eighteen full magazines on the engineer and
nineteen magazines in the turret, including the partial magazine.

Source 0.4.1 now rejects transfers involving matching partial-magazine stacks
in either inventory before mutation. Full-magazine transfers remain available.
The check uses the normal [magazine-size metadata](https://lua-api.factorio.com/latest/classes/LuaItemPrototype.html#magazine_size)
and [remaining-round count](https://lua-api.factorio.com/latest/classes/LuaItemStack.html#ammo).
This conservative restriction is unit-tested; native stack-preserving typed
transfers and a live rejection check remain future work.

The final practice state completed Military, Gun turret and Automation, with a
powered lab, refuelled iron production and one loaded defensive turret. The
checkpoint ZIP passed integrity verification, the server shut down gracefully,
and the client closed. Controller 0.4.1 was installed afterward; the encounter
itself ran 0.4.0. All 52 unit tests pass.

The rocket remains the objective. The next implementation must connect
validated construction and replenishment skills to a persistent scheduler,
revalidate interrupted work, and prove supplied red/green science through
Military 2. Further defense trials need diverse terrain, repeated waves and
explicit failure records. This session does not establish human speedrun
eligibility, complete factory autonomy or rocket capability.
