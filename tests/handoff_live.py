"""Reload a COPY of the historical save and test fixed observations, never Lua input.

Runs an isolated, unadvertised server with no GUI connection, then shuts it down.
Raw server logs and fresh credentials remain in the ignored runtime directory.
"""
import argparse
import hashlib
import json
import secrets
import shutil
import signal
import socket
import subprocess
import time
from pathlib import Path

from client.agent import Agent, AgentError, ROOT
from client.server import GAME, MOD_DIRECTORY


def free_port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', type=Path, required=True, help='Private historical green-science fixture; never commit it')
    source = parser.parse_args().save.resolve()
    if not source.is_file():
        parser.error('The private historical checkpoint must exist')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = ROOT / 'runtime' / ('handoff-validation-' + secrets.token_hex(4))
    folder.mkdir(parents=True, mode=0o700)
    (folder / 'data').mkdir()
    mods = folder / 'mods'
    mods.mkdir()
    shutil.copytree(ROOT / 'mod/codex-controller', mods / MOD_DIRECTORY)
    (mods / 'mod-list.json').write_text(json.dumps({'mods': [
        {'name': 'base', 'enabled': True}, {'name': 'codex-controller', 'enabled': True}]}))
    save = folder / 'checkpoint-copy.zip'
    shutil.copy2(source, save)
    password = folder / 'rcon-password'
    password.write_text(secrets.token_urlsafe(32)); password.chmod(0o600)
    config = folder / 'config.ini'
    config.write_text(f'[path]\nread-data={GAME / "data"}\nwrite-data={folder / "data"}\n')
    settings = folder / 'server-settings.json'
    settings.write_text(json.dumps({'name': 'Local handoff validation',
        'description': 'Isolated checkpoint and fixed-command validation', 'max_players': 1,
        'visibility': {'public': False, 'lan': False}, 'require_user_verification': False,
        'auto_pause': True, 'autosave_interval': 0, 'allow_commands': 'false'}))
    game_port = free_port(socket.SOCK_DGRAM); rcon_port = free_port(socket.SOCK_STREAM)
    args = [str(GAME / 'MacOS/factorio'), '--config', str(config), '--mod-directory', str(mods),
            '--start-server', str(save), '--server-settings', str(settings),
            '--bind', f'127.0.0.1:{game_port}', '--rcon-bind', f'127.0.0.1:{rcon_port}',
            '--rcon-password', password.read_text()]
    with (folder / 'private-process.log').open('w') as log:
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT)
    report = {}
    try:
        end = time.monotonic() + 40
        while True:
            if proc.poll() is not None:
                raise RuntimeError('Validation server exited; inspect private log without exposing launch credentials')
            try:
                agent = Agent(port=rcon_port, password_file=password, timeout=2)
                break
            except (OSError, AgentError):
                if time.monotonic() >= end: raise
                time.sleep(.25)
        with agent:
            hello = agent.request('hello')
            before = agent.request('observe')
            factory = agent.request('factory')
            research = agent.request('research_state')
            rejected = []
            for op in ['execute_lua', 'spawn_item', 'complete_research', 'teleport']:
                try: agent.request(op)
                except AgentError as exc:
                    assert 'unknown_operation' in str(exc)
                    rejected.append(op)
                else: raise AssertionError('Unexpectedly accepted forbidden operation')
            after = agent.request('observe')
            assert hello['version'] == '0.2.0'
            assert factory['produced']['logistic-science-pack'] == 20
            assert research['produced']['automation-science-pack'] == 114
            assert 'logistics' in research['researched']
            assert before['inventory'] == after['inventory']
            assert before['position'] == after['position']
            assert before['tick'] == after['tick']
            report = dict(controller=hello['version'], checkpoint_loaded=True,
                          source_sha256=digest, fixed_factory_query=True,
                          fixed_research_query=True, rejected_operations=rejected,
                          observation_preserved_tick_inventory_position=True,
                          tick=after['tick'], game_speed=after['speed'],
                          mod_allowlist=after['mods'], console_lua_sent=False)
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try: proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    (folder / 'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
