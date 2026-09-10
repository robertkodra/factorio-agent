"""Offline, observed item-transfer geometry for one bounded production block.

Edges are geometric hypotheses, not proof of item acceptance or throughput.
Unknown belt lanes, missing neighbours and stale domains remain explicit.
This module has no game connection, plan submission or construction path.
"""
from copy import deepcopy
import math

from .state_mirror import ENTITY_FIELDS, InvalidState, StateMirror, TTL, digest

STORAGE = {'container', 'logistic-container'}
MACHINES = {'furnace', 'assembling-machine'}
BELTS = {'transport-belt', 'underground-belt'}
SUPPORTED = STORAGE | MACHINES | BELTS | {'mining-drill', 'inserter', 'electric-pole'}


def entity_key(eid):
    return 'entity:%d' % eid


def _point(value):
    return (isinstance(value, dict) and set(value) >= {'x', 'y'} and
            all(type(value[k]) in (int, float) and math.isfinite(value[k]) for k in ('x', 'y')))


def _contains(box, point):
    if not isinstance(box, dict) or not _point(point):
        return False
    a, b = box.get('left_top'), box.get('right_bottom')
    return (_point(a) and _point(b) and
            all(a[k] <= point[k] <= b[k] for k in ('x', 'y')))


def build_graph(mirror, entity_ids, now, *, historical=False):
    """Freeze mirror state, then derive a deterministic diagnostic projection.

    Normal mode requires fresh, valid structural observations. Historical mode
    explicitly accepts only legacy replay scope, preserves its lack of live
    authority, and still excludes stale samples, missing entities and tombstones.
    Every output is offline-only; it cannot authorize an executor action.
    """
    if (not 1 <= len(entity_ids) <= 64 or len(set(entity_ids)) != len(entity_ids)
            or any(type(eid) is not int or eid <= 0 for eid in entity_ids)):
        raise ValueError('Select 1 to 64 distinct observed entity IDs')
    if type(now) not in (int, float) or not math.isfinite(now):
        raise ValueError('A finite observation time is required')
    snapshot = mirror.checkpoint()
    frozen = StateMirror.restore(snapshot)
    nodes, edges, issues, rows = {}, [], [], {}

    def issue(code, eid, **evidence):
        issues.append(dict(code=code, entity=entity_key(eid), evidence=evidence))

    def read(eid, group):
        key = entity_key(eid) + ':' + group
        d = snapshot['domains'].get(key)
        if historical:
            if d is not None and d['scope'] != 'owned_factory_replay':
                raise InvalidState('Historical mode accepts only explicitly legacy replay domains')
            if (not d or not 0 <= now-d['at'] <= TTL[group]
                    or snapshot['tick']-d['tick'] > TTL[group]*60):
                return None
            return deepcopy(d['data'])
        try:
            return frozen.require([key], now)[key]
        except InvalidState:
            if group == 'structure':
                raise
            return None

    for eid in sorted(entity_ids):
        structure = read(eid, 'structure')
        if (not structure or structure.get('presence') != 'observed'
                or str(eid) in snapshot['tombstones']):
            issue('entity_unavailable', eid)
            continue
        facts = {'structure': structure}
        for group in ENTITY_FIELDS:
            if group != 'structure':
                value = read(eid, group)
                if value is None:
                    issue('domain_unavailable', eid, domain=group)
                else:
                    facts[group] = value
        kind = structure.get('type')
        key = entity_key(eid)
        nodes[key] = dict(key=key, kind=kind, facts=facts, samples={
            group: {k: snapshot['domains'][key+':'+group][k] for k in ('tick', 'at', 'scope', 'valid')}
            for group in facts})
        rows[eid] = structure
        if kind not in SUPPORTED:
            issue('unsupported_entity', eid, type=kind)
        if kind in BELTS:
            lines = facts.get('inventory', {}).get('lines')
            for lane in (1, 2):
                lane_key = key + ':lane:%d' % lane
                nodes[lane_key] = dict(key=lane_key, kind='transport-lane', entity=key,
                    lane=lane, contents=(deepcopy(lines[lane-1])
                    if isinstance(lines, list) and len(lines) == 2 else None))
            issue('belt_connectivity_unresolved', eid)
        if kind in MACHINES and not facts.get('production', {}).get('recipe'):
            issue('recipe_unobserved', eid)
        power = facts.get('power', {})
        if 'status_name' in power:
            issue('native_status_observed', eid, status=power['status_name'])
        contents = facts.get('inventory', {}).get('chest')
        if isinstance(contents, list) and len({v['name'] for v in contents if v['count'] > 0}) > 1:
            issue('mixed_buffer_contents', eid,
                  items=sorted({v['name'] for v in contents if v['count'] > 0}),
                  capacity='unknown')

    def connect(eid, field, pickup=False):
        point = rows[eid].get(field)
        if not _point(point):
            issue('port_unobserved', eid, port=field)
            return
        candidates = [other for other, row in rows.items() if other != eid and
                      _contains(row.get('box'), point)]
        if len(candidates) != 1:
            issue('endpoint_unresolved' if not candidates else 'endpoint_ambiguous', eid,
                  port=field, position=point, candidates=[entity_key(i) for i in candidates])
            return
        target = candidates[0]
        kind = rows[target].get('type')
        if kind in BELTS:
            issue('lane_mapping_unresolved', eid, port=field, target=entity_key(target))
            return
        if kind not in STORAGE | MACHINES:
            issue('unsupported_endpoint', eid, port=field, target=entity_key(target))
            return
        port = 'storage' if kind in STORAGE else ('output' if pickup else 'input_or_fuel')
        source, sink = (target, eid) if pickup else (eid, target)
        edges.append(dict(source=entity_key(source), target=entity_key(sink),
                          source_port=port if pickup else field,
                          target_port=field if pickup else port,
                          evidence='observed_port_intersects_bounding_box', position=point))

    for eid, row in rows.items():
        if row.get('type') == 'inserter':
            connect(eid, 'pickup', pickup=True)
            connect(eid, 'drop')
        elif row.get('type') == 'mining-drill':
            connect(eid, 'drop')
            target = nodes[entity_key(eid)]['facts'].get('production', {}).get('mining_target')
            if target:
                key = entity_key(eid)+':resource'
                nodes[key] = dict(key=key, kind='observed-mining-target', observation=target)
                edges.append(dict(source=key, target=entity_key(eid), source_port='resource',
                                  target_port='mining', evidence='observed_mining_target'))
            else:
                issue('mining_target_unobserved', eid)

    return dict(schema=1, offline_only=True, historical_only=historical,
                identity=deepcopy(snapshot['identity']), checkpoint_sha256=digest(snapshot),
                tick=snapshot['tick'], at=now, selected_ids=sorted(entity_ids),
                nodes=sorted(nodes.values(), key=lambda n:n['key']),
                edges=sorted(edges, key=lambda e:(e['source'],e['target'],e['source_port'])),
                issues=sorted(issues, key=lambda i:(i['entity'],i['code'],digest(i['evidence']))),
                limitations=['Geometry does not establish item acceptance, connectivity outside the sample, or flow.',
                             'Belt lane transfers, filters, inserter hands, fluid flow and capacity are unresolved.',
                             'A mixed buffer is not proof of a full buffer; native statuses are instantaneous.',
                             'Historical mode retains unverified charting and cannot supply live planning facts.'])


