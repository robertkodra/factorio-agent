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
python3 scripts/privacy_gate.py ci
```

The publication guard checks staged content and all reachable history, including removed files, filenames, ref names, commit messages and annotated tags. It rejects known private artifact types, personal home/temp paths (including common URL/JSON escapes and Windows forms), private-key headers, common token formats, embedded URL credentials, and non-no-reply email addresses. The gate also applies Gitleaks default rules to the exact staged snapshot, history and commit/tag metadata. Repository ignore lists and inline scanner suppression comments do not exempt findings. Scanner failures block publication.

CI uses a pinned Gitleaks release whose archive checksum is verified before execution. Privacy scans run before dependencies and unit tests. Detailed findings, including sensitive filenames and scanner diagnostics, stay in ignored `runtime/` with restrictive local permissions; public output gives categories and counts only. Never upload these reports as CI artifacts. Tests or commands can still print private data, so do not supply private runtime values to public CI jobs.

## Local prevention

CI runs after a push, so it cannot prevent the initial disclosure. Install Gitleaks from its official release, verify the archive checksum, and make the executable available as `.tools/gitleaks` or on `PATH`. Then install the reviewed hooks:

```sh
python3 scripts/install_privacy_hooks.py
```

The installer uses Git-local storage and configuration. Copies of the reviewed gate survive branch switches and scan before commits and pushes. It refuses to replace existing custom hooks. Reinstall after reviewed gate updates, and install separately in every clone. A missing scanner, malformed configuration, unsafe report directory or scan error blocks the operation. A pre-push scan includes outgoing object IDs even if they are not reachable through a named local branch.

For private values that generic patterns cannot recognize, keep a JSON list of local identifiers and credential values in ignored `runtime/privacy-private-markers.json`, restrict access to the file, and bind it during installation:

```sh
python3 scripts/install_privacy_hooks.py --private-markers runtime/privacy-private-markers.json
```

No actual values belong in this document. A configured marker file must remain available; a missing or malformed file blocks the scan. The file is local and is never sent to GitHub. Portable environment variable names and repository-relative path examples are allowed; actual environment values, machine paths and private player identifiers stay in private chat or local ignored storage.

## Public text and other surfaces

PR descriptions, issue comments, release notes, screenshots and pasted command output can disclose information even when Git is clean. Prepare text in ignored local storage and scan it before posting:

```sh
python3 scripts/privacy_gate.py text --text-file runtime/draft.md
```

Review images separately before publication; the source guard rejects unreviewed binary files. Do not paste environment dumps or detailed audit output into public threads. Use only aggregate audit results. The initial expanded audit is recorded in [privacy-audit-001.md](knowledge/privacy-audit-001.md).

GitHub secret scanning and push protection are enabled. They cover supported patterns, not arbitrary personal paths or every private identifier. GitHub's non-provider-pattern setting remained disabled on API readback, so it is not counted as an active control; local and CI Gitleaks checks supply generic credential detection. The owner's explicit branch-ruleset bypass remains enabled as requested. Local hooks and platform checks are bypassable, and pattern checks cannot prove the absence of every possible secret or personal detail. Review remains required.

In addition to GitHub user no-reply addresses, the exact public service address
`noreply@github.com` is permitted for GitHub-generated merge commits. Other
addresses at that domain remain rejected. This exception preserves normal merge
history without misclassifying the service committer as a personal address.

For the initial release, Gitleaks 8.30.1 was obtained from the official release with its archive SHA-256 verified. A separate local audit checks the known credentials and private identifiers without embedding their values here. Publication verification results are recorded in `publication-checks.json`.

If something sensitive is accidentally published, revoke or rotate live credentials first, preserve an appropriate private incident record, and follow GitHub's removal process. Simply deleting the visible file is insufficient.
