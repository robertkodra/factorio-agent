import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from client.local_planner import LocalPlanner, load_config, choice_ids
from client.supervisor import EventCursor, Supervisor
from client.benchmark_planner import constructed_cases, recorded_cases, percentile


CANDIDATES = [{'id': 'defense', 'description': 'Defend the engineer'}]


class PlannerTests(unittest.TestCase):
    def test_local_only_config(self):
        config = load_config()
        for url in ('https://example.com', 'http://127.0.0.1' + '@evil.example',
                    'http://localhost:11434/api', 'http://127.0.0.1?redirect=1'):
            with tempfile.TemporaryDirectory() as directory:
                p = Path(directory) / 'config.json'
                p.write_text(json.dumps(dict(config, base_url=url)))
                with self.assertRaises(ValueError):
                    load_config(p)

    def test_bounded_selection_and_request(self):
        planner = LocalPlanner()
        result = {'done': True, 'done_reason': 'stop', 'message': {'content': '{"choice":"defense"}'}}
        with patch.object(planner, '_request', return_value=result) as request:
            self.assertEqual(planner.decide({'health': 33}, CANDIDATES)['choice'], 'defense')
            payload = request.call_args.args[1]
            self.assertIs(payload['think'], False)
            self.assertFalse(payload['stream'])
            self.assertEqual(payload['format']['properties']['choice']['enum'], ['defense'])
            self.assertNotIn('tools', payload)
        for message in ({'content': '{"choice":"teleport"}'},
                        {'content': '{"choice":"defense","code":"x"}'},
                        {'content': '{"choice":"defense"}', 'thinking': 'reasoning'},
                        {'content': '{"choice":"defense"}', 'tool_calls': [{}]}):
            with patch.object(planner, '_request', return_value=dict(result, message=message)):
                with self.assertRaises((ValueError, RuntimeError)):
                    planner.decide({'health': 33}, CANDIDATES)
        with patch.object(planner, '_request', return_value=dict(result, done_reason='length')):
            with self.assertRaisesRegex(RuntimeError, 'Incomplete'):
                planner.decide({}, CANDIDATES)

    def test_candidates_fail_before_network(self):
        planner = LocalPlanner()
        with patch.object(planner, '_request') as request:
            for candidates in ([], CANDIDATES * 2, [{'id': 'x', 'description': 'y', 'code': 'z'}]):
                with self.assertRaises(ValueError):
                    planner.decide({}, candidates)
            request.assert_not_called()

    def test_model_must_be_downloaded(self):
        planner = LocalPlanner()
        with patch.object(planner, '_request', return_value={'models': []}):
            with self.assertRaisesRegex(RuntimeError, 'not present'):
                planner.identity()

    def test_event_pages_and_gaps(self):
        cursor = EventCursor()
        cursor.consume({'sequence': 10})
        events = [{'seq': 11}, {'seq': 12}]
        self.assertEqual(cursor.consume({'sequence': 20, 'events': events}), events)
        self.assertEqual(cursor.value, 12, 'Advance by consumed event, not newest sequence')
        with self.assertRaisesRegex(RuntimeError, 'gap'):
            cursor.consume({'sequence': 20, 'events': [{'seq': 14}]})
        with self.assertRaisesRegex(RuntimeError, 'backwards'):
            cursor.consume({'sequence': 1})
        with self.assertRaisesRegex(RuntimeError, 'gap'):
            cursor.consume({'sequence': 20, 'events_lost': True})

    def test_fifty_case_provenance_requires_real_snapshots(self):
        cases = constructed_cases()
        self.assertEqual(len(cases), 40)
        self.assertTrue(all(c['provenance'] == 'constructed' for c in cases))
        for c in cases:
            self.assertIn(c['expected'], choice_ids(c['candidates']))
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'trace.jsonl'
            p.write_text(json.dumps({'kind': 'state', 'data': {'tick': 1, 'health': 33, 'max_health': 250}}))
            extracted = recorded_cases(p)
            self.assertEqual(len(extracted), 1)
            self.assertEqual(extracted[0]['expected'], 'defense')
            self.assertEqual(extracted[0]['provenance'], 'recorded-snapshot')
        self.assertEqual(percentile([4, 1, 2, 3], .95), 4)


