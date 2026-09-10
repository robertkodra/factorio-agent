# Factorio agent controller

A local, tick-driven controller for Factorio **2.0.77**, tested on macOS with Steam. The planner submits batches; the game executes ordinary walking, mining, crafting, item-funded construction, transfers, and research on its own ticks. The direct Python clients use only the standard library.

Controller development source **0.8.1** uses a fixed `/codex-agent` JSON interface over persistent RCON. An optional [MCP stdio facade](MCP.md) exposes its 19 fixed operations with validated schemas (Python 3.10+ and separate dependencies). Base gameplay is enabled, with Space Age, Quality, and Elevated Rails disabled. The control-only mod changes no prototypes or recipes. The reflex has passed a limited live defensive encounter; broader survival remains under test.

The [smelting state-mirror slice](knowledge/state-mirror-001.md) adds a bounded
owned-entity read, per-domain freshness, event/receipt reconciliation and measured
private replay. Source 0.8.1 has not been installed or live-tested in this work.
The 0.8 integration baseline and this slice have separate draft review boundaries.

The [architecture review and next acceptance gates](knowledge/review-response-001.md)
supersede the earlier implementation priorities. Oil Gathering completed in
checkpoint practice; oil production, blue science and a launch remain unverified.
The scheduler still needs manually surveyed plans. Development now prioritizes
a state mirror, production graph and verified layout compilation. These are
planned capabilities, not a claim that controller 0.8 is a general factory agent.

The [local Qwen integration](knowledge/local-controller-001.md) is configured and
tested through Ollama: 48/50 expected offline choices, 0.694-second median
response. A persistent shadow supervisor and experimental tick-local defense
source are implemented. A [persistent factory scheduler and rocket budget](knowledge/rocket-controller-001.md) now extend the production path. The [buffered-production update](knowledge/production-oil-001.md) adds manufacturing
geometry, stocked cells and measured production auditing. This is not autonomous
rocket readiness.

This is an experimental **tool-assisted vanilla-mechanics benchmark**. It has demonstrated conveyors, electricity, and red/green science production historically. A [fresh conveyor responsiveness test](knowledge/responsiveness-001.md) now passes under the current no-console-Lua policy. A separate [enemy-enabled learning attempt](knowledge/learning-001.md) completed Automation and Gun turret and verified one loaded turret. A [checkpoint continuation](knowledge/rocket-controller-001.md) now completes Military 2 through supplied red/green labs. Repetition from a fresh map, robotics and a rocket launch remain pending. No human speedrun eligibility or record is claimed.

## Start here

- [MIT license](LICENSE) and [contribution and branch rules](CONTRIBUTING.md)
- [Setup and continuation](HANDOFF.md)
- [Connect an agent through MCP](MCP.md)
- [Gameplay strategy](knowledge/strategy.md) and [learning results](knowledge/learning-001.md)
- [Live responsiveness measurements](knowledge/responsiveness-001.md)
- [No-cheats policy](POLICY.md)
- [Progression and MCP roadmap](ROADMAP.md)
- [Knowledge base](knowledge/README.md) and [dry-run results](knowledge/dry-run-001.md)
- [Publication and contribution privacy](PUBLICATION.md)

The public repository contains reviewed source, tests, plans, static recipe data, and summarized findings. Historical saves, raw observations, runtime configuration, credentials, and original Git history are kept separately in a private archive. Clone this repository afresh; do not push old experiment branches into it.

Original project code and documentation are available under the [MIT License](LICENSE).
Factorio and its assets belong to Wube Software and are not licensed or distributed
by this repository. Third-party dependencies retain their own licenses.

## Historical measurements

| Experiment | Observation |
|---|---|
| First conveyor sequence | 29 actions, 12 belts; 7,504 elapsed ticks / 125.07 game seconds, including a final 12-second flow wait |
| Belt placement | 12 consecutive placements, one per tick after crafting |
| Persistent RCON status | 60 samples: median 16.60 ms, p95 19.69 ms |
| Earlier MCP reference | Median 33.5 ms in a separate sample; not a controlled A/B comparison |
| Production extension | Four more belts, verified ore flow; 66.82 ms batch submission |
| Movement and concurrency | Maximum observed displacement 0.14916 tiles/tick; hand crafting overlapped walking |
| Save recovery | A saved walking job continued after a process restart with preserved engineer state |
| Science dry run | 114 red packs, 20 green packs, Automation and Logistics completed; 31:26 game / 32:25 wall time from a continued save |

