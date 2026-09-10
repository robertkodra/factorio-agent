"""Versioned checkpoint + compact cache deltas, not a gameplay event framework."""
from copy import deepcopy
import json
from pathlib import Path
import threading

from .agent import ROOT
from .state_mirror import StateMirror, digest


def encoded(value):
    return (json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False)+'\n').encode()


def delta(before, after):
    changes = {}
    for key in set(before) | set(after):
        if key not in after:
            changes[key] = {'delete': True}
        elif key not in before:
            changes[key] = {'value': after[key]}
        elif before[key] != after[key]:
            changes[key] = ({'fields': delta(before[key], after[key])}
                            if isinstance(before[key], dict) and isinstance(after[key], dict)
                            else {'value': after[key]})
    return changes


def patched(before, changes):
    for key, change in changes.items():
        if change.get('delete'):
            del before[key]
        elif 'fields' in change:
            patched(before[key], change['fields'])
        else:
            before[key] = deepcopy(change['value'])
    return before


class MirrorLog:
    def __init__(self, path, checkpoint_seconds=30):
        path = Path(path).resolve()
        if ROOT / 'runtime' not in path.parents:
            raise ValueError('Mirror output must stay under ignored runtime/')
        if checkpoint_seconds <= 0:
            raise ValueError('Positive checkpoint interval required')
        path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = path.open('xb')
        self.last = None
        self.checkpoint_at = None
        self.interval = checkpoint_seconds
        self.serial = 0
        self.bytes = 0
        self.lock = threading.RLock()

    def append(self, mirror, events=()):
        with self.lock:
            return self._append(mirror, events)

    def _append(self, mirror, events):
        state = mirror.checkpoint()
        checkpoint = self.last is None or state['at']-self.checkpoint_at >= self.interval
        self.serial += 1
        record = dict(schema=1, serial=self.serial, kind='checkpoint' if checkpoint else 'delta',
                      state=state if checkpoint else delta(self.last, state), after=digest(state))
        if events:
            record['events'] = deepcopy(list(events))
        if checkpoint:
            self.checkpoint_at = state['at']
        else:
            record['before'] = digest(self.last)
        wire = encoded(record)
        self.stream.write(wire)
        if checkpoint:
            self.stream.flush()
        self.bytes += len(wire)
        self.last = state
        return record

    def close(self):
        with self.lock:
            self.stream.close()


class Reconstructor:
    def __init__(self):
        self.state = None
        self.serial = None

    def apply(self, record):
        if record['schema'] != 1:
            raise ValueError('Unknown mirror log schema')
        if self.serial is not None and record['serial'] != self.serial+1:
            raise ValueError('Mirror log record gap')
        if record['kind'] == 'checkpoint':
            self.state = deepcopy(record['state'])
        elif record['kind'] == 'delta' and self.state is not None:
            if digest(self.state) != record['before']:
                raise ValueError('Mirror delta baseline mismatch')
            patched(self.state, record['state'])
        else:
            raise ValueError('Reconstruction requires a checkpoint')
        if digest(self.state) != record['after']:
            raise ValueError('Mirror reconstruction hash mismatch')
        self.serial = record['serial']
        return self.state

    def mirror(self):
        return StateMirror.restore(self.state)
