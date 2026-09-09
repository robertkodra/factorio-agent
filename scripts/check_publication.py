"""Check staged files and optional Git history without printing matched values."""
import argparse
import re
import subprocess
from pathlib import PurePosixPath


CONTENT_RULES = {
    'personal-path': re.compile(rb'(?:/(?:Users|home)/[^/\s\x00]+/|/(?:private/)?var/folders/|[A-Za-z]:[\\/]Users[\\/])'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'access-token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{25,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,})'),
    'credential-url': re.compile(rb'https?://[^\s/@:]+:[^\s/@]+@'),
}
EMAIL = re.compile(rb'[A-Za-z0-9_.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PRIVATE_DIRS = {'runtime', 'checkpoints', 'evidence', '.venv', '.tools', '__pycache__'}
PRIVATE_SUFFIXES = ('.zip', '.bundle', '.tar', '.gz', '.7z', '.log', '.jsonl', '.pem', '.key', '.p12', '.pfx', '.env', '.pyc')
TEXT_SUFFIXES = {'.py', '.lua', '.json', '.md', '.txt', '.yml', '.yaml', '.toml'}


def git(*args):
    return subprocess.check_output(['git', *args])


def content_issues(data):
    issues = {name for name, pattern in CONTENT_RULES.items() if pattern.search(data)}
    if any(match.group(1).lower() != b'users.noreply.github.com' for match in EMAIL.finditer(data)):
        issues.add('non-noreply-email')
    return issues


def file_issues(name, mode, data):
    path = PurePosixPath(name)
    issues = content_issues(name.encode())
    if (set(path.parts) & PRIVATE_DIRS or name.startswith('knowledge/runs/')
            or path.name.startswith(('.env', 'id_rsa', 'id_ed25519', 'rcon-password'))
            or path.name in {'server-settings.json', 'config.ini', '.DS_Store'}
            or name.lower().endswith(PRIVATE_SUFFIXES)):
        issues.add('private-artifact')
    if mode not in ('100644', '100755'):
        issues.add('non-regular-file')
    if path.suffix not in TEXT_SUFFIXES and name != '.gitignore':
        issues.add('unreviewed-file-type')
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        issues.add('binary-content')
    if b'\x00' in data or data.startswith((b'PK\x03\x04', b'\x1f\x8b')):
        issues.add('binary-content')
    return issues | content_issues(data)


def audit(history=False):
    findings = set()
    checked = set()
    blobs = {}

    def check_entry(name, mode, oid):
        key = (name, mode, oid)
        if key in checked:
            return
        checked.add(key)
        # Symlinks and submodules are rejected without following their targets.
        if mode == '160000':
            findings.add(('submodule', name))
            return
        if oid not in blobs:
            blobs[oid] = git('cat-file', 'blob', oid)
        for issue in file_issues(name, mode, blobs[oid]):
            findings.add((issue, name))

    for record in git('ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        metadata, name = record.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        if stage != '0':
            findings.add(('unmerged-index', name.decode()))
        check_entry(name.decode(), mode, oid)

    commits = git('rev-list', '--all').decode().splitlines() if history else []
    for commit in commits:
        for issue in content_issues(git('cat-file', 'commit', commit)):
            findings.add((issue, 'commit metadata ' + commit[:12]))
        for record in git('ls-tree', '-r', '-z', commit).split(b'\0'):
            if not record:
                continue
            metadata, name = record.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            check_entry(name.decode(), mode, oid)

    if history:
        for ref in git('for-each-ref', '--format=%(refname)', 'refs/tags').decode().splitlines():
            if git('cat-file', '-t', ref).strip() == b'tag':
                for issue in content_issues(git('cat-file', 'tag', ref)):
                    findings.add((issue, 'tag metadata'))
    return findings, len(blobs), len(commits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Also inspect every reachable commit and tag')
    args = parser.parse_args()
    findings, blobs, commits = audit(args.history)
    for category, name in sorted(findings):
        print(f'{category}: {name}')
    print(f'Checked {blobs} unique blobs and {commits} commits; {len(findings)} findings.')
    return int(bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())
