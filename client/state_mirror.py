"""Small smelting-state cache with explicit provenance, freshness and event fences.

It does not plan or execute gameplay. Save identity is supplied by a private run
manifest, not inferred from a game tick. Missing entities are not invented kills.
"""
from copy import deepcopy
import hashlib
import json
import math
import threading

ENTITY_FIELDS = {
    'structure': ('id', 'name', 'type', 'position', 'direction', 'health', 'max_health',
                  'box', 'pickup', 'drop', 'belt_type', 'neighbour_id',
                  'belt_shape', 'transport_lines', 'inserter_ports'),
    'inventory': ('fuel', 'burner', 'input', 'output', 'chest', 'chest_slots', 'lines', 'fluids',
                  'inventory_slots', 'stack_sizes', 'contents_accessible_only'),
    'power': ('energy', 'electric_network_id', 'status', 'status_name'),
    'production': ('recipe', 'crafting', 'products_finished', 'mining_target',
                   'crafting_speed', 'productivity_bonus'),
}
PLAYER_FIELDS = ('position', 'health', 'max_health', 'crafting', 'paused', 'speed', 'guard')
INVENTORY_FIELDS = ('inventory', 'ammo', 'guns')
RESEARCH_FIELDS = ('researched', 'research', 'progress', 'enabled_recipes')
RECEIPT_FIELDS = ('id', 'status', 'index', 'total', 'action', 'started_tick', 'finished_tick', 'error')
TTL = {'player': .5, 'inventory': 1., 'structure': 5., 'power': .5,
       'production': 1., 'research': 5., 'job': 1.}
TERMINAL = {'complete', 'failed', 'cancelled'}


def select(data, fields):
    return {k: deepcopy(data[k]) for k in fields if k in data}


def player_values(observation):
    data = select(observation, PLAYER_FIELDS)
    guard = data.get('guard')
    if isinstance(guard, dict):
        guard.pop('tick', None)
        if isinstance(guard.get('observation'), dict):
            guard['observation'].pop('tick', None)
    return data


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


class InvalidState(RuntimeError):
    pass


