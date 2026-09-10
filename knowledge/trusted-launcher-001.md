# Trusted-launcher review unit

This is a separate draft library, independent of the offline material-flow PR.
It is not installed into the gameplay startup path and no Factorio process was
started to test it. Gameplay stays stopped. The earlier leftover server was
checkpointed, its ZIP and hash verified, then stopped gracefully.

## Lifecycle

`TrustedLaunch.prepare` requires explicit save/controller hashes, controller/base
versions, actor unit, surface and player. It creates a new private launch-attempt
directory under ignored runtime storage, refusing overwrite. It copies the actual
save, controller and base/core data into private inputs, verifies source and copy
hashes, checks ZIP integrity, and rejects symlinks or special files in input trees.
The selected executable is hashed in place rather than moved out of its platform
installation. Source changes cannot alter copied inputs.

The prepared record binds hashes of the save, complete mod/data trees, mod list,
configuration, settings, executable and fresh RCON credential. Command arguments
and the deliberately minimal child environment also have bound digests. This
record is a launch attempt; it has no episode identity.

`start` rechecks those artifacts, refuses occupied endpoints, and starts one child
directly with an argument list. It binds the prepared hashes to that child's PID,
creation timestamp, executable and command line. It never adopts a PID from disk
or attaches to an existing server. `attach` explicitly refuses. Failed checks
preserve a private failure record and request graceful shutdown of only the child
created by the attempt.

After the server is ready and the expected player has joined, `mint_episode`
requires both loopback listeners to belong to that child. A connection using its
fresh private credential calls only the fixed `hello`, `bind` and `observe`
operations. It validates the controller contract/version, exact active mod set,
expected actor and surface, speed, policy, pause-field type, advancing observation
ticks and absence of unreconciled running work. Process/configuration/input hashes
are checked again after the handshake. Only then is an episode UUID created and
written with the validated identity and launch evidence.

An episode record describes a validated historical launch; reading it later is
not permission to attach to a running server. No arbitrary Lua, item/research
grant, game-speed change or gameplay pause/resume operation is added.

## Evidence and limits

Fourteen tests cover copied input bytes, reviewed hash mismatches, modified saves,
mods, configuration, engine and added unlisted mod files; foreign listeners;
process identity changes; stale/unreconciled work; controller/actor/surface drift;
post-bind mutation; late UUID creation and refusal to attach or reuse a launch.
Failure fixtures confirm that only the owned child receives a stop signal.

The OS-adapter smoke test starts a short-lived Python socket fixture, verifies its
PID, executable, command and TCP/UDP listeners, then stops it. This is not a
Factorio launch, mod-installation test, load-time measurement or trusted gameplay
baseline. The test is optional where listener inspection is unavailable; the
launcher itself fails closed if that inspection cannot be performed.

The platform boundary is a trusted local OS and owner. These hashes bind bytes;
they are not publisher-signature attestation or protection against an adversarial
machine owner. The executable's dynamic libraries and OS are outside this unit's
hash set. Copying and hashing base/core data may be expensive; that startup cost
has not been measured on a real game installation.

The caller must already know the expected actor and surface from reviewed private
checkpoint evidence. Fresh-map actor discovery, graphical-client coordination,
readiness waiting and automatic continuation are deliberately outside this unit.
Readiness or identity failure produces no episode; there is no retry that adopts
an unknown server. Graceful shutdown can remain pending and is recorded rather
than silently escalating to a forced kill.

## Hard gates before live use

Review this unit and the richer observation contract before integrating it into
`client.server`, the mirror observer or the executor. Those existing entry points
are unchanged and do not automatically gain trusted provenance from this draft.
Recheck process/controller/actor identity throughout an eventual episode rather
than trusting a cached launch record forever.

A separate reviewed measurement harness must record engine/RCON observation cost
and event-to-action latency, interruptions and startup time. It must distinguish
those costs from storage compression and replay CPU. The disclosed 88.83 percent
strict compression result remains unchanged. No layout compiler is included.
