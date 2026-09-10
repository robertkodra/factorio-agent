"""Check staged files and optional Git history without printing matched values."""
import argparse
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote_to_bytes


CONTENT_RULES = {
    'personal-path': re.compile(rb"""(?:/(?:Users|home)/[^/\s"'<>]+|/(?:private/)?var/folders/|[A-Za-z]:/+Users/+[^/\s"'<>]+)""", re.I),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
    'access-token': re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{25,}|AKIA[A-Z0-9]{16}|xox[baprs]-[A-Za-z0-9-]{20,})'),
    'credential-url': re.compile(rb'https?://[^\s/@:]+:[^\s/@]+@'),
}
EMAIL = re.compile(rb'[A-Za-z0-9_.+%-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PRIVATE_DIRS = {'runtime', 'checkpoints', 'evidence', '.venv', '.tools', '__pycache__',
                '.ssh', '.aws', '.azure', '.config', '.codex', '.agents', '.idea', '.vscode'}
PRIVATE_SUFFIXES = ('.zip', '.bundle', '.tar', '.gz', '.7z', '.log', '.jsonl', '.pem', '.key', '.p12', '.pfx', '.env', '.pyc',
                    '.sqlite', '.sqlite3', '.db', '.bak', '.orig', '.pcap', '.dmp')
TEXT_SUFFIXES = {'.py', '.lua', '.json', '.md', '.txt', '.yml', '.yaml', '.toml'}
TEXT_NAMES = {'.gitignore', 'LICENSE'}


def git(*args):
    return subprocess.check_output(['git', *args], stderr=subprocess.PIPE)


def tag_objects(refs):
    seen = set()
    for ref in refs:
        while git('cat-file', '-t', ref).strip() == b'tag':
            oid = git('rev-parse', ref).decode().strip()
            if oid in seen:
                break
            seen.add(oid)
            data = git('cat-file', 'tag', oid)
            yield oid, data
            ref = data.splitlines()[0].removeprefix(b'object ').decode()


def normalized(data):
    # Check common copied JSON/URL forms too, without evaluating supplied text.
    for _ in range(2):
        data = unquote_to_bytes(data)
        data = re.sub(rb'\\u([0-9a-fA-F]{4})',
                      lambda m: chr(int(m[1],16)).encode('utf-8',errors='surrogatepass'), data)
        data = data.replace(b'\\/', b'/')
    return re.sub(rb'\\+', b'/', data)


def content_issues(data, markers=()):
    decoded = normalized(data)
    issues = {name for name, pattern in CONTENT_RULES.items()
              if pattern.search(data) or pattern.search(decoded)}
    if any(match.group(1).lower() != b'users.noreply.github.com'
           and match.group(0).lower() != b'noreply@github.com' for match in EMAIL.finditer(decoded)):
        issues.add('non-noreply-email')
    if any(value in data or normalized(value) in decoded for value in markers):
        issues.add('private-local-value')
    return issues


def file_issues(name, mode, data, markers=()):
    path = PurePosixPath(name)
    lower = PurePosixPath(name.lower())
    issues = content_issues(name.encode(), markers)
    if (set(lower.parts) & PRIVATE_DIRS or str(lower).startswith('knowledge/runs/')
            or lower.name.startswith(('.env', 'id_rsa', 'id_ed25519', 'rcon-password'))
            or lower.name in {'server-settings.json', 'config.ini', '.ds_store', 'credentials',
                              'credentials.json', 'credentials.yml', 'secrets.json', 'secrets.yml',
                              'secrets.yaml', 'settings.local.json', '.npmrc', '.pypirc', '.netrc'}
            or str(lower).endswith(PRIVATE_SUFFIXES)):
        issues.add('private-artifact')
    if mode not in ('100644', '100755'):
        issues.add('non-regular-file')
    if path.suffix not in TEXT_SUFFIXES and name not in TEXT_NAMES:
        issues.add('unreviewed-file-type')
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        issues.add('binary-content')
    if b'\x00' in data or data.startswith((b'PK\x03\x04', b'\x1f\x8b')):
        issues.add('binary-content')
    return issues | content_issues(data, markers)


def audit(history=False, markers=(), revisions=()):
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
        for issue in file_issues(name, mode, blobs[oid], markers):
            findings.add((issue, name))

    for record in git('ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        metadata, name = record.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        if stage != '0':
            findings.add(('unmerged-index', name.decode()))
        check_entry(name.decode(), mode, oid)

    commits = git('rev-list', '--all', *revisions).decode().splitlines() if history else []
    for commit in commits:
        for issue in content_issues(git('cat-file', 'commit', commit), markers):
            findings.add((issue, 'commit metadata ' + commit[:12]))
        for record in git('ls-tree', '-r', '-z', commit).split(b'\0'):
            if not record:
                continue
            metadata, name = record.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            check_entry(name.decode(), mode, oid)

    if history:
        for ref in git('for-each-ref', '--format=%(refname)').decode().splitlines():
            for issue in content_issues(ref.encode(), markers):
                findings.add((issue, 'ref ' + ref))
        refs = git('for-each-ref', '--format=%(refname)', 'refs/tags').decode().splitlines()
        for oid, data in tag_objects([*refs, *revisions]):
            for issue in content_issues(data, markers):
                findings.add((issue, 'tag metadata ' + oid[:12]))
    return findings, len(blobs), len(commits)


def load_markers(path):
    if path is None:
        return ()
    values = json.loads(Path(path).read_text())
    if (not isinstance(values, list) or len(values)>1000 or
            any(not isinstance(v,str) or not 4<=len(v)<=4096 for v in values)):
        raise ValueError('Invalid private marker file')
    return tuple(v.encode() for v in values)


def private_report(path, report):
    path = Path(path).resolve()
    if Path.cwd().resolve()/'runtime' not in path.parents:
        raise ValueError('Reports must stay in local ignored runtime storage')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        path.chmod(0o600)
        json.dump(report, stream, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Also inspect every reachable commit and tag')
    parser.add_argument('--revision', action='append', default=[], help='Additional outgoing object ID to scan')
    parser.add_argument('--private-markers', type=Path, help='Optional local values to block; never commit this file')
    parser.add_argument('--private-report', type=Path, help='Write locations only to a new file under runtime/')
    args = parser.parse_args()
    try:
        if any(not re.fullmatch('[0-9a-fA-F]{40}|[0-9a-fA-F]{64}',oid) for oid in args.revision):
            raise ValueError('Full object IDs required')
        findings, blobs, commits = audit(args.history, load_markers(args.private_markers), args.revision)
        if args.private_report:
            private_report(args.private_report, dict(findings=sorted(findings), blobs=blobs, commits=commits))
        for i, (category, _) in enumerate(sorted(findings),1):
            print(f'{category}: finding {i} (location withheld)')
        print(f'Checked {blobs} unique blobs and {commits} commits; {len(findings)} findings.')
        return int(bool(findings))
    except Exception:
        # Git errors and JSON parsing errors can themselves contain private paths.
        print('Publication audit could not complete; details withheld. Publication blocked.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
