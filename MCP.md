# Agent connection through MCP

The optional stdio server exposes the 13 fixed controller operations to MCP
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
| `factory`, `research_state` | Inspect production and completed research |
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
The 12 action schemas cover walking, mining, crafting, waiting for crafting,
placement, transfers, inventory waits, research selection, machine recipe
selection, rotation, and tick waits. The mod applies default values and checks
all actual gameplay conditions. Unknown fields, invalid bounds, nonfinite
numbers, invalid action types, and oversized batches are rejected before RCON.
Optional fields should be omitted rather than set to `null`.

## Recovery and limits

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
  global `sequence`. The controller retains only 2,048 events and 256 jobs;
  clients must record evidence privately and account for missing old events.
- A successful `save` call acknowledges a request. Verify the checkpoint file
  and its hash separately. It does not prove a milestone or fresh-map provenance.

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
