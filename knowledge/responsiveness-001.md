# Live responsiveness test — 2026-09-09

The MCP connection is fast enough to submit work without adding per-action
delays to this early-game sequence. A fresh 29-action opening completed, all
12 belts were placed on consecutive ticks, and cancellation and reconnection
worked. This test also found and reduced avoidable large-batch validation cost.

The Steam graphical client was connected throughout. Factorio 2.0.77 ran at
normal speed with base and controller 0.2.0 only. The fresh save used seed
20260906 and the game's default map settings. The observed baseline was tick 1,
with the default starting inventory. Initial save and source hashes, full calls,
results, pauses, and checkpoint evidence are retained privately under runtime.

## Tool response times

Times begin immediately before the SDK/transport request and end when its reply
is available. They include the local game server's scheduling. They exclude
model reasoning, tool orchestration outside the benchmark process, and display
presentation latency. Percentiles use the empirical nearest-rank method.

The first comparison used persistent MCP and direct RCON connections, five
warmups per tool/transport, and 100 measured calls per tool/transport. Pair order
alternated. These are measurements in a small fresh world, not a large factory.

| Observation | MCP median | MCP p95 | Direct RCON median |
|---|---:|---:|---:|
| Job status | 17.02 ms | 19.93 ms | 15.55 ms |
| Engineer state | 17.22 ms | 19.91 ms | 15.70 ms |
| Nearby scan, radius 64, limit 20 | 16.76 ms | 20.22 ms | 16.13 ms |
| Factory state | 17.02 ms | 20.75 ms | 15.89 ms |

During the opening, another 940 status and 940 engineer observations completed:
status median/p95 were 15.47/18.44 ms; engineer observation median/p95 were
16.47/19.87 ms. No transport or controller error occurred in the 3,135 recorded
controller calls across the test phases and final checkpoint. SDK initialization
and desktop menu actions are outside that call count.

## Actual gameplay

The supplied first-belts plan executed ordinary walking, resource mining,
item-funded construction, fuel/input transfers, smelting, hand crafting, and
placement. It did not require an intervention or recovery.

| Check | Result |
|---|---|
| Plan | 29 actions completed |
| Elapsed game time | 7,504 ticks / 125.07 seconds from acceptance to completion |
| Observed wall duration | 125.22 seconds from submission call to final observation |
| Submission call | 84.45 ms, one sample before validation optimization |
| First action start | Same game tick as the submitted event |
| Belts | 12 placements on consecutive ticks, one per tick |
| Crafting while walking | 30 overlapping ticks |
| Maximum authoritative displacement | 0.149155 tiles per tick |
| Client display | 60 FPS / 60 UPS during sampled walking/production views; 59.9–60.0 in final inspection |

The route was pre-authored. Its duration includes normal mining/crafting/
smelting and a final 12-second belt-flow wait, but excludes route preparation
and model reasoning. This is a responsiveness test, not a measured autonomous
speedrun. Debug FPS/UPS observations are not a frame-time capture; they cannot
establish the absence of occasional display stutter or measure input-to-pixel
latency. The test path did not reproduce the known obstacle-oscillation issue.

## Cancellation and reconnection

Twenty moving-engineer cancellation trials passed, ten before and ten after
the optimization. In the optimized trials, walking submissions had median/p95
33.65/36.94 ms; cancellation replies had median/p95 16.41/17.04 ms. The engineer
was verified moving before cancellation, and successive observations afterward
showed walking disabled and an unchanged position.

Closing the action client's MCP process did not abandon or duplicate its game
job. While disconnected and reconnecting, the simulation advanced 45 ticks and
the engineer moved 6.68 tiles. A new MCP process initialized in 331.78 ms,
retrieved the original job with its unchanged start tick, found exactly one
submission event, and cancelled it. The socket fault tests separately cover a
submission whose response is lost after acceptance.

## Large-batch validation improvement

The original validator checked every alternative in the action `oneOf` schema.
Each alternative already has a distinct, required `type` constant. The optimized
validator selects that type's complete schema and retains all its field, type,
bound, and extra-field checks. Unknown types fail. Other unions use standard
validation. The advertised MCP schemas are unchanged.

A regression test compares acceptance with the advertised JSON Schema across
every action type and field, missing keys, wrong values, bounds, and extra
fields. The complete 25-test suite passes.

The final comparison kept both old and optimized MCP processes connected to the
same live world, alternated pair order, and measured ten submissions per version
and batch size. All batches contained normal long waits and were cancelled;
these measurements do not include actual construction execution time.

| Actions per batch | Previous median | Optimized median | Previous maximum | Optimized maximum |
|---|---:|---:|---:|---:|
| 32 | 33.07 ms | 34.16 ms | 34.53 ms | 37.02 ms |
| 128 | 51.37 ms | 34.52 ms | 54.37 ms | 37.78 ms |
| 512 | 88.72 ms | 38.67 ms | 105.44 ms | 41.62 ms |

The 512-action median fell by 56%. Small-batch timing is largely unchanged;
differences of a few milliseconds vary with tick scheduling. Ten trials per
cell support this local comparison, not a long-term tail-latency guarantee.

## Repeat and continue

After initializing an explicit fresh run as described in the handoff, these
commands use the optional MCP environment. Keep the graphical client connected
and bind its engineer first. The plan assumes the specified seed, fresh inventory,
and original layout; never use it on an unrelated factory.

```sh
.venv/bin/python -m tests.benchmark_live --run-id YOUR_RUN_ID --phase reads --samples 100
.venv/bin/python -m tests.benchmark_live --run-id YOUR_RUN_ID --phase plan --plan plans/first-belts.json --deadline 240
.venv/bin/python -m tests.benchmark_live --run-id YOUR_RUN_ID --phase control --samples 10
```

Each phase creates a separate private attempt directory, resumes the simulation,
and pauses it on normal completion. Control trials walk nearby, cancel, and
submit/cancel additional wait batches; they consume job-history slots. If a phase
raises an exception, its trace retains the failure; inspect status and explicitly
cancel/pause before proceeding. No failed attempt should be overwritten.

The final factory was checked for 12 belts and saved to a new checkpoint. ZIP
integrity and its SHA-256 were verified; the original fresh save hash was unchanged.
The local test server and viewer were left paused for inspection.

Next performance work should exercise longer obstacle routes and sustained
production under growing factory load. Observation payload growth, planner
decision time, fuel scheduling, and bounded job/event history matter more now
than reducing the roughly one-tick cost of ordinary observation calls.
