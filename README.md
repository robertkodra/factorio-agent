# Factorio agent controller

A local, tick-driven controller for Factorio **2.0.77**, tested on macOS with Steam. The planner submits batches; the game executes ordinary walking, mining, crafting, item-funded construction, transfers, and research on its own ticks. Python 3 uses only the standard library.

Controller **0.2.0** uses a fixed `/codex-agent` JSON interface over persistent RCON. A standard MCP protocol facade remains on the [roadmap](ROADMAP.md). Base gameplay is enabled, with Space Age, Quality, and Elevated Rails disabled. The control-only mod changes no prototypes or recipes.

This is an experimental **tool-assisted vanilla-mechanics benchmark**. It has demonstrated conveyors, electricity, and red/green science production. It has not completed a fresh run under the current no-console-Lua policy, green-consuming research, robotics, or a rocket launch. No human speedrun eligibility or record is claimed.

## Start here

- [Setup and continuation](HANDOFF.md)
- [No-cheats policy](POLICY.md)
- [Progression and MCP roadmap](ROADMAP.md)
- [Knowledge base](knowledge/README.md) and [dry-run results](knowledge/dry-run-001.md)
- [Publication and contribution privacy](PUBLICATION.md)

The public repository contains reviewed source, tests, plans, static recipe data, and summarized findings. Historical saves, raw observations, runtime configuration, credentials, and original Git history are kept separately in a private archive. Clone this repository afresh; do not push old experiment branches into it.

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

Authoritative movement was measured; visual smoothness was not measured frame by frame. The viewer usually follows in spectator mode, but remains attached during hand crafting so normal craft statistics and research triggers work. The engineer walks normally; only the spectator camera is moved by script.

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

Fixed operations: `hello`, `bind`, `release`, `observe`, `scan`, `inspect`, `factory`, `research_state`, `submit`, `status`, `cancel`, `pause`, `save`.

Actions: `walk`, `mine`, `craft`, `await_craft`, `place`, `put`, `take`, `wait_inventory`, `research`, `set_recipe`, `rotate`, `wait_ticks`.

- One active batch, with 1–512 actions. Structural validation occurs before enqueueing; gameplay preconditions are checked when a step executes. Failures stop the batch, preserving completed work.
- Construction checks reach, collision, and real inventory costs. It creates entities through the mod API and does not reproduce every player-input statistic/event.
- Transfers check reach, quantity, and destination capacity. Recipe changes require an empty idle machine.
- Scans are limited to charted chunks and a maximum radius of 128. This is structured observation, not a screen-only interface.
- Normal speed, cheat mode, and the allowed mod set are checked during binding, submission, and active execution. RCON is trusted local administration, not an adversarial sandbox.
- Job state and bounded events persist in saves. There are limits of 256 stored jobs and 2,048 in-save events; status supports an event cursor. Raw event files remain in ignored runtime storage.

Navigation can oscillate around trees and poles. Construction needs fuller footprint/power checks, inventory aliases need later-game coverage, and automated supply scheduling remains incomplete. Oil, robotics, and rocket actions need their own live validation. Read the [next-run notes](knowledge/next-run.md) before longer attempts.

## Local verification and planning

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_publication.py --history
python3 -m client.materials '{"assembling-machine-1":2,"inserter":2,"automation-science-pack":40}'
```

The material calculator uses static [2.0.77 recipe data](data/README.md); it covers the tested early deterministic solid-item recipes. Recipe-time sums are not elapsed gameplay predictions. `python3 -m client.factory` reads the current factory when a server is running.

Live test commands and their prerequisites are documented in [HANDOFF.md](HANDOFF.md); they are deliberately excluded from normal unit-test discovery.

References: Factorio's [LuaControl API](https://lua-api.factorio.com/2.0.77/classes/LuaControl.html) and developer discussion of [scripted movement and multiplayer latency hiding](https://forums.factorio.com/viewtopic.php?t=63415).
