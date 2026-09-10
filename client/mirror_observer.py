"""Read-only block observer and a separately scheduled emergency event pump.

No production submit path or live CLI is provided in this review slice. Native
reflex/preemption stays inside Factorio; this client records and surfaces events.
"""
from copy import deepcopy
import queue
import threading
import time

from .agent import AgentRejected
from .state_mirror import InvalidState, StateMirror


def domains_for(targets):
    return ['player', 'inventory', 'research:researched', 'research:enabled_recipes',
            'research:research', 'research:progress'] + [
        'entity:%d:structure' % t['id'] for t in targets]


class BlockObserver:
    def __init__(self, mirror, game, targets, clock=time.time, journal=None):
        if not 1 <= len(targets) <= 64 or len({t['id'] for t in targets}) != len(targets):
            raise ValueError('A block needs 1 to 64 distinct already observed targets')
        self.mirror, self.game, self.targets, self.clock = mirror, game, deepcopy(targets), clock
        self.costs = []
        self.journal = journal

    def _record(self, events=()):
        if self.journal is not None:
            self.journal.append(self.mirror, events=events)

    def _read(self, op, **kwargs):
        start = time.perf_counter()
        try:
            return self.game.request(op, **kwargs)
        except AgentRejected:
            if not (op == 'status' and 'id' in kwargs):
                self.mirror.invalidate('observation_rejected', disconnected=True)
                self._record()
            raise
        except (ConnectionError, TimeoutError, OSError):
            self.mirror.invalidate('disconnected', disconnected=True)
            self._record()
            raise
        finally:
            self.costs.append(dict(operation=op, seconds=time.perf_counter()-start))

    def refresh(self, identity):
        """Read a selected block; healing a gap needs an explicit provenance check."""
        self.mirror.verify_identity(identity)
        hello = self._read('hello')
        if hello.get('version') != identity['controller'] or hello.get('observation_contract') != 'smelting-block-v1':
            self.mirror.invalidate('unsupported_controller', disconnected=True)
            raise InvalidState('Controller lacks the reviewed block observation contract')
        fence = self._read('status')
        if fence['tick'] < self.mirror.checkpoint()['tick']:
            self.mirror.invalidate('world_tick_regressed', disconnected=True)
            raise InvalidState('Tick regressed; start a new explicit episode')
        started = self.clock()
        safety = self.mirror.checkpoint()['safety_revision']
        player = self._read('observe')
        entities = self._read('observe_entities', targets=self.targets)
        research = self._read('research_state')
        self.mirror.player(player, self.clock())
        self.mirror.entities(entities, self.clock(), [t['id'] for t in self.targets])
        self.mirror.research(research, self.clock())
        if not self.mirror.checkpoint()['event_valid'] or not self.mirror.checkpoint()['connected']:
            self.mirror.reconcile(identity, fence['sequence'], fence['tick'], started,
                                  domains_for(self.targets), safety_revision=safety)
        # Only consume actual events following the pre-read fence. A sequence
        # carried by observe_entities does not acknowledge the intervening pages.
        self.poll_events()
        self.reconcile_jobs()

    def poll_events(self):
        state = self.mirror.checkpoint()
        request = {} if state['cursor'] is None else dict(after=state['cursor'])
        status = self._read('status', **request)
        if status['tick'] < state['tick']:
            self.mirror.invalidate('world_tick_regressed', disconnected=True)
            raise InvalidState('Tick regressed; start a new explicit episode')
        events = self.mirror.status(status, self.clock())
        self._record(events)
        return events

    def reconcile_jobs(self):
        for job_id in self.mirror.unknown_jobs():
            try:
                result = self._read('status', id=job_id)
            except AgentRejected as exc:
                if 'unknown_job_id' not in str(exc):
                    raise
                # Absence is not authority to resubmit. Keep unknown and block.
                continue
            if result.get('id') != job_id:
                self.mirror.invalidate('job_id_mismatch')
                raise InvalidState('Receipt returned for another job')
            self.mirror.receipt(result, result['tick'], self.clock())
            self._record()


class EmergencyPump:
    """Owns a separate read connection; never calls a strategic planner/model.

    Consumers receive events through an unbounded in-process queue. It does not
    issue defensive inputs: native damage preemption and the native reflex do so.
    """
    def __init__(self, observer, interval=.1):
        if interval <= 0:
            raise ValueError('Positive poll interval required')
        self.observer, self.interval = observer, interval
        self.events = queue.SimpleQueue()
        self.errors = queue.SimpleQueue()
        self.stopped = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError('Pump already started')
        def run():
            while not self.stopped.is_set():
                try:
                    events = self.observer.poll_events()
                    for event in events:
                        if event['kind'] in ('factory_damaged', 'factory_destroyed', 'engineer_damaged', 'engineer_died'):
                            self.events.put(event)
                except Exception as exc:
                    self.observer.mirror.invalidate('emergency_observer_disconnected', disconnected=True)
                    self.errors.put(type(exc).__name__)
                    break  # reconnect explicitly with revalidated provenance
                self.stopped.wait(self.interval)
        self.thread = threading.Thread(target=run, name='factorio-events', daemon=True)
        self.thread.start()

    def close(self, timeout=1):
        self.stopped.set()
        if self.thread:
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise TimeoutError('Event read still in flight; native guard remains separate')