These are summaries of private historical evidence. Conveyor timings start at submission and exclude preparation and model reasoning beforehand. The science run includes planning, failures, recovery, and debugging. It did **not** complete research consuming green packs. See the [report](knowledge/dry-run-001.md) for corrected milestones and limitations.

Authoritative movement was measured; visual smoothness was not measured frame by frame. The viewer initially follows in spectator mode; native hand crafting attaches it to the engineer and retains ownership so normal craft statistics and research triggers work. The engineer walks normally; only the spectator camera is moved by script.

## Running a plan

After following setup, joining a new map, and dismissing the introduction with Tab:

```sh
python3 client/agent.py '{"op":"bind"}'
python3 -m client.run_plan plans/first-belts.json
python3 client/agent.py '{"op":"status"}'
```

The first plan assumes seed `20260906` and default starting inventory. The extension plan assumes the completed first plan's inventory and layout. Do not use either against an unrelated factory. Use `--id` for an intentional new execution. Repeating the same job ID and actions retrieves the existing job; different actions with that ID are rejected.

Keep one connection open for interactive planning:

```python
from client.agent import Agent

with Agent() as game:
    state = game.request("observe")
    nearby = game.request("scan", name="iron-ore", radius=64, limit=10)
    job = game.request("submit", id="brief-wait", actions=[
        {"type": "wait_ticks", "ticks": 60},
    ])
    status = game.request("status", id="brief-wait")
```

After an uncertain transport failure, reconnect and inspect the same job ID. The client does not replay mutations automatically. A client timeout does not cancel the job. The on-screen Stop job button or `{"op":"cancel"}` stops the remaining batch and movement/mining; already queued hand crafting continues. `release` gives the engineer back to the human player; `bind` restores controller ownership.

## Interface and limits

Fixed operations: `observe_entities`, `prototype`, `hello`, `bind`, `release`, `observe`, `scan`, `survey`, `placement`, `inspect`, `factory`, `research_state`, `guard`, `submit`, `status`, `cancel`, `interrupt`, `pause`, `save`.

Actions: `walk`, `mine`, `craft`, `await_craft`, `place`, `put`, `take`, `wait_inventory`, `research`, `set_recipe`, `rotate`, `wait_ticks`, `limit_chest`, `launch`.

- One active batch, with 1–512 actions. Structural validation occurs before enqueueing; gameplay preconditions are checked when a step executes. Failures stop the batch, preserving completed work.
- Construction checks reach, collision, and real inventory costs. It creates entities through the mod API and does not reproduce every player-input statistic/event.
- Transfers check reach, quantity, and destination capacity. Recipe changes require an empty idle machine.
- Scans are limited to charted chunks and a maximum radius of 128. This is structured observation, not a screen-only interface.
- Normal speed, cheat mode, and the allowed mod set are checked during binding, submission, and active execution. RCON is trusted local administration, not an adversarial sandbox.
- Job state and bounded events persist in saves. There are limits of 256 recent full jobs, 65,536 compact idempotency receipts and 2,048 in-save events; status supports an event cursor. Raw event files remain in ignored runtime storage.

Navigation detects lack of progress, tries alternative service positions and can use configured travel corridors. The [persistent scheduler](plans/AUTOPILOT.md) supplies configured cells and checks research/launch evidence. Local placement checks do not prove power/fluid/inserter connections. General factory layout, oil, robotics, and rocket execution still need live validation. Start with the [strategy playbook](knowledge/strategy.md) and [next-run notes](knowledge/next-run.md) before longer attempts.

## Local verification and planning

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_publication.py --history
python3 -m client.materials '{"assembling-machine-1":2,"inserter":2,"automation-science-pack":40}'
```

The material calculator uses static [2.0.77 recipe data](data/README.md); it covers the tested early deterministic solid-item recipes. Recipe-time sums are not elapsed gameplay predictions. `python3 -m client.factory` reads the current factory when a server is running.

Live test commands and their prerequisites are documented in [HANDOFF.md](HANDOFF.md); they are deliberately excluded from normal unit-test discovery.

References: Factorio's [LuaControl API](https://lua-api.factorio.com/2.0.77/classes/LuaControl.html) and developer discussion of [scripted movement and multiplayer latency hiding](https://forums.factorio.com/viewtopic.php?t=63415).
