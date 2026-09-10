"""Fail-closed staged/history privacy gate; detailed output stays under runtime/."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

try:
    from .check_publication import audit, content_issues, git, load_markers, tag_objects
except ImportError:
    from check_publication import audit, content_issues, git, load_markers, tag_objects


def config(key):
    result = subprocess.run(['git', 'config', '--get', key], capture_output=True)
    if result.returncode not in (0, 1):
        raise RuntimeError('Cannot read local configuration')
    return result.stdout.decode().strip()


def scanner_path(root):
    configured = config('privacy.gitleaksPath')
    candidate = configured or (root / '.tools/gitleaks')
    if Path(candidate).is_file():
        return str(Path(candidate).resolve())
    if configured:
        raise RuntimeError('Configured secret scanner unavailable')
    found = shutil.which('gitleaks')
    if not found:
        raise RuntimeError('Secret scanner unavailable')
    return found


def outgoing(text, markers):
    revisions = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 4:
            raise ValueError('Invalid pre-push input')
        local_ref, local_oid, remote_ref, remote_oid = fields
        if any(not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', oid)
               for oid in (local_oid, remote_oid)):
            raise ValueError('Full object IDs required')
        if content_issues((local_ref + '\n' + remote_ref).encode(), markers):
            raise ValueError('Private outgoing reference')
        if set(local_oid) != {'0'}:
            revisions.append(local_oid)
    return revisions


def export_index(destination):
    # Export the exact staged blobs, never unstaged working files or symlink targets.
    for record in git('ls-files', '--stage', '-z').split(b'\0'):
        if not record:
            continue
        metadata, raw_name = record.split(b'\t', 1)
        mode, oid, stage = metadata.decode().split()
        name = PurePosixPath(raw_name.decode())
        if mode not in ('100644', '100755') or stage != '0' or name.is_absolute() or '..' in name.parts:
            raise ValueError('Unsafe index entry')
        target = destination.joinpath(*name.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git('cat-file', 'blob', oid))


def scan(scanner, kind, target, report_dir, label, revisions=()):
    # Explicit default rules and an empty ignore file prevent repository allowlists
    # or inline suppression comments from silently weakening this gate.
    rules = report_dir / 'scanner.toml'
    rules.write_text('[extend]\nuseDefault = true\n')
    ignore = report_dir / 'scanner.ignore'
    ignore.write_text('')
    command = [scanner, kind, '--redact', '--no-banner', '--no-color',
               '--ignore-gitleaks-allow', '--config', str(rules),
               '--gitleaks-ignore-path', str(ignore)]
    if kind == 'git':
        command.append('--log-opts=--all ' + ' '.join(revisions))
    command.append(str(target))
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GITLEAKS_')}
    result = subprocess.run(command, capture_output=True, env=environment, timeout=300)
    (report_dir / (label + '.log')).write_bytes(result.stdout + result.stderr)
    return result.returncode == 0


def run(mode, push_input='', text_file=None):
    root = Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve()
    os.chdir(root)
    runtime = root / 'runtime'
    if runtime.is_symlink() or (runtime.exists() and not runtime.is_dir()):
        raise ValueError('Unsafe private report directory')
    runtime.mkdir(exist_ok=True)
    # Reports must be excluded even on a checkout that lacks the project ignore file.
    if subprocess.run(['git', 'check-ignore', '-q', '--', 'runtime/privacy-gate-report'],
                      capture_output=True).returncode or git('ls-files', '--', 'runtime'):
        raise ValueError('Private reports are not safely ignored')
    marker_file = config('privacy.markersFile')
    if not marker_file and (runtime / 'privacy-private-markers.json').exists():
        marker_file = str(runtime / 'privacy-private-markers.json')
    markers = load_markers(marker_file or None)
    revisions = outgoing(push_input, markers) if mode == 'push' else []
    history = mode in ('push', 'ci')
    if mode == 'text':
        draft = Path(text_file).read_bytes()
        findings = {(issue, 'publication draft') for issue in content_issues(draft, markers)}
        blobs, commits = 1, 0
    else:
        findings, blobs, commits = audit(history, markers, revisions)
    identities = b''
    if mode == 'staged':
        identities = git('var', 'GIT_AUTHOR_IDENT') + git('var', 'GIT_COMMITTER_IDENT')
        findings.update((issue, 'local commit identity') for issue in content_issues(identities, markers))
    report_dir = Path(tempfile.mkdtemp(prefix='privacy-gate-', dir=runtime))
    (report_dir / 'publication.json').write_text(json.dumps(
        dict(findings=sorted(findings), blobs=blobs, commits=commits), indent=2))
    if findings:
        categories = ', '.join(sorted({issue for issue, _ in findings}))
        print(f'Privacy gate blocked: {len(findings)} publication findings ({categories}); details withheld.')
        return 1
    scanner = scanner_path(root)
    with tempfile.TemporaryDirectory(prefix='export-', dir=report_dir) as directory:
        snapshot = Path(directory) / 'staged'
        snapshot.mkdir()
        if mode == 'text':
            (snapshot / 'draft.txt').write_bytes(draft)
        else:
            export_index(snapshot)
        clean = scan(scanner, 'dir', snapshot, report_dir, 'staged')
        if history:
            clean = scan(scanner, 'git', root, report_dir, 'history', revisions) and clean
        metadata = Path(directory) / 'metadata'
        metadata.mkdir()
        (metadata / 'identity.txt').write_bytes(identities)
        if history:
            for oid in git('rev-list', '--all', *revisions).decode().splitlines():
                (metadata / (oid + '.txt')).write_bytes(git('cat-file', 'commit', oid))
            refs = git('for-each-ref', '--format=%(refname)').decode().splitlines()
            (metadata / 'refs.txt').write_text('\n'.join(refs) + '\n' + push_input)
            for oid, data in tag_objects([*refs, *revisions]):
                (metadata / f'tag-{oid}.txt').write_bytes(data)
        clean = scan(scanner, 'dir', metadata, report_dir, 'metadata') and clean
    if not clean:
        print('Privacy gate blocked: secret scanner found a problem or could not complete; details withheld.')
        return 1
    print(f'Privacy gate passed: {blobs} blobs, {commits} commits; publication and secret scans clean.')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['staged', 'push', 'ci', 'text'])
    parser.add_argument('--text-file', type=Path, help='Private draft to scan before posting public text')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if (args.mode == 'text') != bool(args.text_file):
            raise ValueError('Text mode requires a draft file')
        return run(args.mode, sys.stdin.read() if args.mode == 'push' else '', args.text_file)
    except Exception:
        print('Privacy gate could not complete. Commit/push blocked; details withheld.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
