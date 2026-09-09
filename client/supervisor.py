"""Persistent observation and asynchronous local advice; no generated game commands.

Shadow mode is the only mode in this first release. The game-local reflex owns
urgent inputs; advice is recorded for review, never executed as a free-form plan.
"""
from __future__ import annotations

import argparse
from concurrent.futures import Future
import hashlib
import json
from pathlib import Path
import threading
import time

from .agent import Agent, ROOT
from .local_planner import LocalPlanner, load_config


class Recorder:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        if ROOT / 'runtime' not in self.directory.parents:
            raise ValueError('Supervisor records must stay inside runtime/')
        self.directory.mkdir(parents=True, exist_ok=False)
        self.file = (self.directory / 'events.jsonl').open('x')

    def write(self, kind, data):
        self.file.write(json.dumps(dict(kind=kind, monotonic=time.monotonic(),
                                        wall_epoch=time.time(), data=data), allow_nan=False) + '\n')
        self.file.flush()

    def close(self):
        self.file.close()


class EventCursor:
    def __init__(self):
        self.value = None

    def consume(self, status):
        if self.value is None:
            self.value = status['sequence']
            return []
        if status['sequence'] < self.value:
            raise RuntimeError('Event sequence moved backwards: world changed')
        if status.get('events_lost'):
            raise RuntimeError('Event history gap: reconnect from an explicit new baseline')
        for e in status.get('events', []):
            if e['seq'] != self.value + 1:
                raise RuntimeError('Event history gap')
            self.value = e['seq']
        if self.value < status['sequence'] and not status.get('events'):
            raise RuntimeError('Event history unavailable')
        return status.get('events', [])


def compact(observation):
    return {k: observation.get(k) for k in ('tick', 'actor_unit', 'health', 'max_health',
        'position', 'inventory', 'ammo', 'guns', 'job', 'guard', 'paused', 'speed')}


def context_key(observation):
    # Ignore time alone. Any meaningful change invalidates the queued advice.
    data = compact(observation)
    data.pop('tick', None)
    if isinstance(data.get('guard'), dict):
        data['guard'] = {k: v for k, v in data['guard'].items() if k != 'tick'}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def candidates_for(observation):
    if observation.get('guard', {}).get('active') or observation['health'] < .5 * observation['max_health']:
        return [{'id': 'defense', 'description': 'Let the local reflex handle danger; defer production planning'}]
    return [{'id': 'inspect_supply', 'description': 'Inspect actual fuel, input and power conditions before expansion'},
            {'id': 'inspect_route', 'description': 'Inspect permitted route and threat observations before travel'},
            {'id': 'verify_work', 'description': 'Verify actual outcomes of completed construction and research'}]


class Supervisor:
    def __init__(self, game, planner, emit, clock=time.monotonic, max_age=3, advice_interval=2):
        self.game, self.planner, self.emit, self.clock = game, planner, emit, clock
        self.max_age, self.advice_interval = max_age, advice_interval
        self.cursor = EventCursor()
        self.pending = None
        self.last_requested = -float('inf')
        self.previous = None

    def _start_advice(self, observation):
        future = Future()
        choices = candidates_for(observation)
        self.pending = (future, self.clock(), context_key(observation), observation['actor_unit'])
        self.last_requested = self.clock()
        self.emit('advice_requested', dict(observation=compact(observation), candidates=choices))
        def work():
            try:
                future.set_result(self.planner.decide(compact(observation), choices))
            except BaseException as exc:
                future.set_exception(exc)
        threading.Thread(target=work, daemon=True, name='local-planner').start()

    def poll(self):
        request = {} if self.cursor.value is None else {'after': self.cursor.value}
        status = self.game.request('status', **request)
        for event in self.cursor.consume(status):
            self.emit('game_event', event)
        observation = self.game.request('observe')
        self.emit('observation', observation)
        if observation.get('paused') or observation.get('speed') != 1:
            raise RuntimeError('Supervisor requires an already-running normal-speed unpaused game')
        if self.previous and self.previous['actor_unit'] != observation['actor_unit']:
            raise RuntimeError('Character changed; start a new observation episode')
        if self.previous and observation['health'] < self.previous['health']:
            self.emit('damage_alert', {'tick': observation['tick'], 'health': observation['health']})
        self.previous = observation
        if self.pending:
            future, started, key, actor = self.pending
            if future.done():
                try:
                    result = future.result()
                    stale = (self.clock() - started > self.max_age or
                             actor != observation['actor_unit'] or key != context_key(observation))
                    self.emit('advice_discarded' if stale else 'advice_available', result)
                except Exception as exc:
                    self.emit('advice_error', {'type': type(exc).__name__})
                self.pending = None
        # At most one inference is in flight. A slow model never blocks polling.
        if self.pending is None and self.clock() - self.last_requested >= self.advice_interval:
            self._start_advice(observation)
        return observation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shadow', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=60)
    args = parser.parse_args()
    if not 0 < args.seconds <= 3600:
        raise ValueError('Shadow capture must be 1-3600 seconds')
    recorder = Recorder(args.output)
    config = load_config()
    planner = LocalPlanner(config)
    try:
        recorder.write('manifest', {'model': planner.identity(), 'config': config, 'mode': 'shadow'})
        with Agent() as game:
            supervisor = Supervisor(game, planner, recorder.write,
                                    max_age=config['max_decision_age_seconds'])
            until = time.monotonic() + args.seconds
            while time.monotonic() < until:
                began = time.monotonic()
                supervisor.poll()
                time.sleep(max(0, .1 - (time.monotonic() - began)))
    finally:
        recorder.write('capture_stopped', {'game_paused_or_modified': False})
        recorder.close()
        # Do not close a connection from another thread during inference. Worker
        # is daemonized, HTTP has a finite timeout, and process exit closes it.


if __name__ == '__main__':
    main()
