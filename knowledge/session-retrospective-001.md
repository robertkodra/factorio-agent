# Paused practice: what we learned

The user explicitly requested a pause and review. The game is paused, the
gameplay executor has exited, and the passive watcher has stopped. The new
checkpoint passed ZIP integrity and SHA-256 verification. Its exact identity,
timing, pause transition and final observations are recorded privately. Keep
the game paused until the user requests continuation; do not interpret the
unfinished rocket objective as permission to restart this practice.

## Outcome and evidence

The controller has progressed from two early deaths to one separately measured
survived encounter with fourteen small biters, then to a larger working factory.
Military 2, Engine and Fluid handling are completed. At the final paused snapshot,
Oil gathering is about 21 percent complete and the engineer has full health.
There is no rocket launch, oil-production demonstration or blue science.

The latest construction sequence verified eight working iron furnaces, four
working steam engines, four consuming labs, separate science lanes and a
three-turret cluster distributing real ammunition. Those observations were made
at specific points during the sequence; they are not sustained-capacity or
combat-coverage guarantees. Copper and some ingredients still require carrying.

This was extended checkpoint practice with development interventions, earlier
failures and an explicitly requested final pause. It is not a fresh speedrun
baseline or evidence of human leaderboard eligibility. No model weights were
trained. The improvement so far is in controller code, layouts and recorded
operating rules.

## Failures that changed the design

| Failure | Evidence and cause | Rule for the next controller |
|---|---|---|
| Reacting too late | In the first attempt, critical health was visible but planning continued; two deaths followed. Later, factory damage preceded arrival by about 203 game seconds, including roughly 28 seconds of final travel. | Emergency handling must run independently of strategic deliberation and cover both engineer and factory. Measure detection, dispatch and arrival separately. |
| Watching without acting | The engineer-local reflex did not see the remote attack. The factory recorder had evidence but no dispatch authority. | One action owner must accept priority interrupts from continuous monitoring. A logging process is not a defender. |
| Declaring repairs too early | Replacing thirteen visibly lost belt tiles missed other coal belts, a coal drill and power connections. These absences were already present in the attack snapshot. | Validate the entire source-to-consumer path and actual downstream output after repair. Do not attribute every missing entity to enemies without evidence. |
| Starving critical consumers | An upstream spare-coal intake intercepted boiler fuel. An iron-filled shared chest blocked circuit cable. | Put critical consumers before surplus storage; prefer recipe-limited direct feeds or explicitly bounded ingredient buffers. |
| Counting production instead of progress | Red and green packs shared a congested lane. Pack output continued while useful research intermittently stalled. | Separate incompatible flows and measure simultaneous lab consumption and native research completion. |
| Excessive travel and redesign | Small pickups, scattered build order and late transport retrofits generated repeated trips. Neutral wrecks invalidated planned routes. | Check geometry before construction, group work geographically, overlap normal crafting with travel and carry useful batches. |
| Losing defense when production failed | A blocked construction preflight originally terminated the Python executor. | Production suspension must preserve defense and essential maintenance. The implemented correction covers this rejection, not every process or transport failure. |

The nearby northeast nest is a plausible attack source; we did not establish
which nest spawned that group. The turret cluster's ammunition distribution was
verified, but its response to another actual attack was not measured.

## What to build before another extended run

1. **Complete the emergency path.** Add bounded events for owned-factory damage
   and destruction, including event-overflow detection, and an atomic interrupt
   that preserves the local guard. Keep the observation scope within policy.
   The current half-second health comparison can miss destruction between reads
   or damage hidden by repairs; cancel and guard restoration are two commands.
   Test these failures offline before a separately authorized natural encounter.
2. **Make supply recovery check the whole chain.** Diagnose fuel, power, material
   intake, inserter reach, belt continuity and output at critical consumers.
   Treat repairs as incomplete until output resumes. Check shared-buffer capacity
   and lane assignments before constructing the next production block.
3. **Replace repeated errands with prepared construction and supply batches.**
   Adopt the user's hand-fed startup, then planned furnace blocks, transport and
   a small construction mall. Reserve space and resources for expansion instead
   of laying long belts before their consumers are ready. Choose block sizes
   from the production budget; copying a large bus is not itself a faster route.

Grenade use remains a missing normal-mechanics capability. Add it as a narrow,
tested action before attempting grenade kiting; do not assume a firing reflex
already knows safe grouping, throwing and escape behavior. Expand the small
turret cluster only when observed approach coverage or ammunition demand requires
it. A full ring is a candidate layout, not a requirement for every outpost.

## Bounded validation before scaling up

Proposed gates below are targets, not measured results. Gameplay tests wait for
the user's next explicit continuation request and retain all failures.

- For each observed natural attack, record first event, detection, production
  interruption, defensive action, arrival, losses and ammunition. Aim for a
  95th-percentile event-to-defensive-input time below 250 ms; report sample size
  and worst case, and do not include travel in that latency claim.
- Exercise an attack during construction, a placement rejection and a planner
  delay. Verify defense survives each condition without duplicate production
  actions or disabling the guard. Test transport failure offline first.
- Run a ten-game-minute supply segment with no manual inventory fixes. Require
  continuous essential fuel supply and monotonic research progress while
  recording starvation duration and useful throughput. A failure remains a
  failed segment even if later repaired.
- Account for time spent travelling, executing, waiting for materials and waiting
  for planning. Reduce unnecessary idle gaps and repeated trips before tuning
  model response latency. Compare the same prepared segment across attempts.

Qwen stays outside the emergency path. Its earlier live shadow captures had
median latencies around 1.5–3.1 seconds and discarded stale advice; its faster
offline score did not predict game-time behavior. Use it for asynchronous
choices among validated plans only after shadow evaluation. Faster inference
cannot repair an unobserved attack or a blocked ingredient feed. Demonstrations
and repeated held-out runs should precede any decision to train a policy.

The next gameplay objective, when authorized, is reliable oil extraction and
science supply from this checkpoint. A separate fresh-map opening test should
evaluate the revised bootstrap. Full rocket completion comes before making a
competitive performance claim.

## Evidence trail

- [Original deaths and response failures](rocket-attempt-001-review.md)
- [Local model evaluation and its limits](local-controller-001.md)
- [Measured defensive encounter and live Qwen latency](live-defense-001.md)
- [Remote factory attack, partial repair and watch correction](factory-defense-001.md)
- [Supply recovery and boiler priority](supply-recovery-001.md)
- [Circuit input and science lane correction](science-flow-001.md)

These earlier reports retain their historical stopping points. This paused
state supersedes their instructions to continue running an executor.
