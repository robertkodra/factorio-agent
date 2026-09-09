# Setup and continuation

Clone the public repository into a new directory. Its history is independent of the private experiments; do not merge or push those old branches here.

```sh
gh repo clone robertkodra/factorio-agent
cd factorio-agent
git switch -c codex/next-milestone
```

Read [POLICY.md](POLICY.md), [ROADMAP.md](ROADMAP.md), and [knowledge/README.md](knowledge/README.md). Set Git to your own GitHub-provided no-reply identity before committing. Never copy another machine's credentials or local configuration.

## macOS with Steam

The launcher currently supports the macOS Steam installation layout and resolves the current home directory automatically. Other operating systems and other Factorio versions require compatibility work. Factorio itself and its assets are not included.

1. Install Python 3 and Factorio through Steam. The tested game version is **2.0.77**.
2. Close the graphical client while installing/updating the mod.
3. Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 client/server.py setup
python3 client/server.py create --save clean-001
python3 client/server.py start --save clean-001
```

Setup enables only base plus `codex-controller`, backs up the previous client mod list, and generates a new RCON credential in ignored `runtime/`. The runtime directory is private; server logs contain launch arguments and must not be published. Creating a map refuses to overwrite an existing save. Stop an existing server before starting another on these ports.

4. Start the graphical client and connect via Multiplayer → Connect to address → `127.0.0.1:34198`. RCON binds to `127.0.0.1:27016`. Dismiss the introduction with Tab and keep the viewing client connected for normal hand crafting.
5. Check controller version `0.3.2`, then bind and inspect:

```sh
python3 client/agent.py '{"op":"hello"}'
python3 client/agent.py '{"op":"bind"}'
python3 client/agent.py '{"op":"observe"}'
python3 client/agent.py '{"op":"research_state"}'
```

The server automatically pauses without the viewing client. Check explicit pause state after loading. GUI permissions requiring user interaction must be granted on that machine.

## Record a fresh run

The optional `FACTORIO_RUN_ID` variable is a non-secret run label. All notebook output, including named runs, goes under ignored `runtime/`; environment files and values are not distributed with the project.

```sh
export FACTORIO_RUN_ID=clean-001
python3 client/agent.py '{"op":"pause","value":true}'
python3 -m client.play --init
python3 client/agent.py '{"op":"pause","value":false}'
```

Set the same label in each recording process. Without it, output goes to `runtime/notebook`. Initialization refuses to overwrite a baseline and requires a paused game with no running job. A `stop-monitor` marker closes a run to further notebook actions. Record the fresh save name, map settings, version, and mod hashes alongside observations; an observed baseline alone does not prove fresh-map provenance.

Work through G0/G1, then Military 2 as the first green-consuming research target after its prerequisites. The historical green-pack production does not satisfy that milestone. The [MCP facade](MCP.md) is implemented and tested; robust navigation, the milestone evaluator, and later science stages remain pending.

## Local live checks

Normal unit tests use local socket fixtures and do not need a game. These additional commands do:

- `python3 -m tests.live_checks` changes a **completed first-belts test world**, expecting its original furnace location. Use an expendable test world, never an unrelated factory. Its report goes to ignored runtime storage.
- `python3 -m tests.handoff_live --save runtime/checkpoints/dry-run-001-green-science.zip` starts its own isolated server and verifies fixed observations against the **specific historical green-science fixture**. Obtain that fixture privately if authorized; it is not shipped publicly. The test checks the historical counts, is not suitable for any arbitrary save, and shuts down its own process. Its copied save, credential, and report stay under runtime.

Neither optional test was replayed during the initial publication. The subsequent MCP change re-ran the historical reload test with `--mcp`, also checking submission, status, and cancellation on its disposable copy. Use the MCP environment's Python for that option. Results and limits are summarized in [CHANGELOG.md](CHANGELOG.md).

Stop the configured local server with `python3 client/server.py stop` and wait for it to exit before starting a different save. The stop command requests graceful shutdown; it does not wait for completion.

## Current learning checkpoint

The [learning report](knowledge/learning-001.md) records a fresh development
attempt through powered labs, Automation and Gun turret, with one loaded turret.
The private run is closed and its final checkpoint was verified and left paused.
Continue in a new ledger, recording whether it is a checkpoint continuation or
an independent fresh attempt. Exact files, layout and source/checkpoint hashes
remain in the local runtime run directory.

Use controller 0.3.2 from the beginning for the next fresh attempt. If a reload
reports `no_bound_character`, connect the viewer and bind the existing engineer,
then compare position, inventory, ammunition and health to the saved state. Do
not replay failed batches: a placed turret or queued craft may already exist.
Prioritize supplied automatic science and ammunition reserves; Military 2 and a
real defensive encounter remain unverified.
