# Local Qwen integration and responsive controller

Reviewed 2026-09-09. This is the first implementation of the proposed layered
player. Factorio remained stopped throughout this work. Local inference is
verified; live defensive survival and a rocket launch are not.

## Local model setup

The downloaded Ollama tag is `qwen3.8:27b`, reported as 27.3B parameters and
Q4_K_M quantization, approximately 17.74 GB on disk. The test host has an Apple
M5 Max and 48 GiB unified memory. These are test conditions, not minimum
requirements or a measurement of simultaneous model/game performance.

`config/local-planner.json` is the durable project configuration: loopback
Ollama, 8,192 context tokens, at most 64 output tokens, temperature zero,
thinking disabled, 10-minute keep-alive, 15-second transport timeout and
3-second advice validity window. The adapter uses a direct persistent HTTP
connection and rejects remote endpoints, redirects, cloud-tagged models,
unexpected tool calls and decisions outside the supplied candidate IDs. It
neither downloads models nor executes model-generated code or game commands.

Verify the setup with the already-running local Ollama service:

```sh
python3 -m client.local_planner --probe
```

The first separate cold test took 3.46 seconds inside Ollama, including 2.62
seconds of model loading. Warm evaluation results are reported separately below.
API configuration follows [Ollama chat](https://docs.ollama.com/api/chat),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
and [thinking controls](https://docs.ollama.com/capabilities/thinking).

## Offline evaluation

| Measure | Observed result |
|---|---|
| Responses matching the expected selection | 48 / 50 |
| Structurally valid selections | 50 / 50 |
| Constructed cases | 40 / 40 |
| Historical snapshot cases | 8 / 10 |
| Median full request-to-decision time | 0.694 seconds |
| 95th percentile | 1.136 seconds |
| Maximum | 1.381 seconds |

The 40 constructed cases are five small variations of eight templates, not 40
independent encounters. The remaining ten cases use real snapshots from the
failed attempt, including near-duplicate observations. Candidate tasks and
expected answers are authored triage labels, not observed counterfactual game
outcomes or expert-reviewed optimal actions. This is a contract/latency and
basic-priority screen, not a held-out gameplay benchmark. No weights were trained.

Both mismatches occurred at 33/250 health: Qwen chose to gather route information
rather than immediately prioritize survival. All raw cases and failures are
preserved under ignored runtime storage. The prompt was not tuned on these
failures and the score was not replaced by a retest. Critical health is therefore
an unconditional local reflex trigger, outside model authority.

Reproduce with an unused output directory; the trace input must be supplied
privately. Without `--recorded`, only the 40 constructed cases run:

```sh
python3 -m client.benchmark_planner --output runtime/evaluations/new-evaluation
```

## Continuous observation and advice

`client.supervisor` polls fixed status/observation operations independently of
one daemon inference worker. It drains events using the last consumed sequence,
detects missing history, records health changes and discards decisions made
against changed state/character or exceeding the validity window. It never
starts a game, pauses, binds, submits a batch or sends a model-generated action.

The first release is **shadow advice only**. After a separately authorized
unpaused session is already running and bound, capture advice with:

```sh
python3 -m client.supervisor --shadow --seconds 60 --output runtime/advice/new-capture
```

The offline delay test advances 60 seconds of a simulated observation clock
while inference remains pending. It verifies 601 observations, a damage alert,
one in-flight inference and rejection of the stale result. It does not measure
real Factorio polling latency or demonstrate survival for 60 wall-clock seconds.

## Experimental tick-local reflex: source 0.4.0

The new fixed `guard` operation enables an optional early-game bullet-defense
routine. It is off by default. The source has not been installed in the Steam
client or validated in a live encounter.

- Checks nearby currently visible enemies every three ticks; a damage event
  requests a check on the next tick. Critical health also interrupts production.
- Stops the remaining batch with `defense_interrupt`. Already completed work
  remains; a new plan must be validated after danger clears. There is no blind
  batch replay or automatic post-combat production resumption yet.
- Selects an already-equipped pistol/submachine gun with compatible ammunition,
  uses the engine's `can_shoot` and normal shooting inputs, and chooses local
  collision-checked movement away from threats, optionally biased toward a rally.
- Does not grant or equip missing items, create projectiles, change damage or
  ammunition, ignore collision, reveal terrain, or pause the simulation.
- Explicit cancel and the on-screen Stop job button disable the reflex and
  clear movement/firing. Release also relinquishes it; death disables it.
- Damage evidence and enemy scans now omit current enemy information in fog.
  Scans include entity IDs and truncation; status includes event-loss metadata.

The local escape heuristic does not model acid/projectiles, find a global escape
path, prove that a rally is safe, or guarantee success against multiple biters.
The 3,600-tick Lua test checks inputs, interruption and shutdown in a mocked
world. It is not a real combat or sub-100-ms performance measurement.

## What must happen next

Review the source change, then validate normal firing and ammunition consumption
in Factorio before relying on it. Measure encounter outcomes and tick/wall
response time with the planner delayed. Improve escape behavior from those
results. Only then connect validated construction skills to model task choices.
Full factory scheduling, demonstrations, reinforcement-learning updates,
generalization evaluation, oil/later science and rocket capability remain future
work. The user-requested stopped game and its failed checkpoint are preserved.