class FakeGame:
    def __init__(self):
        self.calls = []
        self.observation = {'tick': 1, 'sequence': 0, 'health': 250, 'max_health': 250,
                            'actor_unit': 12, 'paused': False, 'speed': 1, 'guard': {}}

    def request(self, op, **kwargs):
        self.calls.append((op, kwargs))
        if op == 'status':
            return {'sequence': 0, 'events': []}
        assert op == 'observe', 'Shadow supervisor must never mutate the game'
        return dict(self.observation)


class SupervisorTests(unittest.TestCase):
    def test_live_guard_clock_accepts_advice_but_changed_threat_rejects_it(self):
        from concurrent.futures import Future
        from client.supervisor import context_key, planning_context
        game, records, clock = FakeGame(), [], [0]
        game.observation['guard'] = {'enabled': True, 'active': False,
            'observation': {'tick': 3, 'entities': [], 'total': 0}}
        supervisor = Supervisor(game, None, lambda k, v: records.append((k, v)),
                                clock=lambda: clock[0])
        supervisor.last_requested = float('inf')
        key = context_key(game.observation)
        context = planning_context(game.observation)
        self.assertNotIn('tick', context)
        self.assertNotIn('tick', context['guard']['observation'])
        original_tick = game.observation['guard']['observation']['tick']
        self.assertEqual(original_tick, 3)
        future = Future(); future.set_result({'choice': 'verify_work'})
        supervisor.pending = (future, 0, key, 12)
        clock[0] = .7
        game.observation['tick'] = 45
        game.observation['guard']['observation']['tick'] = 45
        supervisor.poll()
        self.assertIn('advice_available', [k for k, v in records])
        supervisor.pending = (future, .7, key, 12)
        game.observation['guard']['observation'].update(total=1, entities=[{'id': 7}])
        supervisor.poll()
        self.assertIn('advice_discarded', [k for k, v in records])

    def test_delayed_model_does_not_block_sixty_seconds_of_observation(self):
        entered, release = threading.Event(), threading.Event()
        class SlowPlanner:
            def decide(self, observation, candidates):
                entered.set()
                release.wait(5)
                return {'choice': candidates[0]['id']}
        game, records, clock = FakeGame(), [], [0]
        supervisor = Supervisor(game, SlowPlanner(), lambda k, v: records.append((k, v)), clock=lambda: clock[0])
        try:
            supervisor.poll()
            self.assertTrue(entered.wait(1))
            future = supervisor.pending[0]
            for i in range(1, 601):
                clock[0] = i / 10
                game.observation['tick'] = i * 6
                if i == 100:
                    game.observation['health'] = 33
                supervisor.poll()
            self.assertEqual(sum(k == 'observation' for k, v in records), 601)
            self.assertEqual(sum(k == 'advice_requested' for k, v in records), 1)
            self.assertEqual(sum(k == 'damage_alert' for k, v in records), 1)
            self.assertFalse(future.done())
            release.set(); future.result(timeout=1)
            supervisor.last_requested = clock[0]  # Do not schedule another request in this assertion.
            supervisor.poll()
            self.assertIn('advice_discarded', [k for k, v in records])
            self.assertNotIn('advice_available', [k for k, v in records])
        finally:
            release.set()

    def test_changed_character_and_pause_end_episode(self):
        game = FakeGame()
        supervisor = Supervisor(game, None, lambda *args: None)
        supervisor.last_requested = float('inf')
        supervisor.poll()
        game.observation['actor_unit'] = 13
        with self.assertRaisesRegex(RuntimeError, 'Character changed'):
            supervisor.poll()
        game.observation['paused'] = True
        with self.assertRaisesRegex(RuntimeError, 'unpaused'):
            supervisor.poll()


if __name__ == '__main__':
    unittest.main()
