# Controller 0.8 integration review

The integration review preserves the linear ancestry of draft PRs 1 through 4.
Their branch heads and discussion remain intact. A cumulative baseline PR targets
`codex/public-release` from `codex/reactive-execution`; no rebase, force push or
merge is needed. The state-mirror PR will target that baseline on a separate
branch. This makes the new work independently reviewable while keeping the
earlier executor history available for focused inspection.

The previously staged eleven-file change was committed intact before additional
review fixes. It includes opt-in checkpoint recovery heuristics and private
cadence analysis; those are preserved experiments, not proof of general planning.
The runtime journals, initial staged patch and checkpoint evidence remain ignored.

Review of the immediate health poll confirms a fresh runner now samples before
using the half-second throttle, including monotonic clocks beginning at zero.
The paginated damage regression confirms the latest-damage summary cannot skip
events in subsequent pages. Baseline review additionally found that health polling
could replace a pending destruction alarm when another entity lost health. The
fallback now merges bounded damage records, with a regression for that case.

The native transfer boolean is documented in the pinned 2.0.77 runtime catalog as
success for the full stack or requested amount. The quantity-limited transfer
logic and metadata mocks are consistent with that contract; live used-science
durability reconciliation remains unproved. Emergency preemption is unit tested;
there is no new natural-attack validation. No gameplay was resumed for this review.

## Architectural objections governing the next PR

- A lossless snapshot codec alone does not reduce RCON work. Keep storage,
  observation cost and reaction timing as separate measurements. Native events
  do not cover every fuel, inventory, energy or production change.
- The current fixed `inspect` requires reach and omits identity, health and power
  fields needed for a remote smelting block. A narrow, bounded owned-entity read
  is needed; adding a general world subscription framework is unnecessary.
- Actor ID, version and monotonic tick cannot distinguish every same-save reload
  or branch. Require explicit private save/episode provenance, detect observable
  identity changes and tick regressions, and document the remaining trust boundary.
- Discovery, input accounting and stale-state rejection belong in the first
  mirror slice. Production-flow diagnosis and layout generation remain later
  work; they must not be smuggled into this PR's acceptance criteria.
- The later throughput gate needs an independently calculated upper bound and
  material accounting. Otherwise a low promised rate or draining a prefilled
  buffer can satisfy 95 percent delivery without proving useful production.
  Preserve the proposed two-location, 36,000-tick, enemy-enabled contract, but
  separately count initial work in progress, external deliveries and sink output.
