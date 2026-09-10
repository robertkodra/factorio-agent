# Agent connection through MCP

The optional stdio server exposes the 16 fixed controller operations to MCP
clients. It uses the [official Python SDK](https://github.com/modelcontextprotocol/python-sdk)
and validates calls against the same JSON Schemas it advertises. The original
RCON clients still use only the Python standard library.

## Install and connect

Use Python **3.10 or newer** for MCP; validation used Python 3.12. From this
repository, create a local environment:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-mcp.txt
.venv/bin/python -m unittest discover -s tests -v
```

The server command is `.venv/bin/python scripts/run_mcp.py`. Use absolute paths
in a client's configuration; the launcher works from any working directory.
It speaks MCP on stdin/stdout and connects only to loopback RCON. It does not
start Factorio, create a map, install a mod, or bind an engineer automatically.
Follow [HANDOFF.md](HANDOFF.md) for those explicit setup steps.

For Codex, run this from the repository root:

```sh
codex mcp add factorio -- "$PWD/.venv/bin/python" "$PWD/scripts/run_mcp.py"
codex mcp get factorio
```

This saves the local launcher in Codex's user configuration. Consult the
[official MCP configuration guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
for project-scoped configuration or other clients. Reload the MCP connection
in the host, or start a new session if it does not refresh its tool catalog.
Discovery works while Factorio is offline; gameplay calls return
`connection_unavailable` until the game server and credential file are ready.

Defaults are port `27016`, the checkout's `runtime/rcon-password`, and a
5-second RCON exchange timeout. Optional launcher arguments are `--port`,
`--password-file`, and `--timeout` (at most 30 seconds). Credentials remain in
the private file; the MCP interface accepts no host, credential, file, shell,
console, or Lua arguments.

## Tools and workflow

| Tools | Purpose |
|---|---|
| `hello` | Verify controller version and operations before playing |
| `bind`, `release` | Take control of an existing connected engineer or return it to the viewer |
| `observe`, `scan`, `inspect` | Read engineer state and charted/reachable surroundings |
| `survey`, `placement` | Read nearby charted water/pollution and local normal-placement preflight (controller 0.3.0+) |
| `factory`, `research_state` | Inspect production and completed research |
| `guard` | Enable experimental normal-input bullet defense; off by default; limited live defense validated |
| `submit` | Enqueue one bounded batch and return immediately |
| `status`, `cancel` | Track or stop the active job without waiting for its planned duration |
| `pause`, `save` | Record an explicit pause/resume or request a private checkpoint |

Start with `hello`, then `bind` and `observe`. Submit a job with a stable ID:

```json
{
  "id": "opening-wait-001",
  "actions": [{"type": "wait_ticks", "ticks": 60}]
}
```

Call `status` with `{"id":"opening-wait-001"}` to observe completion. Passing
the ID to `cancel` guards against accidentally cancelling a different job.
The 13 action schemas cover walking, mining, crafting, waiting for crafting,
placement, transfers, inventory waits, research selection, machine recipe
selection, rotation, tick waits, and normal rocket launch. The mod applies default values and checks
all actual gameplay conditions. Unknown fields, invalid bounds, nonfinite
numbers, invalid action types, and oversized batches are rejected before RCON.
Optional fields should be omitted rather than set to `null`.

Controller 0.3.0 adds `inventory: "ammo"` for normal transfers to/from an
ammunition turret, plus ammunition contents in its factory snapshot. It does not
add shooting, equipment or repair actions. `placement` applies to a building
with an identically named placement item, within ten tiles of the engineer; it
checks the current stance, reach and collision, without reserving an item or
proving power coverage. `survey` never charts new chunks. A water query returns
at most 100 nearest water tiles and reports the total before truncation.
Factorio's character placement check returns false while the simulation is
explicitly paused. Check pause state and perform placement preflight during a
recorded running interval; a false result while paused does not prove collision.

Controller 0.3.1 queues crafts through the owning player and retains ownership
after completion. Native player-crafted events are recorded, and `research_state`
also lists currently enabled recipe names. A fresh lab craft must actually unlock
red science; recipe costs or a lab in inventory are insufficient evidence.

Controller 0.3.2 exposes the engineer's ammunition slots as `observe.ammo`.
For `put` and `take`, `player_inventory: "ammo"` selects those slots as source
or destination; the default remains `"main"`. This is separate from
`inventory: "ammo"`, which selects the turret's inventory. Native crafting can
put magazines into equipped ammunition slots, so inspect both before budgeting
a transfer. The game still checks reach, item count and destination capacity.

A walking job now requests at most two recovery paths for lack of measurable
progress towards its current waypoint. Movement stops during path requests.
This bounds oscillation; the planner must still select a reachable service
position or choose an ordinary mining action to clear an obstruction.

## Recovery and limits

Source 0.4.0 adds `guard` with `enabled` and an optional nearby charted `rally`
position. It interrupts remaining production on danger, uses equipped weapons
and normal movement/firing. A limited [live encounter](knowledge/live-defense-001.md) passed; broader survival remains unproven. Both `cancel` and the
Stop job button disable it. Completed actions and queued crafts remain. See
the [implementation report](knowledge/local-controller-001.md) for exact limits.
`observe` exposes equipment and guard state; `status.events_lost` flags an
expired cursor. Enemy scans and damage causes now require current visibility,
not merely previously charted terrain.

- `submit` does not wait for the batch to finish. `status` and `cancel` share
  the persistent connection and wait only for earlier RCON exchanges, bounded
  by the exchange timeout. Tool discovery remains responsive during an exchange.
- A confirmed controller rejection returns `controller_rejected`; completed
  earlier work in a failed gameplay batch remains. Inspect status to recover.
- A lost or malformed response returns `transport_failure`, `outcome: unknown`,
  and, for submissions, the exact `status` call needed to reconcile the job.
  The next explicit call opens a new connection. The bridge never replays a call.
- A connection/authentication/setup failure before dispatch returns
  `connection_unavailable`, `outcome: not_sent`. No gameplay request was sent.
- Cancelling an MCP request is distinct from cancelling the game job. An
  in-flight RCON exchange consumes its reply or times out before the socket is
  reused. Use the `cancel` tool to stop remaining game actions. Already queued
  hand crafting continues normally, including after release or disconnection.
- For event paging, use the last returned event's `seq` as `after`, not the
  global `sequence`. The controller retains 2,048 events, 256 recent full jobs and up to 65,536 compact job receipts;
  clients must record evidence privately and account for missing old events.
- A successful `save` call acknowledges a request. Verify the checkpoint file
  and its hash separately. It does not prove a milestone or fresh-map provenance.
- If a reload reports `no_bound_character`, connect the viewer, bind its existing
  engineer and compare against the checkpoint state before continuing. The
  learning run required this after a controller upgrade; automatic recovery of
  a player-owned character is not yet established.

The [live responsiveness report](knowledge/responsiveness-001.md) records a fresh
29-action conveyor sequence, observation/cancellation timings, reconnect behavior,
and the measured large-batch validation improvement.

MCP is the connection layer, not a production planner or an unattended player.
Navigation, sustained supply, clean-run evidence, later science, robots, and
rocket actions retain the limitations in [ROADMAP.md](ROADMAP.md).

## Validation

Ordinary MCP tests require no game. They cover SDK initialization/discovery,
all advertised tools and action shapes, invalid inputs before transport,
stdio startup from another directory, persistent RCON, dropped submissions,
explicit reconnect/status/cancel, definite rejection, and cancellation during
an exchange. CI installs the optional dependencies so these tests cannot
silently skip. Without the dependencies, the original standard-library tests
still run and MCP tests report explicit skips.

Optional live compatibility check, with an authorized private historical fixture:

```sh
.venv/bin/python -m tests.handoff_live --save runtime/checkpoints/dry-run-001-green-science.zip --mcp
```

This starts its own isolated server on temporary loopback ports and stops it
afterward. It reads fixed observations and submits/cancels a wait job in a
disposable, auto-paused copy. It verifies the base/controller mod allowlist and
unchanged tick, inventory, position, and source checkpoint hash. All raw output
stays under ignored `runtime/`. This is a historical compatibility test, not a
clean gameplay run, navigation test, or demonstrated rocket capability.


Controller 0.5.1 uses native stack transfers, including partially spent
ammunition. Semantic `input` and `output` inventories cover assemblers, furnaces,
labs and silos. `factory` includes fluid boxes, power-network IDs, machine status,
research completion records and actual rocket-launch events. Submit
`{"type":"launch","entity":"rocket-silo","x":0,"y":0}` only for a real, ready,
owned silo at its actual reachable coordinates. The example coordinates are
placeholders. Successful submission/order is not launch completion.
