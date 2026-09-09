# Rocket attempt 001: failure review

The attempt was stopped at the user's request after two engineer deaths. The
user observed several biters attacking. The server is shut down and the failed
checkpoint is preserved. No rocket was launched.

## What the evidence establishes

- Both damaging batches included travel from copper toward coal. The recorded
  health fell from 250 to 40 in the first case and from 250 to 33 in the second.
- Both jobs reported complete. That describes action execution, not survival or
  a successful strategic outcome. I continued planning instead of responding to
  the critical health readings.
- After the first death I recovered the corpse, but repeated the exposed travel
  pattern without establishing a working combat or retreat response.
- Several biters attacked, according to the user's direct observation. The old
  controller did not record damage or death causes, so it cannot independently
  identify the individual attackers or exact first-hit locations.
- Empty unit scans after respawning did not establish that the earlier route was
  safe. They sampled another time and position, with charted-area limits.
- The first lab and power equipment were crafted, but not installed. Only one
  red pack was completed before the second death interrupted the crafting queue.
  Coal, iron and copper production existed; there was no powered lab research,
  loaded turret, green science or launch progress.

Initial setup and scouting used pauses before the user added the no-pause rule.
From that instruction until the explicit stop request, the simulation remained
unpaused. The stop request then authorized pausing and shutting down. There were
no recovery grants, teleports or gameplay reloads. Normal respawn ammunition is
recorded separately from manufactured ammunition and is not a supply strategy.

## What changes in how I play

**Combat interrupts production.** On the first health decrease, the current
delivery or crafting objective loses priority. React immediately by fighting or
moving toward a previously checked escape route. Do not wait for a batch to end,
for health to fall below half, or for a model's next long planning cycle.

**Observe during travel.** Sample health and position while a movement job runs,
and scan the charted route before entering it. Include mobile enemies, spawners
and worms. Use intermediate waypoints to avoid known nests; ordinary collision
pathfinding does not establish that the route avoids enemies.

**Use actual defensive capability.** Carry usable ammunition, check the equipped
weapon, and establish a working normal firing/retreat method before another
exposed resource trip. Put loaded turrets where they protect the engineer's work
area and supplies. A turret research plan or ammunition in a corpse provides no
current protection. Keep necessary escape space around the factory.

**Recovery must change the conditions.** Retrieve a corpse only after checking
the approach and arranging an escape or protection. The previous recovery
restored inventory but did not correct the lethal behavior.

**Keep the user's rules.** No cheating and no pauses during play. Use normal
movement, ammunition, damage and death. The current game stays stopped until the
user requests another attempt; do not restart it to test these changes.

The Factorio enemy reference describes small biters as melee attackers with a
speed of 43.2 km/h and 7 physical damage per attack. Several attackers can drain
an unarmored character's health quickly. Spitters and worms need different
responses because their acid can damage and slow a player over time. These are
mechanics to plan around; acid is not the established cause of this attempt's
deaths. [Official enemy reference](https://wiki.factorio.com/Enemies).

## Diagnostic repair made while the game is stopped

Controller source 0.3.3 now listens to normal engineer damage and death events.
It records tick, engineer identity and position, damage amount/type, remaining
health and an available cause/source. Attacker identity and location are only
included when charted. `status` retains the last damage/death evidence even after
the old character becomes invalid. This observes events; it never changes
health, items, damage, movement or pause state.

The Lua tests exercise real event registration and status after death, as well
as missing causes and uncharted attackers. All 42 unit tests pass. The source
change is **not installed or live-tested**; the game remains stopped. It improves
diagnosis, but does not itself implement firing, threat-aware navigation or an
automatic escape. Those behaviors must work before resuming exposed play.
