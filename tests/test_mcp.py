"""MCP contracts and real stdio/RCON fault recovery; no Factorio needed."""
import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock

from client.agent import Agent, AgentRejected, ROOT
from client.tool_schemas import ACTIONS, READ_ONLY, TOOLS
from tests.test_transport import read_packet

HAS_MCP = all(importlib.util.find_spec(name) is not None for name in ("mcp", "jsonschema", "anyio"))
if HAS_MCP:
    import anyio
    from jsonschema import Draft202012Validator
    from mcp import Client, MCPError
    from mcp.client.stdio import StdioServerParameters
    from client.mcp_server import Bridge, RequestValidator, create_server


class RconFixture:
    """A real socket peer that accepts a job, optionally dropping its reply."""

    def __init__(self, drop_submit=False):
        self.drop_submit = drop_submit
        self.received = []
        self.jobs = {}
        self.connections = 0
        self.errors = []
        self.stop = threading.Event()

    def __enter__(self):
        self.folder = tempfile.TemporaryDirectory()
        self.password = Path(self.folder.name) / "password"
        self.password.write_text("test-only")
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.listener.settimeout(0.1)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()
        return self

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    peer, _ = self.listener.accept()
                except socket.timeout:
                    continue
                with peer:
                    peer.settimeout(3)
                    self.connections += 1
                    rid, kind, password = read_packet(peer)
                    assert kind == 3 and password == b"test-only"
                    peer.sendall(Agent._packet(rid, 2, ""))
                    while not self.stop.is_set():
                        try:
                            rid, kind, wire = read_packet(peer)
                        except EOFError:
                            break
                        assert kind == 2 and wire.startswith(b"/codex-agent ")
                        req = json.loads(wire[len(b"/codex-agent "):])
                        self.received.append(req)
                        op = req["op"]
                        if op == "submit":
                            self.jobs.setdefault(req["id"], dict(id=req["id"], status="running"))
                            if self.drop_submit:
                                self.drop_submit = False
                                break
                            out = self.jobs[req["id"]]
                        elif op == "status":
                            out = self.jobs[req["id"]]
                        elif op == "cancel":
                            out = self.jobs[req["id"]]
                            out["status"] = "cancelled"
                        else:
                            out = dict(version="0.2.0", op=op)
                        peer.sendall(Agent._packet(rid, 0, json.dumps(dict(ok=True, result=out))))
        except BaseException as exc:
            self.errors.append(exc)

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(4)
        self.listener.close()
        self.folder.cleanup()
        if self.thread.is_alive():
            raise AssertionError("RCON fixture did not stop")
        if self.errors:
            raise self.errors[0]

    def factory(self):
        return Agent(port=self.port, password_file=self.password, timeout=2)


