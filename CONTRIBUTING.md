# Contributing

This public project's original code and documentation use the [MIT License](LICENSE).
Contributions must be compatible with that license. Follow [AGENTS.md](AGENTS.md),
the [gameplay policy](POLICY.md) and the [publication boundary](PUBLICATION.md).

## Protected branches

The active GitHub ruleset protects the repository's default branch, `main`,
`master` and `release/**`. Using the default-branch selector keeps protection in
place if the default branch is renamed. Feature branches remain available for
ordinary development and pull requests.

For users without bypass permission:

- Changes require a pull request and one approving review.
- New commits dismiss stale approvals; the latest push requires approval from
  someone other than its pusher.
- Review conversations must be resolved.
- The `checks` job from GitHub Actions must pass, with the branch up to date.
  This includes unit tests, publication/history checks and the secret scanner.
- Force-pushes and branch deletion are blocked on protected branches.

The owner account, **@robertkodra** (GitHub user ID `36516516`), has an explicit
`always` bypass. It can bypass both pull-request and push rules; bypass use remains
auditable. No blanket admin-role, application or team bypass is configured.
Normal contributions should still use passing CI and reviewed pull requests.

The reviewed settings payload is [protected-branches.json](.github/rulesets/protected-branches.json).
The live GitHub ruleset is authoritative; editing this file alone does not change
GitHub settings. Keep the payload and live settings synchronized when changing
protection. Ruleset semantics are documented in the
[GitHub rules API](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset).

## Validation and privacy

Run both Python suites when the optional MCP environment is available, followed
by the publication and secret scans described in [PUBLICATION.md](PUBLICATION.md).
Keep saves, raw observations, replay reports and runtime configuration under
ignored `runtime/`. Include aggregate evidence and limitations in a pull request;
do not publish private archives or personal machine paths.
