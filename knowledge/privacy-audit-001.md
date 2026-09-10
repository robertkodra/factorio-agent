# Public repository privacy audit

Audit date: 2026-09-10. This is a point-in-time review of the public repository;
private raw evidence and the local identifier list are deliberately excluded.

## Inspected scope

- Fresh mirror of every advertised public ref: 9 branch heads, 12 pull-request
  refs, no tags; 314 unique file blobs and 40 commits including merge commits.
- Source, removed files, filenames, commit metadata and ref names checked with
  the publication guard and a separate private-value list.
- Gitleaks 8.30.1 history scan: 32 non-merge commits scanned, zero findings.
- Eight issue/PR records, two issue comments, and workflow metadata inspected.
  No review comments, commit comments, releases or uploaded Actions artifacts
  were returned by the corresponding APIs.
- All 46 completed Actions runs available at the inventory time had downloadable
  logs. Their extracted text was checked for private values and credential
  patterns, including a dedicated Gitleaks scan.
- GitHub secret-scanning alert inventory returned zero alerts.

## Findings

No confirmed credential, private local identifier, personal machine path or
environment value was found in this inspected scope. Path-pattern matches in
metadata were public GitHub account API URLs; log path matches were GitHub-hosted
runner workspace paths. Neither contained a private machine path. One generic
secret-pattern match in a PR description was reviewed as ordinary prose about
event consumption. No blanket scanner exception was added for it.

The audit covers advertised Git objects and API-accessible records at the time
of collection. It cannot prove that no sensitive data was ever exposed through
deleted/unadvertised objects, caches, forks, edited comment versions or other
external copies. No history was rewritten and no run evidence was deleted.

## Prevention added

The publication guard now checks encoded paths, more private artifact types,
optional local identifiers and outgoing objects, while withholding finding
locations from public output. Git-local pre-commit and pre-push hooks scan exact
staged content and full/outgoing history, fail closed, and survive branch changes.
A text-draft command supports privacy review before posting public descriptions
or comments. CI scans before running tests and keeps detailed diagnostics out of
public output and uploaded artifacts.

GitHub secret scanning and push protection are enabled. The non-provider-pattern
setting remains disabled on readback and is not claimed as protection. Generic
credential checks run locally and in CI through Gitleaks. The owner's explicitly
authorized ruleset bypass is preserved. See [PUBLICATION.md](../PUBLICATION.md)
for setup, limitations and the continuing review requirement.
