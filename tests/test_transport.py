"""Protocol edge cases that are difficult to induce in a live game."""
import json
import socket
import struct
import tempfile
import threading
import unittest
from pathlib import Path

from client.agent import Agent, AgentError


def read_packet(sock):
    def exact(n):
        out = b""
        while len(out) < n:
            data = sock.recv(n - len(out))
            if not data:
                raise EOFError()
            out += data
        return out
    size, = struct.unpack("<i", exact(4))
    data = exact(size)
    rid, kind = struct.unpack("<ii", data[:8])
    return rid, kind, data[8:-2]


class TransportTests(unittest.TestCase):
    def exercise(self, handler, assertion):
        with socket.socket() as listener, tempfile.TemporaryDirectory() as directory:
            listener.bind(("127.0.0.1", 0)); listener.listen(1)
            password = Path(directory) / "password"
            password.write_text("test-only")
            errors = []
            def serve():
                try:
                    with listener.accept()[0] as peer:
                        peer.settimeout(2)
                        handler(peer)
                except BaseException as error:
                    errors.append(error)
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                assertion(dict(port=listener.getsockname()[1], password_file=password, timeout=2))
            finally:
                thread.join(3)
            self.assertFalse(thread.is_alive())
            if errors:
                raise errors[0]

    def test_fragmented_packet_and_two_packet_auth(self):
        def serve(peer):
            rid, kind, _ = read_packet(peer)
            self.assertEqual(kind, 3)
            peer.sendall(Agent._packet(rid, 0, "") + Agent._packet(rid, 2, ""))
            rid, _, body = read_packet(peer)
            self.assertTrue(body.startswith(b'/codex-agent '))
            self.assertIn(b'"op":"observe"', body)
            wire = Agent._packet(rid, 0, json.dumps(dict(ok=True, result=dict(tick=123))))
            for byte in wire:
                peer.sendall(bytes([byte]))
        def check(kwargs):
            with Agent(**kwargs) as agent:
                self.assertEqual(agent.request("observe"), dict(tick=123))
        self.exercise(serve, check)

    def test_authentication_rejection(self):
        def serve(peer):
            read_packet(peer)
            peer.sendall(Agent._packet(-1, 2, ""))
        def check(kwargs):
            with self.assertRaisesRegex(AgentError, "authentication failed"):
                Agent(**kwargs)
        self.exercise(serve, check)

    def test_connection_loss_does_not_replay_mutation(self):
        received = []
        def serve(peer):
            rid, _, _ = read_packet(peer)
            peer.sendall(Agent._packet(rid, 2, ""))
            received.append(read_packet(peer)[2])
        def check(kwargs):
            with Agent(**kwargs) as agent:
                with self.assertRaises(ConnectionError):
                    agent.request("submit", id="exactly-once", actions=[dict(type="wait_ticks", ticks=1)])
        self.exercise(serve, check)
        self.assertEqual(len(received), 1)

    def test_wrong_response_id_closes_connection(self):
        def serve(peer):
            rid, _, _ = read_packet(peer)
            peer.sendall(Agent._packet(rid, 2, ""))
            rid, _, _ = read_packet(peer)
            peer.sendall(Agent._packet(rid + 1, 0, '{"ok":true,"result":{}}'))
        def check(kwargs):
            with Agent(**kwargs) as agent:
                with self.assertRaisesRegex(AgentError, "response type or ID"):
                    agent.request("observe")
        self.exercise(serve, check)


if __name__ == "__main__":
    unittest.main()
