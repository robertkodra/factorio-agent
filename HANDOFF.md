# Setup and continuation

Clone the public repository into a new directory. Its history is independent of the private experiments; do not merge or push those old branches here.

```sh
gh repo clone robertkodra/factorio-agent
cd factorio-agent
git switch -c codex/next-milestone
```

Read [POLICY.md](POLICY.md), [ROADMAP.md](ROADMAP.md), and [knowledge/README.md](knowledge/README.md). Set Git to your own GitHub-provided no-reply identity before committing. Never copy another machine's credentials or local configuration.

## Current development — controller 0.7.0

Read [the remote factory-attack failure and response](knowledge/factory-defense-001.md)
first. The coal conveyor was attacked while attention was on construction. Its
lost tiles were replaced and the loaded turret relocated. Two additional turrets
now receive ammunition from that center turret through powered long-handed
inserters. Live inventories showed ten magazines in each outer turret and twenty
in the center. This verifies distribution, not performance under fire. A persistent
factory defense watch now owns the executor; inspect its live handle/journal before any
new gameplay. The game remains unpaused. Preserve the failed response and damage
records. New polling/dispatch code passes unit tests but has not faced another
measured real attack. Native factory events and grenade use remain unimplemented.

Advanced material processing and Fast inserter completed through labs. The mall
now has iron/gear/circuit/cable transport, but copper input still needs carrying.
The additional boiler/engines now operate after normally rebuilding the coal
approach to feed the underground entrance inline. Coal in the boiler and steam
in both added working engines were observed; sustained full-load capacity still
needs measurement. Engine research has started; later oil/science and the rocket remain.

Read [belt-fed production development](knowledge/belt-production-001.md) and the
updated [strategy](knowledge/strategy.md). Controller 0.7.0 is installed and its
underground crossing and continuous iron return were verified live. The 0.6.0
ledger closed with its failures preserved; a new checkpoint continuation is
open. Check live server identity and active journals before continuing. The single
scheduler currently watches defense and replenishes ammunition after completing
the coal-feed correction; science supply needs resuming in its next production plan.
Next are connected copper/construction supplies and fewer ingredient trips.
Do not assume the older stopped states below still apply.

## Latest state — controller 0.6.0

Read [buffered production and fluid observations](knowledge/production-oil-001.md)
and [the private plan format](plans/AUTOPILOT.md) before the older history below.
The latest checkpoint practice completed Electric mining drill and Automation 2
through labs. Two electric smelting cells, five buffered intermediate cells,
three green assemblers, four labs and two steam engines were live-verified.
The corrected final controller phase completed 41 jobs without execution failure;
earlier failures and normal movement recoveries remain recorded.

The checkpoint and its hash are verified; server and viewer are stopped, and
the private ledger is closed. Start a new ledger for continuation. The source
checkpoint was preserved. Do not use a gameplay pause to initialize this user's
next run; record startup waits and any development restarts separately.

Next work is a real oil survey and connected oil/blue-science production, plus
stronger transport and navigation. Neutral wrecks must be included in local
collision observations; reaching a factory-only stance is not proof of a clear
route. Keep Qwen in shadow until separately validated. A rocket, later science
and competitive performance remain unproven. Older notes below retain their
historical stopping points and are superseded by this section.

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
5. Check the installed controller version against the reviewed source, then bind and inspect:

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

The subsequent [preparation rehearsal](knowledge/speedrun-preparation.md)
continued that checkpoint in a separate ledger, with controller 0.3.2 unchanged.
Two red assemblers now deliver automatically to the labs, Electric mining drill
is completed, and an exhausted iron drill/furnace pair was normally relocated
and observed producing again. The final checkpoint is saved and paused; the
rehearsal ledger is closed. Use a new ledger for further play, preserving the
checkpoint identity and earlier failure records. Science ingredients need
replenishment, and green science, Military 2 and live defense remain pending.

Use `python3 -m client.capacity` to check the proposed science load and fuel
reserves. Its supply inputs are assumptions unless measured; placed machines do
not prove active capacity. The next scored test should follow the declared
protocol in the preparation report after the complete segment passes practice.

## Historical failed attempt

The user requested a fresh rocket attempt and then imposed no cheating and no
pausing. After two deaths, the user explicitly stopped the game and requested
relearning; they observed several biters attacking. The server is shut down and
the failed checkpoint is preserved. Later practice used a separately authorized
copy rather than replacing this failure record. Read the
[failure review](knowledge/rocket-attempt-001-review.md).

Source 0.3.3 adds read-only damage/death evidence in `status`. It is unit-tested
but has not been installed or live-tested. The stopped attempt ran 0.3.2. This
diagnostic addition does not provide combat, automatic retreat or safer paths.

## Local Qwen and reflex implementation

Source 0.4.0 supersedes the uninstalled 0.3.3 diagnostic draft. Read
[local-controller-001](knowledge/local-controller-001.md) for the durable Ollama
configuration, measured 50-case results, shadow-supervisor command and remaining
live checks. The local model is set up and inference tested. A later authorized
[live practice](knowledge/live-defense-001.md) installed 0.4.0 and survived one
fourteen-biter encounter. Military, Gun turret and Automation completed, and the
final checkpoint has a loaded turret and full-health engineer. The practice is
closed and the server/client stopped. Source 0.4.1 is now installed; its new
partial-ammunition transfer rejection is unit-tested but not live-tested. Use
native inventory controls for partial magazines. Start a new ledger when
continuing. Shadow advice remains disconnected from production actions.


## Current production-controller development

Controller 0.5.1 supersedes the older setup notes above. Read the
[factory-controller report](knowledge/rocket-controller-001.md) and
[private plan format](plans/AUTOPILOT.md). It replaces the partial-magazine
rejection with native stack transfers and retains compact receipts beyond the
old 256-job ceiling. The scheduler and rocket material/capacity planner are
implemented; later science, fluid layout and an actual launch remain unverified.

The current user requires no cheating and no gameplay pauses. Do not use the
historical paused initialization recipe above for this user's new attempts.
Create a private manifest from the actual unpaused starting observation; record
startup waits and any development restarts separately. Keep one production
executor, retain every prior journal, and reconcile pending IDs before resuming.
A Python deadline leaves the game running. End a practice session by saving and
gracefully stopping its server, preserving the checkpoint identity and failures.


The latest practice completed Military 2 through the labs with full final health
and no new deaths or gameplay pause transitions. It includes development
restarts and corrected private layouts, so it is not a fresh timed baseline.
The checkpoint is verified and both server and viewer are stopped. The closed
private run retains all four scheduler journals and the final validation record.
Continue in a new ledger from that checkpoint, or create a fresh map for a scored
baseline. Next implementation priorities are automatic intermediate production,
shorter material routes and the connected oil/blue-science chain.
