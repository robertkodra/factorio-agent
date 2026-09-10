"""Offline material-flow evidence; never a factory plan or a live authority.

Native lane links are optional normalized observations, not inferred from lane
contents. Old journals do not contain them. Absence therefore means unknown.
Capacity bounds apply to a specified single-material route, not a whole factory.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

from .production_graph import BELTS, MACHINES, STORAGE, _contains
from .state_mirror import InvalidState, digest

CATALOG = json.loads((Path(__file__).resolve().parents[1] / 'data/catalog-2.0.77.json').read_text())
DIRECTIONS = {0: (0, -1), 4: (1, 0), 8: (0, 1), 12: (-1, 0)}
BELT_UPPER = {'transport-belt': 7.5, 'underground-belt': 7.5,
              'fast-transport-belt': 15., 'fast-underground-belt': 15.,
              'express-transport-belt': 22.5, 'express-underground-belt': 22.5}
CHEMICAL_FUELS = {'wood', 'coal', 'solid-fuel', 'rocket-fuel', 'nuclear-fuel'}
SCIENCE = {'automation-science-pack', 'logistic-science-pack'}


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def lane(key, index):
    if type(index) is not int or not 1 <= index <= 4:
        raise ValueError('Expected a surface or underground transport-line index')
    return key + ':lane:' + str(index)


def item_counts(values):
    if not isinstance(values, list):
        return None
    result = {}
    for row in values:
        if (not isinstance(row, dict) or not isinstance(row.get('name'), str)
                or not number(row.get('count')) or row.get('quality', 'normal') != 'normal'):
            return None
        result[row['name']] = result.get(row['name'], 0) + row['count']
    return result


def classify_rate(requested, lower, upper, *, limiting=None, needed=()):
    """Classify an already established interval; never repair inconsistent bounds."""
    if (not number(requested) or not number(lower) or
            (upper is not None and (not number(upper) or upper < lower))):
        raise ValueError('Invalid rate or capacity interval')
    status = ('feasible' if requested <= lower else
              'infeasible' if upper is not None and requested > upper else 'unknown')
    if status == 'infeasible' and not limiting:
        raise ValueError('Infeasibility needs an identified limiting node or edge')
    return dict(status=status, requested_per_second=requested,
                capacity=dict(lower_per_second=lower, upper_per_second=upper),
                limiting=limiting, observations_needed=sorted(set(needed)) if status == 'unknown' else [])


def acceptance(node, item, port, base):
    """Recipe acceptance is distinct from available inventory room and fuel."""
    facts = node['facts']; structure = facts['structure']; kind = structure['type']
    if base != CATALOG['factorio_version']:
        return None
    if kind in STORAGE or kind in BELTS:
        return True  # Storage filters/room are a separate constraint.
    if port == 'fuel':
        if structure['name'] in ('stone-furnace', 'steel-furnace', 'boiler', 'burner-inserter'):
            return item in CHEMICAL_FUELS
        if structure['name'] == 'electric-furnace':
            return False
        return None
    recipe = CATALOG['recipes'].get(facts.get('production', {}).get('recipe'))
    if recipe is None:
        return None
    if port == 'input':
        return item in {r['name'] for r in recipe['ingredients'] if r['type'] == 'item'}
    if port == 'output':
        return item in {r['name'] for r in recipe['products'] if r['type'] == 'item'}
    return None


def buffer_room(node, item):
    """Room bounds from accessible slots; aggregate mixtures alone prove no jam."""
    inventory = node['facts'].get('inventory', {})
    sizes = inventory.get('stack_sizes', {})
    size = sizes.get(item) if isinstance(sizes, dict) else None
    if type(size) is not int or size <= 0:
        return dict(lower=0, upper=None, needed=['item_stack_sizes'])
    slots = inventory.get('inventory_slots')
    if isinstance(slots, list):
        # Complete list of accessible slots, after the chest bar; filters explicit.
        room = 0
        for slot in slots:
            if (not isinstance(slot, dict) or 'filter' not in slot or
                    type(slot.get('count')) is not int or slot['count'] < 0 or
                    slot.get('quality', 'normal') != 'normal'):
                return dict(lower=0, upper=None, needed=['complete_accessible_slot_contents_and_filters'])
            if slot['count'] and (not isinstance(slot.get('name'),str)
                    or type(sizes.get(slot['name'])) is not int or sizes[slot['name']] <= 0
                    or slot['count'] > sizes[slot['name']]):
                return dict(lower=0, upper=None, needed=['consistent_slot_contents_and_stack_sizes'])
            if slot['filter'] not in (None, item):
                continue
            if slot['count'] == 0:
                room += size
            elif slot.get('name') == item and slot['count'] <= size:
                room += size - slot['count']
        return dict(lower=room, upper=room, needed=[])
    count = inventory.get('chest_slots'); contents = item_counts(inventory.get('chest'))
    if type(count) is not int or count < 0 or contents is None:
        return dict(lower=0, upper=None, needed=['accessible_slot_count_and_contents'])
    if any(type(sizes.get(name)) is not int or sizes[name] <= 0 for name in contents):
        return dict(lower=0, upper=None, needed=['item_stack_sizes'])
    used = sum(math.ceil(amount / sizes[name]) for name, amount in contents.items())
    if used > count:
        return dict(lower=0, upper=None, needed=['consistent_accessible_inventory_snapshot'])
    # Maximum assumes packed stacks and no filters; fragmentation can only reduce it.
    partial = (size - contents.get(item, 0) % size) % size
    return dict(lower=0, upper=(count - used) * size + partial,
                needed=['complete_accessible_slot_contents_and_filters'])


def build_flow(topology):
    entities = {n['key']: deepcopy(n) for n in topology['nodes'] if 'facts' in n}
    nodes, edges, missing = {}, [], []
    base = topology['identity']['base']

    def add_node(key, owner, port, **extra):
        nodes[key] = dict(key=key, owner=owner, port=port, **extra)

    def add_edge(source, target, evidence, **extra):
        if source not in nodes or target not in nodes:
            missing.append(dict(code='unobserved_endpoint', source=source, target=target))
            return
        edge = dict(source=source, target=target, evidence=evidence, **extra)
        if edge not in edges:
            edges.append(edge)

    for key, node in sorted(entities.items()):
        structure = node['facts']['structure']; kind = structure['type']
        if kind in BELTS:
            links = structure.get('transport_lines')
            indices = {1, 2} | ({3, 4} if kind == 'underground-belt' else set())
            for index in sorted(indices):
                contents = node['facts'].get('inventory', {}).get('lines')
                values = contents[index-1] if isinstance(contents, list) and len(contents) >= index else None
                add_node(lane(key, index), key, 'lane', index=index, contents=deepcopy(values))
            if links is None:
                missing.append(dict(code='native_lane_links_unobserved', entity=key))
        elif kind == 'inserter':
            add_node(key+':hand', key, 'hand')
        elif kind in STORAGE:
            add_node(key+':storage', key, 'storage')
        elif kind in MACHINES | {'boiler', 'lab'}:
            for port in ('input', 'fuel', 'output'):
                add_node(key+':'+port, key, port)

    for key, node in sorted(entities.items()):
        structure = node['facts']['structure']; kind = structure['type']
        if kind in BELTS:
            links = structure.get('transport_lines')
            if links is None:
                continue
            if not isinstance(links, list) or len(links) > 4:
                raise ValueError('Invalid bounded transport-line observation')
            seen = set()
            for line in links:
                index = line['index']; source = lane(key, index)
                if index in seen or source not in nodes or type(line.get('complete')) is not bool:
                    raise ValueError('Invalid or duplicate transport-line observation')
                seen.add(index)
                nodes[source]['outputs_complete'] = line['complete']
                if not isinstance(line.get('outputs'), list) or len(line['outputs']) > 8:
                    raise ValueError('Unbounded line outputs')
                for target in line['outputs']:
                    if type(target.get('entity')) is not int or target['entity'] <= 0:
                        raise ValueError('Invalid observed lane owner')
                    add_edge(source, lane('entity:'+str(target['entity']), target['lane']), 'native_line_relation')
        if kind != 'inserter':
            continue
        ports = structure.get('inserter_ports')
        if ports is not None:
            # Explicit resolved lane ports take precedence over geometric candidates.
            if not isinstance(ports, dict) or set(ports) != {'pickup', 'drop'}:
                raise ValueError('Invalid inserter lane-port evidence')
            if not isinstance(ports['pickup'], list) or len(ports['pickup']) > 2:
                raise ValueError('Unbounded pickup lanes')
            for target in ports['pickup']:
                add_edge(lane('entity:'+str(target['entity']), target['lane']), key+':hand', 'observed_pickup_lane')
            target = ports['drop']
            add_edge(key+':hand', lane('entity:'+str(target['entity']), target['lane']), 'observed_drop_lane')
            continue
        for field in ('pickup', 'drop'):
            matches = [other for other, e in entities.items() if other != key
                       and _contains(e['facts']['structure'].get('box'), structure.get(field))]
            if len(matches) != 1:
                missing.append(dict(code='inserter_endpoint_unresolved', entity=key, port=field))
                continue
            other = matches[0]; target = entities[other]['facts']['structure']; ports_out = []
            if target['type'] in BELTS:
                if field == 'pickup':
                    # Each lane stays a distinct possible pickup. The hand is shared.
                    order = [1,2]
                    direction = DIRECTIONS.get(target.get('direction'))
                    if target.get('belt_shape') == 'straight' and direction:
                        dx = structure['position']['x']-target['position']['x']
                        dy = structure['position']['y']-target['position']['y']
                        if -direction[1]*dx+direction[0]*dy > 0:order=[2,1]
                    ports_out = [lane(other,index) for index in order]
                elif target.get('belt_shape') == 'straight' and target['type'] == 'transport-belt':
                    direction = DIRECTIONS.get(target.get('direction'))
                    if direction:
                        dx = structure['position']['x']-target['position']['x']
                        dy = structure['position']['y']-target['position']['y']
                        right = -direction[1]*dx + direction[0]*dy
                        ports_out = [lane(other, 1 if right > 0 else 2)]
                else:
                    missing.append(dict(code='drop_lane_unobserved', entity=key, target=other))
            elif target['type'] in STORAGE:
                ports_out = [other+':storage']
            elif target['type'] in MACHINES | {'boiler', 'lab'}:
                ports_out = [other+':output'] if field == 'pickup' else [other+':input', other+':fuel']
            for priority, port in enumerate(ports_out):
                source, sink = (port, key+':hand') if field == 'pickup' else (key+':hand', port)
                evidence=dict(role=field)
                if field=='pickup' and target['type']=='transport-belt' and target.get('belt_shape') in ('straight','left','right'):
                    evidence.update(pickup_priority=priority,fallback_when_no_eligible_item=True)
                add_edge(source, sink, 'geometric_candidate', **evidence)
    return dict(schema=1, offline_only=True, historical_only=topology['historical_only'],
                identity=deepcopy(topology['identity']), tick=topology['tick'],
                topology_sha256=digest(topology), entities=entities, nodes=nodes,
                edges=sorted(edges, key=lambda e: (e['source'],e['target'],e['evidence'])),
                missing=missing, base=base)


def route_capacity(flow, route, item, requested):
    """Bounds for this route only. Unknown parallel routes are never ruled out.

    Retained snapshots establish no positive guaranteed supply/acceptance rate,
    so their lower bound stays zero. Finite upper cuts can still reject a rate.
    No observed operating rate is used as a theoretical capacity guarantee.
    """
    if len(route) < 2 or len(set(route)) != len(route) or any(k not in flow['nodes'] for k in route):
        raise ValueError('Select a simple route through observed nodes')
    constraints, needed = [], ['continuous_boundary_supply_and_sink_acceptance', 'joint_flow_service_bounds']
    for key in route:
        node = flow['nodes'][key]; entity = flow['entities'][node['owner']]
        port = node['port']; facts = entity['facts']; structure = facts['structure']
        accepted = acceptance(entity, item, port, flow['base'])
        if accepted is False:
            constraints.append((0., key, 'material_incompatible'))
        elif accepted is None and port != 'hand':
            needed.append('recipe_or_material_acceptance:'+key)
        if port == 'lane' and flow['base'] == CATALOG['factorio_version']:
            cap = BELT_UPPER.get(structure['name'])
            if cap is not None:
                constraints.append((cap, key, 'base_unstacked_lane_upper'))
        elif port == 'output':
            production = facts.get('production', {}); recipe = CATALOG['recipes'].get(production.get('recipe'))
            speed, bonus = production.get('crafting_speed'), production.get('productivity_bonus')
            if flow['base'] == CATALOG['factorio_version'] and recipe and number(speed) and number(bonus):
                products = [r for r in recipe['products'] if r['type']=='item' and r['name']==item]
                amounts = [r.get('amount',r.get('amount_max')) for r in products]
                if products and all(number(n) for n in amounts) and recipe['energy'] > 0:
                    constraints.append((sum(amounts)*speed*(1+bonus)/recipe['energy'],key,'recipe_output_upper'))
            else:
                needed.append('effective_recipe_speed_and_productivity:'+key)
    for source, target in zip(route, route[1:]):
        links = [e for e in flow['edges'] if e['source']==source and e['target']==target]
        if not links:
            if flow['nodes'][source].get('outputs_complete') is True:
                constraints.append((0.,source+' -> '+target,'observed_missing_direct_link'))
            else:
                needed.append('direct_link:'+source+' -> '+target)
        elif any(e['evidence']=='geometric_candidate' for e in links):
            needed.append('resolved_transfer_and_filters:'+source+' -> '+target)
    minimum = min(constraints) if constraints else None
    limiting = dict(element=minimum[1],reason=minimum[2]) if minimum else None
    result = classify_rate(requested,0.,minimum[0] if minimum else None,limiting=limiting,needed=needed)
    result.update(scope='selected_single_material_route',item=item,route=route,offline_only=True,
                  assumptions=['ordinary base prototypes without belt stacking'],
                  observed_operating_rate=None)
    return result


def replay_flow(source, output):
    """Read every retained mirror frame without choosing historical site IDs."""
    import hashlib
    from .agent import ROOT
    from .mirror_log import Reconstructor
    from .production_graph import build_graph
    source=Path(source);output=Path(output).resolve()
    if ROOT/'runtime' not in output.parents:
        raise ValueError('Flow evidence must remain under ignored runtime storage')
    output.mkdir(parents=True,exist_ok=False)
    reader=Reconstructor();hasher=hashlib.sha256();results=[];previous=None
    try:
        with source.open('rb') as stream:
            for raw in stream:
                hasher.update(raw);reader.apply(json.loads(raw))
                if reader.state is None:continue
                ids=sorted({int(key.split(':')[1]) for key in reader.state['domains']
                            if key.startswith('entity:') and key.endswith(':structure')})
                if not ids:continue
                scopes={d['scope'] for key,d in reader.state['domains'].items() if key.startswith('entity:')}
                historical=scopes=={'owned_factory_replay'}
                if len(ids)>64:
                    results.append(dict(tick=reader.state['tick'],status='unknown',
                                        observations_needed=['bounded_selection_of_at_most_64_entities']))
                    previous=None;continue
                try:
                    flow=build_flow(build_graph(reader.mirror(),ids,reader.state['at'],historical=historical))
                except InvalidState as exc:
                    results.append(dict(tick=reader.state['tick'],status='unknown',reason=type(exc).__name__,
                                        observations_needed=['valid_fresh_scoped_snapshot']))
                    previous=None;continue
                rates=[]
                if previous and flow['tick']>previous['tick']:
                    rates=observed_craft_rates(previous,flow)
                results.append(dict(tick=flow['tick'],flow_sha256=digest(flow),
                                    diagnoses=diagnose(flow),missing=flow['missing'],observed_craft_rates=rates))
                previous=flow
        original=hasher.hexdigest();after=hashlib.sha256()
        with source.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):after.update(chunk)
        if after.hexdigest()!=original:raise ValueError('Source changed during replay')
        report=dict(schema=1,offline_only=True,live_calls=0,source_sha256=original,
                    source_unchanged=True,frames=results,positive_rate_guarantee=False)
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(error=type(exc).__name__)))
        raise


def main():
    import argparse
    from collections import Counter
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        report=replay_flow(args.journal,args.output)
        counts=Counter(d['status'] for f in report['frames'] for d in f.get('diagnoses',[]))
        print(json.dumps(dict(frames=len(report['frames']),diagnosis_statuses=counts,live_calls=0)))
    except Exception:
        print('Offline replay could not complete; diagnostic details remain private.')
        return 1
    return 0


def diagnose(flow):
    findings = []
    for key, entity in sorted(flow['entities'].items()):
        facts = entity['facts']; structure = facts['structure']; inventory = facts.get('inventory', {})
        if structure['name'] in ('stone-furnace','steel-furnace','boiler'):
            fuel = item_counts(inventory.get('fuel')); burner = inventory.get('burner', {})
            empty = fuel == {} and burner.get('remaining_burning_fuel') == 0
            status = facts.get('power', {}).get('status_name')
            findings.append(dict(case='coal_feed',entity=key,
                status='supported_symptom' if empty and status=='no_fuel' else 'unknown',
                diagnosis='fuel_starvation_at_sample' if empty and status=='no_fuel' else None,
                cause='unknown',observations_needed=['resolved_upstream_fuel_route','feed_transfer_window']))
        if structure['type'] in STORAGE:
            contents = item_counts(inventory.get('chest'))
            if not contents:
                continue
            for pick in flow['edges']:
                if pick['source'] != key+':storage':
                    continue
                for drop in flow['edges']:
                    if drop['source'] != pick['target'] or not drop['target'].endswith(':input'):
                        continue
                    sink = flow['entities'][flow['nodes'][drop['target']]['owner']]
                    recipe = CATALOG['recipes'].get(sink['facts'].get('production', {}).get('recipe'))
                    if flow['base'] != CATALOG['factorio_version'] or not recipe:
                        findings.append(dict(case='mixed_buffer',entity=key,status='unknown',observations_needed=['sink_recipe']))
                        continue
                    for ingredient in recipe['ingredients']:
                        item = ingredient['name']
                        if ingredient['type']!='item' or contents.get(item,0)>0:
                            continue
                        room = buffer_room(entity,item)
                        findings.append(dict(case='mixed_buffer',entity=key,item=item,
                            status='supported_obstruction' if room['upper']==0 else 'unknown',
                            diagnosis='buffer_cannot_accept_required_item' if room['upper']==0 else None,
                            room=room,observations_needed=room['needed'] if room['upper']!=0 else [],
                            limitation='A local buffer obstruction does not prove all alternative supplies are blocked.'))
    for key, node in sorted(flow['nodes'].items()):
        if node['port']!='lane':
            continue
        counts=item_counts(node.get('contents'))
        if counts and SCIENCE <= {name for name,count in counts.items() if count>0}:
            findings.append(dict(case='science_lane',entity=node['owner'],lane=key,status='unknown',
                observed='red_and_green_share_one_lane',diagnosis=None,
                observations_needed=['ordered_lane_items','lab_input_acceptance','continuous_item_motion_and_delivery_window']))
    present={f['case'] for f in findings}
    for case in ('coal_feed','mixed_buffer','science_lane'):
        if case not in present:
            findings.append(dict(case=case,status='unknown',diagnosis=None,
                                 observations_needed=['relevant_pre_failure_scoped_observations']))
    return findings


def observed_craft_rates(before, after):
    if before['identity'] != after['identity'] or after['tick'] <= before['tick']:
        raise ValueError('Rate samples need one episode and advancing ticks')
    seconds=(after['tick']-before['tick'])/60
    result=[]
    for key, entity in sorted(after['entities'].items()):
        old=before['entities'].get(key)
        if not old or old['facts']['structure']['name'] != entity['facts']['structure']['name']:
            continue
        a=old['facts'].get('production',{}).get('products_finished')
        b=entity['facts'].get('production',{}).get('products_finished')
        if not number(a) or not number(b):continue
        if b<a:raise ValueError('Production counter regressed')
        result.append(dict(entity=key,completed_crafts=b-a,crafts_per_second=(b-a)/seconds,
                           item_delivery_rate=None,capacity_guarantee=False,
                           limitation='Recipe continuity and sink delivery are not established by these counters.'))
    return result


if __name__=='__main__':
    raise SystemExit(main())