class StateMirror:
    def __init__(self, identity):
        required = {'episode', 'save_sha256', 'controller', 'mod_sha256', 'base', 'actor', 'surface'}
        if set(identity) != required or not all(identity.values()):
            raise ValueError('Explicit save, episode, actor and controller provenance required')
        for name in ('save_sha256', 'mod_sha256'):
            value = identity[name]
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Invalid provenance hash')
        self.lock = threading.RLock()
        self.state = dict(schema=1, identity=deepcopy(identity), tick=0, at=0., cursor=None,
                          last_consumed_event_sequence=None, reconciled_fence=None, reconciliations=[],
                          head=None, event_at=None, event_valid=False, connected=False, domains={},
                          tombstones={}, recent_events={}, safety_revision=0, reason='not_reconciled')

    def checkpoint(self):
        with self.lock:
            return deepcopy(self.state)

    @classmethod
    def restore(cls, state):
        if state.get('schema') != 1:
            raise ValueError('Unsupported mirror checkpoint')
        mirror = cls(state['identity'])
        mirror.state = deepcopy(state)
        return mirror

    def _time(self, tick, at):
        if type(tick) is not int or tick < 0 or not isinstance(at, (int, float)) or not math.isfinite(at):
            raise ValueError('Invalid observation time')
        self.state['tick'] = max(self.state['tick'], tick)
        self.state['at'] = max(self.state['at'], at)

    def invalidate(self, reason, disconnected=False):
        with self.lock:
            self.state.update(event_valid=False, reason=reason)
            self.state['safety_revision'] += 1
            if disconnected:
                self.state['connected'] = False
            for key, domain in self.state['domains'].items():
                if not (key.startswith('job:') and domain['data'].get('status') in TERMINAL):
                    domain['valid'] = False

    def verify_identity(self, identity):
        if identity != self.state['identity']:
            self.invalidate('identity_changed', disconnected=True)
            raise InvalidState('World/save, actor or controller identity changed')

    def _sample(self, key, data, tick, at, scope, valid=True):
        self._time(tick, at)
        previous = self.state['domains'].get(key)
        if previous and (tick < previous['tick'] or at < previous['at']):
            return False
        revision = previous['revision'] if previous else 0
        if previous is None or previous['data'] != data or previous['valid'] != valid:
            revision += 1
        self.state['domains'][key] = dict(data=deepcopy(data), tick=tick, at=at,
            scope=scope, valid=valid, revision=revision)
        return True

    def player(self, observation, at):
        with self.lock:
            identity = dict(self.state['identity'], actor=observation['actor_unit'],
                            controller=observation['version'], base=observation['mods']['base'])
            if 'surface' in observation:
                identity['surface'] = observation['surface']
            self.verify_identity(identity)
            self._sample('player', player_values(observation), observation['tick'], at, 'bound_player')
            self._sample('inventory', select(observation, INVENTORY_FIELDS), observation['tick'], at, 'bound_player')
            if observation.get('job', {}).get('id') and observation['job']['id'] not in self.unknown_jobs():
                self.receipt(observation['job'], observation['tick'], at)

    def research(self, observation, at):
        with self.lock:
            # factory and research_state expose different subsets; absence in a
            # full subset is a deletion, while the other subset keeps its age.
            fields = ('enabled_recipes',) if 'enabled_recipes' in observation else ()
            if 'progress' in observation or 'enabled_recipes' not in observation:
                fields += ('research', 'progress')
            fields += ('researched',)
            for field in fields:
                self._sample('research:' + field, select(observation, (field,)),
                             observation['tick'], at, 'player_force')

    def entities(self, observation, at, requested):
        with self.lock:
            if observation.get('scope') not in ('owned_charted_requested_entities', 'owned_factory_replay'):
                raise InvalidState('Explicit owned/charted observation scope required')
            if observation['scope'] == 'owned_charted_requested_entities' and any(
                    field not in observation for field in ('actor_unit', 'version', 'surface')):
                raise InvalidState('Live entity observation identity is incomplete')
            for field, key in (('actor_unit', 'actor'), ('version', 'controller'), ('surface', 'surface')):
                if field in observation and observation[field] != self.state['identity'][key]:
                    self.invalidate('entity_observation_identity_changed')
                    raise InvalidState('Entity observation identity changed')
            requested = set(requested)
            if not requested or len(requested) > 64:
                raise ValueError('A block must select 1 to 64 observed entities')
            rows = {e['id']: e for e in observation['entities']}
            missing = set(observation.get('missing', []))
            if len(rows) != len(observation['entities']) or set(rows) & missing or set(rows) | missing != requested:
                raise InvalidState('Incomplete or out-of-scope entity response')
            for eid in sorted(requested):
                # Unit numbers are not reused for normally rebuilt buildings.
                dead = str(eid) in self.state['tombstones']
                for group, fields in ENTITY_FIELDS.items():
                    data = select(rows[eid], fields) if eid in rows else {}
                    if group == 'structure':
                        data['presence'] = 'destroyed' if dead else ('observed' if eid in rows else 'missing')
                    self._sample('entity:%d:%s' % (eid, group), data,
                                 observation['tick'], at, observation['scope'],
                                 observation['scope'] != 'owned_factory_replay' and
                                 (group == 'structure' or (eid in rows and not dead)))

    def submitted(self, job_id, tick, at):
        """Record BEFORE a submit attempt; lost replies must never cause a replay."""
        with self.lock:
            key = 'job:' + job_id
            if key in self.state['domains']:
                raise InvalidState('Job ID already recorded')
            self._sample(key, dict(id=job_id, status='unknown'), tick, at, 'job_id')

    def receipt(self, receipt, tick, at):
        with self.lock:
            data = select(receipt, RECEIPT_FIELDS)
            if not data.get('id') or data.get('status') not in TERMINAL | {'running', 'unknown'}:
                raise InvalidState('Invalid job receipt')
            key = 'job:' + data['id']
            previous = self.state['domains'].get(key)
            if previous and previous['data'].get('status') in TERMINAL and previous['data'] != data:
                self.invalidate('conflicting_terminal_receipt')
                raise InvalidState('Conflicting terminal job receipt')
            self._sample(key, data, tick, at, 'job_id')

    def status(self, status, at):
        """Consume a contiguous page. Head sequence is never the consumed cursor."""
        with self.lock:
            cursor = self.state['cursor']
            self._time(status['tick'], at)
            self.state['head'] = status['sequence']
            self.state['event_at'] = at
            if cursor is None:
                return []  # explicit snapshot reconciliation must establish a fence
            if status['sequence'] < cursor or status.get('events_lost'):
                self.invalidate('event_sequence_gap')
                return []
            events = status.get('events') or []
            fresh, expected, page_seen = [], cursor + 1, {}
            for event in events:
                seq = event['seq']
                if seq > status['sequence']:
                    self.invalidate('event_above_head'); return []
                if seq < expected:
                    known = page_seen.get(seq) or self.state['recent_events'].get(str(seq))
                    if known and known != digest(event):
                        self.invalidate('conflicting_duplicate_event'); return []
                    continue
                if seq != expected:
                    self.invalidate('event_sequence_gap'); return []
                fresh.append(event); page_seen[seq] = digest(event); expected += 1
            if not fresh and cursor < status['sequence']:
                self.invalidate('event_sequence_gap'); return []
            for event in fresh:
                self._event(event, at)
                self.state['cursor'] = event['seq']
                self.state['last_consumed_event_sequence'] = event['seq']
                self.state['recent_events'][str(event['seq'])] = digest(event)
            recent = self.state['recent_events']
            for seq in sorted(recent, key=int)[:-2048]:
                del recent[seq]
            return deepcopy(fresh)

    def _event(self, event, at):
        kind, detail = event['kind'], event.get('detail') or {}
        if kind in ('factory_damaged', 'factory_destroyed'):
            eid = detail['id']; key = 'entity:%d:structure' % eid
            self.state['safety_revision'] += 1
            domain = self.state['domains'].get(key)
            if kind == 'factory_destroyed':
                self.state['tombstones'][str(eid)] = event['tick']
            if domain and event['tick'] >= domain['tick']:
                domain['data'].update(select(detail, ('health',)))
                domain['revision'] += 1
            for group in ENTITY_FIELDS:
                d = self.state['domains'].get('entity:%d:%s' % (eid, group))
                if d:
                    # Damage is not a fresh inventory/power/production sample.
                    d['valid'] = False
        elif kind in ('engineer_died', 'released', 'bound'):
            self.invalidate('actor_event_requires_reconciliation')
        elif kind in ('engineer_damaged', 'pause', 'guard_configured'):
            self.state['safety_revision'] += 1
            for key in ('player', 'inventory'):
                if key in self.state['domains']:
                    self.state['domains'][key]['valid'] = False
        elif kind in ('complete', 'failed', 'cancelled', 'submitted') and event.get('job'):
            # Native events do not contain a full receipt: resolve by ID.
            key = 'job:' + event['job']
            d = self.state['domains'].get(key)
            if not d or d['data']['status'] not in TERMINAL:
                self._sample(key, dict(id=event['job'], status='unknown'), event['tick'], at, 'native_job_event')
        elif kind == 'research_finished':
            for key, d in self.state['domains'].items():
                if key.startswith('research:'):
                    d['valid'] = False

    def reconcile(self, identity, fence, tick, at, required, safety_revision=None):
        """Only a full selected-domain read AT/AFTER a pre-read fence may heal a gap.

        The caller must obtain the fence before these reads. Events after the
        fence are drained normally, including events occurring during the reads.
        """
        with self.lock:
            self.verify_identity(identity)
            if not required or (safety_revision is not None and safety_revision != self.state['safety_revision']):
                raise InvalidState('Reconciliation raced a safety change or omitted required domains')
            for key in required:
                d = self.state['domains'].get(key)
                if not d or not d['valid'] or d['tick'] < tick or d['at'] < at:
                    raise InvalidState('Reconciliation needs fresh selected-domain observations')
            # A snapshot fence covers state, not proof that lost events were
            # consumed. Preserve the last actual event and the recovery reason.
            self.state['reconciliations'].append(dict(from_cursor=self.state['cursor'],
                through=fence, tick=tick, at=at, reason=self.state['reason']))
            self.state['reconciliations'] = self.state['reconciliations'][-32:]
            self.state.update(cursor=fence, head=fence, event_valid=True, connected=True,
                              event_at=at, reason=None, recent_events={}, reconciled_fence=fence)
            self.state['safety_revision'] += 1

    def unknown_jobs(self):
        with self.lock:
            return [d['data']['id'] for key, d in self.state['domains'].items()
                    if key.startswith('job:') and (not d['valid'] or d['data']['status'] == 'unknown')]

    def require(self, keys, now):
        with self.lock:
            s = self.state
            if not s['connected'] or not s['event_valid'] or s['cursor'] != s['head']:
                raise InvalidState('Disconnected, invalid or undrained event state')
            if s['event_at'] is None or now < s['event_at'] or now - s['event_at'] > .5:
                raise InvalidState('Event observation is stale')
            if self.unknown_jobs():
                raise InvalidState('Unknown job outcomes require ID reconciliation')
            result = {}
            for key in keys:
                d = s['domains'].get(key)
                group = key.rsplit(':', 1)[-1] if key.startswith('entity:') else key.split(':')[0]
                ttl = TTL[group]
                if not d or not d['valid'] or now < d['at'] or now-d['at'] > ttl or s['tick']-d['tick'] > ttl*60:
                    raise InvalidState('Stale or invalid domain: ' + key)
                result[key] = deepcopy(d['data'])
            return result

    def plan_token(self, keys, now):
        with self.lock:
            self.require(keys, now)
            return dict(identity=digest(self.state['identity']), safety=self.state['safety_revision'],
                        revisions={key:self.state['domains'][key]['revision'] for key in keys})

    def validate_plan(self, token, now):
        with self.lock:
            if token != self.plan_token(list(token['revisions']), now):
                raise InvalidState('Plan facts changed; replan before submitting')
            return True
