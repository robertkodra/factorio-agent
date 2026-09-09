"""Local stdio MCP facade around the fixed Factorio controller operations."""
from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from functools import partial
import json
from pathlib import Path

import anyio
from jsonschema import Draft202012Validator, ValidationError, validators
from mcp import MCPError
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import INVALID_PARAMS, CallToolResult, ListToolsResult, TextContent, Tool, ToolAnnotations

from client.agent import Agent, AgentError, AgentRejected
from client.tool_schemas import ACTIONS, READ_ONLY, TOOLS


ACTION_BY_TYPE = {schema["properties"]["type"]["const"]: schema for schema in ACTIONS}
assert len(ACTION_BY_TYPE) == len(ACTIONS)
assert all("type" in schema["required"] for schema in ACTIONS)


def action_one_of(validator, choices, instance, schema):
    # The action alternatives have distinct required type constants, so at most
    # one can match. Validate that complete branch instead of testing 12 branches
    # for every action. Other oneOf schemas keep standard JSON Schema semantics.
    if choices is not ACTIONS:
        yield from Draft202012Validator.VALIDATORS["oneOf"](validator, choices, instance, schema)
        return
    kind = instance.get("type") if isinstance(instance, dict) else None
    if not isinstance(kind, str) or kind not in ACTION_BY_TYPE:
        yield ValidationError("Unknown or missing action type")
        return
    yield from validator.descend(instance, ACTION_BY_TYPE[kind])


RequestValidator = validators.extend(Draft202012Validator, {"oneOf": action_one_of})


def result(payload, error=False):
    return CallToolResult(content=[TextContent(type="text", text=json.dumps(payload, allow_nan=False))],
                          structured_content=payload, is_error=error)


class Bridge:
    """One lazy persistent connection; never wait for an entire gameplay job."""

    def __init__(self, agent_factory=Agent):
        self.agent_factory = agent_factory
        self.agent = None
        self.lock = anyio.Lock()

    def close(self):
        if self.agent is not None:
            self.agent.close()
            self.agent = None

    def request(self, op, arguments):
        if self.agent is None:
            try:
                self.agent = self.agent_factory()
            except (OSError, AgentError):
                # Do not expose credentials or machine paths in error responses.
                return result(dict(error="connection_unavailable", outcome="not_sent",
                                   message="Check the local server and RCON password file."), True)
        try:
            return result(self.agent.request(op, **arguments))
        except AgentRejected as exc:
            return result(dict(error="controller_rejected", message=str(exc)), True)
        except (OSError, AgentError, ValueError, TypeError):
            self.close()
            payload = dict(error="transport_failure", outcome="unknown",
                           message="No automatic replay. Reconnect with an explicit observation. "
                                   "The game may still be executing the command.")
            if op == "submit":
                payload["reconcile"] = dict(tool="status", arguments=dict(id=arguments["id"]))
            elif op == "cancel" and "id" in arguments:
                payload["reconcile"] = dict(tool="status", arguments=dict(id=arguments["id"]))
            return result(payload, True)

    async def call(self, op, arguments):
        async with self.lock:
            # Once a wire exchange starts, consume its reply (or timeout) before
            # another request touches the socket, even if MCP cancels its waiter.
            # Cancellation while waiting for this lock never sends a command.
            with anyio.CancelScope(shield=True):
                return await anyio.to_thread.run_sync(self.request, op, arguments)


def create_server(agent_factory=Agent):
    request_validators = {name: RequestValidator(schema) for name, (schema, _) in TOOLS.items()}

    @asynccontextmanager
    async def lifespan(server):
        bridge = Bridge(agent_factory)
        try:
            yield bridge
        finally:
            bridge.close()

    async def list_tools(ctx, params):
        return ListToolsResult(tools=[
            Tool(name=name, description=description, input_schema=schema,
                 annotations=ToolAnnotations(read_only_hint=name in READ_ONLY,
                                             destructive_hint=name not in READ_ONLY,
                                             idempotent_hint=name in READ_ONLY or name == "submit",
                                             open_world_hint=False))
            for name, (schema, description) in TOOLS.items()
        ])

    async def call_tool(ctx, params):
        if params.name not in TOOLS:
            raise MCPError(code=INVALID_PARAMS, message="Unknown Factorio tool")
        arguments = params.arguments if params.arguments is not None else {}
        try:
            encoded = json.dumps(dict(op=params.name, **arguments), allow_nan=False, separators=(",", ":"))
        except (ValueError, TypeError):
            return result(dict(error="invalid_arguments", message="Arguments must be finite JSON values."), True)
        if len(encoded.encode("utf-8")) > 131072:
            return result(dict(error="invalid_arguments", message="Request exceeds controller byte limit."), True)
        violation = next(request_validators[params.name].iter_errors(arguments), None)
        if violation is not None:
            # Report where validation failed without echoing arbitrary input.
            return result(dict(error="invalid_arguments", path=list(violation.absolute_path),
                               rule=violation.validator,
                               message="Arguments do not match the advertised tool schema."), True)
        return await ctx.lifespan_context.call(params.name, arguments)

    return Server("factorio-controller", version="0.1.0", lifespan=lifespan,
                  instructions="Control Factorio with normal mechanics only. Check hello, then bind. "
                  "Submit bounded jobs and observe progress with status; never assume a timeout cancels work. "
                  "Use stable job IDs for recovery. A rocket requires an actual launch event; "
                  "this controller has only demonstrated early-game production.",
                  on_list_tools=list_tools, on_call_tool=call_tool)


async def serve(factory):
    server = create_server(factory)
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=27016)
    parser.add_argument("--password-file", type=Path)
    parser.add_argument("--timeout", type=float, default=5, help="RCON exchange timeout, seconds (0 < n <= 30)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or not 0 < args.timeout <= 30:
        parser.error("Port must be 1..65535 and timeout must be > 0 and <= 30 seconds")
    # Loopback and stdio only. No shell, console, arbitrary Lua, or network listener.
    anyio.run(serve, partial(Agent, port=args.port, password_file=args.password_file, timeout=args.timeout))


if __name__ == "__main__":
    main()
