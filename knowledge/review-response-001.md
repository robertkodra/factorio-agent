# Architecture review response — 2026-09-10

The review's central diagnosis is supported: fixed actions and private evidence
are useful foundations, while the current scheduler still depends on manually
surveyed sites, sources and service positions. Keep the executor and change the
planning layer. Finishing more checkpoint errands is insufficient evidence of a
general factory agent. This document supersedes the next-work priorities in the
[earlier improvement analysis](improvement-plan-001.md); historical failures remain.

## Findings checked against this checkout

The installed controller reports 0.8.0. Oil Gathering has a native, non-scripted
completion record. The final recorded factory contains 825 entities, including
599 transport belts, and no launch event. No active research was selected in that
snapshot: idle labs alone therefore do not demonstrate starvation. Earlier
starvation and unjustified stock accumulation are separately documented.

The four completed recording intervals total about 13.5 wall minutes and 1.43 GB
of journals. Their wall spans are summed separately; gaps between phases are not
included. Linear extrapolation gives approximately 12.7 GB over two hours, not a
measured two-hour run. Repeated full observations impose a storage cost; CPU and
RCON contributions to gameplay delay still need profiling. Reducing journal size
alone will not prove a faster or more responsive controller.

| Recorded phase | Completed / reconciled jobs | Median / p95 native inter-job gap | Outcome |
|---|---:|---:|---|
| Initial supply | 38 / 39 | 0.167 / 48.400 s | One insufficient-items failure; supply starvation prompted intervention |
| Upstream supply recovery | 50 / 50 | 0.167 / 5.567 s | Oil Gathering verified complete |
| Direct-feed preparation | 8 / 8 | 0.150 / 30.333 s | Placement target incomplete; repair bootstrap blocked |
| Repair continuation | 10 / 10 | 0.150 / 1.083 s | Infrastructure placement verified; sustained output not verified |

These are different tasks with code/plan interventions, not an A/B speedup.
Native job intervals exclude preparation before the first job and time after the
last. They do not measure enemy reaction, model inference or rendered smoothness.
The small final gaps do not invalidate the user's observed long periods without
useful progress.

The documented system-Python test command reproduced three defense failures.
The first health poll used zero as a previous monotonic timestamp; a clock close
to zero could skip it. A fresh/resumed runner now samples immediately, then
applies the half-second interval. A deterministic zero-origin test covers both
startup and resume. A separate regression ensures paginated native damage events
are consumed before a newer summary can advance their sequence.

Validation after those changes: all 140 tests pass in the project environment;
system Python passes 129 tests and skips the 11 optional MCP tests. Neither
command starts a live game or measures response to a natural attack.

At closure, the server remained running, the latest job was complete, no gameplay
scheduler was running, the guard was disabled and character observation returned
`no_bound_character`. This is not proof of death or explicit pause. A new private
checkpoint passed ZIP integrity and SHA-256 verification. The development ledger
is closed; all four journals and interventions remain available. Do not resume
the old repair scheduler automatically.

The private archive audit and earlier publication counts quoted by the supplied
review were not independently repeated for this assessment. A passing executor
test suite does not validate an opening, combat policy or rocket route.

## Scope and constraints

Use an explicitly declared agent/tool-assisted benchmark. The published human
leaderboard rules forbid mods and restrict commands, so this mod-controlled
architecture must not be presented as human leaderboard eligible.
[Rules clarification](https://www.speedrun.com/factorio/forums/5typt).
The refreshed Default Settings 2.x leaderboard lists Zaspar's 1:59:01 on 2.0.77;
it is a reference, not a directly comparable score for our development sessions.
[Leaderboard](https://www.speedrun.com/factorio?h=Default_Settings-2-x-x&x=7dg85xp2-p85yzj0l.14o74req).

Pin base 2.0.77, default settings, enemies, one controller, normal costs and
visibility. For scored attempts, freeze source/model/configuration identities,
count wall time from the declared start through the native launch event, and
allow no gameplay pause, reload or human gameplay input. Record automatic pauses,
disconnections and failures rather than silently excluding them. A setup-only
period must be declared and must not supply advance map knowledge.

Keep Qwen as asynchronous advice over validated alternatives. Mandatory emergency
inputs must continue while any model or strategic planner is delayed. No model
training is required for the next gate. Research documents and prompt changes
are not reinforcement learning.

## Work packages and acceptance gates

1. **Identify the review baseline.** Review the 0.8 executor, transfer changes and
   experimental recovery options separately. Test standard-library Python and
   the MCP environment, recording skipped optional dependencies. Reconcile the
   stacked drafts into a reviewed integration baseline before calling it stable;
   preserve review history and do not merge merely to tidy branch names.

2. **Build a state mirror.** Keep one sequenced view of observed owned entities,
   player state, research and receipts. Consume native damage/destruction and
   completion events where available. For inventory, fluids and continuously
   changing production, use bounded targeted observations and periodic compact
   checkpoints; do not assume the engine provides every desired delta event.
   Include world/actor identity, visibility scope and freshness. Sequence gaps
   invalidate planning until reconciled; a planner stall must not block native
   emergency handling. Unknown mutations still require job-ID reconciliation.

   Pass deterministic reconstruction against retained snapshots, including
   destruction, repair, duplicate/page boundaries, disconnects and stale plans.
   Measure bytes, observation cost and event-to-action delay separately. An
   initial storage target is at least 90 percent reduction on the same replayed
   observations without losing required evidence; this is a target, not a result.

3. **Diagnose and compile one production block.** Model source, mining, transport
   lane, inserter, machine, buffer and consumer connections, plus power and fluid
   constraints. Separate expected geometry from observed operation. Replay our
   broken coal feed, full mixed-input chest and science-lane failures; diagnosis
   must identify the missing or blocked connection without hard-coded site IDs.

   Compile one smelting block from a charted resource patch and a throughput
   request into a bill of materials, reachable stances, connections and ordered
   actions. Validate another location without editing coordinate-specific code.
   Live acceptance requires ten game minutes of promised downstream output,
   supplied fuel/power and no manual inventory repair. Include ramp-up, starvation
   and material cost. Placed buildings alone cannot satisfy this gate.

4. **Plan backward from launch.** Reserve inputs and size production by phase and
   deadline, including startup stock, infrastructure, mining, power, logistics,
   travel and defense. The current rocket-material estimate omits these costs;
   an early furnace row is not expected to supply the entire two-hour route.
   Validate predicted versus actual supply and research splits before expanding
   to connected oil, blue science, later science and a silo.

5. **Establish capability, then performance.** A checkpoint rocket is an
   integration milestone. Follow it with a clean fixed-seed launch without
   mid-run edits, then at least five previously unseen seeds selected after the
   implementation is frozen. Report every attempt and completion rate. Five
   seeds are an initial generalization check, not strong statistical evidence.
   Only then pursue sub-four-, sub-three- and sub-two-hour wall-time targets.

The next concrete deliverable is the state mirror with reconstruction tests and
flow diagnostics, followed by the single compiled smelting block. The factory
graph, general compiler, backward phase planner and clean benchmark harness are
not implemented by this review response.
