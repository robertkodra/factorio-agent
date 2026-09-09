"""The deprecated diagnostic entrypoint must never open a network connection."""
import unittest
from unittest.mock import patch

from client.play import query
from client.play import call


class PolicyTests(unittest.TestCase):
    def test_arbitrary_lua_is_rejected_before_transport(self):
        with patch('client.play.Agent') as transport:
            with self.assertRaisesRegex(RuntimeError, 'disabled'):
                query('return 1')
            transport.assert_not_called()

    def test_closed_run_blocks_actions_before_transport(self):
        with patch('client.play.RUN') as run, patch('client.play.Agent') as transport:
            run.__truediv__.return_value.exists.return_value = True
            with self.assertRaisesRegex(RuntimeError, 'closed'):
                call('submit', id='must-not-send', actions=[])
            transport.assert_not_called()


if __name__ == '__main__':
    unittest.main()
