"""Install reviewed privacy hooks in Git-local storage, surviving branch changes."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

try:
    from .privacy_gate import config, scanner_path
    from .check_publication import git, load_markers
except ImportError:
    from privacy_gate import config, scanner_path
    from check_publication import git, load_markers


def install(private_markers=None):
    root = Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve()
    os.chdir(root)
    common = Path(git('rev-parse', '--git-common-dir').decode().strip()).resolve()
    destination = common / 'privacy-hooks'
    old_path = config('core.hooksPath')
    if old_path and Path(old_path).resolve() != destination:
        raise ValueError('Existing custom hooks must be integrated manually')
    if not old_path and any(p.is_file() and not p.name.endswith('.sample')
                            for p in (common / 'hooks').glob('*')):
        raise ValueError('Existing hooks must be preserved')
    scanner = scanner_path(root)
    if private_markers:
        marker_path = Path(private_markers).resolve()
        load_markers(marker_path)
        if root / 'runtime' not in marker_path.parents:
            raise ValueError('Keep private marker files under ignored runtime storage')
        if subprocess.run(['git', 'check-ignore', '-q', '--', str(marker_path)],
                          capture_output=True).returncode:
            raise ValueError('Marker file must be ignored')
    source = Path(__file__).resolve().parent
    installed = common / 'privacy-gate'
    installed.mkdir(mode=0o700, exist_ok=True)
    destination.mkdir(mode=0o700, exist_ok=True)
    for name in ('privacy_gate.py', 'check_publication.py'):
        shutil.copyfile(source / name, installed / name)
    for hook, mode in [('pre-commit', 'staged'), ('pre-push', 'push')]:
        path = destination / hook
        path.write_text('#!/bin/sh\nexec python3 ' + shlex.quote(str(installed / 'privacy_gate.py')) + ' ' + mode + '\n')
        path.chmod(0o700)
    git('config', '--local', 'privacy.gitleaksPath', scanner)
    if private_markers:
        git('config', '--local', 'privacy.markersFile', str(marker_path))
    git('config', '--local', 'core.hooksPath', str(destination))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-markers', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        install(args.private_markers)
        print('Installed local pre-commit and pre-push privacy checks. Reinstall after reviewed gate changes.')
        return 0
    except Exception:
        print('Hook installation could not complete; existing configuration preserved where possible. Details withheld.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
