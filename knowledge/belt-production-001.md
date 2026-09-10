# Belt-fed production development

This is checkpoint practice, not a fresh timed run or a rocket demonstration.
Exact coordinates, saves, source identities, job journals and samples stay private.
The practice runs at normal game speed without gameplay pause commands.

## Implemented

- Directed surface-belt routes and bounded nearby placement batches, each locally
  preflighted before any included tile is submitted.
- An infrastructure construction target, separate from research/throughput claims.
- Eight-furnace row and opposing 12-by-2 / 24-by-2 layout templates. Only the
  smaller row has been constructed live; the larger templates are unit-tested.
- Normal tree mining for explicitly enabled, locally observed belt obstructions.
- Construction waypoint checks against newly built machinery, including generated
  intermediate destinations. Inserters are no longer accepted as standing points.
- Handcrafting can overlap travel. An initial version oscillated between queued
  build sites; the corrected planner waits at the first site until stock exists.
- A cadence audit that includes failed jobs and long gaps rather than presenting
  only the fast median.
- Controller 0.7.0 adds a typed underground-belt input/output placement option,
  ordinary item costs/preflight and owned endpoint/line observations. The pinned
  2.0.77 API supports this endpoint type in normal entity construction.
  [Native API](https://lua-api.factorio.com/2.0.77/classes/LuaSurface.html#create_entity).

## Initial live findings on controller 0.6.0

A 190-tile coal conveyor, an electric coal drill and a powered inserter now feed
steam generation. The boiler reached its native automatic fuel buffer and stayed
supplied while construction continued. This is stronger evidence than placement
alone, but does not establish indefinite fuel or ore availability.

An eight-furnace row receives coal and iron ore on separate lanes. Five electric
iron drills supply it. All eight furnaces were observed working after correcting
a disconnected power span. The initial unloading design used one inserter and a
chest; output eventually backed up. A roughly nine-and-a-half-minute sample
averaged about 110 iron plates/minute, below the row's nominal capacity. The
unloading restriction must be corrected before claiming sustained capacity.

The completed coal-belt scheduler phase reconciled 86 jobs with no execution
failure, but had placement-preflight stops and normal obstacle clearing. Its
median native gap between jobs was about 0.13 seconds; its longest was about
65 seconds. The first furnace scheduler phase had 14 failed jobs, and the next
access revision had three more. Generated waypoints crossing new drills were a
major cause. Preserve all these phases; the corrected continuation does not erase
them. Later gaps and failures remain in the private journal and final audit.

## Strategy correction

Experienced-player feedback correctly identified that a slow transport retrofit
is not a competitive opening. Bootstrap abundant plates by hand, automate gears,
circuits and construction supplies, then build planned smelting blocks and a bus.
See [the updated strategy](strategy.md). Favor output and useful work during
planning over constructing long empty belts. Qwen remains outside production
inputs; these changes improve controller policies, not model weights.

## Continuation on controller 0.7.0

The initial ledger closed after about 32.4 game minutes, with 444 terminal jobs:
427 completed and 17 failed. No new damage, death or gameplay pause transition
was recorded. A verified checkpoint was saved, then the server was stopped and
restarted to install 0.7.0. This development interruption is retained separately;
the continuation is not a clean timed run.

Logistics completed through normal research. An earlier attempt to craft its
locked underground recipe failed without spending items and remains recorded.
The installed underground endpoints report reciprocal native neighbours, and
iron was observed on both ends. The return belt now feeds the gear and circuit
input buffers and a nearby construction reserve.

Replacing the single-inserter unloading choke with continuous belt improved a
later three-minute sample to about 129.6 iron plates/minute. This is a shorter,
different operating interval, not a controlled speed comparison or proof of the
row's nominal 150/minute. Some output remains backed up as downstream demand
and transfers limit consumption.

The production scheduler now balances required science colours before topping
up abundant packs, and takes larger available intermediate batches to amortize
travel. An optional nearby-inventory transfer avoids unnecessary service-stance
walks; the native reach check remains authoritative. These changes have unit
coverage; their effect on full-run completion time still needs measurement.

Connected copper/steel supply, autonomous science, repeated enemy response and
a rocket still need proof. Downstream ingredient hauling remains a major limit.