def upstream(graph, sink):
    """Structural candidate ancestry, never a material-flow or capacity proof."""
    known = {n['key'] for n in graph['nodes']}
    if sink not in known:
        raise ValueError('Sink is outside the observed graph')
    seen, pending = {sink}, [sink]
    while pending:
        target = pending.pop()
        for edge in graph['edges']:
            if edge['target'] == target and edge['source'] not in seen:
                seen.add(edge['source'])
                pending.append(edge['source'])
    return sorted(seen-{sink})


def analyze_journal(source, output, entity_ids, *, historical=False):
    """Reconstruct a private journal, retain a diagnostic graph, and never connect."""
    from collections import Counter
    import hashlib
    import json
    from pathlib import Path
    from .agent import ROOT
    from .mirror_log import Reconstructor

    source, output = Path(source), Path(output).resolve()
    if ROOT/'runtime' not in output.parents:
        raise ValueError('Graph output must remain under ignored runtime/')
    output.mkdir(parents=True, exist_ok=False)
    reader, source_hash = Reconstructor(), hashlib.sha256()
    try:
        with source.open('rb') as stream:
            for raw in stream:
                source_hash.update(raw)
                reader.apply(json.loads(raw))
        if reader.state is None:
            raise ValueError('Journal has no checkpoint')
        graph = build_graph(reader.mirror(), entity_ids, reader.state['at'], historical=historical)
        if graph != build_graph(reader.mirror(), list(reversed(entity_ids)), reader.state['at'], historical=historical):
            raise AssertionError('Graph depends on selection order')
        after = hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024), b''):
                after.update(chunk)
        if after.hexdigest() != source_hash.hexdigest():
            raise AssertionError('Source journal changed during analysis')
        report = dict(source_sha256=source_hash.hexdigest(), source_unchanged=True,
                      graph_sha256=digest(graph), selected_entities=len(entity_ids),
                      nodes=len(graph['nodes']), edges=len(graph['edges']),
                      geometric_edges=sum(e['evidence']=='observed_port_intersects_bounding_box'
                                          for e in graph['edges']),
                      issues=dict(sorted(Counter(i['code'] for i in graph['issues']).items())),
                      implementation_sha256={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                          for name in ('production_graph.py','state_mirror.py','mirror_log.py')},
                      deterministic_selection_order=True, historical_only=historical,
                      live_calls=0, throughput=None, limitations=graph['limitations'])
        (output/'graph.json').write_text(json.dumps(graph,indent=2)+'\n')
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps({'error':type(exc).__name__})+'\n')
        raise


def main():
    import argparse
    import json
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal', type=Path)
    parser.add_argument('--entity-ids', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--historical', action='store_true', help='Analyze legacy scope without live authority')
    args = parser.parse_args()
    report = analyze_journal(args.journal, args.output, json.loads(args.entity_ids.read_text()),
                             historical=args.historical)
    print(json.dumps({k:report[k] for k in ('selected_entities','nodes','edges','geometric_edges','issues','live_calls')},indent=2))


if __name__ == '__main__':
    main()