@unittest.skipUnless(HAS_MCP, "Optional MCP tests: install requirements-mcp.txt with Python 3.10+")
class McpTests(unittest.IsolatedAsyncioTestCase):
    def test_optimized_validation_matches_advertised_schema(self):
        schema = TOOLS['submit'][0]
        reference, optimized = Draft202012Validator(schema), RequestValidator(schema)
        # Exercise every discriminator, field, required key, bound, and unknown
        # field with JSON values; compare acceptance to the published oneOf.
        values = [None, True, False, 0, -1, 1, 0.1, 216000, 216001, 1000001,
                  'coal', 'north', 'fuel', '', [], {}, ['walk']]
        for branch in ACTIONS:
            fields = branch['properties']
            action = {}
            for key, field in fields.items():
                if key == 'type':
                    action[key] = field['const']
                elif 'enum' in field:
                    action[key] = field['enum'][0]
                elif field.get('type') == 'string':
                    action[key] = 'coal'
                else:
                    action[key] = max(1, field.get('minimum', 1))
            candidates = [action]
            for key in fields:
                omitted = dict(action)
                del omitted[key]
                candidates.append(omitted)
                candidates.extend(dict(action, **{key: value}) for value in values)
            candidates.extend([dict(action, code='return 1'), {}, [], None, True])
            for candidate in candidates:
                payload = dict(id='validation', actions=[candidate])
                self.assertEqual(reference.is_valid(payload), optimized.is_valid(payload), payload)
        # A structurally copied or unrelated union must use standard validation.
        copied = copy.deepcopy(schema)
        self.assertTrue(RequestValidator(copied).is_valid(dict(id='copy', actions=[dict(type='wait_ticks', ticks=1)])))
        self.assertFalse(RequestValidator(dict(oneOf=[dict(type='number'), dict(type='integer')])).is_valid(1))

    async def test_initialize_and_discover_offline_without_credentials(self):
        factory = Mock(side_effect=AssertionError("Discovery must not connect"))
        async with Client(create_server(factory), mode="legacy") as client:
            self.assertTrue(client.protocol_version)
            listed = (await client.list_tools()).tools
            self.assertEqual({t.name for t in listed}, set(TOOLS))
            self.assertEqual(len(listed), 16)
            for tool in listed:
                Draft202012Validator.check_schema(tool.input_schema)
                self.assertEqual(tool.annotations.read_only_hint, tool.name in READ_ONLY)
                self.assertFalse(tool.input_schema["additionalProperties"])
            self.assertEqual(client.server_info.name, "factorio-controller")
        factory.assert_not_called()

    async def test_all_action_shapes_and_fixed_operations_round_trip(self):
        actions = [
            dict(type="walk", x=1, y=-2.5),
            dict(type="mine", x=1, y=2, count=1, entity="iron-ore"),
            dict(type="craft", recipe="iron-gear-wheel", count=2),
            dict(type="await_craft"),
            dict(type="place", x=1, y=2, entity="transport-belt", direction="east"),
            dict(type="put", x=1, y=2, item="coal", count=1, inventory="fuel"),
            dict(type="put", x=1, y=2, item="firearm-magazine", count=1,
                 inventory="ammo", player_inventory="ammo"),
            dict(type="take", x=1, y=2, item="coal", count=1, inventory="chest"),
            dict(type="wait_inventory", item="iron-plate", count=1),
            dict(type="research", technology="military-2"),
            dict(type="set_recipe", x=1, y=2, recipe="iron-gear-wheel"),
            dict(type="rotate", x=1, y=2),
            dict(type="wait_ticks", ticks=60, timeout=120),
            dict(type="launch", entity="rocket-silo", x=1, y=2),
        ]
        self.assertEqual({a["type"] for a in actions}, {a["properties"]["type"]["const"] for a in ACTIONS})
        agent = Mock()
        agent.request.side_effect = lambda op, **kw: dict(op=op, arguments=kw)
        factory = Mock(return_value=agent)
        examples = {"submit": dict(id="round-trip", actions=actions), "pause": dict(value=True),
                    "save": dict(name="checkpoint"), "inspect": dict(x=1, y=2),
                    "scan": dict(type="resource", name="iron-ore", radius=128, limit=100),
                    "survey": dict(radius=128, limit=100),
                    "placement": dict(x=1, y=2, entity="stone-furnace", direction="north"),
                    "status": dict(id="round-trip", after=0), "cancel": dict(id="round-trip"),
                    "guard": dict(enabled=True, rally=dict(x=1, y=2))}
        async with Client(create_server(factory)) as client:
            for name in TOOLS:
                args = examples.get(name, {})
                reply = await client.call_tool(name, args)
                self.assertFalse(reply.is_error)
                self.assertEqual(reply.structured_content, dict(op=name, arguments=args))
                self.assertEqual(json.loads(reply.content[0].text), reply.structured_content)
        factory.assert_called_once()
        agent.close.assert_called_once()

    async def test_invalid_requests_never_connect(self):
        factory = Mock(side_effect=AssertionError("Invalid requests must not connect"))
        invalid = [
            ("hello", {"op": "execute_lua"}), ("observe", {"code": "return 1"}),
            ("scan", {"radius": 129}), ("scan", {"limit": True}),
            ("scan", {"radius": float("nan")}), ("scan", {"radius": float("inf")}),
            ("survey", {"radius": 129}), ("survey", {"limit": 101}),
            ("survey", {"radius": float("nan")}), ("survey", {"x": 100000}),
            ("placement", {"x": 1, "y": 2}),
            ("placement", {"x": 1, "y": 2, "entity": "stone-furnace", "direction": "up"}),
            ("inspect", {"x": 1}), ("bind", {"player": 0}),
            ("pause", {"value": 1}), ("status", {"after": -1}),
            ("guard", {"enabled": 1}), ("guard", {"enabled": True, "code": "x"}),
            ("guard", {"enabled": True, "rally": {"x": 1}}),
            ("save", {"name": "../overwrite"}), ("save", {"name": "bad\n"}),
        ]
        bad_actions = [
            [], [dict(type="execute_lua", code="return 1")],
            [dict(type="wait_ticks", ticks=1, code="return 1")],
            [dict(type="wait_ticks", ticks=True)], [dict(type="wait_ticks", ticks="1")],
            [dict(type="wait_ticks", ticks=216001)],
            [dict(type="craft", recipe="iron-plate", count=0)],
            [dict(type="walk", x=1000001, y=0)],
            [dict(type="walk", x=0, y=0, tolerance=.01)],
            [dict(type="wait_inventory", item="coal", count=1, x=0)],
            [dict(type="rotate", x=0, y=0, direction="east")],
            [dict(type="put", x=0, y=0, item="coal", count=1, player_inventory="guns")],
            [dict(type="walk", x=0, y=0, player_inventory="ammo")],
            [dict(type="wait_ticks", ticks=1)] * 513,
        ]
        invalid.extend(("submit", dict(id="invalid", actions=a)) for a in bad_actions)
        async with Client(create_server(factory)) as client:
            for name, args in invalid:
                with self.subTest(name=name, args=args):
                    reply = await client.call_tool(name, args)
                    self.assertTrue(reply.is_error)
                    self.assertEqual(reply.structured_content["error"], "invalid_arguments")
            for name in ("execute_lua", "spawn_item", "teleport", "complete_research"):
                with self.assertRaises(MCPError):
                    await client.call_tool(name, {})
        factory.assert_not_called()

    async def test_byte_limit_before_transport(self):
        factory = Mock(side_effect=AssertionError("Oversized requests must not connect"))
        action = dict(type="mine", x=1, y=2, count=1, entity="a"*120, item="b"*120)
        async with Client(create_server(factory)) as client:
            reply = await client.call_tool("submit", dict(id="too-big", actions=[action]*512))
            self.assertTrue(reply.is_error)
            self.assertIn("byte limit", reply.structured_content["message"])
        factory.assert_not_called()

    async def test_connection_failure_is_not_sent_and_does_not_leak_path(self):
        factory = Mock(side_effect=FileNotFoundError("private machine path"))
        async with Client(create_server(factory)) as client:
            reply = await client.call_tool("observe")
            self.assertEqual(reply.structured_content["outcome"], "not_sent")
            self.assertNotIn("private machine path", reply.content[0].text)
        factory.assert_called_once()

    async def test_controller_rejection_keeps_connection(self):
        agent = Mock()
        agent.request.side_effect = [AgentRejected("out_of_reach"), dict(status="idle")]
        factory = Mock(return_value=agent)
        async with Client(create_server(factory)) as client:
            reply = await client.call_tool("inspect", dict(x=0, y=0))
            self.assertEqual(reply.structured_content["error"], "controller_rejected")
            self.assertNotIn("outcome", reply.structured_content)
            self.assertFalse((await client.call_tool("status")).is_error)
        factory.assert_called_once()

    async def test_dropped_submission_reconciles_and_cancels_over_real_rcon(self):
        with RconFixture(drop_submit=True) as peer:
            async with Client(create_server(peer.factory)) as client:
                reply = await client.call_tool("submit", dict(id="lost", actions=[dict(type="wait_ticks", ticks=600)]))
                self.assertTrue(reply.is_error)
                self.assertEqual(reply.structured_content["outcome"], "unknown")
                self.assertEqual(reply.structured_content["reconcile"], dict(tool="status", arguments=dict(id="lost")))
                self.assertEqual(peer.connections, 1)
                status = await client.call_tool("status", dict(id="lost"))
                self.assertEqual(status.structured_content["status"], "running")
                stopped = await client.call_tool("cancel", dict(id="lost"))
                self.assertEqual(stopped.structured_content["status"], "cancelled")
            self.assertEqual([r["op"] for r in peer.received], ["submit", "status", "cancel"])
            self.assertEqual(peer.connections, 2)

    async def test_stdio_process_initializes_and_uses_persistent_rcon(self):
        with RconFixture() as peer:
            params = StdioServerParameters(command=sys.executable, cwd=peer.folder.name,
                args=[str(ROOT / "scripts/run_mcp.py"), "--port", str(peer.port), "--password-file", str(peer.password)])
            async with Client(params, mode="legacy", read_timeout_seconds=5) as client:
                self.assertEqual(len((await client.list_tools()).tools), 16)
                self.assertEqual(peer.connections, 0)
                self.assertEqual((await client.call_tool("hello")).structured_content["version"], "0.2.0")
                job = dict(id="stdio-job", actions=[dict(type="wait_ticks", ticks=216000)])
                self.assertEqual((await client.call_tool("submit", job)).structured_content["status"], "running")
                self.assertEqual((await client.call_tool("status", dict(id="stdio-job"))).structured_content["status"], "running")
                self.assertEqual((await client.call_tool("cancel", dict(id="stdio-job"))).structured_content["status"], "cancelled")
            self.assertEqual(peer.connections, 1)

    async def test_slow_rcon_does_not_block_mcp_discovery(self):
        entered, release = threading.Event(), threading.Event()
        agent = Mock()
        def request(op, **kw):
            entered.set()
            if not release.wait(3):
                raise TimeoutError()
            return dict(status="running")
        agent.request.side_effect = request
        async with Client(create_server(lambda: agent)) as client:
            task = asyncio.create_task(client.call_tool("status"))
            try:
                self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                tools = await asyncio.wait_for(client.list_tools(cache_mode="bypass"), 1)
                self.assertEqual(len(tools.tools), 16)
            finally:
                release.set()
                await task

    async def test_cancellation_does_not_replay_or_interrupt_wire_exchange(self):
        entered, release = threading.Event(), threading.Event()
        agent = Mock()
        def request(op, **kw):
            if op == "submit":
                entered.set()
                if not release.wait(3):
                    raise TimeoutError()
            return dict(status="running")
        agent.request.side_effect = request
        bridge = Bridge(lambda: agent)
        async def submit():
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                await bridge.call("submit", dict(id="cancel-waiter", actions=[dict(type="wait_ticks", ticks=1)]))
        scopes = []
        try:
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(submit)
                self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                scopes[0].cancel()
                release.set()
            reply = await bridge.call("status", dict(id="cancel-waiter"))
            self.assertFalse(reply.is_error)
            self.assertEqual([c.args[0] for c in agent.request.call_args_list], ["submit", "status"])
        finally:
            release.set()
            bridge.close()


if __name__ == "__main__":
    unittest.main()
