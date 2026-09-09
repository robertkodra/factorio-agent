# Speedrun references and experiments

Reviewed **2026-09-09** from the user-supplied
[Factorio leaderboard](https://www.speedrun.com/factorio). Our target remains
base 2.0.77 with enemies, normal mechanics and the fixed controller. References
teach decisions and execution techniques; a ranked human run is not evidence
that our agent can reproduce it.

## Pick a comparable reference

The site separates Any%, Default Settings, multiplayer, Space Age and major game
versions. Its unfiltered landing page currently opens on Any% 1.x.x. Explicitly
select the category and version before interpreting a time.

| Reference | Verified on this review | Use and remaining study |
|---|---|---|
| [Zaspar, Default Settings 1:59:01](https://www.speedrun.com/factorio/runs/yvk04e8m) | Listed first in Default Settings 2.x.x, played on **2.0.77**; video and a Drive ZIP link supplied | Closest version/settings reference. Video page and limited opening samples inspected; full route, defensive encounters and replay still need analysis. |
| [JeHor, Any% 1:42:41](https://www.speedrun.com/factorio/runs/y8ovjjwm) | Listed first in Any% 2.x.x, played on 2.0.28; explicitly links a save with replay | Study production order and material scheduling later; settings and exact-version differences need checking. Video/replay not reviewed. |
| [Phredward's Default Settings guide, AntiElitz design](https://www.speedrun.com/factorio/guides/li2kd) | Public slide text read, including opening, adaptation, defense and common mistakes | Useful reasoning for enemy-enabled play. Historical recipe lists, quantities, mirroring restrictions and research order require fresh 2.0.77 validation. |
| [OverCraft's Phoenix guide](https://www.speedrun.com/factorio/guides/cl454) | Guide description read; PDF not reviewed | The author emphasizes reducing travel, dividing construction into phases, and limiting production to the goal's demand. Historical route, not a current record claim. |

Rankings are a dated snapshot. Refresh individual run pages before quoting a
current record. Exact run dates were not resolved from relative website labels.

## Timing and map rules change the comparison

The category rules were read directly from the site's public API:
[Default Settings](https://www.speedrun.com/api/v1/categories/7dg85xp2) and
[Any%](https://www.speedrun.com/api/v1/categories/ndxjper2).

| Category | Map | Timer starts | Timer stops |
|---|---|---|---|
| Default Settings | Default preset, random map | Pressing the random-seed button | First victory-screen frame |
| Any% | Chosen seed and map-generator settings permitted | First map frame | First victory-screen frame |

Both use real time, a single player and a rocket-launch goal. Both disallow
imported blueprints while allowing blueprints made during the run. Category
rules also inherit game-wide rules. This review is not a complete eligibility
audit, and our controller-assisted practice is not a leaderboard submission.

Our previous fixed-seed, paused learning attempt is a **practice baseline**.
Its elapsed game time excludes planning pauses and cannot be compared to these
real-time results. Retain wall time, setup/seed selection, pauses, reloads,
failures and unfinished attempts. Never change map settings to make an existing
run appear comparable.

## Lessons from the default-settings guide

The [slide text](https://docs.google.com/presentation/d/1etZgz5d2yIiFXLEXcKAeLRrEmdxyWHn2_8mrzQwgCLI/htmlpresent)
supports the following principles:

- Adapt orientation and servicing routes to the actual resource/water layout
  (slides 2–4).
- Defense, reserve materials and noticing stalled builds are recurring work
  (slides 3 and 6).
- Supply coal to smelting and power as part of expansion (slide 14).
- Research timing depends on production readiness: the guide even delays a
  later phase until its iron outpost and lab modules are ready (slide 5).

These are sourced strategies, not successful agent experiments. The guide
includes obsolete rocket-control-unit steps; its exact route is not a 2.0.77
shopping list. Its practice-map suggestions are not the category's submission
rules. No illustrated layout was copied or validated in this review.

## Limited video observations

In [Zaspar's video](https://www.youtube.com/watch?v=2PwyPjjoOJo), the frame at
3:00 shows rock gathering with a visible hand-crafting queue; at 12:24 a working
furnace/drill cluster and nearby assemblers are visible during inventory handling.
These isolated samples confirm visible activity, not a complete build order,
machine count or throughput. The full two-hour video was not watched.

Zaspar's pinned comment points to a [smelter placement demonstration](https://www.twitch.tv/videos/2156553379)
called BLIPI. That technique is a follow-up study candidate, not an implemented
controller optimization. The page also exposes Zaspar's
[TAS developer commentary](https://www.youtube.com/watch?v=tImNejO5g48), a relevant
future source for comparing scripted execution with adaptive planning. Its
content and compatibility have not yet been reviewed.

## Turn imitation into measurable experiments

The following are **our hypotheses**, informed by the references and the
[learning attempt](learning-001.md). None has yet demonstrated a speed gain.

| ID | Change one decision | Expected benefit | Measurements and reason to reject |
|---|---|---|---|
| S1 | Combine fuel delivery and plate collection into the next construction trip | Fewer repeated journeys | Walking ticks, stockouts and time to Military 2. Reject if a shorter route strands a machine without fuel or delays necessary defense. |
| S2 | Start each small mining/smelting/science block as soon as it can produce, before finishing the larger array | Earlier useful output while the engineer keeps building | Time to first useful output, cumulative plates/packs, rework and later supply gaps. Reject if temporary layout overhead exceeds the saved waiting. |
| S3 | Size fuel and ammo reserves for the planned time away, using measured consumption and a stated margin | Fewer emergency returns | Reserve remaining on return, damage, lost buildings and material cost. Enemy demand is uncertain; any unexplained safety loss invalidates a faster result. |
| S4 | Generate a short batch from a reusable layout and re-check state at construction milestones | Less model/tool overhead without a long unobserved commitment | Total wall time, game ticks, rejected actions and time to detect a fault. Reject if missing fuel, damage or blocked movement is detected too late. |
| S5 | Produce slow intermediates early, with an explicit maximum buffer | Remove later waits without starving construction | Idle crafting/lab time, unused stock at the target, time to Military 2. Reject if buffering delays expansion or consumes defense reserves. |

First establish a reproducible 0.3.2 baseline through supplied red/green science
and Military 2. Then compare a control and one variant from identical normal
checkpoints, with separate ledgers and alternating order. Track terminal state
as well as time: completed research, living engineer, intact production, fuel
and ammunition. Retain every failure and partial attempt.

Repeat promising changes on additional fresh default maps before calling them
general improvements. Route planning may use only charted knowledge acquired in
that attempt. Fixed-map practice can have an explicitly declared known layout;
do not carry that map knowledge into a purported random-map evaluation.

For each studied video segment, record the source timestamp, visible action,
inferred purpose, competing explanation and proposed test. Video timestamps are
not automatically the run timer. A screenshot of a factory establishes neither
its throughput nor the moment it first became operational.

Raw downloaded guide text and category JSON are stored privately under runtime.
Full replays, route timing extraction, later-game controls and a complete rocket
run remain future work.
