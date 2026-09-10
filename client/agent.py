"""Persistent, dependency-free Factorio RCON transport for bounded tick jobs."""
from __future__ import annotations

import argparse
import json
import socket
import struct
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AgentError(RuntimeError):
    pass


class AgentRejected(AgentError):
    """The controller returned a definite rejection, rather than a lost reply."""


class Agent:
    def __init__(self, host="127.0.0.1", port=27016, password_file=None, timeout=5):
        password_file = Path(password_file or ROOT / "runtime/rcon-password")
        password = password_file.read_text().strip()
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.lock = threading.Lock()
        self.next_id = 1
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.sendall(self._packet(1, 3, password))
            for _ in range(3):
                rid, kind, _ = self._read_packet()
                if rid == -1:
                    raise AgentError("RCON authentication failed")
                if rid == 1 and kind == 2:
                    break
            else:
                raise AgentError("Missing RCON authentication response")
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _packet(rid, kind, body):
        data = struct.pack("<ii", rid, kind) + body.encode("utf-8") + b"\0\0"
        return struct.pack("<i", len(data)) + data

    def _read_exact(self, n):
        out = bytearray()
        while len(out) < n:
            part = self.sock.recv(n - len(out))
            if not part:
                raise ConnectionError("RCON closed; command outcome may be unknown")
            out.extend(part)
        return bytes(out)

    def _read_packet(self):
        size, = struct.unpack("<i", self._read_exact(4))
        if not 10 <= size <= 16 * 1024 * 1024:
            raise AgentError("Invalid RCON packet length")
        packet = self._read_exact(size)
        if packet[-2:] != b"\0\0":
            raise AgentError("Invalid RCON packet terminator")
        rid, kind = struct.unpack("<ii", packet[:8])
        return rid, kind, packet[8:-2]

    def request(self, op, **kwargs):
        body = json.dumps(dict(op=op, **kwargs), separators=(",", ":"), allow_nan=False)
        if len(body.encode()) > 131072:
            raise ValueError("Request exceeds controller limit")
        with self.lock:
            self.next_id += 1
            rid = self.next_id
            # Factorio returns a complete response in one length-prefixed packet.
            # Do not pipeline a second command: script-command scheduling can
            # otherwise produce an empty acknowledgement before its result.
            wire = self._packet(rid, 2, "/codex-agent " + body)
            try:
                self.sock.sendall(wire)
                response_id, kind, data = self._read_packet()
                if kind != 0 or response_id != rid:
                    raise AgentError("Unexpected RCON response type or ID")
                response = json.loads(data)
                if (not isinstance(response, dict) or type(response.get("ok")) is not bool
                        or (response["ok"] and "result" not in response)
                        or (not response["ok"] and not isinstance(response.get("error"), str))):
                    raise AgentError("Invalid controller response envelope")
            except BaseException:
                # Never replay a mutating command after an uncertain transport failure.
                self.close()
                raise
        if not response.get("ok"):
            raise AgentRejected(response["error"])
        return response["result"]

    def run(self, plan, poll=0.25, deadline=180):
        self.request("submit", **plan)
        until = time.monotonic() + deadline
        while time.monotonic() < until:
            status = self.request("status", id=plan["id"])
            if status["status"] != "running":
                return status
            time.sleep(poll)
        raise TimeoutError("Client wait expired; job may still be running; use status/cancel")

    def close(self):
        self.sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", help='JSON request, or @path/to/request.json')
    parser.add_argument("--port", type=int, default=27016)
    parser.add_argument("--password-file", type=Path)
    args = parser.parse_args()
    raw = Path(args.request[1:]).read_text() if args.request.startswith("@") else args.request
    req = json.loads(raw)
    with Agent(port=args.port, password_file=args.password_file) as agent:
        print(json.dumps(agent.request(**req), indent=2))
