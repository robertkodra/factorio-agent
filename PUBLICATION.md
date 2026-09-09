# Public repository boundary

The public repository starts from a reviewed source snapshot with new Git history. The original experiment repository remains private. No original objects, branches, bundles, save files, or raw traces are imported into this repository.

Rewriting existing history alone can leave sensitive content accessible through cached commit references. Independent publication avoids exposing the private repository's historical objects. See [GitHub's sensitive-data removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository).

## Included

- Original Python clients, control-mod source, plans, and local tests.
- Static Factorio 2.0.77 recipe/technology facts with observed run state removed.
- Reviewed setup instructions, policy, progression roadmap, and aggregate experimental results, including failures and unfinished work.
- Public GitHub account attribution via a no-reply commit identity.

## Kept private

- Credentials, tokens, environment/configuration files, personal filesystem paths, and machine/player identifiers.
- Factorio saves and other binary archives, raw server logs, action/event traces, local backups, private handoff bundles, and original commit metadata.
- Runtime installations and proprietary game binaries/assets.

Code uses repository-relative paths and resolves the current home directory for the standard macOS Steam layout at runtime. Loopback addresses and a generic `FACTORIO_RUN_ID` option are public interface documentation; no local environment files or secret values are supplied. Named runs and live-test reports are written into ignored `runtime/`.

## Before contributing

Use a new branch and review the staged diff and filenames. Keep private artifacts outside Git and use a GitHub no-reply commit email. Do not merge old private history into the public repository. If you need a historical checkpoint, obtain it privately and keep it under runtime.

```sh
git diff --cached --stat
python3 -m unittest discover -s tests -v
python3 scripts/check_publication.py --history
gitleaks git --redact --log-opts=--all .
```

The publication guard checks staged content and all reachable history, including removed files and commit messages. It rejects known private artifact types, personal home/temp paths, private-key headers, common token formats, embedded URL credentials, and non-no-reply email addresses. CI runs the guard, unit tests, and a pinned Gitleaks release whose archive checksum is verified before execution. Pattern checks cannot prove the absence of every possible secret or personal detail.

For the initial release, Gitleaks 8.30.1 was obtained from the official release with its archive SHA-256 verified. A separate local audit checks the known credentials and private identifiers without embedding their values here. Publication verification results are recorded in `publication-checks.json`.

If something sensitive is accidentally published, revoke or rotate live credentials first, preserve an appropriate private incident record, and follow GitHub's removal process. Simply deleting the visible file is insufficient.
