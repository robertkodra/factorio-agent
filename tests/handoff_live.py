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
from client.server import GAME, MOD_DIRECTORY, controller_mod_list


def free_port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def validate_mcp(port, password):
    """Exercise the real stdio facade on this disposable, auto-paused fixture."""
    import sys
    import anyio
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    async def check():
        params = StdioServerParameters(command=sys.executable, cwd=ROOT,
            args=['-m', 'client.mcp_server', '--port', str(port), '--password-file', str(password)])
        async with Client(params, mode='legacy', read_timeout_seconds=10) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 13

            async def call(name, **arguments):
                response = await client.call_tool(name, arguments)
                assert not response.is_error, response.content
                return response.structured_content

            hello = await call('hello')
            before = await call('observe')
            factory = await call('factory')
            research = await call('research_state')
            await call('scan', radius=1, limit=1)
            assert hello['version'] == '0.2.0'
            assert factory['produced']['logistic-science-pack'] == 20
            assert 'logistics' in research['researched']
            invalid = await client.call_tool('submit', dict(id='must-not-send', actions=[dict(type='execute_lua')]))
            assert invalid.is_error and invalid.structured_content['error'] == 'invalid_arguments'
            job_id = 'mcp-check-' + secrets.token_hex(4)
            submitted = await call('submit', id=job_id, actions=[dict(type='wait_ticks', ticks=216000)])
            assert submitted['status'] == 'running'
            status = await call('status', id=job_id)
            assert status['status'] == 'running'
            stopped = await call('cancel', id=job_id)
            assert stopped['status'] == 'cancelled'
            after = await call('observe')
            for key in ('tick', 'inventory', 'position'):
                assert after[key] == before[key]
            return dict(protocol=client.protocol_version, tools=len(tools),
                        controller=hello['version'], fixed_observations=True,
                        invalid_action_rejected=True, submit_status_cancel=True,
                        observation_preserved_tick_inventory_position=True)
    return anyio.run(check)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--save', type=Path, required=True, help='Private historical green-science fixture; never commit it')
    parser.add_argument('--mcp', action='store_true', help='Also exercise the optional MCP facade on the isolated copy')
    options = parser.parse_args()
    source = options.save.resolve()
    if not source.is_file():
        parser.error('The private historical checkpoint must exist')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    folder = ROOT / 'runtime' / ('handoff-validation-' + secrets.token_hex(4))
    folder.mkdir(parents=True, mode=0o700)
    (folder / 'data').mkdir()
    mods = folder / 'mods'
    mods.mkdir()
    shutil.copytree(ROOT / 'mod/codex-controller', mods / MOD_DIRECTORY)
    (mods / 'mod-list.json').write_text(json.dumps(controller_mod_list()))
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
            assert before['mods'] == {'base': '2.0.77', 'codex-controller': '0.2.0'}
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
        if options.mcp:
            report['mcp'] = validate_mcp(rcon_port, password)
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
